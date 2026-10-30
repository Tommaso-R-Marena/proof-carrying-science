"""Bounded, exact-rational scientific contracts, outside PCS kernel authority.

Only explicitly supplied mass-action models are supported. Discovery never runs
project code. These executable predicates do not establish biochemical adequacy,
continuous-ODE correctness, or correctness of the producing implementation.
"""
from __future__ import annotations

import csv
import hashlib
import io
import re
from fractions import Fraction
from typing import Any

from .canonical_json import canonicalize_jcs_bytes
from .checks.chemistry import parse_formula, reaction_balanced
from .checks.units import parse_unit
from .jsonio import strict_json_loads

FORMAT = "pcs-mass-action-contract-v1"
REPORT_FORMAT = "pcs-mass-action-replay-v1"
MAX_BYTES = 2 * 1024 * 1024
MAX_STEPS = 128
MAX_SPECIES = 16
MAX_REACTIONS = 32
MAX_FRACTION_BITS = 4096
_IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,63}")
_NUMBER = re.compile(r"-?(?:[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]{1,3})?|[0-9]+/[1-9][0-9]*)")


class ScientificContractError(ValueError):
    pass


class ScientificResourceLimit(ScientificContractError):
    pass


def digest(value: Any) -> str:
    return hashlib.sha256(canonicalize_jcs_bytes(value)).hexdigest()


def _bounded(value: Fraction) -> Fraction:
    if max(value.numerator.bit_length(), value.denominator.bit_length()) > MAX_FRACTION_BITS:
        raise ScientificResourceLimit("exact rational exceeds 4096-bit numerator/denominator limit")
    return value


def rational(value: Any, label: str) -> Fraction:
    # Binary floats, booleans and permissive Fraction syntax never cross this boundary.
    if not isinstance(value, str) or len(value) > 128 or not _NUMBER.fullmatch(value):
        raise ScientificContractError(f"{label}: expected a bounded decimal or rational string")
    try:
        return _bounded(Fraction(value))
    except (ValueError, ZeroDivisionError, OverflowError) as exc:
        raise ScientificContractError(f"{label}: invalid rational") from exc


