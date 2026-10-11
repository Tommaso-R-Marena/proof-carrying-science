# PCS: verified learning, reusable reasoning and exact assumption discovery

Build one integrated, executable and kernel-checked Lean 4.28.0 package that establishes the mathematical foundations of a reasoning system which learns reusable proof strategies, discovers sufficient assumptions, optimizes programs and improves through independently verified experience. Aim for the full theorem chain below. Invent useful algorithms, representations and stronger theorems where they advance that chain.

The attached package is a single standalone Lean workspace: the former PCS `formal/` directory is now the archive root. Read `SOURCE_MANIFEST.json`, `REPOSITORIES.json` and `README.md` first. It has no local dependencies. The manifest maps every original repository source path to its exact uploaded file. Non-workspace Python, JavaScript, Rust, Mathlib and older CertiForge Lean sources are retained under `source_reference/` with a `.txt` suffix, including their original extensions (for example `intervention.py.txt`); read these as source text, not Lake dependencies. All 691 original source files retain their exact bytes and pinned Git identities. Repository revisions:

- PCS: `4034db308d171b46c41e7e9ba2723e7fe4db6647`.
- Website: `457b6c62d451de20be9fb0435207b8fc9b655606`.
- CertiForge: `758c2c7d1ef0b0c68dda09938420aa6755c581cb`.

The previous Aristotle package already proves the general Boolean evaluator/enumerator, BDD operations and canonicity, assumption checking, Bellman optimum/count/masks, reconstruction and typed receipt replay. All 226 original named positive theorems, 66 positive controls and 1071 ordinary-kernel computation-certificate lemmas have since passed protected integration. Reuse these results. The new assignment is to close the implementation correspondence and learning-interface gaps and build the new reasoning algorithms below.

## 1. Required integrated result

Prove an end-to-end theorem for the implemented supported language, exact runtime programs and new checked reasoning machinery:

**For every accepted request, every untrusted proposal policy, every valid resource budget and every admitted library generation, a successful result is bound to the immutable selected mathematical statement and its actual assumptions, carries independently checked proof or counterexample evidence, survives independent replay, and supplies only verifier-derived training labels. Changing the policy, weights, rankings or unverified research memory cannot manufacture acceptance.**

Compose the decoder, language semantics, typed IR, lowering, action receiver, search, final verifier, replay and training intake theorems. Define each premise independently. Success must entail the semantic result through an actual checked witness. A producer-supplied `verified` Boolean or an uninterpreted `checkerIsSound` assumption is not a witness. Use Lean's kernel and the declared standard logical foundations as the mathematical foundation. Construct proof terms or verified certificates for the supported fragment.

Include a second end-to-end theorem for conditional assumption discovery: a reported explanation is a satisfiable, sufficient, globally minimum-cost assumption set, with exact counts and mandatory/possible membership across all optimal explanations. Carry the additional assumptions explicitly in the conclusion and receipt.

## 2. Engineering and proof requirements

Target Lean **4.28.0**. Preserve existing production definitions, authority contracts, toolchains, locks, registered checkpoints and import graphs. Add new proof libraries and executable entry points in separate namespaces, for example `PCSRuntimeRefinement`, `PCSVerifiedLearning`, `PCSReasoningLibrary`, `PCSAssumptionDiscovery` and `PCSForgeRefinement`. Ordinary finite controls supplement general theorems.

The uploaded root `lakefile.toml`, `lake-manifest.json` and `lean-toolchain` are the original standalone PCS formal configuration: Lean4.28.0, Std-only, zero `require` declarations and zero manifest packages. Do not introduce `path` dependencies or try to load the outer repository Lake configuration retained as inert reference text. Original `formal/...` paths in this request map to root paths; all other paths map through `SOURCE_MANIFEST.json`. Intentionally failing `PCSNegative` fixtures and the separate Mathlib `real/` sources are inert reference text, outside the active import graph.

