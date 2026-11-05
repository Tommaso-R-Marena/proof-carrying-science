"""Task 13 tests — TCB dependency atlas."""

from __future__ import annotations

from python_harness.tcb_atlas import build_atlas, write_atlas


REQUIRED_CHAIN = [
    "source_bytes",
    "os_io",
    "zip_archive",
    "crypto_sha256",
    "crypto_ed25519",
    "python_runtime",
    "transcripts",
    "lean_authority",
    "reviewer_policy",
    "verification_output",
]

TRUST_CLASSES = {
    "kernel-proved",
    "executable-tested",
    "cryptographically-assumed",
    "externally-trusted",
    "unresolved",
}


def test_atlas_chain_and_classifications(tmp_path) -> None:
    atlas = build_atlas()
    assert atlas["audit_mode"] == "read-only"
    assert atlas["task"] == 13
    assert atlas["chain"] == REQUIRED_CHAIN
    assert atlas["lean_tcb_status_extracted"]
    assert atlas["probes"]["formal/PCS/V2/TCB.lean"]["exists"] is True
    assert atlas["probes"]["pcs/canonical_zip_v06.py"]["exists"] is True

    nodes = {n["id"]: n for n in atlas["graph"]["nodes"]}
    for node_id in REQUIRED_CHAIN:
        assert node_id in nodes
        assert nodes[node_id]["trust_class"] in TRUST_CLASSES

    assert nodes["lean_authority"]["trust_class"] == "kernel-proved"
    assert nodes["crypto_sha256_collision"]["trust_class"] == "cryptographically-assumed"
    assert nodes["environment_reconstruction"]["trust_class"] == "unresolved"
    assert nodes["os_io"]["trust_class"] == "externally-trusted"

    edges = atlas["graph"]["edges"]
    assert any(e["from"] == "source_bytes" and e["to"] == "os_io" for e in edges)
    assert any(e["from"] == "transcripts" and e["to"] == "lean_authority" for e in edges)

    written = write_atlas(tmp_path / "tcb_atlas.json")
    assert (tmp_path / "tcb_atlas.json").is_file()
    assert written["atlas_sha256"]


def test_atlas_does_not_require_lean_mutation() -> None:
    """Sanity: atlas construction is a pure read of existing paths."""
    atlas = build_atlas()
    assert atlas["git_commit"]
    # open gaps must include unresolved reconstruction fidelity
    assert "environment_reconstruction" in atlas["open_gaps"]
