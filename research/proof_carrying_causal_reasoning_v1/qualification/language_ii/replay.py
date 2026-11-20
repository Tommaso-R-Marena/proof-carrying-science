"""Issue the pinned public text, freeze predictions, score and compare with archived evidence."""

import argparse
import gzip
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

from ...external import blind_eval
from ...external.finite_replay import canonical
from ...scripts.replay_blind_protocols import ARCHIVE_SHA256, ROOT, run

HERE = Path(__file__).resolve().parent
BASELINE = HERE.parent / "blind_protocols"
MOD = "research.proof_carrying_causal_reasoning_v1.qualification.language_ii.freeze"
LOCK = "5e94ee9f087d30a87339c72e8a38127f104d37eec7d5bf36d3b0ae7d9bb6988b"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def extra(rows, baseline, questions):
    by_kind = defaultdict(list)
    reasons = Counter()
    overlap = defaultdict(Counter)
    uncertain = defaultdict(Counter)
    structural = Counter()
    for r, old, q in zip(rows, baseline, questions, strict=True):
        if old["id"] != r["id"] or q["question_id"] != r["id"]:
            raise ValueError("mismatched IDs")
        before, pred, target = old["prediction"], r["prediction"], q["answer"]
        reasons[r["reason"]] += 1
        kind = r["claim"]["kind"] if r["claim"] else "unparsed"
        correct = None if pred is None else pred == target
        by_kind[kind].append(correct)
        for label, answer in [("old", before), ("new", pred)]:
            group = (
                "both_answer"
                if before and pred
                else "baseline_only"
                if before
                else "typed_only"
                if pred
                else "neither"
            )
            overlap[group][
                label
                + (
                    "_abstained"
                    if answer is None
                    else "_correct"
                    if answer == target
                    else "_incorrect"
                )
            ] += 1
        if pred is None:
            continue
        dest = structural
        if r["interval"]:
            lo, hi = map(Fraction, r["interval"])
            clearance = lo if pred == "yes" else -hi
            if clearance <= 0:
                raise ValueError("uncertified sign")
            dest = uncertain[clearance]
        dest["correct" if correct else "incorrect"] += 1
    # Include the no-numerical-answer endpoint, then add all tied margins
    # together as the acceptance threshold falls. Every achievable point.
    correct, wrong = structural["correct"], structural["incorrect"]
    curve = [["structural_only", correct, wrong, len(rows) - correct - wrong]]
    for threshold, count in sorted(uncertain.items(), reverse=True):
        correct += count["correct"]
        wrong += count["incorrect"]
        curve.append([str(threshold), correct, wrong, len(rows) - correct - wrong])
    return (
        {
            "claim_kind": {k: blind_eval._summary(v) for k, v in by_kind.items()},
            "decision_reason": dict(reasons),
            "paired_comparison": dict(overlap),
        },
        {
            "columns": [
                "minimum_absolute_signed_contrast",
                "correct",
                "incorrect",
                "abstained",
            ],
            "points": curve,
        },
    )


def replay(archive, save):
    if sha(archive.read_bytes()) != ARCHIVE_SHA256:
        raise ValueError("pinned CLadder archive required")
    if sha((HERE.parents[1] / "external/typed_language.py").read_bytes()) != LOCK:
        raise ValueError("predictor changed since protocol freeze")
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        public, predictions = folder / "public", folder / "predictions"
        with zipfile.ZipFile(archive) as z:
            for name in ("cladder-v1-q-balanced.json", "cladder-v1-meta-models.json"):
                (folder / name).write_bytes(z.read(name))
        run("blind_eval", "prepare", "A", folder, public)
        frozen = (
            subprocess.check_output(
                [sys.executable, "-m", MOD, public, predictions], cwd=ROOT
            )
            .decode()
            .strip()
        )
        questions, models = blind_eval.load(folder)
        report = blind_eval.score(questions, models, public, predictions, frozen)
        original = json.loads(
            gzip.decompress((BASELINE / "A.rows.json.gz").read_bytes())
        )
        baseline_report = json.loads((BASELINE / "A.report.json").read_bytes())
        if (
            sha(canonical(original) + b"\n") != baseline_report["predictions_sha256"]
            or original["public_sha256"] != report["public_sha256"]
        ):
            raise ValueError("historical baseline or public projection differs")
        metrics, curve = extra(
            json.loads(predictions.read_bytes())["rows"], original["rows"], questions
        )
        report.update(metrics)
        report.update(
            {
                "baseline": baseline_report["overall"],
                "predictor_sha256": LOCK,
                "protocol_file_sha256": sha((HERE / "PROTOCOL.md").read_bytes()),
                "curve_sha256": sha(canonical(curve) + b"\n"),
                "curve_points": len(curve["points"]),
            }
        )
        artifacts = {
            "report.json": json.dumps(report, sort_keys=True, indent=2).encode()
            + b"\n",
            "typed.rows.json.gz": predictions.read_bytes(),
            "coverage.json.gz": canonical(curve) + b"\n",
        }
        for name, content in artifacts.items():
            path = HERE / name
            if save:
                with path.open("xb") as out:
                    out.write(
                        gzip.compress(content, mtime=0)
                        if name.endswith(".gz")
                        else content
                    )
            else:
                stored = path.read_bytes()
                if content != (
                    gzip.decompress(stored) if name.endswith(".gz") else stored
                ):
                    raise ValueError("replay differs: " + name)
        print(
            json.dumps(report["overall"], sort_keys=True),
            report["curve_points"],
            "curve points",
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument(
        "--record", action="store_true", help="create new evidence files exclusively"
    )
    args = parser.parse_args()
    replay(args.archive, args.record)
