"""Rebuild the proofs, exhaustively compare small domains, and replay two signed edges."""
from __future__ import annotations

import argparse
import itertools
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from . import receiver as r


def run(args, workdir, env):
    proc = subprocess.run(args, cwd=workdir, env=env, capture_output=True, text=True, timeout=1800 if args[0] == "leanchecker" else 240)
    if proc.returncode:
        raise RuntimeError(f"{args[0]} returned {proc.returncode}\n" + proc.stderr + proc.stdout[-4000:])
    return proc.stdout


def prove(out, env):
    source_tree = r.HERE.parent.parent / "assurance_mirage_v1" / "formal"
    paths = [source_tree / (m + ".lean") for m in ("AssuranceMirage", "ObservationAdequacy")]
    paths += [*r.KERNEL_SOURCES, r.HERE / "RobustObservation.lean", r.HERE / "Audit.lean"]
    closures = {}
    for path in paths:
        local = out / path.name
        shutil.copyfile(path, local)
        log = run(["lean", "-DwarningAsError=true", "-o", path.stem + ".olean", path.name], out, env)
        (out / (path.stem + ".log")).write_text(log)
        if path.stem in {"HardReview", "RobustObservation"}:
            theorems = set(re.findall(r"^theorem (\w+)", local.read_text(), re.MULTILINE))
            records = re.findall(rf"^'{path.stem}\.(\w+)' depends on axioms: \[([^\]]+)\]$", log, re.MULTILINE)
            if {name for name, _ in records} != theorems or not records:
                raise ValueError("incomplete theorem audit")
            for name, axioms in records:
                if set(axioms.split(", ")) - {"propext", "Quot.sound"}:
                    raise ValueError("unexpected axiom: " + name)
                closures[f"{path.stem}.{name}"] = axioms.split(", ")
    (out / "ReviewReplay.lean").write_text("import RobustObservation\nimport ReceiptCheck\n")
    run(["lean", "-o", "ReviewReplay.olean", "ReviewReplay.lean"], out, env)
    log = run(["leanchecker", "--fresh", "ReviewReplay"], out, env)
    (out / "fresh-kernel.log").write_text(log)
    return closures


def monitoring(lines):
    checked = conflicts = unreachable = decisive = pairs = separated = 0
    for width in range(5):
        size = 2**width
        # Build report sets explicitly by choosing subsets of coordinates to flip.
        masks = []
        for radius in range(width + 1):
            masks.append({sum(1 << i for i in flips) for k in range(radius + 1)
                          for flips in itertools.combinations(range(width), k)})
        for left, right in itertools.product(range(size), repeat=2):
            for a, b in itertools.product(range(width + 1), repeat=2):
                possibles = ({left ^ change for change in masks[a]}, {right ^ change for change in masks[b]})
                overlap = possibles[0] & possibles[1]
                if bool(overlap) != ((left ^ right).bit_count() <= a + b):
                    raise ValueError("confusability threshold disagreement")
                cells = ["-" if (z in possibles[0]) == (z in possibles[1]) else
                         "0" if z in possibles[0] else "1" for z in range(size)]
                if next(lines) != "".join(cells):
                    raise ValueError(f"monitor disagrees at {(width, left, right, a, b)}")
                pairs += 1
                separated += not overlap
                checked += size
                conflicts += len(overlap)
                unreachable += size - len(possibles[0] | possibles[1])
                decisive += cells.count("0") + cells.count("1")
    if next(lines, None) is not None:
        raise ValueError("unexpected monitoring rows")
    return dict(report_verdicts=checked, opposite_label_pairs_with_radii=pairs, separable_pairs=separated,
                conflicting=conflicts, unseen=unreachable, decisive=decisive, disagreements=0)


def promotions(lines):
    inputs = [
        ([(6, False), (4, True)], [(2, True), (3, True), (5, False)]),
        ([(7, True), (4, False), (5, True)], [(3, False), (3, True), (2, False), (6, True)]),
    ]
    checked = accepted = 0
    for hard, measured in inputs:
        for old in range(256):
            line = "".join("1" if r.python_evaluation(old, new, hard, measured).startswith("true ")
                           else "0" for new in range(256))
            if next(lines) != line:
                raise ValueError(f"promotion disagreement on {hard=} {old=}")
            checked += len(line)
            accepted += line.count("1")
    if next(lines, None) is not None:
        raise ValueError("unexpected promotion rows")
    return dict(transitions=checked, accepted=accepted, rejected=checked-accepted, disagreements=0)


def signed_lineage(out, env):
    fixture = json.loads((r.HERE / "signed_fixture.json").read_bytes())
    (out / "review.json").write_bytes(r.canonical(fixture["review"]))
    (out / "reviewer.pub").write_bytes(bytes.fromhex(fixture["public_key_hex"]))
    (out / "state0.json").write_bytes(r.canonical(fixture["seed"]))
    for mask in (18, 22, 30):
        (out / f"mask{mask}.json").write_bytes(r.canonical(
            {"schema": "pcs.detector-table/v1", "admission": "jointChannel", "mask": mask}))
    for index, (old, new, edge) in enumerate(zip((18, 22), (22, 30), fixture["envelopes"], strict=True)):
        envelope = f"edge{index+1}.json"
        (out / envelope).write_bytes(r.canonical(edge))
        result = run([sys.executable, str(r.HERE / "receiver.py"), f"state{index}.json", "reviewer.pub",
                      "review.json", envelope, f"mask{old}.json", f"mask{new}.json"], out, env)
        (out / f"state{index+1}.json").write_text(result)
    if (out / "state2.json").read_bytes() != r.canonical(fixture["terminal"]):
        raise ValueError("signed fixture lineage differs")
    return fixture["terminal"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("new_directory", type=Path)
    out = parser.parse_args().new_directory.resolve()
    out.mkdir()
    env = {**os.environ, "LEAN_PATH": str(out)}
    version = run(["lean", "--version"], out, env).strip()
    if "version 4.28.0," not in version:
        raise ValueError("expected Lean 4.28.0")
    report = dict(lean=version, closures=prove(out, env))
    for kind, checker in (("monitoring", monitoring), ("promotions", promotions)):
        output = run(["lean", "--run", "Audit.lean", kind], out, env)
        report[kind] = checker(iter(output.splitlines()))
        report[kind]["wire_sha256"] = r.digest(output.encode("ascii"))
    report["terminal"] = signed_lineage(out, env)
    result = json.dumps(report, sort_keys=True, indent=2) + "\n"
    (out / "replay-summary.json").write_text(result)
    print(result, end="")


if __name__ == "__main__":
    main()
