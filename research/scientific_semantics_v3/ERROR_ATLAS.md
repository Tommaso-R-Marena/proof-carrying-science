# PR #202 exhaustive primary error atlas

This is a post-hoc diagnostic review of the exposed v2 evaluation. It reproduces the frozen grader exactly and preserves development **6/21** and old-final **1/20** supported-claim recall. It is not a new held-out experiment or revised semantic score.

All 41 supported probes are inspected below, including all 34 misses and all 19 old-final misses. The 12 counterclaim/insufficient-evidence probes are retained in JSON. Internal adjudication is AI-assisted and requires domain-expert review; there is no independent external validation.

## What failed

The failures are not 34 demonstrated incorrect scientific assertions. They combine absent extraction/derived claims, unresolved scientific roles and assumptions, and strict representation/grading mismatches. Three correctly recovered reported iteration/evaluation counts are rejected solely by the frozen relation schema. The Goldbeter V1 inverse-power expression is independently equal to the division expression on the common defined domain, but syntax matching misses it. This diagnostic does not establish full scientific equivalence or alter the original result.

Other apparently simple mismatches need care. Unspecified units cannot be changed into physical units to make a label pass. `encoded_model_unit` and `encoded_concentration` are reference role labels, not SI units. Extracting a return vector does not establish an ODE derivative role. A source sum is not a conservation law without a complete model/dependency argument. Conditional dimensional consequences must retain their assumptions.

No targeted mismatch in this set demonstrates an incorrect numeric literal replacing an already correctly grounded reference value. This does not measure overall extraction precision: most generated candidates are unannotated. A retained **genuine semantic counterexample outside the probes** is the integration tutorial's `2N` differential-equation count: the heuristic emits value2 with unitN (newton). That confuses a symbolic equation count with a force measurement. Duplicate quantity/claim projections and parameter-only targets also inflate pair mismatches relative to scientific claim counts.

## Reproduction

```bash
python -m research.scientific_semantics_v3.error_atlas --check
```

The command checks original archive/object hashes, source spans and the full frozen grading output for every case. It independently computes the V1 rational diagnostic with the v2 bounded normalizer. It does not run uploaded code, alter old artifacts or consult the new prospective corpus.

## development

Frozen matched/supported: 6/21. Misses: 15.

| Primary diagnosis | Missed claims |
| --- | ---: |
| assumption_sensitive_missing_derivation | 3 |
| missing_conditional_scientific_claim | 1 |
| missing_dependency_assertion | 1 |
| missing_derived_assertion | 1 |
| missing_derived_claim_link | 1 |
| missing_extraction | 3 |
| mixed_relation_and_unit_gap | 2 |
| reported_relation_grading_mismatch | 3 |

### biomodels_tyson1991

**tyson-init-cp — MATCH: matched**

The encoded initial amount of CP is 0.75.

CP initialAmount=0.75 is an exact source-declaration match; unrelated declaration metadata is also targeted by the strict grader.

Required next check: No new interpretation check needed for the literal declaration.

Abstention assessment: `not_abstained`. Error tags: `none`.

Source: `research/scientific_understanding_v2/fixtures/upstream/tyson1991.sbml` (SHA256 `5a4f44b5a0bc8f32d3206f460f748236539de593be0fb016da2ed7cddd098e36`). Overlapping candidate IDs: `quantitie-08cc0f50f885ee07e866ae4d`, `assumption-3eaea76ea74cd432dd587c0b`.

Frozen first rejection reasons: quantity name differs/missing.

**tyson-init-pm — MATCH: matched**

The encoded initial amount of pM is 0.25.

pM initialAmount=0.25 is an exact source-declaration match. Case-sensitive identifier is preserved.

Required next check: No new interpretation check needed for the literal declaration.

Abstention assessment: `not_abstained`. Error tags: `none`.

Source: `research/scientific_understanding_v2/fixtures/upstream/tyson1991.sbml` (SHA256 `5a4f44b5a0bc8f32d3206f460f748236539de593be0fb016da2ed7cddd098e36`). Overlapping candidate IDs: `quantitie-24650740aec50e11ae2ac9d3`, `assumption-3d61f7fa932f82942ad05fcd`.

Frozen first rejection reasons: quantity name differs/missing.

**tyson-total-cdc2-definition — MATCH: matched**

The model defines CT as C2 + CP + M + pM.

CT assignment and all four linear terms match exactly. This definition alone is not conservation.

Required next check: Keep a distinct conservation obligation.

Abstention assessment: `not_abstained`. Error tags: `none`.

Source: `research/scientific_understanding_v2/fixtures/upstream/tyson1991.sbml` (SHA256 `5a4f44b5a0bc8f32d3206f460f748236539de593be0fb016da2ed7cddd098e36`). Overlapping candidate IDs: `equation-401c740c0340c0ac2975c4f1`.

**tyson-cdc2-conservation — MISS: missing_derived_claim_link**

For the encoded reactions in the fixed size-one compartment, CT is conserved and has initial value 1.

The interpretation contains CT's sum, while the separate model-assurance check already contains the exact nullspace vector [1,1,1,1,0,0] and initial total 1. No typed CT conservation claim links the two. The reference is reviewer-derived and explicitly outside the frozen inference fragment; a match would additionally encounter its unsupported balance slot.

