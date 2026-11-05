from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from pcs.attest_v06 import V06AttestationError, attest_v06
from pcs.discover_v06 import (
    confirm_manifest_draft_v06,
    discover_project_v06,
    write_discovery_outputs_v06,
)
from pcs.scaffold import init_project
from pcs.signing import generate_keypair
from pcs.workflow_discovery_v06 import (
    WORKFLOW_DISCOVERY_FORMAT_V06,
    analyze_static_workflow_v06,
)


def _inventory_for(root: Path, paths: list[str]) -> list[dict]:
    out = []
    for index, rel in enumerate(paths):
        p = root / rel
        out.append(
            {
                "artifact_id": f"artifact_{index}",
                "path": rel,
                "size": p.stat().st_size,
                "sha256": "0" * 64,
                "media_type": "application/octet-stream",
                "role": "scientific-artifact",
            }
        )
    return out


def _keys(tmp_path: Path) -> tuple[Path, Path, str]:
    private = tmp_path / "private.pem"
    public = tmp_path / "public.pem"
    result = generate_keypair(private, public)
    return private, public, result["fingerprint"]


def test_static_python_analysis_resolves_constants_pathlib_and_dataframe_writes(tmp_path):
    project = tmp_path / "project"
    (project / "data").mkdir(parents=True)
    (project / "data" / "train.csv").write_text("id,x\n1,2\n", encoding="utf-8")
    (project / "result.csv").write_text("id,y\n1,3\n", encoding="utf-8")
    (project / "pipeline.py").write_text(
        "from pathlib import Path\n"
        "import pandas as pd\n"
        "DATA = Path('data') / 'train.csv'\n"
        "OUT = 'result.csv'\n"
        "df = pd.read_csv(DATA)\n"
        "df.to_csv(OUT, index=False)\n",
        encoding="utf-8",
    )
    inventory = _inventory_for(
        project,
        ["data/train.csv", "result.csv", "pipeline.py"],
    )

    result = analyze_static_workflow_v06(project, inventory)

    assert result["format"] == WORKFLOW_DISCOVERY_FORMAT_V06
    assert result["static_only"] is True
    assert result["user_code_executed"] is False
    assert result["summary"]["source_files_with_resolved_dependencies"] == 1
    source = result["sources"][0]
    assert source["reads"] == ["artifact_0"]
    assert source["writes"] == ["artifact_1"]
    assert source["confidence"] == 0.98
    node = result["nodes"][0]
    assert node["inputs"] == ["artifact_0", "artifact_2"]
    assert node["outputs"] == ["artifact_1"]
    assert node["contract"]["static_only"] is True
    assert node["contract"]["user_code_executed"] is False
    assert node["contract"]["inference_id"] == source["id"]


