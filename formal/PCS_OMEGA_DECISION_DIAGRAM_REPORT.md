# PCS bounded reasoning, repair and optimal intervention — Lean 4.28 reference package

Toolchain `leanprover/lean4:v4.28.0` (unchanged), standalone `formal/` workspace, `import Std`
only, no Mathlib, no new dependency, `lake-manifest.json` unchanged.  The existing `PCS`,
`PCSAuthority`, `PCSSemanticCheck`, `PCSCountermodel` libraries/executables and their import
graph are untouched; the new libraries are **not** imported by any of them.

New libraries (added to `lakefile.toml` and to `defaultTargets`):

| library | modules |
|---|---|
| `PCSOmega` | `Formula`, `Check`, `Repair`, `Named` |
| `PCSDecisionDiagram` | `Diagram`, `Apply`, `Witness`, `Conditional`, `Summary`, `Bellman`, `Optimal`, `Recon`, `Pass`, `Intervention`, `Validate` |
| `PCSControls` | `PCSOmega.Controls`, `PCSDecisionDiagram.Controls` (executed positive controls) |

Outside every library (never imported): `PCSNegative/FalseEquivalence.lean`,
`PCSNegative/FalseWeightedMinimum.lean` (negative controls), `PCSOmegaDDAudit.lean` (axiom audit).

No `sorry`, `admit`, `axiom`, `unsafe`, `implemented_by`, `native_decide` or `Lean.ofReduceBool`
occurs in these sources.  Finite controls use ordinary kernel-checked `decide` / `decide +kernel`.

## Commands executed and logs (all in `formal/logs/`)

| command | log | result |
|---|---|---|
| `cd formal && lake build` | `lake-build.log` | `Build completed successfully (291 jobs)`, exit 0 (the `PCSDecisionDiagram.Controls` module alone takes ≈ 9–10 min: 24-variable controls are kernel-evaluated through the symbolic pipeline) |
| `lake env lean PCSCountermodel/Audit.lean` | `countermodel-audit.log` | exit 0 (existing audit unchanged) |
| `lake env lean PCSOmegaDDAudit.lean` | `omega-dd-axioms.log` | 99 `#print axioms` lines, exit 0 |
| `lake env lean PCSDecisionDiagram/Controls.lean` | `dd-controls.log`, `dd-controls.time` | exit 0 |
| `lake env lean PCSNegative/FalseEquivalence.lean`, `... FalseWeightedMinimum.lean` | `negative-controls.log` | both **fail** (exit 1) with the intended semantic `decide` errors |
| baseline before this work | `baseline-lake-build.log` | earlier full build |

Every principal theorem depends only on a subset of `propext`, `Classical.choice`, `Quot.sound`
(`js_safe_bounds` depends on none).  The full output is reproduced at the end of this file.

## Scope: reference vs. refinement

* Everything here is a **typed executable Lean reference model** with proofs about that model.
  Exact operational parity with `pcs/experimental/omega/*.py`, `public/omega-*.mjs`,
  `conditional.py`, `public/conditional-core.mjs`, `intervention.py`, `intervention_cli.py` and
  `public/intervention-core.mjs` is **not proved** (no Python/JavaScript refinement theorem).
  Where the transcription is deliberately literal it is noted (e.g. `stepCell` / `winnersCell`
  transcribe the Python winners loop and are *proved* equal to `comb`; `walkPy` transcribes
  the Python reconstruction loop and is *proved* to return the lexicographically least optimum).
* The Omega frontier is ordered by `sortBy rk` (a structural stable insertion sort) for an
  arbitrary comparator `rk`; for a total preorder this coincides with any stable sort.  All Omega
  soundness theorems hold for **every** ranking; learned weights only affect priority.
* Receipts model content only; hashing, JSON bytes, serialization, browser concurrency and
  authority binding are outside the model.  All new receipts carry `pcsAuthority = false` and
  `leanKernelChecked = false` (proved: `check_flags`, `search_flags`, `plan_flags`); the
  existing browser/Python flags are not changed by these proofs.

## Theorem-to-contract map

