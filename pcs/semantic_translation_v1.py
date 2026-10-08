"""PCS Semantic Translation v1: deterministic, *non-authoritative* Python precheck.

Untrusted model proposals never become proof-authoritative here. A future Lean
refinement + exact-source compiled verifier is required for that boundary.
Only a trusted caller supplies/pins the registry and independently verifies
interpretation confirmation and elaboration/proof receipts.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping

REGISTRY_FORMAT = "pcs-semantic-symbol-registry-v1"
INTERPRETATION_FORMAT = "pcs-human-interpretation-v1"
CANDIDATE_FORMAT = "pcs-semantic-translation-candidate-v1"
DECISION_FORMAT = "pcs-semantic-translation-decision-v1"
EXPLANATION_FORMAT = "pcs-explanation-ir-v1"
_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,127}$")
_SHA = re.compile(r"^[a-f0-9]{64}$")
MAX_DEPTH = 64
MAX_NODES = 2048
MAX_SYMBOLS = 256
MAX_ASSUMPTIONS = 64


class SemanticError(ValueError):
    def __init__(self, code: str, path: str, message: str):
        super().__init__(message)
        self.code, self.path, self.message = code, path, message

    def record(self) -> dict[str, str]:
        return {"code": self.code, "path": self.path, "message": self.message}


def _error(code: str, path: str, message: str) -> None:
    raise SemanticError(code, path, message)


def _object(value: Any, path: str, required: set[str], allowed: set[str]) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        _error("MALFORMED_CANDIDATE", path, "expected an object")
    missing, extra = required - value.keys(), value.keys() - allowed
    if missing or extra:
        _error("MALFORMED_CANDIDATE", path, f"missing keys {sorted(missing)}; unexpected keys {sorted(extra)}")
    return value


def _identifier(value: Any, path: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        _error("MALFORMED_CANDIDATE", path, "invalid identifier")
    return value


def _digest(value: Any, path: str) -> str:
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        _error("MALFORMED_CANDIDATE", path, "expected lowercase SHA-256 digest")
    return value


def _array(value: Any, path: str, max_items: int) -> list[Any]:
    if not isinstance(value, list) or len(value) > max_items:
        _error("MALFORMED_CANDIDATE", path, f"expected array of at most {max_items} items")
    return value


def canonical_bytes(value: Any) -> bytes:
    """Version-local deterministic serialization; not PCS v0.6 JCS equivalence."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _limited_statement(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 4000:
        _error("MALFORMED_CANDIDATE", path, "expected nonempty statement of at most 4000 characters")
    return value


@dataclass
class Registry:
    symbols: dict[str, dict[str, Any]]
    sorts: set[str]
    digest: str


def validate_registry(value: Any, approved_sha256: str) -> Registry:
    """approved_sha256 comes from a trusted configuration, never from proposer output."""
    obj = _object(value, "registry", {"format", "sorts", "symbols"}, {"format", "sorts", "symbols"})
    if obj["format"] != REGISTRY_FORMAT:
        _error("UNSUPPORTED_CONSTRUCT", "registry.format", "unknown registry format")
    actual = sha256(obj)
    if _digest(approved_sha256, "approved_registry_sha256") != actual:
        _error("REGISTRY_COMMITMENT_MISMATCH", "registry", "registry differs from independently approved SHA-256")
    sort_values = _array(obj["sorts"], "registry.sorts", MAX_SYMBOLS)
    sorts: set[str] = set()
    for i, val in enumerate(sort_values):
        name = _identifier(val, f"registry.sorts[{i}]")
        if name in sorts:
            _error("SHADOWED_OR_DUPLICATE_GROUNDING", f"registry.sorts[{i}]", "duplicate sort")
        sorts.add(name)
    symbols: dict[str, dict[str, Any]] = {}
    for i, entry in enumerate(_array(obj["symbols"], "registry.symbols", MAX_SYMBOLS)):
        path = f"registry.symbols[{i}]"
        sym = _object(entry, path, {"id", "kind", "definition_id", "definition_sha256", "provenance"},
                      {"id", "kind", "sort", "args", "definition_id", "definition_sha256", "provenance"})
        ident = _identifier(sym["id"], f"{path}.id")
        if ident in symbols:
            _error("SHADOWED_OR_DUPLICATE_GROUNDING", path, "duplicate canonical symbol")
        if sym["kind"] not in ("predicate", "constant"):
            _error("UNSUPPORTED_CONSTRUCT", f"{path}.kind", "only typed predicates/constants supported")
        _identifier(sym["definition_id"], f"{path}.definition_id")
        _digest(sym["definition_sha256"], f"{path}.definition_sha256")
        provenance = sym["provenance"]
        if not isinstance(provenance, str) or not provenance.strip() or len(provenance) > 1024:
            _error("UNKNOWN_DEFINITION", f"{path}.provenance", "definition requires provenance")
        if sym["kind"] == "constant":
            if "args" in sym or sym.get("sort") not in sorts:
                _error("BINDING_MISMATCH", path, "constant requires one registered sort and no arguments")
        else:
            if "sort" in sym:
                _error("BINDING_MISMATCH", path, "predicate must not carry return sort")
            args = _array(sym.get("args"), f"{path}.args", 12)
            if any(not isinstance(s, str) or s not in sorts for s in args):
                _error("BINDING_MISMATCH", path, "unregistered argument sort")
        symbols[ident] = dict(sym)
    return Registry(symbols=symbols, sorts=sorts, digest=actual)


