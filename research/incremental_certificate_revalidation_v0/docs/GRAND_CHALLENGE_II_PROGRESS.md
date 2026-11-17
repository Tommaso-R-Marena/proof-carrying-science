# Grand Challenge II — Progress

**Branch:** `research/pcs-incremental-revalidation-v0`  
**Draft PR:** #217  
**Tip:** see `results/HEAD_COMMIT.txt`  
**Updated:** 2026-11-17 (America/New_York)

## Completed this campaign cycle

### Milestone 1 — Mathematical specification strengthened
- [x] `docs/GRAND_CHALLENGE_II_BASELINE.md` (start head `6481522c`; CI census failure documented)
- [x] `docs/ASSUMPTION_AUDIT_V2.md` — logical vs operational; ChangesComplete unused in logical case split
- [x] LocalCheck evidence-bound (`Op→Ver→Pol→Evidence→deps→payload→out`)
- [x] `LogicalAccept` separated from operational `IncrementalAccept`
- [x] `logical_implies_fresh` / evidence-aware `reuse_entry_checks`

### Milestone 2 — Verified Lean algorithm (substantive, bridge pending)
- [x] `Algorithm.lean`: `computeChanges`, proved `computeChanges_complete`, `computeChanges_seeds_new`
- [x] Executable `affectedClosure` + step soundness (`collectDependents` ⇒ `dependsOn`)
- [x] Concrete `runIncremental` / `runNodes` / `stepNode` (computable)
- [x] `runIncremental_changes_complete`, `incremental_run_sound` (= LogicalAccept ⇒ FreshValid)
- [ ] Full bridge: `runIncremental` accepted ⇒ constructed `LogicalAccept` (in progress)

No `sorry` / `admit` / custom axioms. Axiom audit: propext / Classical.choice / Quot.sound only.

### Executable / systems
- [x] Python `compute_changes` / `auto_compute_changes`
- [x] Transactional ValidState commit (fresh disagreement rolls back)
- [x] Evidence-binding + atomic tests; independent arith reference

### Performance
- [x] Cheap-ops slowdown preserved; synthetic expensive speedups labeled
- [x] Real Lean kernel baseline (`BenchObligations.lean`, ~177ms check−startup) — not yet incremental reuse

### Literature
- [x] `docs/PRIOR_ART.md` draft

### CI note
`source-policy` / `verified-public-integration` fail on sealed census — **expected**; not weakened.

## Deferred
- Full fuel-induction completeness of affectedClosure ↔ Affected
- Incremental Lean-obligation reuse experiment (baseline only)
- Proof-carrying update transcripts; multistep history

## Highest-priority next
1. Bridge `runIncremental` accepted ⇒ `LogicalAccept`
2. Incremental Lean proof-obligation reuse with matched trust
3. Multistep history soundness
4. Expand adversarial campaign

## Reproduction
```bash
cd research/incremental_certificate_revalidation_v0
bash scripts/check_lean.sh
PYTHONPATH=. python3 -m pytest -q tests
PYTHONPATH=. python3 -m benchmarks.lean_kernel_suite
```
