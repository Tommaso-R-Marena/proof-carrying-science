"""CLI authority path for PCS Next (offline, no production mutation)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core.canonical import loads_strict
from .core.errors import PcsNextError
from .pilot.intake import freeze_intake, load_intake, write_lock
from .pilot.runner import PilotRunner
from .reviewer.assurance_card import export_card
from .reviewer.independent import review_package
from .trust.policy import load_policy, pin_policy
from .translation.formalize import formalize_text
from .falsification.challenges import run_pk_suite, negative_result_report
from .demos.theophylline_demo import run_demo as run_theoph_demo
from .demos.provenance import verify_manifest


def _print(obj) -> None:
    print(json.dumps(obj, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pcs-next", description="PCS Next isolated assurance candidate")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_freeze = sub.add_parser("freeze-intake", help="Freeze an intake object")
    p_freeze.add_argument("intake")
    p_freeze.add_argument("--policy")
    p_freeze.add_argument("--out", required=True)

    p_run = sub.add_parser("run-pilot", help="Run synthetic/bounded pilot")
    p_run.add_argument("project_root")
    p_run.add_argument("--intake", required=True)
    p_run.add_argument("--policy", required=True)
    p_run.add_argument("--work", required=True)
    p_run.add_argument("--repo-root")

    p_rev = sub.add_parser("review", help="Independently review a package directory")
    p_rev.add_argument("package_dir")
    p_rev.add_argument("--policy")

    p_card = sub.add_parser("assurance-card", help="Export assurance card from report JSON")
    p_card.add_argument("report")
    p_card.add_argument("--out", required=True)

    p_form = sub.add_parser("formalize", help="Deterministic Claim IR formalization")
    p_form.add_argument("--id", required=True)
    p_form.add_argument("--text", required=True)

    p_chal = sub.add_parser("challenge-pk", help="Run PK scientific challenges")
    p_chal.add_argument("--model", required=True)
    p_chal.add_argument("--predictions", required=True)
    p_chal.add_argument("--claim", required=True)

    p_jd = sub.add_parser("journal-demos", help="Verify manifests / run theophylline journal demo")
    p_jd.add_argument("--out", required=True)
    p_jd.add_argument("--verify-only", action="store_true")

    args = parser.parse_args(argv)
    try:
        if args.cmd == "freeze-intake":
            intake = load_intake(args.intake)
            policy = pin_policy(loads_strict(Path(args.policy).read_bytes())) if args.policy else None
            lock = freeze_intake(intake, acceptance_policy=policy.raw if policy else None)
            write_lock(lock, args.out, overwrite=True)
            _print({"ok": True, "out": args.out, "intake_semantic_hash": lock["intake_semantic_hash"]})
            return 0
        if args.cmd == "run-pilot":
            intake = load_intake(args.intake)
            policy = load_policy(args.policy)
            runner = PilotRunner(args.work, policy=policy, repo_root=args.repo_root)
            report = runner.run_synthetic(args.project_root, intake)
            _print(report)
            return 0
        if args.cmd == "review":
            policy = load_policy(args.policy) if args.policy else None
            receipt = review_package(args.package_dir, receiver_policy=policy)
            _print(receipt)
            return 0
        if args.cmd == "assurance-card":
            report = loads_strict(Path(args.report).read_bytes())
            card = export_card(report, args.out)
            _print({"ok": True, "card_hash": card.get("format"), "out": args.out})
            return 0
        if args.cmd == "formalize":
            _print(formalize_text(args.id, args.text))
            return 0
        if args.cmd == "journal-demos":
            if args.verify_only:
                _print(verify_manifest())
                return 0
            _print(run_theoph_demo(args.out))
            return 0
        if args.cmd == "challenge-pk":
            model = loads_strict(Path(args.model).read_bytes())
            preds = [float(x) for x in Path(args.predictions).read_text().split()]
            results = run_pk_suite(model, preds, args.claim)
            _print(negative_result_report(results) | {"results": results})
            return 0
    except PcsNextError as exc:
        _print({"ok": False, **exc.to_dict()})
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
