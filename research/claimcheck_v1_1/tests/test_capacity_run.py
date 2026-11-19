"""The capacity run's summary (prospective/capacity_run.py) on hand-written logs: no Lean is run."""
import json
import tempfile
import unittest
from pathlib import Path

from research.claimcheck_v1_1.prospective import capacity_run as C


def write(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def syn(rows, stat, ok, seconds=10.0, digest=None, detail=None):
    return {"phase": "synthetic", "key": f"synthetic:{rows}:{stat}", "statistic": stat, "rows": rows, "table_bytes": rows * 20,
            "seconds": seconds, "kernel_accepted": ok, "detail": detail or ("kernel accepted" if ok else "Lean rejected the obligation"),
            "obligation_sha256": digest or f"{stat}-{rows}"}


class Summary(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def test_the_supported_size_is_the_last_size_before_the_first_failure(self):
        write(self.dir / "runs.jsonl", [syn(100, "min", True), syn(200, "min", True), syn(300, "min", False), syn(400, "min", True),
                                        syn(100, "mean", True), syn(200, "mean", True, seconds=301.0)])
        write(self.dir / "guard.jsonl", [])
        s = C.summarise(self.dir)["synthetic"]["candidate_supported_size_bytes"]
        self.assertEqual(s["min"], 4000)          # 400 rows accepted again does not count: the boundary is the first failure
        self.assertEqual(s["mean"], 2000)         # 200 rows took longer than C7's 95th-percentile limit
        self.assertIsNone(s["median"])            # not measured

    def test_peak_memory_and_memory_stops_come_from_the_guard_log(self):
        write(self.dir / "runs.jsonl", [syn(100, "median", True, digest="a"), syn(200, "median", False, digest="b")])
        write(self.dir / "guard.jsonl", [{"event": "started", "obligation_sha256": "a"},
                                         {"event": "finished", "obligation_sha256": "a", "peak_rss_mb": 2048.0, "stopped_for_memory": False},
                                         {"event": "finished", "obligation_sha256": "b", "peak_rss_mb": 7168.0, "stopped_for_memory": True}])
        s = C.summarise(self.dir)["synthetic"]
        self.assertEqual(s["overall"]["max_peak_gb"], 7.0)
        self.assertEqual(s["overall"]["stopped_for_memory"], 1)
        self.assertEqual(s["candidate_supported_size_bytes"]["median"], 2000)
        self.assertFalse(s["overall"]["c7_limits_hold"])            # half the runs did not complete

    def test_c7_holds_only_when_every_limit_holds(self):
        write(self.dir / "runs.jsonl", [{**syn(100 + i, "count", True, seconds=5.0), "phase": "development", "document": "d:original"}
                                        for i in range(20)])
        write(self.dir / "guard.jsonl", [])
        dev = C.summarise(self.dir)["development"]["overall"]
        self.assertTrue(dev["c7_limits_hold"])
        self.assertEqual(dev["completed_share"], 1.0)


    def test_development_runs_are_split_by_the_candidate_supported_size(self):
        dev = lambda stat, size, ok: {"phase": "development", "document": "p:original", "statistic": stat, "table_bytes": size,
                                      "seconds": 5.0, "kernel_accepted": ok, "detail": "", "obligation_sha256": f"{stat}{size}"}
        write(self.dir / "runs.jsonl", [syn(100, "median", True), syn(200, "median", False), syn(100, "sd_sample", True),
                                        dev("median", 2000, True), dev("median", 3000, False), dev("sd_pop", 2000, True),
                                        dev("max", 2000, True), dev("max", 2500, True)])
        write(self.dir / "guard.jsonl", [])
        d = C.summarise(self.dir)["development"]
        # median: 2000 B supported; sd_pop takes sd_sample's 2000 B; max (not measured) takes the smallest, 2000 B
        self.assertEqual(d["within_candidate_supported_size"]["runs"], 3)
        self.assertEqual(d["outside_candidate_supported_size"]["runs"], 2)
        self.assertEqual(d["within_candidate_supported_size"]["completed_share"], 1.0)


if __name__ == "__main__":
    unittest.main()
