"""CLI for the Heterogeneous Evidence Composition Kernel."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .canonical import canonicalize
from .compose import CompositeClaim, EvidenceAtom, compose_receipt
from .falsify import run_attack_campaign
from .levels import Level, meet, meet_list
from .predictive import PredictiveObligation, observe_against_prediction, discharge
from .receiver import verify_package
from .theory_ir import TheoryObject, evaluate_theory


def _write(path: Path | None, obj: object) -> None:
    raw = canonicalize(obj) + b"\n"
    if path is None:
        sys.stdout.buffer.write(raw)
    else:
        path.write_bytes(raw)


def cmd_meet(args: argparse.Namespace) -> int:
    levels = [Level(x) for x in args.levels]
    result = {
        "format": "heck-meet-v1",
        "levels": [l.value for l in levels],
        "meet": meet_list(levels).value if len(levels) != 2 else meet(levels[0], levels[1]).value,
    }
    _write(Path(args.output) if args.output else None, result)
    return 0


def cmd_compose(args: argparse.Namespace) -> int:
    atoms = [EvidenceAtom.from_dict(a) for a in json.loads(Path(args.atoms).read_text())]
    claim = CompositeClaim.from_dict(json.loads(Path(args.claim).read_text()))
    receipt = compose_receipt(atoms, claim)
    _write(Path(args.output) if args.output else None, receipt)
    return 0 if receipt["accepted"] else 1


def cmd_verify(args: argparse.Namespace) -> int:
    result = verify_package(Path(args.package))
    _write(Path(args.output) if args.output else None, result)
    return 0 if result["accepted"] else 1


def cmd_predict(args: argparse.Namespace) -> int:
    obl = PredictiveObligation.from_prediction(
        id=args.id,
        theory_id=args.theory_id,
        prediction=json.loads(Path(args.prediction).read_text()),
    )
    observed = json.loads(Path(args.observation).read_text())
    obs = observe_against_prediction(obl, observed, tolerance=args.tolerance)
    updated = discharge(obl, obs)
    result = {
        "format": "heck-predict-v1",
        "obligation": obl.to_dict(),
        "observation_kind": obs.kind.value,
        "status": updated.status.value,
        "to_level": updated.status.to_level().value,
    }
    _write(Path(args.output) if args.output else None, result)
    return 0 if updated.status.value == "empirically_supported" else 2


def cmd_theory(args: argparse.Namespace) -> int:
    theory = TheoryObject.from_dict(json.loads(Path(args.theory).read_text()))
    atoms_path = Path(args.atoms) if args.atoms else None
    atoms = (
        [EvidenceAtom.from_dict(a) for a in json.loads(atoms_path.read_text())]
        if atoms_path
        else []
    )
    if args.observations:
        observations = json.loads(Path(args.observations).read_text())
        for obl_id, payload in observations.items():
            theory.apply_observation(obl_id, payload, tolerance=args.tolerance)
    result = evaluate_theory(theory, atoms)
    _write(Path(args.output) if args.output else None, result)
    return 0 if result["scientific_closure"] else 1


def cmd_attacks(args: argparse.Namespace) -> int:
    result = run_attack_campaign()
    _write(Path(args.output) if args.output else None, result)
    return 0 if result["caught"] == result["attacks"] else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="heck",
        description="HECK — Heterogeneous Evidence Composition Kernel (incubation)",
    )
    p.add_argument("--version", action="version", version=f"heck {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("meet", help="compute assurance-level meet")
    m.add_argument("levels", nargs="+")
    m.add_argument("--output")
    m.set_defaults(func=cmd_meet)

    c = sub.add_parser("compose", help="independently compose leaf evidence")
    c.add_argument("--atoms", required=True)
    c.add_argument("--claim", required=True)
    c.add_argument("--output")
    c.set_defaults(func=cmd_compose)

    v = sub.add_parser("verify", help="verify a HECK package directory")
    v.add_argument("package")
    v.add_argument("--output")
    v.set_defaults(func=cmd_verify)

    pr = sub.add_parser("predict", help="discharge a predictive obligation")
    pr.add_argument("--id", required=True)
    pr.add_argument("--theory-id", required=True)
    pr.add_argument("--prediction", required=True)
    pr.add_argument("--observation", required=True)
    pr.add_argument("--tolerance", type=float, default=0.0)
    pr.add_argument("--output")
    pr.set_defaults(func=cmd_predict)

    th = sub.add_parser("theory", help="evaluate a theory object with predictive closure")
    th.add_argument("--theory", required=True)
    th.add_argument("--atoms")
    th.add_argument("--observations")
    th.add_argument("--tolerance", type=float, default=0.0)
    th.add_argument("--output")
    th.set_defaults(func=cmd_theory)

    at = sub.add_parser("attacks", help="run conflation-attack campaign")
    at.add_argument("--output")
    at.set_defaults(func=cmd_attacks)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
