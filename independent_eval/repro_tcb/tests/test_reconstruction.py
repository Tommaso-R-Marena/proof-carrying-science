"""Task 12 tests — cross-environment reconstruction harness."""

from __future__ import annotations

import json
from pathlib import Path

from python_harness.canonical_zip import canonical_zip_bytes, noncanonical_zip_bytes
from python_harness.hashing import sha256_bytes
from python_harness.reconstruction import (
    build_synthetic_members,
    materialize_fixtures,
    reconstruct,
    run_full_campaign,
)


def test_canonical_vs_noncanonical_distinction(tmp_path: Path) -> None:
    evidence = build_synthetic_members()
    canonical = evidence.canonical_archive
    regenerated = canonical_zip_bytes(dict(evidence.members))
    noncanonical = noncanonical_zip_bytes(evidence.members)
    assert canonical == regenerated
    assert canonical != noncanonical
    assert sha256_bytes(canonical) != sha256_bytes(noncanonical)
    # Member digests remain equal even when archive bytes differ.
    from python_harness.canonical_zip import read_zip_members

    assert {
        k: sha256_bytes(v) for k, v in read_zip_members(canonical).items()
    } == {k: sha256_bytes(v) for k, v in read_zip_members(noncanonical).items()}


def test_identical_archive_replay_passes(tmp_path: Path) -> None:
    fixtures = tmp_path / "evidence_bundle"
    materialize_fixtures(fixtures)
    report = reconstruct(
        mode="identical_archive_replay",
        fixture_dir=fixtures,
        output=tmp_path / "ident.json",
        clean_dir_count=3,
    )
    assert report["verdict"]["pass"] is True
    assert report["distinction"]["observed_byte_identity_with_canonical"] is True
    assert report["environment"]["git_commit"]
    assert report["environment"]["platform"]["platform"]
    assert report["environment"]["toolchains"]["lean_toolchain_file"]
    authority = report["environment"]["toolchains"]["pcs_lean_authority"]
    assert "present" in authority
    if authority["present"]:
        assert authority["sha256"] and len(authority["sha256"]) == 64
    else:
        assert authority.get("sha256") is None
    assert len(report["clean_directory_verifications"]) == 3
    assert report["cross_python_verifications"]


def test_regenerated_noncanonical_is_not_byte_identical(tmp_path: Path) -> None:
    fixtures = tmp_path / "evidence_bundle"
    materialize_fixtures(fixtures)
    report = reconstruct(
        mode="regenerated_noncanonical",
        fixture_dir=fixtures,
        output=tmp_path / "noncanon.json",
    )
    assert report["verdict"]["pass"] is True
    assert report["distinction"]["observed_byte_identity_with_canonical"] is False
    assert report["distinction"]["semantic_member_digests_stable"] is True


def test_full_campaign(tmp_path: Path) -> None:
    fixtures = tmp_path / "evidence_bundle"
    materialize_fixtures(fixtures)
    # Point FIXTURES indirectly by using reconstruct inside campaign on default;
    # campaign uses default fixture path — ensure materialize wrote there or use local.
    summary = run_full_campaign(tmp_path / "out")
    assert summary["pass"] is True
    assert summary["modes"]["identical_archive_replay"]["observed_byte_identity_with_canonical"] is True
    assert summary["modes"]["regenerated_noncanonical"]["observed_byte_identity_with_canonical"] is False
    assert (tmp_path / "out" / "reconstruction_campaign.json").is_file()
    payload = json.loads((tmp_path / "out" / "reconstruction_campaign.json").read_text())
    assert payload["pass"] is True
