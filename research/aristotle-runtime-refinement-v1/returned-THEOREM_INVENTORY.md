# Theorem inventory: statements, files, status and runtime contracts

"Proved" means the theorem builds with the commands in `BUILD.md`, has no `sorry`, and its
transitive axioms (`logs/principal_axioms.log`) are a subset of `propext`, `Classical.choice`
and `Quot.sound`.  The three Mathlib theorems were checked against Mathlib
`8f9d9cff6bd728b17a24e163c9402775d9e6a365` (`logs/statistics_mathlib_gates.log`).

## §3 Correspondence with the running implementations

| Theorem | File | Status | Runtime contract |
|---|---|---|---|
| `python_intervention_refines_reference` | `PCSRuntimeRefinement/PyIntervention.lean` | proved | The extracted `bellman` from `intervention.py` (lines 33–62, byte-bound) returns the Lean reference cells/choices for every valid diagram and task, given enough fuel. |
| `javascript_intervention_refines_reference` | `PCSRuntimeRefinement/JsIntervention.lean` | proved | The same for `intervention-core.mjs` (lines 14–27).  Every intermediate number is shown to be a safe integer. |
| `source_extraction_certificate_sound` | `PCSRuntimeRefinement/Summary.lean` | proved | An accepted Python/JS certificate means: byte-identical rendering of the source window, an unambiguous operator structure, and lowering equal to the executed program. |
| `runtime_result_semantics` | `PCSRuntimeRefinement/Summary.lean` | proved | The result is either the explicit unresolved (fuel) outcome or the exact optimum, count and mandatory/possible masks. |
| `omega_execution_replay_correct` | `PCSRuntimeRefinement/OmegaReplay.lean` | proved | For every ranking policy, every adaptive-search episode passes the independent replay, and its solutions are semantically equivalent to the source.  This is stated over the Lean model of `adaptive.py`. |
| `rust_certir_extraction_sound` | `PCSForgeRefinement/RustExtraction.lean` | proved | The extracted Rust `eval_expr` and its callees (token-bound to `certir-interpreter/src/lib.rs` lines 14–19, 39–137 and `certir/src/lib.rs` lines 20–35) run under the Rust-subset semantics and equal the Lean CertIR interpreter on every store and expression, at every width. |
| `python_conditional_refines_reference` | none | **outstanding** | See `OUTSTANDING.md`. |
| `javascript_conditional_refines_reference` | none | **outstanding** | See `OUTSTANDING.md`. |

Supporting results:
* `certir_width_source_bound`, `interp_bitvec_source_bound`, `interp_eval_binop_source_bound`,
  `interp_eval_cmp_bv_source_bound`, `interp_eval_expr_source_bound` and `extracted_fns_wf`
  (`PCSForgeRefinement/RustSyntax.lean`).
* `rust_eval_binop` (covers oversized shifts), `rust_eval_cmp_bv`, `rust_value_bitvec`,
  `rust_width_mask` and `rust_width_bits`.

## §4 Mathematical language, actions and immutable goals

| Theorem | File | Status | Runtime contract |
|---|---|---|---|
| `language_candidates_exact` | `PCSMathLanguage/LanguageExact.lean` | proved | The candidate list of the controlled language equals the set of successful parses under the tried precedence tables.  Ambiguity keeps both meanings.  A ranker only permutes the list. |
| `typed_lowering_preserves_denotation` | `PCSMathLanguage/IR.lean` | proved | Lowering checked IR to the typed IR preserves the denotation. |
| `render_parse_alpha_roundtrip` | `PCSMathLanguage/RoundTrip.lean` | proved | An independent parser applied to the rendered Lean statement returns the original IR.  Distinct checked IRs never share a rendering. |
| `action_rendering_closed` | `PCSMathLanguage/Receipt.lean` | proved | Rendered actions cannot contain imports, declarations, axioms or commands. |
| `transition_preserves_original_goal` | `PCSMathLanguage/Goals.lean` | proved | Valid, invalid, backtracking and exhausted transitions never change the original goal. |
| `all_branches_required` | `PCSMathLanguage/Goals.lean` | proved | Closure requires every subgoal of every split.  A single closed branch of `A ∨ B → A` does not authorize the theorem. |
| `final_receipt_sound` | `PCSMathLanguage/Receipt.lean` | proved | A receipt accepted by the final verifier implies the original claim. |
| `replay_reestablishes_original_claim` | `PCSMathLanguage/Receipt.lean` | proved | Replay rebinds the claim to the full IR, interpretation, actions and checker. |

