"""Exact-byte Python ↔ Lean archive boundary for independent-pilot packages.

Asserts the high-assurance path uses Lean-decoded canonical ZIP bytes and that
Python-materialized member digests match the signed package inventory. This is
an independently tested correspondence check, not a refinement proof of the
Python/OS runtime.
"""

from __future__ import annotations

import hashlib
import json
import os
import zipfile
from pathlib import Path

import pytest

from pcs.independent_pilot_v1 import run_independent_pilot_v1
from pcs.lean_authority_v06 import V06LeanAuthorityError, resolve_lean_authority_v06
from pcs.verifier_zip_v06 import load_package_zip_v06, verify_package_zip_end_to_end_v06


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


def test_independent_pilot_bundle_uses_lean_decoded_canonical_zip(tmp_path):
    evidence = run_independent_pilot_v1(
        tmp_path / "pilot",
        lean_authority_path=AUTHORITY if AUTHORITY.is_file() else None,
        overwrite=True,
    )
    bundle = Path(evidence["paths"]["bundle"])
    public = Path(evidence["paths"]["delivery_archive"]) / "trusted-public.pem"
    # delivery_archive has trusted-public; reviewer also has it
    if not public.is_file():
        public = tmp_path / "pilot" / "reviewer" / "trusted-public.pem"

    loaded = load_package_zip_v06(bundle)
    inventory = json.loads(loaded["package_manifest_bytes"].decode("utf-8"))["files"]
    for name, meta in inventory.items():
        raw = loaded["package_files"][name]
        assert hashlib.sha256(raw).hexdigest() == meta["sha256"]
        assert len(raw) == meta["size"]

    checked = verify_package_zip_end_to_end_v06(
        bundle,
        public,
        expected_fingerprint=evidence["signer_fingerprint"],
        lean_authority_path=AUTHORITY if AUTHORITY.is_file() else None,
        require_canonical_archive=True,
    )
    assert checked["valid"] is True
    assert checked["authoritative"] is True
    assert checked["archive_assurance"] == "lean-decoded-canonical-zip"
    assert checked["lean_authority"]["archive_mode"] == "lean-decoded-canonical-zip"
    assert "pilot-intake-lock.json" in loaded["package_files"]


def test_require_canonical_archive_rejects_noncanonical_deflate_repack(tmp_path):
    evidence = run_independent_pilot_v1(
        tmp_path / "pilot",
        lean_authority_path=AUTHORITY if AUTHORITY.is_file() else None,
        overwrite=True,
    )
    source = Path(evidence["paths"]["bundle"])
    public = tmp_path / "pilot" / "reviewer" / "trusted-public.pem"
    deflated = tmp_path / "deflated.pcs.zip"
    with zipfile.ZipFile(source, "r") as zin, zipfile.ZipFile(
        deflated, "w", compression=zipfile.ZIP_DEFLATED
    ) as zout:
        for info in zin.infolist():
            zout.writestr(info.filename, zin.read(info.filename))

    checked = verify_package_zip_end_to_end_v06(
        deflated,
        public,
        expected_fingerprint=evidence["signer_fingerprint"],
        lean_authority_path=AUTHORITY if AUTHORITY.is_file() else None,
        require_canonical_archive=True,
    )
    assert checked["valid"] is not True
    assert checked.get("failed_stage") == "canonical_archive" or any(
        "canonical" in str(err).lower() for err in (checked.get("errors") or [])
    )
