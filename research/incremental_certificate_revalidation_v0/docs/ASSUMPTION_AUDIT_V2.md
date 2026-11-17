# Assumption audit v2 — hostile review of central theorems

**Head audited:** `6481522c` (start of Grand Challenge II)  
**Scope:** `formal/PCSIncremental/{Semantics,Soundness,Correspondence,Cache,Certificate,Invalidation}.lean`

## Decomposition (do not conflate)

| Layer | Claim | Role of ChangesComplete / idsCovered |
|---|---|---|
| **Logical soundness** | Given per-node local evidence (Affected rechecked ∨ Unaffected reused), `FreshValid` holds | **Unused** in the case split — already discharged into those premises |
| **Operational correctness** | An algorithm *constructs* those per-node premises from prior state + graphs | **Essential** — seeds Affected; without them reuse/recheck classification is wrong |

Do **not** insert unused hypotheses into logical theorems merely to name them. Prove operational theorems that *establish* the premises instead.

## Assumption-dependency matrix

| Theorem | Hypotheses actually used in proof | Unused named fields | Substantive? | About impl? |
|---|---|---|---|---|
| `incremental_implies_fresh` | `affectedRechecked`, `unaffectedReused`, `prior` (via `reuse_entry_checks`) | `changesComplete`, `idsCovered` | **Yes** — derives FreshValid without assuming it | No — witness only |
| `reuse_entry_checks` | `reusePermitted`, `cacheSound`, key equality ⇒ op/ver/pol/deps | evidence equality implied by key but **not passed to LocalCheck** | Yes for abstract check | No |
| `executableAcceptImpliesLeanFresh` | decoded `IncrementalAccept` | execAccepted boolean ignored after `true` | Conditional only | **No** — assumes decoding |
| `invalidation_sound` / `complete` | inductive Affected | — | Definitional | No |
| `new_edge_requires_new_graph_invalidation` | Downstream on `g'` | — | Yes for topology | Guides Python default |
| `no_authority_no_reuse` | `priorAccepted=false` | — | Yes | Matches cache API |
| `fresh_implies_incremental_full_recheck` | FreshValid + full seed set | changesComplete supplied by caller | Shows full-recheck embeds | No |
| `affected_least` | inductive path | — | Yes (least fixed point) | No |

## LocalCheck / evidence binding (critical gap)

| Side | Signature | Evidence |
|---|---|---|
| Lean `LocalCheck` (GC-II) | `Op→Ver→Pol→Evidence→deps→payload→out→Bool` | **bound** |
| Python `local_check_node` | includes `evidence` | **used** (constants) |
| `ObligationKey` | includes `evidence` | eligibility binds it |

**Status:** Repaired in GC-II. `reuse_entry_checks` now rewrites evidence equality from obligation keys into the checker call.

**Opaque evidence ID ≠ source-byte fidelity.** Matching `evidence : Nat` only proves identifier equality, not correct parsing of source bytes. Remaining trust: evidence registry / content addressing outside this model.

## Minimal sufficient hypotheses

### Logical (`incremental_implies_fresh`)

For every `n ∈ g'.nodes`:

- If `Affected g' changes n.id`, then `nodeChecks check n σ' (certs' n.id)`
- If `Unaffected …`, then ∃ authoritative eligible cache entry whose cert/output are used
- Prior `FreshWitness.cacheSound` (for reuse path)

`ChangesComplete` and `idsCovered` are **not** logically required once the above hold.

### Operational (algorithm must prove)

- `changes = computeChanges prior.graph g'` (or proven `ChangesComplete`)
- Affected computed on `g'` equals mathematical `Affected`
- Recheck/reuse classification follows that set
- New nodes treated as changes and rechecked
- Checker receives evidence-bound obligations
- Commit only after acceptance gates

## Counterexamples (operational necessity)

| Weakened claim | Counterexample |
|---|---|
| Prior-graph Affected complete | New edge → set incompleteness (`test_prior_affected_misses_new_edge_completeness`) |
| Accept without ChangesComplete + with forged authority | Stale accept (`test_forged_authority_plus_incomplete_changes_false_accept`) |
| Prior invalidation + incomplete + forgery | Stale accept (`test_prior_invalidation_plus_forgery_false_accept`) |
| No authority | Reuse denied (`test_no_authority_blocks_reuse`) |

These falsify **operational** weakened claims, not the logical theorem’s unused fields.

## Stronger statements not yet proved

1. `runIncremental … = .ok r ∧ r.accepted → FreshValid` (algorithm soundness)
2. `ChangesComplete g g' (computeChanges g g')` with exactness/minimality
3. Executable affected BFS ↔ `Affected`
4. Multistep `S₀→⋯→Sₙ` preservation
5. Evidence-bound denotation theorems for concrete ops
6. Refinement: Python trace ⇒ IncrementalAccept

## Graph evolution coverage

| Mutation | Modeled? |
|---|---|
| Node field replacement | Yes (same id) |
| Dependency rewiring | Yes (defn change + new-graph Affected) |
| Insertion | Partially (Python changes_complete; Lean `idsCovered` forbids) |
| Deletion | No |
| Rename | No (would appear as delete+insert) |

## Answer key (hostile questions)

1. Substantive? **Yes** for `incremental_implies_fresh` post-vacuity repair.  
2. Conclusion in hypothesis? **No** (FreshValid not a field).  
3. Trusted cache witness? **Yes** — `FreshWitness.cacheSound` / `priorAccepted`; executable cannot construct securely against adversarial storage without extra mechanisms.  
4. About actual impl? **No** until algorithm/refinement theorems.  
5. Stronger true statements? Algorithm soundness, computeChanges, multistep.  
6. Redundant assumptions? `changesComplete`/`idsCovered` redundant **for logical FreshValid**; not for ops.  
7. Graph mods? Replacements+rewires; not deletes/renames.  
8. WF/acyclicity? In `ValidState`; not re-checked in `incremental_implies_fresh` body.  
9. Values vs abstract checker? Only abstract `LocalCheck` acceptance — denotation separate.  
10. Bound to source/ops? **Weak** until evidence enters LocalCheck and concrete denotation theorems exist.
