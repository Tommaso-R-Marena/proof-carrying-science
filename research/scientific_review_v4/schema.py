"""Reviewable v4 structural/source checks, separate from scientific correctness."""
from __future__ import annotations

import hashlib

from .semantics import CATEGORIES, VERSION


def _source_errors(source, artifact_by_id, raw_artifacts, *, allow_empty=False, inventory=None):
    if not isinstance(source, dict):
        return ["missing source object"]
    errors = []
    artifact = artifact_by_id.get(source.get("artifact_id"))
    if artifact is None or source.get("path") != artifact.get("path") or source.get("sha256") != artifact.get("sha256"):
        errors.append("source artifact binding")
    if source.get('transformation',{}).get('kind')=='adapter_extracted_text':
        from .grounding import bound_source
        t=source['transformation'];quote=source.get('quote');a=t.get('extracted_byte_start');b=t.get('extracted_byte_end')
        if type(a) is not int or type(b) is not int or not isinstance(quote,str) or a<0 or b<a or (not allow_empty and a==b):return errors+['invalid extracted-text span']
        if len(quote.encode('utf-8'))!=b-a:errors.append('extracted quote length')
        if raw_artifacts is not None and not bound_source(source,raw_artifacts,inventory):errors.append('independent extracted-text grounding')
        return errors
    start, end, quote = source.get("byte_start"), source.get("byte_end"), source.get("quote")
    if type(start) is not int or type(end) is not int or not isinstance(quote, str):
        return errors + ["source span types"]
    if start < 0 or end < start or (not allow_empty and (not quote or end <= start)):
        errors.append("source span must be nonempty")
    if len(quote.encode("utf-8")) != end - start:
        errors.append("source quote byte length")
    if artifact is not None and end > artifact.get("size", -1):
        errors.append("source span exceeds artifact")
    if raw_artifacts is not None:
        raw = raw_artifacts.get(source.get("path"))
        if type(raw) is not bytes or hashlib.sha256(raw).hexdigest() != source.get("sha256") or raw[start:end] != quote.encode("utf-8"):
            errors.append("source original byte grounding")
    return errors


def validate_interpretation(value, artifacts=None, *, inventory=None):
    """Return explicit errors, never an authority grant or scientific verdict.

    Supplying original ``dict[path,bytes]`` also verifies source hashes and byte
    spans. Without bytes, validation checks structural consistency only.
    """
    errors = []
    if not isinstance(value, dict):
        return {"valid": False, "errors": ["interpretation must be an object"], "authority": False}
    if value.get("schema_version") != VERSION:
        errors.append("schema_version")
    if value.get("authority") is not False:
        errors.append("top-level authority must be false")
    for category in CATEGORIES:
        if not isinstance(value.get(category), list):
            errors.append(category + " must be a list")
    if errors:
        return {"valid": False, "errors": errors, "authority": False}
    for category in CATEGORIES:
        if any(not isinstance(row, dict) for row in value[category]):
            errors.append(category + ": records must be objects")
    if errors:
        return {"valid": False, "errors": errors, "authority": False}
    identifiers = [row.get("id") for category in CATEGORIES for row in value[category]]
    if any(not isinstance(identifier, str) for identifier in identifiers):
        errors.append("record IDs must be unique strings")
        return {"valid": False, "errors": errors, "authority": False}
    if len(identifiers) != len(set(identifiers)):
        errors.append("record IDs must be unique strings")
    for artifact in value["artifacts"]:
        if type(artifact.get("size")) is not int or artifact["size"] < 0 or not isinstance(artifact.get("path"), str) or not isinstance(artifact.get("sha256"), str):
            errors.append("invalid artifact metadata")
    if errors:
        return {"valid": False, "errors": errors, "authority": False}
    artifact_by_id = {row.get("id"): row for row in value["artifacts"]}
    claims = {row.get("id") for row in value["claims"]}
    symbols = {row.get("id") for row in value["symbols"]}
    for category in CATEGORIES:
        for index, row in enumerate(value[category]):
            label = f"{category}[{index}]"
            if not isinstance(row, dict):
                errors.append(label + ": record must be an object")
                continue
            if not isinstance(row.get("origin_id"), str) or row.get("origin_id") == row.get("id"):
                errors.append(label + ": original ID missing or not reidentified")
            if category == "artifacts":
                raw = artifacts.get(row.get("path")) if artifacts is not None else None
                if artifacts is not None and (type(raw) is not bytes or len(raw) != row.get("size") or hashlib.sha256(raw).hexdigest() != row.get("sha256")):
                    errors.append(label + ": artifact byte identity")
                continue
            if row.get("authority") is not False:
                errors.append(label + ": authority must be false")
            errors.extend(label + ": " + error for error in _source_errors(row.get("source"), artifact_by_id, artifacts, allow_empty=category == "unresolved",inventory=inventory))
            for key in ("claim_id", "from_claim"):
                if key in row and row[key] not in claims:
                    errors.append(label + ": dangling " + key)
            for key in ("symbol_id", "to_symbol"):
                if key in row and row[key] not in symbols:
                    errors.append(label + ": dangling " + key)
            for binding in row.get("symbol_bindings", []):
                if "symbol_id" in binding and binding["symbol_id"] not in symbols:
                    errors.append(label + ": dangling symbol binding")
            if category == "claims":
                if row.get("entity") != row.get("subject"):
                    errors.append(label + ": subject/entity mismatch")
                for field, evidence in row.get("field_evidence", {}).items():
                    errors.extend(label + ".field_evidence." + field + ": " + error for error in _source_errors(evidence, artifact_by_id, artifacts,inventory=inventory))
                if not any(o.get("claim_id") == row.get("id") and o.get("kind") == "scientific_meaning_review" and o.get("status") == "OPEN" for o in value["obligations"]):
                    errors.append(label + ": open scientific meaning obligation missing")
    return {"valid": not errors, "errors": errors, "authority": False,
            "scientific_correctness": "NOT_ESTABLISHED", "source_bytes_checked": artifacts is not None}


validate = validate_interpretation
