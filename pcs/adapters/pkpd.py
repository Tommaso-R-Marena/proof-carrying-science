from __future__ import annotations

import json
import math
import re
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path
from typing import Any

from ..checks.splits import parse_strict_csv
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


def _decimal(value: Any) -> Decimal:
    """Convert a validated numeric value through its canonical decimal spelling.

    PCS certificates commit replay diagnostics into their semantic hash. Using
    platform libm for transcendental calculations made those diagnostics vary by
    a few ulps across environments. Decimal with an explicit precision keeps the
    narrow analytic PK/PD replay deterministic for fixed input bytes.
    """
    return Decimal(str(value))


# High-assurance numeric surface, mirrored by the Lean authority
# (formal/PCS/V2/PKPDCheck.lean, `decimalQ`): a plain decimal spelling with an optional
# exponent of at most 4 digits and magnitude <= 400. `Decimal()` alone would also accept
# surrounding whitespace, '+', '.5', '5.', '1_0', 'Infinity' and 'NaN'; those fail closed.
_STRICT_DECIMAL = re.compile(r"-?[0-9]+(?:\.[0-9]+)?(?:[eE]([+-]?)([0-9]{1,4}))?")
MAX_DECIMAL_EXPONENT = 400


def strict_decimal_text(text: str) -> Decimal:
    """Parse a prediction-table or tolerance number under the strict decimal grammar."""
    m = _STRICT_DECIMAL.fullmatch(text)
    if m is None:
        raise ValueError(f"number {text!r} is outside the strict decimal subset")
    if m.group(2) is not None and int(m.group(2)) > MAX_DECIMAL_EXPONENT:
        raise ValueError(f"number {text!r} exceeds the strict exponent bound")
    return Decimal(text)


def _decimal_isclose(a: Decimal, b: Decimal, *, rel_tol: Decimal, abs_tol: Decimal) -> bool:
    return abs(a - b) <= max(abs_tol, rel_tol * max(abs(a), abs(b)))


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

    pd = contract.get("pd")
    mismatches: list[dict[str, float | int | str]] = []
    row_count = 0

    try:
        # Fixed precision and Decimal.exp deliberately remove platform libm from
        # certificate semantics. Inputs still cross the explicit JSON/CSV parser
        # TCB, but identical parsed values now yield identical replay diagnostics.
        with localcontext() as ctx:
            ctx.prec = 50
            time_scale = _decimal(contract["time_si_scale"])
            conc_scale = _decimal(contract["concentration_si_scale"])
            kel_si = _decimal(contract["derived"]["kel_per_s"])
            c0_si = _decimal(contract["derived"]["c0_kg_per_m3"])
            rel_tol_d = _decimal(rel_tol)
            abs_tol_d = _decimal(abs_tol)
            rel_floor = abs_tol_d if abs_tol_d > 0 else Decimal("1e-300")

            if pd is not None:
                e0_si = _decimal(pd["e0"]["si_value"])
                emax_si = _decimal(pd["emax"]["si_value"])
                ec50_si = _decimal(pd["ec50"]["si_value"])
                effect_scale = _decimal(pd["effect_si_scale"])

            max_abs = Decimal(0)
            max_rel = Decimal(0)
            max_effect_abs = Decimal(0)
            max_effect_rel = Decimal(0)

            # Strict CSV subset (pcs-strict-csv-v1), identical to the Lean authority's
            # `PCS.V2.Csv.parseCsv`; csv.DictReader's lenient dialect is not used.
            header_b, rows_b = parse_strict_csv(Path(csv_path).read_bytes())
            header = [h.decode("utf-8") for h in header_b]
            required = {time_column, concentration_column}
            if pd is not None:
                required.add(effect_column)
            if not required.issubset(set(header)):
                raise ValueError(f"CSV must contain columns {sorted(required)!r}")
            col = {name: idx for idx, name in enumerate(header)}
            for i, row_b in enumerate(rows_b, start=2):
                row = {name: row_b[idx].decode("utf-8") for name, idx in col.items()}
                t = strict_decimal_text(row[time_column])
                observed = strict_decimal_text(row[concentration_column])
                if not (t.is_finite() and observed.is_finite()):
                    raise ValueError(f"row {i} contains non-finite PK numeric values")
                if t < 0:
                    raise ValueError(f"row {i} has negative time")

                t_si = t * time_scale
                expected_si = c0_si * (-kel_si * t_si).exp()
                expected = expected_si / conc_scale
                abs_err = abs(observed - expected)
                rel_err = abs_err / max(abs(expected), rel_floor)
                max_abs = max(max_abs, abs_err)
                max_rel = max(max_rel, rel_err)
                row_count += 1

                if not _decimal_isclose(observed, expected, rel_tol=rel_tol_d, abs_tol=abs_tol_d):
                    if len(mismatches) < 10:
                        mismatches.append({
                            "row": i,
                            "field": concentration_column,
                            "observed": float(observed),
                            "expected": float(expected),
                            "abs_error": float(abs_err),
                            "rel_error": float(rel_err),
                        })

                if pd is not None:
                    observed_effect = strict_decimal_text(row[effect_column])
                    if not observed_effect.is_finite():
                        raise ValueError(f"row {i} contains non-finite PD effect")
                    expected_effect_si = e0_si + emax_si * expected_si / (ec50_si + expected_si)
                    expected_effect = expected_effect_si / effect_scale
                    eff_abs = abs(observed_effect - expected_effect)
                    eff_rel = eff_abs / max(abs(expected_effect), rel_floor)
                    max_effect_abs = max(max_effect_abs, eff_abs)
                    max_effect_rel = max(max_effect_rel, eff_rel)
                    if not _decimal_isclose(observed_effect, expected_effect, rel_tol=rel_tol_d, abs_tol=abs_tol_d):
                        if len(mismatches) < 10:
                            mismatches.append({
                                "row": i,
                                "field": effect_column,
                                "observed": float(observed_effect),
                                "expected": float(expected_effect),
                                "abs_error": float(eff_abs),
                                "rel_error": float(eff_rel),
                            })

            if row_count == 0:
                raise ValueError("prediction CSV has no data rows")
    except (OSError, ValueError, OverflowError, ZeroDivisionError, InvalidOperation) as exc:
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
        "max_concentration_abs_error": float(max_abs),
        "max_concentration_rel_error": float(max_rel),
        "max_effect_abs_error": float(max_effect_abs) if pd is not None else None,
        "max_effect_rel_error": float(max_effect_rel) if pd is not None else None,
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

