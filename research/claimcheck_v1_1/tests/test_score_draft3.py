"""The draft-3 scorer (prospective/score.py) implements each written rule of PROTOCOL_DRAFT.md and
criteria.json, on synthetic per-number records only.  No prospective paper, label or outcome is
involved.  (Replaces the draft-2 tests: the rules changed, see AMENDMENTS_DRAFT_3.md.)"""
import copy
import inspect
import json
import unittest
from pathlib import Path

from research.claimcheck_v1_1 import verify as v11verify
from research.claimcheck_v1_1.prospective import score, stats

HERE = Path(__file__).resolve().parents[1] / "prospective"
CRITERIA = json.loads((HERE / "criteria.json").read_text(encoding="utf-8"))
PROTOCOL = (HERE / "PROTOCOL_DRAFT.md").read_text(encoding="utf-8")
MODELS = json.loads((HERE / "model_config.json").read_text(encoding="utf-8"))
MUTATE = (HERE.parents[1] / "claimcheck_v1" / "benchmark" / "mutate.py").read_text(encoding="utf-8")
PILOT = CRITERIA["levels"]["supervised_external_pilot"]


def rec(variant, cls, outcome, match=True, changed=False):
    return {"variant": variant, "cls": cls, "outcome": outcome, "reading_matches": match, "changed": changed}


def records(*, t=10, conf=4, n=6, a=0, f_nat=1, nat_flag=False, unsupported=0, misleading=0, planted=4, planted_flags=1,
            misleading_in_copy=0, unsupported_in_copy=0, changed_n=0, flag_changed_n=False):
    """One paper, one arm.  Original: t T numbers (conf confirmed, the rest sent to review), n N numbers
    (some confirmed or flagged by mistake), a A numbers, f_nat natural F numbers.  Copy: the first
    `planted` T numbers changed (planted errors; the first `planted_flags` of them flagged), optionally
    `changed_n` N numbers changed too, errors in the copy as asked."""
    r = []
    for j in range(t):
        r.append(rec("original", "T", "CONFIRMATION" if j < conf else "REQUIRE_HUMAN_REVIEW"))
    for j in range(n):
        r.append(rec("original", "N", "CONFIRMATION" if j < unsupported else "DISCREPANCY_FOR_REVIEW" if j < unsupported + misleading else "UNKNOWN"))
    r += [rec("original", "A", "NO_PROPOSAL") for _ in range(a)]
    r += [rec("original", "F", "DISCREPANCY_FOR_REVIEW" if nat_flag else "UNKNOWN") for _ in range(f_nat)]
    for j in range(t):
        changed = j < planted
        out = ("DISCREPANCY_FOR_REVIEW" if j < planted_flags else "UNKNOWN") if changed else "CONFIRMATION"
        r.append(rec("planted", "T", out, changed=changed))
    for j in range(n):
        changed = j < changed_n
        out = ("DISCREPANCY_FOR_REVIEW" if changed and flag_changed_n else "CONFIRMATION" if j < unsupported_in_copy
               else "DISCREPANCY_FOR_REVIEW" if j < unsupported_in_copy + misleading_in_copy else "UNKNOWN")
        r.append(rec("planted", "N", out, changed=changed))
    r += [rec("planted", "A", "NO_PROPOSAL") for _ in range(a)]
    r += [rec("planted", "F", "UNKNOWN") for _ in range(f_nat)]
    return r


def papers(per_context=(20, 20, 20), complete=None, special=None, **kw):
    """Synthetic papers in contexts A, B, C; ``special`` maps an index to other record arguments."""
    out, i = {}, 0
    for ctx, count in zip("ABC", per_context):
        for j in range(count):
            args = dict(kw, **(special or {}).get(i, {}))
            out[f"{ctx}{j:03d}"] = {"context": ctx, "order": f"{ctx}{j:03d}", "counts": score.paper_counts(records(**args)),
                                    "primary_complete": True if complete is None else i >= complete}
            i += 1
    return out


def run(design=60, criteria=CRITERIA, **kw):
    return score.evaluate(papers(**kw), criteria, design=design)


