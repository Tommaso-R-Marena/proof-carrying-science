from __future__ import annotations
import json
import pytest
from scripts.build_semantic_golden_benchmark_v1 import prepare

def fixture(tmp_path):
    root=tmp_path/"fixtures"
    (root/"requests").mkdir(parents=True)
    (root/"requests/pos.json").write_text('{"schema":"pcs-semantic-translation-v1"}')
    manifest={"schema":"pcs-semantic-fixtures-v1","fixtures":[
        {"name":"pos_safety","authority":"authority.json","request":"requests/pos.json",
         "verdict":"ACCEPTED","codes":[]}]}
    (root/"expected.json").write_text(json.dumps(manifest))
    return root

def test_provenance_not_misclassified_as_human(tmp_path):
    root=fixture(tmp_path)
    result=prepare(root)
    assert result["counts"]=={"all":1,"development":1,"evaluation":0}
    example=result["examples"][0]
    assert example["origin"]=="aristotle_generated_test_fixture"
    assert example["human_trajectory"] is False
    assert example["learned_model_supervision_approved"] is False
    assert result["authority"]=="NOT_REPLAYED_BY_THIS_EXPORTER"

def test_traversal_and_duplicate_fail_closed(tmp_path):
    root=fixture(tmp_path)
    data=json.loads((root/"expected.json").read_text())
    data["fixtures"][0]["request"]="../../escapes.json"
    (root/"expected.json").write_text(json.dumps(data))
    with pytest.raises(ValueError):
        prepare(root)
    data["fixtures"][0]["request"]="requests/pos.json"
    data["fixtures"].append(dict(data["fixtures"][0]))
    (root/"expected.json").write_text(json.dumps(data))
    with pytest.raises(ValueError):
        prepare(root)

def test_unexpected_metadata_fail_closed(tmp_path):
    root=fixture(tmp_path);data=json.loads((root/"expected.json").read_text())
    data["fixtures"][0]["user_id"]="do-not-leak"
    (root/"expected.json").write_text(json.dumps(data))
    with pytest.raises(ValueError):
        prepare(root)
