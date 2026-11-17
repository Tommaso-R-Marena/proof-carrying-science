"""
Restricted synthetic operations for incremental certificate revalidation.

Exact int add/mul/sub, exact rational add/mul (fractions.Fraction),
predicate eq, and composition. Each op has a version id.
LocalCheck never grants authority from cache lookup.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .graph import CanonValue, Certificate, Value, canonicalize_value, decode_value


# Op identifiers (stable synthetic catalog)
OP_INT_CONST = 1
OP_INT_ADD = 2
OP_INT_MUL = 3
OP_INT_SUB = 4
OP_RAT_CONST = 10
OP_RAT_ADD = 11
OP_RAT_MUL = 12
OP_EQ = 20
OP_COMPOSE = 30

DEFAULT_POLICY = 1


def _as_int(v: Value) -> int:
    if isinstance(v, bool) or not isinstance(v, int):
        raise TypeError(f"expected int, got {type(v)!r}")
    return v


def _as_rat(v: Value) -> Fraction:
    if isinstance(v, Fraction):
        return v
    if isinstance(v, int) and not isinstance(v, bool):
        return Fraction(v)
    raise TypeError(f"expected rational, got {type(v)!r}")


def compute_op(op: int, deps: Sequence[Value], evidence: int) -> Value:
    """
    Pure computation for a synthetic op.
    Evidence supplies the constant for *_CONST ops.
    """
    if op == OP_INT_CONST:
        if len(deps) != 0:
            raise ValueError("int_const expects 0 deps")
        return int(evidence)
    if op == OP_INT_ADD:
        if len(deps) != 2:
            raise ValueError("int_add expects 2 deps")
        return _as_int(deps[0]) + _as_int(deps[1])
    if op == OP_INT_MUL:
        if len(deps) != 2:
            raise ValueError("int_mul expects 2 deps")
        return _as_int(deps[0]) * _as_int(deps[1])
    if op == OP_INT_SUB:
        if len(deps) != 2:
            raise ValueError("int_sub expects 2 deps")
        return _as_int(deps[0]) - _as_int(deps[1])
    if op == OP_RAT_CONST:
        if len(deps) != 0:
            raise ValueError("rat_const expects 0 deps")
        # evidence encodes numerator; denominator fixed at 1 for simple consts,
        # or packed as evidence = num (den=1). For non-unit dens use encode in
        # a companion convention: evidence low 16 bits = den, high = num is avoided;
        # instead evidence is numerator and we require den=1, or pass Fraction via
        # a dedicated helper that sets evidence to a registry index.
        return Fraction(int(evidence), 1)
    if op == OP_RAT_ADD:
        if len(deps) != 2:
            raise ValueError("rat_add expects 2 deps")
        return _as_rat(deps[0]) + _as_rat(deps[1])
    if op == OP_RAT_MUL:
        if len(deps) != 2:
            raise ValueError("rat_mul expects 2 deps")
        return _as_rat(deps[0]) * _as_rat(deps[1])
    if op == OP_EQ:
        if len(deps) != 2:
            raise ValueError("eq expects 2 deps")
        return 1 if canonicalize_value(deps[0]) == canonicalize_value(deps[1]) else 0
    if op == OP_COMPOSE:
        if len(deps) != 1:
            raise ValueError("compose expects 1 dep")
        return deps[0]
    raise ValueError(f"unknown op id: {op}")


def make_certificate(op: int, deps: Sequence[Value], evidence: int) -> Certificate:
    """Build a certificate whose payload witnesses the exact computation."""
    out = compute_op(op, deps, evidence)
    # payload = ("ok", op, canon(output)) — exact witness, not a digest-as-proof
    payload: CanonValue = ("ok", op, canonicalize_value(out))
    return Certificate(payload=payload, output=out)


@dataclass(frozen=True)
class OpSpec:
    op_id: int
    version: int
    name: str


# LocalCheck: OpId → VersionId → PolicyId → List Value → CertPayload → Value → Bool
LocalCheck = Callable[
    [int, int, int, Sequence[Value], CanonValue, Value],
    bool,
]


@dataclass
class OpRegistry:
    """Versioned op catalog + policy gate."""

    versions: Dict[int, int]
    allowed_policies: set
    # optional rational constant table: evidence_id -> Fraction
    rat_table: Dict[int, Fraction]

    def __init__(
        self,
        versions: Optional[Dict[int, int]] = None,
        allowed_policies: Optional[set] = None,
        rat_table: Optional[Dict[int, Fraction]] = None,
    ):
        self.versions = dict(versions or {})
        self.allowed_policies = set(allowed_policies or {DEFAULT_POLICY})
        self.rat_table = dict(rat_table or {})

    def register(self, op_id: int, version: int) -> None:
        self.versions[op_id] = version

    def register_rat_const(self, evidence_id: int, value: Fraction) -> None:
        self.rat_table[evidence_id] = value

    def expected_version(self, op_id: int) -> Optional[int]:
        return self.versions.get(op_id)

    def compute(self, op: int, deps: Sequence[Value], evidence: int) -> Value:
        if op == OP_RAT_CONST and evidence in self.rat_table:
            if len(deps) != 0:
                raise ValueError("rat_const expects 0 deps")
            return self.rat_table[evidence]
        return compute_op(op, deps, evidence)

    def make_cert(self, op: int, deps: Sequence[Value], evidence: int) -> Certificate:
        out = self.compute(op, deps, evidence)
        payload: CanonValue = ("ok", op, canonicalize_value(out))
        return Certificate(payload=payload, output=out)

    def local_check(
        self,
        op: int,
        version: int,
        policy: int,
        deps: Sequence[Value],
        payload: CanonValue,
        output: Value,
    ) -> bool:
        """Executable LocalCheck matching the Lean abbrev."""
        if policy not in self.allowed_policies:
            return False
        exp_ver = self.versions.get(op)
        if exp_ver is None or version != exp_ver:
            return False
        try:
            expected = self.compute(op, deps, evidence=_evidence_from_payload_or_node(op, payload, deps))
        except (TypeError, ValueError):
            # For CONST ops evidence is needed; fall back to verifying payload witness
            try:
                expected = self._expected_from_witness(op, deps, payload)
            except (TypeError, ValueError):
                return False
        if canonicalize_value(expected) != canonicalize_value(output):
            return False
        # payload must be exact witness
        want: CanonValue = ("ok", op, canonicalize_value(output))
        return payload == want

    def _expected_from_witness(
        self, op: int, deps: Sequence[Value], payload: CanonValue
    ) -> Value:
        if (
            isinstance(payload, tuple)
            and len(payload) == 3
            and payload[0] == "ok"
            and payload[1] == op
        ):
            # Recompute from deps when possible; for consts, decode payload
            if op in (OP_INT_CONST, OP_RAT_CONST) and len(deps) == 0:
                return _decode_canon(payload[2])
            # recompute with evidence 0 placeholder then compare — not used
        raise ValueError("cannot recover expected value")

    def local_check_node(
        self,
        op: int,
        version: int,
        policy: int,
        evidence: int,
        deps: Sequence[Value],
        payload: CanonValue,
        output: Value,
    ) -> bool:
        """Node-aware LocalCheck that uses evidence for constants."""
        if policy not in self.allowed_policies:
            return False
        exp_ver = self.versions.get(op)
        if exp_ver is None or version != exp_ver:
            return False
        try:
            expected = self.compute(op, deps, evidence)
        except (TypeError, ValueError):
            return False
        if canonicalize_value(expected) != canonicalize_value(output):
            return False
        want: CanonValue = ("ok", op, canonicalize_value(output))
        return payload == want

    def as_local_check(self) -> LocalCheck:
        """
        Lean-shaped LocalCheck (no evidence arg).
        Evidence is recovered from payload for const ops; for others recomputed.
        Prefer `local_check_node` in the executable verifier.
        """

        def check(
            op: int,
            version: int,
            policy: int,
            deps: Sequence[Value],
            payload: CanonValue,
            output: Value,
        ) -> bool:
            if policy not in self.allowed_policies:
                return False
            exp_ver = self.versions.get(op)
            if exp_ver is None or version != exp_ver:
                return False
            # recover evidence for consts from output/payload; recompute others
            if op == OP_INT_CONST:
                if len(deps) != 0:
                    return False
                try:
                    expected = _decode_canon(payload[2]) if _is_ok_payload(payload, op) else None
                except Exception:
                    return False
                if expected is None:
                    return False
                return (
                    canonicalize_value(expected) == canonicalize_value(output)
                    and payload == ("ok", op, canonicalize_value(output))
                )
            if op == OP_RAT_CONST:
                if len(deps) != 0:
                    return False
                if not _is_ok_payload(payload, op):
                    return False
                try:
                    expected = _decode_canon(payload[2])
                except Exception:
                    return False
                return (
                    canonicalize_value(expected) == canonicalize_value(output)
                    and payload == ("ok", op, canonicalize_value(output))
                )
            try:
                # non-const: evidence unused
                expected = self.compute(op, deps, evidence=0)
            except (TypeError, ValueError):
                return False
            return (
                canonicalize_value(expected) == canonicalize_value(output)
                and payload == ("ok", op, canonicalize_value(output))
            )

        return check


def _is_ok_payload(payload: CanonValue, op: int) -> bool:
    return (
        isinstance(payload, tuple)
        and len(payload) == 3
        and payload[0] == "ok"
        and payload[1] == op
    )


def _decode_canon(c: CanonValue) -> Value:
    if isinstance(c, tuple):
        if len(c) == 2 and c[0] == "int":
            return int(c[1])
        if len(c) == 3 and c[0] == "rat":
            return Fraction(int(c[1]), int(c[2]))
    raise ValueError(f"bad canon value: {c!r}")


def _evidence_from_payload_or_node(op: int, payload: CanonValue, deps: Sequence[Value]) -> int:
    # unused helper kept for API clarity
    return 0


def default_registry(version: int = 1) -> OpRegistry:
    """Default catalog of restricted synthetic ops."""
    reg = OpRegistry(
        versions={
            OP_INT_CONST: version,
            OP_INT_ADD: version,
            OP_INT_MUL: version,
            OP_INT_SUB: version,
            OP_RAT_CONST: version,
            OP_RAT_ADD: version,
            OP_RAT_MUL: version,
            OP_EQ: version,
            OP_COMPOSE: version,
        },
        allowed_policies={DEFAULT_POLICY},
    )
    return reg


OP_NAMES = {
    OP_INT_CONST: "int_const",
    OP_INT_ADD: "int_add",
    OP_INT_MUL: "int_mul",
    OP_INT_SUB: "int_sub",
    OP_RAT_CONST: "rat_const",
    OP_RAT_ADD: "rat_add",
    OP_RAT_MUL: "rat_mul",
    OP_EQ: "eq",
    OP_COMPOSE: "compose",
}
