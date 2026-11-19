# PGRA execution report

**Date:** 2026-11-17 (America/New_York)  
**Branch:** `feature/lean-recursive-autoformalization-v1-3d8c`  
**Status:** research-only; not production PCS authority

## Result

Proof-gated recursive autoformalization closed the documented gap between
PGSI (exact finite acceptance gates on toy ReLU models) and the Lean
formalization loop (real feedback without measured promotion).

### v1 — formalization capability

On a frozen **28-item** authored corpus (8 grammar rules), the recursive
rulebook loop accepted **8 generations** with certified capability rising

`13 → 15 → 17 → 19 → 21 → 23 → 24 → 26 → 28`

and exact loss falling to **0**. Automatic deployment remained false.

### v2 — proof-coupled

Kernel-proved expansion on an expanded frozen proof-target set (12 ids):

`3 → 5 → 7 → 8 → 10 → 12`

across **5** accepted generations (`rising_proved=true`). New rules
`rule_zero_word` and `rule_is_equal_to` unlock additional Nat identities that
the symbolic LeanEnvironment verifies under the frozen budget.

### v3 — dual formalize+prove with holdout blind

Acceptance requires **both** the formalization gate and the proof-coupled gate
on the fitting splits (`seed` ∪ `validation`) only. Holdout is report-only.

Fitting certified `8 → 9 → 10 → 11 → 12`; fitting proved `2 → 3 → 4 → 5 → 6`
across **4** accepted generations. Holdout proved `1 → 2 → 3 → 4 → 5`
(non-decreasing; never consulted by the gate).

Lemma harvest (alpha-deduped checked library + `reuse_priority`): fitting
expansions **`52 → 18`** with proved count preserved (`6→6`).

Lean `ProofGatedProofCoupled.lean` specializes the formalization gate to
proved/unproved certificates with `accept_sound` and strict-loss theorems.

### Continual self-repair (breakthrough)

`continual_self_repair.py` closes the one-shot gap: on REJECT it diagnoses,
repairs, re-gates, and CAS-promotes only on ACCEPT (HEAD unchanged otherwise).

Measured:
- **4 accepts**, **3 repair accepts**, **1 adversarial removal rejected**
- self-repair rate **0.6** (`repairs_succeeded / rejects_seen`)
- rising fitting proved on accept events; fitting form/proof loss → **0**
- Repair strategy that recovered partial failures: `combine_with_proof_expander`

## What was built

| Artifact | Role |
| --- | --- |
| `grammar_extensions.py` | Eight discrete fail-closed English→IR extensions |
| `capability.py` | Exact case outcomes + integer loss |
| `gate.py` | Preserve / expand / loss↓ / monotonic rules |
| `store.py` | Content-addressed CAS promotion + receipts |
| `recursive_loop.py` | Multi-generation proposer + gate + store |
| `proof_coupled_v2.py` | Kernel-proof preserve/expand/loss↓ loop |
| `dual_recursive_v3.py` | Joint formalize+prove gate; holdout-blind |
| `ranker_cycle.py` | FormalizationRanker gated candidate (never promoted) |
| `formal_bridge.py` | Lean wire CLI against research `lean/` package |
| `research/.../lean/PCS/V2/ProofGatedFormalization*.lean` | Lean soundness of the abstract gate |

## Measured

- **Pytest:** 38 passed (including dual-v3 + Lean bridge)
- **v1 recursive loop:** 8 accepted generations; final loss 0; all 8 catalog rules enabled
- **v2 proof-coupled:** proved `3→12`; rising
- **v3 dual:** fitting proved `2→6`; holdout proved nondecreasing; rising fitting certified
- **Lean:** research package typechecks under Lean 4.28.0; wire CLI returns ACCEPT
- **Source census:** V23 whole-tree reconcile `--require-committed` passes locally
- **V7 census:** 38 ProofGated modules restored

## Non-claims

- Not unrestricted English equivalence
- Not neural superiority over symbolic proof search
- Not PCS scientific authority or automatic deployment
- Holdout is authored and public; the gate is holdout-blind, not a private semantic holdout
- Does not conflict with open incremental-revalidation / causal / JEPA / safety PRs

## Reproduce

```bash
export PATH="$HOME/.elan/bin:$HOME/.local/bin:$PATH"
cd proof-carrying-science
PYTHONPATH=. python3 -m pytest research/lean_recursive_autoformalization_v1/tests -q
rm -rf research/lean_recursive_autoformalization_v1/results
PYTHONPATH=research/lean_recursive_autoformalization_v1:. python3 -m recursive_loop \
  --output research/lean_recursive_autoformalization_v1/results
PYTHONPATH=. python3 -m research.lean_recursive_autoformalization_v1.proof_coupled_v2 \
  --output research/lean_recursive_autoformalization_v1/results/proof_coupled_v2
PYTHONPATH=. python3 -m research.lean_recursive_autoformalization_v1.dual_recursive_v3 \
  --output research/lean_recursive_autoformalization_v1/results/dual_v3 --no-harvest
cd research/lean_recursive_autoformalization_v1/lean && lake build
```

## Source census successor

Reviewed combined-source contract successor
`docs/integration/2026-11-05/RECONCILIATION_V23.json` admits the PGRA research
tree while freezing V22/V21/V20 predecessors unchanged. V7 module discovery
remains 38.