Required next check: Bind CT's definition to the complete stoichiometric matrix, fixed compartment and initial state; preserve the real-trajectory/refinement obligations.

Abstention assessment: `justified_fragment_abstention_but_linkable_scoped_result`. Error tags: `scientific_dependency_tracking`, `assumptions_conditions`, `identifier_resolution`, `evaluator_schema`.

Source: `research/scientific_understanding_v2/fixtures/upstream/tyson1991.sbml` (SHA256 `5a4f44b5a0bc8f32d3206f460f748236539de593be0fb016da2ed7cddd098e36`). Overlapping candidate IDs: `equation-401c740c0340c0ac2975c4f1`.

**tyson-total-cyclin-definition — MATCH: matched**

The model defines YT as Y + YP + M + pM.

YT's four-term source definition matches. The model does not thereby conserve YT.

Required next check: Do not promote the sum definition to a conservation law.

Abstention assessment: `not_abstained`. Error tags: `none`.

Source: `research/scientific_understanding_v2/fixtures/upstream/tyson1991.sbml` (SHA256 `5a4f44b5a0bc8f32d3206f460f748236539de593be0fb016da2ed7cddd098e36`). Overlapping candidate IDs: `equation-684a086934ede528d3182dd6`.

**tyson-association-rate — MATCH: matched**

The encoded Reaction4 rate is cell * CP * k3 * Y, with k3 = 200.

Reaction4 expression and k3=200 are recovered. Parameter-only candidates are also targeted, inflating mismatching pair counts without representing distinct false scientific claims.

Required next check: Keep reaction-local parameter scope explicit.

Abstention assessment: `not_abstained`. Error tags: `none`.

Source: `research/scientific_understanding_v2/fixtures/upstream/tyson1991.sbml` (SHA256 `5a4f44b5a0bc8f32d3206f460f748236539de593be0fb016da2ed7cddd098e36`). Overlapping candidate IDs: `equation-e41ab0148b7fef31c90d27c3`, `quantitie-cb031e35c093d33825d2a16b`, `table-7c2cc072baa8de288c8d31f7`.

Frozen first rejection reasons: equation rhs differs/missing.

**tyson-activation-rate — MATCH: matched**

The encoded Reaction9 rate is cell * pM * (k4prime + k4 * (M/CT)^2), with k4 = 180 and k4prime = 0.018.

Reaction9 rational expression and both local parameters match; CT!=0 remains a separate condition.

Required next check: Do not infer nonzero CT solely from algebraic matching.

Abstention assessment: `not_abstained`. Error tags: `none`.

Source: `research/scientific_understanding_v2/fixtures/upstream/tyson1991.sbml` (SHA256 `5a4f44b5a0bc8f32d3206f460f748236539de593be0fb016da2ed7cddd098e36`). Overlapping candidate IDs: `equation-cb3d931e45b749ac7f3ec1f8`, `quantitie-23702f9696a93ac6287317af`, `quantitie-6900463a038451bd16a3eac2`, `table-34aa39c0a4b02c20e1ac34cb`.

Frozen first rejection reasons: equation rhs differs/missing.

**tyson-zero-deactivation — MISS: missing_derived_assertion**

With encoded parameter k5notP = 0, Reaction5 has zero flux for finite species values.

The complete rate and k5notP=0 are present, but neither is typed as a derived flux=0 claim. The quantity name flux is absent; the reviewer-derived label would still require assumptions outside this grader's supported fragment.

Required next check: Perform exact scoped substitution and retain finite operands and model-closure assumptions.

Abstention assessment: `justified_fragment_abstention_but_simple_derivation_possible`. Error tags: `numerical_relationship`, `scientific_dependency_tracking`, `assumptions_conditions`, `evaluator_schema`.

Source: `research/scientific_understanding_v2/fixtures/upstream/tyson1991.sbml` (SHA256 `5a4f44b5a0bc8f32d3206f460f748236539de593be0fb016da2ed7cddd098e36`). Overlapping candidate IDs: `equation-6f229293957bd6d98e17b2af`, `quantitie-83bfce0a2522aea030fa7a72`, `table-027bd203b64f250d3195a4f7`.

Frozen first rejection reasons: quantity name differs/missing.

**tyson-biosynthesis-rate — MISS: missing_dependency_assertion**

The encoded cyclin biosynthesis rate is cell * k1aa, where k1aa = 0.015.

The correct Reaction6 expression cell*k1aa and parameter0.015 are already extracted. Missing depends_on_Y=false blocks the conjunction; syntactic free-symbol absence must be distinguished from transitive model dependency.

Required next check: Resolve k1aa and cell definitions before certifying no transitive Y dependency.

Abstention assessment: `not_abstained_partial_proposal`. Error tags: `scientific_dependency_tracking`, `evaluator_schema`.

Source: `research/scientific_understanding_v2/fixtures/upstream/tyson1991.sbml` (SHA256 `5a4f44b5a0bc8f32d3206f460f748236539de593be0fb016da2ed7cddd098e36`). Overlapping candidate IDs: `equation-e9fc04195604c04526fa626d`, `quantitie-b163a18229ab5b22ae16e3ad`, `table-f7b5ab689b94992a7f8721ae`.

Frozen first rejection reasons: equation rhs differs/missing; typed slot depends_on_Y differs/missing.

