from __future__ import annotations

import copy
import hashlib

import pytest

from pcs.canonical_json import canonicalize_jcs
import pcs.runtime_replay_v06 as rr


def _realized(version: str = "3.12.2", numpy: str = "1.26.4") -> dict:
    value = {
        "format": rr.REALIZED_ENVIRONMENT_FORMAT_V06,
        "container": {
            "requested": "example/image@sha256:" + "a" * 64,
            "image_id": "sha256:" + "b" * 64,
            "repo_digests": ["example/image@sha256:" + "a" * 64],
            "os": "linux",
            "architecture": "amd64",
        },
        "os": {
            "system": "Linux",
            "release": "6.0",
            "architecture": "x86_64",
            "os_release": {"ID": "debian"},
        },
        "python": {
            "version": version,
            "implementation": "CPython",
            "executable": "/usr/local/bin/python",
            "executable_sha256": "c" * 64,
            "system": "Linux",
            "release": "6.0",
            "architecture": "x86_64",
            "os_release": {"ID": "debian"},
            "packages": [
                {"name": "numpy", "version": numpy, "requires": []},
                {"name": "pandas", "version": "2.2.2", "requires": ["numpy>=1.23"]},
            ],
        },
        "r": None,
        "conda": None,
        "dependency_tree_fingerprint": "d" * 64,
    }
    value["realized_environment_sha256"] = rr._canonical_sha256(value)
    return value


def _signed() -> dict:
    return {
        "python": {
            "interpreter_constraints": [
                {"source_path": ".python-version", "value": "3.12.2"}
            ],
            "dependencies": [
                {
                    "ecosystem": "python",
                    "name": "numpy",
                    "source_kind": "requirements",
                    "exact_pin": True,
                    "version": "1.26.4",
                },
                {
                    "ecosystem": "python",
                    "name": "pandas",
                    "source_kind": "pyproject_pep621",
                    "exact_pin": False,
                    "version": None,
                },
                {
                    "ecosystem": "python",
                    "name": "pytest",
                    "source_kind": "pyproject_optional:dev",
                    "exact_pin": True,
                    "version": "8.3.0",
                },
            ],
        },
        "r": {"dependencies": []},
        "conda": {"dependencies": []},
        "containers": [
            {
                "stages": [
                    {
                        "reference": "example/image@sha256:" + "a" * 64,
                        "digest_pinned": True,
                        "dynamic": False,
                    }
                ]
            }
        ],
    }


def test_sandbox_command_is_networkless_read_only_and_never_pulls(tmp_path):
    cmd = rr.sandbox_command_v06(
        runtime="docker",
        image="example/image@sha256:" + "a" * 64,
        workspace=tmp_path,
        command=["python", "analysis.py"],
        memory="2g",
        cpus=2.0,
        pids_limit=256,
    )
    joined = " ".join(cmd)
    assert "--pull=never" in joined
    assert "--network=none" in joined
    assert "--read-only" in cmd
    assert "--cap-drop=ALL" in cmd
    assert "no-new-privileges:true" in cmd
    assert "PYTHONHASHSEED=0" in cmd
    assert "SOURCE_DATE_EPOCH=0" in cmd
    assert cmd[-2:] == ["python", "analysis.py"]


def test_image_selection_requires_content_addressing():
    signed = _signed()
    assert rr.select_replay_image_v06(signed, None).endswith("a" * 64)
    with pytest.raises(rr.V06RuntimeReplayError, match="content-addressed"):
        rr.select_replay_image_v06(signed, "python:3.12")


def test_no_unsandboxed_runtime_fallback(monkeypatch):
    monkeypatch.setattr(rr.shutil, "which", lambda _: None)
    with pytest.raises(rr.V06RuntimeReplayError, match="does not fall back"):
        rr.select_oci_runtime_v06("auto")


def test_realized_environment_comparison_accepts_exact_pins_and_constraints():
    result = rr.compare_realized_environment_v06(_signed(), _realized())
    assert result["valid"] is True
    assert result["errors"] == []
    assert result["exact_dependency_projection"]["match"] is True
    pytest_row = next(
        row
        for row in result["checks"]
        if row.get("kind") == "python_dependency"
        and row.get("name") == "pytest"
    )
    assert pytest_row["enforced"] is False


