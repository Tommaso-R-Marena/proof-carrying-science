"""The per-process memory limit (prospective/lean_guard.py), with a SYNTHETIC stand-in for Lean,
through the frozen v1 kernel call: a stopped process fails closed, every run is logged, and a run
cut off by the frozen call's timeout does not leave Lean running without its guard."""
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from research.claimcheck_v1 import lean as v1lean
from research.claimcheck_v1_1.prospective import lean_guard as G

FAKE = r'''#!{python}
import sys, time
if sys.argv[1:] == ["--version"]:
    print("Lean (version 4.28.0, x86_64-unknown-linux-gnu, commit synthetic, Release)"); sys.exit(0)
src = open(sys.argv[1]).read()
mb = int(src.split("ALLOC_MB=")[1].split()[0])
blocks = []
for _ in range(mb // 10):
    blocks.append(bytearray(10 * 1024 * 1024)); time.sleep(0.02)
time.sleep(0.2)
print("'pcs_claim_0' depends on axioms: [propext]")
'''

SLEEPER = r'''#!{python}
import os, sys, time
if sys.argv[1:] == ["--version"]:
    print("Lean (version 4.28.0, x86_64-unknown-linux-gnu, commit synthetic, Release)"); sys.exit(0)
pidfile = open(sys.argv[1]).read().split("PIDFILE=")[1].split()[0]
with open(pidfile, "w") as fh:
    fh.write(str(os.getpid()))
time.sleep(60)
print("'pcs_claim_0' depends on axioms: [propext]")
'''


def running(pid: int) -> bool:
    """True while the process exists and is neither a zombie nor dead."""
    try:
        state = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0]
    except (FileNotFoundError, ProcessLookupError, IndexError):
        return False
    return state not in ("Z", "X", "x")


@unittest.skipUnless(os.path.isdir("/proc"), "Linux only")
class MemoryGuard(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        fake = self.tmp / "fake-lean"
        fake.write_text(FAKE.format(python=sys.executable), encoding="utf-8")
        fake.chmod(0o755)
        self.log = self.tmp / "guard.jsonl"
        self.exe = G.make_guarded_lean(self.tmp, str(fake), 150, self.log, poll_seconds=0.02)
        v1lean._VERSION_CACHE.clear()

    def check(self, mb):
        with mock.patch.dict(os.environ, {"PCS_CLAIMCHECK_LEAN": str(self.exe)}):
            return v1lean.check_source(f"ALLOC_MB={mb}\n", claims=1, timeout=60)

    def test_within_the_limit_the_frozen_call_accepts_and_the_peak_is_logged(self):
        res = self.check(30)
        self.assertTrue(res.accepted, res.detail)
        run = [r for r in G.finished_runs(self.log) if r["obligation_sha256"]][-1]
        self.assertFalse(run["stopped_for_memory"])
        self.assertGreaterEqual(run["peak_rss_mb"], 30)
        self.assertEqual(run["obligation_sha256"], res.source_sha256)        # joins the kernel record

    def test_over_the_limit_the_process_is_stopped_and_the_claim_fails_closed(self):
        res = self.check(600)
        self.assertFalse(res.accepted)
        self.assertIn("Lean rejected the obligation", res.detail)
        run = [r for r in G.finished_runs(self.log) if r["obligation_sha256"]][-1]
        self.assertTrue(run["stopped_for_memory"])
        self.assertEqual(run["exit"], 137)
        self.assertLess(run["peak_rss_mb"], 600)
        self.assertEqual(G.stopped_from_outside(self.log), [])

    def test_a_timeout_of_the_frozen_call_stops_lean_with_its_guard(self):
        d = self.tmp / "sleeper"
        d.mkdir()
        sleeper = d / "sleeping-lean"
        sleeper.write_text(SLEEPER.format(python=sys.executable), encoding="utf-8")
        sleeper.chmod(0o755)
        log = d / "guard.jsonl"
        exe = G.make_guarded_lean(d, str(sleeper), 150, log, poll_seconds=0.02)
        pidfile = d / "lean.pid"
        with mock.patch.dict(os.environ, {"PCS_CLAIMCHECK_LEAN": str(exe)}):
            res = v1lean.check_source(f"PIDFILE={pidfile}\n", claims=1, timeout=3)
        self.assertFalse(res.accepted)
        self.assertIn("timed out", res.detail)
        pid = int(pidfile.read_text())
        deadline = time.monotonic() + 10
        while running(pid) and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertFalse(running(pid), "Lean outlived its guard and kept running without a memory limit")
        self.assertEqual([r["obligation_sha256"] for r in G.stopped_from_outside(log)], [res.source_sha256])


if __name__ == "__main__":
    unittest.main()
