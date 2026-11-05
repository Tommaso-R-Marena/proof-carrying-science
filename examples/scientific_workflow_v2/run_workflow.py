"""Authored CC0 reference workflow: exact normal equations on real CC0 data.

This source is deliberately independent of the PCS adapter and uses a different
calculation (uncentered normal equations rather than centered statistics).
"""
import csv
import json
from fractions import Fraction
from pathlib import Path


def run(root: Path):
    contract = json.loads((root / "contract.json").read_text())
    rows = list(csv.DictReader((root / contract["data_path"]).open(newline="")))
    points, excluded = [], []
    for index, row in enumerate(rows, 1):
        xraw, yraw = row[contract["x"]["column"]], row[contract["y"]["column"]]
        if xraw == "NA" or yraw == "NA":
            excluded.append(index)
        else:
            points.append((Fraction(xraw) * Fraction(contract["x"]["scale"]),
                           Fraction(yraw) * Fraction(contract["y"]["scale"])))
    n = len(points)
    sx = sum(x for x, _ in points)
    sy = sum(y for _, y in points)
    sx2 = sum(x*x for x, _ in points)
    sxy = sum(x*y for x, y in points)
    slope = (n*sxy - sx*sy) / (n*sx2 - sx*sx)
    intercept = (sy - slope*sx) / n
    residuals = [y - intercept - slope*x for x, y in points]
    result = {"format": "pcs-linear-calibration-result-v2", "total_rows": len(rows),
        "complete_rows": n, "excluded_rows": excluded, "intercept_kg": str(intercept),
        "slope_kg_per_m": str(slope), "residual_sum_squares_kg2": str(sum(r*r for r in residuals)),
        "residual_sum_zero": sum(residuals) == 0,
        "residual_predictor_inner_product_zero": sum(x*r for (x, _), r in zip(points, residuals)) == 0}
    (root / contract["result_path"]).write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    print(json.dumps(run(Path(__file__).resolve().parent)))
