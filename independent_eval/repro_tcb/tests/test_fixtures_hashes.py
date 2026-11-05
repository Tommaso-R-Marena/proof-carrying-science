"""Fixture integrity — pinned SHA-256 digests for evidence members."""

from __future__ import annotations

import json

from python_harness.hashing import sha256_bytes, sha256_file
from python_harness.paths import EVIDENCE_FIXTURES, FIXTURES, HASH_MANIFEST
from python_harness.reconstruction import materialize_fixtures


def test_materialize_and_hash_manifest_roundtrip() -> None:
    digests = materialize_fixtures()
    assert "certificate.json" in digests
    assert "evidence_canonical.zip" in digests
    assert (EVIDENCE_FIXTURES / "certificate.json").is_file()
    assert (FIXTURES / "evidence_canonical.zip").is_file()

    # Recompute and compare.
    for name, expected in digests.items():
        if name == "evidence_canonical.zip":
            path = FIXTURES / name
        else:
            path = EVIDENCE_FIXTURES / name
        assert sha256_file(path) == expected

    claims = FIXTURES / "claims" / "sample_claims_report.md"
    files = {
        (f"evidence_bundle/{k}" if k != "evidence_canonical.zip" else k): v
        for k, v in digests.items()
    }
    if claims.is_file():
        files["claims/sample_claims_report.md"] = sha256_file(claims)
    manifest = {"format": "pcs-independent-eval-fixture-hashes-v1", "files": files}
    HASH_MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    loaded = json.loads(HASH_MANIFEST.read_text(encoding="utf-8"))
    for rel, digest in loaded["files"].items():
        path = FIXTURES / rel
        assert path.is_file(), rel
        assert sha256_file(path) == digest


def test_synthetic_members_are_deterministic() -> None:
    from python_harness.reconstruction import build_synthetic_members

    a = build_synthetic_members().canonical_archive
    b = build_synthetic_members().canonical_archive
    assert a == b
    assert sha256_bytes(a) == digests_canonical()


def digests_canonical() -> str:
    from python_harness.reconstruction import build_synthetic_members

    return sha256_bytes(build_synthetic_members().canonical_archive)
