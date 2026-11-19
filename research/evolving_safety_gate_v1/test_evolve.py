"""Unit tests: formal gate + offline evolution (no model downloads)."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from research.evolving_safety_gate_v1.catalog import (
    SEED_CANDIDATES,
    detector_for,
    formal_admissible,
    mutate,
)
from research.evolving_safety_gate_v1.evolve import run_evolution
from research.evolving_safety_gate_v1.fitness import score_candidate
from research.evolving_safety_gate_v1.formal_check import check_formal
from research.evolving_safety_gate_v1.hard_suite import build_hard_suite

EVIDENCE = Path(__file__).resolve().parents[1] / "assurance_mirage_v1" / "evidence"


class TestFormal(unittest.TestCase):
    def test_lean_admission_lattice(self):
        with tempfile.TemporaryDirectory() as td:
            m = check_formal(Path(td) / "formal")
            self.assertTrue(m["kernel_checked"])
            self.assertEqual(len(m["theorems"]), 17)
            for axs in m["axiom_closures"].values():
                self.assertTrue(set(axs) <= {"propext", "Quot.sound"})


class TestCatalog(unittest.TestCase):
    def test_negative_controls_not_admissible(self):
        self.assertFalse(formal_admissible("channel1Only"))
        self.assertFalse(formal_admissible("correctingGuard"))
        self.assertTrue(formal_admissible("jointDetectingGuard"))
        self.assertTrue(formal_admissible("ensembleProbe"))

    def test_mutations_can_promote_to_ensemble(self):
        parent = next(c for c in SEED_CANDIDATES if c.id == "joint-v1")
        kids = mutate(parent, 1)
        self.assertTrue(any(k.formal_class == "ensembleProbe" for k in kids))
        self.assertTrue(any(k.formal_class == "jointDetectingGuard" for k in kids))


class TestHardSuite(unittest.TestCase):
    def test_joint_misses_stealth_ensemble_catches(self):
        if not (EVIDENCE / "qwen06b" / "summary.json").exists():
            self.skipTest("mirage evidence absent")
        suite = build_hard_suite(EVIDENCE)
        stealth = [e for e in suite if e.get("stealth_mirage")]
        self.assertGreaterEqual(len(stealth), 5)
        joint = next(c for c in SEED_CANDIDATES if c.id == "joint-v1")
        ens = next(c for c in SEED_CANDIDATES if c.id == "ensemble-v1")
        jdet, edet = detector_for(joint), detector_for(ens)
        joint_hits = sum(1 for e in stealth if jdet(e))
        ens_hits = sum(1 for e in stealth if edet(e))
        self.assertLess(joint_hits, len(stealth))
        self.assertGreater(ens_hits, joint_hits)


class TestEvolution(unittest.TestCase):
    def test_offline_evolution_rejects_channel1_and_beats_joint_on_stealth(self):
        if not (EVIDENCE / "qwen06b" / "summary.json").exists():
            self.skipTest("mirage evidence absent")
        with tempfile.TemporaryDirectory() as td:
            lineage = run_evolution(Path(td) / "evo", evidence_root=EVIDENCE, generations=3)
            self.assertTrue(lineage["champion_score"]["formal_admissible"])
            self.assertNotEqual(lineage["champion"]["formal_class"], "channel1Only")
            self.assertNotEqual(lineage["champion"]["formal_class"], "correctingGuard")
            self.assertGreater(lineage["champion_score"]["detect_rank"], 0)
            c1 = score_candidate(SEED_CANDIDATES[0], EVIDENCE)
            self.assertLess(c1["fitness"], lineage["champion_score"]["fitness"])
            joint = score_candidate(
                next(c for c in SEED_CANDIDATES if c.id == "joint-v1"), EVIDENCE
            )
            # Champion should match or beat joint on stealth when suite is present.
            self.assertGreaterEqual(
                lineage["champion_score"].get("stealth_recall") or 0.0,
                joint.get("stealth_recall") or 0.0,
            )
            self.assertTrue((Path(td) / "evo" / "lineage.json").exists())
            self.assertTrue((Path(td) / "evo" / "hard_suite.json").exists())


if __name__ == "__main__":
    unittest.main()
