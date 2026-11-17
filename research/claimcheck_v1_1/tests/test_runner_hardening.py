"""Hardening of the stand-alone kernel runner after the independent security review of 2026-11-17.

No Lean needed: stand-in `lean` programs record whether and how they were started.  The same file
under the real kernel is exercised by check_live_v11.  Findings and reproductions:
docs/integration/claimcheck/SECURITY_REVIEW_C3_D4.md.
"""
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from research.claimcheck_v1_1 import claimcheck_kernel_runner as runner
from research.claimcheck_v1_1.runner_negative_controls import MARKER

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUNNER = HERE.parent / "claimcheck_kernel_runner.py"
CHECKER = (ROOT / "research/claimcheck_v1/formal/ClaimCheck.lean").read_text(encoding="utf-8")
GENUINE = sorted((ROOT / "research/claimcheck_v1/benchmark/results/bundles").glob("*/obligations/*.lean"))[0].read_text(encoding="utf-8")
BANNER = "Lean (version 4.28.0, x86_64-unknown-linux-gnu, commit 0123456789abcdef, Release)"


def standin(path: Path, record: Path, banner=BANNER):
    """A stand-in `lean`: records argv[0], its arguments and directory, prints the banner for --version, rejects proofs."""
    path.write_text(f"#!{sys.executable}\nimport json, os, sys\n"
                    f"open({str(record)!r}, 'a').write(json.dumps([sys.argv[0], sys.argv[1:], os.getcwd()]) + '\\n')\n"
                    f"if sys.argv[1:] == ['--version']:\n    print({banner!r})\nelse:\n    sys.exit(1)\n")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def calls(record: Path):
    return [json.loads(line) for line in record.read_text().splitlines()] if record.exists() else []


def runner_proc(args, cwd, path_env):
    env = {**os.environ, "PATH": path_env}
    env.pop("PCS_CLAIMCHECK_LEAN", None)
    return subprocess.run([sys.executable, str(RUNNER), *args], cwd=cwd, env=env, capture_output=True, text=True)


def _tail():
    return GENUINE.split(MARKER)[1]


class Statements(unittest.TestCase):
    def test_a_genuine_claim_has_its_settings_and_no_flag(self):
        data, statements, outcomes = runner.parse_tail_claims(_tail())
        self.assertEqual(len(statements), len(outcomes))
        first = statements[0]
        self.assertEqual(first["settings_the_page_never_writes"], [])
        self.assertEqual(first["settings"]["na_tokens"], ["", "NA"])
        self.assertEqual(first["settings"]["scale"], "1")
        self.assertEqual(set(first["settings"]), {"column", "filter", "stat", "na_tokens", "scale", "reported"})
        self.assertEqual(runner.parse_tail(_tail()), (data, outcomes), "parse_tail keeps its result")

    def test_settings_that_can_force_a_verdict_are_flagged(self):
        tail = _tail()
        cases = {
            "scale": tail.replace("scale := ((1 : Rat) / 1)", "scale := ((4571 : Rat) / 4247)", 1),
            "missing-value tokens": tail.replace('naTokens := [b "", b "NA"]', 'naTokens := [b "", b "NA", b "11"]', 1),
            "zero with a positive exponent": _replace_reported(tail, "0e400"),
            "not a decimal literal": _replace_reported(tail, "1.5 mm"),
        }
        for words, altered in cases.items():
            _, statements, _ = runner.parse_tail_claims(altered)
            notes = " ".join(statements[0]["settings_the_page_never_writes"])
            self.assertIn(words, notes, words)

    def test_unit_ratios_from_the_fixed_table_are_not_flagged(self):
        for scale in ("((100 : Rat) / 1)", "((1 : Rat) / 1000)", "((3600 : Rat) / 1)", "((1 : Rat) / 60)"):
            _, statements, _ = runner.parse_tail_claims(_tail().replace("scale := ((1 : Rat) / 1)", "scale := " + scale, 1))
            self.assertEqual(statements[0]["settings_the_page_never_writes"], [], scale)

    def test_number_literals_above_the_resource_limit_are_refused_not_crashed(self):
        big = "1" + "0" * 5000
        for altered in (_tail().replace("scale := ((1 : Rat) / 1)", f"scale := (({big} : Rat) / 3)", 1),
                        _tail().replace(", " + _tail().split("⟩")[0].rsplit(", ", 1)[1] + "⟩", ", " + big + "⟩", 1)):
            with self.assertRaises(runner.NotCanonical):
                runner.parse_tail_claims(altered)


def _replace_reported(tail: str, value: str) -> str:
    start = tail.index("reported := ")
    end = tail.index(" }", start)
    return tail[:start] + f'reported := b "{value}"' + tail[end:]