class Compiler:
    def __init__(self, registry: Registry, free: list[tuple[str, str]]):
        self.registry, self.free = registry, free
        self.used: set[str] = set()
        self.nodes = 0

    def term(self, value: Any, env: list[tuple[str, str]], path: str) -> tuple[Any, str]:
        obj = _object(value, path, set(), {"var", "constant"})
        if len(obj) != 1:
            _error("UNSUPPORTED_CONSTRUCT", path, "term must be exactly one variable or registered constant")
        if "var" in obj:
            ident = _identifier(obj["var"], path + ".var")
            for distance, (name, sort) in enumerate(reversed(env)):
                if name == ident:
                    return ("bound", distance, sort), sort
            for name, sort in self.free:
                if name == ident:
                    return ("free", name, sort), sort
            _error("UNEXPECTED_FREE_VARIABLE", path, f"variable {ident} is not bound or explicitly declared")
        ident = _identifier(obj["constant"], path + ".constant")
        sym = self.registry.symbols.get(ident)
        if sym is None:
            _error("UNRESOLVED_SYMBOL", path, f"constant {ident} is not registered")
        if sym["kind"] != "constant":
            _error("BINDING_MISMATCH", path, "predicate used as a term")
        self.used.add(ident)
        return ("constant", ident, sym["definition_sha256"]), sym["sort"]

    def formula(self, value: Any, env: list[tuple[str, str]], path: str, depth: int = 0) -> Any:
        self.nodes += 1
        if self.nodes > MAX_NODES or depth > MAX_DEPTH:
            _error("UNSUPPORTED_CONSTRUCT", path, "semantic formula complexity limit exceeded")
        if not isinstance(value, dict) or not isinstance(value.get("op"), str):
            _error("MALFORMED_CANDIDATE", path, "formula needs an operator")
        op = value["op"]
        if op in ("true", "false"):
            _object(value, path, {"op"}, {"op"})
            return (op,)
        if op == "atom":
            _object(value, path, {"op", "symbol", "args"}, {"op", "symbol", "args"})
            name = _identifier(value["symbol"], path + ".symbol")
            sym = self.registry.symbols.get(name)
            if sym is None:
                _error("UNRESOLVED_SYMBOL", path, f"predicate {name} is not registered")
            if sym["kind"] != "predicate":
                _error("BINDING_MISMATCH", path, "registered constant used as predicate")
            args = _array(value["args"], path + ".args", 12)
            if len(args) != len(sym["args"]):
                _error("BINDING_MISMATCH", path, "predicate arity mismatch")
            terms = []
            for i, (arg, expected) in enumerate(zip(args, sym["args"])):
                term, got = self.term(arg, env, f"{path}.args[{i}]")
                if got != expected:
                    _error("BINDING_MISMATCH", f"{path}.args[{i}]", f"expected {expected}, received {got}")
                terms.append(term)
            self.used.add(name)
            return ("atom", name, sym["definition_sha256"], tuple(terms))
        if op in ("eq", "neq"):
            _object(value, path, {"op", "left", "right"}, {"op", "left", "right"})
            l, ls = self.term(value["left"], env, path + ".left")
            r, rs = self.term(value["right"], env, path + ".right")
            if ls != rs:
                _error("BINDING_MISMATCH", path, "equality terms have different sorts")
            return (op, l, r)
        if op == "not":
            _object(value, path, {"op", "body"}, {"op", "body"})
            return ("not", self.formula(value["body"], env, path + ".body", depth + 1))
        if op in ("and", "or", "implies"):
            _object(value, path, {"op", "left", "right"}, {"op", "left", "right"})
            return (op, self.formula(value["left"], env, path + ".left", depth + 1),
                    self.formula(value["right"], env, path + ".right", depth + 1))
        if op in ("forall", "exists"):
            _object(value, path, {"op", "var", "sort", "body"}, {"op", "var", "sort", "body"})
            ident = _identifier(value["var"], path + ".var")
            sort = _identifier(value["sort"], path + ".sort")
            if sort not in self.registry.sorts:
                _error("UNKNOWN_DEFINITION", path, "quantifier domain sort unregistered")
            if any(name == ident for name, _ in env) or any(name == ident for name, _ in self.free):
                _error("BINDING_MISMATCH", path, "shadowed bound variable")
            return (op, sort, self.formula(value["body"], env + [(ident, sort)], path + ".body", depth + 1))
        _error("UNSUPPORTED_CONSTRUCT", path, f"unsupported logical operator {op}")


