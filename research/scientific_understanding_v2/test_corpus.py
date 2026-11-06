"""Integrity and split-boundary checks; these are not scientific acceptance tests."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from . import corpus


class CorpusTests(unittest.TestCase):
    def test_fixed_identities_and_source_freeze(self):
        registration = corpus.preregistration()
        self.assertFalse(registration["checker_tests_run_before_freeze"])
        self.assertEqual([case["id"] for case in corpus.projects()],
                         ["biomodels_tyson1991", "scipy_rosenbrock"])
        self.assertEqual([case["id"] for case in corpus.projects("final")],
                         ["biomodels_goldbeter1991", "scipy_integrate"])
        self.assertLess(corpus.source_manifest()["total_fixture_bytes"],
                        10 * 1024 * 1024)

    def test_default_materialization_copies_development_only(self):
        original_read = Path.read_bytes
        reads = []

        def observed_read(path):
            reads.append(path)
            if "heldout" in path.parts:
                self.fail("development materialization opened final raw data")
            return original_read(path)

        with tempfile.TemporaryDirectory(dir="/dev/shm") as temporary:
            output = Path(temporary) / "development"
            with patch.object(Path, "read_bytes", observed_read):
                records = corpus.materialize(output)
            self.assertEqual(len(records), 2)
            for record in records:
                project = Path(record["root"])
                metadata = json.loads((project / "project.json").read_text())
                self.assertFalse(metadata["imported_code_executed"])
                for artifact in record["artifacts"]:
                    raw = (project / artifact["path"]).read_bytes()
                    self.assertEqual(hashlib.sha256(raw).hexdigest(), artifact["sha256"])
                for name in ("project.json", "provenance.json"):
                    content = (project / name).read_text().lower()
                    self.assertNotIn('"expected_answer"', content)
                    self.assertNotIn('"reference_claims"', content)
                    self.assertNotIn('"evaluator_label"', content)
            self.assertTrue(reads)
            self.assertFalse(any("heldout" in path.parts for path in reads))
            with self.assertRaises(corpus.CorpusError):
                corpus.materialize(output)

    def test_source_corruption_fails_before_output_creation(self):
        source_read = corpus._read_source

        def corrupted(source, expected, split):
            changed = dict(source)
            changed["sha256"] = "0" * 64
            return source_read(changed, expected, split)

        with tempfile.TemporaryDirectory(dir="/dev/shm") as temporary:
            output = Path(temporary) / "corrupt"
            with patch.object(corpus, "_read_source", corrupted):
                with self.assertRaises(corpus.CorpusError):
                    corpus.materialize(output)
            self.assertFalse(output.exists())

    def test_unknown_split_rejected(self):
        with self.assertRaises(corpus.CorpusError):
            corpus.projects("all")


if __name__ == "__main__":
    unittest.main()
