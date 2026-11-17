# Grand Challenge II — Baseline (continuation from PR #217)

**Recorded:** 2026-11-17 (America/New_York)  
**Branch:** `research/pcs-incremental-revalidation-v0`  
**Exact head at audit start:** `6481522cb9951422547ed2368e26c224b558d68f`  
**Draft PR:** https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/217  
**Exclusive namespace:** `research/incremental_certificate_revalidation_v0/`  
**Work after `6481522c` before this campaign:** none (clean worktree aside from untracked `.lean_env.sh`)

## CI at head (do not weaken)

| Check | Result | Interpretation |
|---|---|---|
| `formal-research`, focused-python, portability, lean-learning-loop, cross-pr | success | Research / portability gates green |
| `source-policy` | **failure** | `research.integration_v2.reconcile`: combined tracked file census differs — expected for unadmitted research adding exclusive-namespace files |
| `verified-public-integration` | **failure** | Cascades from source-policy ≠ success |
| Many core/kernel gates | skipped | Not triggered / gated on admission |

**Policy:** Do **not** modify protected manifests, workflows, or weaken these checks. Research remains draft-only outside production authority.

## Verified findings (already established)

| Claim | Evidence |
|---|---|
| `IncrementalAccept` does not embed `FreshValid` | `Semantics.lean` structure fields |
| `incremental_implies_fresh` derives FreshValid from premises | `Soundness.lean`; `#print axioms` → propext, Classical.choice, Quot.sound |
| New-graph invalidation required for new edges | `new_edge_requires_new_graph_invalidation`; Python default `invalidation_graph="new"` |
| Assumption removal breaks guarantees | `tests/test_assumption_counterexamples.py` |
| Cheap Int ops: incremental slower | `results/benchmark_report.json` (~0.45–0.53×) |
| Synthetic expensive checks: trusted sparse reuse fast | `results/expensive_benchmark_report.json` (~64–123×) — **synthetic delay, not Lean kernel** |
| Differential ≠ refinement | `Correspondence.lean`, `REFINEMENT_ANALYSIS.md` |

## Theorem inventory (central)

- Logical: `incremental_implies_fresh`, `reuse_entry_checks`, invalidation sound/complete, `affected_least`, eligibility/non-escalation families
- Conditional correspondence: `executableAcceptImpliesLeanFresh` (assumes decoded IncrementalAccept)

## Implementation gaps (material assurance limits)

1. **No Lean executable incremental algorithm** — acceptance is a witness structure, not `runIncremental … = .ok`.
2. **`ChangesComplete` / `idsCovered` unused in principal case analysis** of `incremental_implies_fresh` — they are *operational* obligations for constructing the per-node premises, not logically needed once those premises exist.
3. **LocalCheck omits evidence** while Python `local_check_node` uses evidence (esp. constants).
4. **Python→Lean refinement unproved**; producer flags can authorize under ValidState trust.
5. **`priorAccepted` boolean** is not independently enforceable against storage forgery without recheck or authenticated transitions.
6. **State commit ordering:** `ValidState` may update before optional fresh comparison.
7. **Performance positive path is synthetic** (sleep), not Lean kernel proof-checking.
8. **idsCovered** forbids insertions; deletions/renames not modeled.
9. **Shared Python op registry** limits independence of fresh vs incremental paths.
10. **source-policy / public integration** red by design until sealed census / admission.

## Known counterexamples (retain)

- Incomplete changes + forged new-key authority → stale accept (when defenses off)
- Prior-graph Affected incompleteness for new edges (set-level; + forgery → false accept)
- Cheap-ops incremental slowdown
- Root-heavy / defense-recheck erases expensive-check speedup

## Assumptions vs expectations

| Item | Status |
|---|---|
| ValidState trust for in-process `prior_accepted` | **Assumption** (restrictive research model) |
| Synthetic delay ≈ Lean kernel cost structure | **Expectation / analogy only** |
| Python establishes IncrementalAccept | **Expectation**; differentially tested, not proved |
| ChangesComplete necessary for *logical* FreshValid once per-node premises hold | **Not necessary** (audit); necessary for *operational* construction |

## Proposed continuation (priority order)

1. Assumption audit + evidence-binding LocalCheck repair  
2. Lean `computeChanges` + `runIncremental` + `incremental_run_sound`  
3. Atomic Python state transitions; independent arithmetic reference  
4. Real Lean 4.28.0 proof-check benchmarks  
5. Multistep history; proof-carrying update transcripts; literature novelty  
6. Manuscript + integration proposal (no production edits)

## Separation

**Verified:** listed theorems and recorded benchmarks/tests.  
**Not verified:** executable refinement, adversarial storage authority, real kernel speedups, novelty vs all prior art.
