"""Load independently annotated scientific references without consulting PCS output.

The explicit final-split opt-in is an evaluation protocol aid, not a security
boundary: the raw reference files remain reviewable in this repository.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


REFERENCE_ROOT = Path(__file__).with_name("reference")
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_STATUSES = frozenset({"supported", "contradicted", "insufficient_evidence"})
ANNOTATION_KINDS = frozenset({
    "scalar_parameter", "initial_condition", "rate_law", "mass_balance",
    "dimension", "optimization_result", "convergence_condition",
    "applicability", "unsupported_counterclaim", "numerical_result",
    "equation", "assumption",
})


def _annotation_file(split: str) -> Path:
    if split not in {"development", "final"}:
        raise ValueError("split must be 'development' or 'final'")
    return REFERENCE_ROOT / f"{split}.json"


def _validate_annotation(annotation: dict[str, Any], split: str) -> None:
    required = {"id", "project_id", "split", "kind", "statement", "source",
                "typed_expectation", "expected_status", "conditions", "units",
                "assumptions", "label_provenance"}
    missing = required - annotation.keys()
    if missing:
        raise ValueError(f"annotation missing fields: {sorted(missing)}")
    if annotation["split"] != split:
        raise ValueError(f"annotation {annotation['id']} belongs to another split")
    if annotation["kind"] not in ANNOTATION_KINDS:
        raise ValueError(f"unknown annotation kind: {annotation['kind']}")
    if annotation["expected_status"] not in EXPECTED_STATUSES:
        raise ValueError(f"unknown annotation status: {annotation['expected_status']}")
    source = annotation["source"]
    if not {"path", "sha256", "locator", "quote"} <= source.keys():
        raise ValueError("source requires path, sha256, locator, and quote")
    if not source["quote"] or not source["locator"]:
        raise ValueError("empty source quote or locator")
    if len(source["sha256"]) != 64:
        raise ValueError("source sha256 must contain 64 hexadecimal characters")
    try:
        int(source["sha256"], 16)
    except ValueError as exc:
        raise ValueError("invalid source sha256") from exc
    for evidence in annotation.get("corroborating_sources", []):
        if not {"path", "sha256", "locator", "quote"} <= evidence.keys():
            raise ValueError("corroborating evidence requires path, sha256, locator, and quote")
    if annotation["label_provenance"].get("reviewer_role") != "independent_internal_review":
        raise ValueError("reference annotations must identify the internal review role")


def load_reference(split: str, *, allow_final: bool = False,
                   verify_sources: bool = True) -> list[dict[str, Any]]:
    """Return manual annotations, requiring explicit permission for final labels.

    ``allow_final`` records the caller's evaluation-policy decision. The caller
    is responsible for freezing the evaluated components before setting it.
    Source verification compares the immutable original's bytes and exact quote;
    it does not run an extractor, interpret an equation, or recompute a label.
    """
    path = _annotation_file(split)
    if split == "final" and not allow_final:
        raise PermissionError("final references require allow_final=True after component freeze")
    raw_labels = path.read_bytes()
    manifest = json.loads((REFERENCE_ROOT / "annotation_freeze.json").read_text(encoding="utf-8"))
    if hashlib.sha256(raw_labels).hexdigest() != manifest["label_files"][split]["sha256"]:
        raise ValueError(f"frozen annotation hash mismatch for {split}")
    document = json.loads(raw_labels)
    if document.get("schema_version") != "manual-reference-v1":
        raise ValueError("unsupported reference schema")
    annotations = document["annotations"]
    seen: set[str] = set()
    for annotation in annotations:
        _validate_annotation(annotation, split)
        if annotation["id"] in seen:
            raise ValueError(f"duplicate annotation id: {annotation['id']}")
        seen.add(annotation["id"])
    if verify_sources:
        verify_reference_sources(annotations)
    return annotations


def verify_reference_sources(annotations: list[dict[str, Any]]) -> dict[str, int]:
    """Check evidence hashes and exact anchors against original source files."""
    cache: dict[str, tuple[str, str]] = {}
    for annotation in annotations:
        for source in [annotation["source"], *annotation.get("corroborating_sources", [])]:
            relative = source["path"]
            path = (REPOSITORY_ROOT / relative).resolve()
            if not path.is_relative_to(REPOSITORY_ROOT):
                raise ValueError("reference source escapes repository")
            if relative not in cache:
                raw = path.read_bytes()
                cache[relative] = (hashlib.sha256(raw).hexdigest(), raw.decode("utf-8"))
            digest, text = cache[relative]
            if digest != source["sha256"]:
                raise ValueError(f"source hash mismatch for {relative}")
            if source["quote"] not in text:
                raise ValueError(f"source quote absent for annotation {annotation['id']}")
    return {"annotations_checked": len(annotations), "source_files_checked": len(cache)}