def test_realized_environment_comparison_rejects_dependency_drift():
    result = rr.compare_realized_environment_v06(
        _signed(), _realized(numpy="2.0.0")
    )
    assert result["valid"] is False
    assert any("numpy" in error for error in result["errors"])
    assert result["exact_dependency_projection"]["match"] is False


def test_runtime_expectations_compare_binary_os_arch_image_and_tree():
    signed = _signed()
    signed["runtime_expectations"] = {
        "python_interpreter_sha256": "c" * 64,
        "os": "Linux",
        "architecture": "x86_64",
        "container_image_digest": "example/image@sha256:" + "a" * 64,
        "dependency_tree_fingerprint": "d" * 64,
    }
    result = rr.compare_realized_environment_v06(signed, _realized())
    assert result["valid"] is True
    compared = {
        row["kind"]: row
        for row in result["checks"]
        if row["kind"]
        in {
            "python_interpreter_binary_sha256",
            "os",
            "architecture",
            "container_image_digest",
            "full_dependency_tree_fingerprint",
        }
    }
    assert all(
        row["enforced"] is True and row["match"] is True
        for row in compared.values()
    )


def test_undeclared_runtime_values_are_captured_without_false_claim_of_match():
    result = rr.compare_realized_environment_v06(_signed(), _realized())
    by_kind = {row["kind"]: row for row in result["checks"]}
    for kind in (
        "python_interpreter_binary_sha256",
        "os",
        "architecture",
        "container_image_digest",
        "full_dependency_tree_fingerprint",
    ):
        assert by_kind[kind]["status"] == "not_declared"
        assert by_kind[kind]["enforced"] is False


def _workflow_certificate() -> dict:
    source_contract = {
        "inference_format": "pcs-static-workflow-map-v1",
        "inference_id": "W_STATIC_A_SRC",
        "static_only": True,
        "user_code_executed": False,
        "human_confirmed": True,
        "source_path": "a.py",
        "source_kind": "python",
        "dependency_claim_mode": "exact_resolved_set",
        "confidence": 0.98,
    }
    downstream_contract = {
        **source_contract,
        "inference_id": "W_STATIC_B_SRC",
        "source_path": "b.py",
    }
    return {
        "artifacts": [
            {"id": "A_SRC", "source_path": "a.py", "sha256": "1" * 64, "size": 1},
            {"id": "B_SRC", "source_path": "b.py", "sha256": "2" * 64, "size": 1},
            {"id": "MID", "source_path": "mid.csv", "sha256": "3" * 64, "size": 1},
            {"id": "OUT", "source_path": "out.csv", "sha256": "4" * 64, "size": 1},
        ],
        "workflow": {
            "nodes": [
                {
                    "id": "B",
                    "inputs": ["B_SRC", "MID"],
                    "outputs": ["OUT"],
                    "contract": {
                        "type": "external",
                        "namespace": "pcs-manifest-workflow-contract-v1",
                        "proposition": canonicalize_jcs(downstream_contract),
                    },
                },
                {
                    "id": "A",
                    "inputs": ["A_SRC"],
                    "outputs": ["MID"],
                    "contract": {
                        "type": "external",
                        "namespace": "pcs-manifest-workflow-contract-v1",
                        "proposition": canonicalize_jcs(source_contract),
                    },
                },
            ]
        },
    }


def test_workflow_execution_plan_is_topological_and_binds_signed_outputs():
    plan = rr.workflow_execution_plan_v06(_workflow_certificate())
    assert [node["id"] for node in plan] == ["A", "B"]
    assert plan[0]["output_contracts"][0]["source_path"] == "mid.csv"
    assert plan[1]["output_contracts"][0]["sha256"] == "4" * 64


