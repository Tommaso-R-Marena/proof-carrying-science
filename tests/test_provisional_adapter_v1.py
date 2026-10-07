from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pcs.provisional_adapter_v1 import (
    AdapterProposalError,
    evaluate_file,
    evaluate_proposal,
    main,
)


def write(root: Path, name: str, data: bytes) -> dict:
    (root / name).write_bytes(data)
    return {"id": name.replace(".", "_"), "path": name, "sha256": hashlib.sha256(data).hexdigest()}


def template(artifacts: list[dict], check: dict) -> dict:
    return {
        "format": "pcs-adapter-proposal-v1",
        "source": {"project": "sample", "commit": "a" * 40, "disclosure": "synthetic"},
        "claim": {"id": "C1", "kind": "computational", "statement": "Finite local check of pinned synthetic artifacts"},
        "artifacts": artifacts,
        "check": check,
        "assumptions": ["Exact bytes are the inputs to this local diagnostic"],
    }


def identity(tmp_path: Path, left: bytes = b"abc", right: bytes = b"abc") -> dict:
    a = write(tmp_path, "before.bin", left)
    b = write(tmp_path, "after.bin", right)
    return template([a, b], {
        "type": "pcs.reference.identical_bytes.v1",
        "left_artifact": a["id"], "right_artifact": b["id"],
    })


def trace_case(tmp_path: Path, events: list[dict]) -> dict:
    source = write(tmp_path, "trace.json", json.dumps({"events": events}).encode())
    return template([source], {
        "type": "pcs.reference.bounded_trace.v1",
        "trace_artifact": source["id"],
        "forbidden_action": 7, "max_cumulative_risk": 4,
    })


def test_identity_pass_is_never_authoritative(tmp_path):
    result = evaluate_proposal(identity(tmp_path), tmp_path)
    assert result["result"] == "LOCAL_CHECK_PASS"
    assert result["authoritative"] is False
    assert result["pcs_acceptance"] == "NOT_EVALUATED"
    assert result["claim_status"] == "OPEN"
    assert "valid" not in result and "accept" not in result


def test_identity_changed_bytes_fail_even_when_pinned(tmp_path):
    report = evaluate_proposal(identity(tmp_path, b"alpha", b"beta"), tmp_path)
    assert report["result"] == "LOCAL_CHECK_FAIL"
    assert report["claim_status"] == "OPEN"


def test_trace_valid_and_two_distinct_counterexamples(tmp_path):
    assert evaluate_proposal(trace_case(tmp_path, [
        {"action": 1, "risk": 1}, {"action": 2, "risk": 3},
    ]), tmp_path)["result"] == "LOCAL_CHECK_PASS"
    assert evaluate_proposal(trace_case(tmp_path, [
        {"action": 7, "risk": 0},
    ]), tmp_path)["result"] == "LOCAL_CHECK_FAIL"
    assert evaluate_proposal(trace_case(tmp_path, [
        {"action": 1, "risk": 3}, {"action": 2, "risk": 2},
    ]), tmp_path)["result"] == "LOCAL_CHECK_FAIL"


def test_unknown_type_refuses_signed_or_transcript_pass(tmp_path):
    p = identity(tmp_path)
    p["check"]["type"] = "certiforge.unregistered.pretend"
    with pytest.raises(AdapterProposalError, match="UNREGISTERED_CHECK_TYPE"):
        evaluate_proposal(p, tmp_path)
    p = identity(tmp_path)
    p["check"]["transcript_outcome"] = "PASS"
    with pytest.raises(AdapterProposalError, match="exactly"):
        evaluate_proposal(p, tmp_path)
    p = identity(tmp_path)
    p["valid"] = True
    with pytest.raises(AdapterProposalError, match="exactly"):
        evaluate_proposal(p, tmp_path)


def test_changed_hash_never_admits_artifact(tmp_path):
    p = identity(tmp_path)
    (tmp_path / "after.bin").write_bytes(b"modified")
    with pytest.raises(AdapterProposalError, match="SHA-256 mismatch"):
        evaluate_proposal(p, tmp_path)


def test_rejects_symlink_traversal_and_alias(tmp_path):
    p = identity(tmp_path)
    p["artifacts"][0]["path"] = "../secrets.txt"
    with pytest.raises(AdapterProposalError, match="unsafe artifact path"):
        evaluate_proposal(p, tmp_path)
    outside = tmp_path.parent / "secret-file-in-test.txt"
    outside.write_text("confidential", encoding="utf-8")
    (tmp_path / "linked.bin").symlink_to(outside)
    p = identity(tmp_path)
    p["artifacts"][0]["path"] = "linked.bin"
    with pytest.raises(AdapterProposalError, match="symbolic links"):
        evaluate_proposal(p, tmp_path)
    p = identity(tmp_path)
    p["artifacts"][1]["id"] = p["artifacts"][0]["id"]
    with pytest.raises(AdapterProposalError, match="duplicate"):
        evaluate_proposal(p, tmp_path)