class TheWrittenRules(unittest.TestCase):
    def test_a_clean_sixty_paper_run_meets_c1_to_c3_and_may_show_flags(self):
        r = run()
        c = r["criteria"]
        for k in ("C1_unsupported_confirmations", "C2_misleading_refutations", "C3_useful_coverage"):
            self.assertTrue(c[k]["met"], (k, c[k]))
        self.assertEqual(c["pilot_scope_if_C4_to_C10_are_met"]["discrepancy_flags_shown_to"], "pilot users, as discrepancies for review")
        self.assertFalse(c["D1_discrepancy_detection"]["may_be_described_as_finding_errors"])        # owner has set no level
        self.assertTrue(c["pilot_scope_if_C4_to_C10_are_met"]["every_screen_must_say_that_no_flag_carries_no_information"])

    def test_per_context_minimum_without_topping_up(self):
        s = score.select_primary(papers(per_context=(21, 20, 19)), CRITERIA, 60)
        self.assertFalse(s["evaluable"])
        self.assertTrue(any("shortfall" in x and "C" in x for x in s["reasons"]))
        s = score.select_primary(papers(per_context=(40, 20)), CRITERIA, 60)
        self.assertFalse(s["evaluable"])                                      # two contexts are not three

    def test_the_120_paper_design_and_its_fallback(self):
        s = score.select_primary(papers(per_context=(40, 40, 40)), CRITERIA, 120)
        self.assertEqual((s["design_used"], len(s["primary"]), s["fallback"]), (120, 120, False))
        s = score.select_primary(papers(per_context=(40, 40, 30)), CRITERIA, 120)
        self.assertEqual((s["design_used"], len(s["primary"]), s["fallback"]), (60, 60, True))
        self.assertTrue(s["evaluable"])
        self.assertEqual([p for p in s["primary"] if p.startswith("C")], [f"C{j:03d}" for j in range(20)])   # hash order
        self.assertEqual(len(s["secondary_all_eligible"]), 110)
        self.assertFalse(score.select_primary(papers(per_context=(40, 40, 19)), CRITERIA, 120)["evaluable"])

    def test_the_90_percent_primary_complete_rule(self):
        self.assertTrue(score.select_primary(papers(complete=6), CRITERIA, 60)["evaluable"])          # 54 of 60
        s = score.select_primary(papers(complete=7), CRITERIA, 60)                                    # 53 of 60
        self.assertFalse(s["evaluable"])
        self.assertTrue(any("primary-complete" in x for x in s["reasons"]))

    def test_scopes_c1_on_originals_c2_on_both_copies(self):
        c = run(special={0: {"unsupported_in_copy": 2}})["criteria"]           # wrong confirmations in a copy only
        self.assertTrue(c["C1_unsupported_confirmations"]["met"])
        self.assertEqual(c["C1_unsupported_confirmations"]["confirmations"], 240)
        c = run(special={0: {"misleading_in_copy": 1}})["criteria"]            # one misleading flag in a copy
        self.assertFalse(c["C2_misleading_refutations"]["b_per_paper"]["met"])
        self.assertIsNone(c["pilot_scope_if_C4_to_C10_are_met"]["discrepancy_flags_shown_to"])

    def test_labels_of_the_planted_copy_come_from_the_original(self):
        self.assertEqual(score.copy_class("T", True), ("F", True))
        for cls in ("N", "A", "F"):
            self.assertEqual(score.copy_class(cls, True), (cls, False))
        c = score.paper_counts(records(changed_n=1, flag_changed_n=True))["planted"]
        self.assertEqual(c["false_planted_total"], 4)                         # the changed N number is not a planted error
        self.assertEqual(c["misleading_refutation"], 1)                       # and a flag on it is misleading

    def test_c2c_uses_the_clustered_bound(self):
        five_in_one = {0: {"planted_flags": 4, "nat_flag": True}}             # 4 planted + 1 natural flag, all in one paper
        c = run(planted_flags=0, special=five_in_one)["criteria"]["C2_misleading_refutations"]
        self.assertEqual(c["c_among_flags"]["flags"], 5)
        self.assertLessEqual(c["c_among_flags"]["bound_ignoring_clustering"], 0.5)     # draft 2's scorer would pass it
        self.assertFalse(c["c_among_flags"]["met"])
        spread = {i: {"planted_flags": 1} for i in range(5)}
        self.assertTrue(run(planted_flags=0, special=spread)["criteria"]["C2_misleading_refutations"]["c_among_flags"]["met"])

    def test_c2c_not_evaluable_gives_a_confirmation_only_pilot(self):
        c = run(planted_flags=0, special={i: {"planted_flags": 1} for i in range(4)})["criteria"]
        k = c["C2_misleading_refutations"]
        self.assertFalse(k["c_among_flags"]["evaluable"])
        self.assertFalse(k["met"])
        self.assertTrue(k["met_for_a_confirmation_only_pilot"])
        self.assertEqual(c["pilot_scope_if_C4_to_C10_are_met"]["discrepancy_flags_shown_to"], "the supervising PCS reviewer only")

    def test_ambiguous_share_counts_t_f_and_a_numbers_of_the_originals(self):
        ok = run(a=2)["criteria"]                                              # 2 / (10 + 1 + 2) = 15 %
        self.assertTrue(ok["C1_unsupported_confirmations"]["evaluable"])
        bad = run(a=3)["criteria"]                                             # 3 / 14 = 21 %; draft 2's denominator gave 3 / 20
        self.assertFalse(bad["sample_evaluable"])
        for k in ("C1_unsupported_confirmations", "C2_misleading_refutations", "C3_useful_coverage"):
            self.assertFalse(bad[k]["met"], k)

    def test_d1_uses_planted_errors_only(self):
        c = run(planted_flags=0, nat_flag=True)["criteria"]["D1_discrepancy_detection"]    # every natural F flagged, no planted one
        self.assertEqual(c["flag_recall_planted"], 0.0)
        self.assertEqual(c["flag_recall_natural_reported"], 1.0)
        self.assertFalse(c["necessary_condition_met"])
        crit = copy.deepcopy(CRITERIA)
        crit["levels"]["supervised_external_pilot"]["criteria"]["D1_discrepancy_detection"]["wording_rule"][
            "flag_recall_lower_bound_needed_to_describe_the_tool_as_finding_errors"] = 0.2
        c = run(criteria=crit, planted_flags=3)["criteria"]                   # 3 of 4 planted errors flagged
        self.assertTrue(c["D1_discrepancy_detection"]["necessary_condition_met"])
        self.assertTrue(c["pilot_scope_if_C4_to_C10_are_met"]["may_be_described_as_finding_errors"])

    def test_too_few_confirmations(self):
        c = run(conf=2)["criteria"]                                            # 120 < 150
        self.assertFalse(c["C1_unsupported_confirmations"]["evaluable"])

    def test_one_unsupported_confirmation_and_cluster_size(self):
        # protocol 10: about four confirmations per paper, about 150 in all: one unsupported fails C1
        special = {i: {"conf": 0} for i in range(38, 60)}
        special[37] = {"conf": 4, "unsupported": 1}
        r = run(special=special)
        self.assertEqual(r["metrics"]["C1_unsupported_among_confirmations"]["opportunities"], 153)
        self.assertFalse(r["criteria"]["C1_unsupported_confirmations"]["met"])
        # the same count spread three per paper passes
        special = {i: {"conf": 0} for i in range(51, 60)}
        special[50] = {"conf": 3, "unsupported": 1}
        r = run(conf=3, special=special)
        self.assertTrue(r["criteria"]["C1_unsupported_confirmations"]["met"], r["criteria"]["C1_unsupported_confirmations"])

    def test_c4_replay_rule_and_shards(self):
        shards = score.replay_shards([f"p{i}" for i in range(120)], 12)
        self.assertEqual(sorted(len(s) for s in shards), [10] * 12)
        self.assertEqual(shards, score.replay_shards([f"p{i}" for i in reversed(range(120))], 12))       # fixed order
        self.assertTrue(score.judge_c4({"a": "replayed", "b": "replayed"}, CRITERIA)["met"])
        r = score.judge_c4({"a": "replayed", "b": "infrastructure_failure"}, CRITERIA)
        self.assertEqual((r["met"], r["evaluable"], r["rerun_required"]), (False, False, ["b"]))
        r = score.judge_c4({"a": "replayed", "b": "mismatch"}, CRITERIA)
        self.assertEqual((r["met"], r["evaluable"], r["failed"]), (False, True, ["b"]))

    def test_c7_within_the_supported_size_of_each_statistic(self):
        sizes = PILOT["criteria"]["C7_computation"]["supported_size_bytes"]
        run_ = lambda stat, b, s=10.0, gb=2.0, ok=True: {"statistic": stat, "table_bytes": b, "seconds": s, "peak_gb": gb, "kernel_accepted": ok}
        runs = [run_("median", 8000)] * 19 + [run_("median", 16000, s=900, ok=False)] * 5 + [run_("count", 50000)]
        r = score.judge_c7(runs, CRITERIA)
        self.assertEqual((r["runs_within_supported_size"], r["runs_outside_supported_size"]), (20, 5))
        self.assertTrue(r["met"])
        self.assertLess(r["completed_share_all_runs_reported"], 0.95)
        r = score.judge_c7([run_("median", 8000)] * 19 + [run_("mean", 8000, s=900, ok=False)], CRITERIA)
        self.assertTrue(r["met"])                                              # 19 of 20 complete: 95 %, and p95 is the 19th value
        r = score.judge_c7([run_("median", 8000)] * 18 + [run_("mean", 8000, s=900, ok=False)] * 2, CRITERIA)
        self.assertFalse(r["met"])                                             # 90 % complete, p95 900 s
        self.assertEqual(r["p95_seconds"], 900)
        self.assertEqual(score.supported_size("ols_slope", CRITERIA), sizes["any_other_statistic"])


