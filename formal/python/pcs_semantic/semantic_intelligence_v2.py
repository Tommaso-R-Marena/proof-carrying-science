"""PCS Proof-Carrying Semantic Intelligence v2 — Python client for the Lean authority.

Like the v1 client, this module contains **no semantic checking logic**.  Every decision is
computed by the compiled Lean binary ``pcs-semantic-check --v2``, whose pure decision
function ``PCS.V2.Semantic.semanticCheckV2`` is proved (``PCS.V2.TranslationV2Json``) to
compute the certified v2 classifier ``decideV2`` on canonical input bytes, and whose
``CERTIFIED_TRANSLATION`` outcome is proved to imply denotational equivalence of the selected
interpretation and the candidate in every model.

Python only serializes canonically, invokes the binary, and parses its output **fail-closed**:
any error (missing binary, crash, timeout, unexpected exit code, schema mismatch, outcome /
exit-code disagreement, certified outcome with diagnostics) is reported as
``INVALID_PROPOSAL`` and is never authoritative.

The independent re-verification helpers at the end (``evaluate_claim``,
``countermodel_is_valid``) are a *test oracle* written separately from the Lean evaluator;
they are used by the test-suite for differential checking and are not part of the authority.
"""

from __future__ import annotations

import itertools
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .semantic_translation_v1 import canonical_json

REQUEST_SCHEMA = "pcs-semantic-translation-v2"
DECISION_SCHEMA = "pcs-semantic-decision-v2"
RECORD_SCHEMA = "pcs-verifier-feedback-v1"
COUNTERMODEL_SCHEMA = "pcs-countermodel-v1"

OUTCOMES = ("CERTIFIED_TRANSLATION", "VERIFIED_COUNTEREXAMPLE", "NEEDS_HUMAN_CLARIFICATION",
            "UNRESOLVED_PROOF_OBLIGATION", "UNSUPPORTED_FRAGMENT", "SEARCH_EXHAUSTED",
            "INVALID_PROPOSAL")
LABELS = ("VERIFIED_POSITIVE", "VERIFIED_SEMANTIC_NEGATIVE", "CONTRACT_REJECTION", "UNRESOLVED")

_DEFAULT_BINARY = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    ".lake", "build", "bin", "pcs-semantic-check")


@dataclass
class DecisionV2:
    outcome: str
    label: str = "UNRESOLVED"
    diagnostics: List[Dict[str, str]] = field(default_factory=list)
    exit_code: Optional[int] = None
    raw: Optional[Dict[str, Any]] = None

    @property
    def authoritative(self) -> bool:
        """True only for a well-formed CERTIFIED_TRANSLATION decision with exit code 0."""
        return (self.outcome == "CERTIFIED_TRANSLATION" and self.exit_code == 0
                and not self.diagnostics and self.raw is not None
                and self.raw.get("schema") == DECISION_SCHEMA
                and self.label == "VERIFIED_POSITIVE")

    @property
    def codes(self) -> List[str]:
        return [d.get("code", "") for d in self.diagnostics]

    @property
    def semantic_status(self) -> Dict[str, Any]:
        return (self.raw or {}).get("semantic_status") or {}

    @property
    def countermodel(self) -> Optional[Dict[str, Any]]:
        s = self.semantic_status
        return s.get("countermodel") if s.get("kind") == "VERIFIED_COUNTERMODEL" else None

    @property
    def certificate(self) -> Optional[Dict[str, Any]]:
        return (self.raw or {}).get("certificate")

    @property
    def repair_obligations(self) -> List[Dict[str, Any]]:
        return (self.raw or {}).get("repair_obligations") or []

    def feedback(self) -> Dict[str, Any]:
        """Deterministic, machine-readable checker feedback for an untrusted proposer."""
        return {"outcome": self.outcome, "label": self.label,
                "failure_codes": sorted(set(self.codes)),
                "repair_obligations": self.repair_obligations,
                "countermodel": self.countermodel,
                "needs_human": any(o.get("requires_human_clarification") for o in self.repair_obligations)}