class LeanLookup(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.downloads, self.real = base / "downloads", base / "toolchain" / "bin"
        self.downloads.mkdir()
        self.real.mkdir(parents=True)
        (self.downloads / "proof.lean").write_text(GENUINE, encoding="utf-8")
        self.planted, self.honest = base / "planted.log", base / "honest.log"
        standin(self.downloads / "lean", self.planted, banner=BANNER.replace("Release", "Release (planted)"))
        standin(self.real / "lean", self.honest)

    @unittest.skipUnless(os.name == "posix", "POSIX PATH semantics")
    def test_a_lean_planted_in_the_current_directory_never_runs(self):
        proc = runner_proc(["proof.lean"], self.downloads, ":" + str(self.real) + ":/usr/bin:/bin")
        report = json.loads(proc.stdout)
        self.assertEqual(calls(self.planted), [], "the planted lean must not run")
        self.assertEqual(report["lean_executable"], str(self.real / "lean"))
        self.assertEqual(len(calls(self.honest)), 2, "version check and proof run, both by the same binary")
        self.assertFalse(report["accepted"])

    @unittest.skipUnless(os.name == "posix", "POSIX PATH semantics")
    def test_a_lean_next_to_the_proof_is_refused_even_from_an_absolute_path_entry(self):
        proc = runner_proc(["proof.lean"], self.downloads, str(self.downloads) + ":" + str(self.real) + ":/usr/bin:/bin")
        report = json.loads(proc.stdout)
        self.assertEqual(calls(self.planted), [])
        self.assertIn("refusing the lean found in the current directory or next to the proof file", report["why_not"])
        self.assertEqual(proc.returncode, 2)

    def test_an_explicit_relative_lean_is_made_absolute_once_and_used_for_both_calls(self):
        user = Path(self.tmp.name) / "user"
        (user / "bin").mkdir(parents=True)
        record = Path(self.tmp.name) / "relative.log"
        standin(user / "bin" / "lean", record)
        (user / "proof.lean").write_text(GENUINE, encoding="utf-8")
        proc = runner_proc(["proof.lean", "--lean", "bin/lean"], user, "/usr/bin:/bin")
        report = json.loads(proc.stdout)                         # a report, not a crash
        made = [c[0] for c in calls(record)]
        self.assertEqual(made, [str(user / "bin" / "lean")] * 2)
        self.assertEqual(report["lean_executable"], str(user / "bin" / "lean"))
        self.assertEqual(report["lean_found"], "given explicitly")
        self.assertIn("Lean rejected the file", report["why_not"])


class FailClosed(unittest.TestCase):
    def test_a_runner_error_is_a_refusal_with_a_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run([sys.executable, str(RUNNER), tmp], capture_output=True, text=True)   # a directory
            report = json.loads(proc.stdout)
            self.assertFalse(report["accepted"])
            self.assertIn("the runner could not complete", report["why_not"])
            self.assertEqual(proc.returncode, 1)

    def test_out_is_replaced_even_when_the_file_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            proof, out = Path(tmp) / "p.lean", Path(tmp) / "kernel-run.json"
            proof.write_text(CHECKER + MARKER + _tail().replace("scale := ((1 : Rat) / 1)", "scale := ((1" + "0" * 5000 + " : Rat) / 3)", 1),
                             encoding="utf-8")
            out.write_text('{"accepted": true, "note": "stale"}\n')
            proc = subprocess.run([sys.executable, str(RUNNER), str(proof), "--out", str(out)], capture_output=True, text=True)
            written = json.loads(out.read_text())
            self.assertFalse(written["accepted"])
            self.assertIn("resource limit", written["why_not"])
            self.assertEqual(json.loads(proc.stdout), written)
            self.assertFalse((Path(tmp) / "kernel-run.json.partial").exists())

    @unittest.skipUnless(os.name == "posix", "byte file names")
    def test_undecodable_and_direction_changing_file_names_are_neutralised(self):
        with tempfile.TemporaryDirectory() as tmp:
            for raw_name in (b"proof-\xff.lean", "proof-\u202egnp.lean".encode()):
                proof = os.path.join(os.fsencode(tmp), raw_name)
                with open(proof, "wb") as fh:
                    fh.write(b"not a proof file")
                out = os.path.join(tmp, "r.json")
                proc = subprocess.run([sys.executable, str(RUNNER), proof, "--out", out], capture_output=True)
                self.assertTrue(proc.stdout.isascii(), "the printed receipt is ASCII")
                report = json.loads(proc.stdout)
                self.assertIn("\ufffd", report["proof_file"])
                self.assertNotIn("\u202e", report["proof_file"])
                self.assertEqual(json.loads(Path(out).read_text(encoding="utf-8")), report)

    def test_an_overridden_checker_digest_is_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            proof = Path(tmp) / "p.lean"
            proof.write_text(GENUINE, encoding="utf-8")
            proc = subprocess.run([sys.executable, str(RUNNER), str(proof), "--checker-sha256", "0" * 64], capture_output=True, text=True)
            report = json.loads(proc.stdout)
            self.assertTrue(report["checker_pin_overridden"])
            proc = subprocess.run([sys.executable, str(RUNNER), str(proof), "--lean", "/nonexistent/lean"], capture_output=True, text=True)
            self.assertFalse(json.loads(proc.stdout)["checker_pin_overridden"])


if __name__ == "__main__":
    unittest.main()
