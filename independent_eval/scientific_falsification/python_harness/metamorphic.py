"""Metamorphic scientific testing harness (Task 9).

Applies valid/invalid transformations to certified projects and compares
outcomes against black-box `pcs certify` / `pcs verify` behavior.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from .hashing import write_json
from .pcs_cli import certify, verify_certificate


@dataclass
class TransformResult:
    name: str
    kind: str  # "valid" | "invalid"
    expected_verify_ok: bool
    certify_ok: bool | None
    verify_ok: bool | None
    passed_oracle: bool
    detail: str


TransformFn = Callable[[Path], None]

# Default casebook cases for the metamorphic campaign (beyond PK/PD-only).
DEFAULT_CAMPAIGN_CASE_IDS: tuple[str, ...] = (
    "01_pkpd_one_compartment",
    "03_mass_action_reaction_balance",
    "04_unit_compatible_concentration",
    "06_scientific_workflow_composite",
)


def _load_manifest(project: Path) -> dict[str, Any]:
    return json.loads((project / "manifest.json").read_text(encoding="utf-8"))


def _write_manifest(project: Path, manifest: dict[str, Any]) -> None:
    (project / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _check_types(project: Path) -> set[str]:
    return {c.get("type") for c in _load_manifest(project).get("checks", []) if c.get("type")}


def transform_rename_subject(project: Path) -> None:
    """Valid: subject string change should still certify/verify after re-certify."""
    m = _load_manifest(project)
    m["subject"] = m.get("subject", "subject") + "-renamed"
    _write_manifest(project, m)


def transform_reorder_claims(project: Path) -> None:
    """Valid: claim order should not affect computational outcomes after re-certify."""
    m = _load_manifest(project)
    if len(m.get("claims", [])) >= 2:
        m["claims"] = list(reversed(m["claims"]))
        # Keep check claim_ids consistent; do not reverse checks (IDs still match).
        _write_manifest(project, m)


def transform_tamper_prediction_after_certify(project: Path) -> None:
    """Invalid helper applied to evidence package, not project — see runner."""
    raise RuntimeError("use post_certify_tamper_predictions")


def transform_break_model_dose(project: Path) -> None:
    """Invalid: change dose without regenerating predictions."""
    model_path = project / "model.json"
    if not model_path.is_file():
        # Fall back to breaking a reaction if no PK model.
        rxn = project / "reaction.json"
        if rxn.is_file():
            obj = json.loads(rxn.read_text(encoding="utf-8"))
            if obj.get("products"):
                obj["products"][0]["coefficient"] = int(obj["products"][0]["coefficient"]) + 1
            (project / "reaction.json").write_text(
                json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            # Sync manifest check reactants/products if present.
            m = _load_manifest(project)
            for check in m.get("checks", []):
                if check.get("type") == "reaction_balance":
                    check["reactants"] = obj.get("reactants", check.get("reactants"))
                    check["products"] = obj.get("products", check.get("products"))
            for claim in m.get("claims", []):
                pred = claim.get("predicate", {})
                if pred.get("type") == "reaction_balance":
                    pred["reactants"] = obj.get("reactants", pred.get("reactants"))
                    pred["products"] = obj.get("products", pred.get("products"))
            _write_manifest(project, m)
            return
        raise FileNotFoundError("no model.json or reaction.json to invalidate")
    model = json.loads(model_path.read_text(encoding="utf-8"))
    model["dose"]["value"] = float(model["dose"]["value"]) * 2.0
    model_path.write_text(json.dumps(model, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def transform_incompatible_units(project: Path) -> None:
    """Invalid: flip a unit_compatible check to incompatible units."""
    m = _load_manifest(project)
    found = False
    for check in m.get("checks", []):
        if check.get("type") == "unit_compatible":
            check["right_unit"] = "s"
            found = True
    for claim in m.get("claims", []):
        pred = claim.get("predicate", {})
        if pred.get("type") == "unit_compatible":
            pred["right_unit"] = "s"
    if not found:
        raise ValueError("no unit_compatible check in project")
    _write_manifest(project, m)


def transform_overlap_csv_keys(project: Path) -> None:
    """Invalid: force train/test key overlap for csv_disjoint checks."""
    m = _load_manifest(project)
    found = False
    for check in m.get("checks", []):
        if check.get("type") != "csv_disjoint":
            continue
        found = True
        key = check.get("key", "subject_id")
        right_id = check.get("right_artifact")
        left_id = check.get("left_artifact")
        arts = {a["id"]: a for a in m.get("artifacts", []) if "id" in a}
        left_path = project / arts[left_id]["path"]
        right_path = project / arts[right_id]["path"]
        left_lines = left_path.read_text(encoding="utf-8").splitlines()
        if len(left_lines) < 2:
            raise ValueError("left csv too short to leak a key")
        # Copy first data row's key into the right table.
        header = left_lines[0].split(",")
        key_idx = header.index(key)
        leaked = left_lines[1].split(",")[key_idx]
        right_lines = right_path.read_text(encoding="utf-8").splitlines()
        if len(right_lines) < 2:
            raise ValueError("right csv too short")
        rheader = right_lines[0].split(",")
        r_idx = rheader.index(key)
        parts = right_lines[1].split(",")
        parts[r_idx] = leaked
        right_lines[1] = ",".join(parts)
        right_path.write_text("\n".join(right_lines) + "\n", encoding="utf-8")
    if not found:
        raise ValueError("no csv_disjoint check in project")


VALID_TRANSFORMS: list[tuple[str, TransformFn]] = [
    ("rename_subject", transform_rename_subject),
    ("reorder_claims", transform_reorder_claims),
]

INVALID_TRANSFORMS: list[tuple[str, TransformFn]] = [
    ("break_model_or_reaction", transform_break_model_dose),
]


def _certify_and_verify(project: Path, work: Path) -> tuple[bool, bool, str]:
    out = work / "evidence"
    if out.exists():
        shutil.rmtree(out)
    c = certify(project / "manifest.json", out)
    if not c.ok:
        return False, False, f"certify failed: {c.combined()[-500:]}"
    cert = out / "certificate.json"
    v = verify_certificate(cert)
    return True, v.ok, v.combined()[-500:]


def _oracle_invalid_after_certify(
    work_root: Path, run_name: str, c_ok: bool, v_ok: bool
) -> bool:
    if not c_ok:
        return True
    cert = json.loads(
        (work_root / run_name / "evidence" / "certificate.json").read_text(encoding="utf-8")
    )
    statuses = [c.get("assessment", {}).get("status") for c in cert.get("claims", [])]
    return any(s != "COMPUTATIONALLY_SUPPORTED" for s in statuses) or not v_ok


def post_certify_tamper(project: Path, work: Path) -> TransformResult:
    """Invalid: certify clean project, then tamper packaged artifact bytes."""
    out = work / "evidence"
    if out.exists():
        shutil.rmtree(out)
    c = certify(project / "manifest.json", out)
    if not c.ok:
        return TransformResult(
            name="post_certify_artifact_tamper",
            kind="invalid",
            expected_verify_ok=False,
            certify_ok=False,
            verify_ok=None,
            passed_oracle=False,
            detail=f"baseline certify failed: {c.combined()[-300:]}",
        )
    # Tamper a copied artifact inside the evidence package if present.
    candidates = list(out.rglob("predictions.csv")) + list(out.rglob("*.csv"))
    if not candidates:
        # Tamper certificate JSON claim text as a semantic change.
        cert_path = out / "certificate.json"
        obj = json.loads(cert_path.read_text(encoding="utf-8"))
        obj["subject"] = str(obj.get("subject", "")) + "-TAMPERED"
        cert_path.write_text(json.dumps(obj), encoding="utf-8")
    else:
        path = candidates[0]
        data = path.read_bytes()
        path.write_bytes(data + b"\n#tamper\n")

    v = verify_certificate(out / "certificate.json")
    passed = not v.ok
    return TransformResult(
        name="post_certify_artifact_tamper",
        kind="invalid",
        expected_verify_ok=False,
        certify_ok=True,
        verify_ok=v.ok,
        passed_oracle=passed,
        detail="verify should reject tampered evidence package",
    )


def _applicable_invalid_transforms(source_project: Path) -> list[tuple[str, TransformFn]]:
    """Select invalid transforms that the project surface can express."""
    types = _check_types(source_project)
    selected: list[tuple[str, TransformFn]] = []
    if (source_project / "model.json").is_file() or (source_project / "reaction.json").is_file():
        selected.append(("break_model_or_reaction", transform_break_model_dose))
    if "unit_compatible" in types:
        selected.append(("incompatible_units", transform_incompatible_units))
    if "csv_disjoint" in types:
        selected.append(("overlap_csv_keys", transform_overlap_csv_keys))
    return selected


def run_metamorphic_suite(
    source_project: Path,
    work_root: Path,
) -> dict[str, Any]:
    work_root.mkdir(parents=True, exist_ok=True)
    results: list[TransformResult] = []

    # Baseline
    baseline_dir = work_root / "baseline"
    if baseline_dir.exists():
        shutil.rmtree(baseline_dir)
    shutil.copytree(source_project, baseline_dir)
    # Drop negative_controls from runtime copy noise
    cert_ok, ver_ok, detail = _certify_and_verify(baseline_dir, work_root / "baseline_run")
    results.append(
        TransformResult(
            name="baseline",
            kind="valid",
            expected_verify_ok=True,
            certify_ok=cert_ok,
            verify_ok=ver_ok,
            passed_oracle=bool(cert_ok and ver_ok),
            detail=detail,
        )
    )

    for name, fn in VALID_TRANSFORMS:
        proj = work_root / f"valid_{name}"
        if proj.exists():
            shutil.rmtree(proj)
        shutil.copytree(source_project, proj)
        fn(proj)
        c_ok, v_ok, det = _certify_and_verify(proj, work_root / f"run_valid_{name}")
        results.append(
            TransformResult(
                name=name,
                kind="valid",
                expected_verify_ok=True,
                certify_ok=c_ok,
                verify_ok=v_ok,
                passed_oracle=bool(c_ok and v_ok),
                detail=det,
            )
        )

    for name, fn in _applicable_invalid_transforms(source_project):
        proj = work_root / f"invalid_{name}"
        if proj.exists():
            shutil.rmtree(proj)
        shutil.copytree(source_project, proj)
        try:
            fn(proj)
        except Exception as exc:  # noqa: BLE001 — record transform failure
            results.append(
                TransformResult(
                    name=name,
                    kind="invalid",
                    expected_verify_ok=False,
                    certify_ok=None,
                    verify_ok=None,
                    passed_oracle=False,
                    detail=f"transform error: {exc}",
                )
            )
            continue
        c_ok, v_ok, det = _certify_and_verify(proj, work_root / f"run_invalid_{name}")
        oracle = _oracle_invalid_after_certify(work_root, f"run_invalid_{name}", c_ok, v_ok)
        results.append(
            TransformResult(
                name=name,
                kind="invalid",
                expected_verify_ok=False,
                certify_ok=c_ok,
                verify_ok=v_ok,
                passed_oracle=oracle,
                detail=det,
            )
        )

    results.append(post_certify_tamper(source_project, work_root / "tamper_run"))

    report = {
        "format": "pcs-independent-eval-metamorphic-report-v1",
        "source_project": str(source_project),
        "case_id": source_project.name,
        "check_types": sorted(_check_types(source_project)),
        "cases": [asdict(r) for r in results],
        "valid_pass": sum(1 for r in results if r.kind == "valid" and r.passed_oracle),
        "valid_total": sum(1 for r in results if r.kind == "valid"),
        "invalid_pass": sum(1 for r in results if r.kind == "invalid" and r.passed_oracle),
        "invalid_total": sum(1 for r in results if r.kind == "invalid"),
        "all_oracles_passed": all(r.passed_oracle for r in results),
    }
    return report


def run_metamorphic_campaign(
    casebook_cases_root: Path,
    work_root: Path,
    report_dir: Path,
    *,
    case_ids: tuple[str, ...] | list[str] | None = None,
) -> dict[str, Any]:
    """Run metamorphic suites across multiple cases; write per-case reports.

    Per-case JSON lands under ``report_dir`` as ``metamorphic_<case_id>.json``.
    A campaign rollup is written as ``metamorphic_campaign.json``.
    """
    selected = list(case_ids) if case_ids is not None else list(DEFAULT_CAMPAIGN_CASE_IDS)
    report_dir.mkdir(parents=True, exist_ok=True)
    work_root.mkdir(parents=True, exist_ok=True)

    per_case: list[dict[str, Any]] = []
    for case_id in selected:
        source = casebook_cases_root / case_id
        if not (source / "manifest.json").is_file():
            per_case.append(
                {
                    "case_id": case_id,
                    "status": "missing",
                    "all_oracles_passed": False,
                }
            )
            continue
        report = run_metamorphic_suite(source, work_root / case_id)
        out_path = report_dir / f"metamorphic_{case_id}.json"
        write_json(out_path, report)
        per_case.append(
            {
                "case_id": case_id,
                "status": "ok",
                "report_path": str(out_path),
                "check_types": report.get("check_types", []),
                "valid_pass": report["valid_pass"],
                "valid_total": report["valid_total"],
                "invalid_pass": report["invalid_pass"],
                "invalid_total": report["invalid_total"],
                "all_oracles_passed": report["all_oracles_passed"],
            }
        )

    campaign = {
        "format": "pcs-independent-eval-metamorphic-campaign-v1",
        "case_ids": selected,
        "case_count": len(selected),
        "cases_ok": sum(1 for c in per_case if c.get("status") == "ok"),
        "oracles_all_passed_count": sum(
            1 for c in per_case if c.get("all_oracles_passed")
        ),
        "per_case": per_case,
    }
    write_json(report_dir / "metamorphic_campaign.json", campaign)
    return campaign
