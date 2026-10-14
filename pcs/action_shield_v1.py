"""Finite-state tool-action shield proposals and independent kernel replay.

The producer's permitted-action table is untrusted. Every nondeterministic
successor of each admitted action is checked. A fresh Lean proof applies the
inductive theorem to the exact model; neither a signature nor a Python PASS
establishes that a deployed agent obeys this model.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import time
from typing import Any

from .canonical_json import canonicalize_jcs_bytes
from .jsonio import strict_json_loads

MODEL_FORMAT = "pcs-action-shield-model-v1"
SHIELD_FORMAT = "pcs-action-shield-certificate-v1"
REPORT_FORMAT = "pcs-action-shield-replay-v1"
MAX_BYTES = 2 * 1024 * 1024
MAX_STATES = 32
MAX_ACTIONS = 16
MAX_EDGES = 512
MAX_PAIRS = 512
_ROOT = Path(__file__).resolve().parents[1]
_FORMAL = _ROOT / "formal" / "PCSActionShield.lean"
_PREMISES = {"model_completeness", "state_observation", "shield_enforcement"}


class ActionShieldError(ValueError):
    pass


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _object(value: Any, keys: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != keys:
        raise ActionShieldError(f"{label} must have exactly the declared fields")
    return value


def _nat(value: Any) -> int:
    if type(value) is not int or not 0 <= value < 65536:
        raise ActionShieldError("state/action IDs must be exact natural integers below 65536")
    return value


def _ids(value: Any, maximum: int, label: str, *, nonempty: bool = False) -> list[int]:
    if not isinstance(value, list) or len(value) > maximum or (nonempty and not value):
        raise ActionShieldError(f"{label} list is empty or outside its resource bound")
    values = [_nat(x) for x in value]
    if values != sorted(set(values)):
        raise ActionShieldError(f"{label} must contain sorted unique IDs")
    return values


def _json(raw: bytes) -> Any:
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
        raise ActionShieldError("input must be bytes within the 2 MiB limit")
    try:
        return strict_json_loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ActionShieldError("invalid strict UTF-8 JSON") from exc


def load_model(model_raw: bytes) -> dict:
    model = _object(_json(model_raw), {"format", "states", "actions", "initial", "safe",
        "forbidden", "transitions", "assumptions"}, "model")
    if model["format"] != MODEL_FORMAT:
        raise ActionShieldError("unsupported finite transition-model format")
    states = _ids(model["states"], MAX_STATES, "states", nonempty=True)
    actions = _ids(model["actions"], MAX_ACTIONS, "actions", nonempty=True)
    initial = _ids(model["initial"], MAX_STATES, "initial", nonempty=True)
    safe = _ids(model["safe"], MAX_STATES, "safe", nonempty=True)
    forbidden = _ids(model["forbidden"], MAX_ACTIONS, "forbidden")
    if not set(initial + safe).issubset(states) or not set(forbidden).issubset(actions):
        raise ActionShieldError("initial/safe/forbidden IDs must belong to the declared domains")
    edges = model["transitions"]
    if not isinstance(edges, list) or not 1 <= len(edges) <= MAX_EDGES:
        raise ActionShieldError("transition count outside 1..512")
    triples = []
    for edge in edges:
        edge = _object(edge, {"source", "action", "target"}, "transition")
        s, a, t = (_nat(edge[x]) for x in ("source", "action", "target"))
        if s not in states or t not in states or a not in actions:
            raise ActionShieldError("transition leaves the declared state/action domains")
        triples.append((s, a, t))
    if triples != sorted(set(triples)):
        raise ActionShieldError("transitions must be sorted unique triples")
    premises = model["assumptions"]
    if not isinstance(premises, list) or len(premises) != 3:
        raise ActionShieldError("three explicit deployment premises are required")
    for item in premises:
        _object(item, {"id", "statement", "status"}, "assumption")
        if (not isinstance(item["id"], str) or not isinstance(item["statement"], str)
                or not 1 <= len(item["statement"]) <= 2048
                or item["status"] != "OPEN"):
            raise ActionShieldError("deployment premises must remain explicit and OPEN")
    if {x["id"] for x in premises} != _PREMISES or [x["id"] for x in premises] != sorted(_PREMISES):
        raise ActionShieldError("missing, duplicate or unordered deployment premise IDs")
    return model


def load_shield(shield_raw: bytes, model: dict, *, model_sha256: str) -> dict:
    shield = _object(_json(shield_raw), {"format", "model_sha256", "allowed"}, "shield")
    if shield["format"] != SHIELD_FORMAT or shield["model_sha256"] != model_sha256:
        raise ActionShieldError("shield is not bound to these exact model bytes")
    allowed = shield["allowed"]
    if not isinstance(allowed, list) or len(allowed) > MAX_PAIRS:
        raise ActionShieldError("permitted-pair count exceeds 512")
    pairs = []
    outgoing = {(e["source"], e["action"]) for e in model["transitions"]}
    for pair in allowed:
        if not isinstance(pair, list) or len(pair) != 2:
            raise ActionShieldError("allowed entries must be [state, action] pairs")
        s, a = (_nat(x) for x in pair)
        if s not in model["states"] or a not in model["actions"] or (s, a) not in outgoing:
            raise ActionShieldError("permitted pair has no modeled successor")
        pairs.append((s, a))
    if pairs != sorted(set(pairs)):
        raise ActionShieldError("permitted pairs must be sorted and unique")
    return shield


def propose(model_raw: bytes) -> dict:
    """A deterministic producer proposal; receiving replay remains mandatory.

    The proposal includes every safe-source pair with at least one successor and
    with all successors safe. No optimality/liveness authority is granted.
    """
    model = load_model(model_raw)
    grouped: dict[tuple[int, int], list[int]] = {}
    for edge in model["transitions"]:
        grouped.setdefault((edge["source"], edge["action"]), []).append(edge["target"])
    allowed = [[s, a] for (s, a), targets in sorted(grouped.items()) if s in model["safe"]
        and a not in model["forbidden"] and all(t in model["safe"] for t in targets)]
    return {"format": SHIELD_FORMAT, "model_sha256": _sha(model_raw), "allowed": allowed}


def evaluate(model_raw: bytes, shield_raw: bytes) -> dict:
    """Independent complete finite closure check; not itself kernel evidence."""
    model = load_model(model_raw)
    shield = load_shield(shield_raw, model, model_sha256=_sha(model_raw))
    safe, forbidden = set(model["safe"]), set(model["forbidden"])
    allowed = {tuple(x) for x in shield["allowed"]}
    violations = [{"kind": "unsafe_initial", "state": s} for s in model["initial"] if s not in safe]
    for edge in model["transitions"]:
        if edge["source"] in safe and (edge["source"], edge["action"]) in allowed:
            if edge["target"] not in safe:
                violations.append({"kind": "unsafe_successor", "transition": edge})
            if edge["action"] in forbidden:
                violations.append({"kind": "forbidden_action", "transition": edge})
    reachable = set(model["initial"])
    while True:
        extra = {e["target"] for e in model["transitions"] if e["source"] in reachable
                 and (e["source"], e["action"]) in allowed}
        if extra.issubset(reachable):
            break
        reachable.update(extra)
    all_pairs = sorted({(e["source"], e["action"]) for e in model["transitions"]})
    deadlocks = [s for s in sorted(reachable) if not any(pair[0] == s for pair in allowed)]
    return {"format": REPORT_FORMAT, "model_sha256": _sha(model_raw), "shield_sha256": _sha(shield_raw),
        "outcome": "FAIL" if violations else "PASS", "violations": violations,
        "allowed_pairs": shield["allowed"], "restricted_pairs": [list(x) for x in all_pairs if x not in allowed],
        "reachable_states": sorted(reachable), "reachable_deadlocks": deadlocks,
        "checks": {"initial_safe": all(s in safe for s in model["initial"]),
            "all_nondeterministic_successors_safe": not any(x["kind"] == "unsafe_successor" for x in violations),
            "forbidden_actions_excluded": not any(x["kind"] == "forbidden_action" for x in violations)},
        "assumptions": model["assumptions"], "formal_model_support": "REQUIRES_FRESH_KERNEL_REPLAY",
        "implementation_correspondence": "OPEN", "deployment_safety": "OPEN", "liveness": "OPEN",
        "maximality_authority": False, "scientific_acceptance": False,
        "untrusted_project_code_executed": False}


def formal_source() -> bytes:
    return _FORMAL.read_bytes()


def admit_action(model_raw: bytes, shield_raw: bytes, state: int, action: int) -> bool:
    """Bounded runtime proposal filter, with fail-closed certificate validation.

    The decision is a Python implementation result, not a replacement for fresh
    receiving kernel replay. The caller must establish observation/enforcement
    correspondence before interpreting it as deployed safety.
    """
    state, action = _nat(state), _nat(action)
    model = load_model(model_raw)
    shield = load_shield(shield_raw, model, model_sha256=_sha(model_raw))
    return (evaluate(model_raw, shield_raw)["outcome"] == "PASS" and state in model["safe"]
            and [state, action] in shield["allowed"])


def proof_source(model_raw: bytes, shield_raw: bytes) -> bytes:
    """Generate only literal integer data and fixed first-party proof text."""
    model = load_model(model_raw)
    shield = load_shield(shield_raw, model, model_sha256=_sha(model_raw))
    def nums(items: list[int]) -> str:
        return "[" + ", ".join(str(x) for x in items) + "]"
    edges = "[" + ", ".join("⟨" + ", ".join(str(e[k]) for k in ("source", "action", "target"))
                             + "⟩" for e in model["transitions"]) + "]"
    allowed = "[" + ", ".join(f"({s}, {a})" for s, a in shield["allowed"]) + "]"
    return (f"import PCSActionShield\nset_option autoImplicit false\n"
        "set_option maxRecDepth 8192\nset_option maxHeartbeats 2000000\n"
        f"-- Exact model SHA256: {_sha(model_raw)}\n-- Exact shield SHA256: {_sha(shield_raw)}\n"
        "namespace PCSActionShieldReplay\n"
        f"def model : PCSActionShield.Model := ⟨{nums(model['initial'])}, {nums(model['safe'])}, "
        f"{edges}, {allowed}, {nums(model['forbidden'])}⟩\n"
        "theorem certificate_checked : PCSActionShield.check model = true := by decide\n"
        "theorem all_finite_histories_safe {history : List PCSActionShield.Edge} {s : Nat}\n"
        "    (h : PCSActionShield.History model history s) :\n"
        "    s ∈ model.safe ∧ ∀ e ∈ history, e.action ∉ model.forbidden :=\n"
        "  PCSActionShield.admitted_histories_safe certificate_checked h\n"
        "#print axioms certificate_checked\n#print axioms all_finite_histories_safe\n"
        "end PCSActionShieldReplay\n").encode("utf-8")


def kernel_replay(model_raw: bytes, shield_raw: bytes, *, timeout: float = 60) -> dict:
    """Fresh kernel replay of a private immutable source/data snapshot.

    Producer proof/transcript files are never executed. Exhaustion, missing Lean
    or a failed certificate produce no formal support. Std and the Lean compiler
    are trusted separately from the Python parser and literal rendering boundary.
    """
    if type(timeout) not in {int, float} or not 0 < timeout <= 180:
        raise ActionShieldError("kernel timeout must be within 0..180 seconds")
    generated = proof_source(model_raw, shield_raw)
    core = formal_source()
    base = {"format": "pcs-action-shield-kernel-replay-v1", "kernel_checked": False,
        "model_sha256": _sha(model_raw), "shield_sha256": _sha(shield_raw),
        "formal_source_sha256": _sha(core), "proof_sha256": _sha(generated),
        "theorem": "PCSActionShieldReplay.all_finite_histories_safe",
        "kernel_axioms": [], "deployment_safety": "OPEN", "scientific_acceptance": False,
        "producer_proof_trusted": False}
    started = time.monotonic()
    try:
        version = subprocess.run(["lean", "--version"], capture_output=True, text=True, timeout=10)
        if version.returncode != 0 or "version 4.28.0" not in version.stdout:
            return {**base, "status": "UNSUPPORTED_LEAN_VERSION"}
        with tempfile.TemporaryDirectory(prefix="pcs-shield-kernel-") as td:
            private = Path(td)
            source = private / "PCSActionShield.lean"
            proof = private / "Replay.lean"
            source.write_bytes(core)
            proof.write_bytes(generated)
            env = dict(os.environ)
            env["LEAN_PATH"] = str(private)
            built = subprocess.run(["lean", "-j1", "-M1024", "-o", str(private / "PCSActionShield.olean"),
                str(source)], cwd=private, env=env, capture_output=True, text=True, timeout=timeout)
            if built.returncode:
                return {**base, "status": "FORMAL_SOURCE_REJECTED", "output": (built.stdout + built.stderr)[-8192:]}
            replay = subprocess.run(["lean", "-j1", "-M1024", str(proof)], cwd=private,
                env=env, capture_output=True, text=True, timeout=timeout)
            output = replay.stdout + replay.stderr
            if replay.returncode:
                return {**base, "status": "CERTIFICATE_REJECTED", "output": output[-8192:]}
            # Audits are generated by fixed proof text; no user-controlled Lean text
            # enters the subprocess. Collect each theorem's actual axiom list.
            import re
            audit = re.findall(r"depends on axioms: \[([^\]]*)\]", output)
            empty = output.count("does not depend on any axioms")
            axioms = sorted({a.strip() for row in audit for a in row.split(",") if a.strip()})
            if len(audit) + empty != 2 or not set(axioms).issubset({"propext", "Classical.choice", "Quot.sound"}):
                return {**base, "status": "AXIOM_AUDIT_REJECTED", "output": output[-8192:]}
            return {**base, "kernel_checked": True, "status": "KERNEL_CHECKED", "kernel_axioms": axioms,
                "lean_version": version.stdout.strip(), "elapsed_seconds": round(time.monotonic() - started, 6)}
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {**base, "status": "UNAVAILABLE_OR_EXHAUSTED", "error": type(exc).__name__}
