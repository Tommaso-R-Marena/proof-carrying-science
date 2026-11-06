# Scientific understanding: prospective results and limits

The new implementation performs useful source-grounded mathematical and numerical checks on authentic projects. It does **not** establish reliable general automatic scientific understanding. The primary held-out evaluation found only 1 of 20 supported reference claims under its strict typed matching protocol, and the learned retriever underperformed lexical baselines. No unsupported scientific meaning was certified.

## Frozen sources and independent reference preparation

This branch starts at exact PR #201 head `d42088ef28a3f6b6bfb72b10318d270d11eea0e9`, above unchanged draft #200 and #199. Protected main was audited at `bc78660b5fac857fce3873eb6cda0445d1903da1`. All additions are confined to `research/scientific_understanding_v2/` and one experimental workflow. There is no deployment, model promotion, production-authority change or source-admission bypass.

Before testing, `preregistration.json` froze four project cases, revisions, source digests, the development/final split and evaluation conditions:

| Case | Source | Split |
| --- | --- | --- |
| Tyson1991 cell-cycle model | BioModels BIOMD0000000005 revision4; DOI10.1073/pnas.88.16.7328 | Development |
| SciPy Rosenbrock optimization | SciPy1.14.1 commit92d2a8592782ee19a1161d0bf3fc2241ba78bb63 | Development |
| Goldbeter1991 mitotic oscillator | BioModels BIOMD0000000003 revision3; DOI10.1073/pnas.88.20.9107 | Final |
| SciPy integration tutorial | Same pinned SciPy revision, different methods/results | Final |

These are four project cases from two resource families and three publications, not four independent experimental studies. Authentic SBML, upstream generated Octave code, documentation, code, metadata and reported findings are retained. The BioModels models contain CC0 notices. SciPy code/docs are BSD licensed and its2020 paper (DOI10.1038/s41592-019-0686-2) is CC BY. The full1991 biochemical papers are not redistributed without permission; attributed excerpts, publication links and retrieval provenance are retained. Numerical model inputs are not experimental biological measurements.

Separate AI agents read the original sources and authored 53 reference annotations without reading or running PCS extraction/check output:28 development,25 final. These are **AI-assisted independent internal annotations**, not human domain-expert or external validation. Source quotations and hashes are independently checked. They distinguish author-reported observations, model declarations, reviewer-derived consequences and counterclaims. The final labels/sources entered the integrated pipeline only after component/model/protocol freezes. No project or reference was used for model training.

## Implemented workflow

PR #201 supplies unchanged exact-byte intake, file adapters, source inventory, its existing PCS Claim IR/obligation graph, authenticated caching and base replay. New components add:

- Bounded nonexecuting arithmetic AST and MathML/SBML interpretation, parameters, initial quantities, reaction stoichiometry, document numbers/counts, uncertainty, conditions and ambiguity.
- A linked scientific sidecar graph with explicit source/dependency edges, independently executable check obligations, and blocking scientific-meaning review for every claim.
- Independent direct MathML checking, exact bounded rational-function normalization, and explicit nonzero-denominator obligations. Rational equivalence is on the common defined domain; it does not prove domain preservation or Python refinement.
- Exact stoichiometric left-nullspace certificates and concrete Lean checking; fixed-compartment volume weighting is explicit.
- Two-algorithm numerical ODE comparison with pinned SciPy1.15.3, and finite static comparison with the BioModels-generated Octave derivative expressions. The exported code is never executed. Because this export derives from SBML, it is not an independent biological source or full program-equivalence proof.
- Safe reconstruction of supported documentation examples using literal inputs and an approved mathematical kernel. Arbitrary doctest code is never run.
- A trained scientific source retriever, deterministic BM25/TFIDF baselines and a randomized-label control. Recommendations cannot set scientific meaning or checking authority.
- Portable evidence, cache-independent source/graph/check/display replay, and a real local ZIP-upload interface with explicit authorization, loopback/Host/Origin/token restrictions and manifest-bound file serving.

The format/semantic subsets are deliberately bounded. Missing physical units, undefined dependencies, unsupported SBML features, code statements, statistical models and ambiguous formulas cause abstention. The published optimization tutorial's unbracketed summation scope is not silently reinterpreted.

## Primary prospective evaluation

The primary implementation and evidence are preserved in commit `9e8a8f0`. The frozen protocol grades exact source grounding and typed slots against independent internal probes. Reported precision is **candidate/probe precision on annotated, targeted pairs**, not overall extraction precision or an externally adjudicated scientific error rate. Unannotated extractions are not silently counted correct. Some misses/mismatches reflect conservative schema, relation, unit and assumption alignment; their scientific significance needs expert adjudication.

