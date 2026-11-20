"""Elaboration and reference checks for a closed, first-order Lean fragment.

Candidate source is data. Emit a trusted template containing only generated
binder names, four fixed types, constants, numerals and fixed operators.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import signal
import subprocess
import tempfile
from pathlib import Path
from typing import Any

DEFAULT_PROJECT = Path(__file__).resolve().parent / "lean"
_TYPES = {"Nat", "Int", "Bool", "Prop"}
_CONSTANTS = {"True", "False", "true", "false"}
_OPERATORS = set("()=+*-<>≤≥≠¬∧∨→↔")
_TOKEN = re.compile(r"\s+|[A-Za-z][A-Za-z0-9_]*|[0-9]{1,10}(?![0-9])|:=|->|<=|>=|[():=+*<>≤≥≠¬∧∨→↔-]")
_BINDER = re.compile(r"\(\s*([a-z][a-z0-9_]*(?:\s+[a-z][a-z0-9_]*)*)\s*:\s*(Nat|Int|Bool|Prop)\s*\)")
_HEADER = re.compile(r"(?:theorem|lemma)\s+[A-Za-z][A-Za-z0-9_]*\b|example\b")
_TRANSLATE = {"->": "→", "<=": "≤", ">=": "≥"}


def extract_lean_code(text: str) -> str:
    if len(text) > 4096:
        raise ValueError("candidate exceeds 4096 characters")
    text = text.strip()
    fenced = re.fullmatch(r"```(?:lean4?)?[ \t]*\n(.*)\n```", text, re.S)
    return fenced[1].strip() if fenced else text


def _proposition(code: str) -> str:
    code = extract_lean_code(code)
    code = re.sub(r"^import (?:Mathlib|Std)\s*\n", "", code, count=1).strip()
    header = _HEADER.match(code)
    if header is None:
        raise ValueError("expected a single theorem, lemma or example")
    tail = code[header.end():].strip()
    variables = {}
    binders = []
    while binder := _BINDER.match(tail):
        for name in binder[1].split():
            if name in variables or name in _CONSTANTS or len(variables) >= 16:
                raise ValueError("duplicate, reserved or excess binder")
            variables[name] = f"x{len(variables)}"
            binders.append(f"({variables[name]} : {binder[2]})")
        tail = tail[binder.end():].strip()
    if not tail.startswith(":"):
        raise ValueError("missing proposition")
    tail = tail[1:].strip()
    # Only two exact, historically used annotations are accepted. No proof text
    # is passed to Lean, even when evaluating a candidate with a reference.
    expression, assignment, body = tail.partition(":=")
    if assignment and body.split() not in (["by", "sorry"], ["sorry"]):
        raise ValueError("unsupported proof body")
    tokens = []
    pos = 0
    while pos < len(expression):
        match = _TOKEN.match(expression, pos)
        if match is None:
            raise ValueError("token outside the statement fragment")
        pos = match.end()
        token = _TRANSLATE.get(match[0], match[0])
        if token.isspace():
            continue
        if token in variables:
            tokens.append(variables[token])
        elif token in _CONSTANTS or token in _OPERATORS or token.isdecimal():
            tokens.append(token)
        else:
            raise ValueError("free variable or unsupported symbol")
    if not tokens or len(tokens) > 256:
        raise ValueError("empty or oversized expression")
    return ("∀ " + " ".join(binders) + ", " if binders else "") + " ".join(tokens)


def normalize_candidate(code: str) -> str:
    return "import Std\nset_option autoImplicit false\ndef Candidate : Prop := " + _proposition(code) + "\n"


def _check(source: str, project: Path, timeout: float) -> tuple[int | None, str]:
    if not (project / "lakefile.lean").is_file() and not (project / "lakefile.toml").is_file():
        return None, "missing trusted Lake project"
    with tempfile.TemporaryDirectory(prefix="pgra-statement-") as temp:
        path = Path(temp) / "Statement.lean"
        path.write_text(source, encoding="utf-8")
        try:
            proc = subprocess.Popen(
                ["lake", "env", "lean", str(path)], cwd=project,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                start_new_session=True,
            )
        except OSError as error:
            return None, str(error)
        try:
            output, _ = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.communicate()
            return None, "timeout"
        return proc.returncode, output


def compile_lean(code: str, *, project: Path = DEFAULT_PROJECT, timeout: float = 30.0) -> dict[str, Any]:
    result = dict(compiled=False, proof_verified=False, normalized=None, syntax_valid=None)
    try:
        proposition = _proposition(code)
    except ValueError as error:
        return dict(result, ok=True, status="UNSUPPORTED_SYNTAX", error=str(error))
    source = "import Std\nset_option autoImplicit false\ndef Candidate : Prop := " + proposition + "\n"
    # Query the same Lean parser as elaboration. All text interpolated below
    # has already been rebuilt from the closed vocabulary.
    parse_probe = (
        "import Lean\nopen Lean Elab Command in\nrun_cmd do\n"
        "  match Lean.Parser.runParserCategory (← getEnv) `term "
        + json.dumps(proposition, ensure_ascii=False) + " with\n"
        '  | .ok _ => logInfo "PGRA_SYNTAX_ACCEPTED"\n'
        '  | .error _ => logInfo "PGRA_SYNTAX_INVALID"\n'
    )
    probe = source.replace("set_option autoImplicit false", parse_probe + "set_option autoImplicit false", 1)
    rc, output = _check(probe, project, timeout)
    lines = output.splitlines()
    if rc is None:
        return dict(result, normalized=source, ok=False, status="UNKNOWN", error=output[-4000:])
    if "PGRA_SYNTAX_INVALID" in lines:
        return dict(result, normalized=source, syntax_valid=False, ok=True, status="SYNTAX_INVALID",
                    returncode=rc, error=output[-4000:])
    if "PGRA_SYNTAX_ACCEPTED" not in lines:
        return dict(result, normalized=source, ok=False, status="UNKNOWN", returncode=rc, error=output[-4000:])
    return dict(result, normalized=source, ok=True, compiled=rc == 0, returncode=rc, syntax_valid=True,
                status="WELL_TYPED_UNVALIDATED" if rc == 0 else "ELABORATION_FAILED",
                error=None if rc == 0 else output[-4000:])


def compare_reference(code: str, reference: str, *, project: Path = DEFAULT_PROJECT,
                      timeout: float = 30.0) -> dict[str, Any]:
    """Check definitional equality, then attempt a separate proof with bounded tactics.

    The caller owns the reference's relationship to the English source. Failure
    of definitional equality leaves semantic equivalence open.
    """
    result = compile_lean(code, project=project, timeout=timeout)
    result.update(reference_sha256=hashlib.sha256(reference.encode()).hexdigest(),
                  candidate_sha256=hashlib.sha256(code.encode()).hexdigest(), equivalence_verified=False)
    if not result["compiled"]:
        return result
    try:
        proposition = _proposition(reference)
    except ValueError:
        return dict(result, error="reference outside the statement fragment")
    base = result["normalized"] + f"def Reference : Prop := {proposition}\n"
    equal = base + "theorem sameStatement : Candidate = Reference := rfl\n#print axioms sameStatement\n"
    rc, audit = _check(equal, project, timeout)
    if rc != 0 or "'sameStatement' does not depend on any axioms" not in audit:
        return dict(result, error="definitional equality unchecked or unestablished")
    result.update(status="SEMANTICALLY_EQUIVALENT", equivalence_verified=True,
                  equivalence_source=equal, equivalence_audit=audit.strip())
    proof = equal + ("theorem sourceTheorem : Candidate := by\n"
                     "  unfold Candidate\n  intros\n  first | rfl | decide | omega | assumption\n"
                     "#print axioms sourceTheorem\n")
    rc, audit = _check(proof, project, timeout)
    if rc != 0:
        return result
    allowed = {"propext", "Classical.choice", "Quot.sound"}
    found = re.search(r"'sourceTheorem' depends on axioms: \[([^\]]*)\]", audit)
    if "'sourceTheorem' does not depend on any axioms" in audit:
        deps = []
    elif found:
        deps = [v.strip() for v in found[1].split(",")]
    else:
        return result
    if set(deps) <= allowed:
        result.update(status="PROOF_VERIFIED", proof_verified=True,
                      proof_source=proof, proof_audit=audit.strip(), proof_axioms=deps)
    return result