### §1 Typed Boolean semantics, exhaustive checking, screening, repair (`PCSOmega`)
| contract | theorem |
|---|---|
| evaluator correctness vs. independent `Holds` | `BForm.eval_iff_holds`; locality `BForm.eval_congr` |
| complete False-before-True enumeration (incl. `n = 0`: `allAsg 0 = [[]]`) | `mem_allAsg`, `length_allAsg` (= `2^n`), `nodup_allAsg`, `pairwise_lexLt_allAsg` |
| fresh exhaustive check ⇔ agreement on every valuation | `check_none_iff` |
| first disagreement distinguishes the immutable source; it is lexicographically least | `check_some_sound`, `check_some_least` |
| receipt replay of a check | `checkReceipt_equivalent_iff`, `checkReceipt_count`, `verifyCheckReceipt_iff` |
| remembered-witness rejection ⇒ non-equivalence; more witnesses cannot restore; equivalent candidates always survive | `screen_some_not_equiv`, `screen_append_of_some`, `screen_isSome_append_left`, `screen_none_of_equiv` |
| survival alone ≠ equivalence | `Controls.screen_survivor_not_equiv` |
| bounded legal edits (≤ 63 nodes, depth 8, ≤ 128 actions) | `applyAction_bounded`, `actionsOf_length` |
| accepted search solutions preserve source semantics (any ranking) | `search_solution_sound`, `search_status_iff` |
| work accounting (initial check, ranked proposals, screened witnesses, examined candidates) | `search_accounting` |
| replay with immutable source, checked parents, remembered witnesses, acceptance only after a fresh check | `replay_sound` |
| named lowering (declared, sorted distinct names; meaning preserved; bounds preserved) | `lower_eval`, `lower_isSome_iff`, `lower_size_depth`, `strictSortedS_nodup` |

### §2 Ordered decision diagrams, apply, compilation (`Diagram`, `Apply`, `Validate`)
| contract | theorem |
|---|---|
| reads only variables ≥ top variable | `evalD_support` |
| extension preserves old roots | `evalD_extend` |
| Shannon decomposition | `evalD_shannon` |
| constant-root completeness (root 0 ⇔ unsatisfiable, 1 ⇔ valid) | `exists_sat_unsat`, `eq_zero_iff_unsat`, `eq_one_iff_valid` |
| canonicity | `canonical` |
| executable validator decides validity exactly | `validB_iff` |
| unique-table node creation preserves invariants | `mkNode_spec` |
| memoised bounded apply (AND/OR/XOR): invariants + denotation; cache hits counted against the operation budget | `apply_spec`, `apply_ops_le`, `apply_exhausted` |
| bounded AST compilation preserves meaning | `compile_spec` |

### §3 Conditional outcomes (`Witness`, `Conditional`)
| contract | theorem |
|---|---|
| false-first witness is lexicographically least satisfying assignment; `none` iff root 0 | `wit_least`, `world_spec`; work `witSteps_le` |
| premises compiled first, prefix-stopping; prefix inconsistency ⇒ full inconsistency; query never compiled | `premLoop_spec`, `check_inconsistent` (diagram `source = candidate = none`) |
| inclusion-minimal core, removal witnesses satisfy the other **core** premises | `shrink_spec`, `coreWits_spec`, `check_inconsistent` |
| equivalent-under-assumptions: satisfying context witness + equal values on all satisfying assignments | `check_equivalent` |
| disagreement: total assignment satisfies every premise, separates meanings, lexicographically least | `check_counterexample` |
| resource exhaustion claims nothing | `check_resource_limit` |
| replay compares the entire regenerated receipt | `verify_iff` |