def _free_vars(value: Any, registry: Registry, path: str) -> list[tuple[str, str]]:
    free = []
    for i, val in enumerate(_array(value, path, MAX_SYMBOLS)):
        v = _object(val, f"{path}[{i}]", {"name", "sort"}, {"name", "sort"})
        name, sort = _identifier(v["name"], f"{path}[{i}].name"), _identifier(v["sort"], f"{path}[{i}].sort")
        if sort not in registry.sorts:
            _error("UNKNOWN_DEFINITION", f"{path}[{i}]", "free-variable sort is unknown")
        if name in [item[0] for item in free]:
            _error("BINDING_MISMATCH", path, "duplicate free-variable declaration")
        free.append((name, sort))
    return free


def _scope(value: Any, path: str) -> tuple[str, str]:
    v = _object(value, path, {"context_id", "description"}, {"context_id", "description"})
    return _identifier(v["context_id"], path + ".context_id"), _limited_statement(v["description"], path + ".description")


def compile_claim(value: Mapping[str, Any], registry: Registry, *, human: bool, path: str) -> dict[str, Any]:
    required = {"format", "claim_id", "statement", "formula", "assumptions", "free_variables", "scope"} if human else \
               {"format", "claim_id", "formula", "assumptions", "free_variables", "scope", "grounding"}
    allowed = required | ({"ambiguities", "provenance"} if human else {"model_confidence", "proposer", "proof_receipt", "elaboration_receipt"})
    obj = _object(value, path, required, allowed)
    expected = INTERPRETATION_FORMAT if human else CANDIDATE_FORMAT
    if obj["format"] != expected:
        _error("UNSUPPORTED_CONSTRUCT", path + ".format", "wrong semantic wire format")
    claim_id = _identifier(obj["claim_id"], path + ".claim_id")
    if human:
        _limited_statement(obj["statement"], path + ".statement")
        if "provenance" in obj and not isinstance(obj["provenance"], dict):
            _error("MALFORMED_CANDIDATE", path + ".provenance", "expected structured provenance")
        ambiguity = _array(obj.get("ambiguities", []), path + ".ambiguities", 64)
        if ambiguity:
            _error("AMBIGUOUS_SCOPE", path + ".ambiguities", "interpretation has unresolved ambiguity")
    free = _free_vars(obj["free_variables"], registry, path + ".free_variables")
    scope = _scope(obj["scope"], path + ".scope")
    compiler = Compiler(registry, free)
    assumptions = _array(obj["assumptions"], path + ".assumptions", MAX_ASSUMPTIONS)
    atoms = [compiler.formula(a, [], f"{path}.assumptions[{i}]") for i, a in enumerate(assumptions)]
    if len(set(atoms)) != len(atoms):
        _error("ASSUMPTION_DUPLICATED", path + ".assumptions", "duplicate semantic assumption")
    result = compiler.formula(obj["formula"], [], path + ".formula")
    grounding_errors: list[dict[str, str]] = []
    if not human:
        declared: dict[str, str] = {}
        for i, g in enumerate(_array(obj["grounding"], path + ".grounding", MAX_SYMBOLS)):
            entry = _object(g, f"{path}.grounding[{i}]", {"symbol", "definition_sha256"}, {"symbol", "definition_sha256"})
            name = _identifier(entry["symbol"], f"{path}.grounding[{i}].symbol")
            dig = _digest(entry["definition_sha256"], f"{path}.grounding[{i}].definition_sha256")
            if name in declared:
                _error("SHADOWED_OR_DUPLICATE_GROUNDING", path + ".grounding", "duplicate grounding for symbol")
            declared[name] = dig
        if set(declared) != compiler.used:
            grounding_errors.append({"code": "GROUNDING_MISMATCH", "path": path + ".grounding",
                                     "message": "grounding declarations differ from actually referenced symbols"})
        for name, digest in declared.items():
            if name not in registry.symbols or registry.symbols[name]["definition_sha256"] != digest:
                grounding_errors.append({"code": "UNKNOWN_DEFINITION", "path": path + ".grounding",
                                         "message": f"unregistered or incorrect definition digest for {name}"})
    return {"claim_id": claim_id, "scope": scope, "free": tuple(free),
            "assumptions": tuple(atoms), "formula": result, "symbols": tuple(sorted(compiler.used)),
            "grounding_errors": grounding_errors}


