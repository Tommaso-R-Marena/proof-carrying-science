"""Render typed constructors and replay closed decision certificates under Lean 4.28."""
from __future__ import annotations

from functools import lru_cache
import hashlib
import itertools
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from .set_algebra import ALLOWED_AXIOMS, MODULE, validate

VERSION = re.compile(r"Lean \(version 4\.28\.0, [^,]+, commit 7e01a1bf5c70fc6167d49c345d3bf80596e9a79b, Release\)")


def _expression(e, variables):
    key, arg = next(iter(e.items()))
    if key == "var":
        # Fin has a modulo OfNat instance; constructor bounds must be checked.
        return f"(.var ⟨{variables.index(arg)}, by decide⟩)"
    if key in {"empty", "univ"}:
        return f".{key}"
    if key == "compl":
        return f"(.compl {_expression(arg, variables)})"
    return f"(.{key} {_expression(arg[0], variables)} {_expression(arg[1], variables)})"


def _contract(contract):
    def atom(row):
        key, pair = next(iter(row.items()))
        return f"⟨.{key}, " + ", ".join(_expression(e, contract["variables"]) for e in pair) + "⟩"

    return "⟨[" + ", ".join(atom(a) for a in contract["premises"]) + "], " + atom(contract["conclusion"]) + "⟩"


def _eval(e, values):
    k, arg = next(iter(e.items()))
    if k == "var":
        return values[arg]
    if k == "univ":
        return True
    if k == "empty":
        return False
    if k == "compl":
        return not _eval(arg, values)
    lhs, rhs = (_eval(t, values) for t in arg)
    if k in {"sup", "union"}:
        return lhs or rhs
    if k in {"inf", "inter"}:
        return lhs and rhs
    return lhs and not rhs


def _interpret(contract, bits):
    assignment = dict(zip(contract["variables"], bits, strict=True))
    def atom(a):
        kind, pair = next(iter(a.items()))
        lhs, rhs = (_eval(e, assignment) for e in pair)
        return (kind, lhs, rhs)
    return [atom(a) for a in contract["premises"]], atom(contract["conclusion"])


def _holds(atom):
    kind, lhs, rhs = atom
    return (lhs == rhs) if kind == "equal" else (not lhs or rhs)


def render_pair(reference, candidate):
    """Return proof source and an untrusted forecast; only check_pair grants verdicts."""
    validate(reference)
    validate(candidate)
    nr, nc = len(reference["variables"]), len(candidate["variables"])
    source = [
        "import SetSemantics", "open PCS.SetAlgebra", "set_option autoImplicit false",
        "set_option maxRecDepth 4096", "set_option maxHeartbeats 800000",
        f"def reference : Contract {nr} := {_contract(reference)}",
        f"def candidate : Contract {nc} := {_contract(candidate)}",
    ]
    witness = None
    proof = "NOT_CHECKED"
    if nr != nc:
        correspondence = "DIFFERENT"
        source.append(f"theorem correspondence : ({nr} : Nat) ≠ {nc} := by decide")
    else:
        same = True
        for bits in itertools.product((False, True), repeat=nc):
            left = _interpret(reference, bits)
            right = _interpret(candidate, bits)
            if left != right:
                same = False
                break
            if witness is None and all(_holds(a) for a in right[0]) and not _holds(right[1]):
                witness = bits
        if same:
            correspondence = "EQUIVALENT"
            source.append("theorem correspondence : reference.Same candidate := "
                          "(correspondence_iff _ _).mp (by decide)")
            if witness is None:
                proof = "KERNEL_CHECKED"
                source.append("theorem validity : candidate.Valid := (validity_iff _).mp (by decide)")
            else:
                proof = "COUNTEREXAMPLE"
                valuation = "Fin.elim0"
                for bit in reversed(witness):
                    valuation = f"(Fin.cases {str(bit).lower()} {valuation})"
                source += [
                    f"def witness : Fin {nc} → Bool := {valuation}",
                    "theorem refutation : (∀ a ∈ candidate.premises, a.holds "
                    "(fun i (_ : Unit) => witness i = true)) ∧ "
                    "¬candidate.conclusion.holds (fun i (_ : Unit) => witness i = true) := "
                    "singleton_countermodel candidate witness (by decide)",
                ]
        else:
            correspondence = "DIFFERENT"
            witness = None
            source.append("theorem correspondence : ¬reference.Same candidate := fun h => "
                          "(by decide : ¬(compareContracts reference candidate = true)) "
                          "((correspondence_iff _ _).mpr h)")
    names = ["correspondence"]
    if proof == "COUNTEREXAMPLE":
        names.append("refutation")
    if proof == "KERNEL_CHECKED":
        names.append("validity")
    source.extend(f"#print axioms {name}" for name in names)
    return "\n".join(source) + "\n", {
        "correspondence": correspondence, "proof": proof, "declarations": names,
        "counterexample": None if witness is None else dict(zip(candidate["variables"], witness, strict=True)),
    }


