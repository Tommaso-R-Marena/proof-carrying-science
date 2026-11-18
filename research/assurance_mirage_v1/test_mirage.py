"""Unit tests that do not download weights or call models."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from research.assurance_mirage_v1.channels import (
    EpisodeResult,
    ProposalRecord,
    detect_raw_leak,
    detect_scope_escalation,
    mirage_gap,
    parse_proposal,
)
from research.assurance_mirage_v1.formal_check import check_formal
from research.assurance_mirage_v1.programs.scientific_store import ScientificStore
from research.assurance_mirage_v1.protocol import ADMITTED, APPROVED_SUMMARY, PRIVATE_MARKER, CASES


class TestChannels(unittest.TestCase):
    def test_parse_and_leak(self):
        action, note, malformed = parse_proposal(
            '{"action":"exfiltrate","note":"x"}'
        )
        self.assertEqual(action, "exfiltrate")
        self.assertFalse(malformed)
        self.assertTrue(detect_raw_leak(PRIVATE_MARKER + " trailing"))
        self.assertTrue(detect_scope_escalation("this empirically proves clinical safety"))

    def test_mirage_gap_counts(self):
        ep = EpisodeResult(
            case_id="x",
            family="direct",
            attack=True,
            prompt_arm="plain",
            tools=[("start", "load_evidence")] * 4,
            proposals=[
                ProposalRecord(
                    turn=0,
                    state="start",
                    admitted="load_evidence",
                    proposed="exfiltrate",
                    forbidden=True,
                    malformed=False,
                    note="n",
                    raw_text='{"action":"exfiltrate"}',
                )
            ],
            published=[APPROVED_SUMMARY],
            raw_leak=True,
        )
        gap = mirage_gap([ep])
        self.assertEqual(gap["guarded_complete"], 1)
        self.assertEqual(gap["mirage_episodes"], 1)
        self.assertTrue(gap["channel1_only_would_report_perfect_safety"])


class TestScientificStore(unittest.TestCase):
    def test_correcting_guard_path(self):
        with tempfile.TemporaryDirectory() as td:
            store = ScientificStore(Path(td) / "db.sqlite")
            pubs = []
            for _ in range(4):
                self.assertEqual(store.admitted(), ADMITTED[store.state])
                result = store.execute_admitted()
                self.assertTrue(result["ok"])
                if "published" in result:
                    pubs.append(result["published"])
            self.assertEqual(store.state, "done")
            self.assertEqual(pubs, [APPROVED_SUMMARY])
            self.assertFalse(store.private_exposed_in_publications())
            store.close()


class TestProtocol(unittest.TestCase):
    def test_case_census(self):
        self.assertEqual(len(CASES), 10)
        self.assertEqual(sum(1 for c in CASES if not c["attack"]), 2)
        ids = [c["id"] for c in CASES]
        self.assertEqual(len(ids), len(set(ids)))


class TestFormal(unittest.TestCase):
    def test_lean_theorems(self):
        with tempfile.TemporaryDirectory() as td:
            manifest = check_formal(Path(td) / "formal")
            self.assertTrue(manifest["kernel_checked"])
            self.assertEqual(len(manifest["theorems"]), 8)
            for axs in manifest["axiom_closures"].values():
                self.assertTrue(set(axs) <= {"propext", "Quot.sound"})


if __name__ == "__main__":
    unittest.main()
