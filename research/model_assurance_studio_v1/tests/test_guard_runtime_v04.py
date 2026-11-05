import copy
import json
import threading
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from studio.agent_gate import DEMO_POLICY,DEMO_APPROVED_SUMMARY
from studio.guard_runtime import GuardedDemoRuntime,GuardError,evaluate_demo_trace
from studio.server import app

ROOT=Path(__file__).resolve().parents[1]
def proposal(id,tool='publish_summary',args=None):
    return {'id':id,'tool':tool,'args':{'channel':'public-research','body':DEMO_APPROVED_SUMMARY} if args is None else args}

class GuardTests(unittest.TestCase):
    def test_actual_in_memory_publication(self):
        rt=GuardedDemoRuntime()
        self.assertTrue(rt.execute(proposal('1'))['allowed'])
        ev=rt.evidence()
        self.assertEqual(len(ev['publications']),1)
        self.assertEqual([x['record']['decision'] for x in ev['audit_records']],['AUTHORIZED','EXECUTED'])
        self.assertTrue(rt.verify_ledger())
    def test_denied_attempt_is_not_published(self):
        rt=GuardedDemoRuntime()
        self.assertFalse(rt.execute(proposal('b','publish_summary',{'channel':'public-research','body':'secret'}))['allowed'])
        self.assertEqual(rt.evidence()['publications'],[])
        self.assertEqual(rt.evidence()['audit_records'][0]['record']['decision'],'DENY')
    def test_unknown_command_denied(self):
        rt=GuardedDemoRuntime()
        self.assertFalse(rt.execute(proposal('evil','shell',{'command':'rm -rf /'}))['allowed'])
        self.assertEqual(rt.evidence()['publications'],[])
    def test_unapproved_dataset_denied(self):
        rt=GuardedDemoRuntime()
        self.assertFalse(rt.execute(proposal('x','read_public_dataset',{'dataset_id':'private-patient'}))['allowed'])
    def test_approved_synthetic_read(self):
        rt=GuardedDemoRuntime()
        self.assertEqual(rt.execute(proposal('x','read_public_dataset',{'dataset_id':'synthetic-public-v1'}))['result']['approved_result_count'],12)
    def test_budget_before_effect(self):
        rt=GuardedDemoRuntime(policy=DEMO_POLICY|{'maximum_approved_actions':1})
        self.assertTrue(rt.execute(proposal('a'))['allowed'])
        self.assertFalse(rt.execute(proposal('b'))['allowed'])
        self.assertEqual(len(rt.evidence()['publications']),1)
    def test_duplicate_id_denied(self):
        rt=GuardedDemoRuntime()
        self.assertTrue(rt.execute(proposal('a'))['allowed'])
        self.assertFalse(rt.execute(proposal('a'))['allowed'])
        self.assertEqual(len(rt.evidence()['publications']),1)
    def test_duplicate_denied_then_approved_same_id_is_denied(self):
        rt=GuardedDemoRuntime()
        self.assertFalse(rt.execute(proposal('a','unknown',{}))['allowed'])
        self.assertFalse(rt.execute(proposal('a'))['allowed'])
    def test_hmac_chain_tampering_detected(self):
        rt=GuardedDemoRuntime(key=b'q'*32)
        rt.execute(proposal('a'))
        altered=copy.deepcopy(rt.evidence()['audit_records'])
        altered[1]['record']['decision']='DENY'
        self.assertFalse(rt.verify_ledger(altered))
        self.assertTrue(rt.verify_ledger())
    def test_chain_reorder_detected(self):
        rt=GuardedDemoRuntime()
        rt.execute(proposal('a'));rt.execute(proposal('b'))
        ev=rt.evidence()['audit_records']
        self.assertFalse(rt.verify_ledger(ev[::-1]))
        self.assertFalse(rt.verify_ledger(ev[1:]))
    def test_model_cannot_change_host_policy(self):
        rt=GuardedDemoRuntime()
        attack=proposal('a');attack['policy']={'rules':{'shell':{}}}
        self.assertFalse(rt.execute(attack)['allowed'])
        self.assertEqual(rt.evidence()['publications'],[])
    def test_concurrent_budget_reservation(self):
        rt=GuardedDemoRuntime(policy=DEMO_POLICY|{'maximum_approved_actions':3})
        threads=[threading.Thread(target=lambda j=j: rt.execute(proposal(str(j)))) for j in range(24)]
        for t in threads:t.start()
        for t in threads:t.join()
        self.assertEqual(len(rt.evidence()['publications']),3)
        self.assertTrue(rt.verify_ledger())
    def test_malformed_policy_rejected(self):
        with self.assertRaises(GuardError):GuardedDemoRuntime(policy={'schema':'nonsense'})
    def test_invalid_audit_key_rejected(self):
        with self.assertRaises(GuardError):GuardedDemoRuntime(key=b'short')
    def test_example_trace_run_ignores_claimed_execution(self):
        data=(ROOT/'samples/demo_agent_attack_blocked.agenttrace.json').read_bytes()
        ev=evaluate_demo_trace(data)
        self.assertGreater(ev['denied'],0)
        self.assertTrue(ev['audit_chain_verified_inside_host'])
    def test_api_endpoint_guards_real_synthetic_actions(self):
        cli=TestClient(app)
        doc={'schema':'pcs-agent-trace-v1','proposals':[proposal('okay'),proposal('bad','shell',{'cmd':'danger'})],
             'executed':[{'proposal_id':'bad','tool':'shell','args':{'cmd':'danger'}}]}
        res=cli.post('/api/guarded-demo',content=json.dumps(doc).encode())
        self.assertEqual(res.status_code,200)
        self.assertEqual(res.json()['executions'],1)
        self.assertEqual(res.json()['denied'],1)
        self.assertEqual(len(res.json()['publications']),1)
    def test_duplicate_json_key_rejected(self):
        res=TestClient(app).post('/api/guarded-demo',content=b'{"schema":"pcs-agent-trace-v1","proposals":[],"proposals":[],"executed":[]}')
        self.assertEqual(res.status_code,400)
    def test_blank_proposal_denied(self):
        rt=GuardedDemoRuntime()
        self.assertFalse(rt.execute(None)['allowed'])
        self.assertTrue(rt.verify_ledger())

if __name__=='__main__':unittest.main()
