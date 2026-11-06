"""Development-only project checks; held-out source bytes remain sealed here."""
from __future__ import annotations

import csv
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from . import adapters, projects


@pytest.fixture(scope="module")
def development(tmp_path_factory):
    output = tmp_path_factory.mktemp("project-tests") / "materialized"
    return projects.materialize_projects(output)


def test_default_split_never_reads_held_out_sources(tmp_path, monkeypatch):
    sealed = {"1UBQ.fasta", "1UBQ.pdb", "1UBQ.cif", "Pontius.dat", "lean4_List_Basic.lean"}
    reads = []
    original = Path.read_bytes

    def guarded(path):
        assert path.name not in sealed, "held-out bytes opened during development"
        reads.append(path.name)
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", guarded)
    records = projects.materialize_projects(tmp_path / "cases")
    assert [record["id"] for record in records] == ["rcsb_1crn", "nist_norris", "lean4_nat_add"]
    assert {record["split"] for record in records} == {"development"}
    assert {"1CRN.pdb", "Norris.dat", "lean4_Nat_Basic.lean"} <= set(reads)
    assert not set(reads) & sealed


def test_frozen_registration_includes_disjoint_cases_without_opening_final_data():
    # Split membership is metadata and may be inspected before the evaluation freeze.
    registration = json.loads((projects.UPSTREAM / "preregistration.json").read_text())
    observed = {case["id"]: case["split"] for case in registration["cases"]}
    assert observed == {spec["id"]: spec["split"] for spec in projects._SPECS}
    assert len([split for split in observed.values() if split == "development"]) == 3
    assert len([split for split in observed.values() if split == "final"]) == 3
    assert registration["training"] == []


def test_original_hashes_sources_and_license_evidence_are_retained(development):
    for record in development:
        root = Path(record["path"])
        assert record["license"]["spdx"] in {"CC0-1.0", "NIST-PD", "Apache-2.0"}
        for evidence in record["license"]["evidence"]:
            assert (root / evidence).is_file()
        for source in record["source_provenance"]:
            raw = (root / source["path"]).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == source["sha256"]
            assert len(raw) == source["byte_count"]
            assert raw == (projects.UPSTREAM / source["original_path"]).read_bytes()
            assert source["status"] == "UPSTREAM" and source["modified"] is False
            assert source["url"].startswith("https://")
        assert record["manifest"]["original_source_preserved"] is True
        assert record["manifest"]["source_code_executed"] is False
        assert record["training_permitted"] is False


def test_generated_formats_are_real_data_and_annotations_are_outside_project(development):
    suffixes = {".csv", ".py", ".ipynb", ".json", ".md", ".docx", ".xlsx", ".pdf"}
    for record in development:
        root = Path(record["path"])
        derived = [item for item in record["manifest"]["files"] if item["status"] == "DERIVED"]
        assert suffixes <= {Path(item["path"]).suffix for item in derived}
        for item in derived:
            raw = (root / item["path"]).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == item["sha256"]
            result = adapters.extract(item["path"], raw)
            if item["path"].endswith(".pdf") and not Path(adapters.PDFTOTEXT).is_file():
                assert result["status"] == "UNSUPPORTED"
                continue
            assert result["status"] == "EXTRACTED", (item["path"], result["warnings"])
            assert result["segments"]
        assert not (root / "annotations.json").exists()
        lineage = json.loads((root / "source_lineage.json").read_text())
        assert lineage["authority"] is False
        assert lineage["source_provenance"]
        assert "annotations" not in lineage
        assert "expected_status" not in (root / "source_lineage.json").read_text()
        for item in lineage["files"]:
            assert hashlib.sha256((root / item["path"]).read_bytes()).hexdigest() == item["sha256"]
            assert item["transformation"]["description"]
        assert all(source["license"]["spdx"] for source in lineage["source_provenance"])
        config = json.loads((root / "config.json").read_text())
        assert config["status"] == "DERIVED"
        assert config["training_permitted"] is False
        notebook = json.loads((root / "analysis.ipynb").read_text())
        assert all(cell.get("execution_count") is None and not cell.get("outputs") for cell in notebook["cells"])
        assert not (root / "__pycache__").exists()


@pytest.mark.skipif(not Path(adapters.PDFTOTEXT).is_file(), reason="pdftotext unavailable")
def test_derived_pdf_is_valid_and_actual_pdftotext_extracts_summary(development):
    for record in development:
        path = Path(record["path"]) / "summary.pdf"
        raw = path.read_bytes()
        assert raw.startswith(b"%PDF-1.4\n") and raw.endswith(b"%%EOF\n")
        xref = int(raw.rsplit(b"startxref\n", 1)[1].splitlines()[0])
        assert raw[xref:].startswith(b"xref\n")
        process = subprocess.run([adapters.PDFTOTEXT, "-layout", str(path), "-"], capture_output=True, text=True, timeout=10)
        assert process.returncode == 0, process.stderr
        assert "DERIVED project summary" in process.stdout
        assert "Case: " + record["id"] in process.stdout
        assert "not an independently sourced paper" in process.stdout
        assert "no PDF equations, tables, or OCR" in process.stdout
        result = adapters.extract(path.name, raw)
        assert result["status"] == "EXTRACTED"
        assert result["segments"][0]["locator"] == {"page": 1}
        assert "DERIVED project summary" in result["segments"][0]["text"]
        manifest = next(item for item in record["manifest"]["files"] if item["path"] == "summary.pdf")
        assert manifest["status"] == "DERIVED"
        assert "no independently sourced paper, equations, tables, or OCR" in manifest["transformation"]["description"]


