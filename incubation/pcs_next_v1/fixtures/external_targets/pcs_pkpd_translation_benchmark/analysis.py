from __future__ import annotations

import csv
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "model.json"
OBSERVATIONS_PATH = ROOT / "observations.csv"
PREDICTIONS_PATH = ROOT / "predictions.csv"
FIT_SUMMARY_PATH = ROOT / "fit_summary.json"
TIMES = [0.0, 0.5, 1.0, 2.0, 4.0, 8.0, 12.0, 24.0]


def _predict(model: dict, time: float) -> tuple[float, float]:
    dose = float(model["dose"]["value"])
    volume = float(model["volume"]["value"])
    clearance = float(model["clearance"]["value"])
    pd = model["pd"]
    e0 = float(pd["e0"]["value"])
    emax = float(pd["emax"]["value"])
    ec50 = float(pd["ec50"]["value"])

    concentration = (dose / volume) * math.exp(-(clearance / volume) * time)
    effect = e0 + emax * concentration / (ec50 + concentration)
    return concentration, effect


def main() -> None:
    model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    prediction_rows = []
    for time in TIMES:
        concentration, effect = _predict(model, time)
        prediction_rows.append(
            {
                "time": time,
                "concentration": concentration,
                "effect": effect,
            }
        )

    with PREDICTIONS_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["time", "concentration", "effect"],
        )
        writer.writeheader()
        writer.writerows(prediction_rows)

    with OBSERVATIONS_PATH.open(newline="", encoding="utf-8") as handle:
        observations = list(csv.DictReader(handle))
    if len(observations) != len(prediction_rows):
        raise ValueError("synthetic observation/prediction row counts differ")

    concentration_sq = 0.0
    effect_sq = 0.0
    for observed, predicted in zip(observations, prediction_rows, strict=True):
        concentration_sq += (
            float(observed["concentration"]) - predicted["concentration"]
        ) ** 2
        effect_sq += (float(observed["effect"]) - predicted["effect"]) ** 2

    summary = {
        "n_observations": len(observations),
        "concentration_rmse": math.sqrt(
            concentration_sq / len(observations)
        ),
        "effect_rmse": math.sqrt(effect_sq / len(observations)),
        "acceptance_threshold_prespecified": False,
        "interpretation": (
            "Descriptive residual summary only. No empirical adequacy or "
            "clinical-validity conclusion is encoded by this file."
        ),
    }
    FIT_SUMMARY_PATH.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
