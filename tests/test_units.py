import unittest
from pcs.checks.units import units_compatible

class UnitTests(unittest.TestCase):
    def test_mass_concentration(self):
        ok, detail = units_compatible('mg/L','g/L')
        self.assertTrue(ok)
        self.assertAlmostEqual(detail['conversion_left_to_right'], 0.001)

    def test_incompatible(self):
        ok, _ = units_compatible('mg/L','L/h')
        self.assertFalse(ok)
