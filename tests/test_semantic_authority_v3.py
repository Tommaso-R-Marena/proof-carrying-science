"""Real checker/store integration and non-promotion/replay negative controls."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from pcs.canonical_json import canonicalize_jcs_bytes
from pcs.semantic_authority_v3 import SemanticAuthority
from pcs.semantic_kernel_bridge_v1 import canonical_bytes, digest
from pcs_semantic.receipt_store import ReceiptStore

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "formal/fixtures/semantic_authority_v3"
BIN = ROOT / "formal/.lake/build/bin/pcs-semantic-check"


def bound(request, authority):
    inner = request["request"]["request"]["interpretation"]
    core = {"format": "pcs-claim-ir-v1", "claims": [
        {"claim_id": "test-v3", "statement": inner["source_text"], "closure_state": "BLOCKED"}]}
    ir = dict(core, claim_ir_sha256=digest(canonicalize_jcs_bytes(core)))
    binding = {"format": "pcs-semantic-claim-ir-binding-v1", "claim_ir_sha256": ir["claim_ir_sha256"],
               "claim_id": "test-v3", "request_sha256": digest(canonical_bytes(request)),
               "source_statement": inner["source_text"],
               "selected_semantic_claim_sha256": digest(canonical_bytes(inner["selected"])),
               "registry_sha256": digest(authority)}
    return {"claim_ir": ir, "binding": binding,
            "approved_binding_sha256": digest(canonical_bytes(binding))}


@pytest.fixture
def setup_authority(tmp_path):
    assert BIN.is_file(), "Build the required semantic executable before full integration tests"
    authority = (FIX / "authority.json").read_bytes()
    request = json.loads((FIX / "requests/pos_certified.json").read_text())
    scope = json.loads(authority)["context"]["scope"]
    database = tmp_path / "receipts.sqlite"
    ReceiptStore.initialize(str(database), scope, 1000)
    args = {"binary": BIN, "binary_sha256": digest(BIN.read_bytes()),
            "authority_bytes": authority, "authority_sha256": digest(authority),
            "store": database, "allow_public_fixtures": True, "clock": lambda: 2000}
    return args, request, bound(request, authority)


def test_actual_certification_then_replay_and_claim_ir_stays_unpromoted(setup_authority):
    args, request, binding = setup_authority
    authority = SemanticAuthority(**args)
    first = authority.evaluate(canonical_bytes(request), **binding)
    assert first["outcome"] == "CERTIFIED_TRANSLATION"
    assert first["store_commit_completed"] and len(first["consumed_nonces"]) == 3
    assert not first["production_configuration"] and not first["pcs_scientific_authority"]
    assert binding["claim_ir"]["claims"][0]["closure_state"] == "BLOCKED"
    replay = authority.evaluate(canonical_bytes(request), **binding)
    assert replay["outcome"] == "RECEIPT_REJECTED"
    assert not replay["store_commit_completed"]


def test_fixture_keys_rejected_by_default(setup_authority):
    args, _, _ = setup_authority
    with pytest.raises(ValueError, match="PUBLIC_FIXTURE"):
        SemanticAuthority(**dict(args, allow_public_fixtures=False))


@pytest.mark.parametrize("field", ["binary_sha256", "authority_sha256"])
def test_untrusted_pin_rejected(setup_authority, field):
    args, _, _ = setup_authority
    with pytest.raises(ValueError, match="PIN_MISMATCH"):
        SemanticAuthority(**dict(args, **{field: "0" * 64}))


def test_edited_claim_ir_rejected_before_any_consumption(setup_authority):
    args, request, binding = setup_authority
    changed = copy.deepcopy(binding)
    changed["claim_ir"]["claims"][0]["statement"] = "A different scientific statement"
    authority = SemanticAuthority(**args)
    result = authority.evaluate(canonical_bytes(request), **changed)
    assert result["outcome"] == "REJECTED"
    assert authority.store.consumed_nonces() == []


def test_legacy_request_and_duplicate_json_fail_closed(setup_authority):
    args, request, binding = setup_authority
    authority = SemanticAuthority(**args)
    raw = canonical_bytes(request)
    duplicate = b'{"schema":"pcs-semantic-translation-v3",' + raw[1:]
    for data in [canonical_bytes(request["request"]["request"]), duplicate]:
        assert authority.evaluate(data, **binding)["outcome"] == "REJECTED"
    assert authority.store.consumed_nonces() == []


def test_checker_replacement_rejected_inside_transaction(setup_authority, tmp_path):
    args, request, binding = setup_authority
    binary = tmp_path / "checker"
    shutil.copy2(BIN, binary)
    authority = SemanticAuthority(**dict(args, binary=binary))
    binary.write_bytes(b"replaced checker")
    assert authority.evaluate(canonical_bytes(request), **binding)["outcome"] == "REJECTED"
    assert authority.store.consumed_nonces() == []


def test_revocation_is_read_from_actual_store(setup_authority):
    args, request, binding = setup_authority
    authority = SemanticAuthority(**args)
    proof_key = next(r["issuer"] for r in request["receipts"] if r["role"] == "proof")
    authority.store.revoke(proof_key, 1900)
    result = authority.evaluate(canonical_bytes(request), **binding)
    assert result["outcome"] == "RECEIPT_REJECTED"
    assert authority.store.consumed_nonces() == []


def test_lost_store_is_not_silently_reinitialized(setup_authority, tmp_path):
    args, _, _ = setup_authority
    with pytest.raises(ValueError, match="MISSING"):
        SemanticAuthority(**dict(args, store=tmp_path / "absent.sqlite"))


def test_installed_cli_uses_actual_checker_and_committed_store(setup_authority, tmp_path):
    args, request, binding = setup_authority
    inputs = {"authority": args["authority_bytes"], "request": canonical_bytes(request),
              "claim-ir": canonical_bytes(binding["claim_ir"]), "binding": canonical_bytes(binding["binding"])}
    command = [sys.executable, "-m", "pcs.cli", "semantic-authority-v3", "--binary", str(BIN),
               "--approved-binary-sha256", args["binary_sha256"],
               "--approved-authority-sha256", args["authority_sha256"],
               "--approved-binding-sha256", binding["approved_binding_sha256"],
               "--store", str(args["store"]), "--allow-public-fixtures", "--fixture-clock", "2000"]
    for name, data in inputs.items():
        path = tmp_path / (name + ".json")
        path.write_bytes(data)
        command.extend(["--" + name, str(path)])
    run = subprocess.run(command, capture_output=True, check=True, cwd=ROOT)
    assert json.loads(run.stdout)["outcome"] == "CERTIFIED_TRANSLATION"
    second = subprocess.run(command, capture_output=True, cwd=ROOT)
    assert second.returncode == 1
    assert json.loads(second.stdout)["outcome"] == "RECEIPT_REJECTED"
