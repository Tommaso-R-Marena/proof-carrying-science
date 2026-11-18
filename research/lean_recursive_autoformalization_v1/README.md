# Proof-Gated Recursive Autoformalization (PGRA) v1

Research-only package joining PCS **proof-gated self-improvement (PGSI)** with
the Lean formalization loop. Capability is an exact finite certificate over a
frozen English→IR corpus under discrete grammar-extension rulebooks.

## Claims

- Exact integer loss and discrete case outcomes on a frozen multi-split corpus
- Monotonic rule enabling gated by preserve / expand / strict loss decrease
- Content-addressed compare-and-swap promotion store with receipt chain
- ≥2 accepted recursive generations with rising certified count on the frozen corpus
- Adversarial rule removal, abstention regression, and fake expansion rejected
- Optional FormalizationRanker cycle using the same gate idea (never auto-promotes)

## Non-claims

- Not production scientific authority (`pcs_scientific_authority=false`)
- Not automatic deployment (`automatic_deployment=false`)
- Not general English understanding — unrestricted English remains unproved
- Does not modify sealed `research/lean-learning-v1` or `lean-learning-v2`
- Does not weaken `pcs/experimental/prover/promotion.py`, `feedback_cycle.py`,
  `language.py`, or `formalization_model.py`

## Relation to PGSI and lean-learning-v2

| Component | PGSI | PGRA |
| --- | --- | --- |
| Domain | Finite ReLU regression | Finite formalization rulebooks |
| Gate | preserve / expand / loss↓ | same four checks (+ no rule removal) |
| Store | CAS + Lean file oracle | CAS + Python reference gate |
| Artifact | weight/bias model | sorted rule id set |

Lean-learning-v2 sealed formalization artifacts remain untouched. A thin
discoverability re-export lives at
`pcs/experimental/prover/recursive_autoformalization_v1.py` and only imports
this research package.

## Measured (this branch)

- 6 accepted generations; certified counts `13→15→17→19→21→23→24`; final loss `0`
- 25 pytest cases passed
- Ranker discrete accuracy `1→6` on frozen labels (candidate not promoted)
- End-to-end: extension English (`plus`, `distinct`) formalizes and symbolically proves under Lean
- Lean gate modules typecheck on Lean 4.28.0

## Reproduction

```bash
export PATH="$HOME/.elan/bin:$HOME/.local/bin:$PATH"
cd /path/to/proof-carrying-science
PYTHONPATH=. python3 -m pytest research/lean_recursive_autoformalization_v1/tests -q
rm -rf research/lean_recursive_autoformalization_v1/results
PYTHONPATH=research/lean_recursive_autoformalization_v1:. python3 -m recursive_loop \
  --output research/lean_recursive_autoformalization_v1/results
cd formal && lake env lean PCS/V2/ProofGatedFormalization.lean
```

Artifacts: `tasks.json`, `protocol.json` (`pcs-pgra-protocol-v1`, `frozen=true`),
`summary.json`, `generations.json`, `SHA256.json`.


## PGRA v2 (proof-coupled)

Kernel-proved expansion on a frozen proof-target set: previously proved items
are preserved; each accepted generation adds ≥1 new independently verified
Lean proof under the frozen symbolic budget. Lean gate modules live under
`lean/` (not `formal/PCS/V2/`) so the frozen V7 ProofGated census stays at 38.

## Conflict avoidance

Stay inside `research/lean_recursive_autoformalization_v1/`. Do not edit open-PR
trees (incremental revalidation, causal, claimcheck, jepa, safety,
evidencekernel, etc.) or sealed lean-learning packages.
