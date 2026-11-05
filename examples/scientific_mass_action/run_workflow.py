"""Authored synthetic standard-library workflow. No PCS import or private data.

This script is explicitly run by the experiment owner, never by PCS discovery.
It implements its own simultaneous stoichiometric matrix update for the declared
finite Euler calculation. Biology names identify formulas, not validated kinetics.
"""
import csv
import io
import json
from fractions import Fraction
from pathlib import Path

MODEL = Path("model.json")
OUTPUT = Path("observations.csv")
model = json.loads(MODEL.read_text(encoding="utf-8"))
names = [entry["id"] for entry in model["species"]]
state = [Fraction(model["initial"][name]) for name in names]
step = Fraction(model["time_step"])
matrix = []
for reaction in model["reactions"]:
    column = [0] * len(names)
    for direction, sign in (("reactants", -1), ("products", 1)):
        for item in reaction[direction]:
            column[names.index(item["species"])] += sign * item["coefficient"]
    matrix.append(column)
rows = [[Fraction(0), *state]]
for iteration in range(model["steps"]):
    fluxes = []
    for reaction in model["reactions"]:
        flux = Fraction(reaction["rate_constant"])
        for item in reaction["reactants"]:
            flux *= state[names.index(item["species"])] ** item["coefficient"]
        fluxes.append(flux)
    state = [value + step * sum(column[i] * flux for column, flux in zip(matrix, fluxes))
             for i, value in enumerate(state)]
    rows.append([(iteration + 1) * step, *state])
buffer = io.StringIO(newline="")
writer = csv.writer(buffer, lineterminator="\n")
writer.writerow(["time_s", *names])
writer.writerows([[str(value) for value in row] for row in rows])
OUTPUT.write_text(buffer.getvalue(), encoding="utf-8")
