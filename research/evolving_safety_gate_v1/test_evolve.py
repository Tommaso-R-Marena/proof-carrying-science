"""Unit tests: formal gate + offline evolution (no model downloads)."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from research.evolving_safety_gate_v1.catalog import SEED_CANDIDATES, formal_admissible, mutate
from research.evolving_safety_gate_v1.evolve import run_evolution
from research.evolving_safety_gate_v1.fitness import score_candidate
from research.evolving_safety_gate_v1.formal_check import check_formal

EVIDENCE = Path(__file__).resolve().parents[1] / "assurance_mirage_v1" / "evidence"


class TestFormal(unittest.TestCase):
    def test_lean_admission_lattice(self):
        with tempfile.TemporaryDirectory() as td:
            m = check_formal(Path(td) / "formal")
            self.assertTrue(m["kernel_checked"])
            self.assertEqual(len(m["theorems"]), 12)
            for axs in m["axiom_closures"].values():
                self.assertTrue(set(axs) <= {"propext", "Quot.sound"})


class TestCatalog(unittest.TestCase):
    def test_negative_controls_not_admissible(self):
        self.assertFalse(formal_admissible("channel1Only"))
        self.assertFalse(formal_admissible("correctingGuard"))
        self.assertTrue(formal_admissible("jointDetectingGuard"))

    def test_mutations_stay_joint(self):
        parent = next(c for c in SEED_CANDIDATES if c.id == "joint-v1")
        kids = mutate(parent, 1)
        self.assertGreaterEqual(len(kids), 3)
        self.assertTrue(all(k.formal_class == "jointDetectingGuard" for k in kids))


class TestEvolution(unittest.TestCase):
    def test_offline_evolution_rejects_channel1_champion(self):
        if not (EVIDENCE / "qwen06b" / "summary.json").exists():
            self.skipTest("mirage evidence absent")
        with tempfile.TemporaryDirectory() as td:
            lineage = run_evolution(Path(td) / "evo", evidence_root=EVIDENCE, generations=3)
            self.assertTrue(lineage["champion_score"]["formal_admissible"])
            self.assertNotEqual(lineage["champion"]["formal_class"], "channel1Only")
            self.assertNotEqual(lineage["champion"]["formal_class"], "correctingGuard")
            self.assertGreater(lineage["champion_score"]["detect_rank"], 0)
            # Channel-1 seed must lose.
            c1 = score_candidate(SEED_CANDIDATES[0], EVIDENCE)
            self.assertLess(c1["fitness"], lineage["champion_score"]["fitness"])
            self.assertTrue((Path(td) / "evo" / "lineage.json").exists())


if __name__ == "__main__":
    unittest.main()
