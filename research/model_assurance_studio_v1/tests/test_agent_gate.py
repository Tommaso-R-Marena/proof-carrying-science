"""No tool is ever executed during these tests: decisions only."""
import copy
import json
from pathlib import Path
import unittest
from studio.engine import analyze
from studio.agent_gate import authorize, DEMO_POLICY, DEMO_APPROVED_SUMMARY
from studio.verify_receipt import replay_verify
ROOT=Path(__file__).resolve().parents[1]

def statuses(r):return {c['id']:c['status'] for c in r['checks']}

class TestAgentGate(unittest.TestCase):
    def proposal(self,pid='t1',tool='publish_summary',args=None):
        return {'id':pid,'tool':tool,'args':args if args is not None else {
            'channel':'public-research','body':DEMO_APPROVED_SUMMARY}}
    def test_allowed_exact_body(self):
        ok,_=authorize(self.proposal());self.assertTrue(ok)
    def test_block_modified_body_even_if_plausible(self):
        p=self.proposal();p['args']['body']+=' EXFIL'
        self.assertFalse(authorize(p)[0])
    def test_block_malicious_tool(self):
        self.assertFalse(authorize(self.proposal(tool='shell',args={'command':'rm -rf /'}))[0])
    def test_block_nested_unexpected_args(self):
        p=self.proposal();p['args']['extra']={}
        self.assertFalse(authorize(p)[0])
    def test_block_unapproved_resource(self):
        self.assertFalse(authorize(self.proposal(tool='read_public_dataset',args={'dataset_id':'private-records'}))[0])
    def test_good_trace_still_not_safe(self):
        p=ROOT/'samples/demo_agent_compliant.agenttrace.json';raw=p.read_bytes()
        r=analyze(p.name,raw)
        self.assertEqual(statuses(r)['AGENT_PROPOSAL_REVIEW'],'PASS')
        self.assertEqual(statuses(r)['AGENT_REPORTED_EXECUTIONS'],'PASS')
        self.assertEqual(statuses(r)['AGENT_TRUSTED_CAPTURE'],'OPEN')
        self.assertEqual(r['decision'],'OPEN')
        self.assertTrue(replay_verify(r,raw)[0])
    def test_attack_trace_rejects_actions(self):
        p=ROOT/'samples/demo_agent_attack_blocked.agenttrace.json'
        r=analyze(p.name,p.read_bytes());ss=statuses(r)
        self.assertEqual(ss['AGENT_PROPOSAL_REVIEW'],'FAIL')
        self.assertEqual(ss['AGENT_REPORTED_EXECUTIONS'],'PASS')
        self.assertEqual(r['metrics']['proposals_denied'],2)
    def test_falsely_claimed_executed_tool_flagged(self):
        p=ROOT/'samples/demo_agent_unsafe_execution.agenttrace.json'
        r=analyze(p.name,p.read_bytes())
        self.assertEqual(statuses(r)['AGENT_REPORTED_EXECUTIONS'],'FAIL')
    def test_duplicate_keys_rejected(self):
        bad=b'{"schema":"pcs-agent-trace-v1","schema":"pcs-agent-trace-v1","proposals":[],"executed":[]}'
        r=analyze('bad.agenttrace.json',bad)
        self.assertEqual(statuses(r)['PARSE_FAILURE'],'FAIL')
    def test_untrusted_policy_cannot_override_demo_policy(self):
        bad={'schema':'pcs-agent-trace-v1','proposals':[self.proposal()], 'executed':[],
             'policy':{'allow_everything':True}}
        r=analyze('bad.agenttrace.json',json.dumps(bad).encode())
        self.assertEqual(statuses(r)['PARSE_FAILURE'],'FAIL')
    def test_unknown_executed_proposal_is_failure(self):
        trace={'schema':'pcs-agent-trace-v1','proposals':[],
               'executed':[{'proposal_id':'faked','tool':'publish_summary','args':{'channel':'public-research','body':DEMO_APPROVED_SUMMARY}}]}
        r=analyze('bad.agenttrace.json',json.dumps(trace).encode())
        self.assertEqual(statuses(r)['AGENT_REPORTED_EXECUTIONS'],'FAIL')
    def test_trace_must_not_attest_actual_execution(self):
        p=ROOT/'samples/demo_agent_compliant.agenttrace.json'
        r=analyze(p.name,p.read_bytes())
        self.assertFalse(r['pcs_claim_inventory']['trusted_authority'])
        self.assertTrue(any(c['status']=='OPEN' for c in r['checks']))

if __name__=='__main__':unittest.main()
