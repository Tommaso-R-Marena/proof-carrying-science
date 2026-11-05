"""Independent certificate checker.

Recomputes stoichiometric obligations from claim + witness. Never trusts a
producer-declared PASS/FAIL field. Does not grant PCS scientific acceptance.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Dict, List, Sequence

from pcca.certificate.schema import CERT_FORMAT, SUPPORTED_KINDS
from pcca.stoich.matrix import (
    StoichiometricNetwork,
    fire,
    pool,
    _as_fraction,
    _rat_text,
)


@dataclass
class CheckResult:
    accepted: bool
    reasons: List[str]
    details: Dict[str, Any]

    def to_json(self) -> dict:
        return {
            "accepted": self.accepted,
            "reasons": self.reasons,
            "details": self.details,
            "pcs_authority": False,
            "scientific_acceptance": False,
        }


def _fail(msg: str, **details) -> CheckResult:
    return CheckResult(False, [msg], details)


def _ok(msg: str = "ok", **details) -> CheckResult:
    return CheckResult(True, [msg], details)


def _parse_network(claim: dict) -> StoichiometricNetwork:
    species = tuple(claim["species"])
    reactions = tuple(claim["reactions"])
    rows = claim["matrix"]
    if len(rows) != len(species):
        raise ValueError("matrix row count mismatch")
    matrix = []
    for row in rows:
        if len(row) != len(reactions):
            raise ValueError("matrix column count mismatch")
        matrix.append(tuple(_as_fraction(c, "S") for c in row))
    formulas = tuple(claim.get("formulas") or [None] * len(species))
    return StoichiometricNetwork(species, reactions, tuple(matrix), formulas)


def _parse_weights(claim: dict, species: Sequence[str]) -> tuple[Fraction, ...]:
    raw = claim["weights"]
    if isinstance(raw, dict):
        return tuple(_as_fraction(raw[name], name) for name in species)
    return tuple(_as_fraction(v, f"w[{i}]") for i, v in enumerate(raw))


def check_certificate(cert: Dict[str, Any]) -> CheckResult:
    if not isinstance(cert, dict):
        return _fail("certificate must be an object")
    if cert.get("format") != CERT_FORMAT:
        return _fail(f"bad format {cert.get('format')}")
    # Reject executable text and extras that could confuse authority.
    forbidden = {"lean_source", "python_code", "shell", "executable"}
    if forbidden & set(cert.keys()):
        return _fail("certificate contains forbidden executable fields")
    kind = cert.get("kind")
    if kind not in SUPPORTED_KINDS:
        return _fail(f"unsupported kind {kind}")
    claim = cert.get("claim")
    witness = cert.get("witness") or {}
    if not isinstance(claim, dict):
        return _fail("missing claim object")
    # Producer verdict fields are ignored / rejected if used as authority.
    if "verdict" in cert or "pass" in cert or "accepted" in cert:
        return _fail("producer verdict fields are not authoritative")

    if kind == "conservation_law":
        return _check_conservation_law(claim, witness)
    if kind == "trajectory_conservation":
        return _check_trajectory(claim, witness)
    if kind == "conservation_refutation":
        return _check_refutation(claim, witness)
    return _fail("unreachable")


def _check_conservation_law(claim: dict, witness: dict) -> CheckResult:
    try:
        network = _parse_network(claim)
        weights = _parse_weights(claim, network.species)
    except (KeyError, ValueError, TypeError) as exc:
        return _fail(f"claim parse error: {exc}")
    if not network.annihilates(weights):
        # Find first failing reaction for the report.
        for r, rid in enumerate(network.reactions):
            total = sum(weights[s] * network.matrix[s][r] for s in range(network.n_species))
            if total != 0:
                return _fail(
                    f"weights do not annihilate reaction {rid}",
                    residual=_rat_text(total),
                )
        return _fail("weights are not a conservation law")
    # Optional witness: sample fire must preserve pool.
    if "sample_state" in witness or "sample_xi" in witness:
        try:
            state = tuple(
                _as_fraction(v, "state") for v in witness.get("sample_state", [0] * network.n_species)
            )
            xi = tuple(
                _as_fraction(v, "xi") for v in witness.get("sample_xi", [0] * network.n_reactions)
            )
            before = pool(weights, state)
            after = pool(weights, fire(network, xi, state))
            if before != after:
                return _fail("sample fire did not preserve pool", before=_rat_text(before), after=_rat_text(after))
        except (ValueError, TypeError) as exc:
            return _fail(f"witness error: {exc}")
    return _ok(
        "conservation law verified",
        pool_name=claim.get("name"),
        species=list(network.species),
    )


def _check_trajectory(claim: dict, witness: dict) -> CheckResult:
    try:
        network = _parse_network(claim)
        weights = _parse_weights(claim, network.species)
        states = claim["states"]  # list of lists
        xis = claim["xis"]  # list of firing vectors, len = len(states)-1
    except (KeyError, ValueError, TypeError) as exc:
        return _fail(f"claim parse error: {exc}")
    if not network.annihilates(weights):
        return _fail("weights are not a conservation law for this network")
    if len(states) < 2:
        return _fail("trajectory needs at least two states")
    if len(xis) != len(states) - 1:
        return _fail("xis length must be len(states)-1")
    parsed_states = []
    for i, st in enumerate(states):
        try:
            parsed_states.append(tuple(_as_fraction(v, f"state[{i}]") for v in st))
        except ValueError as exc:
            return _fail(str(exc))
        if len(parsed_states[-1]) != network.n_species:
            return _fail(f"state[{i}] dimension mismatch")
    for k, xi_raw in enumerate(xis):
        try:
            xi = tuple(_as_fraction(v, f"xi[{k}]") for v in xi_raw)
        except ValueError as exc:
            return _fail(str(exc))
        if len(xi) != network.n_reactions:
            return _fail(f"xi[{k}] dimension mismatch")
        expected = fire(network, xi, parsed_states[k])
        if expected != parsed_states[k + 1]:
            return _fail(
                f"step {k} is not a stoichiometric fire of the declared network",
                expected=[_rat_text(v) for v in expected],
                claimed=[_rat_text(v) for v in parsed_states[k + 1]],
            )
    pools = [pool(weights, st) for st in parsed_states]
    if any(p != pools[0] for p in pools):
        return _fail(
            "pool not invariant along trajectory",
            pools=[_rat_text(p) for p in pools],
        )
    # Witness may restate expected constant.
    if "expected_pool" in witness:
        try:
            expected_pool = _as_fraction(witness["expected_pool"], "expected_pool")
        except ValueError as exc:
            return _fail(str(exc))
        if pools[0] != expected_pool:
            return _fail(
                "pool does not match expected_pool witness",
                actual=_rat_text(pools[0]),
                expected=_rat_text(expected_pool),
            )
    return _ok(
        "trajectory conservation verified",
        steps=len(xis),
        pool=_rat_text(pools[0]),
    )


def _check_refutation(claim: dict, witness: dict) -> CheckResult:
    """Accept only when weights demonstrably fail to annihilate S."""
    try:
        network = _parse_network(claim)
        weights = _parse_weights(claim, network.species)
    except (KeyError, ValueError, TypeError) as exc:
        return _fail(f"claim parse error: {exc}")
    if network.annihilates(weights):
        return _fail("refutation rejected: weights actually conserve")
    residuals = []
    for r, rid in enumerate(network.reactions):
        total = sum(weights[s] * network.matrix[s][r] for s in range(network.n_species))
        residuals.append({"reaction": rid, "residual": _rat_text(total)})
    if witness.get("must_refute") is False:
        return _fail("witness attempts to suppress refutation")
    return _ok("conservation law refuted", residuals=residuals)


def build_conservation_certificate(
    network: StoichiometricNetwork,
    name: str,
    weights: Sequence[Fraction],
    *,
    kind: str = "conservation_law",
    states=None,
    xis=None,
    expected_pool=None,
) -> dict:
    claim = {
        "name": name,
        "species": list(network.species),
        "reactions": list(network.reactions),
        "matrix": [[_rat_text(network.matrix[s][r]) for r in range(network.n_reactions)] for s in range(network.n_species)],
        "formulas": list(network.formulas) if network.formulas else None,
        "weights": {network.species[i]: _rat_text(weights[i]) for i in range(network.n_species)},
    }
    witness: Dict[str, Any] = {}
    cert_kind = kind
    if kind == "trajectory_conservation":
        if states is None or xis is None:
            raise ValueError("trajectory certificates require states and xis")
        claim["states"] = [[_rat_text(v) for v in st] for st in states]
        claim["xis"] = [[_rat_text(v) for v in xi] for xi in xis]
        if expected_pool is not None:
            witness["expected_pool"] = _rat_text(expected_pool)
    elif kind == "conservation_refutation":
        cert_kind = "conservation_refutation"
        witness["must_refute"] = True
    else:
        cert_kind = "conservation_law"
        # Include a sample fire witness.
        zero_state = [Fraction(0)] * network.n_species
        if network.n_species:
            zero_state[0] = Fraction(1)
        sample_xi = [Fraction(0)] * network.n_reactions
        if network.n_reactions:
            sample_xi[0] = Fraction(1, 10)
        witness["sample_state"] = [_rat_text(v) for v in zero_state]
        witness["sample_xi"] = [_rat_text(v) for v in sample_xi]

    body = {
        "format": CERT_FORMAT,
        "kind": cert_kind,
        "claim": claim,
        "witness": witness,
        "limitations": [
            "Mathematical stoichiometric conservation only.",
            "Does not establish continuum ODE accuracy.",
            "Does not establish empirical/biological validity.",
            "Does not grant PCS package authority or scientific acceptance.",
        ],
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    body["sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return body
