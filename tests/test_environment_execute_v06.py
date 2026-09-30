from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pcs.attest_v06 import attest_v06
from pcs.canonical_json import canonicalize_jcs
from pcs.discover_v06 import confirm_manifest_draft_v06, discover_project_v06, write_discovery_outputs_v06
from pcs.environment_execute_v06 import REALIZED_ENVIRONMENT_FORMAT_V06, SANDBOX_REPLAY_RECEIPT_FORMAT_V06, V06SandboxReplayError, execute_prepared_replay_workspace_v06
from pcs.environment_workspace_v06 import prepare_verified_environment_workspace_v06
from pcs.scaffold import init_project
from pcs.signing import generate_keypair


def _workspace(tmp_path: Path) -> tuple[Path, Path, str]:
    project = tmp_path / "study"
    init_project(project, template="pkpd", subject="sandbox-replay")
    (project / "input.txt").write_text("hello\n", encoding="utf-8")
    (project / "replayed.txt").write_text("HELLO\n", encoding="utf-8")
    (project / "analysis.py").write_text(
        "from pathlib import Path\n"
        "value = Path('input.txt').read_text(encoding='utf-8')\n"
        "Path('replayed.txt').write_text(value.upper(), encoding='utf-8')\n",
        encoding="utf-8",
    )
    (project / "requirements.txt").write_text("demo==1.0\n", encoding="utf-8")
    (project / ".python-version").write_text("3.12.2\n", encoding="utf-8")
    report = discover_project_v06(project)
    draft = project / "pcs-manifest.draft.json"
    write_discovery_outputs_v06(report, manifest_output=draft, report_output=project / "pcs-discovery.json")
    manifest = project / "manifest.json"
    confirm_manifest_draft_v06(draft, manifest, project_root=project)
    private = tmp_path / "private.pem"; public = tmp_path / "public.pem"
    fingerprint = generate_keypair(private, public)["fingerprint"]
    bundle = tmp_path / "study.pcs.zip"
    assert attest_v06(manifest, bundle, private, public, expected_fingerprint=fingerprint)["valid"] is True
    workspace = tmp_path / "workspace"
    prepared = prepare_verified_environment_workspace_v06(bundle, workspace, public, expected_fingerprint=fingerprint)
    assert prepared["valid"] is True
    meta = json.loads((workspace / "pcs-environment-workspace.json").read_text(encoding="utf-8"))
    assert meta["sandbox_execution_available"] is True
    return workspace, public, fingerprint


class _FakeBackend:
    write_mode = "correct"
    package_version = "1.0"
    mutate_input = False

    def __init__(self, *, runtime, sandbox_root, signed_environment, image, timeout_seconds, memory, cpus):
        self.runtime_name = "fake-oci"
        self.root = sandbox_root
        self.built_image = False
        self.image_meta = {"image_id":"sha256:"+"f"*64,"repo_digests":[],"os":"linux","architecture":"amd64"}

    def prepare_image(self, plan):
        return self.image_meta

    def execute_node(self, node):
        if self.mutate_input:
            (self.root / "input.txt").write_text("mutated\n", encoding="utf-8")
        if self.write_mode != "missing":
            value = "HELLO\n" if self.write_mode == "correct" else "WRONG\n"
            for output in node["outputs"]:
                p = self.root / output["source_path"]; p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(value, encoding="utf-8")
        empty = hashlib.sha256(b"").hexdigest()
        return {"command":["fake",node["source_path"]],"exit_code":0,"stdout":"","stderr":"",
                "stdout_sha256":empty,"stderr_sha256":empty,"stdout_truncated":False,"stderr_truncated":False}

    def capture_environment(self):
        tree = {"python":[{"name":"demo","version":self.package_version,"requires":[]}],"r":[],"conda":[]}
        value = {"format":REALIZED_ENVIRONMENT_FORMAT_V06,
                 "python":{"implementation":"CPython","version":"3.12.2","executable":"/usr/bin/python",
                           "executable_sha256":"a"*64,"packages":tree["python"],"packages_truncated":False},
                 "r":{"version":None,"packages":[],"executable_sha256":None},
                 "conda":{"packages":[]},"platform":{"probe":"Linux test","image_os":"linux","image_architecture":"amd64"},
                 "container_image":self.image_meta,
                 "dependency_tree_sha256":hashlib.sha256(canonicalize_jcs(tree).encode()).hexdigest()}
        value["semantic_sha256"] = hashlib.sha256(canonicalize_jcs(value).encode()).hexdigest()
        return value

    def close(self):
        pass


def _execute(tmp_path: Path, backend):
    workspace, public, fingerprint = _workspace(tmp_path)
    out = tmp_path / "result"
    result = execute_prepared_replay_workspace_v06(
        workspace, out, public, expected_fingerprint=fingerprint, _backend_factory=backend
    )
    receipt = json.loads((out / "pcs-replay-execution.json").read_text(encoding="utf-8"))
    realized = json.loads((out / "pcs-realized-environment.json").read_text(encoding="utf-8"))
    return workspace, out, result, receipt, realized


