"""Issue public text, freeze scoped predictions, then compare both locked systems."""

import argparse
import gzip
import json
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

from ...external import blind_eval, typed_language_scoped, typed_language_v2
from ...external.finite_replay import canonical, digest
from ...scripts.replay_blind_protocols import ARCHIVE_SHA256, ROOT, run
from .replay import HERE, LOCK, extra, sha
from .reviewer.replay import PINS

MODULE = (
    "research.proof_carrying_causal_reasoning_v1.qualification.language_ii.replay_scope"
)
SCOPED = "050283c177b46f57c3e4505706ae0123f7afdf66f0d719bae4f503525feb19f0"


CHECKED = "037957ad5b69f0d1b0bcb34bc77bb073f35e3532ab8bcb357ebe72462cf090f3"


def freeze(source, dest, checked):
    solve = typed_language_scoped.predict if checked else typed_language_v2.predict
    batch = json.loads(source.read_bytes())
    if batch["protocol"] != "A":
        raise ValueError("requires public text")
    rows = [{"id": r["id"], **solve(r["task"])} for r in batch["rows"]]
    data = (
        canonical({"protocol": "A", "public_sha256": digest(batch), "rows": rows})
        + b"\n"
    )
    with dest.open("xb") as f:
        f.write(data)
    return sha(data)


def compare(old, new, refs):
    records = []
    for r, s, ref in zip(old, new, refs, strict=True):
        if r["id"] != s["id"]:
            raise ValueError("misaligned batch")
        if r["prediction"] != s["prediction"]:
            records.append(
                {
                    "id": r["id"],
                    "before": r["prediction"],
                    "after": s["prediction"],
                    "reference": ref,
                    "reason": s["reason"],
                }
            )
    return records