## §5 Library, fair search and separation

| Theorem | File | Status | Runtime contract |
|---|---|---|---|
| `admitted_library_conservative` | `PCSReasoningLibrary/Library.lean` | proved | Every theorem proved with an admitted generation has a primitive proof over the original foundation. |
| `macro_expansion_preserves_proof` | `PCSReasoningLibrary/Library.lean` | proved | Expanding a macro gives a checked primitive proof of the same statement. |
| `research_plan_composes_checked_results` | `PCSReasoningLibrary/Library.lean` | proved | Checked intermediate results compose into the final theorem.  Failed or unknown dependencies are never available. |
| `adaptive_fair_search_complete` | `PCSReasoningLibrary/Search.lean` | proved | For any policy, every proof in the action calculus is found once the budget exceeds its depth. |
| `resume_budget_monotone` | `PCSReasoningLibrary/Search.lean` | proved | Success at budget `b` gives the same answer at every larger budget. |
| `cost_guided_search_optimal` | `PCSReasoningLibrary/Search.lean` | proved | Admissible cost-guided search returns a minimum-cost proof. |
| `shared_reasoning_family_upper_bound` | `PCSReasoningLibrary/Separation.lean` | proved | Certified reuse costs at most `40 (n+1)²`, counting library construction, admission and checking. |
| `baseline_family_lower_bound` | `PCSReasoningLibrary/Separation.lean` | proved | Tree search needs at least `2ⁿ` expansions. |
| `certified_reuse_complexity_separation` | `PCSReasoningLibrary/Separation.lean` | proved | Per-problem exponential-versus-quadratic separation, with a strict advantage for all `n ≥ 13`. |

## §6 Exact assumption discovery

| Theorem | File | Status | Runtime contract |
|---|---|---|---|
| `selector_projection_exact` | `PCSAssumptionDiscovery/Symbolic.lean` | proved | The selector predicate denotes Consistent ∧ Sufficient ∧ Locks. |
| `abduction_feasible_iff` | `PCSAssumptionDiscovery/Symbolic.lean` | proved | On length-`k` selectors, the selector formula holds exactly for the feasible selections. |
| `abduction_global_optimum` | `PCSAssumptionDiscovery/Symbolic.lean` | proved | The reported cost is the global minimum. |
| `abduction_optimal_count` | `PCSAssumptionDiscovery/Symbolic.lean` | proved | The reported count is the exact number of distinct optimal index sets. |
| `abduction_mandatory_possible_exact` | `PCSAssumptionDiscovery/Symbolic.lean` | proved | The mandatory and possible lists are exact. |
| `counterexample_clause_necessary` | `PCSAssumptionDiscovery/Cegar.lean` | proved | Every sufficient consistent explanation satisfies every counterexample clause. |
| `cegar_optimum_preserved` | `PCSAssumptionDiscovery/Cegar.lean` | proved | Refinement never excludes a feasible explanation. |
| `cegar_finite_termination` | `PCSAssumptionDiscovery/Cegar.lean` | proved | With fuel `2^k + 1`, the run never stops for lack of fuel. |
| `abduction_result_replay_sound` | `PCSAssumptionDiscovery/Receipt.lean` | proved | A verified receipt with an optimal outcome carries its additional assumptions explicitly, a conditional claim, a non-vacuity witness and global optimality. |

## §7 Verified learning