def _diagnose_mismatch(expected: Any, got: Any, path: str) -> dict[str, str] | None:
    if expected == got:
        return None
    if isinstance(expected, tuple) and isinstance(got, tuple) and expected and got:
        a, b = expected[0], got[0]
        if a != b:
            if a == "not" or b == "not":
                code = "NEGATION_MISMATCH"
            elif a in ("forall", "exists") or b in ("forall", "exists"):
                code = "QUANTIFIER_MISMATCH"
            elif {a, b} == {"and", "or"}:
                code = "POLARITY_MISMATCH"
            elif a in ("and", "or", "implies") or b in ("and", "or", "implies"):
                code = "CONNECTIVE_MISMATCH"
            elif a in ("eq", "neq") or b in ("eq", "neq"):
                code = "POLARITY_MISMATCH"
            else:
                code = "SYMBOL_MISMATCH"
            return {"code": code, "path": path, "message": f"operator mismatch: {a} versus {b}"}
        if a == "atom" and expected[1:3] != got[1:3]:
            return {"code": "SYMBOL_MISMATCH", "path": path, "message": "canonical symbol or definition mismatch"}
        if a in ("forall", "exists") and expected[1] != got[1]:
            return {"code": "BINDING_MISMATCH", "path": path, "message": "quantified sort mismatch"}
        if a == "bound" and expected != got:
            return {"code": "BINDING_MISMATCH", "path": path, "message": "variable bound by different quantifier"}
        if a in ("free", "constant") and expected != got:
            return {"code": "SYMBOL_MISMATCH", "path": path, "message": "term reference changed"}
        if len(expected) != len(got):
            return {"code": "ROUNDTRIP_MISMATCH", "path": path, "message": "structural arity mismatch"}
        for i, (x, y) in enumerate(zip(expected[1:], got[1:]), 1):
            issue = _diagnose_mismatch(x, y, f"{path}[{i}]")
            if issue:
                return issue
    return {"code": "ROUNDTRIP_MISMATCH", "path": path, "message": "different normalized structured meaning"}


def _match_assumptions(expected: tuple, given: tuple) -> list[dict[str, str]]:
    msgs: list[dict[str, str]] = []
    missing = [a for a in expected if a not in given]
    added = [a for a in given if a not in expected]
    if missing:
        msgs.append({"code": "ASSUMPTION_DROPPED", "path": "candidate.assumptions", "message": f"{len(missing)} interpretation assumptions missing"})
    if added:
        msgs.append({"code": "ASSUMPTION_ADDED", "path": "candidate.assumptions", "message": f"{len(added)} unapproved assumptions added"})
    return msgs


def interpretation_digest(interpretation: Mapping[str, Any]) -> str:
    """Commit the entire selected interpretation including original human words."""
    return sha256(interpretation)


