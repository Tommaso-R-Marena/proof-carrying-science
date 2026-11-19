"""Offline-ish tests for compile oracle helpers (no Mathlib required for normalize)."""
from __future__ import annotations

from lean_compile_oracle import normalize_candidate


def test_normalize_adds_mathlib_and_sorry():
    code = normalize_candidate("theorem t (n : Nat) : n = n")
    assert "import Mathlib" in code
    assert "theorem t" in code
    assert ":= by sorry" in code


def test_normalize_keeps_existing_sorry():
    code = normalize_candidate("import Mathlib\ntheorem t : True := by sorry")
    assert code.count("import Mathlib") == 1