| Theorem | File | Status | Runtime contract |
|---|---|---|---|
| `episode_success_reward_requires_proof` | `PCSVerifiedLearning/Episode.lean` | proved | A success reward requires a fresh verified proof of the original theorem. |
| `eligible_feedback_reverified` | `PCSVerifiedLearning/Episode.lean` | proved | Producer rewards, forged receipts and unverified closures never become training data. |
| `potential_return_telescopes` | `PCSVerifiedLearning/Shaping.lean` | proved | Shaped return = return − Φ(s₀). |
| `potential_shaping_preserves_policy_order` | `PCSVerifiedLearning/Shaping.lean` | proved | Shaping preserves the order of expected returns. |
| `macro_discount_correct` | `PCSVerifiedLearning/Shaping.lean` | proved | Discounting by `γ^duration` matches the per-step return. |
| `alpha_firewall_exact` | `PCSMathLanguage/Alpha.lean` | proved | Canonical objects are equal iff the declarations are alpha-equivalent.  Companion results cover digest-based rejection of alpha duplicates. |
| `training_export_label_noninterference` | `PCSVerifiedLearning/Data.lean` | proved | Hidden evaluation labels do not affect exports, retrieval or feedback. |
| `generation_preserves_verifier_authority` | `PCSVerifiedLearning/Data.lean` | proved | Every generation keeps the acceptance boundary, and registry membership grants no authority. |

## §8 CertiForge optimization

| Theorem | File | Status | Runtime contract |
|---|---|---|---|
| `rust_certir_extraction_sound` | `PCSForgeRefinement/RustExtraction.lean` | proved | See §3. |
| `rust_certificate_preserves_eval_expr` | `PCSForgeRefinement/RustExtraction.lean` | proved | An accepted certificate preserves the extracted Rust `eval_expr` on every well-typed store. |
| `certir_eval_correspondence` | `PCSForgeRefinement/Denote.lean` | proved | The interpreter equals the bit-vector denotation. |
| `rewrite_certificate_universally_sound` | `PCSForgeRefinement/Rewrite.lean` | proved | Every accepted certificate preserves typing and denotation. |
| `optimization_sequence_preserves_program` | `PCSForgeRefinement/Rewrite.lean` | proved | Program-level `eval` is equal on every canonical input. |
| `verified_static_cost_improvement` | `PCSForgeRefinement/Rewrite.lean` | proved | The declared cost does not increase. |
| `optimization_episode_reward_sound` | `PCSForgeRefinement/Episode.lean` | proved | The reward comes from the checker, and a policy cannot affect acceptance. |

## §9 Statistical gates

| Theorem | File | Status | Runtime contract |
|---|---|---|---|
| `paired_improvement_bound` | `statistics/PCSStatistics/Gates.lean` (Mathlib) | proved | Hoeffding bound for the paired difference. |
| `adaptive_promotion_error_budget` | `statistics/PCSStatistics/Gates.lean` (Mathlib) | proved | Union over generations and candidates. |
| `anytime_selection_valid` | `statistics/PCSStatistics/Gates.lean` (Mathlib) | proved | With a summable allocation, the probability of any erroneous promotion is at most δ. |
| `exposure_ledger_enforces_test_protocol` | `PCSStatisticsCore/Finite.lean` | proved | A batch is admitted iff its test tasks are fresh. |

## §1 End-to-end

| Theorem | File | Status | Runtime contract |
|---|---|---|---|
| `end_to_end_acceptance_sound` | `PCSEndToEnd/Pipeline.lean` | proved | A success is bound to the selected statement, carries a checked witness, survives replay and yields verifier-derived labels. |
| `policy_cannot_manufacture_acceptance` | `PCSEndToEnd/Pipeline.lean` | proved | A false statement is never accepted, whatever the policy. |
| `end_to_end_abduction_sound` | `PCSEndToEnd/Abduction.lean` | proved | A reported explanation is satisfiable, sufficient and globally minimum-cost, with exact counts.  The assumptions are explicit in the conclusion and the receipt. |
