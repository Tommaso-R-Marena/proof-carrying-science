"""Authored grading adversaries; imports/reads no scientific benchmark source."""
import copy
import hashlib
from pathlib import Path
import tempfile
import unittest

try:
    from .evaluation import (FROZEN_PROTOCOL, canonical_expression, evaluate_retrieval,
                             grade_reference, protocol_sha256, retrieval_candidates)
except ImportError:
    from evaluation import (FROZEN_PROTOCOL, canonical_expression, evaluate_retrieval,
                            grade_reference, protocol_sha256, retrieval_candidates)


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.text = "concentration = 2 mM\nother = 9 s\nrate = k*x\n"
        self.path = Path(self.directory.name)/"snapshot"
        self.path.write_text(self.text)
        self.digest = hashlib.sha256(self.text.encode()).hexdigest()
        self.inventory = {"artifacts": [{"id": "a", "path": "toy.txt", "sha256": self.digest,
                                          "snapshot_path": str(self.path)}]}
        self.annotation = {"id": "manual-1", "statement": "The concentration is two millimolar.",
                           "kind": "quantity", "expected_status": "supported",
                           "source": {"path": "manual/source/toy.txt", "sha256": self.digest,
                                      "quote": "concentration = 2 mM"},
                           "typed_expectation": {"quantity": "concentration", "value": 2,
                                                 "unit": "mM", "absolute_tolerance": 0}}

    def source(self, quote):
        start = self.text.index(quote)
        return {"artifact_id": "a", "path": "toy.txt", "sha256": self.digest, "quote": quote,
                "locator": {"char_start": start, "char_end": start+len(quote)}}

    def record(self, **changes):
        result = {"id": "q1", "name": "concentration", "value": "2.0", "unit": "mM",
                  "source": self.source("concentration = 2 mM"), "authority": False}
        result.update(changes)
        return result

    def grade(self, records, annotations=None, checks=None, category="quantities"):
        return grade_reference(annotations or [self.annotation], {category: records}, self.inventory, checks)

    def test_typed_numeric_match_and_real_misses(self):
        grade = self.grade([self.record()])
        self.assertEqual(grade["metrics"]["supported_manual_claim_recall"], 1.0)
        self.assertEqual(grade["metrics"]["reference_supported_probe_precision"], 1.0)
        missed = self.grade([])
        self.assertEqual(missed["metrics"]["supported_manual_claim_recall"], 0.0)
        self.assertEqual(missed["outcomes"][0]["outcome"], "missed_supported_claim")
        self.assertIsNone(missed["metrics"]["overall_extraction_precision"])

    def test_same_source_wrong_meaning_and_units_fail(self):
        for changes in ({"value": "3"}, {"unit": "uM"}, {"unit": None},
                        {"name": "other"}, {"value": True}, {"value": "nan"}, {"relation": "not_equals"},
                        {"relation": "<="}, {"relation": "not equal"}):
            with self.subTest(changes=changes):
                grade = self.grade([self.record(**changes)])
                self.assertEqual(grade["metrics"]["supported_manual_claim_recall"], 0.0)

    def test_broad_quote_inventory_and_unknown_semantics_do_not_recall(self):
        broad = self.record(name="other", value=9, source=self.source(self.text))
        grade = self.grade([broad])
        self.assertTrue(grade["outcomes"][0]["source_covered"])
        self.assertEqual(grade["metrics"]["supported_manual_claim_recall"], 0.0)
        generic = {"id": "u", "source": self.source(self.text), "reason": "unknown meaning"}
        grade = self.grade([generic], category="unresolved")
        self.assertEqual(grade["metrics"]["supported_manual_claim_recall"], 0.0)
        self.assertTrue(grade["outcomes"][0]["abstained"])

    def test_forged_digest_filename_quote_and_span_fail(self):
        for changes in ({"sha256": "0"*64}, {"path": "evil.txt"}, {"quote": "concentration = 3 mM"},
                        {"artifact_id": "evil"}, {"locator": {"char_start": 0, "char_end": 1}}):
            with self.subTest(changes=changes):
                record = self.record()
                record["source"].update(changes)
                self.assertEqual(self.grade([record])["metrics"]["supported_manual_claim_recall"], 0.0)

    def test_source_token_similarity_is_not_semantic_span_overlap(self):
        self.text += "concentration = 2 mM at a separate experiment\n"
        self.path.write_text(self.text)
        self.digest = hashlib.sha256(self.text.encode()).hexdigest()
        self.inventory["artifacts"][0]["sha256"] = self.digest
        self.annotation["source"]["sha256"] = self.digest
        # A different reference span is not a substitute for the annotated one.
        self.annotation["source"]["quote"] = "concentration = 2 mM at a separate experiment"
        grade = self.grade([self.record()])
        self.assertEqual(grade["metrics"]["supported_manual_claim_recall"], 0.0)

    def test_counterclaims_and_false_promotions_are_separate(self):
        counter = copy.deepcopy(self.annotation)
        counter.update(id="false", expected_status="contradicted", statement="Concentration is three millimolar.")
        counter["typed_expectation"]["counterclaim_value"] = 3
        records = [self.record(), self.record(id="q2", value=3, certified=True)]
        grade = self.grade(records, [self.annotation, counter])
        self.assertEqual(grade["metrics"]["supported_manual_claim_recall"], 1.0)
        self.assertEqual(grade["metrics"]["counterclaims_proposed"], 1)
        self.assertGreater(grade["metrics"]["unsupported_promotion_count"], 0)
        self.assertLess(grade["metrics"]["reference_supported_probe_precision"], 1.0)
        self.assertTrue(grade["outcomes"][0]["semantic_mismatches"])
        absent = self.grade([], [counter])
        self.assertEqual(absent["outcomes"][0]["outcome"], "counterclaim_not_proposed_or_abstained")

    def test_generic_checker_pass_does_not_certify_meaning(self):
        grade = self.grade([self.record(value=3)], checks=[{"interpretation_id": "q1", "checker": "arithmetic", "status": "PASS"}])
        self.assertEqual(grade["metrics"]["unsupported_promotion_count"], 0)
        self.assertEqual(grade["metrics"]["supported_manual_claim_recall"], 0)
        self.assertFalse(grade["outcomes"][0]["abstained"])

    def test_finite_canonical_ast_and_equation_match(self):
        a = {"op": "mul", "args": [{"op": "symbol", "name": "x"}, {"op": "symbol", "name": "k"}]}
        self.assertEqual(canonical_expression(a), canonical_expression("k*x"))
        for bad in ("1e9999", "open('evil')", "sum(x, bogus=y)", "sum(x, axis=y)", "sum(x, axis=1, axis=2)",
                    {"op": "number", "value": float("inf")}, {"op": "reaction_rate", "reaction": 3},
                    {"op": "derivative", "state": float("nan"), "variable": "time"},
                    {"op": "call", "function": "sum", "args": "x"},
                    {"op": "call", "function": "sum", "args": [{"op": "symbol", "name": "x"}], "keywords": []}):
            with self.assertRaises((ValueError, SyntaxError)):
                canonical_expression(bad)
        annotation = copy.deepcopy(self.annotation)
        annotation["source"]["quote"] = "rate = k*x"
        annotation["typed_expectation"] = {"lhs": "rate", "rhs": "k*x", "relation": "="}
        eq = {"id": "e", "lhs": {"op": "symbol", "name": "rate"}, "rhs": a,
              "source": self.source("rate = k*x")}
        self.assertEqual(self.grade([eq], [annotation], category="equations")["metrics"]["supported_manual_claim_recall"], 1)
        eq["rhs"] = {"op": "add", "args": a["args"]}
        self.assertEqual(self.grade([eq], [annotation], category="equations")["metrics"]["supported_manual_claim_recall"], 0)

    def test_unsupported_inference_abstains(self):
        annotation = copy.deepcopy(self.annotation)
        annotation["units"] = {"scope": "reviewer_inferred_constraint"}
        grade = self.grade([self.record(certified=True)], [annotation])
        self.assertEqual(grade["metrics"]["supported_manual_claim_recall"], 0)
        self.assertGreater(grade["metrics"]["unsupported_promotion_count"], 0)
        self.assertFalse(grade["outcomes"][0]["abstained"])
        evidence = [{"source": self.source("other = 9 s")}]
        grade = self.grade([self.record(assumption_evidence=evidence)], [annotation])
        self.assertEqual(grade["metrics"]["supported_manual_claim_recall"], 0)
        self.assertTrue(grade["outcomes"][0]["abstained"])

    def test_tiny_quote_does_not_support_invented_slots(self):
        grade = self.grade([self.record(source=self.source("mM"))])
        self.assertTrue(grade["outcomes"][0]["source_covered"])
        self.assertEqual(grade["metrics"]["supported_manual_claim_recall"], 0)

    def test_explicit_auxiliary_slots_cannot_be_ignored(self):
        annotation = copy.deepcopy(self.annotation)
        annotation["source"]["quote"] = "rate = k*x"
        annotation["typed_expectation"] = {"lhs": "rate", "rhs": "k*x", "variables": ["k", "x"], "relation": "="}
        eq = {"id": "e", "lhs": "rate", "rhs": "k*x", "source": self.source("rate = k*x")}
        self.assertEqual(self.grade([eq], [annotation], category="equations")["metrics"]["supported_manual_claim_recall"], 1)
        eq["variables"] = ["unrelated"]
        self.assertEqual(self.grade([eq], [annotation], category="equations")["metrics"]["supported_manual_claim_recall"], 0)
        eq.pop("variables")
        annotation["typed_expectation"]["terms"] = {"k": 1, "x": 1}
        self.assertEqual(self.grade([eq], [annotation], category="equations")["metrics"]["supported_manual_claim_recall"], 0)
        annotation["typed_expectation"].pop("terms")
        annotation["typed_expectation"]["parameters"] = {"k": 2}
        eq["parameters"] = None
        self.assertEqual(self.grade([eq], [annotation], category="equations")["metrics"]["supported_manual_claim_recall"], 0)

    def test_retrieval_false_questions_and_missing_candidates(self):
        counter = copy.deepcopy(self.annotation)
        counter.update(id="false", expected_status="contradicted", statement="Is concentration three mM?")
        annotations = [self.annotation, counter]
        result = evaluate_retrieval(annotations, {"quantities": [self.record()]}, self.inventory)
        self.assertEqual(set(result["modes"]), {"bm25", "tfidf", "neural", "random"})
        for metrics in result["modes"].values():
            self.assertEqual(metrics["n"], 2)
            self.assertEqual(metrics["reference_candidate_coverage"], 1)
            self.assertEqual(metrics["mrr"], 1)
        absent = evaluate_retrieval(annotations, {}, self.inventory)
        for metrics in absent["modes"].values():
            self.assertEqual(metrics["mrr"], 0)
            self.assertIsNone(metrics["outcomes"][0]["rank"])

    def test_whole_file_quotes_are_not_retrieval_candidates(self):
        self.text = "concentration = 2 mM\n"*300
        self.path.write_text(self.text)
        self.digest = hashlib.sha256(self.text.encode()).hexdigest()
        self.inventory["artifacts"][0]["sha256"] = self.digest
        records = {"unresolved": [{"id": "huge", "source": self.source(self.text)}]}
        self.assertEqual(retrieval_candidates(records, self.inventory), [])
        self.assertEqual(len(protocol_sha256()), 64)
        self.assertFalse(FROZEN_PROTOCOL["training_or_retuning"])


if __name__ == "__main__":
    unittest.main()