**tyson-dimension-feedback-ratio — MISS: assumption_sensitive_missing_derivation**

If CT and M share concentration dimension C, then the feedback ratio M/CT is dimensionless.

M/CT exists as a subexpression in the rate, but there is no standalone conditional dimensional conclusion. Concentration dimensions are reviewer assumptions rather than source-declared physical units.

Required next check: Represent a conditional dimension theorem with explicit M and CT dimensions and CT!=0; do not infer physical units.

Abstention assessment: `correct_conservative_abstention_without_assumptions`. Error tags: `units_dimensions`, `assumptions_conditions`, `missing_extraction`.

Source: `research/scientific_understanding_v2/fixtures/upstream/tyson1991.sbml` (SHA256 `5a4f44b5a0bc8f32d3206f460f748236539de593be0fb016da2ed7cddd098e36`). Overlapping candidate IDs: `equation-cb3d931e45b749ac7f3ec1f8`, `table-34aa39c0a4b02c20e1ac34cb`.

**tyson-dimension-feedback-coefficients — MISS: assumption_sensitive_missing_derivation**

Under concentration-rate dimensional consistency, k4 and k4prime both have dimension inverse time.

Numeric k4 and k4prime are present with unspecified units. No conditional inverse-time dimension inference is proposed; the reference has no explicit target entity or expression accepted by the frozen target matcher.

Required next check: Solve dimensional constraints conditional on a concentration-rate law and shared concentration dimensions, retaining the assumptions.

Abstention assessment: `correct_conservative_abstention_without_assumptions`. Error tags: `units_dimensions`, `assumptions_conditions`, `missing_extraction`.

Source: `research/scientific_understanding_v2/fixtures/upstream/tyson1991.sbml` (SHA256 `5a4f44b5a0bc8f32d3206f460f748236539de593be0fb016da2ed7cddd098e36`). Overlapping candidate IDs: `equation-cb3d931e45b749ac7f3ec1f8`, `quantitie-23702f9696a93ac6287317af`, `quantitie-6900463a038451bd16a3eac2`, `table-34aa39c0a4b02c20e1ac34cb`.

**tyson-dimension-association-coefficient — MISS: assumption_sensitive_missing_derivation**

Under concentration-rate dimensional consistency, k3 has dimension concentration^-1 * time^-1.

k3=200 is correctly source-bound but has no declared physical unit; expected C^-1*T^-1 is a reviewer-derived consistency condition.

Required next check: Emit a conditional dimensional constraint, separate from declared units and empirical validity.

Abstention assessment: `correct_conservative_abstention_without_assumptions`. Error tags: `units_dimensions`, `assumptions_conditions`.

Source: `research/scientific_understanding_v2/fixtures/upstream/tyson1991.sbml` (SHA256 `5a4f44b5a0bc8f32d3206f460f748236539de593be0fb016da2ed7cddd098e36`). Overlapping candidate IDs: `equation-e41ab0148b7fef31c90d27c3`, `quantitie-cb031e35c093d33825d2a16b`, `table-7c2cc072baa8de288c8d31f7`.

Frozen first rejection reasons: typed slot dimension differs/missing.

### scipy_rosenbrock

**dev-scipy-001 — MISS: mixed_relation_and_unit_gap**

The unmodified Rosenbrock objective has minimum value zero.

minimum_objective=0 is correctly recovered as reported_value. The frozen equality grader rejects that relation; the candidate also lacks the reference's dimensionless typing and a resolved definition of this function.

Required next check: Keep reported versus proved truth separate; bind the function definition and explicitly justify dimensionless coordinates/objective.

Abstention assessment: `correct_unit_abstention_with_avoidable_relation_mismatch`. Error tags: `evaluator_schema`, `units_dimensions`, `assumptions_conditions`.

Source: `research/scientific_understanding_v2/fixtures/upstream/scipy_optimize.rst` (SHA256 `62cc919a2738b31df8c01accf2f95eaadbe71f92d9073f9975dae9c15e6eb29f`). Overlapping candidate IDs: `equation-4913c1a63dd5f982cb3182b6`, `quantitie-34b40897b5c0601c569a3e4d`, `claim-e31a0c38b34245b3939eb8e7`.

Frozen first rejection reasons: typed equality relation differs.

**dev-scipy-002 — MISS: missing_extraction**

The documented five-variable Nelder-Mead example prints a minimizer with all five coordinates equal to one.

The printed five-component res.x vector has no overlapping valid candidate; vectors printed after doctest expressions are not extracted. Printed ones are not an exact theorem about the floating-point optimizer.

Required next check: Link the output vector to its adjacent call and inputs, preserve printed precision and report status.

Abstention assessment: `avoidable_missing_capability`. Error tags: `missing_extraction`, `numerical_relationship`, `source_grounding`, `assumptions_conditions`.

Source: `research/scientific_understanding_v2/fixtures/upstream/scipy_optimize.rst` (SHA256 `62cc919a2738b31df8c01accf2f95eaadbe71f92d9073f9975dae9c15e6eb29f`). No valid overlapping candidate under the frozen bounded source policy.

**dev-scipy-003 — MISS: reported_relation_grading_mismatch**

The documented Nelder-Mead run reports 339 iterations.

339 iterations, count units, adjacent Nelder-Mead call and local solver arguments are already correct. reported_value is rejected as equality. A duplicated claim record yields another mismatching pair, not another scientific failure.

