"""certnum CLI — prove / isolate / optimize / verify / explain."""

from __future__ import annotations

import argparse
import json
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any

from certnum import __cert_format_version__, __version__
from certnum.certificate.checker import check_certificate
from certnum.certificate.schema import make_certificate
from certnum.expr.ast import expr_to_json
from certnum.expr.eval import eval_interval, mean_value_enclosure
from certnum.expr.parse import parse_expr
from certnum.interval.interval import Interval
from certnum.opt.branch_bound import optimize
from certnum.root.isolation import isolate_roots


def _load_json(path: str) -> Any:
    return json.loads(Path(path).read_text())


def _dump(obj: Any) -> None:
    print(json.dumps(obj, indent=2, sort_keys=True))


def cmd_prove_interval(args: argparse.Namespace) -> int:
    problem = _load_json(args.problem)
    expr = parse_expr(problem["expr"]) if isinstance(problem["expr"], str) else None
    from certnum.expr.ast import expr_from_json

    if expr is None:
        expr = expr_from_json(problem["expr"])
    box = {k: Interval.from_json(v) if isinstance(v, dict) else Interval.mk(v[0], v[1])
           for k, v in problem["box"].items()}
    method = problem.get("method", "natural")
    if method == "mean_value":
        enc = mean_value_enclosure(expr, box)
    else:
        enc = eval_interval(expr, box)
    if not enc.is_ok:
        _dump({"ok": False, "status": enc.status.name})
        return 1
    cert = make_certificate(
        "interval_enclosure",
        claim={
            "expr": expr_to_json(expr),
            "box": {k: v.to_json() for k, v in box.items()},
            "enclosure": enc.interval.to_json(),
            "method": method,
        },
        witness={"sample_points": []},
        meta={"generator": "certnum.cli", "version": __version__},
    )
    if args.out:
        Path(args.out).write_text(json.dumps(cert, indent=2))
    _dump(cert)
    return 0


def cmd_isolate_roots(args: argparse.Namespace) -> int:
    problem = _load_json(args.problem)
    expr = parse_expr(problem["expr"]) if isinstance(problem["expr"], str) else None
    from certnum.expr.ast import expr_from_json

    if expr is None:
        expr = expr_from_json(problem["expr"])
    var = problem.get("var", "x")
    dom = problem["domain"]
    domain = Interval.mk(dom[0], dom[1]) if isinstance(dom, list) else Interval.from_json(dom)
    max_width = Fraction(problem.get("max_width", "1/1000"))
    roots = isolate_roots(expr, var, domain, max_width=max_width)
    cert = make_certificate(
        "root_isolation",
        claim={"expr": expr_to_json(expr), "var": var, "domain": domain.to_json()},
        witness={"roots": [r.to_json() for r in roots]},
        meta={"generator": "certnum.cli", "version": __version__},
    )
    if args.out:
        Path(args.out).write_text(json.dumps(cert, indent=2))
    _dump(cert)
    return 0


def cmd_optimize(args: argparse.Namespace) -> int:
    problem = _load_json(args.problem)
    expr = parse_expr(problem["expr"]) if isinstance(problem["expr"], str) else None
    from certnum.expr.ast import expr_from_json

    if expr is None:
        expr = expr_from_json(problem["expr"])
    domain = {}
    for k, v in problem["domain"].items():
        domain[k] = Interval.mk(v[0], v[1]) if isinstance(v, list) else Interval.from_json(v)
    tol = Fraction(problem.get("tol", "1/100"))
    method = problem.get("method", "natural")
    result = optimize(expr, domain, tol=tol, method=method)
    cert = make_certificate(
        "global_optimization",
        claim={
            "expr": expr_to_json(expr),
            "domain": {k: v.to_json() for k, v in domain.items()},
            "lower_bound": str(result.lower_bound),
            "upper_bound": str(result.upper_bound),
            "incumbent": None if result.incumbent is None else {k: str(v) for k, v in result.incumbent.items()},
        },
        witness={"coverage": [{k: v.to_json() for k, v in b.items()} for b in result.coverage]},
        meta={"generator": "certnum.cli", "version": __version__, "method": method,
              "subdivisions": result.subdivisions, "gap": str(result.gap)},
    )
    if args.out:
        Path(args.out).write_text(json.dumps(cert, indent=2))
    _dump(cert)
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    cert = _load_json(args.certificate)
    result = check_certificate(cert)
    _dump(result.to_json())
    return 0 if result.accepted else 2


def cmd_explain(args: argparse.Namespace) -> int:
    cert = _load_json(args.certificate)
    _dump({
        "format": cert.get("format"),
        "kind": cert.get("kind"),
        "claim_keys": sorted((cert.get("claim") or {}).keys()),
        "witness_keys": sorted((cert.get("witness") or {}).keys()),
        "interpretation": _interpret(cert.get("kind")),
        "format_version": __cert_format_version__,
    })
    return 0


def _interpret(kind: str) -> str:
    return {
        "interval_enclosure": "Exact image of expression over box lies in claimed interval (natural/MV extension).",
        "root_isolation": "Root existence/uniqueness/exclusion claims on listed intervals.",
        "global_optimization": "Global lower/upper bounds with domain coverage witness.",
        "linear_residual": "||Ax̂ - b||_∞ ≤ claimed residual bound.",
        "markov_step": "Exact one-step distribution propagation for a row-stochastic matrix.",
        "thermo_partition": "Partition-function enclosure for a finite energy model.",
        "ode_linear_scalar": "Solution enclosure for x'=ax+b via certified exp.",
        "expression_equivalence": "Equivalence evidence (simplify or samples).",
    }.get(kind or "", "unknown kind")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="certnum", description="Certified scientific numerics CLI")
    p.add_argument("--version", action="version", version=f"certnum {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("prove-interval", help="Generate interval enclosure certificate")
    s.add_argument("problem", help="problem JSON path")
    s.add_argument("--out", help="write certificate to path")
    s.set_defaults(func=cmd_prove_interval)

    s = sub.add_parser("isolate-roots", help="Isolate roots with certificates")
    s.add_argument("problem")
    s.add_argument("--out")
    s.set_defaults(func=cmd_isolate_roots)

    s = sub.add_parser("optimize", help="Certified global optimization")
    s.add_argument("problem")
    s.add_argument("--out")
    s.set_defaults(func=cmd_optimize)

    s = sub.add_parser("verify", help="Independently verify a certificate")
    s.add_argument("certificate")
    s.set_defaults(func=cmd_verify)

    s = sub.add_parser("explain", help="Explain certificate kind")
    s.add_argument("certificate")
    s.set_defaults(func=cmd_explain)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