def test_missing_regenerated_output_fails_even_if_it_was_in_original_package(tmp_path):
    run_root = tmp_path / "run"
    run_root.mkdir()
    (run_root / "a.py").write_text("print('x')\n", encoding="utf-8")
    baseline = {
        "A_SRC": {
            "source_path": "a.py",
            "sha256": hashlib.sha256((run_root / "a.py").read_bytes()).hexdigest(),
            "size": (run_root / "a.py").stat().st_size,
        }
    }
    plan = [
        {
            "output_contracts": [
                {
                    "artifact_id": "OUT",
                    "source_path": "out.csv",
                    "sha256": "f" * 64,
                    "size": 10,
                }
            ]
        }
    ]
    outputs, errors = rr._verify_run_outputs_v06(
        run_root=run_root,
        plan=plan,
        baseline_inputs=baseline,
    )
    assert outputs[0]["produced"] is False
    assert any("not regenerated" in error for error in errors)


def test_undeclared_file_and_input_mutation_fail_closed(tmp_path):
    run_root = tmp_path / "run"
    run_root.mkdir()
    (run_root / "input.txt").write_text("original", encoding="utf-8")
    baseline = {
        "IN": {
            "source_path": "input.txt",
            "sha256": hashlib.sha256(b"original").hexdigest(),
            "size": len(b"original"),
        }
    }
    (run_root / "input.txt").write_text("changed", encoding="utf-8")
    (run_root / "scratch.tmp").write_text("x", encoding="utf-8")
    _, errors = rr._verify_run_outputs_v06(
        run_root=run_root,
        plan=[],
        baseline_inputs=baseline,
    )
    assert any("mutated" in error for error in errors)
    assert any("undeclared workspace files" in error for error in errors)


def _fake_run(output_hash: str, env_hash: str) -> dict:
    return {
        "valid": True,
        "errors": [],
        "nodes": [],
        "realized_environment": {
            "realized_environment_sha256": env_hash
        },
        "contract_comparison": {"valid": True, "errors": []},
        "outputs": [
            {
                "artifact_id": "OUT",
                "source_path": "out.csv",
                "actual_sha256": output_hash,
                "actual_size": 10,
            }
        ],
    }


def test_top_level_requires_two_matching_independent_runs(monkeypatch, tmp_path):
    metadata = {
        "format": "pcs-environment-workspace-v1",
        "bundle_sha256": "a" * 64,
        "public_key_fingerprint": "b" * 64,
    }
    certificate = {
        "semantic_hash": "c" * 64,
        "integrity_hash": "d" * 64,
    }
    environment = _signed()
    monkeypatch.setattr(
        rr,
        "_load_verified_workspace_v06",
        lambda *args, **kwargs: (metadata, certificate, environment),
    )
    monkeypatch.setattr(
        rr, "workflow_execution_plan_v06", lambda _: [{"id": "N"}]
    )
    monkeypatch.setattr(
        rr, "select_oci_runtime_v06", lambda _: "docker"
    )
    monkeypatch.setattr(
        rr,
        "select_replay_image_v06",
        lambda *args: "example/image@sha256:" + "a" * 64,
    )
    monkeypatch.setattr(
        rr,
        "_inspect_image_v06",
        lambda *args: {"image_id": "sha256:" + "a" * 64},
    )

    same = _fake_run("1" * 64, "2" * 64)
    monkeypatch.setattr(
        rr,
        "_execute_once_v06",
        lambda **kwargs: copy.deepcopy(same),
    )
    result = rr.execute_prepared_replay_workspace_v06(
        tmp_path,
        "public.pem",
        runs=2,
    )
    assert result["valid"] is True
    assert (
        result["determinism"][
            "identical_realized_environment_and_outputs"
        ]
        is True
    )

    calls = iter(
        [
            _fake_run("1" * 64, "2" * 64),
            _fake_run("9" * 64, "2" * 64),
        ]
    )
    monkeypatch.setattr(
        rr, "_execute_once_v06", lambda **kwargs: next(calls)
    )
    result = rr.execute_prepared_replay_workspace_v06(
        tmp_path,
        "public.pem",
        runs=2,
    )
    assert result["valid"] is False
    assert any("different" in error for error in result["errors"])


def test_receipt_writer_refuses_silent_overwrite(tmp_path):
    out = tmp_path / "receipt.json"
    rr.write_runtime_replay_receipt_v06({"valid": True}, out)
    with pytest.raises(rr.V06RuntimeReplayError, match="overwrite"):
        rr.write_runtime_replay_receipt_v06(
            {"valid": False}, out
        )
