from __future__ import annotations

from pathlib import Path

from python_harness.hashing import sha256_bytes, sha256_file, sha256_paths
from python_harness.paths import (
    find_certificate,
    find_limitations,
    find_receipt,
    resolve_evidence_root,
)


def test_sha256_known_vector():
    # SHA-256("abc") — FIPS 180-4
    assert (
        sha256_bytes(b"abc")
        == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_sha256_file_and_paths(tmp_path: Path):
    f = tmp_path / "x.bin"
    f.write_bytes(b"abc")
    digest = sha256_file(f)
    assert digest == sha256_bytes(b"abc")
    mapped = sha256_paths([f, tmp_path / "missing.bin"])
    assert mapped[str(f.resolve())] == digest
    assert len(mapped) == 1


def test_paths_resolve_dir_and_certificate(fixture_bundle: Path):
    root = resolve_evidence_root(fixture_bundle)
    assert root == fixture_bundle.resolve()
    cert = find_certificate(fixture_bundle)
    assert cert is not None and cert.name == "certificate.json"
    cert_via_file = find_certificate(cert)
    assert cert_via_file == cert.resolve()
    root_via_file = resolve_evidence_root(cert)
    assert root_via_file == fixture_bundle.resolve()
    assert find_receipt(fixture_bundle) is not None
    assert find_limitations(fixture_bundle) is not None
