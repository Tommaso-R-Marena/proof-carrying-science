"""Fixed synthetic SQLite tools, native admission, atomic receipts and live anchor.

No network/shell/general Python effects are exposed. This is a concrete research
adapter, not a sandbox for arbitrary tools or an immutable independently run root.
"""
from __future__ import annotations
import atexit,json,re,sqlite3,threading
from pathlib import Path
from pcs.jsonio import strict_json_loads
from .certificate import encode,sha,propose,groups
from .example import model
from .authority import Authority,packet
PRIVATE='PCS_SYNTHETIC_PRIVATE_CANARY'
PUBLIC='APPROVED_PUBLIC_SUMMARY'

_FIXED_AUTHORITY=None
_BUILD_LOCK=threading.Lock()
def _fixed_authority(raw,cert,build_dir):
    # Trusted process-owned build only. Never load an on-disk or caller-supplied
    # authority cache. Every reuse checks exact source/tool/artifact identity.
    global _FIXED_AUTHORITY
    with _BUILD_LOCK:
        if _FIXED_AUTHORITY is None:_FIXED_AUTHORITY=Authority(raw,cert,build_dir)
        _FIXED_AUTHORITY.check()
        if (_FIXED_AUTHORITY.model_raw,_FIXED_AUTHORITY.cert_raw)!=(raw,cert):raise ValueError('fixed workflow identity changed')
        return _FIXED_AUTHORITY

def _close_fixed():
    if _FIXED_AUTHORITY is not None:_FIXED_AUTHORITY.close()
atexit.register(_close_fixed)

def parse_proposal(raw):
    if type(raw) is not bytes or len(raw)>4096:raise ValueError('bounded proposal bytes required')
    try:
        d=strict_json_loads(raw.decode('utf-8',errors='strict'))
        if type(d) is not dict or set(d)!={'action'}:return None,'MALFORMED_FALLBACK'
        a=d['action']
        if a is not None and (type(a) is not int or not 0<=a<65536):return None,'MALFORMED_FALLBACK'
        return a,'TYPED_PROPOSAL'
    except (ValueError,UnicodeError,RecursionError):return None,'MALFORMED_FALLBACK'

