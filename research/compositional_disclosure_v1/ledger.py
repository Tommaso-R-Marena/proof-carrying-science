"""Research disclosure ledger. One trusted dataset namespace, shared across callers.

Public planners see only prior knowledge and public receipts, never the actual
world or private audit database. Same-host Python/SQLite are trusted, not immutable.
There is deliberately no reset, load-from-unanchored-storage, or new-session API.
"""
import json,sqlite3,threading
from pathlib import Path
from pcs.jsonio import strict_json_loads
from research.llm_firewall_v1.monitor import digest
from .authority import Authority,packet

INITIAL=sum(1<<w for w in range(16) if w.bit_count()==2)
def canonical(d):return json.dumps(d,sort_keys=True,separators=(',',':'))
def parse(raw):
    if type(raw) is not bytes or len(raw)>4096:raise ValueError('Bounded proposal required')
    p=strict_json_loads(raw.decode())
    if type(p) is not dict or set(p)!={'query'} or type(p['query']) is not int or not 0<=p['query']<16:raise ValueError('One exact public subset query required')
    return p['query']

class Ledger:
    def __init__(self,path,authority,*,world,prior=INITIAL):
        if type(authority) is not Authority:raise ValueError('Fixed real Lean authority required')
        packet(prior,world,0);authority.check()
        # Real native validity check, not a Python affirmative surrogate.
        if authority.query(packet(prior,world,0))[1]!=1:raise ValueError('Ambiguous prior containing actual world required')
        self.path=Path(path).resolve();self.authority=authority;self.contract=(prior,world)
        self.genesis=digest(b'PCS-DISCLOSURE-1'+bytes((prior%256,prior//256,world)))
        self.anchor=self.genesis;self.lock=threading.RLock()
        if self.path.exists():raise ValueError('Fresh trusted namespace required; no unauthenticated restart')
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(self.path) as c:
            c.executescript('CREATE TABLE contract(prior INTEGER,world INTEGER); CREATE TABLE state(generation INTEGER,candidates INTEGER); CREATE TABLE receipts(id INTEGER PRIMARY KEY,record TEXT,sha TEXT); CREATE TABLE public(id INTEGER PRIMARY KEY,query INTEGER,status INTEGER,answer INTEGER);')
            c.execute('INSERT INTO contract VALUES(?,?)',self.contract);c.execute('INSERT INTO state VALUES(0,?)',(prior,))
    def connection(self):
        c=sqlite3.connect(self.path.as_uri()+'?mode=rw',uri=True,timeout=15);c.execute('PRAGMA synchronous=FULL');return c
    def _audit(self,c):
        if c.execute('SELECT prior,world FROM contract').fetchall()!=[self.contract]:raise ValueError('Dataset/prior substitution')
        rows=c.execute('SELECT id,record,sha FROM receipts ORDER BY id').fetchall()
        if len(rows)>32:raise ValueError('Bounded research transcript required')
        previous=self.genesis;k,w=self.contract;seen=[previous];public=[];pairs=[]
        for gen,(rid,text,sha) in enumerate(rows,1):
            if rid!=gen or type(text) is not str or len(text)>4096 or digest(text.encode())!=sha:raise ValueError('Receipt integrity')
            r=json.loads(text)
            if set(r)!={'request','reply','previous'} or r['previous']!=previous or canonical(r)!=text:raise ValueError('Receipt chain')
            request=bytes.fromhex(r['request']);reply=bytes.fromhex(r['reply'])
            if len(request)!=5 or request[:4]!=packet(k,w,0)[:4]:raise ValueError('Posterior/world substitution')
            if self.authority.query(request)!=reply or reply[1] not in {0,1}:raise ValueError('Native replay differs')
            k=reply[2]+256*reply[3]
            public.append((gen,request[4],reply[1],reply[4] if reply[1] else None))
            previous=sha;seen.append(sha);pairs.append((request,reply))
        if self.anchor not in seen:raise ValueError('Live prefix rollback/fork')
        if c.execute('SELECT generation,candidates FROM state').fetchall()!=[(len(rows),k)] or c.execute('SELECT id,query,status,answer FROM public ORDER BY id').fetchall()!=public:raise ValueError('Actual effects/state differ from Lean replies')
        return dict(generation=len(rows),candidates=k,receipt=previous,public=public,pairs=pairs)
    def _dispatch(self,c,g,q,r):
        c.execute('INSERT INTO public VALUES(?,?,?,?)',(g,q,r[1],r[4] if r[1] else None))
        c.execute('UPDATE state SET generation=?,candidates=?',(g,r[2]+256*r[3]))
    def _commit(self,c):c.commit()
    def query(self,q,*,expected_generation):
        if type(q) is not int or not 0<=q<16 or type(expected_generation) is not int:raise ValueError('Exact public query and generation required')
        with self.lock:
            c=self.connection()
            try:
                c.execute('BEGIN IMMEDIATE');old=self._audit(c)
                if old['generation']!=expected_generation or old['generation']>=32:raise ValueError('Stale generation or bounded transcript exhausted')
                request=packet(old['candidates'],self.contract[1],q);reply=self.authority.query(request)
                if reply[1] not in {0,1}:raise ValueError('Native validity refusal')
                g=old['generation']+1;self._dispatch(c,g,q,reply)
                text=canonical(dict(request=request.hex(),reply=reply.hex(),previous=old['receipt']))
                c.execute('INSERT INTO receipts VALUES(?,?,?)',(g,text,digest(text.encode())))
                staged=self._audit(c);self._commit(c);self.anchor=staged['receipt']
                return dict(generation=g,query=q,accepted=reply[1]==1,answer=reply[4] if reply[1] else None)
            except BaseException:
                c.rollback();raise
            finally:c.close()
    def audit(self):
        with self.lock:
            c=self.connection()
            try:
                c.execute('BEGIN');r=self._audit(c);c.rollback();self.anchor=r['receipt'];return r
            finally:c.close()
    def certify(self,label):return self.authority.certify(self.audit()['pairs'],label)