For the full probability/real-analysis targets, use Aristotle's approved Lean4.28 Mathlib environment if available. The integration target pins Mathlib `8f9d9cff6bd728b17a24e163c9402775d9e6a365`; record the exact Mathlib revision actually used. Return Mathlib-dependent proofs as an explicitly separate library that can later join that root project, together with exact external Git dependency metadata, never a local `path` dependency. Keep the Std proof core buildable without Mathlib. The full statistical targets below remain requested. If the execution environment cannot supply Mathlib, establish the finite rational probability/union-bound foundation in Std and return the exact remaining general statistical obligations separately, without pretending they were proved. CertiForge's existing formal project uses Lean4.16 and is inert source context for a new Lean4.28 bridge, not a project whose pin may be silently changed.

Use no `sorry`, `admit`, new logical axioms, unsafe proof code, `native_decide`, `Lean.ofReduceBool`, `implemented_by`, external proof oracles or weakened goals in the new proof dependency closure. Computational acceleration may propose certificates; the ordinary kernel must verify their meaning. Print the transitive axiom inventories of all principal theorems. Keep negative controls outside library imports.

Do not resolve a correspondence obligation by writing a second unrelated model and asserting it resembles the source. Every source-level bridge must bind to exact source bytes, a defined language semantics and a checked lowering/extraction artifact. If an existing implementation violates the desired contract, produce the smallest executable counterexample, a concrete proposed patch and the theorem for the repaired program. Preserve the original counterexample. Deliver complete modules and exact remaining theorem obligations rather than imported placeholders.

## 3. Universal correspondence with the running implementations

Primary sources:

- `pcs/experimental/omega/{logic,search,adaptive}.py` and website `public/{omega-core,omega-adaptive}.mjs`.
- `pcs/experimental/conditional.py` and `public/conditional-core.mjs`.
- `pcs/experimental/intervention.py`, `intervention_cli.py` and `public/intervention-core.mjs`.
- `pcs/experimental/prover/{ir,language,environment,data,model,research,public_job}.py`.
- `formal/PCSProofProbe.lean`, `PCSProofWorker.lean` and existing `PCS/V2/Translation*` authorities.
- Website `src/lean-research.js` and `public/lean-learning-lab.mjs`.
- Existing `PCSOmega`, `PCSDecisionDiagram`, `PCSCountermodel` and `PCSReferenceCertificates`.

Define executable operational semantics for the precise Python/ECMAScript subsets used by these pure computations: tagged values, arrays/lists, objects/maps, recursion, update, branching, iteration, exceptions and integer/number operations. Build a source-bound checked extraction/lowering for this subset. Unsupported constructs must be rejected by extraction. A supported source file's extraction certificate must reconstruct its control/data operations, including evaluation order and error paths.

Prove successful and failing execution correspondence for every valid input, including cache hits, dictionary insertion order, node IDs, False-before-True witnesses, memoization, work counters, exhaustion and integer limits. Establish the commuting chain:

`actual source AST → extracted executable semantics → existing Lean reference algorithm → independently defined mathematical denotation`.

For JavaScript prove intermediate as well as output integer exactness at the actual bounds. For Python preserve the Bool/int distinction. Preserve resource exhaustion as an explicit unresolved outcome. Correspondence must cover complete structured results: assignments, inconsistent cores, counts, mandatory/possible masks, costs, work and flags. Prove that search outputs accepted by the actual receiver pass independently specified replay.

Principal targets: `python_conditional_refines_reference`, `javascript_conditional_refines_reference`, `python_intervention_refines_reference`, `javascript_intervention_refines_reference`, `omega_execution_replay_correct`, `source_extraction_certificate_sound`, `runtime_result_semantics`.

## 4. Mathematical language, proof actions and immutable goals

Give the actual supported mathematical grammar independent compositional semantics. Cover Prop, Nat, Int, natural-number functions/predicates, arithmetic, equality/order, Boolean connectives, typed quantifiers and the injectivity/composition expansions currently implemented. Formalize names, binding, scope, domain inference, tokenization, Unicode/whitespace behavior and every normalization used by `language.py`. Prove the exact set of supported parse candidates; ambiguity must retain distinct meanings and require a selected interpretation.

Define intrinsically typed Math IR, its environments/denotation, capture-free lowering and a faithful inverse representation. Prove normalization and rendering round trips up to explicitly defined alpha equivalence, preservation of quantifier order and assumptions, and correspondence to the Lean statement elaborated by the receiver. Extend the existing Semantic IR/Claim IR contracts compositionally. Name resolution must bind the approved definition bodies/environment, including overloaded symbols and universes where introduced.