def rational_text(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _object(value: Any, fields: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != fields:
        raise ScientificContractError(f"{label}: fields must be exactly {sorted(fields)}")
    return value


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ScientificContractError(f"{label}: invalid identifier")
    return value


def _unit(value: Any, label: str) -> dict[str, int]:
    if not isinstance(value, str) or not value or len(value) > 256:
        raise ScientificContractError(f"{label}: unit expression exceeds the supported grammar")
    # Bound integer exponent conversion and Lean replay work before parsing.
    if any(len(x) > 3 or abs(int(x)) > 64 for x in re.findall(r"\^(-?[0-9]+)", value)):
        raise ScientificContractError(f"{label}: exponent outside [-64,64]")
    try:
        return parse_unit(value)[0]
    except ValueError as exc:
        raise ScientificContractError(f"{label}: {exc}") from exc


def required_rate_unit(order: int) -> str:
    # Concentration is amount / volume, time is seconds. Scale conversions are
    # intentionally unsupported; identical symbols and scales are required.
    powers = {"mol": 1 - order, "m": 3 * (order - 1), "s": -1}
    return "*".join(name if power == 1 else f"{name}^{power}"
                    for name, power in powers.items() if power) or "1"


def validate_contract(value: Any) -> dict:
    contract = _object(value, {"format", "question", "species", "reactions", "initial",
        "concentration_unit", "time_unit", "time_step", "steps", "absolute_tolerance",
        "relative_tolerance", "assumptions", "license"}, "contract")
    if contract["format"] != FORMAT:
        raise ScientificContractError("unsupported scientific contract version")
    if not isinstance(contract["question"], str) or not 1 <= len(contract["question"]) <= 4096:
        raise ScientificContractError("question must be a nonempty bounded string")
    if contract["license"] != "CC0-1.0":
        raise ScientificContractError("this authored-synthetic adapter requires explicit CC0-1.0 rights")
    if contract["time_unit"] != "s" or contract["concentration_unit"] != "mol/L":
        raise ScientificContractError("supported units are exactly s and mol/L; unit conversion requires a new contract")
    if (type(contract["steps"]) is not int or not 1 <= contract["steps"] <= MAX_STEPS):
        raise ScientificContractError(f"steps must be an integer in [1,{MAX_STEPS}]")
    if rational(contract["time_step"], "time_step") <= 0:
        raise ScientificContractError("time_step must be positive")
    for name in ("absolute_tolerance", "relative_tolerance"):
        if rational(contract[name], name) < 0:
            raise ScientificContractError(f"{name} must be nonnegative")
    species = contract["species"]
    if not isinstance(species, list) or not 1 <= len(species) <= MAX_SPECIES:
        raise ScientificContractError("species count outside supported bounds")
    names: list[str] = []
    for entry in species:
        _object(entry, {"id", "formula"}, "species")
        name = _identifier(entry["id"], "species.id")
        if name in names:
            raise ScientificContractError("duplicate species identifier")
        names.append(name)
        formula = entry["formula"]
        if not isinstance(formula, str) or not 1 <= len(formula) <= 128:
            raise ScientificContractError("formula must be a bounded flat molecular formula")
        if any(len(x) > 3 or int(x) > 256 for x in re.findall(r"[0-9]+", formula)):
            raise ScientificContractError("molecular atom counts exceed 256")
        try:
            atoms = parse_formula(formula)
        except ValueError as exc:
            raise ScientificContractError(f"unsupported_formula: {exc}") from exc
        if any(number <= 0 for number in atoms.values()):
            raise ScientificContractError("species atom counts must be positive")
    if not isinstance(contract["initial"], dict) or set(contract["initial"]) != set(names):
        raise ScientificContractError("initial concentrations must name each species exactly once")
    for name, concentration in contract["initial"].items():
        if rational(concentration, f"initial.{name}") < 0:
            raise ScientificContractError("initial concentrations must be nonnegative")
    reactions = contract["reactions"]
    if not isinstance(reactions, list) or not 1 <= len(reactions) <= MAX_REACTIONS:
        raise ScientificContractError("reaction count outside supported bounds")
    reaction_ids: set[str] = set()
    for reaction in reactions:
        _object(reaction, {"id", "reactants", "products", "rate_constant", "rate_unit"}, "reaction")
        reaction_id = _identifier(reaction["id"], "reaction.id")
        if reaction_id in reaction_ids:
            raise ScientificContractError("duplicate reaction identifier")
        reaction_ids.add(reaction_id)
        for side in ("reactants", "products"):
            items = reaction[side]
            if not isinstance(items, list) or not 1 <= len(items) <= MAX_SPECIES:
                raise ScientificContractError("each reaction side must be nonempty and bounded")
            seen: set[str] = set()
            for item in items:
                _object(item, {"species", "coefficient"}, f"reaction.{side}")
                name, coefficient = item["species"], item["coefficient"]
                if name not in names or name in seen:
                    raise ScientificContractError("unknown or duplicate reaction species")
                if type(coefficient) is not int or not 1 <= coefficient <= 8:
                    raise ScientificContractError("stoichiometric coefficients must be integers in [1,8]")
                seen.add(name)
        if sum(item["coefficient"] for item in reaction["reactants"]) > 8:
            raise ScientificContractError("mass-action order exceeds eight")
        if rational(reaction["rate_constant"], "rate_constant") < 0:
            raise ScientificContractError("rate constants must be nonnegative")
        _unit(reaction["rate_unit"], "rate_unit")
    assumptions = contract["assumptions"]
    if not isinstance(assumptions, list) or not 1 <= len(assumptions) <= 32:
        raise ScientificContractError("explicit applicability assumptions are required")
    ids: set[str] = set()
    for assumption in assumptions:
        _object(assumption, {"id", "statement"}, "assumption")
        aid = _identifier(assumption["id"], "assumption.id")
        if aid in ids:
            raise ScientificContractError("duplicate assumption identifier")
        ids.add(aid)
        if not isinstance(assumption["statement"], str) or not 1 <= len(assumption["statement"]) <= 4096:
            raise ScientificContractError("assumption statement must be bounded and nonempty")
    return contract


def load_contract(raw: bytes) -> dict:
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
        raise ScientificResourceLimit("contract byte limit exceeded")
    try:
        value = strict_json_loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise ScientificContractError(f"invalid contract JSON: {exc}") from exc
    return validate_contract(value)


def primitive_checks(contract: dict) -> list[dict]:
    validate_contract(contract)
    formulas = {entry["id"]: entry["formula"] for entry in contract["species"]}
    checks = []
    for reaction in contract["reactions"]:
        rid = reaction["id"]
        checks.append({"id": f"balance_{rid}", "type": "reaction_balance",
            **{side: [{"formula": formulas[item["species"]], "coefficient": item["coefficient"]}
                      for item in reaction[side]] for side in ("reactants", "products")}})
        checks.append({"id": f"dimensions_{rid}", "type": "unit_compatible",
            "left_unit": reaction["rate_unit"],
            "right_unit": required_rate_unit(sum(item["coefficient"] for item in reaction["reactants"]))})
    return checks


def simulate(contract: dict) -> list[tuple[Fraction, dict[str, Fraction]]]:
    """Simultaneous explicit Euler, not an exact solution of a continuous ODE."""
    validate_contract(contract)
    state = {name: rational(value, name) for name, value in contract["initial"].items()}
    step = rational(contract["time_step"], "time_step")
    trajectory = [(Fraction(0), state.copy())]
    for index in range(contract["steps"]):
        delta = {name: Fraction(0) for name in state}
        for reaction in contract["reactions"]:
            rate = rational(reaction["rate_constant"], "rate_constant")
            for item in reaction["reactants"]:
                rate = _bounded(rate * _bounded(state[item["species"]] ** item["coefficient"]))
            change = _bounded(step * rate)
            for side, sign in (("reactants", -1), ("products", 1)):
                for item in reaction[side]:
                    name = item["species"]
                    delta[name] = _bounded(delta[name] + sign * item["coefficient"] * change)
        state = {name: _bounded(value + delta[name]) for name, value in state.items()}
        trajectory.append((_bounded((index + 1) * step), state.copy()))
    return trajectory


def trajectory_csv(contract: dict) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    names = [entry["id"] for entry in contract["species"]]
    writer.writerow(["time_s", *names])
    for time, state in simulate(contract):
        writer.writerow([rational_text(time), *[rational_text(state[name]) for name in names]])
    return buffer.getvalue().encode("utf-8")


def _observations(contract: dict, raw: bytes) -> list[tuple[Fraction, dict[str, Fraction]]]:
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
        raise ScientificResourceLimit("observations byte limit exceeded")
    try:
        rows = list(csv.reader(io.StringIO(raw.decode("utf-8")), strict=True))
    except (UnicodeDecodeError, csv.Error) as exc:
        raise ScientificContractError(f"invalid observations CSV: {exc}") from exc
    names = [entry["id"] for entry in contract["species"]]
    if not rows or rows[0] != ["time_s", *names]:
        raise ScientificContractError("CSV header must be time_s followed by declared species in order")
    if len(rows) != contract["steps"] + 2:
        raise ScientificContractError("CSV must contain exactly steps+1 observations")
    parsed = []
    for index, row in enumerate(rows[1:]):
        if len(row) != len(names) + 1:
            raise ScientificContractError(f"CSV row {index}: wrong column count")
        parsed.append((rational(row[0], f"time[{index}]"),
            {name: rational(value, f"{name}[{index}]") for name, value in zip(names, row[1:])}))
    return parsed


def evaluate(contract_raw: bytes, observations_raw: bytes) -> dict:
    """Return exact predicates and witnesses. Unsupported/limit results never PASS."""
    base = {"format": REPORT_FORMAT, "authority": "BOUNDED_PYTHON_REPLAY_ONLY",
        "pcs_authority": False, "clinical_or_biological_acceptance": False,
        "contract_sha256": hashlib.sha256(contract_raw).hexdigest(),
        "observations_sha256": hashlib.sha256(observations_raw).hexdigest(),
        "limits": {"steps": MAX_STEPS, "species": MAX_SPECIES, "reactions": MAX_REACTIONS,
                   "rational_bits": MAX_FRACTION_BITS},
        "limitations": ["rational Euler replay is not continuous-ODE accuracy",
            "no proof relates this Python adapter to a Lean reference model",
            "no biological, clinical, causal or general empirical adequacy is certified",
            "producing source code is bound but never executed or proved by this adapter"]}
    try:
        contract = load_contract(contract_raw)
        observed = _observations(contract, observations_raw)
        expected = simulate(contract)
        absolute = rational(contract["absolute_tolerance"], "absolute_tolerance")
        relative = rational(contract["relative_tolerance"], "relative_tolerance")
        checks = []
        for item in primitive_checks(contract):
            if item["type"] == "reaction_balance":
                passed, witness = reaction_balanced(item["reactants"], item["products"])
            else:
                left = _unit(item["left_unit"], "rate unit")
                right = _unit(item["right_unit"], "required unit")
                passed, witness = left == right, {"left_dimensions": left, "right_dimensions": right}
            checks.append({"id": item["id"], "outcome": "PASS" if passed else "FAIL", "witness": witness})
        for kind in ("time_grid", "nonnegative", "reference_match", "element_conservation"):
            witness = None
            atoms = {entry["id"]: parse_formula(entry["formula"]) for entry in contract["species"]}
            elements = sorted({e for counts in atoms.values() for e in counts})
            baseline = {e: _bounded(sum((rational(contract["initial"][name], name) * counts[e]
                               for name, counts in atoms.items()), Fraction(0))) for e in elements}
            for index, ((time, state), (wanted_time, wanted_state)) in enumerate(zip(observed, expected)):
                if kind == "time_grid" and time != wanted_time:
                    witness = {"row": index, "expected": rational_text(wanted_time), "actual": rational_text(time)}
                if kind == "nonnegative":
                    for name, value in state.items():
                        if value < 0:
                            witness = {"row": index, "species": name, "actual": rational_text(value)}
                            break
                if kind == "reference_match":
                    for name, value in state.items():
                        tolerance = _bounded(absolute + relative * abs(wanted_state[name]))
                        if abs(value - wanted_state[name]) > tolerance:
                            witness = {"row": index, "species": name, "expected": rational_text(wanted_state[name]),
                                "actual": rational_text(value), "tolerance": rational_text(tolerance)}
                            break
                if kind == "element_conservation":
                    for element in elements:
                        actual = _bounded(sum((value * atoms[name][element] for name, value in state.items()), Fraction(0)))
                        tolerance = _bounded(absolute + relative * abs(baseline[element]))
                        if abs(actual - baseline[element]) > tolerance:
                            witness = {"row": index, "element": element, "expected": rational_text(baseline[element]),
                                "actual": rational_text(actual), "tolerance": rational_text(tolerance)}
                            break
                if witness is not None:
                    break
            checks.append({"id": kind, "outcome": "PASS" if witness is None else "FAIL", "witness": witness})
        return {**base, "outcome": "PASS" if all(x["outcome"] == "PASS" for x in checks) else "FAIL",
            "checks": checks, "resources": {"rational_euler_steps": contract["steps"],
                "reaction_step_evaluations": contract["steps"] * len(contract["reactions"]),
                "observations": len(observed), "input_bytes": len(contract_raw) + len(observations_raw)},
            "diagnostics": []}
    except ScientificContractError as exc:
        return {**base, "outcome": "RESOURCE_LIMIT" if isinstance(exc, ScientificResourceLimit) else "OPEN",
            "checks": [], "resources": {"input_bytes": len(contract_raw) + len(observations_raw)},
            "diagnostics": [{"code": "resource_limit" if isinstance(exc, ScientificResourceLimit) else "unsupported_or_invalid_contract",
                "message": str(exc), "action": "Correct the explicit contract or split the task into supported bounded obligations.",
                "suggestions_are_verified": False}]}
