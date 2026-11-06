"""Deterministic, source-bound scientific proposals; never scientific authority.

The deliberately small directive grammar describes observations that independent
checkers can repeat. Free prose and a successful mathematical proof cannot grant
scientific meaning or acceptance. All other schemas are research sidecars.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import PurePosixPath
import re

VERSION = "scientific-knowledge-v1.0"
FORMAT = "pcs-scientific-intake-graph-v1"
_NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
_DIRECTIVE = re.compile(r"^PCS-CLAIM:\s*([a-z_]+)\(([^()]*)\)\s*=\s*(.*?)\s*[.;]?\s*$")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _source(artifact, segment):
    return {"artifact_id": artifact["id"], "sha256": artifact["sha256"],
            "locator": deepcopy(segment.get("locator", {})), "quote": segment.get("text", "")}


def _resolve(reference, artifacts):
    exact = [a for a in artifacts if a.get("path") == reference or a.get("id") == reference]
    if len(exact) == 1:
        return exact[0]
    names = [a for a in artifacts if PurePosixPath(a.get("path", "")).name == reference]
    return names[0] if len(names) == 1 else None


def _directive(line, artifacts):
    match = _DIRECTIVE.fullmatch(line.strip())
    if not match:
        return None
    operation, raw_args, expected = match.groups()
    args = [a.strip().strip('"\'') for a in raw_args.split(",")]
    shape = {"rows": (1, "csv_rows", "computational"),
             "ols_optimality": (2, "ols_optimality", "computational"),
             "sum": (2, "csv_numeric", "statistical"),
             "mean": (2, "csv_numeric", "statistical"),
             "sequence_length": (2, "sequence_length", "empirical"),
             "coordinate_count": (1, "coordinate_count", "empirical"),
             "sequence_matches_structure": (3, "sequence_matches_structure", "mixed"),
             "has_field": (2, "json_field", "computational"),
             "imports": (2, "python_import", "computational")}.get(operation)
    if not shape or len(args) != shape[0] or any(not a for a in args):
        return {"checker": "unsupported", "kind": "unsupported", "payload": {"reason": "Unsupported directive grammar"}, "targets": []}
    _, checker, kind = shape
    bool_op = operation in {"sequence_matches_structure", "has_field", "imports", "ols_optimality"}
    valid = expected.lower() in {"true", "false"} if bool_op else bool(re.fullmatch(_NUMBER, expected))
    if operation in {"rows", "sequence_length", "coordinate_count"}:
        valid = bool(re.fullmatch(r"\d+", expected))
    references = args[:2] if operation in {"sequence_matches_structure","ols_optimality"} else args[:1]
    targets = [_resolve(ref, artifacts) for ref in references]
    if not valid or not all(targets):
        reason = "Invalid exact expected value" if not valid else "Missing or ambiguous artifact reference"
        return {"checker": "unsupported", "kind": kind, "payload": {"reason": reason, "references": references}, "targets": [a for a in targets if a]}
    payload = {"operation": operation, "artifact_id": targets[0]["id"],
               "expected": expected.lower() if bool_op else expected}
    if operation == "ols_optimality":
        payload["fit_artifact_id"] = targets[1]["id"]
    elif operation in {"sum", "mean"}:
        payload["column"] = args[1]
    elif operation == "sequence_length":
        payload["sequence_id"] = args[1]
    elif operation == "sequence_matches_structure":
        payload.update(structure_artifact_id=targets[1]["id"], chain=args[2])
    elif operation in {"has_field", "imports"}:
        payload["pointer" if operation == "has_field" else "module"] = args[1]
    return {"checker": checker, "kind": kind, "payload": payload, "targets": targets}


def build_graph(artifacts):
    """Build proposals from adapter records without executing submitted content."""
    if isinstance(artifacts, dict):
        artifacts = list(artifacts.values())
    artifacts = sorted(artifacts, key=lambda a: (a.get("path", ""), a["id"]))
    claims, obligations, edges, assumptions = [], [], [], []
    seen = set()
    truncated = False

    def add(artifact, segment, statement, kind, checker, payload, targets=(), *, interpretation=None):
        nonlocal truncated
        if len(claims) >= 256:
            truncated = True
            return
        source = _source(artifact, segment)
        seed = {"source": source, "statement": statement, "kind": kind,
                "checker": checker, "payload": payload, "transform": VERSION}
        claim_id = "claim-" + digest(seed)[:24]
        if claim_id in seen:
            return
        seen.add(claim_id)
        refs = {a["id"]: a for a in [artifact, *targets]}
        bindings = [{"artifact_id": a["id"], "sha256": a["sha256"], "size": a["size"]}
                    for a in sorted(refs.values(), key=lambda a: a["id"])]
        claim = {"id": claim_id, "kind": kind, "status": "NEEDS_REVIEW" if checker == "unsupported" else "PROPOSED",
                 "statement": statement, "source": source,
                 "meaning_status": "NEEDS_REVIEW", "verification_status": "UNCHECKED",
                 "extraction_status": "PROPOSED", "authority": False,
                 "transform": {"name": "scientific-proposal-extraction", "version": VERSION}}
        if interpretation is not None:
            claim["interpretation"] = interpretation
        claims.append(claim)
        local_assumptions = ["Only the explicitly bound artifact bytes are checked.",
                             "Extraction and exact arithmetic do not establish scientific validity or intended meaning."]
        if checker == "csv_numeric":
            local_assumptions.append("CSV cells and the expected value are exact finite decimal numbers; no float tolerance is implied.")
        assumption = {"id": "assumption-" + digest([claim_id, local_assumptions])[:24],
                      "claim_id": claim_id, "statements": local_assumptions, "source": source,
                      "status": "DECLARED", "authority": False, "transform": {"name": "scope-boundary", "version": VERSION}}
        assumptions.append(assumption)
        for name, details, category in [(checker, payload, "verification"),
                                        ("meaning_review", {"reason": "Scientific meaning and source interpretation require review."}, "meaning")]:
            obligation_id = "obligation-" + digest([claim_id, name, details, VERSION])[:24]
            obligation = {"id": obligation_id, "claim_id": claim_id, "checker": name,
                          "category": category, "payload": deepcopy(details), "source": source,
                          "artifact_ids": sorted(refs), "source_bindings": bindings,
                          "assumptions": local_assumptions, "status": "PROPOSED", "authority": False,
                          "transform": {"name": "scientific-obligation-lowering", "version": VERSION}}
            obligations.append(obligation)
            edges.append({"from": claim_id, "to": obligation_id, "relation": "requires", "source": source,
                          "transform": {"name": "scientific-obligation-lowering", "version": VERSION}})
        for target in refs.values():
            edges.append({"from": "artifact:" + target["id"], "to": claim_id, "relation": "source_binding",
                          "source": source, "artifact_sha256": target["sha256"],
                          "transform": {"name": "scientific-source-binding", "version": VERSION}})

    for artifact in artifacts:
        segments = artifact.get("segments", [])
        automatic_json = 0
        automatic_lean = 0
        for segment in segments:
            text, kind, data = segment.get("text", ""), segment.get("kind", ""), segment.get("data", {})
            if not isinstance(text, str):
                continue
            for line in text.splitlines():
                directive = _directive(line, artifacts)
                if directive:
                    add(artifact, segment, line.strip(), directive["kind"], directive["checker"], directive["payload"], directive["targets"])
                    continue
                # Only a supported controlled grammar may produce typed mathematical IR.
                if re.match(r"\s*(For all|For every|For any|There exists)\b", line, re.I):
                    from pcs.experimental.prover.induction_language import formalize
                    try:
                        result = formalize(line.strip())
                    except (ValueError, RecursionError):
                        result = {"status": "unsupported", "candidates": []}
                    if result.get("status") == "supported" and len(result.get("candidates", [])) == 1:
                        ir = result["candidates"][0]["ir"]
                        add(artifact, segment, line.strip(), "formal", "lean_closed",
                            {"language": "controlled_english", "input_statement": line.strip(), "ir": ir}, interpretation=result)
                    else:
                        add(artifact, segment, line.strip(), "unsupported", "unsupported", {"reason": "Unresolved or ambiguous mathematical meaning"}, interpretation=result)
                elif re.search(r"\b(causes?|proves?|significant|approximately|correlat\w*|hypothesis|confidence interval)\b|≈", line, re.I):
                    add(artifact, segment, line.strip(), "unsupported", "unsupported", {"reason": "Unrestricted scientific prose is an unverified candidate"})
            if kind == "lean_declaration":
                if automatic_lean >= 32:
                    continue
                automatic_lean += 1
                declaration = data.get("declaration", text)
                header = re.sub(r"^(?:\s*@\[[^]\n]{1,128}\])+\s*", "", declaration)
                header = re.sub(r"^\s*(?:(?:private|protected|noncomputable)\s+)+", "", header)
                match = re.match(r"\s*(?:theorem|lemma)\s+([A-Za-z][A-Za-z0-9_]*)\s*:\s*(.*?)(?:\s*:=.*)?$", header, re.S)
                if match:
                    from pcs.experimental.prover.induction_language import parse_lean
                    try:
                        ir = parse_lean(match[2])
                        add(artifact, segment, "Declared theorem type: " + match[2], "formal", "lean_closed",
                            {"language": "lean_type", "input_statement": match[2], "ir": ir,
                             "submitted_proof_ignored": True})
                    except (ValueError, RecursionError):
                        add(artifact, segment, declaration, "unsupported", "unsupported", {"reason": "Lean declaration type outside the bounded typed fragment; submitted code was not executed"})
                else:
                    add(artifact, segment, declaration, "unsupported", "unsupported", {"reason": "Lean declaration requires meaning review; submitted code was not executed"})
            if kind == "sequence" and isinstance(data.get("length"), int):
                add(artifact, segment, f"Extracted sequence {data.get('id')} has length {data['length']}.",
                    "empirical", "sequence_length", {"artifact_id": artifact["id"], "sequence_id": str(data.get("id", "")), "expected": str(data["length"])})
            if kind == "json_value" and isinstance(segment.get("locator", {}).get("json_pointer"), str):
                if automatic_json >= 16:
                    continue
                automatic_json += 1
                pointer = segment["locator"]["json_pointer"]
                add(artifact, segment, f"JSON field {pointer!r} is present.", "computational", "json_field",
                    {"artifact_id": artifact["id"], "pointer": pointer, "expected": "true"})
            if kind == "python_import" and isinstance(data.get("module"), str):
                add(artifact, segment, f"Python source statically imports {data['module']}.", "computational", "python_import",
                    {"artifact_id": artifact["id"], "module": data["module"], "expected": "true"})
        rows = [s for s in segments if s.get("kind") == "csv_row"]
        if rows:
            add(artifact, rows[0], f"CSV data row count is {len(rows)}.", "computational", "csv_rows",
                {"artifact_id": artifact["id"], "expected": str(len(rows))})
        atoms = [s for s in segments if s.get("kind") == "structure_atom"]
        if atoms:
            add(artifact, atoms[0], f"Structure coordinate record count is {len(atoms)}.", "empirical", "coordinate_count",
                {"artifact_id": artifact["id"], "expected": str(len(atoms))})

    # Existing PCS graph helpers are reused only for already supported claim kinds.
    # Research statistical/unsupported kinds remain explicit sidecar nodes.
    from pcs.proof_translation_v06 import _claim_ir_v06, _obligation, _proof_obligation_graph
    candidates = []
    for claim in claims:
        if claim["kind"] not in {"formal", "computational", "empirical", "mixed"}:
            continue
        candidates.append({"id": claim["id"], "source": claim["source"],
            "artifact_ids": sorted({claim["source"]["artifact_id"]}), "selected": False, "formalizable": False,
            "status": "SCIENTIFIC_SIDECAR_PROPOSAL", "typed_claim": {
                "id": claim["id"], "kind": claim["kind"], "statement": claim["statement"],
                "predicate": {"format": "pcs-scientific-sidecar-predicate-v1", "authority": False}},
            "obligations": [_obligation(claim["id"], "SCIENTIFIC_MEANING_REVIEW",
                "Research sidecar checking grants no registered scientific acceptance authority.", blocking=True)]})
    claim_ir = _claim_ir_v06(candidates)
    pcs_graph = _proof_obligation_graph(candidates, inventory={a["id"]: a for a in artifacts}, claim_ir=claim_ir)
    return {"format": FORMAT, "version": VERSION, "authority": False, "truncated": truncated, "claim_limit": 256,
            "artifacts": deepcopy(artifacts), "claims": sorted(claims, key=lambda c: c["id"]),
            "obligations": sorted(obligations, key=lambda o: o["id"]),
            "edges": sorted(edges, key=lambda e: (e["from"], e["to"], e["relation"])),
            "assumptions": sorted(assumptions, key=lambda a: a["id"]),
            "pcs_claim_ir": claim_ir, "pcs_obligation_graph": pcs_graph,
            "sidecar_kinds": ["statistical", "unsupported"],
            "discovery_scope": {"automatic_json_fields_per_artifact": 16, "automatic_lean_declarations_per_artifact": 32, "free_prose": "bounded candidate patterns only; not general scientific understanding"}}