def explanation_ir(compiled: Mapping[str, Any], registry: Registry, *, human_digest: str) -> dict[str, Any]:
    """Preserve the normalized AST, not an unconstrained prose generator output."""
    return {"format": EXPLANATION_FORMAT, "claim_id": compiled["claim_id"],
            "interpretation_sha256": human_digest, "registry_sha256": registry.digest,
            "scope": list(compiled["scope"]), "free_variables": list(map(list, compiled["free"])),
            "assumptions": [listify(a) for a in compiled["assumptions"]],
            "conclusion": listify(compiled["formula"]),
            "grounding": [{"symbol": s, "definition_id": registry.symbols[s]["definition_id"],
                           "definition_sha256": registry.symbols[s]["definition_sha256"]} for s in compiled["symbols"]],
            "limitations": ["Human intent is not formally verified", "No external elaboration/proof receipt verified",
                            "Python precheck is not yet Lean-refined or PCS-authoritative"]}


def listify(value: Any) -> Any:
    if isinstance(value, tuple):
        return [listify(x) for x in value]
    return value


def check_translation(
    registry_value: Any, interpretation: Any, candidate: Any,
    *, approved_registry_sha256: str, confirmed_interpretation_sha256: str | None = None,
    claim_ir: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Fail-closed structural precheck; this function *never* grants PCS authority.

    confirmed_interpretation_sha256 must come from an authorized external host,
    not from model-generated candidate data. Confirmation is not proof of intent.
    """
    failures: list[dict[str, str]] = []
    reg: Registry | None = None
    human_compiled = None
    cand_compiled = None
    try:
        reg = validate_registry(registry_value, approved_registry_sha256)
        human_compiled = compile_claim(interpretation, reg, human=True, path="interpretation")
    except (SemanticError, TypeError, ValueError, OverflowError, RecursionError) as exc:
        failures.append(exc.record() if isinstance(exc, SemanticError) else
                        {"code": "MALFORMED_CANDIDATE", "path": "interpretation_or_registry", "message": type(exc).__name__})
    if reg is not None:
        try:
            cand_compiled = compile_claim(candidate, reg, human=False, path="candidate")
        except (SemanticError, TypeError, ValueError, OverflowError, RecursionError) as exc:
            failures.append(exc.record() if isinstance(exc, SemanticError) else
                            {"code": "MALFORMED_CANDIDATE", "path": "candidate", "message": type(exc).__name__})
    if cand_compiled is not None:
        failures.extend(cand_compiled["grounding_errors"])
    if human_compiled is not None and cand_compiled is not None:
        if human_compiled["claim_id"] != cand_compiled["claim_id"]:
            failures.append({"code": "CLAIM_BINDING_MISMATCH", "path": "candidate.claim_id", "message": "claim ID changed"})
        if human_compiled["scope"] != cand_compiled["scope"]:
            failures.append({"code": "AMBIGUOUS_SCOPE", "path": "candidate.scope", "message": "scope differs from selected interpretation"})
        if human_compiled["free"] != cand_compiled["free"]:
            failures.append({"code": "BINDING_MISMATCH", "path": "candidate.free_variables", "message": "declared free variables differ"})
        failures.extend(_match_assumptions(human_compiled["assumptions"], cand_compiled["assumptions"]))
        mismatch = _diagnose_mismatch(human_compiled["formula"], cand_compiled["formula"], "candidate.formula")
        if mismatch:
            failures.append(mismatch)
        if human_compiled["symbols"] != cand_compiled["symbols"]:
            failures.append({"code": "GROUNDING_MISMATCH", "path": "candidate.grounding", "message": "different set of approved symbols used"})
        if claim_ir is not None:
            try:
                _object(claim_ir, "claim_ir", {"format", "claims", "claim_ir_sha256"},
                        set(claim_ir.keys()) if isinstance(claim_ir, dict) else set())
                if claim_ir["format"] != "pcs-claim-ir-v1":
                    _error("CLAIM_BINDING_MISMATCH", "claim_ir.format", "unexpected Claim IR format")
                claims = _array(claim_ir["claims"], "claim_ir.claims", MAX_NODES)
                bound = [c for c in claims if isinstance(c, dict) and c.get("claim_id") == human_compiled["claim_id"]]
                if len(bound) != 1 or bound[0].get("statement") != interpretation["statement"]:
                    _error("CLAIM_BINDING_MISMATCH", "claim_ir.claims", "interpretation does not match exactly one existing Claim IR claim")
                if not isinstance(claim_ir["claim_ir_sha256"], str) or not _SHA.fullmatch(claim_ir["claim_ir_sha256"]):
                    _error("CLAIM_BINDING_MISMATCH", "claim_ir.claim_ir_sha256", "invalid Claim IR commitment")
                # Cross-check full existing Claim IR payload with its JCS commitment.
                # Import the actual PCS canonicalizer, never trust a supplied hash alone.
                from .canonical_json import canonicalize_jcs_bytes
                ir_core = {k: v for k, v in claim_ir.items() if k != "claim_ir_sha256"}
                if hashlib.sha256(canonicalize_jcs_bytes(ir_core)).hexdigest() != claim_ir["claim_ir_sha256"]:
                    _error("CLAIM_BINDING_MISMATCH", "claim_ir.claim_ir_sha256", "Claim IR content does not match its commitment")
            except (SemanticError, TypeError, ValueError) as exc:
                failures.append(exc.record() if isinstance(exc, SemanticError) else
                                {"code": "CLAIM_BINDING_MISMATCH", "path": "claim_ir", "message": "invalid Claim IR"})
    h = interpretation_digest(interpretation) if isinstance(interpretation, dict) else None
    if confirmed_interpretation_sha256 is None or h is None or h != confirmed_interpretation_sha256:
        failures.append({"code": "CONFIRMATION_NOT_VERIFIED", "path": "interpretation", "message": "independent human selection/confirmation digest missing or mismatched"})
    structural = not [f for f in failures if f["code"] != "CONFIRMATION_NOT_VERIFIED"]
    confirmed = not any(f["code"] == "CONFIRMATION_NOT_VERIFIED" for f in failures)
    decision = "REJECTED" if not structural else ("NEEDS_CONFIRMATION" if not confirmed else "STRUCTURALLY_CONFORMANT_NONAUTHORITATIVE")
    result: dict[str, Any] = {
        "format": DECISION_FORMAT, "decision": decision,
        "structural_precheck_pass": structural, "authoritative": False,
        "interpretation_sha256": h, "registry_sha256": reg.digest if reg else None,
        "claim_ir_sha256": claim_ir.get("claim_ir_sha256") if isinstance(claim_ir, dict) else None,
        "diagnostics": failures,
        "unverified_authority_bridges": ["PYTHON_CHECKER_LEAN_REFINEMENT_NOT_VERIFIED",
                                         "ELABORATION_NOT_VERIFIED", "PROOF_NOT_VERIFIED",
                                         "PCS_EXECUTABLE_AUTHORITY_NOT_INVOKED"],
    }
    if structural and human_compiled is not None and reg is not None:
        expl = explanation_ir(human_compiled, reg, human_digest=h)
        result["explanation_ir"] = expl
        result["explanation_ir_sha256"] = sha256(expl)
    return result


def attach_to_claim_ir(claim_ir: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
    """Non-authoritative extension for existing claim IR / POG consumption."""
    if claim_ir.get("format") != "pcs-claim-ir-v1" or not isinstance(claim_ir.get("claim_ir_sha256"), str):
        _error("CLAIM_BINDING_MISMATCH", "claim_ir", "expected existing PCS v1 Claim IR")
    if result.get("format") != DECISION_FORMAT or result.get("claim_ir_sha256") != claim_ir["claim_ir_sha256"]:
        _error("CLAIM_BINDING_MISMATCH", "result", "semantic result not bound to this Claim IR")
    claim_id = result.get("explanation_ir", {}).get("claim_id")
    if not isinstance(claim_id, str):
        _error("CLAIM_BINDING_MISMATCH", "result", "claim binding unavailable on unsuccessful structural check")
    return {"format": "pcs-claim-ir-semantic-overlay-v1", "claim_ir_sha256": claim_ir["claim_ir_sha256"],
            "claim_id": claim_id, "semantic_translation": dict(result),
            "pcs_authority_granted": False,
            "blocking_obligations": list(result["unverified_authority_bridges"]) +
                                    [d["code"] for d in result["diagnostics"]]}
