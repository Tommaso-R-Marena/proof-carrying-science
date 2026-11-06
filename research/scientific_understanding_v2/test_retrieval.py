"""Checks use authored synthetic examples only, never scientific fixtures."""
import copy
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest

from .retrieval import rank, load_checkpoint, _validate_checkpoint, tokenize
from .learning.synthetic_benchmark import build_benchmark, SPLIT_FAMILIES, dataset_sha256

ARTIFACTS = Path(__file__).parent / "learning" / "artifacts"


class RetrievalTests(unittest.TestCase):
    def test_lexical_baselines(self):
        docs = [{"id": "a", "text": "The initial concentration is two millimolar."},
                {"id": "b", "text": "The rate law has first order kinetics."}]
        for mode in ("bm25", "tfidf"):
            scores = rank("initial concentration", docs, mode)
            self.assertGreater(scores[0], scores[1])
            self.assertTrue(all(math.isfinite(x) for x in scores))
            self.assertEqual(rank("", [], mode), [])
            self.assertEqual(rank("absent", [{"text": ""}], mode), [0.0])

    def test_validation_and_metadata_is_not_input(self):
        with self.assertRaises(ValueError):
            rank("q", [{"id": "missing-text"}])
        with self.assertRaises(ValueError):
            rank("q", [], "checker")
        one = [{"id": "a", "kind": "correct", "text": "initial value"}]
        two = [{"id": "b", "kind": "false", "text": "initial value"}]
        for mode in ("bm25", "tfidf", "neural"):
            self.assertEqual(rank("starting value", one, mode), rank("starting value", two, mode))

    def test_family_split_and_training_vocabulary(self):
        data = build_benchmark()
        sets = [set(SPLIT_FAMILIES[k]) for k in ("train", "validation", "test")]
        self.assertTrue(all(not a & b for i, a in enumerate(sets) for b in sets[i+1:]))
        self.assertEqual(sum(len(s["queries"]) for s in data.values()), 144)
        model = load_checkpoint()
        expected = {t for part in ("queries", "candidates") for x in data["train"][part] for t in tokenize(x["text"])}
        self.assertEqual(set(model["vocabulary"]), expected)
        self.assertNotIn("reservoir", expected)
        self.assertNotIn("culture", expected)
        report = json.loads((ARTIFACTS/"evaluation.json").read_text())
        self.assertEqual(report["dataset_sha256"], dataset_sha256(data))

    def test_real_checkpoint_and_randomized_control(self):
        main = load_checkpoint()
        control = load_checkpoint(ARTIFACTS/"randomized_encoder.json")
        self.assertFalse(main["training_label_shuffle"])
        self.assertTrue(control["training_label_shuffle"])
        self.assertNotEqual(main["weights"], control["weights"])
        data = build_benchmark()["test"]
        scores = rank(data["queries"][0]["text"], data["candidates"], "neural")
        self.assertEqual(len(scores), len(data["candidates"]))
        self.assertTrue(all(math.isfinite(x) and -1.000001 <= x <= 1.000001 for x in scores))
        self.assertEqual(scores, rank(data["queries"][0]["text"], data["candidates"], "neural"))

    def test_checkpoint_rejects_nonfinite_or_shape_and_digest(self):
        model = copy.deepcopy(load_checkpoint())
        model["weights"]["embedding"][0][0] = float("nan")
        with self.assertRaises(ValueError):
            _validate_checkpoint(model)
        model["weights"]["embedding"][0][0] = 0.0
        model["weights"]["hidden_bias"].append(0.0)
        with self.assertRaises(ValueError):
            _validate_checkpoint(model)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/"weights.json"
            path.write_text("{}")
            path.with_suffix(".json.sha256").write_text("0"*64)
            with self.assertRaisesRegex(ValueError, "SHA256"):
                load_checkpoint(path)

    def test_metrics_recompute_from_ranks(self):
        report = json.loads((ARTIFACTS/"evaluation.json").read_text())
        for models in report["metrics"].values():
            for metrics in models.values():
                rows = metrics["examples"]
                self.assertEqual(metrics["n"], len(rows))
                self.assertAlmostEqual(metrics["top1"], sum(x["rank"] == 1 for x in rows)/len(rows))
                self.assertAlmostEqual(metrics["mrr"], sum(1/x["rank"] for x in rows)/len(rows))
                self.assertTrue(all(1 <= x["rank"] <= x["candidate_count"] for x in rows))


if __name__ == "__main__":
    unittest.main()