### §4 Positive-cost intervention (`Summary`, `Bellman`, `Optimal`, `Recon`, `Pass`, `Intervention`)
| item | theorem |
|---|---|
| tie algebra (counts add, mandatory ∩, possible ∪; strict winner) | `Summ.append`, `Summ.shift`, `Summ.unique` |
| skipped variables: strictly positive cost always loses | `comb_shift_pos`, `comb_bcell_skip`, `optC_skip_iff` |
| exact cell meaning at every level | `summ_cellRec` |
| 1. single pass terminates (structural fold), cell = spec, exactly one computation / two inspections per node, `ns.size + 2` cells | `bellmanPass_spec`; literal winners loop `winnersCell_two`, `stepCell_eq`; node count ≤ limit (`plan_optimal` gives `dpNodes ≤ lim.nodes`, i.e. ≤ 4096) |
| 2. null root ⇔ no feasible lock-respecting assignment | `bellman_correct` (first conjunct); AST level `plan_no_feasible` vs. `plan_inconsistent` vs. `plan_resource_limit` |
| 3. reconstruction reaches true, respects locks, reported objective, global minimum | `recon_spec`, `walkPy_spec`, `bellman_correct`, `plan_optimal` |
| 4. lexicographically least optimal **total** assignment (False first, baseline completion) | `recon_least`, `recon_spec`, `walkPy_spec` |
| 5. count = number of distinct optimal total assignments; `count ≤ 2^n`; cost ≤ 24,000,000 | `bellman_correct` (duplicate-free `optList`), `bellman_bounds`, `plan_optimal`, `js_safe_bounds` |
| 6. mandatory ⇔ every optimum flips; possible ⇔ some optimum flips; masks `< 2^n`; mandatory ⊆ possible; locked variables never in a mask | `bellman_correct`, `bellman_bounds`, `plan_optimal` |
| 7. `audit_proposal`: feasibility = premises ∧ target ∧ locks; gap only for feasible proposal vs. resolved optimum, `≥ 0`, `= 0` ⇔ optimal; infeasible / unresolved ⇒ no gap | `audit_feasible_iff`, `audit_gap`, `audit_gap_present`, `audit_no_gap_unresolved`, `audit_no_gap_infeasible` |
| 8. AST-level composition; resource-limit receipts carry no costs/assignment/count/masks/table; internal guard never fires for valid tasks | `plan_optimal`, `plan_resource_limit`, `plan_ok`, `plan_valid`, `plan_flags` |
| guarded entry for external diagrams (invalid table, bad root, zero cost rejected) | `bellmanChecked_ok` |

### §5 Replay / decoder boundaries
| contract | theorem |
|---|---|
| deterministic replay rejects any receipt differing from the reference output (task, limits, cells, witnesses, masks, costs, work, flags) | `IReceipt.verify_iff`, `IReceipt.verify_rejects`, `IReceipt.verify_rejects_changed`, `PCSDD.verify_iff` |
| typed validators: names `[A-Z][A-Z0-9_]{0,15}`, not reserved, strictly sorted; ≤ 24 vars, ≤ 8 assumptions, ≤ 128 nodes / depth 12; costs 1…1,000,000; sorted distinct locks; limits in range | `namesOK`, `CTask.validB`, `ITask.validB`, `Limits.valid` (executable) with `validFacts`, `strictSortedS_nodup`, `plan_valid` |

## Executed controls (all pass in `lake build`)
`PCSOmega/Controls.lean`: implication reversal rejected with least witness `[false,true]`;
De Morgan accepted (⇒ `SemEquiv`); remembered counterexample rejection; partial-filter survivor
`A→B` vs `A∨B` that a fresh check rejects; `n = 0` constants; a repair episode (constant
ranking) found by search, replayed, and a tampered episode rejected; named-lowering controls.

`PCSDecisionDiagram/Controls.lean`: `TRUE` vs `B` under `A`, `A→B` (equivalent, context witness
`[true,true]`), with `A` removed → disagreement `[false,false]`; opposite premises `A`, `¬A` with
a dense query → inconsistent, core `[0,1]`, query never compiled, removal witnesses; 24-variable
De Morgan (balanced, depth 6) decided symbolically (`dm24_equivalent`); dense ordering
`x_i ∧ x_{i+6}` exhausts a 40-node budget (no semantic field) but resolves under default limits;
`n = 0` constants; weighted `A∨B` costs 3/1 → minimum 1, count 1, `[false,true]`, mandatory `B`;
tied 1/1 → count 2, no mandatory flip, possible `{A,B}`; lock `B` → minimum 3, mandatory `A`;
lock both → no feasible plan (`lockBoth_infeasible`); `A ∨ (B ∧ ¬B)` with true `B` baseline →
`[true,true]` (skipped `B` keeps baseline), cost 5; 12 disjoint choices over 24 variables →
minimum 12, count 4096, assignment `[false,true]×12`, no mandatory flip, all 24 possible
(`choices12_summary`); `n = 0` TRUE (empty plan, count 1) / FALSE (infeasible); inconsistent
context reported separately from infeasible goal.  Runtime rejections: invalid ordering,
forward child id, redundant node, duplicate triple, out-of-range variable (`validB = false`);
zero cost / out-of-range root in `bellmanChecked`; zero cost, cost > 10^6, non-FALSE candidate,
unsorted locks, invalid limits (`plan` errors); forged count, mandatory/possible masks, minimum,
assignment, authority flag and limits all fail replay; a forged optimal receipt for an exhausted
run fails replay; audit gaps (infeasible cheap proposal: none; optimum: 0; `[true,false]`: 2).

