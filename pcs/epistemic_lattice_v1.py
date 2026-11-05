"""Falsifier-carrying epistemic obligation lattice (experimental).

Revolutionary PCS research line: every empirical/computational claim must carry
explicit falsifiers; evidence classes cannot silently promote; composition cannot
hide a refuted dependency; support is defeasible under new observations.

This module grants **no** package authority, Lean-authority acceptance, biological
adequacy, clinical validity, or scientific truth. The production verifier remains
the authority boundary. Aristotle external traces are not training inputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .canonical_json import canonicalize_jcs_bytes

FORMAT = "pcs-epistemic-lattice-v1"
RECEIPT_FORMAT = "pcs-epistemic-lattice-receipt-v1"
MAX_BYTES = 256 * 1024
MAX_CLAIMS = 64
MAX_ATOMS = 128
MAX_LITERALS = 32
CLASSES = ("formal", "computational", "empirical", "provenance")
STATUSES = ("unsound", "open", "supported", "refuted")
REQUIRES_FALSIFIER = frozenset({"empirical", "computational"})


class EpistemicLatticeError(ValueError):
    pass


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _load(raw: bytes) -> Any:
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
        raise EpistemicLatticeError("bounded JSON bytes required")

    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise EpistemicLatticeError("duplicate JSON key")
            out[key] = value
        return out

    return json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(EpistemicLatticeError("finite JSON required")),
    )


def _atom(value: Any) -> str:
    if not isinstance(value, str) or not value or len(value) > 128 or "\n" in value:
        raise EpistemicLatticeError("atom labels must be short nonempty strings")
    return value


def _literal(obj: Any) -> dict:
    if not isinstance(obj, dict) or set(obj) != {"atom", "expects"}:
        raise EpistemicLatticeError("literal requires exact fields atom, expects")
    expects = obj["expects"]
    if not isinstance(expects, bool):
        raise EpistemicLatticeError("literal expects must be Boolean")
    return {"atom": _atom(obj["atom"]), "expects": expects}


def _claim(obj: Any) -> dict:
    if not isinstance(obj, dict):
        raise EpistemicLatticeError("claim must be an object")
    required = {"id", "class", "dependencies", "falsifiers", "support_requires"}
    if set(obj) != required:
        raise EpistemicLatticeError("claim requires exact fields: " + ", ".join(sorted(required)))
    ident = obj["id"]
    klass = obj["class"]
    if not isinstance(ident, str) or not ident or len(ident) > 64:
        raise EpistemicLatticeError("claim id must be a short nonempty string")
    if klass not in CLASSES:
        raise EpistemicLatticeError(f"unsupported evidence class: {klass}")
    deps = obj["dependencies"]
    falsifiers = obj["falsifiers"]
    supports = obj["support_requires"]
    if not isinstance(deps, list) or len(deps) > MAX_CLAIMS:
        raise EpistemicLatticeError("dependencies must be a bounded list")
    if any(not isinstance(d, str) or not d for d in deps) or len(deps) != len(set(deps)):
        raise EpistemicLatticeError("dependencies must be unique nonempty strings")
    if ident in deps:
        raise EpistemicLatticeError("self-dependency is unsound")
    if not isinstance(falsifiers, list) or len(falsifiers) > MAX_LITERALS:
        raise EpistemicLatticeError("falsifiers must be a bounded list")
    if not isinstance(supports, list) or len(supports) > MAX_LITERALS:
        raise EpistemicLatticeError("support_requires must be a bounded list")
    parsed_f = [_literal(x) for x in falsifiers]
    parsed_s = [_literal(x) for x in supports]
    if klass in REQUIRES_FALSIFIER and not parsed_f:
        raise EpistemicLatticeError(
            f"{klass} claims must declare at least one falsifier (Popperian barrier)"
        )
    return {
        "id": ident,
        "class": klass,
        "dependencies": list(deps),
        "falsifiers": parsed_f,
        "support_requires": parsed_s,
    }


def _evidence(obj: Any) -> dict:
    if not isinstance(obj, dict) or set(obj) != {"claim_id", "class", "pass"}:
        raise EpistemicLatticeError("evidence requires exact fields claim_id, class, pass")
    if not isinstance(obj["claim_id"], str) or not obj["claim_id"]:
        raise EpistemicLatticeError("evidence claim_id must be a nonempty string")
    if obj["class"] not in CLASSES:
        raise EpistemicLatticeError("evidence class unsupported")
    if not isinstance(obj["pass"], bool):
        raise EpistemicLatticeError("evidence pass must be Boolean")
    return {"claim_id": obj["claim_id"], "class": obj["class"], "pass": obj["pass"]}


def load_package(raw: bytes) -> dict:
    data = _load(raw)
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise EpistemicLatticeError(f"format must be {FORMAT}")
    required = {"format", "claims", "evidence", "observations"}
    if set(data) != required:
        raise EpistemicLatticeError("package requires exact fields format, claims, evidence, observations")
    claims_raw = data["claims"]
    evidence_raw = data["evidence"]
    observations_raw = data["observations"]
    if not isinstance(claims_raw, list) or not 1 <= len(claims_raw) <= MAX_CLAIMS:
        raise EpistemicLatticeError("claims must be a nonempty bounded list")
    if not isinstance(evidence_raw, list) or len(evidence_raw) > MAX_CLAIMS:
        raise EpistemicLatticeError("evidence must be a bounded list")
    if not isinstance(observations_raw, dict) or set(observations_raw) != {"atoms"}:
        raise EpistemicLatticeError("observations require exact field atoms")
    atoms = observations_raw["atoms"]
    if not isinstance(atoms, dict) or len(atoms) > MAX_ATOMS:
        raise EpistemicLatticeError("atoms must be a bounded object")
    parsed_atoms = {}
    for key, value in atoms.items():
        label = _atom(key)
        if not isinstance(value, bool):
            raise EpistemicLatticeError("observation atoms must be Boolean")
        if label in parsed_atoms:
            raise EpistemicLatticeError("duplicate observation atom")
        parsed_atoms[label] = value
    claims = [_claim(c) for c in claims_raw]
    ids = [c["id"] for c in claims]
    if len(ids) != len(set(ids)):
        raise EpistemicLatticeError("duplicate claim ids")
    id_set = set(ids)
    for claim in claims:
        for dep in claim["dependencies"]:
            if dep not in id_set:
                raise EpistemicLatticeError(f"unknown dependency: {dep}")
    evidence = [_evidence(e) for e in evidence_raw]
    for item in evidence:
        if item["claim_id"] not in id_set:
            raise EpistemicLatticeError(f"evidence references unknown claim: {item['claim_id']}")
    return {
        "format": FORMAT,
        "claims": claims,
        "evidence": evidence,
        "observations": {"atoms": parsed_atoms},
    }


def _matches(literal: dict, atoms: dict[str, bool]) -> bool:
    if literal["atom"] not in atoms:
        return False
    return atoms[literal["atom"]] is literal["expects"]


def _dep_join(statuses: list[str]) -> str:
    if any(s == "unsound" for s in statuses):
        return "unsound"
    if any(s == "refuted" for s in statuses):
        return "refuted"
    if any(s == "open" for s in statuses):
        return "open"
    if not statuses or all(s == "supported" for s in statuses):
        return "supported"
    return "open"


def _evidence_for(evidence: list[dict], claim_id: str, klass: str) -> bool | None:
    for item in evidence:
        if item["claim_id"] == claim_id and item["class"] == klass:
            return item["pass"]
    return None


def _eval_claim(claim: dict, dep_statuses: list[str], evidence: list[dict], atoms: dict[str, bool]) -> str:
    joined = _dep_join(dep_statuses)
    if joined == "unsound":
        return "unsound"
    if any(_matches(f, atoms) for f in claim["falsifiers"]):
        return "refuted"
    if joined == "refuted":
        return "open"
    if joined == "open":
        return "open"
    passed = _evidence_for(evidence, claim["id"], claim["class"])
    if passed is True and all(_matches(s, atoms) for s in claim["support_requires"]):
        return "supported"
    return "open"


def evaluate(package: dict) -> dict:
    """Independently evaluate a loaded epistemic package."""
    claims = package["claims"]
    evidence = package["evidence"]
    atoms = package["observations"]["atoms"]
    by_id = {c["id"]: c for c in claims}
    done: dict[str, str] = {}
    remaining = set(by_id)
    # Fuel-bounded topological evaluation
    for _ in range(len(claims) + 1):
        ready = sorted(
            ident
            for ident in remaining
            if all(dep in done for dep in by_id[ident]["dependencies"])
        )
        if not ready:
            break
        for ident in ready:
            deps = [done[d] for d in by_id[ident]["dependencies"]]
            done[ident] = _eval_claim(by_id[ident], deps, evidence, atoms)
            remaining.remove(ident)
    for ident in remaining:
        done[ident] = "unsound"
    table = [{"claim_id": c["id"], "class": c["class"], "status": done[c["id"]]} for c in claims]
    statuses = [row["status"] for row in table]
    return {
        "format": RECEIPT_FORMAT,
        "package_sha256": None,  # filled by replay()
        "claims": table,
        "aggregate": {
            "all_supported": bool(statuses) and all(s == "supported" for s in statuses),
            "any_refuted": any(s == "refuted" for s in statuses),
            "any_unsound": any(s == "unsound" for s in statuses),
            "any_open": any(s == "open" for s in statuses),
        },
        "scientific_acceptance": False,
        "pcs_authority": False,
        "limitations": [
            "Experimental epistemic lattice only; not production package authority.",
            "Does not establish biological, clinical, or regulatory adequacy.",
            "Formal class claims still require an independent formal checker outside this lattice.",
            "Observation atoms are declared Boolean labels, not sensors or statistical estimators.",
        ],
    }


def replay(raw: bytes) -> dict:
    """Fail-closed receiving entry: parse, evaluate, bind exact package bytes."""
    package = load_package(raw)
    # Canonicalize through the validated object so semantically identical payloads
    # with different key orders still bind the same meaning after validation.
    canonical = canonicalize_jcs_bytes({
        "format": package["format"],
        "claims": package["claims"],
        "evidence": package["evidence"],
        "observations": package["observations"],
    })
    result = evaluate(package)
    result["package_sha256"] = sha(canonical)
    result["input_sha256"] = sha(raw)
    result["canonical_sha256"] = sha(canonical)
    return result


def export_receipt(path: Path, result: dict) -> None:
    path = Path(path)
    if path.exists():
        raise EpistemicLatticeError(f"refusing to overwrite existing receipt: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonicalize_jcs_bytes(result))


def run_campaign(fixtures_dir: Path) -> dict:
    """Execute positive/negative controls from a fixture directory."""
    fixtures_dir = Path(fixtures_dir)
    cases = sorted(
        path for path in fixtures_dir.glob("*.json")
        if not path.name.endswith(".expect.json")
    )
    if not cases:
        raise EpistemicLatticeError("no fixture JSON files found")
    results = []
    for path in cases:
        raw = path.read_bytes()
        meta_path = path.with_name(path.stem + ".expect.json")
        if not meta_path.is_file():
            raise EpistemicLatticeError(f"missing expectation file: {meta_path.name}")
        expect = _load(meta_path.read_bytes())
        try:
            receipt = replay(raw)
            error = None
        except EpistemicLatticeError as exc:
            receipt = None
            error = str(exc)
        ok = False
        if expect.get("reject") is True:
            ok = error is not None
        else:
            if receipt is None:
                ok = False
            else:
                want = expect.get("statuses", {})
                got = {row["claim_id"]: row["status"] for row in receipt["claims"]}
                ok = got == want and receipt["aggregate"] == expect.get("aggregate", receipt["aggregate"])
        results.append({
            "fixture": path.name,
            "ok": ok,
            "error": error,
            "statuses": None if receipt is None else {
                row["claim_id"]: row["status"] for row in receipt["claims"]
            },
        })
    return {
        "format": "pcs-epistemic-lattice-campaign-v1",
        "passed": all(r["ok"] for r in results),
        "cases": results,
        "scientific_acceptance": False,
    }


def command(args: argparse.Namespace) -> int:
    try:
        if args.campaign:
            report = run_campaign(Path(args.campaign))
            out = Path(args.output)
            if out.exists() and not args.force:
                raise EpistemicLatticeError("refusing to overwrite campaign report")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(canonicalize_jcs_bytes(report))
            print(json.dumps({
                "passed": report["passed"],
                "cases": len(report["cases"]),
                "scientific_acceptance": False,
                "output": str(out.resolve()),
            }))
            return 0 if report["passed"] else 1
        raw = Path(args.package).read_bytes()
        result = replay(raw)
        export_receipt(Path(args.output), result)
        print(json.dumps({
            "all_supported": result["aggregate"]["all_supported"],
            "any_refuted": result["aggregate"]["any_refuted"],
            "any_unsound": result["aggregate"]["any_unsound"],
            "scientific_acceptance": False,
            "pcs_authority": False,
            "output": str(Path(args.output).resolve()),
        }))
        return 0 if result["aggregate"]["all_supported"] and not result["aggregate"]["any_unsound"] else 1
    except (EpistemicLatticeError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({
            "accepted": False,
            "error": str(exc),
            "scientific_acceptance": False,
            "pcs_authority": False,
        }))
        return 2


def register(subparsers) -> None:
    parser = subparsers.add_parser(
        "epistemic-lattice-v1",
        help=(
            "experimental falsifier-carrying epistemic obligation lattice; "
            "no scientific or package authority"
        ),
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--package", help="epistemic package JSON")
    group.add_argument("--campaign", help="directory of fixture + expect JSON pairs")
    parser.add_argument("--output", required=True, help="new receipt or campaign report path")
    parser.add_argument("--force", action="store_true", help="overwrite campaign report only")
    parser.set_defaults(func=command)
