"""Integrity checks for manual references, independent of PCS checks (stdlib only)."""

import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from . import reference


class ReferenceIntegrityTests(unittest.TestCase):
    def test_final_requires_explicit_policy_opt_in(self):
        with self.assertRaisesRegex(PermissionError, "component freeze"):
            reference.load_reference("final")

    def test_unknown_split_rejected(self):
        with self.assertRaisesRegex(ValueError, "split"):
            reference.load_reference("test")

    def test_development_reference_evidence_integrity(self):
        annotations = reference.load_reference("development")
        self.assertTrue(annotations)
        self.assertEqual(len({a["project_id"] for a in annotations}), 2)
        self.assertTrue(any(a["expected_status"] == "contradicted" for a in annotations))
        self.assertTrue(any(a["expected_status"] == "insufficient_evidence" for a in annotations))
        self.assertTrue(all(a["label_provenance"]["pcs_output_used"] is False for a in annotations))

    def test_original_bytes_and_exact_quote_are_required(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root / "original.txt"
            evidence.write_text("Original evidence: parameter a = 3.\n", encoding="utf-8")
            annotation = {"id": "integrity-example", "source": {
                "path": "original.txt",
                "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
                "quote": "parameter a = 3",
            }}
            with patch.object(reference, "REPOSITORY_ROOT", root):
                self.assertEqual(reference.verify_reference_sources([annotation]), {
                    "annotations_checked": 1, "source_files_checked": 1})
                evidence.write_text("Original evidence: parameter a = 4.\n", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "hash mismatch"):
                    reference.verify_reference_sources([annotation])
                annotation["source"]["sha256"] = hashlib.sha256(evidence.read_bytes()).hexdigest()
                with self.assertRaisesRegex(ValueError, "quote absent"):
                    reference.verify_reference_sources([annotation])

    def test_corroborating_evidence_is_verified(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / "original.txt"
            original.write_text("Original source.\n", encoding="utf-8")
            source = {"path": "original.txt",
                      "sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
                      "quote": "Original source."}
            annotation = {"id": "corroborating-example", "source": source,
                          "corroborating_sources": [{**source, "quote": "Absent evidence"}]}
            with patch.object(reference, "REPOSITORY_ROOT", root):
                with self.assertRaisesRegex(ValueError, "quote absent"):
                    reference.verify_reference_sources([annotation])


if __name__ == "__main__":
    unittest.main()
