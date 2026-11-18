"""Discoverability re-export for Proof-Gated Recursive Autoformalization v1.

Imports the research package only. Does not alter sealed promotion.py,
feedback_cycle.py, language.py, or formalization_model.py behavior.
"""
from __future__ import annotations

from research.lean_recursive_autoformalization_v1 import (
    AUTOMATIC_DEPLOYMENT,
    PCS_AUTHORITY,
    PCS_SCIENTIFIC_AUTHORITY,
)
from research.lean_recursive_autoformalization_v1.capability import (
    RULE_CATALOG,
    RULE_IDS,
    evaluate_case,
    evaluate_corpus,
    formalize_with_rules,
)
from research.lean_recursive_autoformalization_v1.corpus import build_frozen_corpus
from research.lean_recursive_autoformalization_v1.gate import (
    POLICY_HASH,
    Decision,
    accept,
    check,
)
from research.lean_recursive_autoformalization_v1.recursive_loop import automatic_search
from research.lean_recursive_autoformalization_v1.ranker_cycle import run_ranker_cycle

__all__ = [
    "AUTOMATIC_DEPLOYMENT",
    "PCS_AUTHORITY",
    "PCS_SCIENTIFIC_AUTHORITY",
    "RULE_CATALOG",
    "RULE_IDS",
    "POLICY_HASH",
    "Decision",
    "accept",
    "check",
    "evaluate_case",
    "evaluate_corpus",
    "formalize_with_rules",
    "build_frozen_corpus",
    "automatic_search",
    "run_ranker_cycle",
]
