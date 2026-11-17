# Lean ↔ Python correspondence (Phase II)

## Mapping

| Concern | Lean | Python | Bound |
|---|---|---|---|
| Step citations | `StepSpec` + `checkCertificate` | `check_certificate_v1.py` | Structural; differential tests |
| Soundness | `checkCertificate_sound` → `Derives` | N/A (tested) | Kernel-checked |
| Meet | `Authority.meet` commutative | `authority.meet` | Enumerated agree |
| math_established | `hyp_not_math_established` | Hyp ⇒ False | Proved / tested |
| Legacy forged JSON | N/A | Rejected by v1 | Regressions A/B/C |

## Levels achieved

1. Differential / mutation testing on schema v1.  
2. Small exhaustive meet table (6×6 authorities).  
3. **Not** claimed: CPython source refinement; serialized JSON parser correctness in Lean.

## Open trust boundary

JSON parsing, resource limits, and OS I/O remain outside Lean. Independent checker must stay import-free of the reference evaluator.
