"""Opt-in constructor and operand-role receipts for two pinned binary set identities."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from .forml4_protocol import DATA_SHA256, REVISION
from .set_algebra import MODULE, parse_english, validate
from .set_algebra_evaluation import external_reference, sha
from .set_algebra_kernel import _axioms, _contract, _library, _run, render_pair

# An explicit editorial alignment of the two *source sentences* to the formal
# function sides. No assumption about orientation is inferred from provability.
SOURCES = {
    498: ("03f0bf647e124e411a992e5e3785a595b842a388dbfb374648a035502002de19",
          "39238dac5db80d3b940c1c98e469682caa05d339efb620955dcc42ce5ce4b99a", "direct"),
    499: ("c3b415d8b075c80542dc11c01c9a4ee0612b9f52ccf8c8a136573e1addc335f5",
          "3a49008e76b06c93310764448b4cced531588c8ff98added54a0bd1f789fa04e", "symmetric"),
}

DECIDABLE = """deriving instance DecidableEq for Expr
deriving instance DecidableEq for Atom
deriving instance DecidableEq for Contract
"""


def _program(reference, candidate, orientation):
    """Reuse the extensional proof verbatim and add a closed structural judgment."""
    if orientation not in {"direct", "symmetric"}:
        raise ValueError("unknown source alignment")
    base, forecast = render_pair(reference, candidate)
    arity = len(candidate["variables"])
    aligned = deepcopy(reference)
    if orientation == "symmetric":
        aligned["conclusion"]["equal"].reverse()
    matches = arity == 2 and _contract(candidate) == _contract(aligned)
    if orientation == "direct":
        rhs = "reference"
        alignment_proof = "Iff.rfl"
    else:
        rhs = ("{ reference with conclusion := { reference.conclusion with "
               "lhs := reference.conclusion.rhs, rhs := reference.conclusion.lhs } }")
        alignment_proof = "by constructor <;> intro h α ρ hp <;> exact (h α ρ hp).symm"
    aligned_definition = (f"def sourceRoles : Contract 2 := {rhs}\n"
                          f"theorem alignment : sourceRoles.Valid ↔ reference.Valid := {alignment_proof}\n"
                          "#print axioms alignment\n")
    if arity != 2:
        target = f"({arity} : Nat) ≠ 2"
    else:
        target = "candidate = sourceRoles" if matches else "candidate ≠ sourceRoles"
    role = f"theorem operatorRoles : {target} := by decide\n#print axioms operatorRoles\n"
    return base + DECIDABLE + aligned_definition + role, base, forecast, matches


def verify(index, english, formal, candidate):
    """Bind the exact sources, then kernel-check both the old and new judgments."""
    out = {"strict_accept": False, "concept": "UNKNOWN", "correspondence": "UNKNOWN",
           "proof": "NOT_CHECKED"}
    if type(index) is not int or index not in SOURCES or type(english) is not str or type(formal) is not str:
        return dict(out, concept="UNSUPPORTED_SOURCE")
    english_hash, formal_hash, orientation = SOURCES[index]
    try:
        bound = (len(english) <= 1024 and len(formal) <= 1024
                 and sha(english) == english_hash and sha(formal) == formal_hash)
    except UnicodeEncodeError:
        bound = False
    if not bound:
        return dict(out, concept="SOURCE_BINDING_MISMATCH")
    reference = external_reference(formal)
    if reference is None:
        return dict(out, concept="UNSUPPORTED_FORMAL_SIGNATURE")
    try:
        validate(candidate)
        source, base, proposal, matches = _program(reference, candidate, orientation)
        module = MODULE.read_bytes()
        out.update(source_index=index, english_sha256=english_hash, formal_sha256=formal_hash,
                   formal_alignment=orientation, lean_sha256=sha(source), extensional_lean_sha256=sha(base),
                   library_sha256=hashlib.sha256(module).hexdigest(),
                   candidate_sha256=sha(json.dumps(candidate, ensure_ascii=True, separators=(",", ":"), sort_keys=True)))
        lean = shutil.which("lean")
        if lean is None:
            raise RuntimeError("pinned Lean missing")
        lean = str(Path(lean).absolute())
        library, env, checker = _library(lean, module)
        with tempfile.TemporaryDirectory(prefix="pcs-operator-role-") as scratch:
            path = Path(scratch)
            env = dict(env, LEAN_PATH=os.pathsep.join([library.name, scratch]))
            (path / "Roles.lean").write_text(source, encoding="utf-8")
            audit = _run([lean, "-j1", "-o", "Roles.olean", "Roles.lean"], path, env)
            axioms = _axioms(audit, [*proposal["declarations"], "alignment", "operatorRoles"])
            _run([checker, "Roles"], path, env)
        out.update(concept="PRESERVED" if matches else "ROLE_MISMATCH", axioms=axioms,
                   correspondence=proposal["correspondence"], proof=proposal["proof"],
                   strict_accept=matches and proposal["correspondence"] == "EQUIVALENT"
                   and proposal["proof"] == "KERNEL_CHECKED")
        return out
    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as e:
        return dict(out, error=str(e))


def controls(candidate):
    result = {"original": candidate}
    alpha = deepcopy(candidate)
    alpha["variables"] = ["Red", "Blue"]
    for operand in alpha["conclusion"]["equal"]:
        operand[next(iter(operand))] = [{"var": "Red"}, {"var": "Blue"}]
    result["alpha_renamed"] = alpha
    erased = deepcopy(candidate)
    left, right = erased["conclusion"]["equal"]
    if "inf" in left:  # retain only the set-theoretic operation on each side
        erased["conclusion"]["equal"][0] = deepcopy(right)
    else:
        erased["conclusion"]["equal"][1] = deepcopy(left)
    result["lattice_concept_erased"] = erased
    exchanged = deepcopy(candidate)
    exchanged["conclusion"]["equal"].reverse()
    result["english_sides_exchanged"] = exchanged
    permuted = deepcopy(candidate)
    first = permuted["conclusion"]["equal"][0]
    first[next(iter(first))].reverse()
    result["left_arguments_exchanged"] = permuted
    return result


def evaluate(path):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != DATA_SHA256:
        raise ValueError("different upstream release")
    rows = json.loads(data)
    results = {}
    for i in SOURCES:
        row = rows[i]
        candidate = parse_english(row["nl_problem"])
        if candidate is None:
            raise ValueError(f"original English abstained on row {i}")
        results[str(i)] = {label: verify(i, row["nl_problem"], row["formal"], c)
                           for label, c in controls(candidate).items()}
    return {"revision": REVISION, "data_sha256": DATA_SHA256, "results": results}


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("basic_test", type=Path)
    print(json.dumps(evaluate(cli.parse_args().basic_test), indent=2, sort_keys=True))