Required next check: Use separate relation and epistemic-status fields in a successor contract; retain reported-only status.

Abstention assessment: `not_abstained_correct_reported_literal`. Error tags: `evaluator_schema`.

Source: `research/scientific_understanding_v2/fixtures/upstream/scipy_optimize.rst` (SHA256 `62cc919a2738b31df8c01accf2f95eaadbe71f92d9073f9975dae9c15e6eb29f`). Overlapping candidate IDs: `quantitie-ada267265a3634102a21fcbf`, `quantitie-48c4632c50d8065a76daadbf`, `quantitie-b648e664cbcb76dd0acdeba2`, `claim-4b342e2e5b6d67eb69b58a55`, `claim-8798f7331eb3439ff2aa742b`, `claim-45101465cf48bb86b86b4440`.

Frozen first rejection reasons: typed equality relation differs.

**dev-scipy-004 — MISS: reported_relation_grading_mismatch**

The documented Nelder-Mead run reports 571 function evaluations.

571 function evaluations and count units are already correct with the local solver call. The reported_value relation is not accepted as equals by the frozen grader.

Required next check: Separate literal equality from reported evidence status, without changing this frozen score.

Abstention assessment: `not_abstained_correct_reported_literal`. Error tags: `evaluator_schema`.

Source: `research/scientific_understanding_v2/fixtures/upstream/scipy_optimize.rst` (SHA256 `62cc919a2738b31df8c01accf2f95eaadbe71f92d9073f9975dae9c15e6eb29f`). Overlapping candidate IDs: `quantitie-48c4632c50d8065a76daadbf`, `quantitie-b648e664cbcb76dd0acdeba2`, `claim-8798f7331eb3439ff2aa742b`, `claim-45101465cf48bb86b86b4440`.

Frozen first rejection reasons: typed equality relation differs.

**dev-scipy-005 — MISS: missing_extraction**

The Nelder-Mead example configures the coordinate stopping tolerance xatol to 1e-8.

The solver_context includes the complete options expression with xatol=1e-8, but no independent typed xatol quantity overlaps the probe. This is a missing extracted option, not an incorrect literal.

Required next check: Parse bounded literal option maps and link option meaning to the declared solver call; do not confuse local stopping tolerance with achieved global error.

Abstention assessment: `avoidable_missing_capability`. Error tags: `missing_extraction`, `scientific_dependency_tracking`, `identifier_resolution`.

Source: `research/scientific_understanding_v2/fixtures/upstream/scipy_optimize.rst` (SHA256 `62cc919a2738b31df8c01accf2f95eaadbe71f92d9073f9975dae9c15e6eb29f`). No valid overlapping candidate under the frozen bounded source policy.

**dev-scipy-006 — MISS: mixed_relation_and_unit_gap**

With the tutorial scaling parameter a=0.5 and offset b=1, the reported objective value is 1.

reported_objective=1 and the adjacent rosen_with_args call including args=(.5,1.) are present. reported_value first fails equality; dimensionless unit semantics remain missing after that mismatch is removed.

Required next check: Bind objective definition and argument substitutions; retain six-decimal reporting tolerance and numerical reproduction status.

Abstention assessment: `correct_unit_abstention_with_avoidable_relation_mismatch`. Error tags: `evaluator_schema`, `units_dimensions`, `assumptions_conditions`.

Source: `research/scientific_understanding_v2/fixtures/upstream/scipy_optimize.rst` (SHA256 `62cc919a2738b31df8c01accf2f95eaadbe71f92d9073f9975dae9c15e6eb29f`). Overlapping candidate IDs: `quantitie-5fd5f40eb18886f7584ba98f`, `claim-43dff333dfbc263f2cc54579`.

Frozen first rejection reasons: typed equality relation differs.

**dev-scipy-007 — MISS: reported_relation_grading_mismatch**

The illustrative BFGS run with analytic gradient reports 25 iterations, and the text explicitly permits variation.

25 iterations and count units with BFGS call, jac=rosen_der, may_vary=true and value_semantics=REPORTED are preserved in the quantity record. The grader rejects reported_value; its duplicate claim also omits value_semantics, causing a separate scope mismatch.

Required next check: Preserve epistemic/scope metadata across duplicate record projections; treat reported variability separately from numerical equality.

Abstention assessment: `not_abstained_correct_reported_literal`. Error tags: `evaluator_schema`, `uncertainty_scope`.

Source: `research/scientific_understanding_v2/fixtures/upstream/scipy_optimize.rst` (SHA256 `62cc919a2738b31df8c01accf2f95eaadbe71f92d9073f9975dae9c15e6eb29f`). Overlapping candidate IDs: `quantitie-d524a4d26c55da735a4292bc`, `quantitie-7ef589bcaba6cbba5fbb90de`, `quantitie-ae8beb569bef1e756d6029c2`, `claim-2fffa4acdf57f4e7720e3bd9`, `claim-0c4304285c903300629449f8`, `claim-509641ec7475861f82b3c43c`.

Frozen first rejection reasons: reported versus universal scope is unspecified; typed equality relation differs.

**dev-scipy-010 — MISS: missing_extraction**

The documented final-coordinate Rosenbrock gradient is 200*(x[-1]-x[-2]**2).

