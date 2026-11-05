"""Task 14 tests — evidence traceability auditor."""

from __future__ import annotations

from pathlib import Path

from python_harness.hashing import sha256_bytes
from python_harness.paths import CLAIMS_FIXTURES, HASH_MANIFEST
from python_harness.reconstruction import materialize_fixtures
from python_harness.traceability import (
    audit_report,
    classify_claim,
    load_evidence_catalog,
    parse_claims_markdown,
)


def _ensure_hash_manifest() -> None:
    digests = materialize_fixtures()
    files = {
        (f"evidence_bundle/{k}" if k != "evidence_canonical.zip" else k): v
        for k, v in digests.items()
    }
    claims = CLAIMS_FIXTURES / "sample_claims_report.md"
    if claims.is_file():
        files["claims/sample_claims_report.md"] = sha256_bytes(claims.read_bytes())
    import json

    HASH_MANIFEST.write_text(
        json.dumps(
            {"format": "pcs-independent-eval-fixture-hashes-v1", "files": files},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def test_parse_and_classify_fixture_claims(tmp_path: Path) -> None:
    _ensure_hash_manifest()
    text = (CLAIMS_FIXTURES / "sample_claims_report.md").read_text(encoding="utf-8")
    claims = parse_claims_markdown(text)
    ids = {c["claim_id"] for c in claims}
    assert "C12.identity" in ids
    assert "C14.unsupported" in ids
    assert "C14.stale" in ids
    assert "C14.ambiguous" in ids

    catalog = load_evidence_catalog()
    by_id = {c["claim_id"]: classify_claim(c, catalog) for c in claims}

    assert by_id["C12.identity"]["status"] == "supported"
    assert by_id["C14.unsupported"]["status"] == "unsupported"
    assert by_id["C14.stale"]["status"] == "stale"
    assert by_id["C14.ambiguous"]["status"] == "ambiguous"
    assert by_id["C13.os"]["status"] == "ambiguous"


def test_audit_report_writes_json(tmp_path: Path) -> None:
    _ensure_hash_manifest()
    result = audit_report(output=tmp_path / "audit.json")
    assert result["task"] == 14
    assert result["counts"]["unsupported"] >= 1
    assert result["counts"]["stale"] >= 1
    assert result["counts"]["ambiguous"] >= 1
    assert result["verdict"]["has_flags"] is True
    assert (tmp_path / "audit.json").is_file()
