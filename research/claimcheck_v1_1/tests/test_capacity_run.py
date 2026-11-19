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


STOP = "Lean rejected the obligation: lean guard: memory limit of 7168 MB exceeded; process stopped"
KILLED = "Lean rejected the obligation: no output"
DEPTH = "Lean rejected the obligation: /tmp/pcs-claimcheck-x/Obligation.lean:9:2: error: maximum recursion depth has been reached"


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
        write(self.dir / "runs.jsonl", [syn(100, "median", True, digest="a"),
                                        syn(200, "median", False, digest="b", detail=STOP)])
        write(self.dir / "guard.jsonl", [{"event": "started", "obligation_sha256": "a"},
                                         {"event": "finished", "obligation_sha256": "a", "peak_rss_mb": 2048.0, "stopped_for_memory": False, "exit": 0},
                                         {"event": "finished", "obligation_sha256": "b", "peak_rss_mb": 7168.0, "stopped_for_memory": True, "exit": 137}])
        s = C.summarise(self.dir)["synthetic"]
        self.assertEqual(s["overall"]["max_peak_gb"], 7.0)
        self.assertEqual(s["overall"]["stopped_for_memory"], 1)
        self.assertEqual(s["candidate_supported_size_bytes"]["median"], 2000)
        self.assertFalse(s["overall"]["c7_limits_hold"])            # half the runs did not complete

    def test_a_process_the_system_killed_is_a_failure_recorded_as_such(self):
        write(self.dir / "runs.jsonl", [syn(100, "median", True, digest="a"), syn(200, "median", False, digest="k", detail=KILLED)])
        write(self.dir / "guard.jsonl", [{"event": "finished", "obligation_sha256": "a", "peak_rss_mb": 1024.0, "stopped_for_memory": False, "exit": 0},
                                         {"event": "finished", "obligation_sha256": "k", "peak_rss_mb": 7290.0, "stopped_for_memory": False, "exit": -9}])
        o = C.summarise(self.dir)["synthetic"]["overall"]
        self.assertEqual((o["runs"], o["completed"], o["killed_by_system"], o["stopped_for_memory"]), (2, 1, 1, 0))

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

    def test_one_obligation_in_two_runs_keeps_each_runs_own_outcome(self):
        # An original and its planted copy share an unchanged claim: the guard stopped it once and the
        # operating system killed it once.  Each run keeps its own label, and its own peak.
        dev = lambda doc, detail: {"phase": "development", "document": doc, "statistic": "median", "table_bytes": 26444, "seconds": 90.0,
                                   "kernel_accepted": False, "detail": detail, "obligation_sha256": "shared"}
        write(self.dir / "runs.jsonl", [dev("p:original", STOP), dev("p:mutated", KILLED), dev("q:original", DEPTH)])
        write(self.dir / "guard.jsonl", [
            {"event": "finished", "obligation_sha256": "shared", "peak_rss_mb": 7171.0, "stopped_for_memory": True, "exit": 137},
            {"event": "finished", "obligation_sha256": "shared", "peak_rss_mb": 6836.5, "stopped_for_memory": False, "exit": -9}])
        runs = C._documented(self.dir)
        self.assertEqual([r["outcome"] for r in runs],
                         ["memory guard stop", "killed by the operating system", "kernel rejection: Lean recursion-depth limit"])
        self.assertEqual([r["peak_gb"] for r in runs[:2]], [round(7171.0 / 1024, 2), round(6836.5 / 1024, 2)])
        o = C.summarise(self.dir)["development"]["overall"]
        self.assertEqual((o["stopped_for_memory"], o["killed_by_system"], o["resource_unknown"], o["completed"]), (1, 1, 2, 0))

    def test_no_output_without_a_system_kill_is_not_called_one(self):
        write(self.dir / "runs.jsonl", [syn(100, "mean", False, digest="n", detail=KILLED)])
        write(self.dir / "guard.jsonl", [{"event": "finished", "obligation_sha256": "n", "peak_rss_mb": 900.0, "stopped_for_memory": False, "exit": 1}])
        self.assertEqual(C._documented(self.dir)[0]["outcome"], "kernel rejection: other")

    def test_a_further_configuration_is_judged_by_the_rule_fixed_in_advance(self):
        write(self.dir / "runs.jsonl", [syn(100, "median", True, digest="a"), syn(200, "median", True, digest="b"),
                                        syn(300, "median", False, digest="c", detail=STOP)])
        write(self.dir / "guard.jsonl", [
            {"event": "finished", "obligation_sha256": "a", "peak_rss_mb": 1000.0, "exit": 0, "stopped_for_memory": False},
            {"event": "finished", "obligation_sha256": "b", "peak_rss_mb": 6500.0, "exit": 0, "stopped_for_memory": False},
            {"event": "finished", "obligation_sha256": "c", "peak_rss_mb": 7172.0, "exit": 137, "stopped_for_memory": True, "memory_limit_mb": 7168}])
        self.assertEqual(sorted(C.targets_high_memory(self.dir)), ["b", "c"])           # documented peak above 5 GiB
        ph = self.dir / "safer_6gib"
        ph.mkdir()
        rerun = lambda d, ok, detail: {"phase": "safer_6gib", "rebuilt": True, "target_obligation_sha256": d, "obligation_sha256": d,
                                       "statistic": "median", "table_bytes": {"b": 4000, "c": 6000}[d], "rows": {"b": 200, "c": 300}[d],
                                       "documented_runs": [], "seconds": 50.0, "kernel_accepted": ok, "detail": detail}
        write(ph / "runs.jsonl", [rerun("b", False, STOP), rerun("c", False, STOP)])
        write(ph / "guard.jsonl", [
            {"event": "finished", "obligation_sha256": d, "peak_rss_mb": 6150.0, "exit": 137, "stopped_for_memory": True, "memory_limit_mb": 6144}
            for d in "bc"])
        gib = 1024 ** 3
        base = {"phase": "safer_6gib", "workers": 2, "memory_limit_mb": 6144, "limit_bytes": int(13.35 * gib), "sampled_max_usage_bytes": 12 * gib,
                "counters_before": {"oom_kill": 0}, "counters_after": {"oom_kill": 0}}
        write(ph / "phase.jsonl", [{**base, "sampled_max_working_set_bytes": int(11.9 * gib)}])
        sf = C.safety(self.dir, "safer_6gib")
        self.assertTrue(sf["worst_case_leaves_reserve"])           # 2 x (6144 + 8) MB + 128 MB = 12.14 GiB <= 12.35 GiB
        self.assertTrue(sf["safe_on_this_machine"])
        write(ph / "phase.jsonl", [{**base, "sampled_max_working_set_bytes": int(12.6 * gib)}])
        self.assertFalse(C.safety(self.dir, "safer_6gib")["safe_on_this_machine"])      # less than 1 GiB left
        write(ph / "phase.jsonl", [{**base, "sampled_max_working_set_bytes": int(11.9 * gib), "counters_after": {"oom_kill": 1}}])
        self.assertFalse(C.safety(self.dir, "safer_6gib")["no_system_kill"])
        # supported size: 200 rows (4000 B) was accepted at 7 GiB but stopped at 6 GiB; 100 rows keeps its documented result
        self.assertEqual(C.supported_sizes(self.dir)["median"], 4000)
        self.assertEqual(C.supported_sizes(self.dir, "safer_6gib")["median"], 2000)
        self.assertFalse(C.safety(self.dir, "safer_6gib") is None)

    def test_two_documented_configurations_never_fit_this_machine(self):
        # 2 x 7 GiB cannot leave the 1 GiB reserve under a 13.35 GiB limit, whatever the sample shows
        self.assertGreater(C.worst_case_gb(2, 7 * 1024, 8.0, 128.0), 13.35 - C.RESERVE_GB)
        self.assertLessEqual(C.worst_case_gb(1, 7 * 1024, 8.0, 128.0), 13.35 - C.RESERVE_GB)


if __name__ == "__main__":
    unittest.main()
