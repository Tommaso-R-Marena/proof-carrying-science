"""Explicit scientific intake bound to the existing Claim IR and graph formats."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import re

from pcs.proof_translation_v06 import _claim_ir_v06, _obligation, _proof_obligation_graph
from pcs.semantic_translation_v1 import Compiler, validate_registry
from .logic import check, digest, exact, integer, task

PROJECT_FORMAT = "pcs-omega-project-v1"


def text(value, label, maximum=10000):
    if type(value) is not str or not value.strip() or len(value) > maximum:
        raise ValueError(f"Invalid {label}")
    return value


def validate_project(project):
    exact(project, {"format", "source", "claims"}, "project")
    if project["format"] != PROJECT_FORMAT:
        raise ValueError("Unsupported project version; no implicit migration")
    source = exact(project["source"], {"name", "revision", "license", "text"}, "source")
    for field in source:
        text(source[field], "source " + field, 24000 if field == "text" else 512)
    claims = project["claims"]
    if type(claims) is not list or not 1 <= len(claims) <= 16:
        raise ValueError("Project must contain 1–16 explicit claims")
    ids = []
    for c in claims:
        exact(c, {"id", "statement", "source_lines", "task", "scope", "assumptions", "depends_on"}, "claim")
        if type(c["id"]) is not str or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,47}", c["id"]) or c["id"] in ids:
            raise ValueError("Invalid or duplicate claim ID")
        ids.append(c["id"])
        text(c["statement"], "claim statement", 2000)
        text(c["scope"], "claim scope", 2000)
        if type(c["source_lines"]) is not list or len(c["source_lines"]) != 2:
            raise ValueError("Source lines must identify an inclusive range")
        lines = source["text"].splitlines()
        a, b = c["source_lines"]
        integer(a, 1, len(lines), "first source line")
        integer(b, a, len(lines), "last source line")
        if c["statement"] not in "\n".join(lines[a - 1:b]):
            raise ValueError("Claim statement absent from cited source range")
        task(c["task"])
        if type(c["assumptions"]) is not list or len(c["assumptions"]) > 16:
            raise ValueError("Assumptions must be an explicit bounded array")
        for assumption in c["assumptions"]:
            text(assumption, "assumption", 2000)
        if (type(c["depends_on"]) is not list or len(c["depends_on"]) > 16 or
                any(type(n) is not str for n in c["depends_on"]) or len(set(c["depends_on"])) != len(c["depends_on"])):
            raise ValueError("Invalid dependencies")
    seen, active = set(), set()
    lookup = {c["id"]: c for c in claims}

    def visit(name):
        if name not in lookup or name in active:
            raise ValueError("Dangling or cyclic claim dependency")
        if name in seen:
            return
        active.add(name)
        for dep in lookup[name]["depends_on"]:
            visit(dep)
        active.remove(name)
        seen.add(name)

    for name in ids:
        visit(name)
    # Reuse the existing semantic compiler for a second, typed AST check. This
    # is an experimental registry pin, not owner/intent or authority approval.
    for c in claims:
        reg = {"format": "pcs-semantic-symbol-registry-v1", "sorts": [], "symbols": [
            {"id": n, "kind": "predicate", "args": [], "definition_id": "Omega." + n,
             "definition_sha256": digest({"symbol": n, "domain": "Bool"}),
             "provenance": "Explicit experimental Boolean interpretation; external grounding unproved"}
            for n in c["task"]["variables"]]}
        checked_registry = validate_registry(reg, digest(reg))
        for f in ("source", "candidate"):
            Compiler(checked_registry, []).formula(c["task"][f], [], "omega." + f)
    return deepcopy(project)


def compile_project(project):
    project = validate_project(project)
    source, candidates, receipts = project["source"], [], {}
    source_sha = hashlib.sha256(source["text"].encode("utf-8")).hexdigest()
    source_id = "omega-source"
    inventory = {source_id: {"id": source_id, "path": source["name"],
                            "sha256": source_sha, "size": len(source["text"].encode("utf-8")), "media_type": "text/plain"}}
    for c in project["claims"]:
        receipt = check(c["task"])
        receipts[c["id"]] = receipt
        obligations = [
            _obligation(c["id"], "OMEGA_INTENT_GROUNDING", "Boolean interpretation does not establish scientific intent or external observations.", blocking=True),
            _obligation(c["id"], "OMEGA_REGISTERED_AUTHORITY", "Experimental exhaustive checking is not a registered PCS scientific verifier.", blocking=True)]
        if not receipt["equivalent"]:
            obligations.append(_obligation(c["id"], "OMEGA_MEANING_MISMATCH", "The candidate differs from the selected interpretation under a checked Boolean valuation.", blocking=True, details={"counterexample": receipt["counterexample"]}))
        candidates.append({"id": c["id"], "source": {**source, "text": None, "source_sha256": source_sha, "source_lines": c["source_lines"]},
            "artifact_ids": [source_id], "selected": False, "formalizable": False,
            "status": "EXPERIMENTAL_BOOLEAN_CHECKED", "finding": c["statement"],
            "typed_claim": {"id": c["id"], "kind": "formal", "statement": c["statement"],
                "predicate": {"format": "pcs-omega-interpretation-v1", "task": c["task"], "scope": c["scope"], "receipt_sha256": digest(receipt)}},
            "check": {"id": c["id"], "type": "omega_exhaustive_bool_experimental"},
            "assumptions": [{"id": c["id"] + "-a" + str(i), "statement": s} for i, s in enumerate(c["assumptions"])],
            "decomposition": {"parent_claim_id": None, "relation": "root", "depends_on_claim_ids": c["depends_on"], "depth": 0},
            "obligations": obligations})
    ir = _claim_ir_v06(candidates)
    graph = _proof_obligation_graph(candidates, inventory=inventory, claim_ir=ir)
    return {"format": "pcs-omega-intake-v1", "project_sha256": digest(project),
            "source_sha256": source_sha, "source_metadata_sha256": digest(source), "claim_ir": ir, "obligation_graph": graph,
            "receipts": receipts, "experimental": True, "pcs_authority": False,
            "grounding": "Explicit source ranges and selected Boolean interpretations; no automatic scientific or natural-language understanding"}


def invalidate(project, changed_claim_ids):
    """Conservative transitive reopening within the explicitly declared graph."""
    project = validate_project(project)
    if type(changed_claim_ids) is not list or any(type(n) is not str or n not in {c["id"] for c in project["claims"]} for n in changed_claim_ids):
        raise ValueError("Unknown changed claim")
    affected = set(changed_claim_ids)
    for _ in project["claims"]:
        affected |= {c["id"] for c in project["claims"] if any(d in affected for d in c["depends_on"])}
    return {"affected": sorted(affected), "dependency_completeness": "Unproved external assumption", "pcs_authority": False}