class Broker:
    def __init__(self,path,build_dir,*,pre_sanitized=False):
        if type(pre_sanitized) is not bool:raise ValueError('trusted fixture mode must be Boolean')
        self.path=Path(path);self._lock=threading.RLock();self._closed=False;self._pre=pre_sanitized
        self.model_raw=encode(model());self.cert_raw=encode(propose(self.model_raw,[4]))
        if self.path.exists():raise FileExistsError('Existing ledger cannot be adopted without an external restart anchor')
        self._authority=_fixed_authority(self.model_raw,self.cert_raw,build_dir)
        try:
            with self.path.open('xb'):pass  # Never adopt/rewrite an existing ledger.
            self._db=sqlite3.connect(self.path,isolation_level=None,check_same_thread=False)
            self._db.execute('PRAGMA journal_mode=WAL');self._db.execute('PRAGMA synchronous=FULL')
            self._db.executescript('CREATE TABLE meta(state INTEGER,generation INTEGER,head TEXT); CREATE TABLE events(id TEXT PRIMARY KEY,generation INTEGER UNIQUE,body_sha TEXT,event_json TEXT); CREATE TABLE payload(value TEXT,loaded INTEGER,sanitized INTEGER); CREATE TABLE public(value TEXT);')
            self._source_id=self._authority.source_id
            self._seed=self._authority.source_binding.seed(pre_sanitized)
            self._db.execute('INSERT INTO meta VALUES(0,0,?)',(self._seed,))
            self._db.execute('INSERT INTO payload VALUES(?,0,?)',(PUBLIC if pre_sanitized else PRIVATE,int(pre_sanitized)))
            self._anchor=(0,0,self._seed)
        except BaseException:raise
    def _verify(self):
        self._authority.check();state=0;head=self._seed;generation=0
        payload=PUBLIC if self._pre else PRIVATE;loaded=0;sanitized=int(self._pre);public=[]
        edges=groups(model())
        for rid,g,bsha,encoded in self._db.execute('SELECT id,generation,body_sha,event_json FROM events ORDER BY generation'):
            event=json.loads(encoded);core={k:v for k,v in event.items() if k!='event_sha256'}
            if event.get('generation')!=generation+1 or event.get('source')!=state or event.get('previous_sha256')!=head or event.get('request_id')!=rid or event.get('body_sha256')!=bsha or g!=generation+1 or sha(encode(core))!=event.get('event_sha256'):raise ValueError('receipt chain corrupted')
            req=packet(state,event['proposal']);reply=self._authority.query_raw(req)
            if event['request_hex']!=req.hex() or event['reply_hex']!=reply.hex() or reply[1]!=1 or event['source_id']!=self._source_id:raise ValueError('receipt/native correspondence mismatch')
            action=reply[2]+256*reply[3];target=event['target']
            if event['action']!=action or target not in edges[state,action]:raise ValueError('unmodeled transition in receipt')
            if action==1:
                loaded=1
                if target!=(3 if payload==PUBLIC else 2):raise ValueError('wrong observed read outcome')
            elif action==2:payload=PUBLIC;sanitized=1
            elif action==3:
                if payload!=PUBLIC or not sanitized:raise ValueError('unapproved publication')
                public.append(PUBLIC)
            state=target;generation+=1;head=event['event_sha256']
        observed=tuple(self._db.execute('SELECT state,generation,head FROM meta').fetchone() or ())
        if observed!=(state,generation,head) or observed!=self._anchor:raise ValueError('state rollback/substitution or unanchored restart')
        if self._db.execute('SELECT value,loaded,sanitized FROM payload').fetchall()!=[(payload,loaded,sanitized)] or self._db.execute('SELECT value FROM public').fetchall()!=[(v,) for v in public]:raise ValueError('materialized effects disagree with checked history')
        return state,generation,head
    def _apply(self,state,action):
        if (state,action)==(0,0):return 1
        if (state,action)==(1,1):
            value=self._db.execute('SELECT value FROM payload').fetchone()[0]
            self._db.execute('UPDATE payload SET loaded=1')
            return 3 if value==PUBLIC else 2
        if (state,action)==(2,2):
            self._db.execute('UPDATE payload SET value=?,sanitized=1',(PUBLIC,));return 3
        if (state,action)==(3,3):
            value,loaded,sanitized=self._db.execute('SELECT value,loaded,sanitized FROM payload').fetchone()
            if value!=PUBLIC or not loaded or not sanitized:raise ValueError('fixed tool refuses unsanitized publication')
            self._db.execute('INSERT INTO public VALUES(?)',(value,));return 4
        raise ValueError('no actual fixed tool for this native action')
    def step(self,raw,request_id):
        if type(request_id) is not str or re.fullmatch('[a-z0-9_-]{1,64}',request_id) is None:raise ValueError('bounded request identity required')
        proposal,classification=parse_proposal(raw)
        with self._lock:
            if self._closed:raise ValueError('broker closed/quarantined')
            self._db.execute('BEGIN IMMEDIATE')
            try:
                state,generation,head=self._verify()
                old=self._db.execute('SELECT body_sha,event_json FROM events WHERE id=?',(request_id,)).fetchone()
                if old:
                    if old[0]!=sha(raw):raise ValueError('same request identity, different bytes')
                    self._db.execute('ROLLBACK');return json.loads(old[1])
                req=packet(state,proposal);reply=self._authority.query_raw(req)
                if reply[0]!=1 or reply[1] not in [0,1,2,3]:raise ValueError('native protocol failure')
                if reply[1]!=1:
                    self._db.execute('ROLLBACK')
                    return dict(status='HALTED' if reply[1]==0 else 'REFUSED',state=state,generation=generation,pcs_authority=False)
                action=reply[2]+256*reply[3];target=self._apply(state,action)
                ranks=dict(json.loads(self.cert_raw)['ranks'])
                if target not in groups(model())[state,action] or ranks.get(target,65536)>=ranks[state] or reply[4]+256*reply[5]!=ranks[state]:raise ValueError('actual tool outcome does not match progress model')
                event=dict(request_id=request_id,generation=generation+1,source=state,target=target,action=action,proposal=proposal,
                    proposal_classification=classification,body_sha256=sha(raw),request_hex=req.hex(),reply_hex=reply.hex(),
                    source_id=self._source_id,previous_sha256=head,pcs_authority=False)
                event['event_sha256']=sha(encode(event))
                self._db.execute('INSERT INTO events VALUES(?,?,?,?)',(request_id,generation+1,sha(raw),encode(event).decode()))
                changed=self._db.execute('UPDATE meta SET state=?,generation=?,head=? WHERE state=? AND generation=? AND head=?',(target,generation+1,event['event_sha256'],state,generation,head)).rowcount
                if changed!=1:raise ValueError('stale state/generation')
                self._db.execute('COMMIT');self._anchor=(target,generation+1,event['event_sha256'])
                self._verify();return event
            except BaseException:
                if self._db.in_transaction:self._db.execute('ROLLBACK')
                raise
    def snapshot(self):
        with self._lock:
            state,generation,head=self._verify()
            return dict(state=state,transitions=generation,head=head,public=[v[0] for v in self._db.execute('SELECT value FROM public')],pcs_authority=False)
    def close(self):
        with self._lock:
            self._closed=True
            if hasattr(self,'_db'):self._db.close()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
