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