Model actual goals, local contexts and simultaneous subgoals. Define receiver-approved actions and their proof-term semantics. Cover introductions, conjunction/iff construction, alternatives, exact/apply, conjunction projections, equality rewriting, the controlled simp set, witnesses, named disjunction branches and existing lemma references. A disjunction split must preserve both branches; no hidden discarded metavariable or missing branch may authorize a theorem.

Prove action rendering cannot inject imports, declarations, axioms or arbitrary commands. Prove immutable goal preservation through valid, invalid, backtracking and exhausted transitions; receiver-reported closure is followed by independent final verification. Tie receipts to full original IR, selected interpretation, proof/action sequence, definitions, checker revision and allowed axiom inventory. Treat digests as indices; exact canonical content/witness binding supplies the identity theorem.

Principal targets: `language_candidates_exact`, `typed_lowering_preserves_denotation`, `render_parse_alpha_roundtrip`, `action_rendering_closed`, `transition_preserves_original_goal`, `all_branches_required`, `final_receipt_sound`, `replay_reestablishes_original_claim`.

## 5. A conservative, growing library of learned proof strategies

Design and implement a typed library of reusable intermediate lemmas, proof macros and parameterized multi-step strategies. A library entry must include a closed checked proof term or a checked expansion into primitive proof actions, exact context/parameters, a dependency DAG and explicit resource costs. Model-proposed entries enter the admitted library only after independent checking. Type-correct instantiation must preserve binding and required premises.

Prove library-extension conservativity: every theorem established using any admitted generation already has a proof over the original approved foundation. Prove macro expansion soundness and termination, dependency acyclicity, deterministic replay and provenance invalidation when a premise, definition or checker changes. Give context-sensitive substitution, equality rewriting and certificate sharing correct semantics.

The current `research.py` only schedules obligations; implement real certified reuse of preceding results. Prove that a dependency-respecting research plan composes its checked intermediate results into the requested final theorem. A failed or unknown dependency must not become an available lemma.

Build a policy-independent search envelope combining arbitrary adaptive learned ranking with a trusted fair primitive fallback. Keep all fallback obligations eligible rather than beam-pruning them away. Prove acceptance soundness for any policy, budget monotonicity for resumable search, fairness, and completeness for every finite proof in the explicitly defined action calculus as total resources grow. Prove admissible cost-guided/A* optimality for the appropriate positive-cost model. Account for inference, retrieval, macro expansion, primitive checker transitions, replay and failed attempts.

Then prove a genuine algorithmic advantage on an explicitly defined infinite family of mathematical problems with repeated subproof structure. Establish a lower bound for a specified tree-search baseline and an upper bound for the certified shared-lemma/strategy algorithm. Count construction and checking of the library and all expansion costs. State whether the advantage is per problem or amortized over a family and prove that exact statement. Aim for an exponential-to-polynomial separation when the concrete algorithms and family support it; otherwise derive the strongest true separation. Instantiate the family with actual logical/arithmetic/function-composition theorems and executable Lean controls.

Principal targets: `admitted_library_conservative`, `macro_expansion_preserves_proof`, `research_plan_composes_checked_results`, `adaptive_fair_search_complete`, `resume_budget_monotone`, `cost_guided_search_optimal`, `shared_reasoning_family_upper_bound`, `baseline_family_lower_bound`, `certified_reuse_complexity_separation`.

## 6. Exact counterexample-guided discovery of sufficient assumptions

Implement a new algorithm over a finite valuation domain, ambient assumptions `A`, target `T`, named hypothesis catalog `H₀…Hₖ₋₁`, positive costs and optional locked selections. The output must characterize **all cheapest sufficient, consistent explanations**, not merely one repair or an inconsistent implication.

For selector vector `y`, define:

`Context(v,y) = A(v) ∧ ∧ᵢ (yᵢ → Hᵢ(v))`.

`Feasible(y) = (∃v, Context(v,y)) ∧ (∀v, Context(v,y) → T(v))`, together with locks.

`Cost(y) = Σᵢ (if yᵢ then costᵢ else 0)`.

