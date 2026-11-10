"""Source-witness independent regression and frozen Writ/13 fixture check."""
import json
import unittest
from research.writ_authority_v9.source_witness import (
    SourceWitnessError, commitment, reconstruct, same_witness
)

POLICY='78fde2f2c8ebe499d40e83fdd9efb2746edf3f656806190481e90f94c9f47cd4'
EXPECTED='35508ee5c4f886ef8a2154b81ce39a5318ec6d0334995d2dc1179087ac78eb8a'
DATA=json.dumps({'title':'Audited public report','risk':1,'approved':True}).encode()

class SourceWitnessTests(unittest.TestCase):
    def test_independent_runtime_manifest_fixture(self):
        specs={'report':(0,())}
        roots={'report':(DATA,0)}
        self.assertEqual(commitment(POLICY,specs,roots,{}),EXPECTED)
        self.assertTrue(same_witness(EXPECTED,POLICY,specs,roots,{}))
        self.assertFalse(same_witness(EXPECTED,POLICY,specs,
                         {'report':(DATA.replace(b'risk',b'RISK'),0)},{}))

    def test_declared_multisource_secret_cannot_launder_into_public(self):
        specs={'public':(0,()), 'secret':(2,()),
               'derived':(0,('public','secret'))}
        roots={'public':(b'public',0),'secret':(b'secret',2)}
        recipes={'derived':(('public','secret'),b'::')}
        m=reconstruct(POLICY,specs,roots,recipes)
        derived=next(r for r in m['resources'] if r['name']=='derived')
        self.assertEqual(derived['label'],2)
        self.assertEqual(derived['lineage'],['derived','public','secret'])
        first=commitment(POLICY,specs,roots,recipes)
        self.assertNotEqual(first,commitment(POLICY,specs,roots,
                              {'derived':(('public','secret'),b'--')}))
        self.assertNotEqual(first,commitment(POLICY,specs,
                              {'public':(b'public',1),'secret':(b'secret',2)},recipes))

    def test_missing_cycle_wrong_order_fail(self):
        with self.assertRaises(SourceWitnessError):
            reconstruct(POLICY,{'x':(0,('x',))},{},
                        {'x':(('x',),b':')})
        with self.assertRaises(SourceWitnessError):
            reconstruct(POLICY,{'a':(0,()), 'z':(0,('a',))},
                        {'a':(b'a',0)}, {'z':(('z',),b'')})

if __name__=='__main__':unittest.main()