def test_static_discovery_never_executes_user_python(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    sentinel = project / "SHOULD_NOT_EXIST"
    (project / "input.csv").write_text("id,x\n1,2\n", encoding="utf-8")
    (project / "output.csv").write_text("id,x\n1,2\n", encoding="utf-8")
    (project / "danger.py").write_text(
        "from pathlib import Path\n"
        "Path('SHOULD_NOT_EXIST').write_text('executed')\n"
        "import pandas as pd\n"
        "df = pd.read_csv('input.csv')\n"
        "df.to_csv('output.csv')\n"
        "raise RuntimeError('must never execute')\n",
        encoding="utf-8",
    )
    inventory = _inventory_for(
        project,
        ["input.csv", "output.csv", "danger.py"],
    )

    result = analyze_static_workflow_v06(project, inventory)

    assert result["summary"]["source_files_with_resolved_dependencies"] == 1
    assert not sentinel.exists()


def test_dynamic_source_paths_are_reported_not_guessed(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "known.csv").write_text("id,x\n1,2\n", encoding="utf-8")
    (project / "dynamic.py").write_text(
        "import pandas as pd\n"
        "path = input('file? ')\n"
        "df = pd.read_csv(path)\n",
        encoding="utf-8",
    )
    inventory = _inventory_for(project, ["known.csv", "dynamic.py"])

    result = analyze_static_workflow_v06(project, inventory)

    assert result["summary"]["source_files_with_resolved_dependencies"] == 0
    unresolved = [
        item
        for item in result["unresolved"]
        if item["type"] == "unresolved_source_references"
    ]
    assert len(unresolved) == 1
    ref = unresolved[0]["references"][0]
    assert ref["resolution"] == "dynamic"
    assert ref["path"] is None


def test_multiple_static_producers_are_not_emitted_as_conflicting_workflow_outputs(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "input.csv").write_text("id,x\n1,2\n", encoding="utf-8")
    (project / "output.csv").write_text("id,x\n1,2\n", encoding="utf-8")
    for name in ("a.py", "b.py"):
        (project / name).write_text(
            "import pandas as pd\n"
            "df = pd.read_csv('input.csv')\n"
            "df.to_csv('output.csv')\n",
            encoding="utf-8",
        )
    inventory = _inventory_for(
        project,
        ["input.csv", "output.csv", "a.py", "b.py"],
    )

    result = analyze_static_workflow_v06(project, inventory)

    conflicts = [
        item for item in result["unresolved"]
        if item["type"] == "multiple_static_producers"
    ]
    assert len(conflicts) == 1
    assert conflicts[0]["artifact_id"] == "artifact_1"
    assert all("artifact_1" not in node["outputs"] for node in result["nodes"])


def test_jupyter_code_cells_create_static_workflow_node(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "train.csv").write_text("id,x\n1,2\n", encoding="utf-8")
    (project / "processed.csv").write_text("id,x\n1,2\n", encoding="utf-8")
    notebook = {
        "cells": [
            {
                "cell_type": "code",
                "metadata": {},
                "source": [
                    "import pandas as pd\n",
                    "df = pd.read_csv('train.csv')\n",
                    "df.to_csv('processed.csv', index=False)\n",
                ],
                "outputs": [],
                "execution_count": None,
            }
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    (project / "analysis.ipynb").write_text(
        json.dumps(notebook),
        encoding="utf-8",
    )
    inventory = _inventory_for(
        project,
        ["train.csv", "processed.csv", "analysis.ipynb"],
    )

    result = analyze_static_workflow_v06(project, inventory)

    assert result["summary"]["workflow_nodes"] == 1
    source = result["sources"][0]
    assert source["source_kind"] == "jupyter"
    assert source["reads"] == ["artifact_0"]
    assert source["writes"] == ["artifact_1"]
    locations = [
        ref["location"]
        for ref in source["resolved_references"]
    ]
    assert any(location.startswith("cell[0]:") for location in locations)


def test_guided_discovery_merges_static_workflow_with_pkpd_checks_without_duplicate_producer(tmp_path):
    project = tmp_path / "pkpd"
    init_project(project, template="pkpd", subject="workflow-aware-pkpd")
    (project / "generate.py").write_text(
        "import json\n"
        "import pandas as pd\n"
        "model = json.load(open('model.json'))\n"
        "df = pd.read_csv('predictions.csv')\n"
        "df.to_csv('predictions.csv', index=False)\n",
        encoding="utf-8",
    )

    report = discover_project_v06(project, minimum_workflow_confidence=0.90)
    manifest = report["manifest_draft"]

    assert report["summary"]["workflow_sources_analyzed"] == 1
    assert report["summary"]["workflow_nodes_drafted"] == 1
    assert report["workflow_map"]["static_only"] is True
    assert len(manifest["workflow"]["nodes"]) == 1
    node = manifest["workflow"]["nodes"][0]
    assert node["operation"] == "static_python_workflow"
    assert any(
        artifact["path"] == "generate.py"
        for artifact in manifest["artifacts"]
    )
    # predictions.csv must have only one workflow producer.
    producers = [
        node["id"]
        for node in manifest["workflow"]["nodes"]
        if any(
            artifact["id"] in node["outputs"]
            for artifact in manifest["artifacts"]
            if artifact["path"] == "predictions.csv"
        )
    ]
    assert len(producers) == 1


def test_confirmed_static_workflow_provenance_survives_full_attestation(tmp_path):
    project = tmp_path / "pkpd"
    init_project(project, template="pkpd", subject="workflow-aware-pkpd")
    (project / "generate.py").write_text(
        "import pandas as pd\n"
        "df = pd.read_csv('predictions.csv')\n"
        "df.to_csv('predictions.csv', index=False)\n",
        encoding="utf-8",
    )

    report = discover_project_v06(project, minimum_workflow_confidence=0.90)
    draft = project / "pcs-manifest.draft.json"
    write_discovery_outputs_v06(
        report,
        manifest_output=draft,
        report_output=project / "pcs-discovery.json",
    )
    manifest = project / "manifest.json"
    confirm_manifest_draft_v06(
        draft,
        manifest,
        project_root=project,
        overwrite=True,
    )

    confirmed = json.loads(manifest.read_text(encoding="utf-8"))
    assert confirmed["pcs_intake"]["workflow_inferences_confirmed"] is True
    static_nodes = [
        node for node in confirmed["workflow"]["nodes"]
        if node["operation"] == "static_python_workflow"
    ]
    assert len(static_nodes) == 1
    assert static_nodes[0]["contract"]["human_confirmed"] is True

    private, public, fingerprint = _keys(tmp_path)
    bundle = tmp_path / "workflow-aware.pcs.zip"
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
    cert_nodes = [
        node for node in certificate["workflow"]["nodes"]
        if node["operation"] == "static_python_workflow"
    ]
    assert len(cert_nodes) == 1
    proposition = cert_nodes[0]["contract"]["proposition"]
    assert '"human_confirmed":true' in proposition
    assert '"user_code_executed":false' in proposition


def test_source_change_after_confirmation_is_rejected_before_signing(tmp_path):
    project = tmp_path / "pkpd"
    init_project(project, template="pkpd", subject="workflow-aware-pkpd")
    script = project / "generate.py"
    script.write_text(
        "import pandas as pd\n"
        "df = pd.read_csv('predictions.csv')\n"
        "df.to_csv('predictions.csv', index=False)\n",
        encoding="utf-8",
    )
    report = discover_project_v06(project, minimum_workflow_confidence=0.90)
    draft = project / "pcs-manifest.draft.json"
    write_discovery_outputs_v06(
        report,
        manifest_output=draft,
        report_output=project / "pcs-discovery.json",
    )
    manifest = project / "manifest.json"
    confirm_manifest_draft_v06(draft, manifest, project_root=project, overwrite=True)

    script.write_text(
        script.read_text(encoding="utf-8") + "\nprint('changed')\n",
        encoding="utf-8",
    )
    private, public, _ = _keys(tmp_path)

    with pytest.raises(
        V06AttestationError,
        match="changed after PCS discovery/confirmation",
    ):
        attest_v06(
            manifest,
            tmp_path / "should-not-exist.zip",
            private,
            public,
        )



def test_static_python_handles_dunder_file_parent_keyword_paths_and_path_open(tmp_path):
    project = tmp_path / "project"
    scripts = project / "scripts"
    data = project / "data"
    scripts.mkdir(parents=True)
    data.mkdir()
    (data / "input.csv").write_text("id,x\n1,2\n", encoding="utf-8")
    (data / "output.csv").write_text("id,x\n1,3\n", encoding="utf-8")
    (scripts / "pipeline.py").write_text(
        "from pathlib import Path\n"
        "import pandas as pd\n"
        "ROOT = Path(__file__).resolve().parent.parent\n"
        "INP = ROOT / 'data' / 'input.csv'\n"
        "OUT = ROOT / 'data' / 'output.csv'\n"
        "df = pd.read_csv(filepath_or_buffer=INP)\n"
        "with OUT.open('w') as fh:\n"
        "    fh.write('placeholder')\n",
        encoding="utf-8",
    )
    inventory = _inventory_for(
        project,
        ["data/input.csv", "data/output.csv", "scripts/pipeline.py"],
    )

    result = analyze_static_workflow_v06(project, inventory)

    assert result["summary"]["source_files_with_resolved_dependencies"] == 1
    source = result["sources"][0]
    assert source["reads"] == ["artifact_0"]
    assert source["writes"] == ["artifact_1"]


def test_notebook_line_magics_do_not_force_false_parse_failure(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "train.csv").write_text("id,x\n1,2\n", encoding="utf-8")
    (project / "result.csv").write_text("id,x\n1,3\n", encoding="utf-8")
    notebook = {
        "cells": [
            {
                "cell_type": "code",
                "metadata": {},
                "source": [
                    "%matplotlib inline\n",
                    "!echo local-shell-command-not-executed\n",
                    "import pandas as pd\n",
                    "df = pd.read_csv('train.csv')\n",
                    "df.to_csv('result.csv', index=False)\n",
                ],
                "outputs": [],
                "execution_count": None,
            }
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    (project / "analysis.ipynb").write_text(json.dumps(notebook), encoding="utf-8")
    inventory = _inventory_for(
        project,
        ["train.csv", "result.csv", "analysis.ipynb"],
    )

    result = analyze_static_workflow_v06(project, inventory)

    assert result["summary"]["source_files_with_resolved_dependencies"] == 1
    source = result["sources"][0]
    assert source["reads"] == ["artifact_0"]
    assert source["writes"] == ["artifact_1"]
    assert source["confidence"] == 0.98



def test_r_literal_workflow_is_discovered_but_review_only_by_default(tmp_path):
    project = tmp_path / "r-project"
    project.mkdir()
    (project / "train.csv").write_text("id,x\n1,2\n", encoding="utf-8")
    (project / "result.csv").write_text("id,x\n1,3\n", encoding="utf-8")
    (project / "analysis.R").write_text(
        "library(readr)\n"
        "df <- read.csv('train.csv')\n"
        "write.csv(df, 'result.csv', row.names=FALSE)\n",
        encoding="utf-8",
    )
    inventory = _inventory_for(
        project,
        ["train.csv", "result.csv", "analysis.R"],
    )

    result = analyze_static_workflow_v06(project, inventory)

    assert result["summary"]["source_files_with_resolved_dependencies"] == 1
    source = result["sources"][0]
    assert source["source_kind"] == "r"
    assert source["analysis_mode"] == "r_literal_heuristic"
    assert source["confidence"] == 0.88
    assert source["reads"] == ["artifact_0"]
    assert source["writes"] == ["artifact_1"]
    assert "readr" in source["imports"]


def test_r_workflow_enters_draft_only_when_threshold_is_explicitly_lowered(tmp_path):
    project = tmp_path / "r-guided"
    project.mkdir()
    (project / "train.csv").write_text("id,x\n1,1\n", encoding="utf-8")
    (project / "test.csv").write_text("id,x\n2,2\n", encoding="utf-8")
    (project / "processed.csv").write_text("id,x\n1,1\n", encoding="utf-8")
    (project / "analysis.R").write_text(
        "df <- read.csv('train.csv')\n"
        "write.csv(df, 'processed.csv', row.names=FALSE)\n",
        encoding="utf-8",
    )

    default_report = discover_project_v06(project)
    assert default_report["workflow_map"]["sources"][0]["confidence"] == 0.88
    assert default_report["selected_workflow_inferences"] == []
    assert "analysis.R" not in {
        artifact["path"]
        for artifact in default_report["manifest_draft"]["artifacts"]
    }

    opted_in = discover_project_v06(
        project,
        minimum_workflow_confidence=0.85,
    )
    assert len(opted_in["selected_workflow_inferences"]) == 1
    assert "analysis.R" in {
        artifact["path"]
        for artifact in opted_in["manifest_draft"]["artifacts"]
    }
    assert any(
        node["operation"] == "static_r_workflow"
        for node in opted_in["manifest_draft"]["workflow"]["nodes"]
    )
