"""Actual Git/source identity controls for the narrow receipt repair successor."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from research.integration_v1 import source_gate as gate


REPOSITORY = Path(__file__).resolve().parents[1]
PROFILE = "docs/integration/2026-10-18/SOURCE_PROFILE.json"


@pytest.fixture
def isolated_identity_repository(tmp_path, monkeypatch):
    profile = json.loads((REPOSITORY / PROFILE).read_bytes())
    paths = set(profile["files"]) | {
        PROFILE, gate.SUCCESSOR_PATH, gate.GATE_PATH, "pcs/receipt_contract_v06.py",
        "docs/integration/2026-10-18/OPEN_PR_LEDGER.json",
    }
    for name in paths:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPOSITORY / name, target)
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    _commit_fixture(tmp_path)
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    monkeypatch.setattr(gate, "REPORTS", tmp_path / "docs/integration/2026-10-18")
    return tmp_path


def _commit_fixture(root):
    subprocess.run([
        "git", "-c", "user.name=PCS source test", "-c", "user.email=pcs-test@example.invalid",
        "commit", "-qm", "Commit isolated source identity fixture",
    ], cwd=root, check=True)


def test_successor_keeps_all_original_scope_and_additional_contract_pin(isolated_identity_repository):
    result = gate.check_profile()
    assert result["passed"] is True, result
    assert result["files_checked"] == 1992
    assert result["additional_files_checked"] == 1
    assert result["V7_modules"] == 38
    original = subprocess.check_output([
        "git", "show", f"{gate.PREDECESSOR_COMMIT}:{PROFILE}"
    ], cwd=REPOSITORY)
    assert (isolated_identity_repository / PROFILE).read_bytes() == original
    assert hashlib.sha256(original).hexdigest() == gate.PREDECESSOR_PROFILE_SHA256


@pytest.mark.parametrize("mutation", [
    "unrelated_source", "predecessor_bytes", "predecessor_hash", "predecessor_commit",
    "old_hash", "new_hash", "source_and_manifest", "formal_override", "unknown_key",
    "duplicate_key", "mode", "symlink", "absent_successor", "gate_source",
    "gate_and_manifest", "uncommitted_manifest",
])
def test_successor_fails_closed_on_identity_mutation(isolated_identity_repository, mutation):
    root = isolated_identity_repository
    successor_path = root / gate.SUCCESSOR_PATH
    successor = json.loads(successor_path.read_bytes())
    changed = root / "pcs/intake_verify_v06.py"
    if mutation == "unrelated_source":
        other = root / "pcs/intake.py"
        other.write_bytes(other.read_bytes() + b"\n# Unreviewed source change\n")
    elif mutation == "predecessor_bytes":
        path = root / PROFILE
        path.write_bytes(path.read_bytes() + b"\n")
    elif mutation == "predecessor_hash":
        successor["predecessor_profile_sha256"] = "ab" * 32
    elif mutation == "predecessor_commit":
        successor["predecessor_commit"] = "0" * 40
    elif mutation == "old_hash":
        successor["files"]["pcs/intake_verify_v06.py"]["old_sha256"] = "ab" * 32
    elif mutation == "new_hash":
        successor["files"]["pcs/intake_verify_v06.py"]["new_sha256"] = "ab" * 32
    elif mutation == "source_and_manifest":
        changed.write_bytes(changed.read_bytes() + b"\n# Broader unreviewed replacement\n")
        successor["files"]["pcs/intake_verify_v06.py"]["new_sha256"] = hashlib.sha256(changed.read_bytes()).hexdigest()
    elif mutation == "formal_override":
        successor["files"]["formal/PCS/V2/ProofGatedPolicy.lean"] = dict(
            successor["files"]["pcs/intake_verify_v06.py"]
        )
    elif mutation == "unknown_key":
        successor["allow_any_source"] = True
    elif mutation == "duplicate_key":
        successor_path.write_text(
            '{"format":"pcs-receipt-source-successor-v1",' +
            json.dumps(successor)[1:], encoding="utf-8",
        )
    elif mutation == "mode":
        changed.chmod(0o755)
    elif mutation == "symlink":
        replacement = root / "replacement.py"
        replacement.write_bytes(changed.read_bytes())
        changed.unlink()
        changed.symlink_to(replacement)
    elif mutation == "absent_successor":
        successor_path.unlink()
    elif mutation == "gate_source":
        path = root / gate.GATE_PATH
        path.write_bytes(path.read_bytes() + b"\n# Unreviewed gate change\n")
    elif mutation == "gate_and_manifest":
        path = root / gate.GATE_PATH
        path.write_bytes(path.read_bytes() + b"\n# Gate and manifest changed together\n")
        successor["files"][gate.GATE_PATH]["new_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    elif mutation == "uncommitted_manifest":
        successor["review_status"] = "independently_reviewed"
    if mutation not in {"duplicate_key", "absent_successor"}:
        successor_path.write_text(json.dumps(successor), encoding="utf-8")
    # Exercise the fixed allowlists/hashes even after a manifest edit is
    # committed. The separate two working-tree controls test the HEAD boundary.
    if mutation not in {"gate_and_manifest", "uncommitted_manifest"}:
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        _commit_fixture(root)
    result = gate.check_profile()
    assert result["passed"] is False, result
    assert result["failures"], result