Construct the exact selector predicate symbolically using decision-diagram conjunction, negation and existential elimination of world variables. Prove quantification/elimination semantics, invariant preservation and variable-index renaming. Compile the selector diagram into the existing positive-cost Bellman machinery. Prove global optimum, exact number of distinct optimal catalog-index sets, mandatory/possible hypotheses, false-first optimal reconstruction and faithful replay. Handle an inconsistent ambient context, no sufficient consistent explanation and budget exhaustion separately.

Also implement counterexample-guided optimization. Each genuine bad world contributes the selector clause `∨{yᵢ | Hᵢ(v)=false}`. Search for the cheapest candidate satisfying accumulated clauses, test its consistency and entailment, and refine with an independently checked bad world or consistency rejection. Prove each counterexample clause is necessary for every sufficient explanation; valid optimums are never excluded; each refinement makes genuine progress; completed acceptance is globally optimal; and fair unrestricted finite-domain refinement terminates. Preserve exact counting/explanation semantics when collecting all optimums. A resource-limited partial run must return its certified lower bound and unresolved obligations, with no fabricated optimum.

Generalize to certified theorem-level abduction over finite catalogs using a proof/countermodel interface, retaining explicit satisfiability and context witnesses. Compose resulting conditional conclusions with the original Claim IR, rather than silently importing discovered hypotheses into an unconditional theorem.

Principal targets: `selector_projection_exact`, `abduction_feasible_iff`, `abduction_global_optimum`, `abduction_optimal_count`, `abduction_mandatory_possible_exact`, `counterexample_clause_necessary`, `cegar_optimum_preserved`, `cegar_finite_termination`, `abduction_result_replay_sound`.

## 7. Sequential learning whose rewards and data come from verification

Formalize the actual episode state, transition logic and reward arithmetic in `environment.py`, including invalid actions, timeouts, terminal proofs, simultaneous goals and truncation. Prove successful terminal rewards require a fresh proof of the immutable original theorem, and that producer-supplied rewards, forged receipts and unverified closure cannot enter eligible training data. Bind replay to exact actions, IR, checker/environment and verified source provenance.

Analyze the current dense reward mathematically. Construct a verifier-controlled potential-based replacement `r' = r + γΦ(s') − Φ(s)` with bounded potentials, explicit cost and zero terminal/truncation potential. Prove the telescoping identity and policy-order preservation for the specified discounted episode objective. Cover variable-length proof macros using their actual duration and `γ^duration`; freeze or explicitly account for potential/model versions. Give executable exact-rational or fixed-point reward arithmetic and prove any float adapter's stated error bound. The learning policy must not choose its success label or terminal condition.

Formalize the supported alpha-normalization firewall and prove canonical-normal-form equality iff alpha equivalence in that grammar. Prove the actual fingerprint firewall rejects every alpha duplicate: equal canonical objects have equal deterministic digests, while collisions may cause additional conservative rejection. Use full canonical objects for the converse identity theorem. Build explicit typed/capability-separated training and evaluation exports. Prove noninterference of hidden evaluation proof labels with the permitted training/export computation, including retrieval and feedback intake; preserve module/source-family splits and checked provenance. Provide a concrete dependency/taint certificate for each exported example. General semantic equivalence must be established by proof where used, not inferred from a hash.

Define an iterative experimental state machine: frozen sources/checker/model, collection, independent label checking, training, fresh evaluation, promotion/rejection and versioned research memory. Prove that every generation preserves the acceptance boundary, that rejected/unknown results cannot become certified facts, and that registry membership alone grants no production authority.

Principal targets: `episode_success_reward_requires_proof`, `eligible_feedback_reverified`, `potential_return_telescopes`, `potential_shaping_preserves_policy_order`, `macro_discount_correct`, `alpha_firewall_exact`, `training_export_label_noninterference`, `generation_preserves_verifier_authority`.

## 8. Universal CertiForge optimization and proof-carrying extraction

Read the exact Rust CertIR types, parser, interpreter, rewrite/search and cost modules, PCS adapter and existing Lean semantics. Build a source-bound Lean4.28 operational bridge for the supported straight-line program fragment. Cover booleans, every supported bit-vector width, modular add/sub/mul/negation, bitwise operations, comparisons, shifts including oversized shift operands, binding, conditional expression evaluation and error behavior. Reflect Rust evaluation order and width masking exactly.

