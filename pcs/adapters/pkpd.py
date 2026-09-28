from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

from ..checks.units import parse_unit
from ..jsonio import strict_json_load, StrictJSONError


MODEL_TYPE = "one_compartment_iv_bolus"
PD_MODEL_TYPE = "direct_emax"


def _quantity(q: dict[str, Any], name: str, expected_dims: dict[str, int], *, strictly_positive: bool = True) -> tuple[float, str, float]:
    if not isinstance(q, dict):
        raise ValueError(f"{name} must be an object with value and unit")
    value = q.get("value")
    unit = q.get("unit")
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
        raise ValueError(f"{name}.value must be finite numeric")
    value = float(value)
    if strictly_positive and value <= 0:
        raise ValueError(f"{name}.value must be > 0")
    if not isinstance(unit, str) or not unit:
        raise ValueError(f"{name}.unit must be a non-empty string")
    dims, scale = parse_unit(unit)
    if dims != expected_dims:
        raise ValueError(f"{name}.unit={unit!r} has dimensions {dims}, expected {expected_dims}")
    return value, unit, value * scale


def _compatible_quantity(q: dict[str, Any], name: str, reference_unit: str, *, strictly_positive: bool) -> tuple[float, str, float]:
    ref_dims, _ = parse_unit(reference_unit)
    return _quantity(q, name, ref_dims, strictly_positive=strictly_positive)