No candidate overlaps the der[-1] assignment. Return-expression extraction does not recover component assignments; mapping Python negative indices to N-1/N-2 requires an explicit N>=2 sequence context.

Required next check: Extract typed indexed assignments and independently establish index/domain correspondence before matching the mathematical gradient.

Abstention assessment: `avoidable_missing_capability`. Error tags: `missing_extraction`, `identifier_resolution`, `equivalent_forms`, `scientific_dependency_tracking`.

Source: `research/scientific_understanding_v2/fixtures/upstream/scipy_optimize.rst` (SHA256 `62cc919a2738b31df8c01accf2f95eaadbe71f92d9073f9975dae9c15e6eb29f`). No valid overlapping candidate under the frozen bounded source policy.

**dev-scipy-011 — MISS: missing_conditional_scientific_claim**

The local quadratic Newton stationary step is described as a local minimum when the Hessian is positive definite.

The positive-definite-Hessian conditional prose is not represented. No incorrect unconditional minimum claim was proposed.

Required next check: Extract the conditional statement and resolve this function to the local quadratic model; retain that local versus global scope.

Abstention assessment: `avoidable_missing_capability`. Error tags: `missing_extraction`, `assumptions_conditions`, `scientific_reference_resolution`.

Source: `research/scientific_understanding_v2/fixtures/upstream/scipy_optimize.rst` (SHA256 `62cc919a2738b31df8c01accf2f95eaadbe71f92d9073f9975dae9c15e6eb29f`). No valid overlapping candidate under the frozen bounded source policy.

## final

Frozen matched/supported: 1/20. Misses: 19.

| Primary diagnosis | Missed claims |
| --- | ---: |
| assumed_unit_role_missing | 1 |
| assumption_sensitive_missing_derivation | 2 |
| equivalent_form_grading_mismatch | 1 |
| identifier_and_model_unit_representation_mismatch | 1 |
| missing_conditional_scientific_claim | 2 |
| missing_derived_numerical_claim | 1 |
| missing_extraction | 7 |
| missing_negated_applicability_claim | 1 |
| missing_ode_semantic_link | 1 |
| missing_source_to_model_derivation | 1 |
| undeclared_unit_reference_mismatch | 1 |

### biomodels_goldbeter1991

**final-goldbeter-001 — MISS: identifier_and_model_unit_representation_mismatch**

The encoded Goldbeter model initializes cyclin C concentration to 0.01.

C initialConcentration=0.01 and symbolic (substance)/(volume) units are present. Reference quantity initial_C has no shared typed slot with name C/role sbml_initialConcentration; encoded_concentration is a role label, not a physical unit synonym.

Required next check: Represent entity C, quantity-kind initial_concentration and declared versus inferred unit roles separately. Do not blindly alias scientific unit expressions.

Abstention assessment: `partial_representation_not_wrong_initial_value`. Error tags: `identifier_resolution`, `evaluator_schema`, `units_dimensions`.

Source: `research/scientific_understanding_v2/fixtures/heldout/goldbeter1991.sbml` (SHA256 `a633872e4c602922e85ac487ef52ac8bd8ead762ec7c0f86f9e93032a84c90f5`). Overlapping candidate IDs: `quantitie-2dafe654814811646980432c`, `assumption-cac9a8dca61e4ddd4a96b6ad`.

**final-goldbeter-002 — MISS: undeclared_unit_reference_mismatch**

The encoded maximum activation parameter VM1 is 3.

VM1=3 is recovered exactly. Source declares no physical units and the candidate keeps unit=null; reference encoded_model_unit is an unspecified-role placeholder, not a source-declared unit.

Required next check: Use an explicit unspecified model-unit role in a successor contract while retaining unknown physical dimensions.

Abstention assessment: `correct_abstention_on_undeclared_physical_unit`. Error tags: `units_dimensions`, `evaluator_schema`.

Source: `research/scientific_understanding_v2/fixtures/heldout/goldbeter1991.sbml` (SHA256 `a633872e4c602922e85ac487ef52ac8bd8ead762ec7c0f86f9e93032a84c90f5`). Overlapping candidate IDs: `quantitie-c66c7186d42d9f12d991e59e`.

Frozen first rejection reasons: unit semantics differs/missing.

**final-goldbeter-003 — MISS: equivalent_form_grading_mismatch**

The model assigns V1=VM1*C/(C+Kc).

The exact source expression C*VM1*(C+Kc)^(-1) is recovered. The frozen matcher compares canonical syntax and does not reduce inverse powers to division. Independent rational normalization confirms equality on the common defined domain, retaining C+Kc!=0.

Required next check: Keep the same lhs/symbol identities and explicit nonzero-domain obligation; algebraic equality alone does not establish scientific meaning.

Abstention assessment: `not_abstained_correct_equivalent_expression`. Error tags: `equivalent_forms`, `evaluator_schema`, `assumptions_conditions`.

Source: `research/scientific_understanding_v2/fixtures/heldout/goldbeter1991.sbml` (SHA256 `a633872e4c602922e85ac487ef52ac8bd8ead762ec7c0f86f9e93032a84c90f5`). Overlapping candidate IDs: `equation-1ac19d4e038045af20bfb5d1`.

Frozen first rejection reasons: equation rhs differs/missing.

