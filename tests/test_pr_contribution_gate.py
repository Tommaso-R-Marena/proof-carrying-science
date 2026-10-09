"""Exercise protected contribution gates against real temporary Git histories."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]
SID = "11111111-1111-4111-8111-111111111111"
PID = "22222222-2222-4222-8222-222222222222"
REPO = "Tommaso-R-Marena/" + SOURCE.name


class ContributionGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "scripts").mkdir()
        for name in ["check_pr_contributions.py", "check_contribution_bundle.py", "check_promotion_bundle.py"]:
            shutil.copyfile(SOURCE / "scripts" / name, self.root / "scripts" / name)
        self.git("init", "-q")
        self.git("config", "user.name", "PCS synthetic test fixture")
        self.git("config", "user.email", "fixture@example.test")
        self.commit()
        self.base = self.git("rev-parse", "HEAD")

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.root, text=True).strip()

    def commit(self):
        self.git("add", ".")
        self.git("commit", "-qm", "Synthetic fixture")

    def write(self, path, text):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return p

    def archive(self):
        folder = f"contributions/pcs-submissions/OMEGA-CI/{SID}"
        text = "# Synthetic CI fixture; no participant or scientific authority\n"
        raw = text.encode()
        self.write(folder + "/Fixture.md", text)
        self.write(folder + "/manifest.json", json.dumps({
            "format": "pcs-submission-artifacts-v1", "task_id": "OMEGA-CI", "submission_id": SID,
            "files": [{"name": "Fixture.md", "size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}]
        }))
        return folder, text

    def promotion(self):
        folder, text = self.archive()
        self.commit()
        self.base = self.git("rev-parse", "HEAD")
        self.write("docs/Fixture.md", text)
        self.write(f"contributions/pcs-promotions/{PID}/manifest.json", json.dumps({
            "format": "pcs-production-promotion-v1", "promotion_id": PID,
            "source_submission_id": SID, "source_task_id": "OMEGA-CI", "repository": REPO,
            "base_sha": self.base, "attempt": 1, "source_pr_number": 1,
            "changes": [{"production_path": "docs/Fixture.md", "source_name": "Fixture.md",
                         "size_bytes": len(text.encode()), "sha256": hashlib.sha256(text.encode()).hexdigest()}]
        }))

    def gate(self, **extra):
        env = {**os.environ, "GITHUB_REPOSITORY": REPO, "GITHUB_BASE_SHA": self.base, **extra}
        return subprocess.run(["python3", "scripts/check_pr_contributions.py"], cwd=self.root,
                              env=env, capture_output=True, text=True)

    def test_normal_change_does_not_require_a_nonexistent_archive(self):
        self.write("docs/ordinary.md", "Reviewed source change\n")
        self.commit()
        r = self.gate()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("no contribution paths changed", r.stdout)

    def test_valid_archive_runs_the_actual_digest_checker(self):
        self.archive()
        self.commit()
        r = self.gate()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Bundle integrity PASS", r.stdout)

    def test_tampered_archive_fails_required_gate(self):
        folder, _ = self.archive()
        self.write(folder + "/Fixture.md", "Changed after hashing\n")
        self.commit()
        self.assertNotEqual(self.gate().returncode, 0)

    def test_removing_archive_does_not_skip_validation(self):
        folder, _ = self.archive()
        self.commit()
        self.base = self.git("rev-parse", "HEAD")
        shutil.rmtree(self.root / folder)
        self.commit()
        self.assertNotEqual(self.gate().returncode, 0)

    def test_valid_promotion_runs_exact_archive_to_source_checker(self):
        self.promotion()
        self.commit()
        r = self.gate()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("PCS PROMOTION FILE GATE PASS", r.stdout)

    def test_promotion_with_unmapped_change_fails_required_gate(self):
        self.promotion()
        self.write("docs/Unmapped.md", "Unapproved extra change\n")
        self.commit()
        self.assertNotEqual(self.gate().returncode, 0)

    def test_unknown_repository_or_missing_baseline_fails(self):
        self.assertNotEqual(self.gate(GITHUB_REPOSITORY="another-owner/proof-carrying-science").returncode, 0)
        self.assertNotEqual(self.gate(GITHUB_BASE_SHA="").returncode, 0)


if __name__ == "__main__":
    unittest.main()