def test_replay_removes_stale_output_recreates_exact_bytes_and_captures_realized_state(tmp_path):
    class Backend(_FakeBackend): pass
    workspace, out, result, receipt, realized = _execute(tmp_path, Backend)
    assert result["valid"] is True
    assert receipt["format"] == SANDBOX_REPLAY_RECEIPT_FORMAT_V06
    assert receipt["preexisting_outputs"][0]["preexisting_signed_output_removed"] is True
    assert receipt["workflow_outputs"][0]["status"] == "match"
    assert receipt["environment_comparison"]["enforceable_contract_match"] is True
    assert receipt["environment_comparison"]["interpreter_binary_hash"]["python_sha256"] == "a"*64
    assert realized["platform"]["image_architecture"] == "amd64"
    assert len(realized["dependency_tree_sha256"]) == 64
    assert (out / "outputs" / "replayed.txt").read_text(encoding="utf-8") == "HELLO\n"
    assert (workspace / "replayed.txt").read_text(encoding="utf-8") == "HELLO\n"


def test_stale_signed_output_cannot_mask_missing_reexecution_output(tmp_path):
    class Backend(_FakeBackend): write_mode = "missing"
    _, _, result, receipt, _ = _execute(tmp_path, Backend)
    assert result["valid"] is False
    assert receipt["workflow_outputs"][0]["status"] == "missing"


def test_replayed_output_byte_divergence_fails_closed(tmp_path):
    class Backend(_FakeBackend): write_mode = "wrong"
    _, _, result, receipt, _ = _execute(tmp_path, Backend)
    assert result["valid"] is False
    assert receipt["workflow_outputs"][0]["status"] == "mismatch"


def test_signed_input_mutation_fails_closed(tmp_path):
    class Backend(_FakeBackend): mutate_input = True
    _, _, result, receipt, _ = _execute(tmp_path, Backend)
    assert result["valid"] is False
    assert receipt["non_output_artifact_mutations"]


def test_realized_dependency_version_drift_fails_contract_comparison(tmp_path):
    class Backend(_FakeBackend): package_version = "2.0"
    _, _, result, receipt, _ = _execute(tmp_path, Backend)
    assert result["valid"] is False
    row = next(x for x in receipt["environment_comparison"]["signed_exact_packages"] if x["name"] == "demo")
    assert row["expected"] == "1.0"
    assert row["realized"] == "2.0"
    assert row["status"] == "version_mismatch"


def test_workspace_control_path_escape_is_rejected(tmp_path):
    workspace, public, fingerprint = _workspace(tmp_path)
    meta_path = workspace / "pcs-environment-workspace.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["signed_certificate"] = "../outside.json"
    meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(V06SandboxReplayError, match="unsafe project-relative path"):
        execute_prepared_replay_workspace_v06(
            workspace,
            tmp_path / "result",
            public,
            expected_fingerprint=fingerprint,
            _backend_factory=_FakeBackend,
        )


def test_tampered_execution_plan_is_rederived_from_signed_certificate(tmp_path):
    workspace, public, fingerprint = _workspace(tmp_path)
    meta_path = workspace / "pcs-environment-workspace.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    plan_path = workspace / meta["sandbox_execution_plan"]
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["sandbox_policy"]["network"] = "host"
    plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    meta["sandbox_execution_plan_sha256"] = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(V06SandboxReplayError, match="differs from signed certificate"):
        execute_prepared_replay_workspace_v06(
            workspace,
            tmp_path / "result",
            public,
            expected_fingerprint=fingerprint,
            _backend_factory=_FakeBackend,
        )


def test_replay_created_symlink_output_is_rejected_without_following_it(tmp_path):
    class Backend(_FakeBackend):
        def execute_node(self, node):
            for output in node["outputs"]:
                p = self.root / output["source_path"]
                p.parent.mkdir(parents=True, exist_ok=True)
                p.symlink_to("input.txt")
            empty = hashlib.sha256(b"").hexdigest()
            return {
                "command": ["fake", node["source_path"]],
                "exit_code": 0,
                "stdout": "",
                "stderr": "",
                "stdout_sha256": empty,
                "stderr_sha256": empty,
                "stdout_truncated": False,
                "stderr_truncated": False,
            }

    _, out, result, receipt, _ = _execute(tmp_path, Backend)
    assert result["valid"] is False
    assert receipt["workflow_outputs"][0]["status"] == "unsafe_symlink"
    assert receipt["unsafe_symlinks"] == ["replayed.txt"]
    assert receipt["verdict"]["filesystem_contains_no_symlinks"] is False
    assert not (out / "outputs" / "replayed.txt").exists()