class TheTextAgreesWithTheCode(unittest.TestCase):
    def test_draft_3_and_unapproved(self):
        self.assertIn("DRAFT 3", PROTOCOL)
        self.assertIn("UNAPPROVED", PROTOCOL)
        self.assertIn("DRAFT 3", CRITERIA["status"])

    def test_sample_sizes_and_thresholds(self):
        need = PILOT["minimum_sample"]
        self.assertEqual((need["papers"], need["scientific_contexts"], need["papers_per_context"], need["primary_complete_share"]), (60, 3, 20, 0.9))
        self.assertIn("20 eligible papers per stratum", PROTOCOL)
        self.assertIn("**240 calls**", PROTOCOL)
        c = PILOT["criteria"]
        self.assertEqual(c["C2_misleading_refutations"]["c_among_flags"]["max_upper_bound"], 0.5)
        self.assertIsNone(c["D1_discrepancy_detection"]["wording_rule"]["flag_recall_lower_bound_needed_to_describe_the_tool_as_finding_errors"])
        for needle in ("clustered upper bound ≤ 50 %; needs at least 5 flags", "estimate ≥ 25 %; lower bound ≥ 15 %", "upper bound ≤ 5 %",
                       "74 % / 55 % / 30 % / 4.6 %"):
            self.assertIn(needle, PROTOCOL)
        rows = {r["papers"]: r for r in stats.power_table(0.05)}
        self.assertAlmostEqual(rows[60]["chance_of_passing_by_true_paper_level_rate"]["0.01"], 0.547, places=3)

    def test_planted_errors_are_described_as_the_frozen_code_makes_them(self):
        self.assertIn('"claimcheck-mutation-v1:" + doc.slug', MUTATE)
        self.assertIn("rng.random() < 0.5", MUTATE)
        self.assertIn("claimcheck-mutation-v1:<slug>", PROTOCOL)
        self.assertIn("probability ½", PROTOCOL)
        self.assertNotIn("up to four numbers", PROTOCOL)

    def test_kernel_configuration(self):
        k = PILOT["criteria"]["C7_computation"]["kernel_configuration"]
        self.assertEqual((k["workers"], k["claims_per_proof_file"], k["seconds_per_proof_file"], k["memory_limit_gb_per_lean_process"]), (2, 1, 900, 7))
        self.assertIn("**one claim per proof file**", PROTOCOL)
        self.assertIn("**7 GB limit\n   per Lean process**", PROTOCOL)
        params = inspect.signature(v11verify.verify).parameters
        self.assertTrue({"workers", "batch_size", "lean_timeout"} <= set(params))

    def test_model_identifiers_by_configuration(self):
        f, p = MODELS["configurations"]["F"]["providers"], MODELS["configurations"]["P"]["providers"]
        self.assertEqual(f["openrouter"]["model"], "nvidia/nemotron-3-ultra-550b-a55b:free")
        self.assertEqual(p["openrouter"]["model"], "nvidia/nemotron-3-ultra-550b-a55b")
        self.assertEqual(f["gemini"]["model"], p["gemini"]["model"])
        for ident in (f["openrouter"]["model"], p["openrouter"]["model"], p["gemini"]["model"]):
            self.assertIn(f"`{ident}`", PROTOCOL)
        self.assertIsNone(p["gemini"]["usd_per_million_prompt_tokens"])      # until the owner reads the price
        self.assertEqual(MODELS["configurations"]["P"]["caps_usd"]["120"]["total"], 30)
        self.assertIn('"critic" calls of v1\'s `benchmark/run.py` are not made', PROTOCOL)


if __name__ == "__main__":
    unittest.main()
