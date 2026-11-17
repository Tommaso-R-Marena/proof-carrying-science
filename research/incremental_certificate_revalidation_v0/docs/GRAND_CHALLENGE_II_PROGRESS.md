# Grand Challenge II — Progress

**Branch:** `research/pcs-incremental-revalidation-v0`  
**Draft PR:** #217  
**Updated:** 2026-11-17 (America/New_York)

## Completed this campaign cycle

### Milestone 1 — Mathematical specification strengthened
- [x] `docs/GRAND_CHALLENGE_II_BASELINE.md` (head `6481522c`, CI census failure documented)
- [x] `docs/ASSUMPTION_AUDIT_V2.md` — logical vs operational; ChangesComplete unused in logical case split
- [x] LocalCheck evidence-bound (`Op→Ver→Pol→Evidence→deps→payload→out`)
- [x] `LogicalAccept` separated from operational `IncrementalAccept`
- [x] `logical_implies_fresh` / evidence-aware `reuse_entry_checks`

### Milestone 2 — Verified Lean algorithm (partial → substantive)
- [x] `Algorithm.lean`: `computeChanges`, proved `computeChanges_complete`, `computeChanges_seeds_new`
- [x] Executable `affectedClosure` + step soundness (`collectDependents` ⇒ `dependsOn`)
- [x] Concrete `runIncremental` / `runNodes` / `stepNode` (computable)
- [x] `runIncremental_changes_complete`, `incremental_run_sound` (= LogicalAccept ⇒ FreshValid)
- [ ] Full bridge: `runIncremental = ok accepted` ⇒ constructed `LogicalAccept` (remaining)

No `sorry` / `admit` / custom axioms. Axiom audit: propext / Classical.choice / Quot.sound only.

### Executable / systems
- [x] Python `compute_changes` aligned with Lean
- [x] `auto_compute_changes` path on `revalidate`
- [x] Transactional ValidState commit (fresh disagreement rolls back)
- [x] Evidence-binding + atomic tests

### CI note
`source-policy` / `verified-public-integration` fail on sealed census — **expected** for unadmitted research; not weakened.

## Abandoned / deferred (this cycle)
- Full fuel-induction completeness of affectedClosure ↔ Affected (soundness of steps proved; full ↔ deferred)
- Real Lean-kernel benchmarks (next priority after this push)
- Proof-carrying update transcripts
- Literature PRIOR_ART.md (subagent in flight)

## Highest-priority next
1. Prove `runIncremental` ok ⇒ LogicalAccept (or extract decide-checker)
2. Real Lean 4.28.0 proof-check benchmarks (cold/warm/trusted/defense)
3. Independent arithmetic reference (no shared registry)
4. Multistep history soundness
5. Expand adversarial + PRIOR_ART integration

## Reproduction
```bash
cd research/incremental_certificate_revalidation_v0
bash scripts/check_lean.sh
PYTHONPATH=. python3 -m pytest -q tests
```
