from __future__ import annotations

import json
import tempfile
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pcs.bundle_verify import verify_bundle
from pcs.cli import cmd_bundle
from pcs.environment import (
    diff_environments,
    snapshot_environment,
    validate_environment,
    write_environment,
)
from pcs.kernel import build_certificate


def test_runtime_snapshot_is_deterministic_and_valid():
    left = snapshot_environment()
    right = snapshot_environment()
    assert validate_environment(left)["valid"]
    assert validate_environment(right)["valid"]
    assert left["semantic_hash"] == right["semantic_hash"]
    assert left["packages"] == sorted(left["packages"], key=lambda x: x["name"])


def test_runtime_snapshot_contains_no_environment_variables():
    snapshot = snapshot_environment()
    encoded = json.dumps(snapshot)
    assert "environment_variables" not in snapshot
    assert "env" not in snapshot
    assert "PATH=" not in encoded


def test_environment_diff_detects_package_change_and_rejects_tamper():
    left = snapshot_environment()
    right = deepcopy(left)
    right["packages"] = deepcopy(right["packages"])
    right["packages"].append({"name": "zz-test-package", "version": "1.0"})
    right["packages"].sort(key=lambda x: x["name"])
    from pcs.environment import runtime_semantic_hash
    right["semantic_hash"] = runtime_semantic_hash(right)

    diff = diff_environments(left, right)
    assert diff["packages_added"] == {"zz-test-package": "1.0"}
    assert not diff["same_semantic_hash"]

    tampered = deepcopy(right)
    tampered["python"]["version"] = "forged"
    try:
        diff_environments(left, tampered)
    except ValueError as exc:
        assert "semantic hash mismatch" in str(exc)
    else:
        raise AssertionError("tampered runtime snapshot should be rejected")


def test_attestation_bundle_binds_runtime_snapshot():
    from pcs.attest import attest
    from pcs.scaffold import init_project
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        project = root / "project"
        init_project(project)
        result = attest(project / "manifest.json", root / "evidence")
        runtime_path = root / "evidence" / "runtime.json"
        assert runtime_path.is_file()
        runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
        assert validate_environment(runtime)["valid"]
        manifest = result["package_manifest"]
        assert "runtime.json" in manifest["files"]
        assert "LIMITATIONS.md" in manifest["files"]
        limitations = (root / "evidence" / "LIMITATIONS.md").read_text(encoding="utf-8")
        assert "does not by itself establish" in limitations
        assert "clinical safety" in limitations
        assert result["semantic_hash"] in limitations
        verified = verify_bundle(result["bundle"]["bundle"])
        assert verified["valid"], verified["errors"]


def test_low_level_bundle_command_builds_required_package_manifest():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        source = Path(__file__).resolve().parents[1] / "examples" / "biopharma_demo"
        evidence = root / "evidence"
        build_certificate(source / "manifest.json", evidence)
        output = root / "bundle.zip"
        rc = cmd_bundle(SimpleNamespace(certificate=str(evidence / "certificate.json"), output=str(output)))
        assert rc == 0
        assert (evidence / "package_manifest.json").is_file()
        verified = verify_bundle(output)
        assert verified["valid"], verified["errors"]


def test_attestation_refuses_runtime_drift():
    from pcs.attest import attest, AttestationError
    from pcs.environment import snapshot_environment, runtime_semantic_hash
    from pcs.scaffold import init_project

    before = snapshot_environment()
    after = deepcopy(before)
    after["python"] = deepcopy(after["python"])
    after["python"]["version"] = "changed-during-attestation"
    after["semantic_hash"] = runtime_semantic_hash(after)

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        project = root / "project"
        init_project(project)
        with patch("pcs.attest.snapshot_environment", side_effect=[before, after]):
            try:
                attest(project / "manifest.json", root / "evidence")
            except AttestationError as exc:
                assert "runtime environment changed during attestation" in str(exc)
            else:
                raise AssertionError("runtime drift should prevent attestation")
        assert not (root / "evidence.zip").exists()
