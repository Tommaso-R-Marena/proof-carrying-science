# Lean ↔ Python correspondence

| Lean | Python | Status |
|---|---|---|
| Formula / Authority / Context | `syntax.py` | Structural match (differential) |
| Derives Hyp/AndI/AndE | `evaluator.py` | Same rules; not refinement-proved |
| Authority.meet | `authority.meet` | Rank table matched |
| Certificate.valid | independent checker + build_certificate | Differential / rule replay |
| Context.retract | `retract_context` | Differential |

**Level achieved:** differential testing + adversarial certificate checks.  
**Not claimed:** source-level refinement of CPython to Lean.
