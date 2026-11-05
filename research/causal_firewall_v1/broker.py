"""Execute only returned native byte plans; replay before every attempted write.

Audit packets contain private resources and MUST NOT be sent as model feedback.
Only the explicit model_feedback projection is delivered to the untrusted agent.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import sqlite3
import subprocess

from research.llm_firewall_v1.broker import parse
from research.llm_firewall_v1.monitor import digest
from .authority import Authority,decode_reply,encode_request


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'))
def blob(text):
    if type(text) is not str:raise ValueError('UTF-8 text required')
    value=text.encode('utf-8')
    if len(value)>1024:raise ValueError('Bounded text required')
    return value
def genesis(public,private):return digest(b'PCS-CAUSAL-INITIAL-1'+len(public).to_bytes(2,'little')+public+len(private).to_bytes(2,'little')+private)


class Session:
    def __init__(self,path,authority,*,public='PUBLIC_OK',private='PCS_SYNTHETIC_CANARY'):
        self._bind(path,authority);self.public=blob(public);self.private=blob(private)
        self.genesis=genesis(self.public,self.private)
        if self.path.exists():raise ValueError('Fresh session required')
        self.path.parent.mkdir(parents=True,exist_ok=True)
        c=sqlite3.connect(self.path)
        try:
            c.executescript('''PRAGMA journal_mode=DELETE;
                CREATE TABLE state(id INTEGER PRIMARY KEY CHECK(id=1),
                    generation INTEGER CHECK(generation BETWEEN 0 AND 8),
                    remaining INTEGER CHECK(remaining BETWEEN 0 AND 8),tainted INTEGER CHECK(tainted IN (0,1)));
                INSERT INTO state VALUES(1,0,8,0);
                CREATE TABLE meta(id INTEGER PRIMARY KEY CHECK(id=1),public BLOB,private BLOB,genesis TEXT);
                CREATE TABLE effects(id INTEGER PRIMARY KEY,kind INTEGER CHECK(kind IN (1,2)),payload BLOB);
                CREATE TABLE attempts(id INTEGER PRIMARY KEY,record TEXT,sha256 TEXT);
                CREATE TABLE protected(id INTEGER PRIMARY KEY CHECK(id=1),value TEXT,admin INTEGER);
                INSERT INTO protected VALUES(1,'retain',0);''')
            c.execute('INSERT INTO meta VALUES(1,?,?,?)',(self.public,self.private,self.genesis));c.commit()
        finally:c.close()

    def _bind(self,path,authority):
        if type(authority) is not Authority:raise ValueError('Fixed real compiled effect authority required')
        authority.check();self.path=Path(path).resolve();self.authority=authority

    def connection(self):
        # mode=rw refuses a missing file instead of creating an empty replacement.
        c=sqlite3.connect(self.path.as_uri()+'?mode=rw',uri=True,timeout=15)
        c.execute('PRAGMA synchronous=FULL');return c

    @classmethod
    def reopen(cls,path,authority,checkpoint):
        s=cls.__new__(cls);s._bind(path,authority)
        if type(checkpoint) is not dict or set(checkpoint)!={'generation','receipt','genesis'}:
            raise ValueError('Host-retained expected checkpoint required')
        if type(checkpoint['generation']) is not int or not 0<=checkpoint['generation']<=8 or any(
                type(checkpoint[k]) is not str or not re.fullmatch('[0-9a-f]{64}',checkpoint[k]) for k in ['genesis','receipt']):
            raise ValueError('Invalid checkpoint')
        c=s.connection()
        try:
            public,private,g=c.execute('SELECT public,private,genesis FROM meta WHERE id=1').fetchone()
        finally:c.close()
        if type(public) is not bytes or type(private) is not bytes or len(public)>1024 or len(private)>1024 or genesis(public,private)!=checkpoint['genesis'] or g!=checkpoint['genesis']:
            raise ValueError('Initial resources changed')
        public.decode('utf-8');private.decode('utf-8')
        s.public=public;s.private=private;s.genesis=g
        if s.checkpoint()!=checkpoint:raise ValueError('Rollback/fork or unexpected protected checkpoint')
        return s

    def _replay(self,c):
        if c.execute('SELECT public,private,genesis FROM meta WHERE id=1').fetchone()!=(self.public,self.private,self.genesis):
            raise ValueError('Protected initial resources changed')
        state=(0,8,0);previous=self.genesis;effects=[];intents=[];plans=[]
        rows=c.execute('SELECT id,record,sha256 FROM attempts ORDER BY id').fetchall()
        if len(rows)>32:raise ValueError('Bounded attempt history required')
        for index,(rid,encoded,sha) in enumerate(rows,1):
            if rid!=index or type(encoded) is not str or len(encoded)>32768 or digest(encoded.encode())!=sha:
                raise ValueError('Receipt integrity failed')
            r=json.loads(encoded)
            if set(r)!={'proposal_hex','request_hex','reply_hex','previous'} or r['previous']!=previous or canonical(r)!=encoded:
                raise ValueError('Receipt structure/chain failed')
            raw=bytes.fromhex(r['proposal_hex']);p=parse(raw)
            request=encode_request(state,p.action,p.text.encode(),self.public,self.private)
            if request.hex()!=r['request_hex']:raise ValueError('Receipt request does not bind canonical intent/resources')
            reply=self.authority.query(request)
            if reply.hex()!=r['reply_hex']:raise ValueError('Stored verdict/effect differs from actual native replay')
            plan=decode_reply(reply)
            if plan.status not in {0,1} or plan.action!=p.action:raise ValueError('Unexpected native plan')
            if plan.status==1:
                self._sanity(state,p,plan)
                if plan.effect:effects.append((plan.effect,plan.payload))
                intents.append((p.action,p.text.encode()));plans.append((plan.effect,plan.payload));state=plan.after
            elif plan.after!=state:raise ValueError('Denied plan changes protected state')
            previous=sha
        actual=c.execute('SELECT kind,payload FROM effects ORDER BY id').fetchall()
        if actual!=effects or c.execute('SELECT generation,remaining,tainted FROM state WHERE id=1').fetchone()!=state:
            raise ValueError('Database effects/state differ from independently executed byte plans')
        if c.execute('SELECT value,admin FROM protected WHERE id=1').fetchone()!=('retain',0):
            raise ValueError('Protected data/privileges changed')
        return dict(state=state,receipt=previous,effects=effects,intents=intents,plans=plans,attempts=len(rows))

    def _sanity(self,state,p,plan):
        # Independent host checks only refuse; they cannot replace native allow.
        g,b,t=state;a=p.action;cost=2 if a==3 else 1
        if g>=8 or b<cost or a in {5,6,7} or (t and a in {3,4}):raise ValueError('Inconsistent native permission')
        effect=1 if a==2 else 2 if a in {3,4} else 0
        expected=(g+1,b-cost,int(bool(t or a==1)))
        observation=self.public if a==0 else self.private if a==1 else b''
        if plan.after!=expected or plan.effect!=effect or plan.payload!=(p.text.encode() if effect else b'') or plan.observation!=observation:
            raise ValueError('Native plan/host intent handoff differs')

    def _dispatch_plan(self,c,plan):
        # The caller's Proposal.text is never used here. Effect identity/payload
        # originate solely in the real compiled Lean reply's immutable bytes.
        if plan.effect:c.execute('INSERT INTO effects(kind,payload) VALUES(?,?)',(plan.effect,plan.payload))

    def apply(self,raw,*,expected_generation):
        try:p=parse(raw)
        except (ValueError,UnicodeError,RecursionError,TypeError):return dict(status='REFUSED',accepted=False,error='tool_request_refused')
        c=None
        try:
            c=self.connection();c.execute('BEGIN IMMEDIATE');before=self._replay(c)
            if type(expected_generation) is not int or before['state'][0]!=expected_generation or before['attempts']>=32:
                raise ValueError('Stale/conflicting generation or exhausted receipt budget')
            request=encode_request(before['state'],p.action,p.text.encode(),self.public,self.private)
            reply=self.authority.query(request);plan=decode_reply(reply)
            if plan.status not in {0,1} or plan.action!=p.action:raise ValueError('Invalid native effect plan')
            accepted=plan.status==1
            if accepted:
                self._sanity(before['state'],p,plan)
                self._dispatch_plan(c,plan)
                c.execute('UPDATE state SET generation=?,remaining=?,tainted=? WHERE id=1',plan.after)
            elif plan.after!=before['state']:raise ValueError('Denied state change')
            record=dict(proposal_hex=raw.hex(),request_hex=request.hex(),reply_hex=reply.hex(),previous=before['receipt'])
            encoded=canonical(record);sha=digest(encoded.encode())
            c.execute('INSERT INTO attempts(record,sha256) VALUES(?,?)',(encoded,sha))
            # Check the actual staged SQL rows too. A dispatch/persistence defect
            # must roll back, even when the native verdict itself was valid.
            self._replay(c)
            feedback=dict(status='COMMITTED' if accepted else 'BLOCKED',accepted=accepted,action=p.action,
                          after=plan.after,result=plan.observation.decode('utf-8') if accepted and p.action in {0,1} else 'stored' if accepted else None,
                          public_output=plan.payload.decode('utf-8') if accepted and plan.effect==2 else None)
            c.commit()
            return feedback
        except (ValueError,UnicodeError,OSError,sqlite3.Error,subprocess.SubprocessError,TypeError,KeyError):
            if c is not None:c.rollback()
            return dict(status='REFUSED',accepted=False,error='tool_request_refused')
        finally:
            if c is not None:c.close()

    def audit(self):
        c=self.connection()
        try:
            c.execute('BEGIN');r=self._replay(c);c.rollback();return r
        finally:c.close()

    def state(self):return self.audit()['state']
    def effects(self):return self.audit()['effects']
    def checkpoint(self):
        r=self.audit();return dict(generation=r['state'][0],receipt=r['receipt'],genesis=self.genesis)
    def transcript(self):
        c=self.connection()
        try:return [dict(record=json.loads(r),sha256=h) for r,h in c.execute('SELECT record,sha256 FROM attempts ORDER BY id')]
        finally:c.close()
    def certify(self,label):
        r=self.audit()
        return self.authority.certify(r['intents'],self.public,self.private,r['state'],r['plans'],label)


def model_feedback(result):
    """No audit hashes/native packets/checkpoints/private-resource metadata."""
    fields={'status','accepted','action','after','result','public_output','error'}
    if type(result) is not dict or not set(result)<=fields:raise ValueError('Unreviewed model feedback field')
    return {k:result[k] for k in ['status','accepted','action','after','result','public_output','error'] if k in result}