**final-goldbeter-004 — MATCH: matched**

The model assigns V3=VM3*M.

V3=M*VM3 matches the commutatively reordered reference VM3*M exactly under the frozen expression canon.

Required next check: Keep symbol scope and source identity unchanged.

Abstention assessment: `not_abstained`. Error tags: `none`.

Source: `research/scientific_understanding_v2/fixtures/heldout/goldbeter1991.sbml` (SHA256 `a633872e4c602922e85ac487ef52ac8bd8ead762ec7c0f86f9e93032a84c90f5`). Overlapping candidate IDs: `equation-9e62961f817f980be9ef3ec6`.

**final-goldbeter-005 — MISS: assumed_unit_role_missing**

The cyclin creation reaction uses vi=0.025.

vi=.025 is recovered exactly but units are unspecified. The reference's encoded_concentration_per_time is an inferred dynamical role and explicitly has no physical clock scale.

Required next check: Trace vi through the source reaction and fixed compartment into the concentration derivative; emit conditional role typing without inventing seconds.

Abstention assessment: `correct_conservative_abstention_on_inferred_unit_role`. Error tags: `units_dimensions`, `assumptions_conditions`, `evaluator_schema`.

Source: `research/scientific_understanding_v2/fixtures/heldout/goldbeter1991.sbml` (SHA256 `a633872e4c602922e85ac487ef52ac8bd8ead762ec7c0f86f9e93032a84c90f5`). Overlapping candidate IDs: `equation-d5b666d74b30f0dd7a928143`, `quantitie-080d2f29a446fe978f9b72b6`, `table-dd1d1864a8a2a1fddbc4e721`.

Frozen first rejection reasons: unit semantics differs/missing.

**final-goldbeter-006 — MISS: missing_source_to_model_derivation**

At fixed compartment volume the encoded cyclin balance is dC/dt=vi-kd*C-vd*X*C/(C+Kd).

No candidate overlaps the Octave xdot(1) assignment. The requested expanded balance needs reaction substitution, species-index mapping, local parameter resolution and fixed nonzero volume; no wrong expanded balance was proposed.

Required next check: Build independently checked source-to-model dependency closure and prove exact rational correspondence, retaining denominator conditions.

Abstention assessment: `avoidable_missing_capability`. Error tags: `missing_extraction`, `scientific_dependency_tracking`, `source_to_code`, `assumptions_conditions`.

Source: `research/scientific_understanding_v2/fixtures/heldout/goldbeter1991.m` (SHA256 `5a6951d93c1a39aa04e6ed5517b2870e3428a8018369121f3b9117b05511b59b`). No valid overlapping candidate under the frozen bounded source policy.

**final-goldbeter-007 — MISS: missing_derived_numerical_claim**

At the encoded initial state the initial cyclin derivative is 0.0240666666666667 in encoded concentration per time.

No typed initial dC/dt claim is emitted. Its value requires the complete balance, initial-state and scoped parameter substitutions; the primary model-assurance composite was UNKNOWN rather than a positive semantic verdict.

Required next check: Evaluate the grounded derivative exactly at the fully bound initial state and attach each source assumption; keep numerical and biological claims separate.

Abstention assessment: `avoidable_missing_capability`. Error tags: `missing_extraction`, `numerical_relationship`, `scientific_dependency_tracking`, `source_to_code`, `assumptions_conditions`.

Source: `research/scientific_understanding_v2/fixtures/heldout/goldbeter1991.m` (SHA256 `5a6951d93c1a39aa04e6ed5517b2870e3428a8018369121f3b9117b05511b59b`). No valid overlapping candidate under the frozen bounded source policy.

**final-goldbeter-009 — MISS: missing_conditional_scientific_claim**

The publication abstract reports possible sustained limit-cycle oscillations conditional on activation thresholds.

No valid bounded candidate covers the abstract's conditional limit-cycle sentence. Source-model parsing largely ignores notes/prose. The reference also uses a conditions slot not supported by the frozen semantic matcher, so extraction alone would not suffice.

Required next check: Extract attributed author-claim scope and both thresholds. A conditional abstract report is not an independent oscillation proof.

Abstention assessment: `avoidable_missing_capability`. Error tags: `missing_extraction`, `assumptions_conditions`, `scientific_synonyms`, `scientific_reference_resolution`.

Source: `research/scientific_understanding_v2/fixtures/heldout/goldbeter1991.sbml` (SHA256 `a633872e4c602922e85ac487ef52ac8bd8ead762ec7c0f86f9e93032a84c90f5`). No valid overlapping candidate under the frozen bounded source policy.

**final-goldbeter-011 — MISS: assumption_sensitive_missing_derivation**

The V1 assignment requires Kc and C to have equal dimensions because they are added.

C+Kc is represented inside the V1 expression, but no same-dimension relation is generated. The reference uses quantities plus relation same_dimension, which the frozen target matcher cannot identify or grade.

Required next check: Generate a conditional homogeneity obligation for each addition and distinguish consistency requirements from measured/declared dimensions.

Abstention assessment: `justified_abstention_without_dimensional_constraint_language`. Error tags: `units_dimensions`, `assumptions_conditions`, `evaluator_schema`.

