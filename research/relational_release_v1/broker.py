"""One precommitted public query, private proposal phase, trusted finalization.

Memory anchors protect live receipt ancestry, not an administrator-controlled root.
The scheduler must call finalize even on model refusal/failure. No timing guarantee.
"""
import json,sqlite3,subprocess,threading
from pathlib import Path
from pcs.jsonio import strict_json_loads
from research.llm_firewall_v1.monitor import digest
from .authority import Authority,packet

def canonical(d):return json.dumps(d,sort_keys=True,separators=(',',':'))
def parse(raw):
    if type(raw) is not bytes or len(raw)>4096:raise ValueError('Bounded proposal required')
    d=strict_json_loads(raw.decode())
    if type(d) is not dict or set(d)!={'count','style','submit'} or type(d['count']) is not int or not 0<=d['count']<=4 or type(d['style']) is not str or d['style'] not in {'forward','reverse'} or type(d['submit']) is not bool:raise ValueError('Exact claim schema required')
    return d

class Session:
    def __init__(self,path,authority,*,query,mask,hidden):
        if type(authority) is not Authority:raise ValueError('Fixed real native authority required')
        authority.check();packet(query,0,mask,hidden,0)
        self.authority=authority;self.path=Path(path).resolve();self.contract=(query,mask,hidden)
        self.genesis=digest(b'PCS-RELATIONAL-1'+bytes(self.contract));self.anchor=self.genesis;self.mutex=threading.RLock()
        if self.path.exists():raise ValueError('Fresh session required')
        self.path.parent.mkdir(parents=True,exist_ok=True)
        c=sqlite3.connect(self.path)
        try:
            c.executescript('CREATE TABLE meta(q INTEGER,mask INTEGER,hidden INTEGER); CREATE TABLE receipts(id INTEGER PRIMARY KEY,record TEXT,sha TEXT); CREATE TABLE state(closed INTEGER); INSERT INTO state VALUES(0); CREATE TABLE public(id INTEGER PRIMARY KEY CHECK(id=1),payload BLOB);')
            c.execute('INSERT INTO meta VALUES(?,?,?)',self.contract);c.commit()
        finally:c.close()
    def connection(self):
        c=sqlite3.connect(self.path.as_uri()+'?mode=rw',uri=True,timeout=15);c.execute('PRAGMA synchronous=FULL');return c
    def _audit(self,c):
        if c.execute('SELECT q,mask,hidden FROM meta').fetchall()!=[self.contract]:raise ValueError('Precommitted query/resources changed')
        rows=c.execute('SELECT id,record,sha FROM receipts ORDER BY id').fetchall()
        if len(rows)>8:raise ValueError('Receipt budget exceeded')
        previous=self.genesis;closed=0;public=[];seen=[self.genesis];pairs=[]
        q,mask,hidden=self.contract
        for i,(rid,text,sha) in enumerate(rows,1):
            if rid!=i or type(text) is not str or len(text)>8192 or digest(text.encode())!=sha:raise ValueError('Receipt integrity')
            r=json.loads(text)
            if set(r)!={'request','reply','previous'} or r['previous']!=previous or canonical(r)!=text:raise ValueError('Receipt chain')
            request=bytes.fromhex(r['request']);reply=bytes.fromhex(r['reply'])
            if len(request)!=8 or request[:5]!=bytes((3,q,closed,mask,hidden)):raise ValueError('Contract/state substitution')
            if self.authority.query(request)!=reply:raise ValueError('Native replay differs')
            if reply[1]==1 and request[5]==2:
                closed=1;public.append(reply[4:])
            previous=sha;seen.append(sha);pairs.append((request,reply))
        if self.anchor not in seen:raise ValueError('Live receipt rollback/fork')
        if len(public)>1 or c.execute('SELECT payload FROM public ORDER BY id').fetchall()!=[(b,) for b in public] or c.execute('SELECT closed FROM state').fetchall()!=[(closed,)]:raise ValueError('Actual SQL effects differ from native plans')
        return dict(closed=closed,receipt=previous,public=public,pairs=pairs,attempts=len(rows))
    def _dispatch(self,c,request,reply):
        if reply[1]==1 and request[5]==2:
            c.execute('INSERT INTO public VALUES(1,?)',(reply[4:],));c.execute('UPDATE state SET closed=1')
    def _commit(self,c):c.commit()
    def _operate(self,action,style=0,reported=0):
        with self.mutex:
            c=None
            try:
                c=self.connection();c.execute('BEGIN IMMEDIATE');before=self._audit(c)
                # Private proposals must never consume the trusted completion
                # slot: otherwise quota exhaustion recreates suppression.
                if before['attempts']>=(8 if action==2 else 7):raise ValueError('Reserved completion/receipt budget exhausted')
                q,mask,hidden=self.contract;request=packet(q,before['closed'],mask,hidden,action,style,reported)
                reply=self.authority.query(request)
                if reply[1] not in {0,1} or reply[3]!=action:raise ValueError('Unexpected native verdict')
                self._dispatch(c,request,reply)
                record=canonical(dict(request=request.hex(),reply=reply.hex(),previous=before['receipt']));sha=digest(record.encode())
                c.execute('INSERT INTO receipts(record,sha) VALUES(?,?)',(record,sha));staged=self._audit(c)
                self._commit(c);self.anchor=staged['receipt']
                return reply
            except (ValueError,UnicodeError,OSError,sqlite3.Error,TypeError,KeyError,subprocess.SubprocessError):
                if c is not None:c.rollback()
                raise ValueError('Research release operation refused') from None
            finally:
                if c is not None:c.close()
    def read_private(self):
        r=self._operate(0)
        if r[1]!=1:raise ValueError('Private read refused')
        if len(r)!=9 or any(x>1 for x in r[4:]):raise ValueError('Invalid private observation')
        return dict(hidden_bit=r[4],flags=list(r[5:]))
    def propose(self,raw):
        p=parse(raw);r=self._operate(1,int(p['style']=='reverse'),p['count'])
        # This is private feedback. A valid claim is never published here.
        return dict(valid=r[1]==1,submitted=p['submit'],control_public=r[4:].hex() if r[1]==1 and p['submit'] else None)
    def finalize(self):
        r=self._operate(2)
        if r[1]!=1:raise ValueError('Finalization refused')
        return r[4:]
    def audit(self):
        with self.mutex:
            c=self.connection()
            try:c.execute('BEGIN');r=self._audit(c);c.rollback();self.anchor=r['receipt'];return r
            finally:c.close()
    def certify(self,label):return self.authority.certify(self.audit()['pairs'],label)
