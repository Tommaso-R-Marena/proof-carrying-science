import unittest
from pcs.impact import impact_from_artifacts

class ImpactTests(unittest.TestCase):
    def test_transitive_impact(self):
        cert={'workflow':{'nodes':[{'id':'n1','inputs':['raw'],'outputs':['processed']},{'id':'n2','inputs':['processed'],'outputs':['result']}]},'evidence':[{'id':'e1','artifact_ids':['result'],'claim_ids':['c1']}],'claims':[{'id':'c1','required_evidence':['e1']}]}
        r=impact_from_artifacts(cert, {'raw'})
        self.assertEqual(r['affected_artifacts'], ['processed','raw','result'])
        self.assertEqual(r['affected_claims'], ['c1'])
        self.assertEqual(r['affected_evidence'], ['e1'])
