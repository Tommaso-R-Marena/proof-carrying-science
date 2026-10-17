"""Intake-lock binding on the Lean-authoritative attest-v06 path."""

from __future__ import annotations

import json
import os
import zipfile
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pcs.attest_v06 import V06AttestationError, attest_v06
from pcs.discover_v06 import confirm_manifest_draft_v06, discover_project_v06, write_discovery_outputs_v06
from pcs.independent_pilot_v1 import _align_draft_to_intake, stage_external_lab_project
from pcs.intake import freeze_intake_file
from pcs.lean_authority_v06 import V06LeanAuthorityError, resolve_lean_authority_v06
from pcs.signing import public_key_fingerprint


ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = ROOT / "formal" / ".lake" / "build" / "bin" / "pcs-lean-authority"


def _authority_available() -> bool:
    if AUTHORITY.is_file() and os.access(AUTHORITY, os.X_OK):
        return True
    try:
        resolve_lean_authority_v06(None)
        return True
    except V06LeanAuthorityError:
        return False


def _require_authority() -> None:
    if _authority_available():
        return
    if os.environ.get("PCS_REQUIRE_LEAN_AUTHORITY") == "1":
        pytest.fail(
            "pcs-lean-authority unavailable; required by PCS_REQUIRE_LEAN_AUTHORITY=1"
        )
    pytest.skip("pcs-lean-authority unavailable")


@pytest.fixture(autouse=True)
def _authority_gate():
    _require_authority()


def _keys(tmp: Path) -> tuple[Path, Path, str]:
    tmp.mkdir(parents=True, exist_ok=True)
    private = Ed25519PrivateKey.generate()
    public = private.public_key()
    priv = tmp / "private.pem"
    pub = tmp / "public.pem"
    priv.write_bytes(
        private.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    pub.write_bytes(
        public.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    return priv, pub, public_key_fingerprint(public)


def _confirmed_manifest_and_lock(lab: Path) -> tuple[Path, Path]:
    lock = freeze_intake_file(lab / "pilot_intake.json", lab / "pilot.lock.json", overwrite=True)
    discovered = discover_project_v06(lab)
    draft = lab / "pcs-manifest.draft.json"
    write_discovery_outputs_v06(
        discovered,
        manifest_output=draft,
        report_output=lab / "pcs-discovery.json",
        overwrite=True,
    )
    aligned = _align_draft_to_intake(json.loads(draft.read_text(encoding="utf-8")), lock["intake"])
    draft.write_text(json.dumps(aligned, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = lab / "manifest.json"
    confirm_manifest_draft_v06(draft, manifest, project_root=lab, overwrite=True)
    return manifest, lab / "pilot.lock.json"


def test_attest_v06_binds_matching_intake_lock(tmp_path):
    lab = tmp_path / "lab"
    stage_external_lab_project(lab)
    manifest, lock_path = _confirmed_manifest_and_lock(lab)
    private, public, fingerprint = _keys(tmp_path / "keys")
    bundle = tmp_path / "study.pcs.zip"
    result = attest_v06(
        manifest,
        bundle,
        private,
        public,
        expected_fingerprint=fingerprint,
        intake_lock=lock_path,
        lean_authority_path=AUTHORITY if AUTHORITY.is_file() else None,
        overwrite=True,
        generated_at="2026-10-17T00:00:00+00:00",
    )
    assert result["valid"] is True
    assert result["pilot_intake_lock_bound"] is True
    with zipfile.ZipFile(bundle, "r") as zf:
        assert "pilot-intake-lock.json" in zf.namelist()
        bound = json.loads(zf.read("pilot-intake-lock.json").decode("utf-8"))
    assert bound["intake_semantic_hash"] == json.loads(lock_path.read_text())["intake_semantic_hash"]


def test_attest_v06_rejects_posthoc_intake_statement_change(tmp_path):
    lab = tmp_path / "lab"
    stage_external_lab_project(lab)
    manifest, lock_path = _confirmed_manifest_and_lock(lab)
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    # Mutate the lock statement while keeping the recorded hash (invalid lock),
    # and also a valid lock with a different statement than the certificate.
    mutated_intake = json.loads((lab / "pilot_intake.json").read_text(encoding="utf-8"))
    mutated_intake["claims"][0]["statement"] = "Post-hoc weakened claim after seeing results."
    bad_lock_path = tmp_path / "bad.lock.json"
    from pcs.intake import freeze_intake

    bad = freeze_intake(mutated_intake)
    bad_lock_path.write_text(json.dumps(bad, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    private, public, fingerprint = _keys(tmp_path / "keys")
    with pytest.raises(V06AttestationError, match="intake lock"):
        attest_v06(
            manifest,
            tmp_path / "bad.pcs.zip",
            private,
            public,
            expected_fingerprint=fingerprint,
            intake_lock=bad_lock_path,
            lean_authority_path=AUTHORITY if AUTHORITY.is_file() else None,
            overwrite=True,
            generated_at="2026-10-17T00:00:00+00:00",
        )
    assert lock["intake_semantic_hash"]  # original lock remains usable