def validate_one_compartment_iv(spec: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Validate the narrow PK/PD contract and derive canonical SI quantities.

    This checks a computational representation contract only. It does not establish
    that the PK or PD model is empirically adequate for any drug or patient.
    """
    try:
        if spec.get("model_type") != MODEL_TYPE:
            raise ValueError(f"unsupported model_type {spec.get('model_type')!r}")

        dose_v, dose_u, dose_si = _quantity(spec.get("dose"), "dose", {"M": 1})
        vol_v, vol_u, vol_si = _quantity(spec.get("volume"), "volume", {"L": 3})
        cl_v, cl_u, cl_si = _quantity(spec.get("clearance"), "clearance", {"L": 3, "T": -1})

        time_unit = spec.get("time_unit")
        conc_unit = spec.get("concentration_unit")
        if not isinstance(time_unit, str) or not time_unit:
            raise ValueError("time_unit must be a non-empty string")
        if not isinstance(conc_unit, str) or not conc_unit:
            raise ValueError("concentration_unit must be a non-empty string")

        td, ts = parse_unit(time_unit)
        cd, cs = parse_unit(conc_unit)
        if td != {"T": 1}:
            raise ValueError(f"time_unit={time_unit!r} has dimensions {td}, expected time")
        if cd != {"M": 1, "L": -3}:
            raise ValueError(f"concentration_unit={conc_unit!r} has dimensions {cd}, expected mass/volume")

        kel_si = cl_si / vol_si
        c0_si = dose_si / vol_si
        if not (math.isfinite(kel_si) and kel_si > 0 and math.isfinite(c0_si) and c0_si > 0):
            raise ValueError("derived PK parameters must be finite and positive")

        details: dict[str, Any] = {
            "model_type": MODEL_TYPE,
            "pk_equation": "C(t) = (Dose / V) * exp(-(CL / V) * t)",
            "dose": {"value": dose_v, "unit": dose_u, "si_value": dose_si, "si_dimension": "mass"},
            "volume": {"value": vol_v, "unit": vol_u, "si_value": vol_si, "si_dimension": "volume"},
            "clearance": {"value": cl_v, "unit": cl_u, "si_value": cl_si, "si_dimension": "volume/time"},
            "time_unit": time_unit,
            "time_si_scale": ts,
            "concentration_unit": conc_unit,
            "concentration_si_scale": cs,
            "derived": {"kel_per_s": kel_si, "c0_kg_per_m3": c0_si},
            "scope": "representation/unit/positivity contract; not empirical model validation",
        }

        pd = spec.get("pd")
        if pd is not None:
            if not isinstance(pd, dict) or pd.get("model_type") != PD_MODEL_TYPE:
                raise ValueError(f"unsupported pd.model_type {pd.get('model_type') if isinstance(pd, dict) else None!r}")
            effect_unit = pd.get("effect_unit")
            if not isinstance(effect_unit, str) or not effect_unit:
                raise ValueError("pd.effect_unit must be a non-empty string")
            effect_dims, effect_scale = parse_unit(effect_unit)
            e0_v, e0_u, e0_si = _quantity(pd.get("e0"), "pd.e0", effect_dims, strictly_positive=False)
            emax_v, emax_u, emax_si = _quantity(pd.get("emax"), "pd.emax", effect_dims, strictly_positive=True)
            ec50_v, ec50_u, ec50_si = _compatible_quantity(pd.get("ec50"), "pd.ec50", conc_unit, strictly_positive=True)
            details["pd"] = {
                "model_type": PD_MODEL_TYPE,
                "equation": "E(C) = E0 + Emax * C / (EC50 + C)",
                "effect_unit": effect_unit,
                "effect_si_scale": effect_scale,
                "e0": {"value": e0_v, "unit": e0_u, "si_value": e0_si},
                "emax": {"value": emax_v, "unit": emax_u, "si_value": emax_si},
                "ec50": {"value": ec50_v, "unit": ec50_u, "si_value": ec50_si},
            }
        return True, details
    except (KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError) as exc:
        return False, {"model_type": spec.get("model_type"), "error": type(exc).__name__, "message": str(exc)}


def _load_spec(path: str | Path) -> dict[str, Any]:
    obj = strict_json_load(path)
    if not isinstance(obj, dict):
        raise ValueError("PK/PD model specification must be a JSON object")
    return obj


def verify_one_compartment_iv_output(
    spec: dict[str, Any],
    csv_path: str | Path,
    *,
    time_column: str = "time",
    concentration_column: str = "concentration",
    effect_column: str = "effect",
    rel_tol: float = 1e-9,
    abs_tol: float = 1e-12,
) -> tuple[bool, dict[str, Any]]:
    ok, contract = validate_one_compartment_iv(spec)
    if not ok:
        return False, {"contract_valid": False, "contract": contract}
    if rel_tol < 0 or abs_tol < 0 or not math.isfinite(rel_tol) or not math.isfinite(abs_tol):
        return False, {"contract_valid": True, "error": "invalid tolerance"}

    time_scale = contract["time_si_scale"]
    conc_scale = contract["concentration_si_scale"]
    kel_si = contract["derived"]["kel_per_s"]
    c0_si = contract["derived"]["c0_kg_per_m3"]
    pd = contract.get("pd")

    mismatches: list[dict[str, float | int | str]] = []
    row_count = 0
    max_abs = 0.0
    max_rel = 0.0
    max_effect_abs = 0.0
    max_effect_rel = 0.0

    try:
        with Path(csv_path).open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            required = {time_column, concentration_column}
            if pd is not None:
                required.add(effect_column)
            if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
                raise ValueError(f"CSV must contain columns {sorted(required)!r}")
            for i, row in enumerate(reader, start=2):
                t = float(row[time_column])
                observed = float(row[concentration_column])
                if not (math.isfinite(t) and math.isfinite(observed)):
                    raise ValueError(f"row {i} contains non-finite PK numeric values")
                if t < 0:
                    raise ValueError(f"row {i} has negative time")
                t_si = t * time_scale
                expected_si = c0_si * math.exp(-kel_si * t_si)
                expected = expected_si / conc_scale
                abs_err = abs(observed - expected)
                rel_err = abs_err / max(abs(expected), abs_tol if abs_tol > 0 else 1e-300)
                max_abs = max(max_abs, abs_err)
                max_rel = max(max_rel, rel_err)
                row_count += 1
                if not math.isclose(observed, expected, rel_tol=rel_tol, abs_tol=abs_tol):
                    if len(mismatches) < 10:
                        mismatches.append({"row": i, "field": concentration_column, "observed": observed, "expected": expected, "abs_error": abs_err, "rel_error": rel_err})

                if pd is not None:
                    observed_effect = float(row[effect_column])
                    if not math.isfinite(observed_effect):
                        raise ValueError(f"row {i} contains non-finite PD effect")
                    e0_si = pd["e0"]["si_value"]
                    emax_si = pd["emax"]["si_value"]
                    ec50_si = pd["ec50"]["si_value"]
                    expected_effect_si = e0_si + emax_si * expected_si / (ec50_si + expected_si)
                    expected_effect = expected_effect_si / pd["effect_si_scale"]
                    eff_abs = abs(observed_effect - expected_effect)
                    eff_rel = eff_abs / max(abs(expected_effect), abs_tol if abs_tol > 0 else 1e-300)
                    max_effect_abs = max(max_effect_abs, eff_abs)
                    max_effect_rel = max(max_effect_rel, eff_rel)
                    if not math.isclose(observed_effect, expected_effect, rel_tol=rel_tol, abs_tol=abs_tol):
                        if len(mismatches) < 10:
                            mismatches.append({"row": i, "field": effect_column, "observed": observed_effect, "expected": expected_effect, "abs_error": eff_abs, "rel_error": eff_rel})
            if row_count == 0:
                raise ValueError("prediction CSV has no data rows")
    except (OSError, ValueError, OverflowError, ZeroDivisionError) as exc:
        return False, {
            "contract_valid": True,
            "error": type(exc).__name__,
            "message": str(exc),
            "time_column": time_column,
            "concentration_column": concentration_column,
            "effect_column": effect_column if pd is not None else None,
        }

    return (not mismatches), {
        "contract_valid": True,
        "model_type": MODEL_TYPE,
        "pk_equation": contract["pk_equation"],
        "pd_model_type": pd["model_type"] if pd is not None else None,
        "pd_equation": pd["equation"] if pd is not None else None,
        "row_count": row_count,
        "time_column": time_column,
        "concentration_column": concentration_column,
        "effect_column": effect_column if pd is not None else None,
        "rel_tol": rel_tol,
        "abs_tol": abs_tol,
        "max_concentration_abs_error": max_abs,
        "max_concentration_rel_error": max_rel,
        "max_effect_abs_error": max_effect_abs if pd is not None else None,
        "max_effect_rel_error": max_effect_rel if pd is not None else None,
        "mismatch_count_reported": len(mismatches),
        "mismatches": mismatches,
        "scope": "PK/PD output replay against restricted analytic equations; not empirical model validation",
    }


def check_contract_file(spec_path: str | Path) -> tuple[bool, dict[str, Any]]:
    try:
        return validate_one_compartment_iv(_load_spec(spec_path))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return False, {"error": type(exc).__name__, "message": str(exc)}


def check_output_file(spec_path: str | Path, csv_path: str | Path, **kwargs: Any) -> tuple[bool, dict[str, Any]]:
    try:
        spec = _load_spec(spec_path)
        return verify_one_compartment_iv_output(spec, csv_path, **kwargs)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return False, {"error": type(exc).__name__, "message": str(exc)}
