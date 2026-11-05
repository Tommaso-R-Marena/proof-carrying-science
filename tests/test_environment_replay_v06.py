from __future__ import annotations

import hashlib
from pathlib import Path

from pcs.canonical_json import canonicalize_jcs
from pcs.environment_replay_v06 import (
    environment_binding_v06,
    verify_environment_replay_v06,
)
from pcs.environment_v06 import capture_environment_v06


def _fixture(tmp_path: Path):
    root = tmp_path / "project"
    root.mkdir()
    req = root / "requirements.txt"
    req.write_text(
        "numpy==1.26.4 --hash=sha256:" + "a" * 64 + "\n",
        encoding="utf-8",
    )
    raw = req.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    inventory = [
        {
            "artifact_id": "A_REQ",
            "path": "requirements.txt",
            "size": len(raw),
            "sha256": digest,
            "media_type": "text/plain",
            "role": "environment-specification",
        }
    ]
    environment = capture_environment_v06(root, inventory)
    environment["human_confirmed"] = True
    environment["confirmation_scope"] = "reviewed"
    binding = environment_binding_v06(environment)
    certificate = {
        "artifacts": [
            {
                "id": "A_REQ",
                "path": "artifacts/req/payload",
                "role": "environment-specification",
                "sha256": digest,
                "media_type": "text/plain",
                "source_path": "requirements.txt",
            }
        ],
        "environment": binding,
    }
    package_files = {"artifacts/req/payload": raw}
    return certificate, package_files, environment


def test_environment_replay_accepts_freshly_rederived_contract(tmp_path):
    certificate, package_files, _ = _fixture(tmp_path)

    result = verify_environment_replay_v06(certificate, package_files)

    assert result["valid"] is True
    assert result["mode"] == "static-environment-rederived"
    assert result["hermeticity"] == "hash_pinned_dependencies"
    assert result["source_files_checked"] == 1
    assert result["dependency_records"] == 1
    assert result["replay_plan"]["automatic_execution_permitted_by_pcs"] is False


def test_environment_replay_rejects_forged_dependency_claim(tmp_path):
    certificate, package_files, environment = _fixture(tmp_path)
    forged = dict(environment)
    forged["python"] = {
        **environment["python"],
        "dependencies": [
            {
                **environment["python"]["dependencies"][0],
                "version": "9.9.9",
                "raw": "numpy==9.9.9",
            }
        ],
    }
    forged_binding = environment_binding_v06(forged)
    certificate = dict(certificate)
    certificate["environment"] = forged_binding

    result = verify_environment_replay_v06(certificate, package_files)

    assert result["valid"] is False
    assert result["errors"]
    assert "differs from fresh capture" in result["errors"][0]


def test_environment_replay_rejects_forged_interpreter_constraint(tmp_path):
    certificate, package_files, environment = _fixture(tmp_path)
    forged = dict(environment)
    forged["python"] = {
        **environment["python"],
        "interpreter_constraints": [
            {"source_path": ".python-version", "value": "9.9.9"}
        ],
    }
    forged_binding = environment_binding_v06(forged)
    certificate = dict(certificate)
    certificate["environment"] = forged_binding

    result = verify_environment_replay_v06(certificate, package_files)

    assert result["valid"] is False


def test_environment_replay_rejects_missing_environment_artifact(tmp_path):
    certificate, package_files, _ = _fixture(tmp_path)

    result = verify_environment_replay_v06(certificate, {})

    assert result["valid"] is False
    assert "missing bytes" in result["errors"][0]


def test_environment_replay_requires_human_confirmation(tmp_path):
    certificate, package_files, environment = _fixture(tmp_path)
    unconfirmed = dict(environment)
    unconfirmed["human_confirmed"] = False
    certificate = dict(certificate)
    certificate["environment"] = {
        "format": "pcs-environment-binding-v1",
        "source_artifact_ids": ["A_REQ"],
        "contract": {
            "type": "external",
            "namespace": "pcs-manifest-environment-contract-v1",
            "proposition": canonicalize_jcs(unconfirmed),
        },
    }

    result = verify_environment_replay_v06(certificate, package_files)

    assert result["valid"] is False
    assert "human-confirmed" in result["errors"][0]


def test_environment_replay_absent_contract_is_backward_compatible():
    result = verify_environment_replay_v06({"artifacts": []}, {})

    assert result["valid"] is True
    assert result["mode"] == "no-environment-contract"
    assert result["source_files_checked"] == 0