Negative controls (`logs/negative-controls.log`): `false_implication_reversal` fails with
"`decide` proved that the proposition `check (A.imp B) (B.imp A) = none` is false";
`false_weighted_minimum` / `false_mandatory_flip` fail with "`decide` proved that the proposition
`some 1 = some 0` / `some [1] = some [0]` is false" after the planner output is computed by kernel
`decide`.  These are semantic rejections, not syntax or import errors.

## Unresolved obligations (single list)
1. **Python/JavaScript refinement**: no theorem relates the Lean reference models to
   `omega/{logic,search,adaptive}.py`, `omega-core.mjs`, `omega-adaptive.mjs`, `conditional.py`,
   `conditional-core.mjs`, `intervention.py`, `intervention_cli.py`, `intervention-core.mjs`
   (dict/hash-map caches, recursion order, exception paths, integer semantics in JS).
2. **Search completeness for replay**: `replay_sound` proves accepted replayed solutions are
   equivalent, but it is not proved that every `search` output passes `replay`; no
   bounded-search completeness, fairness or global repair optimality is claimed.
3. **Parsing / decoding**: JSON bytes, exact-field object decoding, Bool/int distinction at the
   JSON level, the conditional text grammar (precedence NOT > AND > OR > right-assoc `->`,
   aliases, case-insensitive keywords, Unicode whitespace / `splitlines`) and the Python/game
   named JSON lowering are not formalised; only typed validators and the typed named-AST
   lowering (`PCSOmega.Named`) are proved.  FOL innermost binders are covered by the existing
   `PCSCountermodel.Named`, not here.
4. **Hashing, serialization, authentication**: SHA-256 digests, receipt hashes, browser
   snapshotting before asynchronous digests, UI revision guards and stale-download prevention
   are external runtime assumptions; replay theorems are about content equality only.
5. **Empirical scope**: no theorem concerns learned accuracy, training improvement, natural
   language interpretation, causality, human provenance, participant identity, consent, or
   scientific authority; `pcs_authority` remains `false`.
6. Zero-cost interventions are outside the protocol (positivity is a hypothesis of every
   Bellman theorem and is enforced by `ITask.validB`).

