import re
from scripts.export_prooflab_source_proofs import extract, proof_text_from_source

def test_real_lean_proofs_can_be_extracted_privately_without_fake_kernel_labels():
    data = extract("train")
    assert data["format"] == "pcs-prooflab-private-source-proof-corpus-v1"
    assert len(data["records"]) == 32
    assert all(r["raw_source_proof"].strip() for r in data["records"])
    assert all(not r["kernel_verified_in_this_export"] for r in data["records"])
    assert all(re.fullmatch("[a-f0-9]{64}",r["proof_sha256"]) for r in data["records"])

def test_private_evaluation_module_proofs_are_not_training_rows():
    evaluation = extract("evaluation")
    assert len(evaluation["records"]) == 15
    assert {r["module"] for r in evaluation["records"]} == {"PKPDCheck", "Workflow"}
    assert not {r["id"] for r in evaluation["records"]} & {
        r["id"] for r in extract("train")["records"]
    }