def replay(archive, record, checked):
    flags = ["--checked"] if checked else []
    if (
        sha(archive.read_bytes()) != ARCHIVE_SHA256
        or sha(Path(typed_language_scoped.__file__).read_bytes()) != CHECKED
        or sha(Path(typed_language_v2.__file__).read_bytes()) != SCOPED
        or sha(Path(typed_language_v2.original.__file__).read_bytes()) != LOCK
    ):
        raise ValueError("archive or predictor implementation differs")
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        with zipfile.ZipFile(archive) as z:
            for n in ("cladder-v1-q-balanced.json", "cladder-v1-meta-models.json"):
                (directory / n).write_bytes(z.read(n))
        public, output = directory / "public", directory / "output"
        run("blind_eval", "prepare", "A", directory, public)
        frozen = (
            subprocess.check_output(
                [sys.executable, "-m", MODULE, "predict", public, output, *flags],
                cwd=ROOT,
            )
            .decode()
            .strip()
        )
        questions, models = blind_eval.load(directory)
        report = blind_eval.score(questions, models, public, output, frozen)
        old_raw = gzip.decompress((HERE / "typed.rows.json.gz").read_bytes())
        if (
            sha(old_raw)
            != json.loads((HERE / "report.json").read_bytes())["predictions_sha256"]
        ):
            raise ValueError("historical text rows changed")
        old = json.loads(old_raw)["rows"]
        new = json.loads(output.read_bytes())["rows"]
        old_scores, curve = extra(new, old, questions)
        changes = compare(old, new, [q["answer"] for q in questions])
        report.update(old_scores)
        report["changed_verdicts"] = changes
        report["original_predictor_sha256"] = LOCK
        report["scoped_predictor_sha256"] = SCOPED
        if checked:
            interim_raw = gzip.decompress((HERE / "scope-rows.json.gz").read_bytes())
            if (
                sha(interim_raw)
                != json.loads((HERE / "scope-report.json").read_bytes())[
                    "predictions_sha256"
                ]
            ):
                raise ValueError("scope candidate rows changed")
            report["feasible_predictor_sha256"] = CHECKED
            report["changed_from_scope_candidate"] = compare(
                json.loads(interim_raw)["rows"], new, [q["answer"] for q in questions]
            )
            count = 0
            for issue, row in zip(
                json.loads(public.read_bytes())["rows"], new, strict=True
            ):
                if row["prediction"] is None or row["claim"]["kind"] == "adjustment":
                    continue
                parsed = typed_language_v2.interpret(issue["task"])
                if not typed_language_scoped.verify_model(
                    parsed, row["feasibility_witness"]
                ):
                    raise ValueError("rejected feasibility witness")
                count += 1
            report["verified_feasibility_models"] = count
        report["curve_points"] = len(curve["points"])
        report["curve_sha256"] = sha(canonical(curve) + b"\n")
        case_raw = (HERE / "reviewer" / "cases.json").read_bytes()
        if sha(case_raw) != PINS["cases"]:
            raise ValueError("reviewed cases changed")
        cases = json.loads(case_raw)
        prior = json.loads((HERE / "reviewer" / "results.json").read_bytes())["phase2"][
            "rows"
        ]
        review_public = directory / "review_public"
        review_output = directory / "review_predictions"
        review_public.write_bytes(
            canonical(
                {
                    "protocol": "A",
                    "rows": [{"id": c["id"], "task": c["public"]} for c in cases],
                }
            )
            + b"\n"
        )
        subprocess.run(
            [
                sys.executable,
                "-m",
                MODULE,
                "predict",
                review_public,
                review_output,
                *flags,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            cwd=ROOT,
        )
        review_rows = json.loads(review_output.read_bytes())["rows"]
        counts = Counter()
        groups = defaultdict(Counter)
        for case, r in zip(cases, review_rows, strict=True):
            if r["id"] != case["id"]:
                raise ValueError("misaligned reviewer batch")
            a, b = r["prediction"], case["reference"]
            outcome = (
                ("required_abstention" if b is None else "missed_answer")
                if a is None
                else ("correct" if a == b else "incorrect")
            )
            counts[outcome] += 1
            groups[case["family"]][outcome] += 1
        report["reviewer"] = {
            "counts": counts,
            "groups": groups,
            "changed_verdicts": compare(
                prior, review_rows, [c["reference"] for c in cases]
            ),
            "cases_sha256": PINS["cases"],
        }
        artifacts = {
            "scope-report.json": json.dumps(report, sort_keys=True, indent=2).encode()
            + b"\n",
            "scope-coverage.json.gz": canonical(curve) + b"\n",
            "scope-rows.json.gz": output.read_bytes(),
            "scope-reviewer.json.gz": review_output.read_bytes(),
        }
        for name, raw in artifacts.items():
            path = HERE / (name.replace("scope-", "feasible-") if checked else name)
            if record:
                with path.open("xb") as out:
                    out.write(
                        gzip.compress(raw, mtime=0) if name.endswith(".gz") else raw
                    )
            else:
                stored = path.read_bytes()
                if raw != (gzip.decompress(stored) if name.endswith(".gz") else stored):
                    raise ValueError("scored artifact differs: " + name)
        print(
            report["overall"],
            len(changes),
            "changed",
            report["reviewer"]["counts"],
            len(report["reviewer"]["changed_verdicts"]),
            "reviewer changes",
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    cmds = parser.add_subparsers(dest="command", required=True)
    predictor = cmds.add_parser("predict")
    predictor.add_argument("public", type=Path)
    predictor.add_argument("output", type=Path)
    scorer = cmds.add_parser("score")
    scorer.add_argument("archive", type=Path)
    scorer.add_argument("--checked", action="store_true")
    predictor.add_argument("--checked", action="store_true")
    scorer.add_argument("--record", action="store_true")
    args = parser.parse_args()
    if args.command == "predict":
        print(freeze(args.public, args.output, args.checked))
    else:
        replay(args.archive, args.record, args.checked)
