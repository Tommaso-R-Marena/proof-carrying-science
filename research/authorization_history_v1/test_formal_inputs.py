"""Fail-closed cache validation fixtures; never modify the shared Mathlib cache."""

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from research.authorization_history_v1 import formal_inputs as inputs


class FormalInputTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.dependency = self.root / ".lake/packages/example"
        self.dependency.mkdir(parents=True)
        self.git("init", "--quiet")
        self.git("config", "user.name", "Research Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        (self.dependency / ".gitignore").write_text(".lake/\n")
        (self.dependency / "Proof.lean").write_text("theorem fixture : True := by trivial\n")
        self.commit()
        self.revision = self.git("rev-parse", "HEAD").strip()
        (self.dependency / ".lake/build/lib/lean").mkdir(parents=True)

    def git(self, *arguments):
        return subprocess.check_output(["git", *arguments], cwd=self.dependency, text=True)

    def commit(self):
        self.git("add", ".")
        self.git("commit", "--quiet", "-m", "fixture")

    def test_exact_clean_revision_accepts_but_wrong_revision_rejects(self):
        self.assertEqual(len(inputs.verify_cache(self.root, {"example": self.revision})), 1)
        with self.assertRaisesRegex(RuntimeError, "revision/source"):
            inputs.verify_cache(self.root, {"example": "0" * 40})

    def test_dirty_tracked_source_and_hidden_index_flags_reject(self):
        (self.dependency / "Proof.lean").write_text("theorem changed : True := by trivial\n")
        with self.assertRaisesRegex(RuntimeError, "revision/source"):
            inputs.verify_cache(self.root, {"example": self.revision})
        self.git("update-index", "--assume-unchanged", "Proof.lean")
        with self.assertRaisesRegex(RuntimeError, "revision/source"):
            inputs.verify_cache(self.root, {"example": self.revision})

    def test_unimported_dependency_source_still_verified_without_build_artifacts(self):
        shutil.rmtree(self.dependency / ".lake/build")
        self.assertEqual(inputs.verify_cache(self.root, {"example": self.revision}), [])

    def test_tracked_source_admission_audit_and_untracked_source_reject(self):
        self.assertEqual(len(inputs.audit_project_sources(self.dependency)), 1)
        (self.dependency / "Proof.lean").write_text("theorem falseProof : False := by sorry\n")
        self.commit()
        with self.assertRaisesRegex(RuntimeError, "source admission"):
            inputs.audit_project_sources(self.dependency)
        (self.dependency / "Proof.lean").write_text("theorem fixture : True := by trivial\n")
        self.commit()
        (self.dependency / "Untracked.lean").write_text("theorem other : True := by trivial\n")
        with self.assertRaisesRegex(RuntimeError, "dirty or untracked"):
            inputs.audit_project_sources(self.dependency)

    def test_standalone_manifest_matches_root_and_detects_changed_pin_or_missing_dependency(self):
        project = Path(__file__).resolve().parent / "formal"
        copy = self.root / "project"
        copy.mkdir()
        for name in ("lakefile.toml", "lake-manifest.json"):
            shutil.copyfile(project / name, copy / name)
        pins = inputs.dependency_pins(copy)
        self.assertEqual(pins["mathlib"], inputs.MATHLIB_REVISION)
        manifest = json.loads((copy / "lake-manifest.json").read_text())
        manifest["packages"][0]["rev"] = "0" * 40
        (copy / "lake-manifest.json").write_text(json.dumps(manifest))
        with self.assertRaisesRegex(RuntimeError, "root pin"):
            inputs.dependency_pins(copy)
        manifest["packages"].pop()
        (copy / "lake-manifest.json").write_text(json.dumps(manifest))
        with self.assertRaisesRegex(RuntimeError, "dependency set"):
            inputs.dependency_pins(copy)


if __name__ == "__main__":
    unittest.main(verbosity=2)