def _invalid(reason: str, exit_code: Optional[int] = None) -> DecisionV2:
    return DecisionV2(outcome="INVALID_PROPOSAL", label="CONTRACT_REJECTION",
                      diagnostics=[{"code": "MALFORMED_INPUT", "component": "python-bridge",
                                    "detail": reason}], exit_code=exit_code)


def parse_decision_v2(stdout: bytes, exit_code: int) -> DecisionV2:
    """Parse the binary's v2 output, failing closed on any inconsistency."""
    try:
        raw = json.loads(stdout.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        return _invalid(f"unparsable checker output: {exc}", exit_code)
    if not isinstance(raw, dict) or raw.get("schema") != DECISION_SCHEMA:
        return _invalid("checker output has the wrong schema", exit_code)
    outcome, label = raw.get("outcome"), raw.get("label")
    if outcome not in OUTCOMES or label not in LABELS:
        return _invalid("checker output has an unknown outcome or label", exit_code)
    expected_rc = {"CERTIFIED_TRANSLATION": 0, "VERIFIED_COUNTEREXAMPLE": 3}.get(outcome, 1)
    if exit_code != expected_rc:
        return _invalid("checker outcome and exit code disagree", exit_code)
    diags = raw.get("diagnostics")
    if not isinstance(diags, list) or (outcome == "CERTIFIED_TRANSLATION" and diags):
        return _invalid("checker diagnostics inconsistent with outcome", exit_code)
    if (outcome == "CERTIFIED_TRANSLATION") != (label == "VERIFIED_POSITIVE"):
        return _invalid("checker label inconsistent with outcome", exit_code)
    return DecisionV2(outcome=outcome, label=label, diagnostics=diags, exit_code=exit_code,
                      raw=raw)


def _run(args: List[str], files: Dict[str, bytes], binary: str, timeout: float):
    if not os.path.isfile(binary):
        return None, f"checker binary not found: {binary}"
    with tempfile.TemporaryDirectory() as d:
        paths = []
        for name, data in files.items():
            p = os.path.join(d, name)
            with open(p, "wb") as f:
                f.write(data)
            paths.append(p)
        try:
            proc = subprocess.run([binary, *args, *paths], capture_output=True, timeout=timeout)
        except Exception as exc:  # noqa: BLE001
            return None, f"checker invocation failed: {exc}"
    return proc, None


def check_v2_bytes(authority_bytes: bytes, request_bytes: bytes,
                   binary: str = _DEFAULT_BINARY, timeout: float = 300.0) -> DecisionV2:
    proc, err = _run(["--v2"], {"authority.json": authority_bytes, "request.json": request_bytes},
                     binary, timeout)
    if proc is None:
        return _invalid(err or "checker failed")
    if proc.returncode not in (0, 1, 3):
        return _invalid(f"checker exited with status {proc.returncode}", proc.returncode)
    return parse_decision_v2(proc.stdout, proc.returncode)


def check_v2(authority: Dict[str, Any], request: Dict[str, Any],
             binary: str = _DEFAULT_BINARY, timeout: float = 300.0) -> DecisionV2:
    try:
        a, r = canonical_json(authority), canonical_json(request)
    except Exception as exc:  # noqa: BLE001
        return _invalid(f"request is outside the canonical JSON fragment: {exc}")
    return check_v2_bytes(a, r, binary=binary, timeout=timeout)


def check_countermodel_bytes(authority_bytes: bytes, bundle_bytes: bytes,
                             binary: str = _DEFAULT_BINARY, timeout: float = 120.0) -> bool:
    """True only if the Lean re-verifier prints VALID_COUNTERMODEL with exit code 0."""
    proc, _ = _run(["--check-countermodel"],
                   {"authority.json": authority_bytes, "bundle.json": bundle_bytes}, binary, timeout)
    return (proc is not None and proc.returncode == 0
            and proc.stdout.strip() == b"VALID_COUNTERMODEL")


def _parse_record(stdout: bytes) -> Optional[Dict[str, Any]]:
    try:
        rec = json.loads(stdout.decode("utf-8"))
    except Exception:  # noqa: BLE001
        return None
    return rec if isinstance(rec, dict) and rec.get("schema") == RECORD_SCHEMA else None


def training_record(authority_path: str, request_path: str, provenance: str, revision: str,
                    binary: str = _DEFAULT_BINARY, timeout: float = 300.0) -> Optional[Dict[str, Any]]:
    if not os.path.isfile(binary):
        return None
    try:
        proc = subprocess.run([binary, "--v2-record", authority_path, request_path, provenance,
                               revision], capture_output=True, timeout=timeout)
    except Exception:  # noqa: BLE001
        return None
    return None if proc.returncode != 0 else _parse_record(proc.stdout)


def propose_check_repair_v2(authority: Dict[str, Any], proposer, max_rounds: int = 5,
                            binary: str = _DEFAULT_BINARY) -> Optional[Dict[str, Any]]:
    """Untrusted propose → check → repair loop driven by the checker's repair obligations.

    ``proposer(history)`` returns the next v2 request given ``(request, feedback)`` pairs.
    Only a request that the Lean authority certifies is returned; a decision requiring human
    clarification stops the loop (PCS never guesses intent)."""
    history: List[Any] = []
    for _ in range(max_rounds):
        req = proposer(history)
        dec = check_v2(authority, req, binary=binary)
        if dec.authoritative:
            return req
        fb = dec.feedback()
        history.append((req, fb))
        if dec.outcome == "NEEDS_HUMAN_CLARIFICATION":
            return None
    return None


# ---------------------------------------------------------------------------------------
# Independent test oracle (NOT part of the authority)
# ---------------------------------------------------------------------------------------

class _Model:
    """A finite structure in the ``pcs-countermodel-v1`` JSON shape."""

    def __init__(self, m: Dict[str, Any]):
        self.dom = {s["sort"]: list(s["carrier"]) for s in m["sorts"]}
        self.preds = {p["symbol"]: {tuple(t) for t in p["true_on"]} for p in m["predicates"]}
        self.fns = {f["symbol"]: {tuple(r["args"]): r["value"] for r in f["table"]}
                    for f in m["functions"]}

    def carrier(self, s: str) -> List[int]:
        return self.dom.get(s, [])

    def fn(self, f: str, args) -> int:
        return self.fns.get(f, {}).get(tuple(args), 0)

    def pred(self, p: str, args) -> bool:
        return tuple(args) in self.preds.get(p, set())


def _term(t, M: _Model, env):
    if "var" in t:
        return env.get(t["var"], 0)
    return M.fn(t["fn"], [_term(a, M, env) for a in t["args"]])


def _formula(f, M: _Model, env) -> bool:
    op = f["op"]
    if op == "true":
        return True
    if op in ("false", "unsupported"):
        return False
    if op == "pred":
        return M.pred(f["symbol"], [_term(a, M, env) for a in f["args"]])
    if op == "eq":
        return _term(f["lhs"], M, env) == _term(f["rhs"], M, env)
    if op == "ne":
        return _term(f["lhs"], M, env) != _term(f["rhs"], M, env)
    if op == "not":
        return not _formula(f["arg"], M, env)
    if op == "and":
        return _formula(f["lhs"], M, env) and _formula(f["rhs"], M, env)
    if op == "or":
        return _formula(f["lhs"], M, env) or _formula(f["rhs"], M, env)
    if op == "implies":
        return (not _formula(f["lhs"], M, env)) or _formula(f["rhs"], M, env)
    if op in ("forall", "exists"):
        vals = (_formula(f["body"], M, {**env, f["var"]: d}) for d in M.carrier(f["sort"]))
        return all(vals) if op == "forall" else any(vals)
    raise ValueError(f"unknown operator {op!r}")


def evaluate_claim(claim: Dict[str, Any], model: Dict[str, Any]) -> bool:
    """Truth of a structured claim (universal closure over its parameters, assumptions ⇒
    conclusion) in a finite structure, by direct recursion — independent of the Lean code."""
    M = _Model(model)
    names = [p["name"] for p in claim["params"]]
    for vals in itertools.product(*[M.carrier(p["sort"]) for p in claim["params"]]):
        env = dict(zip(names, vals))
        if all(_formula(a, M, env) for a in claim["assumptions"]) and \
                not _formula(claim["conclusion"], M, env):
            return False
    return True


def model_conforms(authority: Dict[str, Any], model: Dict[str, Any]) -> bool:
    """Registry conformance: every approved sort has a non-empty carrier and every approved
    function maps typed arguments into the carrier of its result sort."""
    M = _Model(model)
    for s in authority["registry"]["sorts"]:
        if not M.carrier(s["id"]):
            return False
    for e in authority["registry"]["symbols"]:
        if e["kind"] == "fn":
            for args in itertools.product(*[M.carrier(a) for a in e["args"]]):
                if M.fn(e["id"], args) not in M.carrier(e["result"]):
                    return False
    return True


def countermodel_is_valid(authority: Dict[str, Any], interpretation: Dict[str, Any],
                          candidate: Dict[str, Any], countermodel: Dict[str, Any]) -> bool:
    """Independent re-check of a countermodel witness."""
    m = countermodel["model"]
    i, c = evaluate_claim(interpretation, m), evaluate_claim(candidate, m)
    return (model_conforms(authority, m) and i == countermodel["interpretation_holds"]
            and c == countermodel["candidate_holds"] and i != c)


# ---------------------------------------------------------------------------------------
# Independent PCS-CNL parser (test oracle for the controlled-language output)
# ---------------------------------------------------------------------------------------

_KEYWORDS = {"var", "apply", "(", ")", "true", "false", "holds", "of", "equals", "differs-from",
             "not", "both", "and", "either", "or", "if", "then", "for-every", "there-exists",
             "of-sort", "unsupported"}


def parse_cnl(sentence: str) -> Optional[Dict[str, Any]]:
    """Parse a PCS-CNL sentence into the structured-formula JSON (None if not in the
    language).  Written independently of ``PCS.V2.CNL``."""
    words = sentence.split(" ")
    pos = 0

    def peek():
        return words[pos] if pos < len(words) else None

    def take(expected=None):
        nonlocal pos
        w = peek()
        if w is None or (expected is not None and w != expected):
            raise ValueError
        pos += 1
        return w

    def ident():
        w = take()
        if w in _KEYWORDS or w == "" or " " in w:
            raise ValueError
        return w

    def term():
        w = take()
        if w == "var":
            return {"var": ident()}
        if w == "apply":
            f = ident()
            take("(")
            args = []
            while peek() != ")":
                args.append(term())
            take(")")
            return {"args": args, "fn": f}
        raise ValueError

    def bracketed():
        take("(")
        f = formula()
        take(")")
        return f

    def formula():
        w = take()
        if w == "true":
            return {"op": "true"}
        if w == "false":
            return {"op": "false"}
        if w == "holds":
            p = ident()
            take("of")
            take("(")
            args = []
            while peek() != ")":
                args.append(term())
            take(")")
            return {"args": args, "op": "pred", "symbol": p}
        if w == "(":
            a = term()
            k = take()
            b = term()
            take(")")
            if k == "equals":
                return {"lhs": a, "op": "eq", "rhs": b}
            if k == "differs-from":
                return {"lhs": a, "op": "ne", "rhs": b}
            raise ValueError
        if w == "not":
            return {"arg": bracketed(), "op": "not"}
        for kw, sep, op in (("both", "and", "and"), ("either", "or", "or"),
                            ("if", "then", "implies")):
            if w == kw:
                lhs = bracketed()
                take(sep)
                return {"lhs": lhs, "op": op, "rhs": bracketed()}
        if w in ("for-every", "there-exists"):
            x = ident()
            take("of-sort")
            s = ident()
            return {"body": bracketed(), "op": "forall" if w == "for-every" else "exists",
                    "sort": s, "var": x}
        if w == "unsupported":
            return {"construct": ident(), "op": "unsupported"}
        raise ValueError

    try:
        f = formula()
    except ValueError:
        return None
    return f if pos == len(words) else None