def _run(cmd, directory, env):
    proc = subprocess.run(cmd, cwd=directory, env=env, capture_output=True, encoding="utf-8",
                          timeout=40, check=False)
    if proc.returncode != 0:
        raise RuntimeError((proc.stdout + proc.stderr)[-1500:])
    return proc.stdout


@lru_cache(maxsize=1)
def _library(lean, module_bytes):
    # Rebuild the library from bound source. Neither ambient project plugins nor
    # ambient .olean search paths are part of the input protocol.
    env = {"PATH": str(Path(lean).parent) + os.pathsep + os.defpath}
    scratch = tempfile.TemporaryDirectory(prefix="pcs-set-semantics-")
    directory = Path(scratch.name)
    env["LEAN_PATH"] = str(directory)
    try:
        if not VERSION.fullmatch(_run([lean, "--version"], directory, env).strip()):
            raise RuntimeError("Lean toolchain differs from the pinned release")
        (directory / "SetSemantics.lean").write_bytes(module_bytes)
        _run([lean, "-j1", "-o", "SetSemantics.olean", "SetSemantics.lean"], directory, env)
        checker = str(Path(lean).with_name("leanchecker"))
        _run([checker, "SetSemantics"], directory, env)
    except Exception:
        scratch.cleanup()
        raise
    return scratch, env, checker


def _axioms(audit, names):
    axioms = {}
    for name in names:
        if f"'{name}' does not depend on any axioms" in audit.splitlines():
            axioms[name] = []
            continue
        match = re.search(rf"^'{name}' depends on axioms: \[([^\]]+)\]$", audit, re.M)
        if not match:
            raise RuntimeError("incomplete Lean axiom audit")
        deps = match[1].split(", ")
        if not set(deps) <= ALLOWED_AXIOMS:
            raise RuntimeError("axiom outside allowlist")
        axioms[name] = deps
    return axioms


def check_pair(reference, candidate):
    result = {"correspondence": "UNKNOWN", "proof": "UNKNOWN", "axioms": {},
              "elaborated": False, "counterexample": None, "lean_sha256": None}
    try:
        source, proposal = render_pair(reference, candidate)
        result["lean_sha256"] = hashlib.sha256(source.encode()).hexdigest()
        module_bytes = MODULE.read_bytes()
        result["library_sha256"] = hashlib.sha256(module_bytes).hexdigest()
        lean = shutil.which("lean")
        if not lean:
            raise RuntimeError("pinned Lean must be on PATH")
        lean = str(Path(lean).absolute())
        library, env, checker = _library(lean, module_bytes)
        with tempfile.TemporaryDirectory(prefix="pcs-set-pair-") as scratch:
            directory = Path(scratch)
            (directory / "Receipt.lean").write_text(source, encoding="utf-8")
            env = dict(env, LEAN_PATH=os.pathsep.join([library.name, scratch]))
            audit = _run([lean, "-j1", "-o", "Receipt.olean", "Receipt.lean"], directory, env)
            axioms = _axioms(audit, proposal.pop("declarations"))
            _run([checker, "Receipt"], directory, env)
        return dict(result, **{"elaborated": True, "axioms": axioms}, **proposal)
    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as err:
        return dict(result, error=str(err))
