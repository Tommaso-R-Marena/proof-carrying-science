"""Frozen matched-project benchmark; final access requires a software digest.

Both actual v3 and v4 pipelines process each entire admitted project. Failures
remain visible as failures/unknowns, never synthetic successes or rescored old
results. This module never rewrites historical evidence packages.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import resource
import time

from research.scientific_intake_v1.intake import canonical
from research.scientific_semantics_v3 import pipeline as baseline
from research.scientific_semantics_v3 import retrieval
from . import pipeline
from .corpus import materialize, source_freeze, FROZEN_SHA256
from .reference import load_reference, load_protocol, load_workflow_rubric
from .evaluation import grade, grade_workflow, VERSION as GRADING_VERSION

SCHEMA = "scientific-review-prospective-benchmark-v4"
SELECTION = {"source_retrieval": ["bm25", "tfidf", "normalized_bm25", "hybrid"],
             "retrieval_pool": "structural", "neural_ablation": "omitted; no new training or retuning",
             "interpretation_baseline": "actual frozen scientific_semantics_v3.pipeline.run on full matched project",
             "grading": GRADING_VERSION, "formal_checks": True,
             "selection_basis": "public development only; deterministic methods fixed before final access"}


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _write(path, value):
    Path(path).write_bytes(canonical(value) + b"\n")


def _versions():
    versions = {"python": platform.python_version()}
    for name in ("numpy", "scipy"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = "NOT_INSTALLED"
    return versions


def software_freeze():
    """Public-only canonical software/selection record. Opens no final data.

    The annotation manifest pins private final identities without reading them.
    Protocol and source manifests are public and hash validated separately.
    """
    base = Path(__file__).resolve().parent
    source_freeze()
    protocol = load_protocol()
    return {"schema": "scientific-review-software-freeze-v4", "context": pipeline.context(),
            "baseline_context": baseline.context(), "source_freeze_sha256": FROZEN_SHA256,
            "source_metadata_erratum_sha256": _sha(base / "source-freeze-errata.json"),
            "protocol_sha256": _sha(base / "reference/protocol.json"),
            "annotation_freeze_sha256": _sha(base / "reference/annotation-freeze.json"),
            "annotation_freeze_recovered_sha256": _sha(base / "reference/annotation-freeze-recovered.json") if (base / "reference/annotation-freeze-recovered.json").is_file() else None,
            "toolchain_sha256": _sha(base.parents[1] / "lean-toolchain"),
            "reference_schema": protocol.get("schema_version"), "version_pins": _versions(), "selection": SELECTION,
            "final_data_used_for_training_or_selection": False, "external_expert_validation": False, "authority": False}


def software_sha256(freeze=None):
    return hashlib.sha256(canonical(software_freeze() if freeze is None else freeze) + b"\n").hexdigest()


def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _error(exc):
    return {"type": type(exc).__name__, "message": str(exc)[:4000], "status": "FAILED_UNKNOWN"}


def _measure():
    return {"parent_maxrss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "child_maxrss_kib": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss}


def _source_inventory(root):
    """Retrieval over every admitted source, independent of pipeline success."""
    root = Path(root)
    return {"artifacts": [{"id": "source-" + hashlib.sha256(p.relative_to(root).as_posix().encode()).hexdigest(),
                           "path": p.relative_to(root).as_posix(), "snapshot_path": str(p),
                           "size": p.stat().st_size, "sha256": _sha(p)}
                          for p in sorted(root.rglob("*")) if p.is_file()]}


def _retrieval(refs, inventory):
    # The historical retrieval API has a smaller input bound than the v4
    # intake. Admit all UTF-8 files inside its fixed per-file bound and report
    # every excluded original file. Never truncate source text silently.
    eligible, excluded = [], []
    for artifact in inventory["artifacts"]:
        if artifact["size"] > retrieval.MAX_SOURCE:
            excluded.append({"path": artifact["path"], "reason": "historical retrieval per-file bound", "bytes": artifact["size"]})
            continue
        try:
            Path(artifact["snapshot_path"]).read_bytes().decode("utf-8-sig")
        except UnicodeError:
            excluded.append({"path": artifact["path"], "reason": "not UTF-8 source text", "bytes": artifact["size"]})
            continue
        eligible.append(artifact)
    selected = {"artifacts": eligible}
    result = []
    for mode in SELECTION["source_retrieval"]:
        started = time.monotonic()
        try:
            measured = retrieval.evaluate_references(refs, selected, mode=mode, pool="structural")
            result.append({"pool": "structural", "mode": mode, "status": "COMPLETED", "result": measured,
                           "source_relevance_only": True, "scientific_meaning": "OPEN", "seconds": time.monotonic()-started,
                           "eligible_source_files": len(eligible), "excluded_sources": excluded})
        except Exception as exc:
            result.append({"pool": "structural", "mode": mode, "error": _error(exc), "seconds": time.monotonic()-started,
                           "source_relevance_only": True, "scientific_meaning": "OPEN",
                           "eligible_source_files": len(eligible), "excluded_sources": excluded})
    return result


def _pipeline_case(engine, source, packet, refs, rubric, artifacts, *, v4):
    started = time.monotonic()
    row = {"package": str(packet), "review_path": str(packet / "review.html"), "status": "FAILED_UNKNOWN",
           "checks": [], "numerical": [], "check_statuses": {}}
    try:
        summary = engine.run(source, packet, check=True, **({"formal_check": True} if v4 else {}))
        interpretation = _json(packet / ("interpretation.json" if v4 else "semantics.json"))
        checks = _json(packet / "checks.json")
        inventory, captured = engine.snapshot_artifacts(packet / ("parent" if v4 else "baseline"))
        if captured != artifacts:
            raise ValueError("pipeline snapshots differ from full matched project")
        row.update(summary=summary, interpretation_path=str(packet / ("interpretation.json" if v4 else "semantics.json")),
                   checks_path=str(packet / "checks.json"), checks=checks,
                   grading=grade(refs, interpretation, captured, checks, inventory),
                   check_statuses=dict(Counter(c.get("status", "MISSING") for c in checks)),
                   numerical=[c for c in checks if c.get("checker") == "conditional_ode_reconstruction"
                              or c.get("status") in {"REPRODUCED_COMPUTATION", "REPRODUCED_ROUNDED_COMPUTATION"}
                              or any(w in str(c.get("checker", "")).lower() for w in ("numeric", "simulation", "residual", "nist", "prediction"))],
                   status="COMPLETED")
        row["workflow_utility"] = grade_workflow(rubric, refs, row["grading"], interpretation, checks)
    except Exception as exc:
        row["error"] = _error(exc)
        # Negative outcomes remain enumerable even when an interpreter fails.
        row["grading"] = grade(refs, {"claims": []}, artifacts)
        row["grading"]["execution_failed"] = True
        row["grading"]["correct_counterprobe_abstentions"] = 0
        row["grading"]["counterprobe_abstention_interpretation"] = "Execution failed; no abstention credit"
        row["workflow_utility"] = grade_workflow(rubric, refs, row["grading"], {"claims": []})
    row["inference_seconds"] = time.monotonic()-started
    # Replay every produced package independently. Missing/partial packages stay
    # failed rather than being silently skipped or accepted on a manifest alone.
    replay_start = time.monotonic()
    try:
        row["independent_replay"] = {"status": "COMPLETED", "result": engine.replay(packet)}
    except Exception as exc:
        row["independent_replay"] = _error(exc)
        row["status"] = "FAILED_UNKNOWN"
    row["valid_for_prospective_scoring"] = row["status"] == "COMPLETED" and row["independent_replay"]["status"] == "COMPLETED"
    if not row["valid_for_prospective_scoring"]:
        # Retain what the interpreter appeared to achieve for diagnosis, while
        # the aggregate below grants it no validated positive credit.
        row["provisional_grading"] = row["grading"]
        row["provisional_workflow_utility"] = row["workflow_utility"]
    row["review_exists"] = (packet / "review.html").is_file()
    row["replay_seconds"] = time.monotonic()-replay_start
    row["resource_usage"] = _measure()
    row["resource_usage"]["scope"] = "process lifetime high-water RSS; includes preceding cases, not an isolated per-case peak"
    return row


def _aggregate(cases):
    combined = {}
    for key in ("baseline_v3_new_protocol", "review_v4_new_protocol"):
        runs = [case[key] for case in cases]
        totals = {name: sum(r["grading"].get(name, 0) for r in runs) for name in
                  ("supported_total", "core_found", "typed_context_found", "annotated_probe_pairs", "typed_correct_probe_pairs",
                   "counterprobes", "counterprobe_core_proposals", "counterprobe_full_context_proposals", "correct_counterprobe_abstentions",
                   "unsupported_promotions", "source_binding_failures", "reference_binding_failures", "claims_generated")}
        # Every project remains in recall/task denominators, and every observed
        # annotated pair remains in precision's denominator. An invalid or
        # unreplayed package can contribute diagnostic failures/proposals, but
        # cannot improve recall, precision, abstention or workflow achievement.
        valid = [r for r in runs if r["valid_for_prospective_scoring"]]
        for name in ("core_found", "typed_context_found", "typed_correct_probe_pairs", "correct_counterprobe_abstentions"):
            totals[name] = sum(r["grading"].get(name, 0) for r in valid)
        totals["core_recall"] = totals["core_found"]/totals["supported_total"] if totals["supported_total"] else None
        totals["typed_context_recall"] = totals["typed_context_found"]/totals["supported_total"] if totals["supported_total"] else None
        totals["annotated_probe_precision"] = totals["typed_correct_probe_pairs"]/totals["annotated_probe_pairs"] if totals["annotated_probe_pairs"] else None
        totals["failed_or_unreplayed_projects"] = sum(not r["valid_for_prospective_scoring"] for r in runs)
        totals["workflow_tasks"] = sum(r["workflow_utility"]["tasks"] for r in runs)
        totals["workflow_correct"] = sum(r["workflow_utility"]["correct"] for r in valid)
        totals["workflow_correct_informative_abstentions"] = sum(r["workflow_utility"]["correct_informative_abstentions"] for r in valid)
        totals["inference_seconds"] = sum(r["inference_seconds"] for r in runs)
        totals["replay_seconds"] = sum(r["replay_seconds"] for r in runs)
        totals["metrics_include_failed_project_denominators"] = True
        totals["positive_credit_requires_independent_replay"] = True
        combined[key] = totals
    return combined


def run_benchmark(output, *, split="development", allow_final=False, source_root=None, reference_root=None, expected_software_sha256=None):
    if split not in {"development", "final"}:
        raise ValueError("unknown benchmark split")
    if split == "final" and not allow_final:
        raise ValueError("final evaluation requires explicit post-freeze opt-in")
    output = Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise ValueError("refuse benchmark overwrite")
    freeze = software_freeze()
    freeze_sha = software_sha256(freeze)
    if expected_software_sha256 is not None and expected_software_sha256 != freeze_sha:
        raise ValueError("software changed after pre-final freeze")
    if split == "final" and expected_software_sha256 is None:
        raise ValueError("final run requires precommitted software freeze digest")
    # Persist the software boundary before reading labels or materializing cases.
    output.mkdir(parents=True, mode=0o700)
    _write(output / "software-freeze.json", freeze)
    _write(output / "started.json", {"utc": datetime.now(timezone.utc).isoformat(), "split": split, "software_sha256": freeze_sha})
    started, cases = time.monotonic(), []
    try:
        if reference_root is not None:
            supplied = Path(reference_root)
            for name, field in (("annotation-freeze.json", "annotation_freeze_sha256"),
                                ("annotation-freeze-recovered.json", "annotation_freeze_recovered_sha256")):
                if freeze.get(field) is not None and _sha(supplied / name) != freeze[field]:
                    raise ValueError("reference manifest differs from pre-run software freeze: " + name)
        refs = load_reference(split, allow_final=allow_final, reference_root=reference_root)
        rubric = load_workflow_rubric(split, allow_final=allow_final, reference_root=reference_root)
        protocol = load_protocol(reference_root=reference_root)
        if hashlib.sha256(canonical(protocol)).hexdigest() != hashlib.sha256(canonical(load_protocol())).hexdigest():
            raise ValueError("evaluation protocol differs from software freeze")
        records = materialize(output / "projects", split, allow_final=allow_final, source_root=source_root)
        for project in records:
            if software_sha256() != freeze_sha:
                raise ValueError("runtime context changed after benchmark freeze")
            case_start = time.monotonic()
            source = Path(project.get("root", project.get("path", project.get("directory"))))
            inventory = _source_inventory(source)
            artifacts = {a["path"]: Path(a["snapshot_path"]).read_bytes() for a in inventory["artifacts"]}
            selected = [r for r in refs if r["project_id"] == project["id"]]
            tasks = [r for r in rubric if r["project_id"] == project["id"]]
            case = {"project_id": project["id"], "source_files": len(artifacts), "source_bytes": sum(map(len, artifacts.values())),
                    "baseline_v3_new_protocol": _pipeline_case(baseline, source, output / (project["id"] + "-v3"), selected, tasks, artifacts, v4=False)}
            case["review_v4_new_protocol"] = _pipeline_case(pipeline, source, output / (project["id"] + "-v4"), selected, tasks, artifacts, v4=True)
            case["retrieval"] = _retrieval(selected, inventory)
            case["total_case_seconds"] = time.monotonic()-case_start
            case["context_unchanged"] = software_sha256() == freeze_sha
            cases.append(case)
            _write(output / "partial.json", {"split": split, "software_sha256": freeze_sha, "completed_cases": cases})
            if not case["context_unchanged"]:
                raise ValueError("runtime context changed while processing case; retained failure, no prospective score")
        result = {"schema": SCHEMA, "status": "COMPLETED", "split": split, "software_sha256": freeze_sha,
                  "source_freeze_sha256": FROZEN_SHA256, "cases": cases, "seconds": time.monotonic()-started,
                  "aggregate": _aggregate(cases),
                  **_measure(), "protocol": protocol, "authority": False, "external_expert_validation": False,
                  "training_on_sources": False, "test_set_reused_for_development": split == "development",
                  "interpretation_scope": "Selected independent source declarations and findings; not arbitrary paper understanding",
                  "resource_cost": {"external_model_calls": 0, "training_steps": 0, "token_cost": 0,
                                    "note": "Deterministic local interpretation/retrieval; wall time and RSS above"}}
    except Exception as exc:
        result = {"schema": SCHEMA, "status": "FAILED_UNKNOWN", "split": split, "software_sha256": freeze_sha,
                  "error": _error(exc), "cases": cases, "seconds": time.monotonic()-started, **_measure(), "authority": False}
        _write(output / "results.json", result)
        raise
    _write(output / "results.json", result)
    return result