| Case | Equations | Quantities | Checks replayed | Supported manual claims found | Targeted-pair precision | Workflow seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Tyson |11|18|41|6/12|6/16|2.458|
| Rosenbrock |74|53|202|0/9|0/10|2.404|
| Goldbeter, held out |9|17|36|1/10|1/4|1.838|
| Integration, held out |45|5|96|0/10|No targeted pairs|1.040|

Across the four cases:139 proposed equations,93 quantities,375 check executions and375 fresh cache-independent rechecks. Check statuses were63 supported scoped observations and312 unknowns; the original sources produced no refuted check. Separate adversarial cases produced actual contradictions. The supported statuses do not certify scientific meaning.

Supported manual-claim recall was6/21 development and1/20 final. Combined targeted-pair precision was7/30. The final result therefore fails any claim of broad reliable scientific interpretation. All individual matches, mismatches, missing conditions and abstentions are retained; no label was changed to make a result pass. Overall extraction precision remains unmeasured because the reference set does not exhaustively annotate every generated candidate.

All12 counterclaim/insufficient-evidence probes remained unpromoted. Absence of an accepted counterclaim is not a proof that every attack is detected. Every scientific meaning retains OPEN review and authority=false. Zero observed unsupported promotions is a finite result, supported by the gate design, not proof of universal safety.

Workflow wall times include intake, checking and review generation, excluding separate experimental grading/retrieval/replay. Peak parent RSS was64,504KiB, child high-water406,236KiB in these processes. High-water values are cumulative and not isolated per-case allocation measurements. CPU-only, local free resources; no external inference API charge or GPU result.

## Scientific computations and retained failures

For Tyson, independent exact parsing finds the conserved amount combination `C2 + CP + M + pM`, initially1. Its nine stoichiometric column dot products are exactly zero. A concrete source-bound Lean certificate checks the finite integer matrix and establishes cancellation for arbitrary matching integer reaction-rate vectors. The link from this algebra to differentiable real trajectories and biological applicability is not formally proved.

The reconstructed six-state Tyson model was integrated over model time0–10 at101 requested points. Radau(rtol1e-7,atol1e-10) and BDF(rtol1e-8,atol1e-11) differed by at most about9.21e-9; observed conserved-total drift was below4e-11. Twelve exact rational samples matched the supported scalar derivative expressions in the upstream generated export. These are finite computation/correspondence results, not global numerical-error bounds, full code proofs or empirical biology.

Three supported Nelder-Mead documentation examples were reconstructed without executing source/doctest code. The first reproduces339 iterations/571 function evaluations. A parameterized example gives318/522 in SciPy1.15.3 versus the documentation's319/525; iteration counts and print precision are explicitly version-sensitive. The whole tutorial remains PARTIAL because many other examples/meanings are unsupported. The held-out integration tutorial was UNSUPPORTED by this reconstruction subset; it was not simulated as successful.

The primary Goldbeter model-assurance result was UNKNOWN: its export contains an unsupported statement. A completed numerical calculation was lost when that subcheck raised. This generic evidence-retention defect was repaired, with a new authored regression test and explicitly **post-hoc** reruns in commit `a8189b2`. The first prospective result is retained unchanged. The repair does not change sources, reference labels, extraction semantics, learned weights or mathematical specifications.

In that post-hoc rerun, both algorithms reproduce the reconstructed three-state Goldbeter trajectory with maximum difference1.5576328907251913e-9. The export still remains UNKNOWN and overall model assurance still remains UNKNOWN; completed partial evidence is now inspectable. This is not a new untouched evaluation or reproduction of a published figure/experimental outcome.

## Learned experiment and baselines

A scratch scientific text dual encoder was actually trained:12,720 trainable parameters,40 CPU epochs, seed1729, train loss4.293→0.133, approximately8.4seconds, finite JSON checkpoint378,780bytes. It uses96 authored training,24 validation and24 untouched test examples split by wording family before training. A shuffled-label checkpoint is retained. No imported project/reference became training data, and no trained source file uses proof-generation traces.

Authored test top1/MRR: BM25 and TFIDF1.0/1.0; neural0.7083/0.7935; shuffled labels0.4167/0.5544. Pure Python inference agrees with Torch to maximum absolute error5.39e-8. Architecture/epochs were not retuned after the test.

On real source relevance, including false-question queries, top1 was:

| Case | BM25 | TFIDF | Neural |
| --- | ---: | ---: | ---: |
| Tyson |6/15|8/15|1/15|
| Rosenbrock |3/13|5/13|1/13|
| Goldbeter final |5/12|2/12|0/12|
| Integration final |2/13|0/13|0/13|

