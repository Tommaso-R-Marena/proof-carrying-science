"""Frozen multi-split formalization corpus for PGRA v1.

The corpus is assembled and hashed BEFORE any rule fitting. Protocol format is
``pcs-pgra-protocol-v1`` with ``frozen=true`` and sha256 bindings.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from .capability import freeze_expectations
except ImportError:  # flat sys.path research execution
    from capability import freeze_expectations
try:
    from .gate import canonical, digest
except ImportError:  # flat sys.path research execution
    from gate import canonical, digest
try:
    from .grammar_extensions import RULE_IDS
except ImportError:  # flat sys.path research execution
    from grammar_extensions import RULE_IDS

PROTOCOL_FORMAT = "pcs-pgra-protocol-v1"
PACKAGE = "research/lean_recursive_autoformalization_v1"


def _raw_items() -> list[dict[str, Any]]:
    """Hand-authored finite corpus (~24 items) across capability classes."""
    items: list[dict[str, Any]] = []

    # --- Base supported (no extension rules) ---
    base_supported = [
        ("base_nat_eq", "For all natural numbers n, n equals n.", "seed", 0),
        ("base_nat_add", "For all natural numbers n, n + 0 equals n.", "seed", 0),
        (
            "base_prop_implies",
            "For all propositions A and B, if A then B.",
            "validation",
            1,
        ),
        (
            "base_exists",
            "There exists a natural number n such that n equals 0.",
            "holdout",
            2,
        ),
    ]
    for item_id, english, split, generation in base_supported:
        items.append(
            {
                "id": item_id,
                "english": english,
                "target": "supported",
                "class": "base_supported",
                "required_rules": [],
                "split": split,
                "generation_target": generation,
            }
        )

    # --- Extension-required supported (one primary per rule) ---
    extensions = [
        (
            "ext_unique_exists",
            "There exists a unique natural number n such that n equals 0.",
            ["rule_unique_exists"],
            "seed",
            0,
        ),
        (
            "ext_neither_nor",
            "For all propositions A and B, neither A nor B.",
            ["rule_neither_nor"],
            "seed",
            0,
        ),
        (
            "ext_exactly_when",
            "For all propositions A and B, A exactly when B.",
            ["rule_exactly_when"],
            "validation",
            1,
        ),
        (
            "ext_whenever",
            "For all propositions A and B, whenever A, B.",
            ["rule_whenever"],
            "validation",
            1,
        ),
        (
            "ext_plus_times",
            "For all natural numbers n, n plus 0 equals n.",
            ["rule_plus_times_words"],
            "holdout",
            2,
        ),
        (
            "ext_distinct_forall",
            "For all distinct natural numbers a and b, a equals a.",
            ["rule_distinct_forall"],
            "holdout",
            2,
        ),
    ]
    for item_id, english, required, split, generation in extensions:
        items.append(
            {
                "id": item_id,
                "english": english,
                "target": "supported",
                "class": "extension_supported",
                "required_rules": required,
                "split": split,
                "generation_target": generation,
            }
        )

    # --- Abstain negatives (must remain unsupported) ---
    abstain = [
        ("abstain_prove_everything", "Prove everything.", "seed", 0),
        ("abstain_graphs", "Every graph is connected.", "seed", 0),
        ("abstain_reals", "For all real numbers x, x is blue.", "validation", 1),
        ("abstain_poetry", "Beauty is truth, truth beauty.", "validation", 1),
        ("abstain_physics", "Energy is always conserved somehow.", "holdout", 2),
        ("abstain_informal", "Numbers go forever.", "holdout", 2),
    ]
    for item_id, english, split, generation in abstain:
        items.append(
            {
                "id": item_id,
                "english": english,
                "target": "abstain",
                "class": "abstain_negative",
                "required_rules": [],
                "split": split,
                "generation_target": generation,
            }
        )

    # --- Holdout duplicates of each class (extra holdout coverage) ---
    duplicates = [
        (
            "dup_base_nat_eq",
            "For all natural numbers m, m equals m.",
            "supported",
            "base_supported",
            [],
            "holdout",
            2,
        ),
        (
            "dup_ext_unique",
            "There exists a unique natural number k such that k equals 1.",
            "supported",
            "extension_supported",
            ["rule_unique_exists"],
            "holdout",
            2,
        ),
        (
            "dup_ext_neither",
            "For all propositions P and Q, neither P nor Q.",
            "supported",
            "extension_supported",
            ["rule_neither_nor"],
            "holdout",
            2,
        ),
        (
            "dup_abstain",
            "Solve the Riemann hypothesis casually.",
            "abstain",
            "abstain_negative",
            [],
            "holdout",
            2,
        ),
        (
            "dup_ext_plus",
            "For all natural numbers x, x times 1 equals x.",
            "supported",
            "extension_supported",
            ["rule_plus_times_words"],
            "validation",
            1,
        ),
        (
            "dup_ext_whenever",
            "For all propositions P and Q, whenever P, Q.",
            "supported",
            "extension_supported",
            ["rule_whenever"],
            "seed",
            0,
        ),
        (
            "dup_base_iff",
            "For all propositions A and B, A if and only if B.",
            "supported",
            "base_supported",
            [],
            "validation",
            1,
        ),
        (
            "dup_ext_exactly",
            "For all propositions P and Q, P exactly when Q.",
            "supported",
            "extension_supported",
            ["rule_exactly_when"],
            "holdout",
            2,
        ),
    ]
    for item_id, english, target, cls, required, split, generation in duplicates:
        items.append(
            {
                "id": item_id,
                "english": english,
                "target": target,
                "class": cls,
                "required_rules": required,
                "split": split,
                "generation_target": generation,
            }
        )

    return items


def build_frozen_corpus() -> list[dict[str, Any]]:
    """Freeze expectations under the full rule catalog before any fitting."""
    raw = _raw_items()
    if len(raw) < 20:
        raise RuntimeError("corpus too small")
    frozen = freeze_expectations(raw, frozenset(RULE_IDS))
    # Stable order by id for hashing.
    frozen.sort(key=lambda item: item["id"])
    return frozen


def corpus_sha256(corpus: list[dict[str, Any]]) -> str:
    return digest({"format": "pcs-pgra-corpus-v1", "items": corpus})


def slice_for_generation(
    corpus: list[dict[str, Any]], generation: int
) -> list[dict[str, Any]]:
    """Generation-appropriate slice: items with generation_target <= generation,
    always including all previously seen certified candidates' preserve set via
    the full evaluate path when the gate is called on the returned union.
    """
    return [item for item in corpus if int(item.get("generation_target", 0)) <= generation]


def split_corpus(
    corpus: list[dict[str, Any]], split: str
) -> list[dict[str, Any]]:
    return [item for item in corpus if item.get("split") == split]


def write_protocol(output_dir: Path, corpus: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Write tasks.json + protocol.json with frozen=true and sha bindings."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    items = corpus if corpus is not None else build_frozen_corpus()
    tasks_path = output_dir / "tasks.json"
    tasks_payload = {
        "format": "pcs-pgra-tasks-v1",
        "frozen": True,
        "item_count": len(items),
        "items": items,
        "splits": sorted({item["split"] for item in items}),
        "rule_catalog": list(RULE_IDS),
        "pcs_scientific_authority": False,
        "automatic_deployment": False,
    }
    tasks_raw = json.dumps(tasks_payload, indent=2, sort_keys=True) + "\n"
    tasks_path.write_text(tasks_raw)
    tasks_sha = hashlib.sha256(tasks_path.read_bytes()).hexdigest()
    corpus_hash = corpus_sha256(items)

    protocol = {
        "format": PROTOCOL_FORMAT,
        "frozen": True,
        "package": PACKAGE,
        "tasks_sha256": tasks_sha,
        "corpus_sha256": corpus_hash,
        "policy_binding": "pcs-pgra-v1/formalization-rulebook-gate",
        "rule_catalog": list(RULE_IDS),
        "splits": {
            "seed": [i["id"] for i in items if i["split"] == "seed"],
            "validation": [i["id"] for i in items if i["split"] == "validation"],
            "holdout": [i["id"] for i in items if i["split"] == "holdout"],
        },
        "generation_targets": {
            "0": [i["id"] for i in items if i["generation_target"] == 0],
            "1": [i["id"] for i in items if i["generation_target"] == 1],
            "2": [i["id"] for i in items if i["generation_target"] == 2],
        },
        "claims": [
            "Finite certified formalization capability under discrete rulebooks",
            "Monotonic proof-gated rule enabling with exact integer loss",
        ],
        "non_claims": [
            "General English-to-Lean understanding",
            "Production scientific authority",
            "Automatic deployment of rulebooks or models",
        ],
        "pcs_scientific_authority": False,
        "automatic_deployment": False,
    }
    protocol_path = output_dir / "protocol.json"
    protocol_path.write_text(json.dumps(protocol, indent=2, sort_keys=True) + "\n")
    return protocol


def load_tasks(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(Path(path).read_text())
    if raw.get("format") != "pcs-pgra-tasks-v1" or raw.get("frozen") is not True:
        raise ValueError("tasks.json is not a frozen pcs-pgra-tasks-v1 artifact")
    if raw.get("pcs_scientific_authority") is not False:
        raise ValueError("tampered tasks: pcs_scientific_authority")
    if raw.get("automatic_deployment") is not False:
        raise ValueError("tampered tasks: automatic_deployment")
    items = raw["items"]
    if type(items) is not list or not items:
        raise ValueError("empty or invalid items")
    return items


def verify_tasks_binding(path: Path, expected_sha256: str) -> list[dict[str, Any]]:
    data = Path(path).read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected_sha256:
        raise ValueError("corpus/tasks tampering detected: sha256 mismatch")
    return load_tasks(path)


__all__ = [
    "PROTOCOL_FORMAT",
    "build_frozen_corpus",
    "corpus_sha256",
    "load_tasks",
    "slice_for_generation",
    "split_corpus",
    "verify_tasks_binding",
    "write_protocol",
]