Implement proof-carrying rewrite/optimization certificates with a small independent checker. Prove universal expression/program equivalence for every accepted certificate and every well-typed input, not only exhaustive u8 examples. Prove each admitted rewrite schema, congruence/context replacement and composition of multi-step optimization. Counterexample certificates must be actual distinguishing inputs. Static cost improvement must be proved against the declared cost function. Bind each certificate to exact original/candidate programs, semantic version and rewrite library.

Compose extraction correspondence with certificate soundness to obtain correctness for the actual supported Rust execution semantics at u8/u16/u32/u64. Extend the learned optimization environment so arbitrary proposal rankings cannot affect universal acceptance. Prove its sequential reward and replay contracts through the same verified-learning interfaces.

Principal targets: `rust_certir_extraction_sound`, `certir_eval_correspondence`, `rewrite_certificate_universally_sound`, `optimization_sequence_preserves_program`, `verified_static_cost_improvement`, `optimization_episode_reward_sound`.

## 9. Rigorous mathematical gates for adaptive model selection

Using the approved Lean4.28 Mathlib environment described above, prove the statistical theorem required to accept a sequence of candidate policies, and return its source separately from the Std-only core. Define success as independent kernel verification under a fixed compute budget. Use a paired comparison on sampled tasks and bounded per-task solve/cost observations. Specify the probability space, sampling assumptions, stopping rule and permitted information at each generation.

Derive executable finite-sample confidence bounds for success differences and bounded cost differences, plus an anytime-valid/adaptive-generation guarantee with a summable error allocation or valid confidence sequence. Prove that the probability of any erroneous superiority promotion is bounded by the declared global error budget under those hypotheses. Handle correlation within paired tasks correctly and multiple seeds/models without counting the same task as independent observations. Construct mathematical negative controls demonstrating why repeated tuning on the same exposed test answers fails the required conditions.

Connect the theorem hypotheses to the experiment state machine and data exposure ledger. No proof of this selection theorem may assume that the neural architecture actually improves. The theorem should protect genuine measured improvement and correctly reject unsupported promotion.

Principal targets: `paired_improvement_bound`, `adaptive_promotion_error_budget`, `anytime_selection_valid`, `exposure_ledger_enforces_test_protocol`.

## 10. Required integration, adversarial controls and return package

Build the full dependency chain in this order: runtime/typed semantics; original-goal and replay authority; reusable library/fair search; exact assumption discovery; verifier-derived learning/data gates; universal optimization; adaptive statistical promotion; composed end-to-end theorems.

Run kernel-checked controls covering: Bool versus integer confusion; duplicate JSON keys; Unicode and precedence; quantifier reversal; capture and alpha-renaming; changed assumptions/environment; stale caches/receipts; one closed branch of `A∨B→A`; forged success/reward; unverified macro admission; cyclic lemma dependencies; altered definitions; hidden evaluation-label access; equivalent hash indices with unequal underlying content; memoization-budget exhaustion; consistent versus inconsistent explanations; tied cheapest hypotheses and exact optimal count; an unavoidable bad world falsifying every catalog hypothesis; oversized bit-vector shifts; false rewrite certificates; and repeated-exposure statistical controls.

Construct at least one full executable proof-learning cycle and one nontrivial assumption-discovery cycle using the new verified interfaces. Include a parameterized reusable-reasoning family, not only fixed fixtures. Print the exact general theorem statements and dependency/axiom inventories. Supply small and large controls; use ordinary-kernel computational certificates where direct large reduction is inefficient.

Return one integrated source archive containing: complete proof modules, executable algorithms/checkers, source-extraction certificates and source identity map, all required controls, exact build commands, real compiler logs, theorem-to-runtime-contract inventory, and exact outstanding theorem names for any unfinished portion. Keep completed modules compilable without unfinished imports. Preserve original source and failed counterexamples alongside proposed patches.

The central deliverable is a constructive, compositional correctness chain for **a growing learned reasoning library plus exact assumption discovery and independently controlled learning**, grounded in the actual PCS implementation. Push the algorithms and theorems as far as possible.
