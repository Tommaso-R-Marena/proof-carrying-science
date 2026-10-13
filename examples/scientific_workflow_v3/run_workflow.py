"""Authored CC0 synthetic transport computation; never empirical measurements.

Independent edge-flux producer, using no PCS imports. The receiver reconstructs
matrix coefficients and evolves matrix rows instead.
"""
import csv
import json
from fractions import Fraction
from pathlib import Path


def run(root):
    contract = json.loads((root / "contract.json").read_text())
    cells = contract["cells"]
    names = [cell["id"] for cell in cells]
    volumes = [Fraction(cell["volume"]) for cell in cells]
    state = [Fraction(cell["initial_concentration"]) for cell in cells]
    dt = Fraction(contract["time_step"])
    rows = [["0", *(str(x) for x in state)]]
    for index in range(contract["steps"]):
        amount_changes = [Fraction() for _ in state]
        for edge in contract["edges"]:
            i, j = names.index(edge["left"]), names.index(edge["right"])
            transported = dt * Fraction(edge["conductance"]) * (state[i] - state[j])
            amount_changes[i] -= transported
            amount_changes[j] += transported
        state = [value + change/volume for value, change, volume in zip(state, amount_changes, volumes)]
        rows.append([str(dt * (index + 1)), *(str(x) for x in state)])
    with (root / contract["data_path"]).open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["time_s", *names])
        writer.writerows(rows)
    return {"origin": contract["data_origin"], "states": len(rows), "cell_count": len(cells), "maximum_text_length": max(len(x) for row in rows for x in row)}


if __name__ == "__main__":
    print(json.dumps(run(Path(__file__).resolve().parent)))