def test_trace_rejects_fractional_boolean_bad_json_duplicate_keys(tmp_path):
    p = trace_case(tmp_path, [{"action": True, "risk": 1}])
    with pytest.raises(AdapterProposalError, match="integer"):
        evaluate_proposal(p, tmp_path)
    p = trace_case(tmp_path, [{"action": 1.5, "risk": 1}])
    with pytest.raises(AdapterProposalError, match="integer"):
        evaluate_proposal(p, tmp_path)
    raw = b'{"events":[{"action":1,"risk":0,"risk":0}]}'
    p = trace_case(tmp_path, [{"action": 1, "risk": 0}])
    (tmp_path / "trace.json").write_bytes(raw)
    p["artifacts"][0]["sha256"] = hashlib.sha256(raw).hexdigest()
    with pytest.raises(AdapterProposalError, match="strict JSON"):
        evaluate_proposal(p, tmp_path)


def test_proposal_duplicate_keys_fail_and_cli_nonzero(tmp_path, capsys):
    p = identity(tmp_path)
    target = tmp_path / "envelope.json"
    target.write_text(json.dumps(p), encoding="utf-8")
    assert evaluate_file(target, tmp_path)["result"] == "LOCAL_CHECK_PASS"
    assert main(["--envelope", str(target), "--root", str(tmp_path)]) == 0
    assert "UNTRUSTED_ADAPTER_DIAGNOSTIC" in capsys.readouterr().out
    target.write_text('{"format":"pcs-adapter-proposal-v1","format":"pcs-adapter-proposal-v1"}', encoding="utf-8")
    assert main(["--envelope", str(target), "--root", str(tmp_path)]) == 2


def test_unsupported_assurance_and_unpinned_refs_fail(tmp_path):
    p = identity(tmp_path)
    p["claim"]["kind"] = "formal"
    with pytest.raises(AdapterProposalError, match="bounded computational"):
        evaluate_proposal(p, tmp_path)
    p = identity(tmp_path)
    p["check"]["right_artifact"] = "missing"
    with pytest.raises(AdapterProposalError, match="two distinct"):
        evaluate_proposal(p, tmp_path)


def test_no_false_claim_upgrade_on_python_reference_pass(tmp_path):
    p = identity(tmp_path)
    p["source"]["disclosure"] = "private"
    p["assumptions"] = ["Do not infer deployed program equivalence from identical fixture bytes."]
    result = evaluate_proposal(p, tmp_path)
    assert result["result"] == "LOCAL_CHECK_PASS"
    assert result["pcs_acceptance"] == "NOT_EVALUATED"
    assert result["authoritative"] is False
    assert result["claim_status"] == "OPEN"

def test_machine_readable_contract_accepts_pinned_fixture_and_rejects_unknown_keys(tmp_path):
    import jsonschema
    schema_path = Path(__file__).resolve().parents[1] / "pcs" / "schemas" / "adapter_proposal_v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    document = identity(tmp_path)
    jsonschema.validate(document, schema)
    document["check"]["transcript_outcome"] = "PASS"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(document, schema)


def test_unhashable_malicious_fields_rejected_without_raising_type_errors(tmp_path):
    for field, bad_value in [
        ("type", {"reported": "PASS"}),
        ("type", ["unknown"]),
    ]:
        p = identity(tmp_path)
        p["check"][field] = bad_value
        with pytest.raises(AdapterProposalError, match="UNREGISTERED_CHECK_TYPE"):
            evaluate_proposal(p, tmp_path)
    p = identity(tmp_path)
    p["source"]["disclosure"] = ["public"]
    with pytest.raises(AdapterProposalError, match="disclosure"):
        evaluate_proposal(p, tmp_path)
    p = identity(tmp_path)
    p["artifacts"][0]["path"] = ["before.bin"]
    with pytest.raises(AdapterProposalError, match="path"):
        evaluate_proposal(p, tmp_path)


def test_disclosure_and_unverified_claim_status_do_not_confuse_cryptographic_authenticity(tmp_path):
    p = identity(tmp_path)
    p["source"]["disclosure"] = "public"
    report = evaluate_proposal(p, tmp_path)
    assert report["authoritative"] is False
    assert report["pcs_acceptance"] == "NOT_EVALUATED"
    assert report["claim_status"] == "OPEN"
    assert "signature" in " ".join(report["limitations"]).lower() or "unsigned" in " ".join(report["limitations"]).lower()
