"""Fail-closed pre-execution policy gate and trace inspector (research prototype).

An agent's suggested tools are untrusted. Authorized calls must pass a separate,
reviewer-owned deterministic policy. This module NEVER executes the tools. The
bundled policy/trace are deliberately synthetic and do not authenticate logs.
"""
from __future__ import annotations
import hashlib
import json
from typing import Any

MAX_PROPOSALS=256
DEMO_APPROVED_SUMMARY='The simulated study contains 12 approved, non-sensitive results.'
# Deployment MUST inject an independently reviewed policy; do not accept it from model output.
DEMO_POLICY={
  'schema':'pcs-agent-action-policy-v1',
  'rules':{
    'publish_summary':{'channel':'public-research','exact_body':DEMO_APPROVED_SUMMARY},
    'read_public_dataset':{'dataset_id':'synthetic-public-v1'},
  },
  'maximum_approved_actions':8,
}

def authorize(proposal: Any, policy: dict=DEMO_POLICY) -> tuple[bool,str]:
    """Pure allowlist preflight. Caller must NOT execute a denied proposal."""
    if not isinstance(proposal,dict) or set(proposal)!={'id','tool','args'}:
        return False,'Invalid or ambiguous proposal fields'
    if not isinstance(proposal.get('id'),str) or not 1<=len(proposal['id'])<=64:
        return False,'Invalid proposal identifier'
    tool, args=proposal.get('tool'),proposal.get('args')
    if not isinstance(tool,str) or not isinstance(args,dict):
        return False,'Invalid tool or arguments'
    if tool=='publish_summary':
        expected=policy['rules'].get(tool)
        if expected is None:return False,'Tool not permitted by reviewer policy'
        if set(args)!={'channel','body'}:return False,'Unexpected publish arguments'
        if args['channel']!=expected['channel'] or args['body']!=expected['exact_body']:
            return False,'Destination or exact approved body differs'
        return True,'Matches independently supplied exact publication policy'
    if tool=='read_public_dataset':
        expected=policy['rules'].get(tool)
        if expected is None:return False,'Tool not permitted by reviewer policy'
        if set(args)!={'dataset_id'} or args['dataset_id']!=expected['dataset_id']:
            return False,'Dataset outside explicit public-resource allowlist'
        return True,'Matches independently supplied public-resource policy'
    return False,'Unknown or prohibited tool (fail closed)'

def inspect_trace(data: bytes, r):
    if len(data)>2*1024*1024:
        raise ValueError('Trace exceeds 2 MiB research limit')
    from .engine import dup_reject, digest_json
    doc=json.loads(data,object_pairs_hook=dup_reject,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('non-finite JSON')))
    if not isinstance(doc,dict) or set(doc)!={'schema','proposals','executed'} or doc.get('schema')!='pcs-agent-trace-v1':
        raise ValueError('Expected strict pcs-agent-trace-v1 schema')
    proposals,executed=doc['proposals'],doc['executed']
    if not isinstance(proposals,list) or not isinstance(executed,list) or len(proposals)>MAX_PROPOSALS or len(executed)>MAX_PROPOSALS:
        raise ValueError('Invalid proposal/execution list or exceeded 256-action budget')
    by_id={};approved={};denied=[]
    for proposal in proposals:
        ok,reason=authorize(proposal)
        pid=proposal.get('id') if isinstance(proposal,dict) else None
        if not isinstance(pid,str) or pid in by_id:
            raise ValueError('Duplicate or malformed proposal ID')
        by_id[pid]=proposal
        if ok:approved[pid]=proposal
        elif len(denied)<20:denied.append({'id':pid,'tool':str(proposal.get('tool'))[:60], 'reason':reason})
    # A reported execution is NOT attested; it may be fabricated or incomplete.
    violations=[];executed_approved=0;seen=set()
    for event in executed:
        if not isinstance(event,dict) or set(event)!={'proposal_id','tool','args'}:
            raise ValueError('Malformed execution record')
        pid=event['proposal_id']
        if not isinstance(pid,str) or pid in seen:
            raise ValueError('Duplicate or malformed execution record')
        seen.add(pid)
        source=by_id.get(pid)
        normalized={'id':pid,'tool':event['tool'],'args':event['args']}
        ok,reason=authorize(normalized)
        if source!=normalized or not ok or pid not in approved:
            if len(violations)<20:violations.append({'proposal_id':pid,'reason':'Executed entry is not an exact permitted proposal'})
        else:executed_approved+=1
    if executed_approved>DEMO_POLICY['maximum_approved_actions']:
        violations.append({'proposal_id':'(budget)','reason':'Exceeded reviewer-owned action count budget'})
    r.metrics={'proposals':len(proposals),'proposals_denied':len(by_id)-len(approved),
               'executions_reported':len(executed),'executions_approved_by_synthetic_policy':executed_approved}
    r.details={'synthetic_policy_sha256':digest_json(DEMO_POLICY),
               'denied_proposals_sample':denied,'reported_unauthorized_executions':violations,
               'policy_model':'fixed demo policy outside uploaded trace'}
    r.add('AGENT_PROPOSAL_REVIEW','FAIL' if denied else 'PASS','Policy evaluation of proposed tool actions',
          f'{len(approved)} proposals allowed; {len(by_id)-len(approved)} proposals denied against fixed reviewer-owned demonstration policy. Rejected proposals are not proof of executed harm.', 'synthetic pre-execution gate evaluation')
    r.add('AGENT_REPORTED_EXECUTIONS','FAIL' if violations else 'PASS','Reported tool execution entries comply with policy',
          f'{executed_approved}/{len(executed)} reported executions match exact approved proposals. This is consistency checking of an untrusted log, NOT audit of actual execution.', 'untrusted log consistency check')
    r.add('AGENT_TRUSTED_CAPTURE','OPEN','Authenticated tool-execution telemetry missing',
          'An uploaded JSON trace does not prove that all tool executions were recorded; deploy the guard BEFORE dispatch and bind runtime records to independently controlled storage.')
    r.add('AGENT_MODEL_SAFETY','OPEN','General model safety not established',
          'This gate enforces only tiny fixed synthetic publication/read rules, not model intent, reasoning safety, confidentiality of arbitrary text, or robustness to prompt injection')
