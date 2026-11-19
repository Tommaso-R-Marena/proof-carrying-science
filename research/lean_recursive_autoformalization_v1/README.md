# Proof-Gated Recursive Autoformalization (PGRA)

Research-only package joining PCS **proof-gated self-improvement (PGSI)** with
the Lean formalization loop. Capability is an exact finite certificate over a
frozen English→IR corpus under discrete grammar-extension rulebooks.

## Claims

- Exact integer loss and discrete case outcomes on a frozen multi-split corpus
- Monotonic rule enabling gated by preserve / expand / strict loss decrease
- Content-addressed compare-and-swap promotion store with receipt chain
- ≥2 accepted recursive generations with rising certified count on the frozen corpus
- Proof-coupled generations with rising kernel-proved count
- Dual formalize+prove gate that is holdout-blind (fitting only)
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

- **v1:** 8 accepted generations; certified `13→…→28`; final loss `0`
- **v2:** proved `3→5→7→8→10→12` (`rising_proved`)
- **v3:** fitting proved `2→6`; holdout proved nondecreasing; holdout never gates
- 38 pytest cases passed
- Lean gate modules typecheck on Lean 4.28.0 under `lean/`
- V7 ProofGated census remains 38; V23 source census admits this tree

## Reproduction

```bash
export PATH="$HOME/.elan/bin:$HOME/.local/bin:$PATH"
cd /path/to/proof-carrying-science
PYTHONPATH=. python3 -m pytest research/lean_recursive_autoformalization_v1/tests -q
rm -rf research/lean_recursive_autoformalization_v1/results
PYTHONPATH=research/lean_recursive_autoformalization_v1:. python3 -m recursive_loop \
  --output research/lean_recursive_autoformalization_v1/results
cd research/lean_recursive_autoformalization_v1/lean && lake build
```

Artifacts: `tasks.json`, `protocol.json` (`pcs-pgra-protocol-v1`, `frozen=true`),
`summary.json`, `generations.json`, `SHA256.json`.

## PGRA v2 (proof-coupled)

Kernel-proved expansion on a frozen proof-target set: previously proved items
are preserved; each accepted generation adds ≥1 new independently verified
Lean proof under the frozen symbolic budget. Lean gate modules live under
`lean/` (not `formal/PCS/V2/`) so the frozen V7 ProofGated census stays at 38.

## PGRA v3 (dual + holdout-blind)

`dual_recursive_v3.py` requires both formalization and proof gates to accept on
fitting splits only. Holdout metrics are reported after each accept and must
not decrease for proved counts, but never influence acceptance.

Optional lemma harvest builds a checked reusable library from verified fitting
proofs (alpha-deduped) and re-searches under `reuse_priority`; measured
expansions fell `52→18` with proved count preserved. Lean module
`ProofGatedProofCoupled.lean` proves the proof-status gate soundness.

## Continual self-repair

`continual_self_repair.py` is the breakthrough controller: propose → dual-gate →
on REJECT diagnose → repair → re-gate → CAS-promote only on ACCEPT. Illegal
rule removals are rejected and ignored; formalization-only expansions are
repaired by combining a proof-expanding rule. Measured: 3/5 rejects repaired,
adversarial removal blocked, rising fitting proved on accepts.

## External generalization

```bash
PYTHONPATH=. python3 -m research.lean_recursive_autoformalization_v1.external_generalization \
  --output research/lean_recursive_autoformalization_v1/results/external_generalization
```

Axes: sealed lean-learning-v2 formalization + finals prove, OOD paraphrases,
OOD/SVB fail-closed abstention. Measured: 10/10 exact IR, 15/15 OOD supported,
0 SVB false accepts, 5/6 final proves.

## Conflict avoidance

Stay inside `research/lean_recursive_autoformalization_v1/`. Do not edit open-PR
trees (incremental revalidation, causal, claimcheck, jepa, safety,
evidencekernel, etc.) or sealed lean-learning packages.
