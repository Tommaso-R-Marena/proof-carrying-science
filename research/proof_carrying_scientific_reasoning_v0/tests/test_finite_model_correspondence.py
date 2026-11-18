"""Exhaustive finite-model checks for meet (6×6) and short certificates.

Coverage bound: authorities = 6 labels; formulas = atoms {0,1} with optional and;
derivations = hyp and single andI only. Not a proof of Python≡Lean source equivalence.
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "independent_checker"))

from scientific_reasoning.authority import meet
from scientific_reasoning.syntax import Authority
import check_certificate_v1 as v1

AUTHS = list(Authority)


def test_meet_6x6_commutative_and_rank_min():
    for a, b in itertools.product(AUTHS, repeat=2):
        m1 = meet(a, b)
        m2 = meet(b, a)
        assert m1 == m2
        key = lambda x: (v1.RANK[x.value], v1.TIE_ORDER[x.value])
        assert m1 == (a if key(a) <= key(b) else b)


def test_all_single_hyp_certs():
    # 2 atoms × 6 authorities = 12 accepted hyps; math_established always false
    n = 0
    for atom_id, auth in itertools.product((0, 1), AUTHS):
        cert = {
            "schema_version": 1,
            "premises": [
                {"id": 0, "formula": ["atom", atom_id], "declared_authority": auth.value}
            ],
            "steps": [{"id": 0, "rule": "hyp", "premise_id": 0}],
            "conclusion_step": 0,
            "conclusion": ["atom", atom_id],
        }
        j = v1.check(cert)
        assert j.math_established is False
        assert j.declared_authority == auth.value
        n += 1
    assert n == 12


def test_andI_authority_is_meet_exhaustive_pairs():
    # Bound: two premises, authorities from full set; 6×6 = 36
    for a, b in itertools.product(AUTHS, repeat=2):
        cert = {
            "schema_version": 1,
            "premises": [
                {"id": 0, "formula": ["atom", 0], "declared_authority": a.value},
                {"id": 1, "formula": ["atom", 1], "declared_authority": b.value},
            ],
            "steps": [
                {"id": 0, "rule": "hyp", "premise_id": 0},
                {"id": 1, "rule": "hyp", "premise_id": 1},
                {"id": 2, "rule": "andI", "left": 0, "right": 1},
            ],
            "conclusion_step": 2,
        }
        j = v1.check(cert)
        assert j.declared_authority == meet(a, b).value
        assert j.math_established is False
        assert j.formula == ["and", ["atom", 0], ["atom", 1]]
