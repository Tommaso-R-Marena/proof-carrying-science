"""The stand-alone kernel runner refuses forged proof files before starting Lean, and accepts every
proof file the generator wrote (C3, authorised 2026-11-16).  No Lean needed: a stand-in `lean`
records whether it was started.  The same controls run against the real kernel in check_live_v11."""
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from research.claimcheck_v1_1 import claimcheck_kernel_runner as runner
from research.claimcheck_v1_1.runner_negative_controls import MARKER, altered_tails, shadowed_run_tail

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUNNER = HERE.parent / "claimcheck_kernel_runner.py"
CHECKER = (ROOT / "research/claimcheck_v1/formal/ClaimCheck.lean").read_text(encoding="utf-8")
OBLIGATIONS = sorted((ROOT / "research/claimcheck_v1/benchmark/results/bundles").glob("*/obligations/*.lean"))


def run_with_standin(text: str):
    """Run the runner with a stand-in `lean` that records being started and reports a wrong version."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        marker = tmp / "lean-was-started"
        fake = tmp / "lean"
        fake.write_text(f"#!{sys.executable}\nimport pathlib\npathlib.Path({str(marker)!r}).write_text('x')\nprint('Lean (version 0.0.0)')\n")
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
        proof = tmp / "p.lean"
        proof.write_text(text, encoding="utf-8")
        proc = subprocess.run([sys.executable, str(RUNNER), str(proof), "--lean", str(fake)], capture_output=True, text=True)
        return json.loads(proc.stdout), proc.returncode, marker.exists()


class StrictRunner(unittest.TestCase):
    def test_the_receipt_schema_is_v2(self):
        self.assertEqual(runner.SCHEMA, "pcs-claimcheck-kernel-run-v2")
        self.assertEqual(runner.REVIEWED_CHECKER_SHA256,
                         (ROOT / "research/claimcheck_v1/formal/ClaimCheck.lean.sha256").read_text().split()[0])

    def test_every_committed_obligation_file_is_in_canonical_form(self):
        self.assertGreaterEqual(len(OBLIGATIONS), 84)
        for path in OBLIGATIONS:
            head, tail = path.read_text(encoding="utf-8").split(MARKER)
            self.assertEqual(head, CHECKER, path)
            data, outcomes = runner.parse_tail(tail)
            self.assertEqual(len(outcomes), tail.count("#print axioms pcs_claim_"), path)

    def test_a_genuine_file_passes_the_grammar_and_reaches_lean(self):
        report, code, started = run_with_standin(OBLIGATIONS[0].read_text(encoding="utf-8"))
        self.assertTrue(started, "the stand-in lean must have been asked for its version")
        self.assertFalse(report["accepted"])
        self.assertEqual(code, 2)
        self.assertIn("Lean 4.28.0 is required", report["why_not"])
        self.assertTrue(report["generated_part_canonical"])

    def test_the_reported_forgery_is_refused_before_lean(self):
        head, tail = OBLIGATIONS[0].read_text(encoding="utf-8").split(MARKER)
        data, _ = runner.parse_tail(tail)
        report, code, started = run_with_standin(CHECKER + MARKER + shadowed_run_tail(data))
        self.assertFalse(report["accepted"])
        self.assertEqual(code, 1)
        self.assertFalse(started, "Lean must not be started for a forged file")
        self.assertIn("not in canonical form", report["why_not"])
        self.assertNotIn("theorems", [k for k, v in report.items() if v])

    def test_every_negative_control_is_refused_before_lean(self):
        for path in (OBLIGATIONS[0], OBLIGATIONS[-1]):
            head, tail = path.read_text(encoding="utf-8").split(MARKER)
            data, _ = runner.parse_tail(tail)
            for name, forged in altered_tails(tail, data).items():
                with self.subTest(file=path.name, control=name):
                    report, code, started = run_with_standin(CHECKER + MARKER + forged)
                    self.assertFalse(report["accepted"])
                    self.assertEqual(code, 1)
                    self.assertFalse(started)
                    self.assertIn("not in canonical form", report["why_not"])

    def test_size_limits_are_refused_with_their_own_reason(self):
        from research.claimcheck_v1 import lean as generator
        self.assertEqual(runner.MAX_DATA_BYTES, generator.MAX_DATA_BYTES, "the runner accepts exactly the generator's data sizes")
        head, tail = OBLIGATIONS[0].read_text(encoding="utf-8").split(MARKER)
        big = runner.MAX_DATA_BYTES + 1
        with self.assertRaisesRegex(runner.NotCanonical, "this runner accepts at most"):
            runner.parse_tail(f"open PCS.ClaimCheck\n\ndef pcs_src : Source := ⟨0x{'00' * big}, {big}⟩\n\n")
        start = tail.index("def pcs_c0 : Claim :=")
        claim = tail[start:tail.index("\n\n", start) + 2]
        many = tail[:start] + "".join(claim.replace("pcs_c0 ", f"pcs_c{i} ", 1) for i in range(runner.MAX_CLAIMS + 1))
        with self.assertRaisesRegex(runner.NotCanonical, "more than 256 claims"):
            runner.parse_tail(many)

    def test_receipts_say_what_they_do_not_establish(self):
        source = RUNNER.read_text(encoding="utf-8")
        self.assertIn("does not verify that the obligation faithfully represents a paper", source)
        self.assertIn('"does_not_establish"', source)
        self.assertNotIn("the printed number MATCHES", source)


if __name__ == "__main__":
    unittest.main()