def check_peak_concentration_file(
    spec_path: str | Path,
    csv_path: str | Path,
    *,
    concentration_column: str = "concentration",
    upper_bound: Any,
    unit: str,
) -> tuple[bool, dict[str, Any]]:
    """Check the maximum concentration reported in a committed prediction table.

    The bound is interpreted in the model-declared concentration unit. This proves
    a property of the committed table only; it is not a continuous-time maximum
    theorem and is not a clinical safety threshold.
    """
    try:
        spec = _load_spec(spec_path)
        contract_ok, contract = validate_one_compartment_iv(spec)
        if not contract_ok:
            return False, {"contract_valid": False, "contract": contract}

        model_unit = spec.get("concentration_unit")
        if not isinstance(unit, str) or not unit:
            raise ValueError("unit must be a non-empty string")
        if unit != model_unit:
            raise ValueError(
                f"threshold unit {unit!r} must exactly match model concentration_unit {model_unit!r}"
            )

        if isinstance(upper_bound, bool):
            raise ValueError("upper_bound must not be a boolean")
        if isinstance(upper_bound, int):
            bound = Decimal(upper_bound)
        elif isinstance(upper_bound, float):
            if not math.isfinite(upper_bound):
                raise ValueError("upper_bound must be finite")
            bound = strict_decimal_text(str(upper_bound))
        elif isinstance(upper_bound, str):
            bound = strict_decimal_text(upper_bound)
        else:
            raise ValueError(
                "upper_bound must be an integer, float, or strict decimal string"
            )
        if not bound.is_finite() or bound < 0:
            raise ValueError("upper_bound must be finite and non-negative")

        header_b, rows_b = parse_strict_csv(Path(csv_path).read_bytes())
        header = [h.decode("utf-8") for h in header_b]
        if concentration_column not in header:
            raise ValueError(
                f"CSV must contain concentration column {concentration_column!r}"
            )
        if not rows_b:
            raise ValueError("prediction CSV has no data rows")
        idx = header.index(concentration_column)

        maximum: Decimal | None = None
        for row_number, row_b in enumerate(rows_b, start=2):
            value = strict_decimal_text(row_b[idx].decode("utf-8"))
            if not value.is_finite() or value < 0:
                raise ValueError(
                    f"row {row_number} concentration must be finite and non-negative"
                )
            maximum = value if maximum is None else max(maximum, value)
            if value > bound:
                return False, {
                    "contract_valid": True,
                    "concentration_column": concentration_column,
                    "unit": unit,
                    "upper_bound": str(bound),
                    "row_count": len(rows_b),
                    "first_exceeding_row": row_number,
                    "first_exceeding_value": str(value),
                    "scope": (
                        "maximum concentration in committed prediction rows only; "
                        "not a continuous-time or clinical safety claim"
                    ),
                }

        assert maximum is not None
        return True, {
            "contract_valid": True,
            "concentration_column": concentration_column,
            "unit": unit,
            "upper_bound": str(bound),
            "row_count": len(rows_b),
            "maximum_reported_concentration": str(maximum),
            "scope": (
                "maximum concentration in committed prediction rows only; "
                "not a continuous-time or clinical safety claim"
            ),
        }
    except (
        OSError,
        UnicodeDecodeError,
        ValueError,
        OverflowError,
        InvalidOperation,
        StrictJSONError,
        json.JSONDecodeError,
    ) as exc:
        return False, {
            "error": type(exc).__name__,
            "message": str(exc),
            "concentration_column": concentration_column,
            "unit": unit,
            "scope": (
                "maximum concentration in committed prediction rows only; "
                "not a continuous-time or clinical safety claim"
            ),
        }

