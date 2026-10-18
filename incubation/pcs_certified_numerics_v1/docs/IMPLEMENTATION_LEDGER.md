# Implementation ledger

Statuses: `IMPLEMENTED_AND_VERIFIED` | `IMPLEMENTED_TESTED` | `PARTIALLY_IMPLEMENTED` | `EXPERIMENTAL` | `BLOCKED` | `NOT_STARTED` | `REFUTED` | `UNSUPPORTED`

| Requirement area | Status | Evidence |
|---|---|---|
| Private repo `pcs-certified-numerics` | `BLOCKED` | GitHub PAT lacks `repo` create; fallback worktree used |
| Isolation namespace only | `IMPLEMENTED_TESTED` | `scripts/noninterference_check.sh` |
| Lean 4.28 + Mathlib pin | `IMPLEMENTED_TESTED` | `lean-toolchain`, `lakefile.toml`, `lake build` OK |
| Rational interval arithmetic (Python) | `IMPLEMENTED_TESTED` | `python/certnum/interval/`, unit+hypothesis tests |
| Rational interval soundness (Lean) | `IMPLEMENTED_AND_VERIFIED` | `mem_neg/add/sub/mul`, hull, inter; `lake build` |
| Typed expression language | `IMPLEMENTED_TESTED` | AST, parser, exact+interval eval |
| Mean-value enclosure | `IMPLEMENTED_TESTED` | `mean_value_enclosure` + benchmarks |
| Forward AD | `IMPLEMENTED_TESTED` | `ad/forward.py` |
| Root isolation | `IMPLEMENTED_TESTED` | existence/uniqueness/exclusion statuses |
| Global BnB optimization | `IMPLEMENTED_TESTED` | coverage leaves + L/U bounds |
| Validated linear scalar ODE | `IMPLEMENTED_TESTED` | certified `exp` series + exact solution form |
| Interval Euler (general f) | `PARTIALLY_IMPLEMENTED` | Euler image only; remainder flagged |
| Linear algebra residuals / Gershgorin | `IMPLEMENTED_TESTED` | `linalg/basic.py` |
| Finite Markov certificates | `IMPLEMENTED_TESTED` | exact rational stochastic matrices |
| Finite thermo Z bounds | `IMPLEMENTED_TESTED` | enum + energy bins; independent of FoldBounds |
| Certificate format + Python checker | `IMPLEMENTED_TESTED` | adversarial rejection tests |
| Lean certificate checker | `PARTIALLY_IMPLEMENTED` | soundness core ready; IR checker TBD |
| Transcendental enclosures (exp) | `IMPLEMENTED_TESTED` | Taylor + geometric tail on ℚ |
| log/sin/cos | `NOT_STARTED` | |
| Taylor models (general) | `NOT_STARTED` | |
| ML heuristics | `NOT_STARTED` | |
| Native/GPU acceleration | `UNSUPPORTED` | no measured need yet |
| PCS production integration | `NOT_STARTED` | proposal-only |

## Novelty discipline

No “world first” claims. Mean-value forms, interval Newton ideas, and energy-bin Z bounds are classical; this project’s contribution is a **standalone proof-carrying numerics stack** with Lean-checked interval soundness and independent checkers.