def test_annotations_bind_exact_derived_claim_spans_and_original_dependencies(development):
    for record in development:
        root = Path(record["path"])
        assert record["annotations"]
        assert {"VERIFIED_SUPPORTED", "REFUTED", "UNSUPPORTED"} <= {a["expected_status"] for a in record["annotations"]}
        for annotation in record["annotations"]:
            origin = annotation["origin"]
            raw = (root / origin["path"]).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == origin["sha256"]
            line = raw.decode().splitlines()[origin["locator"]["line"] - 1]
            assert line == origin["quote"] == annotation["statement"]
            assert origin["status"] == "DERIVED"
            assert annotation["verification_only"] is True
            assert annotation["scientific_acceptance"] is False
            assert annotation["source_bindings"]
            for dependency in annotation["source_bindings"]:
                assert hashlib.sha256((root / dependency["path"]).read_bytes()).hexdigest() == dependency["sha256"]
                assert dependency["locator"]
        encoded = projects._json(record["annotations"])
        assert hashlib.sha256(encoded).hexdigest() == record["annotation_sha256"]


def test_norris_variant_lineage_and_exact_ols_are_not_certified(development):
    record = next(record for record in development if record["id"] == "nist_norris")
    root = Path(record["path"])
    with (root / "data.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 12
    assert rows[0] == {"y": "6.40", "x": "-0.2", "temperature": "26.908", "pressure": "990.99"}
    assert sum(Fraction(row["y"]) for row in rows) == Fraction("1841.49")
    lineage = json.loads((root / "data_lineage.json").read_text())
    original = (root / "source/Norris.dat").read_text().splitlines()
    for derived, mapping in zip(rows, lineage["rows"]):
        assert list(derived.values()) == original[mapping["source_line"] - 1].split()
    experiment = json.loads((root / "ols_experiment.json").read_text())
    assert experiment["observations"] == 12 and experiment["degree"] == 1
    assert experiment["normal_equations_exact"] is True and experiment["certified"] is False
    coefficients = [Fraction(value) for value in experiment["coefficients_rational"]]
    residuals = [Fraction(row["y"]) - coefficients[0] - coefficients[1] * Fraction(row["x"]) for row in rows]
    assert sum(residuals) == 0
    assert sum(residual * Fraction(row["x"]) for row, residual in zip(rows, residuals)) == 0
    assert sum(residual * residual for residual in residuals) == Fraction(experiment["sse_rational"])
    context = json.loads((root / "context.json").read_text())
    assert "Dataplot" in context["dataset_variant"] and "no StRD certified" in context["dataset_variant"]
    annotations = {a["statement"]: a for a in record["annotations"]}
    assert annotations["PCS-CLAIM: ols_optimality(data.csv,ols_experiment.json)=true"]["expected_status"] == "VERIFIED_SUPPORTED"
    assert annotations["PCS-CLAIM: ols_optimality(data.csv,ols_experiment.json)=false"]["expected_status"] == "REFUTED"


def test_ols_on_known_polynomial_is_exact_and_rejects_singular_design():
    rows = [{"x": str(x), "y": str(2 + 3 * x + 4 * x * x)} for x in range(-2, 3)]
    result = projects.ordinary_least_squares(rows, 2)
    assert result["coefficients_rational"] == ["2", "3", "4"]
    assert result["sse_rational"] == "0"
    with pytest.raises(ValueError, match="singular"):
        projects.ordinary_least_squares([{"x": "1", "y": "2"}] * 3, 2)
    for degree in (-1, 5, True):
        with pytest.raises(ValueError):
            projects.ordinary_least_squares(rows, degree)


def test_formal_source_is_context_not_execution_or_a_false_quote(development):
    record = next(record for record in development if record["id"] == "lean4_nat_add")
    root = Path(record["path"])
    context = json.loads((root / "context.json").read_text())
    assert context["theorem"] == "Nat.zero_add"
    assert "protected theorem zero_add" in context["source_quote"]
    assert "referenced but not declared" in context["preregistration_limit"]
    assert context["imported_source_executed"] is False
    annotations = {a["statement"]: a for a in record["annotations"]}
    false_identity = annotations["For all natural numbers n, n + 0 = n + 1."]
    assert false_identity["expected_status"] == "UNKNOWN"
    assert false_identity["expected_truth"] is False


def test_materialization_is_reproducible_and_refuses_overwrite(tmp_path, development):
    repeated = projects.materialize_projects(tmp_path / "again")
    for first, second in zip(development, repeated):
        assert first["annotation_sha256"] == second["annotation_sha256"]
        assert first["manifest"] == second["manifest"]
        assert first["source_provenance"] == second["source_provenance"]
    with pytest.raises(FileExistsError):
        projects.materialize_projects(tmp_path / "again")
    with pytest.raises(ValueError, match="split"):
        projects.materialize_projects(tmp_path / "bad", "training")


def test_source_provenance_mismatch_fails_before_derivation(tmp_path, monkeypatch):
    fixtures = tmp_path / "source"
    fixtures.mkdir()
    (fixtures / "Norris.dat").write_bytes(b"tampered")
    monkeypatch.setattr(projects, "UPSTREAM", fixtures)
    builder = projects._Builder(tmp_path / "output", {}, {"Norris.dat": {"sha256": "0" * 64, "byte_count": 8}})
    with pytest.raises(ValueError, match="recorded provenance"):
        builder.source("Norris.dat")
    assert not builder.files
