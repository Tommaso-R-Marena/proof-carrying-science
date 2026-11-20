"""Replay both frozen experiments; default verifies the versioned JSON result."""

import argparse
import json
from pathlib import Path

import freeze
import ledger_study
import selection


HERE = Path(__file__).resolve().parent


def render():
    report = {"ledger": ledger_study.study(), "selection": selection.study()}
    freeze.verify(HERE / "frozen")
    return json.dumps(report, sort_keys=True, indent=2) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="write to a new path instead of comparing")
    args = parser.parse_args()
    data = render()
    if args.output:
        with args.output.open("x") as target:
            target.write(data)
    elif (HERE / "results.json").read_text() != data:
        raise SystemExit("replay differs from results.json")
    else:
        print("Both experiments and the frozen inputs reproduce.")
