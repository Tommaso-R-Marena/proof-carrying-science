import unittest
from pcs.checks.chemistry import parse_formula, reaction_balanced

class ChemistryTests(unittest.TestCase):
    def test_formula(self):
        self.assertEqual(dict(parse_formula('C6H12O6')), {'C':6,'H':12,'O':6})

    def test_balanced(self):
        ok, _ = reaction_balanced([{'formula':'H2','coefficient':2},{'formula':'O2','coefficient':1}],[{'formula':'H2O','coefficient':2}])
        self.assertTrue(ok)

    def test_unbalanced(self):
        ok, detail = reaction_balanced([{'formula':'H2','coefficient':1},{'formula':'O2','coefficient':1}],[{'formula':'H2O','coefficient':1}])
        self.assertFalse(ok); self.assertIn('O', detail['delta_product_minus_reactant'])
