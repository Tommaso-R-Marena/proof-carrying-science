import copy
import json
import subprocess
import sys

import pytest

from pcs.countermodel_v1 import VERSION, _missions, check_countermodel_file, check_countermodel_witness


def witness(mission="implication-flip", n=1):
    return {"format": "pcs-countermodel-witness-v1", "version": VERSION, "mission_id": mission,
            "world": {"n": n, "P": [True]*n, "Q": [False]*n, "R": [[False]*n for _ in range(n)]}}


def test_real_direction_counterexample_and_nonclaims():
    result = check_countermodel_witness(witness())
    assert (result["source_true"], result["proposal_true"]) == (False, True)
    assert result["counterexample"] and result["minimum_domain_size"] == 1
    assert not result["pcs_authoritative"] and not result["lean_kernel_checked"]


def test_quantifier_scope_needs_two_independent_witnesses():
    doc = witness("quantifier-scope", 2)
    doc["world"]["R"] = [[True, False], [False, True]]
    result = check_countermodel_witness(doc)
    assert (result["source_true"], result["proposal_true"]) == (True, False)
    assert result["minimum_domain_size"] == 2


@pytest.mark.parametrize("change", [
    lambda x: x.update(score=999), lambda x: x.update(mission_id="unregistered"),
    lambda x: x.update(version="old"), lambda x: x["world"].update(n=True),
    lambda x: x["world"].update(n=0), lambda x: x["world"].update(n=4),
    lambda x: x["world"].update(P=[1]), lambda x: x["world"].update(R=[["false"]]),
    lambda x: x["world"].update(email="private@example.invalid"),
    lambda x: x.update(mission_id=[]),
])
def test_fail_closed_on_forged_or_unsupported_fields(change):
    doc = witness()
    change(doc)
    with pytest.raises(ValueError):
        check_countermodel_witness(doc)


def test_file_rejects_duplicate_keys_and_oversize(tmp_path):
    path = tmp_path / "w.json"
    path.write_text('{"version":"a","version":"b"}')
    with pytest.raises(ValueError, match="Duplicate"):
        check_countermodel_file(path)
    path.write_bytes(b" "*16385)
    with pytest.raises(ValueError, match="16 KiB"):
        check_countermodel_file(path)


def test_cli_different_exit_codes_for_witness_equal_world_and_invalid(tmp_path):
    path = tmp_path / "witness.json"
    for doc, code in [(witness(), 0), (witness("quantifier-switch"), 1), ({}, 2)]:
        path.write_text(json.dumps(doc))
        out = subprocess.run([sys.executable, "-m", "pcs.cli", "countermodel-check-v1", str(path)], capture_output=True, text=True)
        assert out.returncode == code, out.stderr
        assert json.loads(out.stdout)["pcs_authoritative"] is False


def test_all_pinned_formulas_have_a_counterexample():
    for mission in _missions():
        doc = copy.deepcopy(witness(mission))
        result = check_countermodel_witness(doc)
        assert 1 <= result["minimum_domain_size"] <= 3
