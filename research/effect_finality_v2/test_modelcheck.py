import unittest
from research.effect_finality_v2.modelcheck import run

class AbstractModelTests(unittest.TestCase):
    def test_exhaustive_declared_finite_model(self):
        outcome=run()
        self.assertTrue(outcome['safe'])
        self.assertEqual(131,outcome['states_explored'])
        self.assertEqual(161,outcome['transitions_explored'])

    def test_broken_idempotency_has_minimal_counterexample(self):
        bad=run(broken_idempotency=True)
        self.assertFalse(bad['safe'])
        self.assertEqual('duplicate effect for same permit',bad['reason'])
        self.assertEqual(('reserve first','issue a','deliver/retry a','deliver/retry a'),bad['trace'])

if __name__=='__main__': unittest.main()
