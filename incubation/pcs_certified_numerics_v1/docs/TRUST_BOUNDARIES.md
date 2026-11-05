# Trust boundaries

| Component | Trust |
|---|---|
| Lean theorems `mem_neg/add/sub/mul/...` | Trusted after `lake build` |
| Python interval mirror | Differential-tested; not a Lean proof |
| Python certificate checker | Independent recomputation; intended Lean port |
| Generators / BnB search / heuristics | Untrusted |
| `math.exp` / NumPy | Diagnostics only |
| Mathlib | Standard classical foundation |

A buggy generator must not force acceptance of a false claim under the checker’s rules.
