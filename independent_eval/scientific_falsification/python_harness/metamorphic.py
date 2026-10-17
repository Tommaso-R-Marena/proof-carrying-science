"""Metamorphic scientific testing harness (Task 9).

Applies valid/invalid transformations to certified projects and compares
outcomes against black-box `pcs certify` / `pcs verify` behavior.
"""

from __future__ import annotations

import json
import shutil
from copy import deepcopy
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

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


def _load_manifest(project: Path) -> dict[str, Any]:
    return json.loads((project / "manifest.json").read_text(encoding="utf-8"))


def _write_manifest(project: Path, manifest: dict[str, Any]) -> None:
    (project / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


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

    for name, fn in INVALID_TRANSFORMS:
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
        # For invalid transforms, either certify fails a claim (still may produce cert)
        # or verify fails. We inspect claim statuses when certify succeeds.
        oracle = False
        if not c_ok:
            oracle = True
        elif c_ok:
            cert = json.loads(
                (work_root / f"run_invalid_{name}" / "evidence" / "certificate.json").read_text(
                    encoding="utf-8"
                )
            )
            statuses = [
                c.get("assessment", {}).get("status")
                for c in cert.get("claims", [])
            ]
            # PASS only if at least one claim is not COMPUTATIONALLY_SUPPORTED
            # OR verify fails.
            if any(s != "COMPUTATIONALLY_SUPPORTED" for s in statuses) or not v_ok:
                oracle = True
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

    # Unit-incompatible transform when applicable
    if any(
        c.get("type") == "unit_compatible"
        for c in _load_manifest(source_project).get("checks", [])
    ):
        proj = work_root / "invalid_incompatible_units"
        if proj.exists():
            shutil.rmtree(proj)
        shutil.copytree(source_project, proj)
        transform_incompatible_units(proj)
        c_ok, v_ok, det = _certify_and_verify(proj, work_root / "run_invalid_units")
        cert = json.loads(
            (work_root / "run_invalid_units" / "evidence" / "certificate.json").read_text(
                encoding="utf-8"
            )
        )
        statuses = [c.get("assessment", {}).get("status") for c in cert.get("claims", [])]
        oracle = any(s != "COMPUTATIONALLY_SUPPORTED" for s in statuses) or not v_ok or not c_ok
        results.append(
            TransformResult(
                name="incompatible_units",
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
        "cases": [asdict(r) for r in results],
        "valid_pass": sum(1 for r in results if r.kind == "valid" and r.passed_oracle),
        "valid_total": sum(1 for r in results if r.kind == "valid"),
        "invalid_pass": sum(1 for r in results if r.kind == "invalid" and r.passed_oracle),
        "invalid_total": sum(1 for r in results if r.kind == "invalid"),
    }
    return report
