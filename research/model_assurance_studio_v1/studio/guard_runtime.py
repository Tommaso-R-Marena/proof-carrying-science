"""Host-side, pre-dispatch authorization with a toy in-memory action backend.

Unlike v0.3 post-hoc trace inspection, this boundary actually mediates every
invocation to the *demo* executor and denies before side effects. Nothing is
published externally, no third-party tools execute and HMAC is not a PCS Lean
certificate. A production integration must make this the ONLY path to real tools.
"""
from __future__ import annotations
import hashlib
import hmac
import json
import os
import threading
from copy import deepcopy
from .agent_gate import authorize, DEMO_POLICY, DEMO_APPROVED_SUMMARY

class GuardError(ValueError):pass

def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()

def sha(obj):return hashlib.sha256(canonical(obj)).hexdigest()

def mac(secret,record):return hmac.new(secret,canonical(record),hashlib.sha256).hexdigest()

class GuardedDemoRuntime:
    def __init__(self,*,policy=None,key=None):
        self._policy=deepcopy(DEMO_POLICY if policy is None else policy)
        if (not isinstance(self._policy,dict) or self._policy.get('schema')!='pcs-agent-action-policy-v1' or
            set(self._policy)!={'schema','rules','maximum_approved_actions'} or
            not isinstance(self._policy['rules'],dict) or
            not isinstance(self._policy['maximum_approved_actions'],int) or
            isinstance(self._policy['maximum_approved_actions'],bool) or
            not 0<=self._policy['maximum_approved_actions']<=256):
            raise GuardError('Invalid host-owned action policy')
        # Only the two built-in toy capability names exist in this backend.
        if set(self._policy['rules'])-{'read_public_dataset','publish_summary'}:
            raise GuardError('Toy backend cannot execute unknown capabilities')
        # Validate every reviewer-owned rule before accepting any model proposal.
        for name,rule in self._policy['rules'].items():
            if not isinstance(rule,dict):raise GuardError('Each host rule must be an exact object')
            expected={'channel','exact_body'} if name=='publish_summary' else {'dataset_id'}
            if set(rule)!=expected or any(not isinstance(rule[k],str) or not rule[k] or len(rule[k])>8192 for k in expected):
                raise GuardError('Malformed host rule or exceeded rule value budget')
        self._key=os.urandom(32) if key is None else key
        if not isinstance(self._key,bytes) or len(self._key)<32:raise GuardError('Host audit key must be at least 32 bytes')
        self.policy_sha256=sha(self._policy)
        self._events=[]
        self._lock=threading.RLock()
        self._seen=set()
        self._accepted=0
        self._publications=[]
        self._datasets={'synthetic-public-v1':{'study':'PCS fixture','approved_result_count':12}}

    def _append(self,record):
        predecessor=self._events[-1]['mac'] if self._events else '0'*64
        item={'sequence':len(self._events)+1,'previous_mac':predecessor,
              'policy_sha256':self.policy_sha256, **record}
        self._events.append({'record':item,'mac':mac(self._key,item)})

    def execute(self,proposal):
        """The *only* intended route to the toy side-effecting backend.

        The lock covers preflight, reservation, execution and recording. No caller
        can pass a model-supplied policy into this method.
        """
        with self._lock:
            pid=proposal.get('id') if isinstance(proposal,dict) else None
            if isinstance(pid,str) and pid in self._seen:
                self._append({'action_id':pid,'decision':'DENY','reason':'Reused action ID'})
                return {'allowed':False,'reason':'Reused action ID'}
            if isinstance(pid,str):self._seen.add(pid)
            try:
                proposal_sha256=sha(proposal)
            except (TypeError,ValueError):
                self._append({'action_id':str(pid)[:64],'decision':'DENY','reason':'Not canonical JSON'})
                return {'allowed':False,'reason':'Not canonical JSON'}
            ok,reason=authorize(proposal,self._policy)
            if ok and self._accepted>=self._policy['maximum_approved_actions']:
                ok=False;reason='Reviewer-owned approved action budget exhausted'
            if not ok:
                self._append({'action_id':str(pid)[:64],'proposal_sha256':proposal_sha256,
                              'decision':'DENY','reason':reason})
                return {'allowed':False,'reason':reason}
            # Reserve budget before side effect. An exception is not treated as a
            # certified absence of effect; mark it INDETERMINATE and never retry.
            self._accepted+=1
            self._append({'action_id':pid,'proposal_sha256':proposal_sha256,
                          'decision':'AUTHORIZED','reason':reason})
            try:
                if proposal['tool']=='read_public_dataset':
                    result=deepcopy(self._datasets[proposal['args']['dataset_id']])
                elif proposal['tool']=='publish_summary':
                    result={'channel':proposal['args']['channel'],
                            'body':proposal['args']['body']}
                    self._publications.append(deepcopy(result))
                else:
                    raise GuardError('Impossible unknown capability')
                self._append({'action_id':pid,'proposal_sha256':proposal_sha256,
                              'decision':'EXECUTED','result_sha256':sha(result)})
                return {'allowed':True,'result':result}
            except Exception:
                self._append({'action_id':pid,'proposal_sha256':proposal_sha256,
                              'decision':'EXECUTION_UNCERTAIN','reason':'Backend exception; side effects unconfirmed'})
                return {'allowed':False,'reason':'Backend exception; outcome uncertain'}

    def verify_ledger(self,records=None):
        """MAC chain verification under the *local host's* secret key.

        Does not verify the recorder saw every tool call; no immutable root.
        """
        with self._lock:
            records=self._events if records is None else records
            prev='0'*64
            for seq,e in enumerate(records,1):
                if not isinstance(e,dict) or set(e)!={'record','mac'}:return False
                rec=e['record']
                if rec.get('sequence')!=seq or rec.get('previous_mac')!=prev or rec.get('policy_sha256')!=self.policy_sha256:return False
                if not hmac.compare_digest(mac(self._key,rec),e['mac']):return False
                prev=e['mac']
            return True

    def evidence(self):
        with self._lock:
            return {'schema':'pcs-host-guard-demo-receipt-v0.4',
                    'policy_sha256':self.policy_sha256,
                    'audit_records':deepcopy(self._events),
                    'audit_chain_verified_inside_host':self.verify_ledger(),
                    'actions_authorized':self._accepted,
                    'publications':deepcopy(self._publications),
                    'limitations':['All effects are on a local in-memory synthetic backend; no network or real agent tools',
                                   'HMAC key is retained by this temporary host instance, not exported to the client',
                                   'The host can fabricate, suppress or omit records; root-of-trust, completeness and external authentication not established',
                                   'Guard must be the exclusive dispatcher in any real integration; not a general prompt-injection defense']}

def evaluate_demo_trace(data):
    from .engine import dup_reject
    if len(data)>2*1024*1024:raise GuardError('Agent trace exceeds 2 MiB')
    try:
        doc=json.loads(data,object_pairs_hook=dup_reject,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))
    except (ValueError,TypeError) as exc:raise GuardError('Malformed JSON: '+str(exc)[:100]) from exc
    if not isinstance(doc,dict) or doc.get('schema')!='pcs-agent-trace-v1' or set(doc)!={'schema','proposals','executed'}:
        raise GuardError('Expected strict pcs-agent-trace-v1 schema')
    proposals=doc['proposals']
    if not isinstance(proposals,list) or len(proposals)>256:raise GuardError('Invalid proposal list')
    runtime=GuardedDemoRuntime()
    results=[runtime.execute(p) for p in proposals]
    evidence=runtime.evidence()
    evidence['requests']=len(proposals)
    evidence['denied']=sum(not x['allowed'] for x in results)
    evidence['executions']=sum(x['allowed'] for x in results)
    evidence['reported_executions_ignored']='Uploaded executed entries were NOT trusted or executed; only proposals entered the guarded demo dispatcher.'
    evidence['policy_scope']='Host-owned exact synthetic publication and public-dataset reads'
    return evidence
