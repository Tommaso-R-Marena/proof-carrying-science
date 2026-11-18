# Lean ↔ Python correspondence (Phase III)

## Well-formedness contract

| Rule | Lean | Python |
|---|---|---|
| Unique premise IDs | `uniquePremiseIds`; reject in `checkCertificate` | duplicate premise id → CheckError |
| schema_version | N/A (structured) | must be int `1` (bool rejected) |
| mathEstablished | always false on accept (`checkCertificate_mathEstablished_false`) | Hyp false; claim True rejected |
| andI authority | `Authority.meet` | `meet` (rank+tie) |

## Finite coverage (Python)

- Meet: all 6×6 authority pairs (commutative).  
- Hyp: 2 atoms × 6 authorities.  
- AndI: 6×6 authority pairs.  
- Belnap ∧: all 16 cells.

**Not claimed:** CPython ≡ Lean source refinement; JSON parser proved in Lean.

## Duplicate-ID finding (resolved)

Pre-Phase-III Lean `findPremise` took the first match and could accept duplicate-id contexts.  
Now both sides reject non-unique premise ids before step checking.