Source: `research/scientific_understanding_v2/fixtures/heldout/goldbeter1991.sbml` (SHA256 `a633872e4c602922e85ac487ef52ac8bd8ead762ec7c0f86f9e93032a84c90f5`). Overlapping candidate IDs: `equation-1ac19d4e038045af20bfb5d1`.

**final-goldbeter-012 — MISS: assumption_sensitive_missing_derivation**

If the literal 1 in the activation law denotes a dimensionless normalized total, then M must be dimensionless.

The 1-M subexpression is present. No dimensionless-M conclusion is emitted because the literal one's normalized-total meaning is an explicit scientific assumption. The reference's conditional_on field is outside the frozen matcher.

Required next check: Represent a conditional theorem with the normalized-total interpretation visible; never infer a physical fraction from encoded substanceUnits alone.

Abstention assessment: `correct_conservative_abstention_without_normalization_assumption`. Error tags: `units_dimensions`, `assumptions_conditions`, `evaluator_schema`.

Source: `research/scientific_understanding_v2/fixtures/heldout/goldbeter1991.sbml` (SHA256 `a633872e4c602922e85ac487ef52ac8bd8ead762ec7c0f86f9e93032a84c90f5`). Overlapping candidate IDs: `equation-343c36a24923cc70f0a51f42`, `quantitie-9be2bad25300eeeaf6645988`, `table-342489fbd1c5c705d4603257`.

### scipy_integrate

**final-scipy-001 — MISS: missing_ode_semantic_link**

The Airy example uses dy0/dt=t*y1 and dy1/dt=y0.

func(t,y) returning [t*y[1],y[0]] is correctly extracted from the exact source span. The reference asks for component time derivatives, not a generic function return. No checked solve_ivp call-site, y-component convention or ODE-system interpretation connects them; list lhs/equivalent_system is also outside the frozen scalar matcher.

Required next check: Bind the function to the actual supported ODE call contract and component index map; do not equate arbitrary function outputs to derivatives.

Abstention assessment: `partial_expression_correct_but_scientific_role_unresolved`. Error tags: `identifier_resolution`, `scientific_dependency_tracking`, `evaluator_schema`, `source_to_code`.

Source: `research/scientific_understanding_v2/fixtures/heldout/scipy_integrate.rst` (SHA256 `0013ea5b885ce9e956473db028ce0963cc81ee8161458d4d5a50083e023f2b28`). Overlapping candidate IDs: `equation-3af9f15b65edcddbd5047cbc`.

**final-scipy-002 — MISS: missing_extraction**

The Airy example initializes y1(0)=1/(3^(2/3)*Gamma(2/3)).

The scalar y1_0 assignment is not extracted, and gamma is outside the small arithmetic callable fragment. y1_0 to y1(0) and Gamma/gamma spelling require imported-function and initialization-context resolution.

Required next check: Add safe symbolic special-function nodes and exact source binding; preserve fractional-power domains and do not execute uploaded callables.

Abstention assessment: `avoidable_missing_capability`. Error tags: `missing_extraction`, `identifier_resolution`, `equivalent_forms`, `scientific_dependency_tracking`.

Source: `research/scientific_understanding_v2/fixtures/heldout/scipy_integrate.rst` (SHA256 `0013ea5b885ce9e956473db028ce0963cc81ee8161458d4d5a50083e023f2b28`). No valid overlapping candidate under the frozen bounded source policy.

**final-scipy-003 — MISS: missing_extraction**

The Airy example initializes y0(0)=-1/(3^(1/3)*Gamma(1/3)).

The signed scalar y0_0 expression is not extracted. The missing semantic links mirror y1_0, with an additional explicit leading minus sign that must be preserved.

Required next check: Resolve the initial-state mapping and whitelisted gamma identity; compare the signed expression without floating-point-only equality.

Abstention assessment: `avoidable_missing_capability`. Error tags: `missing_extraction`, `identifier_resolution`, `equivalent_forms`, `scientific_dependency_tracking`.

Source: `research/scientific_understanding_v2/fixtures/heldout/scipy_integrate.rst` (SHA256 `0013ea5b885ce9e956473db028ce0963cc81ee8161458d4d5a50083e023f2b28`). No valid overlapping candidate under the frozen bounded source policy.

**final-scipy-004 — MISS: missing_extraction**

The Airy solve_ivp example integrates over the independent-variable interval [0,4].

t_span=[0,4] is not emitted as a typed interval quantity. No unsupported physical seconds were inferred, which is correct.

Required next check: Extract bounded literal lists with their call-site role and retain unspecified independent-variable units.

Abstention assessment: `avoidable_missing_capability`. Error tags: `missing_extraction`, `numerical_relationship`, `scientific_dependency_tracking`.

Source: `research/scientific_understanding_v2/fixtures/heldout/scipy_integrate.rst` (SHA256 `0013ea5b885ce9e956473db028ce0963cc81ee8161458d4d5a50083e023f2b28`). No valid overlapping candidate under the frozen bounded source policy.

**final-scipy-005 — MISS: missing_extraction**

The tightened Airy run sets both relative and absolute tolerances to 1e-8.

Tuple assignment rtol,atol=(1e-8,1e-8) and its call use are not represented as a mapping claim. The frozen matcher also lacks equals_mapping/dictionary numeric support.

Required next check: Track tuple destructuring and keyword dependencies; configured tolerances are not a global numerical-error certificate.