## Actual `#print axioms` output (`lake env lean PCSOmegaDDAudit.lean`)
```
$ lake env lean PCSOmegaDDAudit.lean
'PCSOmega.BForm.eval_iff_holds' depends on axioms: [propext]
'PCSOmega.BForm.eval_congr' depends on axioms: [propext]
'PCSOmega.mem_allAsg' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSOmega.length_allAsg' depends on axioms: [propext, Quot.sound]
'PCSOmega.nodup_allAsg' depends on axioms: [propext, Quot.sound]
'PCSOmega.pairwise_lexLt_allAsg' depends on axioms: [propext, Quot.sound]
'PCSOmega.IsLexLeast.unique' depends on axioms: [propext, Quot.sound]
'PCSOmega.check_none_iff' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSOmega.check_some_sound' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSOmega.check_some_least' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSOmega.checkReceipt_equivalent_iff' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSOmega.checkReceipt_count' depends on axioms: [propext, Quot.sound]
'PCSOmega.verifyCheckReceipt_iff' depends on axioms: [propext]
'PCSOmega.screen_some_not_equiv' depends on axioms: [propext]
'PCSOmega.screen_append_of_some' depends on axioms: [propext, Quot.sound]
'PCSOmega.screen_isSome_append_left' depends on axioms: [propext, Quot.sound]
'PCSOmega.screen_none_of_equiv' depends on axioms: [propext, Quot.sound]
'PCSOmega.actionsOf_length' depends on axioms: [propext, Quot.sound]
'PCSOmega.applyAction_bounded' depends on axioms: [propext]
'PCSOmega.search_solution_sound' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSOmega.search_status_iff' depends on axioms: [propext]
'PCSOmega.search_flags' depends on axioms: [propext]
'PCSOmega.search_accounting' depends on axioms: [propext, Quot.sound]
'PCSOmega.replay_sound' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSOmega.strictSortedS_nodup' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSOmega.lower_eval' depends on axioms: [propext]
'PCSOmega.lower_isSome_iff' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSOmega.lower_size_depth' depends on axioms: [propext]
'PCSOmega.Controls.implication_reversal_not_equiv' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSOmega.Controls.de_morgan_equiv' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSOmega.Controls.remembered_rejection' depends on axioms: [propext]
'PCSOmega.Controls.screen_survivor_not_equiv' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSOmega.Controls.episode_solution_sound' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.evalD_support' depends on axioms: [propext, Quot.sound]
'PCSDD.evalD_shannon' depends on axioms: [propext, Quot.sound]
'PCSDD.evalD_extend' depends on axioms: [propext, Quot.sound]
'PCSDD.exists_sat_unsat' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.eq_zero_iff_unsat' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.eq_one_iff_valid' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.canonical' depends on axioms: [propext, Quot.sound]
'PCSDD.mkNode_spec' depends on axioms: [propext, Quot.sound]
'PCSDD.apply_spec' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.apply_ops_le' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.apply_exhausted' depends on axioms: [propext, Quot.sound]
'PCSDD.compile_spec' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.wit_least' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.world_spec' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.witSteps_le' depends on axioms: [propext, Quot.sound]
'PCSDD.conjList_spec' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.premLoop_spec' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.shrink_spec' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.coreWits_spec' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.verify_iff' depends on axioms: [propext, Quot.sound]
'PCSDD.check_flags' depends on axioms: [propext]
'PCSDD.check_resource_limit' depends on axioms: [propext]
'PCSDD.check_inconsistent' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.check_equivalent' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.check_counterexample' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.Summ.unique' depends on axioms: [propext, Quot.sound]
'PCSDD.Summ.append' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.Summ.shift' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.comb_shift_pos' depends on axioms: [propext, Quot.sound]
'PCSDD.candL_split' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.comb_bcell_skip' depends on axioms: [propext, Quot.sound]
'PCSDD.summ_cellRec' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.bellman_correct' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.bellman_bounds' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.optC_skip_iff' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.recon_least' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.recon_spec' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.winnersCell_two' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.stepCell_eq' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.bellmanPass_spec' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.walkPy_spec' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.validB_iff' depends on axioms: [propext, Quot.sound]
'PCSDD.bellmanChecked_ok' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.plan_valid' depends on axioms: [propext]
'PCSDD.plan_ok' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.plan_resource_limit' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.plan_inconsistent' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.plan_no_feasible' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.plan_optimal' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.plan_flags' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.js_safe_bounds' does not depend on any axioms
'PCSDD.IReceipt.verify_iff' depends on axioms: [propext, Quot.sound]
'PCSDD.IReceipt.verify_rejects' depends on axioms: [propext, Quot.sound]
'PCSDD.IReceipt.verify_rejects_changed' depends on axioms: [propext, Quot.sound]
'PCSDD.audit_feasible_iff' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.audit_gap' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.audit_no_gap_unresolved' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.audit_no_gap_infeasible' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.audit_gap_present' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.Controls.tAB_equivalent' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.Controls.tOpp_inconsistent' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.Controls.dm24_decision' depends on axioms: [propext]
'PCSDD.Controls.dm24_equivalent' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.Controls.tDense_nothing_claimed' depends on axioms: [propext]
'PCSDD.Controls.lockBoth_infeasible' depends on axioms: [propext, Classical.choice, Quot.sound]
'PCSDD.Controls.choices12_summary' depends on axioms: [propext]
exit: 0
```
