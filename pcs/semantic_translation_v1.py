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
