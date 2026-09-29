from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

from pcs.attest_v06 import attest_v06
from pcs.discover_v06 import (
    confirm_manifest_draft_v06,
    discover_project_v06,
    write_discovery_outputs_v06,
)
from pcs.environment_v06 import (
    ENVIRONMENT_CAPTURE_FORMAT_V06,
    ENVIRONMENT_REPLAY_PLAN_FORMAT_V06,
    capture_environment_v06,
    render_environment_replay_script_v06,
)
from pcs.scaffold import init_project
from pcs.signing import generate_keypair


ROOT = Path(__file__).resolve().parents[1]


def _inventory(root: Path, paths: list[str]) -> list[dict]:
    out = []
    for index, rel in enumerate(paths):
        raw = (root / rel).read_bytes()
        out.append(
            {
                "artifact_id": f"A{index}",
                "path": rel,
                "size": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "media_type": "application/octet-stream",
                "role": "environment-specification",
            }
        )
    return out


def _keys(tmp_path: Path) -> tuple[Path, Path, str]:
    private = tmp_path / "private.pem"
    public = tmp_path / "public.pem"
    result = generate_keypair(private, public)
    return private, public, result["fingerprint"]


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pcs.cli", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_capture_python_r_conda_lockfiles_interpreters_and_digest_pinned_container(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        "[project]\n"
        "name='demo'\n"
        "version='0.1.0'\n"
        "requires-python='>=3.11,<3.13'\n"
        "dependencies=['numpy==1.26.4','pandas>=2.2']\n"
        "[build-system]\n"
        "requires=['setuptools>=68']\n"
        "build-backend='setuptools.build_meta'\n",
        encoding="utf-8",
    )
    (project / ".python-version").write_text("3.12.2\n", encoding="utf-8")
    (project / "uv.lock").write_text(
        "version = 1\n"
        "[[package]]\n"
        "name = 'numpy'\n"
        "version = '1.26.4'\n"
        "[package.sdist]\n"
        "url = 'https://example.invalid/numpy.tar.gz'\n"
        "hash = 'sha256:abc'\n",
        encoding="utf-8",
    )
    (project / "renv.lock").write_text(
        json.dumps(
            {
                "R": {"Version": "4.4.1"},
                "Packages": {
                    "jsonlite": {
                        "Package": "jsonlite",
                        "Version": "1.8.8",
                        "Source": "Repository",
                        "Repository": "CRAN",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    (project / "DESCRIPTION").write_text(
        "Package: demo\n"
        "Version: 0.1.0\n"
        "Depends: R (>= 4.3.0)\n"
        "Imports: jsonlite (== 1.8.8)\n",
        encoding="utf-8",
    )
    (project / "environment.yml").write_text(
        "name: demo\n"
        "dependencies:\n"
        "  - python=3.12\n"
        "  - numpy=1.26.4\n"
        "  - pip:\n"
        "    - scipy==1.12.0\n",
        encoding="utf-8",
    )
    digest = "a" * 64
    (project / "Dockerfile").write_text(
        f"FROM python:3.12-slim@sha256:{digest}\n"
        "COPY . /app\n"
        "RUN pip install -r requirements.txt\n",
        encoding="utf-8",
    )
    (project / "requirements.txt").write_text(
        "numpy==1.26.4 --hash=sha256:" + "b" * 64 + "\n",
        encoding="utf-8",
    )

    paths = [
        "pyproject.toml",
        ".python-version",
        "uv.lock",
        "renv.lock",
        "DESCRIPTION",
        "environment.yml",
        "Dockerfile",
        "requirements.txt",
    ]
    result = capture_environment_v06(project, _inventory(project, paths))

    assert result["format"] == ENVIRONMENT_CAPTURE_FORMAT_V06
    assert result["static_only"] is True
    assert result["network_accessed"] is False
    assert result["user_code_executed"] is False
    assert result["hermeticity"] == "strongly_pinned"
    assert {x["value"] for x in result["python"]["interpreter_constraints"]} >= {
        ">=3.11,<3.13",
        "3.12.2",
        "3.12",
    }
    assert {x["value"] for x in result["r"]["interpreter_constraints"]} >= {
        "4.4.1",
        ">= 4.3.0",
    }
    assert any(
        d["name"] == "numpy" and d["exact_pin"]
        for d in result["python"]["dependencies"]
    )
    assert any(
        d["name"] == "jsonlite" and d["exact_pin"]
        for d in result["r"]["dependencies"]
    )
    assert any(
        d["name"] == "numpy" and d["ecosystem"] == "conda"
        for d in result["conda"]["dependencies"]
    )
    assert result["containers"][0]["all_base_images_digest_pinned"] is True
    plan = result["replay_plan"]
    assert plan["format"] == ENVIRONMENT_REPLAY_PLAN_FORMAT_V06
    assert plan["steps"][0]["kind"] == "container_build"
    assert plan["automatic_execution_permitted_by_pcs"] is False


def test_hash_pinned_requirements_are_stronger_than_loose_requirements(tmp_path):
    pinned = tmp_path / "pinned"
    pinned.mkdir()
    (pinned / "requirements.txt").write_text(
        "numpy==1.26.4 --hash=sha256:" + "c" * 64 + "\n",
        encoding="utf-8",
    )
    pinned_capture = capture_environment_v06(
        pinned,
        _inventory(pinned, ["requirements.txt"]),
    )
    assert pinned_capture["hermeticity"] == "hash_pinned_dependencies"
    assert "--require-hashes" in pinned_capture["replay_plan"]["steps"][0][
        "command_template"
    ]

    loose = tmp_path / "loose"
    loose.mkdir()
    (loose / "requirements.txt").write_text(
        "numpy>=1.26\npandas\n",
        encoding="utf-8",
    )
    loose_capture = capture_environment_v06(
        loose,
        _inventory(loose, ["requirements.txt"]),
    )
    assert loose_capture["hermeticity"] == "declared_dependencies"
    assert "--require-hashes" not in loose_capture["replay_plan"]["steps"][0][
        "command_template"
    ]


def test_dynamic_container_base_is_reported_not_upgraded_to_digest_pinned(tmp_path):
    project = tmp_path / "container"
    project.mkdir()
    (project / "Dockerfile").write_text(
        "ARG BASE=python:3.12-slim\n"
        "FROM $BASE\n",
        encoding="utf-8",
    )
    result = capture_environment_v06(
        project,
        _inventory(project, ["Dockerfile"]),
    )

    assert result["containers"][0]["all_base_images_digest_pinned"] is False
    assert result["hermeticity"] == "environment_unspecified"
    assert any(x["type"] == "dynamic_container_base" for x in result["unresolved"])


def test_reconstruction_script_is_review_before_run_and_never_auto_executed(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "requirements.txt").write_text("numpy==1.26.4\n", encoding="utf-8")
    environment = capture_environment_v06(
        project,
        _inventory(project, ["requirements.txt"]),
    )

    script = render_environment_replay_script_v06(environment)

    assert "REVIEW BEFORE EXECUTION" in script
    assert "PCS verification never runs this script automatically" in script
    assert "python -m pip install" in script
    assert environment["replay_plan"]["automatic_execution_permitted_by_pcs"] is False


def test_guided_discovery_selects_environment_sources_and_confirmation_binds_them(tmp_path):
    project = tmp_path / "study"
    init_project(project, template="pkpd", subject="environment-aware-study")
    (project / "requirements.txt").write_text(
        "numpy==1.26.4 --hash=sha256:" + "d" * 64 + "\n",
        encoding="utf-8",
    )
    (project / ".python-version").write_text("3.12.2\n", encoding="utf-8")

    report = discover_project_v06(project)
    manifest = report["manifest_draft"]

    assert report["environment_capture"]["format"] == ENVIRONMENT_CAPTURE_FORMAT_V06
    assert report["summary"]["environment_sources"] == 2
    assert manifest["environment"]["human_confirmed"] is False
    paths = {a["path"] for a in manifest["artifacts"]}
    assert "requirements.txt" in paths
    assert ".python-version" in paths

    draft = project / "pcs-manifest.draft.json"
    write_discovery_outputs_v06(
        report,
        manifest_output=draft,
        report_output=project / "pcs-discovery.json",
    )
    confirmed_path = project / "manifest.json"
    confirm_manifest_draft_v06(
        draft,
        confirmed_path,
        project_root=project,
    )
    confirmed = json.loads(confirmed_path.read_text(encoding="utf-8"))
    assert confirmed["environment"]["human_confirmed"] is True
    assert confirmed["pcs_intake"]["environment_confirmed"] is True


def test_full_attestation_binds_environment_and_verifier_replays_it(tmp_path):
    project = tmp_path / "study"
    init_project(project, template="pkpd", subject="environment-aware-study")
    (project / "requirements.txt").write_text(
        "numpy==1.26.4 --hash=sha256:" + "e" * 64 + "\n",
        encoding="utf-8",
    )
    (project / ".python-version").write_text("3.12.2\n", encoding="utf-8")

    report = discover_project_v06(project)
    draft = project / "pcs-manifest.draft.json"
    write_discovery_outputs_v06(
        report,
        manifest_output=draft,
        report_output=project / "pcs-discovery.json",
    )
    manifest = project / "manifest.json"
    confirm_manifest_draft_v06(draft, manifest, project_root=project)

    private, public, fingerprint = _keys(tmp_path)
    bundle = tmp_path / "study.pcs.zip"
    result = attest_v06(
        manifest,
        bundle,
        private,
        public,
        expected_fingerprint=fingerprint,
    )

    assert result["valid"] is True
    with zipfile.ZipFile(bundle, "r") as zf:
        certificate = json.loads(zf.read("certificate.json").decode("utf-8"))
    assert certificate["environment"]["format"] == "pcs-environment-binding-v1"
    assert certificate["environment"]["source_artifact_ids"]
    proposition = json.loads(certificate["environment"]["contract"]["proposition"])
    assert proposition["human_confirmed"] is True
    assert proposition["hermeticity"] == "hash_pinned_dependencies"


def test_environment_plan_cli_reads_discovery_and_writes_plan_and_script(tmp_path):
    project = tmp_path / "study"
    init_project(project, template="pkpd", subject="environment-plan-cli")
    (project / "requirements.txt").write_text("numpy==1.26.4\n", encoding="utf-8")

    discover = _run("discover-v06", str(project))
    assert discover.returncode == 0, discover.stdout + discover.stderr
    discovered = json.loads(discover.stdout)
    assert Path(discovered["environment_plan"]).exists()

    output = tmp_path / "plan.json"
    script = tmp_path / "reconstruct.sh"
    proc = _run(
        "environment-plan-v06",
        str(project / "pcs-discovery.json"),
        "-o",
        str(output),
        "--script",
        str(script),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    result = json.loads(proc.stdout)
    assert result["automatic_execution_permitted_by_pcs"] is False
    assert json.loads(output.read_text(encoding="utf-8"))["format"] == (
        ENVIRONMENT_REPLAY_PLAN_FORMAT_V06
    )
    assert "REVIEW BEFORE EXECUTION" in script.read_text(encoding="utf-8")
