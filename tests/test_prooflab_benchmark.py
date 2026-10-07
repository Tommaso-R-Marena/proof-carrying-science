import json
from pathlib import Path
from scripts.validate_prooflab_benchmark import validate

ROOT = Path(__file__).resolve().parents[1]

def test_all_real_prooflab_headers_match_original_source():
    result = validate()
    assert result["records"] == 61
    assert result["new_kernel_builds"] == 0
    assert result["by_split"] == {"train": 32, "evaluation": 15, "challenge": 14}

def test_full_module_level_holdout_and_no_private_proof_bodies():
    for module in ("PKPDCheck", "Workflow"):
        raw = json.loads((ROOT / "benchmarks" / "prooflab" / (module + ".json")).read_text())
        assert raw["split"] == "evaluation"
        assert all(x["split"] == "evaluation" for x in raw["records"])
    for path in (ROOT / "benchmarks" / "prooflab").glob("*.json"):
        raw = json.loads(path.read_text())
        for r in raw["records"]:
            assert ":=" not in r["statement"]
            assert "source_declared_kernel_not_attested" == r["status"]
