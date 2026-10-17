"""Generate strict-decimal PK/PD prediction tables matching PCS replay semantics.

Used only to freeze immutable fixtures. Tests assert via CLI, not this module.
"""

from __future__ import annotations

import csv
import json
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any, Iterable


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_predictions_via_pcs_adapter(
    model: dict[str, Any],
    csv_path: Path,
    times: Iterable[float | int | str],
) -> None:
    """Freeze a prediction CSV by replaying the same Decimal path PCS uses."""
    from pcs.adapters.pkpd import validate_one_compartment_iv

    ok, contract = validate_one_compartment_iv(model)
    if not ok:
        raise ValueError(f"model failed contract: {contract}")

    with localcontext() as ctx:
        ctx.prec = 50
        time_scale = Decimal(str(contract["time_si_scale"]))
        conc_scale = Decimal(str(contract["concentration_si_scale"]))
        kel = Decimal(str(contract["derived"]["kel_per_s"]))
        c0 = Decimal(str(contract["derived"]["c0_kg_per_m3"]))
        pd = contract.get("pd")
        if pd is not None:
            e0 = Decimal(str(pd["e0"]["si_value"]))
            emax = Decimal(str(pd["emax"]["si_value"]))
            ec50 = Decimal(str(pd["ec50"]["si_value"]))
            effect_scale = Decimal(str(pd["effect_si_scale"]))

        rows: list[list[str]] = []
        for t_raw in times:
            t = Decimal(str(t_raw))
            t_si = t * time_scale
            expected_si = c0 * (-kel * t_si).exp()
            conc = expected_si / conc_scale
            if pd is not None:
                effect_si = e0 + emax * expected_si / (ec50 + expected_si)
                effect = effect_si / effect_scale
                rows.append([format(t, "f"), format(conc, "f"), format(effect, "f")])
            else:
                rows.append([format(t, "f"), format(conc, "f")])

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        if pd is not None:
            w.writerow(["time", "concentration", "effect"])
        else:
            w.writerow(["time", "concentration"])
        w.writerows(rows)


def default_pkpd_model(**overrides: Any) -> dict[str, Any]:
    model: dict[str, Any] = {
        "model_type": "one_compartment_iv_bolus",
        "dose": {"value": 100.0, "unit": "mg"},
        "volume": {"value": 10.0, "unit": "L"},
        "clearance": {"value": 1.0, "unit": "L/h"},
        "time_unit": "h",
        "concentration_unit": "mg/L",
        "pd": {
            "model_type": "direct_emax",
            "e0": {"value": 0.0, "unit": "1"},
            "emax": {"value": 100.0, "unit": "1"},
            "ec50": {"value": 2.0, "unit": "mg/L"},
            "effect_unit": "1",
        },
    }
    model.update(overrides)
    return model