Abstention assessment: `avoidable_missing_capability`. Error tags: `missing_extraction`, `scientific_dependency_tracking`, `evaluator_schema`.

Source: `research/scientific_understanding_v2/fixtures/heldout/scipy_integrate.rst` (SHA256 `0013ea5b885ce9e956473db028ce0963cc81ee8161458d4d5a50083e023f2b28`). No valid overlapping candidate under the frozen bounded source policy.

**final-scipy-006 — MISS: missing_extraction**

The default Airy example prints y1(4)=0.00405982.

No source-bound result-array candidate covers sol1.y[1]'s printed endpoint. Mapping the last component to t=4 requires a time-grid/solution linkage, not selecting the last number from an arbitrary array.

Required next check: Parse printed bounded arrays and match the exact run/time grid, with printed precision and version context.

Abstention assessment: `avoidable_missing_capability`. Error tags: `missing_extraction`, `numerical_relationship`, `scientific_dependency_tracking`, `source_grounding`.

Source: `research/scientific_understanding_v2/fixtures/heldout/scipy_integrate.rst` (SHA256 `0013ea5b885ce9e956473db028ce0963cc81ee8161458d4d5a50083e023f2b28`). No valid overlapping candidate under the frozen bounded source policy.

**final-scipy-007 — MISS: missing_extraction**

At the default solver time grid endpoint t=4 the tutorial prints the Airy reference value 0.00095156.

The printed airy(sol.t)[0] array is absent. Its final0.00095156 is a special-function reference on a linked grid, distinct from the numerical ODE output0.00405982.

Required next check: Resolve airy component, time-grid endpoint and reference/run identities; do not conflate approximate solver output with the analytic reference.

Abstention assessment: `avoidable_missing_capability`. Error tags: `missing_extraction`, `numerical_relationship`, `scientific_dependency_tracking`, `source_grounding`.

Source: `research/scientific_understanding_v2/fixtures/heldout/scipy_integrate.rst` (SHA256 `0013ea5b885ce9e956473db028ce0963cc81ee8161458d4d5a50083e023f2b28`). No valid overlapping candidate under the frozen bounded source policy.

**final-scipy-009 — MISS: missing_negated_applicability_claim**

In the Airy example the default RK45 method does not support a supplied Jacobian matrix.

The source's RK45 Jacobian non-support statement is not extracted. No false support=true claim is proposed; absent extraction does not demonstrate correct understanding of the negation.

Required next check: Represent supported-operation capabilities with explicit polarity, method and version scope.

Abstention assessment: `avoidable_missing_capability`. Error tags: `missing_extraction`, `assumptions_conditions`, `scientific_reference_resolution`.

Source: `research/scientific_understanding_v2/fixtures/heldout/scipy_integrate.rst` (SHA256 `0013ea5b885ce9e956473db028ce0963cc81ee8161458d4d5a50083e023f2b28`). No valid overlapping candidate under the frozen bounded source policy.

**final-scipy-011 — MISS: missing_extraction**

The Bessel J_2.5 integral over [0,4.5] is reported as 1.1178179380783249.

No candidate covers the Bessel quadrature result tuple. Its first component is an integral estimate and the second a reported error estimate, not another measurement or a formal global error bound.

Required next check: Bind the special.jv order, integration limits and result-tuple roles to an approved independent numerical reconstruction.

Abstention assessment: `avoidable_missing_capability`. Error tags: `missing_extraction`, `numerical_relationship`, `scientific_dependency_tracking`, `source_grounding`.

Source: `research/scientific_understanding_v2/fixtures/heldout/scipy_integrate.rst` (SHA256 `0013ea5b885ce9e956473db028ce0963cc81ee8161458d4d5a50083e023f2b28`). No valid overlapping candidate under the frozen bounded source policy.

**final-scipy-013 — MISS: missing_conditional_scientific_claim**

The matrix exponential expression in the tutorial requires A(t) to commute with its time integral; the Airy matrix does not satisfy that condition.

The noncommutation prose is absent from typed candidates. Interpreting its condition requires resolving A(t) and its time integral in the nearby Airy system, not merely matching the word commute.

Required next check: Represent the exact matrix/time assumptions and independently compute a nonzero commutator witness where supported.

Abstention assessment: `avoidable_missing_capability`. Error tags: `missing_extraction`, `assumptions_conditions`, `scientific_reference_resolution`.

Source: `research/scientific_understanding_v2/fixtures/heldout/scipy_integrate.rst` (SHA256 `0013ea5b885ce9e956473db028ce0963cc81ee8161458d4d5a50083e023f2b28`). No valid overlapping candidate under the frozen bounded source policy.

## Scope and unresolved adjudication

The JSON retains each full source/reference interpretation, exact overlapping candidate quotations and typed fields, every first frozen rejection reason, per-case unchanged metrics and input hashes. Source-grounding failures in this atlas mean no qualifying overlapping candidate; original files remain preserved. Scientific synonym/reference resolution, variable aliases, assumptions, units, numerical relationships, equivalent forms and schema limitations are classified separately. Statistical generalization and biological adequacy remain unestablished.

Conditional scientific prose and dimensional constraints cannot be certified by a broader spelling alias. A successor system needs explicit entity/quantity-kind/evidence-status fields, definition closure and domain-aware checks. It must be evaluated on new projects; this exposed set can now support development only.