Source relevance is not scientific correctness. These results support deterministic retrieval as the current default and provide no neural superiority or transfer finding. Frozen Proof-JEPA and Safety-JEPA components remain untouched; their proof/tool-state weights are not treated as compatible scientific-language models. No new JEPA/RL performance claim is made.

## Formal results

All compile with Lean4.28.0, `-j1 -M512`, with actual source/compiler/library bindings and axiom reports. No sorry/admit, new axioms or unsafe shortcuts are introduced.

`ScientificDimensions` (nine, empty axiom lists): `check_sound`, `check_complete`, `undeclared_symbol_untypable`, `dimension_unique`, `research_has_no_authority`, `nat_mul_assoc_constructive`, `nat_product_reorder`, `scale_multiplicative_compatibility`, `minutes_to_seconds_exact`.

`ScientificConservation` (nine, standard `propext` only): `dot_zero_vector`, `add_vector_length`, `dot_add`, `dot_scale`, `null_columns_have_shape`, `linear_combination_length`, `dot_linear_combination`, `conserved_weighted_flux`, `conserved_linear_combination`.

`ScientificSampling` (three, empty axiom lists): `sampling_zeros`, `ghost_fifty_nonzero`, `sample_agreement_does_not_imply_global_equality`.

The dimensional proofs concern an abstract expression-typing specification and exact scale model; the specification is not a deployed Lean authority or a proved compiler refinement. Conservation concerns finite integer algebra with explicit shapes. Sampling proves the known limitation of finite equality testing using `ghost(x)=∏_{i=1..12}(x-i)`: it vanishes on the twelve samples and not at50. Scaling relates this example to rational samples i/100 and1/2, without proving the Python bridge.

These are useful new PCS assurance capabilities and independently checked mathematical consequences, not claims of new foundational mathematics or scientific discovery.

## Adversarial and engineering evidence

A concrete polynomial perturbation agrees with an expression at all12 fixed rational samples and differs at1/2. The new exact rational normal form detects it, while a sample-only check would miss it. Its source/candidate/witness and the related Lean theorem are retained. Nonzero denominator obligations remain open; normal-form code is not kernel-proved.

The finite campaign also detects altered generated model code, an altered reported objective, incorrect units, malicious uploaded code and misleading causal prose. Exact input/output traces and independent replay are retained. Separate regression tests cover duplicate/foreign model identifiers and namespaces, undeclared/constant assignment targets, unsupported semantics, malformed/ambiguous inputs, arithmetic resource growth, manifest re-sign forgeries, dropped checks, falsified scientific meaning, private-cache behavior and actual HTTP boundaries.

Independent internal code review found scratch leakage on worker termination. Parent-owned temporary storage and process-group cleanup now cover worker and Lean children; budgets remain fail-closed. No OS sandbox, immutable root, secret-backed external verifier identity or hostile-host protection is claimed. HMAC/private directories assume host integrity.

The final local combined run passed **277 tests and168 subtests**:125 new-stage tests plus the unchanged152-test intake suite. One earlier parent-suite failure was a missing sparse-checkout fixture, restored from unchanged Git content; no parent test was weakened. Repository-integrity checks and all new formal profiles pass. The initial development run whose source context changed during proof-harness completion is retained as invalidated, not counted as a successful experiment.

## Reproduction and adoption

`README.md` gives upload/CLI, dependency, training and benchmark commands. `learning/MODEL_CARD.md` records checkpoint provenance and limitations. Primary and post-hoc frozen results/packages have separate names under `evidence/`; historical evidence is never overwritten. Replay the primary artifacts using primary source commit `9e8a8f0`; replay post-hoc artifacts using the corresponding successor source context. A context mismatch must not be bypassed.

The local upload/review flow has seven real HTTP integration tests, including nonexecution and access checks. It has no human usability study or public-service qualification. Supported computations and source quotes are inspectable, but an unfamiliar project's scientific judgment is not automated reliably.

Current readiness: a technical research prototype for source-linked mathematical/model consistency checks with human review. Not ready to certify arbitrary papers, empirical claims or production scientific understanding. Production adoption still requires reviewed source admission, Python/Lean refinement work, stronger isolation, human domain-expert annotation/adjudication and external replication.

The highest-value next experiment is to adjudicate the annotation/type-contract mismatches with qualified domain experts, improve interpretation against a development set, and freeze a **fresh** prospective corpus with genuinely independent measurements and analysis code. Reusing this exposed final set as a new claim of generalization would be invalid. Additional model complexity is not justified by the current evidence.
