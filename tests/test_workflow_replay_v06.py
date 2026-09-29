from __future__ import annotations

import hashlib

from pcs.canonical_json import canonicalize_jcs
from pcs.workflow_replay_v06 import verify_static_workflow_replay_v06


SCRIPT = (
    b"import pandas as pd\n"
    b"df = pd.read_csv('input.csv')\n"
    b"df.to_csv('output.csv', index=False)\n"
)
INPUT = b"id,x\n1,1\n"
OUTPUT = b"id,x\n1,1\n"


def _artifact(ident: str, package_path: str, source_path: str, raw: bytes, role: str):
    return {
        "id": ident,
        "path": package_path,
        "role": role,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "media_type": "text/plain",
        "source_path": source_path,
    }


def _certificate(*, outputs: list[str], human_confirmed: bool = True):
    proposition = {
        "inference_format": "pcs-static-workflow-map-v1",
        "inference_id": "W_STATIC_wf_source",
        "static_only": True,
        "user_code_executed": False,
        "human_confirmed": human_confirmed,
        "confirmation_scope": (
            "Static dependency inference confirmed; this does not prove "
            "source-code correctness or runtime behavior."
        ),
        "source_path": "pipeline.py",
        "source_kind": "python",
        "analysis_mode": "python_ast",
        "dependency_claim_mode": "exact_resolved_set",
        "confidence": 0.98,
        "imports": ["pandas"],
        "resolved_references": [],
        "references_truncated": True,
    }
    return {
        "artifacts": [
            _artifact(
                "wf_source",
                "artifacts/wf_source/payload",
                "pipeline.py",
                SCRIPT,
                "source-code",
            ),
            _artifact(
                "wf_input",
                "artifacts/wf_input/payload",
                "input.csv",
                INPUT,
                "tabular-data",
            ),
            _artifact(
                "wf_output",
                "artifacts/wf_output/payload",
                "output.csv",
                OUTPUT,
                "tabular-output",
            ),
        ],
        "workflow": {
            "nodes": [
                {
                    "id": "N_STATIC_wf_source",
                    "operation": "static_python_workflow",
                    "inputs": ["wf_input", "wf_source"],
                    "outputs": outputs,
                    "contract": {
                        "type": "external",
                        "namespace": "pcs-manifest-workflow-contract-v1",
                        "proposition": canonicalize_jcs(proposition),
                    },
                }
            ]
        },
    }


def _files():
    return {
        "artifacts/wf_source/payload": SCRIPT,
        "artifacts/wf_input/payload": INPUT,
        "artifacts/wf_output/payload": OUTPUT,
    }


def test_static_workflow_replay_accepts_exact_dependency_claim():
    result = verify_static_workflow_replay_v06(
        _certificate(outputs=["wf_output"]),
        _files(),
    )

    assert result["valid"], result["errors"]
    assert result["nodes_checked"] == 1
    assert result["mode"] == "static-source-replay"
    assert result["details"][0]["reproduced"] is True
    assert result["details"][0]["fresh_inputs"] == ["wf_input", "wf_source"]
    assert result["details"][0]["fresh_outputs"] == ["wf_output"]


def test_static_workflow_replay_rejects_forged_output_edge():
    result = verify_static_workflow_replay_v06(
        _certificate(outputs=["wf_input"]),
        _files(),
    )

    assert result["valid"] is False
    assert result["nodes_checked"] == 1
    assert any("output set differs" in error for error in result["errors"])


def test_static_workflow_replay_requires_human_confirmation():
    result = verify_static_workflow_replay_v06(
        _certificate(outputs=["wf_output"], human_confirmed=False),
        _files(),
    )

    assert result["valid"] is False
    assert any("human_confirmed=True" in error for error in result["errors"])
