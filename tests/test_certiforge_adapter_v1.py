from copy import deepcopy
from hashlib import sha256
import json

from pcs.certiforge_adapter_v1 import FORMAT, MEMBERS, evaluate


def fixture(tmp_path):
    root = tmp_path / "package"
    root.mkdir()
    entries = []
    for index, name in enumerate(sorted(MEMBERS)):
        path = root / name
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(b"adversarial test input")
        entries.append({"id": str(index), "path": name, "sha256": sha256(path.read_bytes()).hexdigest()})
    # This executable is deliberately NOT an authoritative checker. These tests
    # only verify rejection; positive integration runs use the real Rust binary.
    checker = tmp_path / "malicious-checker"
    checker.write_text('#!/bin/sh\nprintf \'{"result":"accept"}\\n\'\n')
    checker.chmod(0o700)
    proposal = {"format": FORMAT, "claim_id": "optimization", "source": {
        "repository": "Tommaso-R-Marena/certiforge", "commit": "a" * 40, "disclosure": "private"},
        "artifacts": entries, "cost_objective": {"metric": "CERTIR_AST_NODE_COUNT", "require_improvement": True}}
    pins = {"checker": checker, "checker_sha256": sha256(checker.read_bytes()).hexdigest(), "checker_source_commit": "a" * 40}
    return root, proposal, pins


def test_incomplete_forged_checker_verdict_never_grants_authority(tmp_path):
    root, proposal, pins = fixture(tmp_path)
    result = evaluate(proposal, root, **pins)
    assert result["state"] == "REJECTED"
    assert result["pcs_authority"] is False
    assert result["lean_kernel_checked"] is False


def test_bad_pins_duplicate_inventory_path_escape_and_tampering_reject(tmp_path):
    root, proposal, pins = fixture(tmp_path)
    mutations = [lambda x: x["artifacts"].pop(),
                 lambda x: x["artifacts"].__setitem__(0, deepcopy(x["artifacts"][1])),
                 lambda x: x["artifacts"][0].update(path="../escape"),
                 lambda x: x["artifacts"][0].update(sha256="0" * 64),
                 lambda x: x["cost_objective"].update(require_improvement=1),
                 lambda x: x.update(proved=True)]
    for mutate in mutations:
        altered = deepcopy(proposal)
        mutate(altered)
        assert evaluate(altered, root, **pins)["state"] == "REJECTED"
    assert evaluate(proposal, root, **{**pins, "checker_sha256": "0" * 64})["state"] == "REJECTED"
    path = root / "program.certir"
    path.unlink()
    path.symlink_to(pins["checker"])
    assert evaluate(proposal, root, **pins)["state"] == "REJECTED"
