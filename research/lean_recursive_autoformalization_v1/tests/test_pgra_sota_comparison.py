"""Offline tests for SOTA comparison helpers."""
from __future__ import annotations

from sota_comparison import PUBLISHED_FORML4_GREEDY, lean_similarity


def test_published_table_has_pda_sota():
    sota = PUBLISHED_FORML4_GREEDY["models"]["PDA RFT+Verifier (SOTA in paper)"]
    assert sota["basic"] == 46.28
    assert sota["random"] == 39.38


def test_lean_similarity_norm():
    s = lean_similarity(
        "theorem t (n : Nat) : n = n := by sorry",
        "theorem t (n : ℕ) : n = n := by sorry",
    )
    assert s["exact_norm"] is True
    assert s["token_f1"] == 1.0
