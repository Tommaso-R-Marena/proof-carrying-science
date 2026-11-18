# PGRA v1 execution report

**Date:** 2026-11-17 (America/New_York)  
**Branch:** `feature/lean-recursive-autoformalization-v1-3d8c`  
**Status:** research-only; not production PCS authority

## Result

Proof-gated recursive autoformalization closed the documented gap between
PGSI (exact finite acceptance gates on toy ReLU models) and the Lean
formalization loop (real feedback without measured promotion).

On a frozen 24-item authored corpus, the recursive rulebook loop accepted
**6 generations** with certified capability rising

`13 → 15 → 17 → 19 → 21 → 23 → 24`

and exact loss falling to **0**. Automatic deployment remained false.

## What was built

| Artifact | Role |
| --- | --- |
| `grammar_extensions.py` | Six discrete fail-closed English→IR extensions |
| `capability.py` | Exact case outcomes + integer loss |
| `gate.py` | Preserve / expand / loss↓ / monotonic rules |
| `store.py` | Content-addressed CAS promotion + receipts |
| `recursive_loop.py` | Multi-generation proposer + gate + store |
| `ranker_cycle.py` | FormalizationRanker gated candidate (never promoted) |
| `research/.../lean/PCS/V2/ProofGatedFormalization.lean` | Lean soundness of the abstract gate |
| `research/.../lean/PCS/V2/ProofGatedFormalizationArtifacts.lean` | Wire-format Lean artifact checker |

## Measured

- **Pytest:** 25 passed
- **Recursive loop:** 6 accepted generations; final loss 0; all 6 catalog rules enabled
- **Ranker cycle:** discrete accuracy 1 → 6 on frozen labels; candidate not promoted
- **Lean:** `ProofGatedFormalization.lean` and `ProofGatedFormalizationArtifacts.lean` typecheck under Lean 4.28.0
- **Adversarial:** rule removal, no-ops, and abstention regressions rejected

## Non-claims

- Not unrestricted English equivalence
- Not neural superiority over symbolic proof search
- Not PCS scientific authority or automatic deployment
- Public authored tasks are not a private blind semantic holdout
- Does not conflict with open incremental-revalidation / causal / JEPA / safety PRs

## Reproduce

```bash
export PATH="$HOME/.elan/bin:$HOME/.local/bin:$PATH"
cd proof-carrying-science
PYTHONPATH=. python3 -m pytest research/lean_recursive_autoformalization_v1/tests -q
rm -rf research/lean_recursive_autoformalization_v1/results
PYTHONPATH=research/lean_recursive_autoformalization_v1:. python3 -m recursive_loop \
  --output research/lean_recursive_autoformalization_v1/results
cd formal && lake env lean PCS/V2/ProofGatedFormalization.lean
```


## PGRA v2 follow-up

- Relocated Lean gate out of `formal/PCS/V2/` → restores frozen V7 census (38 modules); `check_profile()` passes locally
- Added proof-coupled recursive loop: preserve proved set, expand ≥1 kernel proof, loss↓
- See `results/proof_coupled_v2/proof_coupled_summary.json`
