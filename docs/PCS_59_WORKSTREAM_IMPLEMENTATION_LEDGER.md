# PCS59-workstream implementation ledger

All59 acceptance boundaries start from independently refreshed protected core fd4ddaf, website72a47c9 and CertiForgec71e857. Historical starting revisions and executed research remain preserved. New continuation source has local execution evidence and still requires protected CI. No status grants scientific authority.

Status counts: 3 BLOCKED, 5 COMPLETE_TESTED, 51 PARTIAL.

Zero independent external human reviewers or participants and zero financial spend. Provider fixtures, actual hosted jobs, local kernel replay, formal model proofs and production metadata are distinct evidence classes.

## Task 1 — Establish a reproducible technical baseline

**Status: PARTIAL.**

Acceptance: A fresh checkout and documented environment can reproduce the required results, and every exception or environment dependency is recorded.

Implementation: Protected core full-suite 1519 passes/10 optional skips; mandatory learning lane 114 passes; exact tested and merged trees agree.

Tests: 21 passed; no missing gate promoted; 1,409 passed/10 setup failures first run; 17 module tests passed after correction; all tracked source unchanged; Protected core full-suite 1519 passes/10 optional skips; mandatory learning lane 114 passes; exact tested and merged trees agree.

Evidence: `scripts/verify_lean.sh`, `.github/workflows/pcs-public-full-verification.yml`, `docs/evidence/platform-baseline-v1/qualification-focused-final.log`, `docs/evidence/platform-baseline-v1/frozen-python-baseline.json`, `docs/evidence/platform-baseline-v1/frozen-reproduction-correction.json`, `docs/evidence/protected-platform-release-v1/core-protected-release.json`

Remaining: Fresh future environment restoration not tested; optional skips remain explicit.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 2 — Complete actual hosted Lean execution

**Status: COMPLETE_TESTED.**

Acceptance: At least ten repeatable real jobs terminate with accurate verified, unknown, failure, or resource-exhaustion outcomes, with no forged or incomplete results accepted.

Implementation: Ten actual source-bound owner hosted jobs completed with correct verified/unknown/ambiguous/unsupported/rejected outcomes; independently replayed proofs and counterexample. One separate live normal-quota proof also completed.

Tests: Ten actual source-bound owner hosted jobs completed with correct verified/unknown/ambiguous/unsupported/rejected outcomes; independently replayed proofs and counterexample. One separate live normal-quota proof also completed.

Evidence: `pcs/experimental/prover/public_job.py`, `pcs/experimental/prover/public_transport.py`, `docs/evidence/protected-platform-release-v1/hosted-ten-diagnostics-summary.json`

Remaining: Bounded owner operational matrix, not ten public admissions or a blind scientific benchmark. Provider is part of remote execution trust boundary.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 3 — Implement robust job lifecycle and recovery

**Status: PARTIAL.**

Acceptance: Restart, retry, race, and duplicate-request tests preserve one coherent authoritative request outcome.

Implementation: Added bounded provider readiness before admission; repeated readiness before POST separates definite not-sent/declined outcomes from uncertainty. Persistent SQLite restart and20-way races retain one admission/dispatch.

Tests: Nine local tests; actual SQLite restart; 20 timestamp races and ten cancellation attempts; Added bounded provider readiness before admission; repeated readiness before POST separates definite not-sent/declined outcomes from uncertainty. Persistent SQLite restart and20-way races retain one admission/dispatch.

Evidence: `src/lean-research.js`, `docs/PCS_PROVIDER_RECOVERY_V2.md`

Remaining: Actual transport preflight passed; failure/race campaign uses provider fixtures. Production process crash injection remains unperformed.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 4 — Implement end-to-end observability

**Status: PARTIAL.**

Acceptance: A failed public research request can be diagnosed from bounded, privacy-safe logs without guessing where execution stopped.

Implementation: New readiness returns fixed privacy-safe diagnostics; signed job stage events already validated on ten hosted controls and live proof.

Tests: 21 passed; no missing gate promoted; New readiness returns fixed privacy-safe diagnostics; signed job stage events already validated on ten hosted controls and live proof.

Evidence: `pcs/experimental/prover/memory_environment.py`, `docs/evidence/platform-baseline-v1/qualification-focused-final.log`, `docs/PCS_PROVIDER_RECOVERY_V2.md`

Remaining: No complete concurrent process-tree observability or production failure-injection guarantee.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 5 — Strengthen resource-exhaustion handling

**Status: PARTIAL.**

Acceptance: Negative tests consistently return bounded and accurately classified failures.

Implementation: Bounded6-second metadata/POST deadlines and32KiB metadata; known rejection is failed, uncertainPOST is preserved for polling. Hosted one-expansion control returned UNKNOWN.

Tests: 21 passed; no missing gate promoted; Bounded6-second metadata/POST deadlines and32KiB metadata; known rejection is failed, uncertainPOST is preserved for polling. Hosted one-expansion control returned UNKNOWN.

Evidence: `pcs/experimental/prover/memory_wire.py`, `docs/evidence/platform-baseline-v1/qualification-focused-final.log`, `docs/PCS_PROVIDER_RECOVERY_V2.md`

Remaining: Actual hosted wall-limit kill/cancellation campaign not rerun; no resource outcome is proof success.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 6 — Verify deployed core revision and evidence bindings

**Status: COMPLETE_TESTED.**

Acceptance: Changing any authority-critical bound field causes the corresponding verification to fail.

Implementation: Exact protected core pin, negative binding tests, ten byte-identical deployed assets and actual remote/local replay bound to the immutable theorem.

Tests: Exact protected core pin, negative binding tests, ten byte-identical deployed assets and actual remote/local replay bound to the immutable theorem.

Evidence: `pcs/experimental/prover/public_transport.py`, `docs/evidence/protected-platform-release-v1/cloudflare-platform-live-assets.json`

Remaining: One qualified deployment; no universal guarantee over future releases or infrastructure compromise.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 7 — Implement comprehensive failure injection

**Status: PARTIAL.**

Acceptance: Every security-critical failure mode is rejected without silently promoting an invalid result.

Implementation: Source drift, missing/forged gates, malformed records, independent scientific false-report replay and browser authorization failures exercised.

Tests: 21 passed; no missing gate promoted

Evidence: `tests/test_public_proof_transport.py`, `docs/evidence/platform-baseline-v1/qualification-focused-final.log`

Remaining: Hosted job-state/provider failure campaign remains separate from these local controls.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 8 — Create a complete release qualification gate

**Status: PARTIAL.**

Acceptance: Critical release failures block promotion, and a qualified release produces an independently inspectable evidence record.

Implementation: All protected core/site/CertiForge gates passed; exact merged feature trees and owner identity checked; no privileged bypass.

Tests: 21 passed; no missing gate promoted; All protected core/site/CertiForge gates passed; exact merged feature trees and owner identity checked; no privileged bypass.

Evidence: `pcs/release_qualification_v1.py`, `docs/evidence/platform-baseline-v1/qualification-focused-final.log`, `docs/evidence/protected-platform-release-v1/core-protected-release.json`

Remaining: Local release JSON is unsigned; external supply-chain attestation and fresh environment restoration remain open.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 9 — Complete external-project adapters

**Status: PARTIAL.**

Acceptance: An unfamiliar public/synthetic scientific workflow can be mapped, reviewed, confirmed, attested, and independently replayed.

Implementation: New generic typed external scientific workflow runs real CC0 PalmerPenguins data through existing signed PCS bundle and independent receiving processes.

Tests: 37 focused tests passed; three fresh scientific receiver processes; eight bounded numerical predicates PASS; New generic typed external scientific workflow runs real CC0 PalmerPenguins data through existing signed PCS bundle and independent receiving processes.

Evidence: `pcs/workflow_discovery_v06.py`, `research/scientific-assurance-v1/SUMMARY.json`, `research/scientific-assurance-v1/ARTIFACT_SHA256.json`, `docs/PCS_SCIENTIFIC_WORKSTREAM_REPORT.md`, `docs/PCS_SCIENTIFIC_WORKFLOW_V2_REPORT.md`

Remaining: Only versioned bounded length-to-mass linear calibration; no unrestricted arbitrary workflow execution or scientific adequacy.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 10 — Expand Claim IR and Proof Obligation Graph

**Status: PARTIAL.**

Acceptance: Every formal outcome has a complete, machine-readable chain to the exact originating scientific claim, evidence, and assumptions.

Implementation: Workflow obligations include measurement-byte identity, complete-case filtering, unit conversion, finite computation and empirical applicability; changed data or premises invalidate descendants.

Tests: 37 focused tests passed; three fresh scientific receiver processes; eight bounded numerical predicates PASS; Workflow obligations include measurement-byte identity, complete-case filtering, unit conversion, finite computation and empirical applicability; changed data or premises invalidate descendants.

Evidence: `pcs/scientific_obligations_v1.py`, `research/scientific-assurance-v1/SUMMARY.json`, `research/scientific-assurance-v1/ARTIFACT_SHA256.json`, `docs/PCS_SCIENTIFIC_WORKSTREAM_REPORT.md`, `docs/PCS_SCIENTIFIC_WORKFLOW_V2_REPORT.md`

Remaining: General inference over unfamiliar scientific claims remains unsupported/OPEN.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 11 — Automate complete scientific evidence packaging

**Status: PARTIAL.**

Acceptance: A fresh independent environment can verify the delivered bundle without access to the producer's private state.

Implementation: Actual real-data signed bundle, public key, source/license bindings and four fresh receiving processes; false report and FALSIFIED dimension do not become bounded success.

Tests: 37 focused tests passed; three fresh scientific receiver processes; eight bounded numerical predicates PASS; Actual real-data signed bundle, public key, source/license bindings and four fresh receiving processes; false report and FALSIFIED dimension do not become bounded success.

Evidence: `pcs/package_v06.py`, `research/scientific-assurance-v1/SUMMARY.json`, `research/scientific-assurance-v1/ARTIFACT_SHA256.json`, `docs/PCS_SCIENTIFIC_WORKSTREAM_REPORT.md`, `docs/PCS_SCIENTIFIC_WORKFLOW_V2_REPORT.md`

Remaining: Package integrity is distinct from claim support; empirical/numerical claims remain OPEN under PCS authority.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 12 — Implement useful unsupported-claim analysis

**Status: PARTIAL.**

Acceptance: Unsupported claims remain explicitly OPEN and receive useful, nonmisleading diagnostics.

Implementation: Unsupported/missing-domain claims return OPEN with explicit diagnostic proposals; clinical control stays unsupported.

Tests: 37 focused tests passed; three fresh scientific receiver processes; eight bounded numerical predicates PASS

Evidence: `pcs/limitations.py`, `research/scientific-assurance-v1/SUMMARY.json`, `research/scientific-assurance-v1/ARTIFACT_SHA256.json`, `docs/PCS_SCIENTIFIC_WORKSTREAM_REPORT.md`

Remaining: Advice is lexical/typed scoped behavior, not a general certified English interpretation.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 13 — Expand domain-specific scientific verification

**Status: PARTIAL.**

Acceptance: PCS verifies several nontrivial, clearly scoped properties of an unfamiliar computational-science workflow.

Implementation: Added actual344-record measurement workflow,342completepairs, exact rational calibration and independent NumPy least-squares baseline.

Tests: 37 focused tests passed; three fresh scientific receiver processes; eight bounded numerical predicates PASS; Added actual344-record measurement workflow,342completepairs, exact rational calibration and independent NumPy least-squares baseline.

Evidence: `pcs/adapters/pkpd.py`, `research/scientific-assurance-v1/SUMMARY.json`, `research/scientific-assurance-v1/ARTIFACT_SHA256.json`, `docs/PCS_SCIENTIFIC_WORKSTREAM_REPORT.md`, `docs/PCS_SCIENTIFIC_WORKFLOW_V2_REPORT.md`

Remaining: Finite numerical agreement is not biological/causal/population validity; no general scientific acceptance.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 14 — Integrate independent reviewer feedback

**Status: BLOCKED.**

Acceptance: Reviewer concerns can be recorded, traced, and resolved without rewriting the historical evidence.

Implementation: Append-only evidence-bound reviewer proposal revisions and existing policy passthrough preserved.

Tests: 37 focused tests passed; three fresh scientific receiver processes; eight bounded numerical predicates PASS

Evidence: `pcs/external_validator_v06.py`, `research/scientific-assurance-v1/SUMMARY.json`, `research/scientific-assurance-v1/ARTIFACT_SHA256.json`, `docs/PCS_SCIENTIFIC_WORKSTREAM_REPORT.md`

Remaining: Zero independently authenticated external reviewers participated; fixture IDs do not authorize training.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 15 — Expand controlled English-to-Lean

**Status: PARTIAL.**

Acceptance: New independently authored meaning fixtures successfully formalize, elaborate, and undergo independent semantic review.

Implementation: Existing restricted grammar, typed lowering and learned formalization/search interfaces retained; parser parity and recursion regressions rerun.

Tests: No new capability execution inferred from protected merge.

Evidence: `pcs/experimental/prover/language.py`

Remaining: No newly trained broad English-to-Lean model or unrestricted meaning-preservation claim.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 16 — Implement stronger bidirectional semantic checking

**Status: PARTIAL.**

Acceptance: The system detects and reports semantic inconsistencies on a meaningful suite of independently authored examples.

Implementation: Restricted typed round-trip and semantic reference theorems freshly audited; original exact source grounding preserved.

Tests: No new capability execution inferred from protected merge.

Evidence: `pcs/semantic_translation_v1.py`

Remaining: General English explanation equivalence and implementation-wide parser correspondence remain unproved.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 17 — Improve ambiguity detection and abstention

**Status: PARTIAL.**

Acceptance: Ambiguous inputs produce reviewable alternatives or abstention rather than unreviewed certification.

Implementation: Existing ambiguity/unsupported abstention retained; deep input rejects without uncaught recursion.

Tests: No new capability execution inferred from protected merge.

Evidence: `pcs/experimental/prover/language.py`

Remaining: Broader linguistic ambiguity corpus and independent human fidelity review remain unperformed.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 18 — Integrate actual Mathlib retrieval

**Status: PARTIAL.**

Acceptance: PCS uses genuine external Mathlib declarations to solve unfamiliar mathematical problems beyond its authored elementary proof catalogs.

Implementation: Historical6-task Mathlib experiment completed; four additional actual Mathlib states roundtrip inDAG,2 retrieved proofs fresh-replayed and2UNKNOWN.

Tests: Frozen144 comparisons completed and audited; full measured results in PCS_GENERALIZATION_AND_LEARNING_EVALUATION.md. No neural/RL gain inferred.; Historical6-task Mathlib experiment completed; four additional actual Mathlib states roundtrip inDAG,2 retrieved proofs fresh-replayed and2UNKNOWN.

Evidence: `pcs/experimental/prover/library.py`, `research/prospective-hybrid-v2/protocol.json`, `research/prospective-hybrid-v2/summary.json`, `research/abstraction-repair-v2/protocol.json`, `docs/PCS_DAG_POLICY_V3_REPORT.md`

Remaining: Learned policy still lacks a rich receiver-controlled Mathlib action catalog; diagnostics are authored and symbolic, not blind transfer.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 19 — Improve structured proof-state representations

**Status: PARTIAL.**

Acceptance: Actual model features derive from real Lean states, and improvements are evaluated against appropriate ablations.

Implementation: Real Lean expression DAG now feeds a6099-parameter trainable policy with child-position/binder/role edges.20epochs39verifiedtransitions changed actual message/edge/update weights.

Tests: Frozen144 comparisons completed and audited; full measured results in PCS_GENERALIZATION_AND_LEARNING_EVALUATION.md. No neural/RL gain inferred.; Real Lean expression DAG now feeds a6099-parameter trainable policy with child-position/binder/role edges.20epochs39verifiedtransitions changed actual message/edge/update weights.

Evidence: `pcs/experimental/prover/environment.py`, `research/prospective-hybrid-v2/protocol.json`, `research/prospective-hybrid-v2/summary.json`, `research/abstraction-repair-v2/protocol.json`, `docs/PCS_DAG_POLICY_V3_REPORT.md`

Remaining: DAG4/12 trails symbolic5/12 and Std12/12; representation accuracy is not neural superiority.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 20 — Strengthen verified-memory discovery

**Status: PARTIAL.**

Acceptance: PCS automatically proposes and admits useful intermediate lemmas that improve unseen proof-search performance beyond trivial theorem memorization.

Implementation: Counterexample-guided scoped abstraction-repair experiment extends existing checked cut/memory admission.

Tests: Frozen144 comparisons completed and audited; full measured results in PCS_GENERALIZATION_AND_LEARNING_EVALUATION.md. No neural/RL gain inferred.

Evidence: `pcs/experimental/prover/abstraction_experiment.py`, `research/prospective-hybrid-v2/protocol.json`, `research/prospective-hybrid-v2/summary.json`, `research/abstraction-repair-v2/protocol.json`

Remaining: No mathematical novelty claim; exact utility/final transfer outcomes must come from completed sealed experiment.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 21 — Improve typed anti-unification and generalization

**Status: PARTIAL.**

Acceptance: Some genuine proposed generalizations survive independent Lean checking and prove useful on held-out problems.

Implementation: Typed anti-unification and scoped repaired proposal admission implemented with fresh kernel checks.

Tests: Frozen144 comparisons completed and audited; full measured results in PCS_GENERALIZATION_AND_LEARNING_EVALUATION.md. No neural/RL gain inferred.

Evidence: `pcs/experimental/prover/memory_discovery.py`, `research/prospective-hybrid-v2/protocol.json`, `research/prospective-hybrid-v2/summary.json`, `research/abstraction-repair-v2/protocol.json`

Remaining: Broader principal anti-unification theory and discovered-mathematics novelty remain unsupported.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 22 — Optimize verified-memory utility

**Status: PARTIAL.**

Acceptance: A selected memory configuration demonstrates reproducible practical value under a frozen evaluation protocol.

Implementation: Frozen memory utility protocols and cost/resource receipts retained; separate amortization experiment staged.

Tests: Frozen144 comparisons completed and audited; full measured results in PCS_GENERALIZATION_AND_LEARNING_EVALUATION.md. No neural/RL gain inferred.

Evidence: `pcs/experimental/prover/memory_experiment.py`, `research/prospective-hybrid-v2/protocol.json`, `research/prospective-hybrid-v2/summary.json`, `research/abstraction-repair-v2/protocol.json`

Remaining: Small paired utility results cannot imply submodularity, global optimum or universal efficiency.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 23 — Develop hybrid symbolic-neural search

**Status: PARTIAL.**

Acceptance: A hybrid system is implemented with reproducible component ablations and measurable performance, without attributing symbolic successes to the neural policy.

Implementation: Existing hybrid portfolio remains stable. New DAG/bag policies plug into existing checked memory_search with bounded JSON checkpoint and saved-checkpoint CLI.

Tests: Frozen144 comparisons completed and audited; full measured results in PCS_GENERALIZATION_AND_LEARNING_EVALUATION.md. No neural/RL gain inferred.; Existing hybrid portfolio remains stable. New DAG/bag policies plug into existing checked memory_search with bounded JSON checkpoint and saved-checkpoint CLI.

Evidence: `pcs/experimental/prover/memory_search.py`, `research/prospective-hybrid-v2/protocol.json`, `research/prospective-hybrid-v2/summary.json`, `research/abstraction-repair-v2/protocol.json`, `docs/PCS_DAG_POLICY_V3_REPORT.md`

Remaining: Symbolic/Std remains stronger; new inferior checkpoints are experimental and not promoted.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 24 — Improve induction strategy selection

**Status: PARTIAL.**

Acceptance: PCS solves additional independently authored induction problems beyond those already supported, with exact verified proofs.

Implementation: Existing real under-hypothesis induction actions retained; typed successor/recurrence search compared with symbolic and Std policies.

Tests: Frozen144 comparisons completed and audited; full measured results in PCS_GENERALIZATION_AND_LEARNING_EVALUATION.md. No neural/RL gain inferred.

Evidence: `pcs/experimental/prover/induction_environment.py`, `research/prospective-hybrid-v2/protocol.json`, `research/prospective-hybrid-v2/summary.json`, `research/abstraction-repair-v2/protocol.json`

Remaining: Learned induction strategy improvement requires completed untouched evaluation, not task repetition.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 25 — Implement counterexample-guided proof repair

**Status: PARTIAL.**

Acceptance: PCS repairs a reproducible set of previously failed proofs without increasing unsound acceptance.

Implementation: Actual bounded counterexamples guide explicit separate abstraction repairs without mutating original goals.

Tests: Frozen144 comparisons completed and audited; full measured results in PCS_GENERALIZATION_AND_LEARNING_EVALUATION.md. No neural/RL gain inferred.

Evidence: `pcs/proof_repair_v06.py`, `research/prospective-hybrid-v2/protocol.json`, `research/prospective-hybrid-v2/summary.json`, `research/abstraction-repair-v2/protocol.json`

Remaining: Not unrestricted conjecture repair or a permission to silently strengthen assumptions.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 26 — Improve genuine reinforcement learning

**Status: PARTIAL.**

Acceptance: Training runs are reproducible, sequential, and independently verified; promotion requires measured held-out performance rather than mere successful gradient updates.

Implementation: Eight real sequential DAG actor-critic episodes produced seven independently replayed positive terminals and one invalid episode; updated checkpoint saved. Fresh4-task supervised/RL/symbolic all2/4, Std4/4.

Tests: Frozen144 comparisons completed and audited; full measured results in PCS_GENERALIZATION_AND_LEARNING_EVALUATION.md. No neural/RL gain inferred.; Eight real sequential DAG actor-critic episodes produced seven independently replayed positive terminals and one invalid episode; updated checkpoint saved. Fresh4-task supervised/RL/symbolic all2/4, Std4/4.

Evidence: `pcs/experimental/prover/memory_experiment.py`, `research/prospective-hybrid-v2/protocol.json`, `research/prospective-hybrid-v2/summary.json`, `research/abstraction-repair-v2/protocol.json`, `docs/PCS_DAG_POLICY_V3_REPORT.md`

Remaining: One seed, small authored split, no RL improvement or self-improvement claim; checkpoints not promoted.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 27 — Implement strict model promotion gates

**Status: PARTIAL.**

Acceptance: The default system cannot be replaced by an inferior or unverified candidate without an explicit authorized override.

Implementation: Implemented stricter source/dataset/evaluator-bound promotion metadata, exposure bookkeeping and fail-closed decision controls.

Tests: Frozen144 comparisons completed and audited; full measured results in PCS_GENERALIZATION_AND_LEARNING_EVALUATION.md. No neural/RL gain inferred.

Evidence: `pcs/experimental/prover/promotion.py`, `research/prospective-hybrid-v2/protocol.json`, `research/prospective-hybrid-v2/summary.json`, `research/abstraction-repair-v2/protocol.json`

Remaining: No checkpoint automatically acquires production authority; independent gate integration and full adaptive statistical protocol remain required.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 28 — Build serious independent benchmarks

**Status: PARTIAL.**

Acceptance: Independent researchers can rerun the comparisons and interpret the results without relying on claims in a summary document.

Implementation: Frozen12challenge structures,36matched action-search comparisons; separate stronger Std12/12. Four additional frozen RL finaltasks and independent Mathlib diagnostics preserve costs/negative results.

Tests: Frozen144 comparisons completed and audited; full measured results in PCS_GENERALIZATION_AND_LEARNING_EVALUATION.md. No neural/RL gain inferred.; Frozen12challenge structures,36matched action-search comparisons; separate stronger Std12/12. Four additional frozen RL finaltasks and independent Mathlib diagnostics preserve costs/negative results.

Evidence: `research/verified-memory-v1/protocol.json`, `research/prospective-hybrid-v2/protocol.json`, `research/prospective-hybrid-v2/summary.json`, `research/abstraction-repair-v2/protocol.json`, `docs/PCS_DAG_POLICY_V3_REPORT.md`

Remaining: Author-known public mathematics, not private blind or externally authored evaluation; semantic near-duplicates not exhaustively excluded.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 29 — Complete conditional-checker refinement

**Status: BLOCKED.**

Acceptance: Additional real production operations are covered by auditable source-bound refinement theorems with explicit assumptions.

Implementation: Existing decision-diagram reference proofs and extracted arithmetic preserved; actual Python/JavaScript/Lean comparisons expanded.

Tests: 54 principal audit entries; four new Value::ty proofs; five canonical-input controls; 1,618 expanded comparisons zero mismatches

Evidence: `research/aristotle-runtime-refinement-v1/REPORT.md`, `docs/evidence/platform-baseline-v1/runtime-refinement.json`, `docs/evidence/platform-baseline-v1/value-type-refinement.json`, `docs/evidence/platform-baseline-v1/runtime-differential-512.json.gz`, `docs/PCS_FORMAL_ASSURANCE_AND_REFINEMENT_REPORT.md`

Remaining: Principal python_conditional_refines_reference and javascript_conditional_refines_reference remain open; unsupported runtime constructs not replaced by a weaker proof.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 30 — Extend formalization parser refinement

**Status: PARTIAL.**

Acceptance: The supported parser fragment has stronger demonstrated source-to-specification correspondence, and unsupported cases fail safely.

Implementation: Fresh restricted parser theorem audit, 1,523 runtime parity cases and depth-995 fail-closed regressions executed.

Tests: 54 principal audit entries; four new Value::ty proofs; five canonical-input controls; 1,618 expanded comparisons zero mismatches

Evidence: `pcs/experimental/prover/language.py`, `docs/evidence/platform-baseline-v1/runtime-refinement.json`, `docs/evidence/platform-baseline-v1/value-type-refinement.json`, `docs/evidence/platform-baseline-v1/runtime-differential-512.json.gz`, `docs/PCS_FORMAL_ASSURANCE_AND_REFINEMENT_REPORT.md`

Remaining: English rewriting, JSON/text decoding and whole actual parser-source refinement remain open.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 31 — Expand CertiForge formal refinement

**Status: PARTIAL.**

Acceptance: More of CertiForge's real checker and optimizer behavior is connected to explicit Lean theorems, with source revision binding and independent differential validation.

Implementation: Exact current Rust checked-wrapper source fragment has17fresh kernel theorems: canonicality, iterator/early-return contract, guard order independence, expression refinement and certificate composition.31native checks and2mutated-source kernel rejections passed.

Tests: 54 principal audit entries; four new Value::ty proofs; five canonical-input controls; 1,618 expanded comparisons zero mismatches; Exact current Rust checked-wrapper source fragment has17fresh kernel theorems: canonicality, iterator/early-return contract, guard order independence, expression refinement and certificate composition.31native checks and2mutated-source kernel rejections passed.

Evidence: `pcs/certiforge_adapter_v1.py`, `docs/evidence/platform-baseline-v1/runtime-refinement.json`, `docs/evidence/platform-baseline-v1/value-type-refinement.json`, `docs/evidence/platform-baseline-v1/runtime-differential-512.json.gz`, `docs/PCS_FORMAL_ASSURANCE_AND_REFINEMENT_REPORT.md`, `docs/PCS_RUNTIME_CHECKED_BOUNDARY_REPORT.md`

Remaining: Compiler/HashMap implementation/top-level eval/type-checker and whole Python/JS conditional source correspondence remain unproved.

Prior protected release: c71e8575db2800b015a9d444f8ed572490f3a871 — https://github.com/Tommaso-R-Marena/certiforge/pull/3

## Task 32 — Formalize learning-runtime safety invariants

**Status: PARTIAL.**

Acceptance: Additional learning-system correctness boundaries are formalized, and any claimed runtime guarantees have explicit implementation evidence.

Implementation: Actual sequential rewards remain environment/kernel-derived; seven positive terminals independently replayed. Tampered checkpoint/actions rejected; theorem statements stay immutable.

Tests: 54 principal audit entries; four new Value::ty proofs; five canonical-input controls; 1,618 expanded comparisons zero mismatches; Actual sequential rewards remain environment/kernel-derived; seven positive terminals independently replayed. Tampered checkpoint/actions rejected; theorem statements stay immutable.

Evidence: `formal/PCSVerifiedMemoryBoundary.lean`, `docs/evidence/platform-baseline-v1/runtime-refinement.json`, `docs/evidence/platform-baseline-v1/value-type-refinement.json`, `docs/evidence/platform-baseline-v1/runtime-differential-512.json.gz`, `docs/PCS_FORMAL_ASSURANCE_AND_REFINEMENT_REPORT.md`, `docs/PCS_DAG_POLICY_V3_REPORT.md`

Remaining: Learning runtime has bounded tested invariants; broad source-bound Python learning-runtime refinement remains open.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 33 — Strengthen cryptographic and serialization assurance

**Status: PARTIAL.**

Acceptance: Critical serialization and authentication invariants have reproducible positive/negative evidence and, where feasible, formal correspondence results.

Implementation: Added real authenticated Ed25519 signing policy, trusted observation, expiry/rotation/compromise and exact-object binding controls; existing canonical primitives preserved.

Tests: 44 focused tests and 17 real cryptographic drill controls passed

Evidence: `pcs/canonical_json.py`, `pcs/receipt_signature_v06.py`, `research/platform-security-v1/signing-recovery.json`, `docs/SIGNING_POLICY_AND_RECOVERY_V1.md`

Remaining: No formal Ed25519/Python/clock/custody proof or production-root rollout is asserted.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 34 — Expand differential testing

**Status: COMPLETE_TESTED.**

Acceptance: The framework finds or rules out mismatches within explicitly defined tested domains, without representing testing as a general proof of equivalence.

Implementation: Executed 1,618 expanded native/Python/JavaScript/Lean comparisons with zero mismatches; release smoke and deliberate historical mismatch shrinking controls retained.

Tests: 54 principal audit entries; four new Value::ty proofs; five canonical-input controls; 1,618 expanded comparisons zero mismatches

Evidence: `research/aristotle-runtime-refinement-v1/REPORT.md`, `docs/evidence/platform-baseline-v1/runtime-refinement.json`, `docs/evidence/platform-baseline-v1/value-type-refinement.json`, `docs/evidence/platform-baseline-v1/runtime-differential-512.json.gz`, `docs/PCS_FORMAL_ASSURANCE_AND_REFINEMENT_REPORT.md`

Remaining: Finite typed-domain testing, not universal equivalence; error-format normalization and JSON/hash authority exclusions explicit.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 35 — Validate end-to-end onboarding

**Status: PARTIAL.**

Acceptance: Independent testers can complete the workflow, and unauthorized privilege changes are rejected.

Implementation: Actual isolated browser account onboarding/manual review/task/submission flow exercised with local verification fixtures.

Tests: 33 real Worker/browser controls; five Node and five Python focused tests; actual synthetic game replay/training/withdrawal; populated local backup/restore

Evidence: `src/worker.js`, `docs/PCS_PLATFORM_WORKSTREAM_REPORT.md`, `docs/evidence/platform-governance-v1/ARTIFACT_SHA256.json`

Remaining: No real external user, email delivery or independent assessment participated.

Prior protected release: 72a47c92d47c93249b6c8b9ec0dc70b95232f48c — https://github.com/Tommaso-R-Marena/proof-carrying-science-site/pull/116

## Task 36 — Strengthen GitHub-backed contribution integration

**Status: PARTIAL.**

Acceptance: A valid low-risk contribution can be integrated through the documented process, and forged or unauthorized promotion attempts fail.

Implementation: Preserved GitHub artifact/owner/protected promotion integration and exact source-gate behavior; frozen contribution tests all pass after canonical checkout setup.

Tests: No new capability execution inferred from protected merge.

Evidence: `src/contribution-github.js`

Remaining: A new live contributor-authored GitHub low-risk merge was not performed in this campaign.

Prior protected release: 72a47c92d47c93249b6c8b9ec0dc70b95232f48c — https://github.com/Tommaso-R-Marena/proof-carrying-science-site/pull/116

## Task 37 — Complete scientific task taxonomy

**Status: PARTIAL.**

Acceptance: A newcomer can select a task and understand exactly what constitutes successful completion.

Implementation: Existing scientific task catalog retained; real eligible task intake and skill boundaries validated.

Tests: 33 real Worker/browser controls; five Node and five Python focused tests; actual synthetic game replay/training/withdrawal; populated local backup/restore

Evidence: `src/worker.js`, `docs/PCS_PLATFORM_WORKSTREAM_REPORT.md`, `docs/evidence/platform-governance-v1/ARTIFACT_SHA256.json`

Remaining: Complete scientific taxonomy and newcomer comprehension are not established by fixture automation.

Prior protected release: 72a47c92d47c93249b6c8b9ec0dc70b95232f48c — https://github.com/Tommaso-R-Marena/proof-carrying-science-site/pull/116

## Task 38 — Improve task dependencies and review tracking

**Status: PARTIAL.**

Acceptance: State transitions remain consistent under concurrent actions, retries, and abandoned tasks.

Implementation: Actual needs_changes feedback, repeated-decision rejection and reviewer identity separation exercised.

Tests: 33 real Worker/browser controls; five Node and five Python focused tests; actual synthetic game replay/training/withdrawal; populated local backup/restore

Evidence: `src/worker.js`, `docs/PCS_PLATFORM_WORKSTREAM_REPORT.md`, `docs/evidence/platform-governance-v1/ARTIFACT_SHA256.json`

Remaining: Broad dependency/concurrency/abandonment cases and real multi-contributor trials remain limited.

Prior protected release: 72a47c92d47c93249b6c8b9ec0dc70b95232f48c — https://github.com/Tommaso-R-Marena/proof-carrying-science-site/pull/116

## Task 39 — Reconcile D1 migration history safely

**Status: PARTIAL.**

Acceptance: Future migrations can execute through a documented, independently checked process without damaging existing accounts, task state, donations, or audit history.

Implementation: Executed fixed read-only production schema/ledger queries:96objects,no missing source objects,23unrecorded historical migrations. Exact definition/layout/default drifts preserved. Five adversarial/local preflight tests passed.

Tests: 33 real Worker/browser controls; five Node and five Python focused tests; actual synthetic game replay/training/withdrawal; populated local backup/restore; Executed fixed read-only production schema/ledger queries:96objects,no missing source objects,23unrecorded historical migrations. Exact definition/layout/default drifts preserved. Five adversarial/local preflight tests passed.

Evidence: `migrations`, `docs/PCS_PLATFORM_WORKSTREAM_REPORT.md`, `docs/evidence/platform-governance-v1/ARTIFACT_SHA256.json`, `docs/PCS_PRODUCTION_D1_PREFLIGHT_V1.md`

Remaining: Issue93 remains open: historical data effects and production password-default drift require review; no backfill/migration/production restore performed.

Prior protected release: 72a47c92d47c93249b6c8b9ec0dc70b95232f48c — https://github.com/Tommaso-R-Marena/proof-carrying-science-site/pull/116

## Task 40 — Improve browser usability and accessibility

**Status: PARTIAL.**

Acceptance: Critical workflows work at representative viewport sizes without blocking usability defects.

Implementation: Keyboard/reduced-motion game completion and recommendation exercised at 320/768/1440 pixels with no overflow/page exceptions.

Tests: 33 real Worker/browser controls; five Node and five Python focused tests; actual synthetic game replay/training/withdrawal; populated local backup/restore

Evidence: `public/memory-workshop.html`, `docs/PCS_PLATFORM_WORKSTREAM_REPORT.md`, `docs/evidence/platform-governance-v1/ARTIFACT_SHA256.json`

Remaining: Not exhaustive all-page or screen-reader accessibility validation; final release browser gates pending.

Prior protected release: 72a47c92d47c93249b6c8b9ec0dc70b95232f48c — https://github.com/Tommaso-R-Marena/proof-carrying-science-site/pull/116

## Task 41 — Improve contributor feedback

**Status: PARTIAL.**

Acceptance: Contributors can meaningfully revise their submissions based on system feedback.

Implementation: Actual submission feedback and needs_changes flow supports revision under separate authorized reviewer.

Tests: 33 real Worker/browser controls; five Node and five Python focused tests; actual synthetic game replay/training/withdrawal; populated local backup/restore

Evidence: `src/worker.js`, `docs/PCS_PLATFORM_WORKSTREAM_REPORT.md`, `docs/evidence/platform-governance-v1/ARTIFACT_SHA256.json`

Remaining: Synthetic workflow is not real contributor usability evidence or complete feedback taxonomy.

Prior protected release: 72a47c92d47c93249b6c8b9ec0dc70b95232f48c — https://github.com/Tommaso-R-Marena/proof-carrying-science-site/pull/116

## Task 42 — Complete independent proof trajectory replay

**Status: PARTIAL.**

Acceptance: Every promoted gameplay success can be independently checked, and forged trajectories are rejected.

Implementation: Actual synthetic gameplay export freshly replays Lean transitions and final proof before labels; invalid/forged sessions rejected.

Tests: 33 real Worker/browser controls; five Node and five Python focused tests; actual synthetic game replay/training/withdrawal; populated local backup/restore

Evidence: `pcs/experimental/prover/bridge_data.py`, `docs/PCS_PLATFORM_WORKSTREAM_REPORT.md`, `docs/evidence/platform-governance-v1/ARTIFACT_SHA256.json`

Remaining: Tested catalogs only; no human participation or archive-only kernel authority claimed.

Prior protected release: 72a47c92d47c93249b6c8b9ec0dc70b95232f48c — https://github.com/Tommaso-R-Marena/proof-carrying-science-site/pull/116

## Task 43 — Strengthen trajectory provenance

**Status: PARTIAL.**

Acceptance: Each training example is traceable to genuine, authorized, independently validated events.

Implementation: Consent/account/source/catalog/goal/split/hint provenance retained with deterministic membership digests.

Tests: 33 real Worker/browser controls; five Node and five Python focused tests; actual synthetic game replay/training/withdrawal; populated local backup/restore

Evidence: `pcs/experimental/prover/bridge_data.py`, `docs/PCS_PLATFORM_WORKSTREAM_REPORT.md`, `docs/evidence/platform-governance-v1/ARTIFACT_SHA256.json`

Remaining: Authenticated account does not establish a genuine human or independent action; zero human trajectories collected.

Prior protected release: 72a47c92d47c93249b6c8b9ec0dc70b95232f48c — https://github.com/Tommaso-R-Marena/proof-carrying-science-site/pull/116

## Task 44 — Build quality-aware training exports

**Status: PARTIAL.**

Acceptance: The research export pipeline reliably produces labeled, provenance-preserving datasets without silently mixing incompatible evidence classes.

Implementation: Added replay-derived quality classes, content/membership identity and separated verified/archived/partial/invalid/utility examples.

Tests: 33 real Worker/browser controls; five Node and five Python focused tests; actual synthetic game replay/training/withdrawal; populated local backup/restore

Evidence: `pcs/experimental/prover/bridge_data.py`, `docs/PCS_PLATFORM_WORKSTREAM_REPORT.md`, `docs/evidence/platform-governance-v1/ARTIFACT_SHA256.json`

Remaining: Use must retain split/consent and independent replay; no universal provenance or human-data validity inferred.

Prior protected release: 72a47c92d47c93249b6c8b9ec0dc70b95232f48c — https://github.com/Tommaso-R-Marena/proof-carrying-science-site/pull/116

## Task 45 — Implement withdrawal and deletion accounting

**Status: PARTIAL.**

Acceptance: The platform can accurately explain what data was deleted, retained, exported, or previously used, with enforceable controls for future use.

Implementation: Actual deletion receipt quarantines export/dataset/checkpoint descendants and denies future ledger-aware use; no silent checkpoint rewrite.

Tests: 33 real Worker/browser controls; five Node and five Python focused tests; actual synthetic game replay/training/withdrawal; populated local backup/restore

Evidence: `src/worker.js`, `docs/PCS_PLATFORM_WORKSTREAM_REPORT.md`, `docs/evidence/platform-governance-v1/ARTIFACT_SHA256.json`

Remaining: Not model unlearning, remote distributed-copy deletion or enforcement over arbitrary independent training code.

Prior protected release: 72a47c92d47c93249b6c8b9ec0dc70b95232f48c — https://github.com/Tommaso-R-Marena/proof-carrying-science-site/pull/116

## Task 46 — Develop adaptive educational curricula

**Status: PARTIAL.**

Acceptance: Users can progress from beginner exercises toward meaningful formal proof contributions while the research evaluation firewall remains intact.

Implementation: Implemented replay-driven practice progression and real keyboard next-challenge navigation, all games remain selectable.

Tests: 33 real Worker/browser controls; five Node and five Python focused tests; actual synthetic game replay/training/withdrawal; populated local backup/restore

Evidence: `public/memory-workshop.html`, `docs/PCS_PLATFORM_WORKSTREAM_REPORT.md`, `docs/evidence/platform-governance-v1/ARTIFACT_SHA256.json`

Remaining: Local practice completion grants no account skill or research authority; no human engagement/curriculum efficacy study.

Prior protected release: 72a47c92d47c93249b6c8b9ec0dc70b95232f48c — https://github.com/Tommaso-R-Marena/proof-carrying-science-site/pull/116

## Task 47 — Demonstrate actual game-to-model transfer

**Status: BLOCKED.**

Acceptance: A reproducible experiment establishes whether gameplay-derived training examples improve performance, or documents a genuine negative result.

Implementation: Synthetic browser→D1→Owner export→fresh Lean intake→12 gradient steps→saved 14,773-parameter candidate executed.

Tests: 33 real Worker/browser controls; five Node and five Python focused tests; actual synthetic game replay/training/withdrawal; populated local backup/restore

Evidence: `research/verified-memory-integration/ARTIFACT_SHA256.json`, `docs/PCS_PLATFORM_WORKSTREAM_REPORT.md`, `docs/evidence/platform-governance-v1/ARTIFACT_SHA256.json`

Remaining: Zero genuine human participants and no held-out transfer evaluation; actual human-game-to-model efficacy remains blocked by absent consented participation.

Prior protected release: 72a47c92d47c93249b6c8b9ec0dc70b95232f48c — https://github.com/Tommaso-R-Marena/proof-carrying-science-site/pull/116

## Task 48 — Run an authorization attack campaign

**Status: PARTIAL.**

Acceptance: Known attack classes are rejected and critical findings are repaired.

Implementation: Protected site gates passed the actual disposable Worker/D1 authorization and withdrawal campaign plus strict source/result rejection.

Tests: 33 real Worker/browser controls; five Node and five Python focused tests; actual synthetic game replay/training/withdrawal; populated local backup/restore; 44 focused tests and 17 real cryptographic drill controls passed; Protected site gates passed the actual disposable Worker/D1 authorization and withdrawal campaign plus strict source/result rejection.

Evidence: `tests/test_adversarial_v06_hardening.py`, `docs/PCS_PLATFORM_WORKSTREAM_REPORT.md`, `docs/evidence/platform-governance-v1/ARTIFACT_SHA256.json`, `research/platform-security-v1/signing-recovery.json`, `docs/SIGNING_POLICY_AND_RECOVERY_V1.md`, `docs/evidence/protected-platform-release-v1/site-protected-release.json`

Remaining: Not exhaustive penetration testing; synthetic accounts and local verified-email fixtures, no external identity-review acceptance.

Prior protected release: 72a47c92d47c93249b6c8b9ec0dc70b95232f48c — https://github.com/Tommaso-R-Marena/proof-carrying-science-site/pull/116

## Task 49 — Verify signing-key lifecycle controls

**Status: PARTIAL.**

Acceptance: Key lifecycle behavior is documented, tested, and bound to actual verification outcomes.

Implementation: Fixed legacy resolve-before-symlink defect and atomic no-clobber registry creation; descriptor identity,type and1MiB bounds tested with real filesystem attacks.32lifecycle/signing tests passed.

Tests: 44 focused tests and 17 real cryptographic drill controls passed; Fixed legacy resolve-before-symlink defect and atomic no-clobber registry creation; descriptor identity,type and1MiB bounds tested with real filesystem attacks.32lifecycle/signing tests passed.

Evidence: `pcs/key_lifecycle.py`, `research/platform-security-v1/signing-recovery.json`, `docs/SIGNING_POLICY_AND_RECOVERY_V1.md`, `docs/PCS_KEY_FILE_BOUNDARY_V2.md`

Remaining: Trusted parent directories/OS semantics still required; unsigned legacy registry not an authenticated production root. No production key rotation.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 50 — Validate recovery and incident response

**Status: PARTIAL.**

Acceptance: Critical research-platform state can be restored in a test environment with documented recovery evidence.

Implementation: Actual populated local D1 online backup/restore and transaction rollback plus isolated encrypted signing recovery succeeded.

Tests: 33 real Worker/browser controls; five Node and five Python focused tests; actual synthetic game replay/training/withdrawal; populated local backup/restore; 44 focused tests and 17 real cryptographic drill controls passed

Evidence: `docs/RELEASE_AND_INCIDENT_RESPONSE.md`, `docs/PCS_PLATFORM_WORKSTREAM_REPORT.md`, `docs/evidence/platform-governance-v1/ARTIFACT_SHA256.json`, `research/platform-security-v1/signing-recovery.json`, `docs/SIGNING_POLICY_AND_RECOVERY_V1.md`

Remaining: No remote production backup restoration, Worker rollback or complete hosted-job disaster recovery demonstrated.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 51 — Strengthen supply-chain attestations

**Status: PARTIAL.**

Acceptance: Released artifacts have inspectable provenance and tampering can be detected.

Implementation: Exact source, action/dependency manifests, artifact SHA seals, fixed recipe/log binding and trusted-verifier distinction implemented.

Tests: 21 passed; no missing gate promoted; 44 focused tests and 17 real cryptographic drill controls passed

Evidence: `pcs/release_qualification_v1.py`, `docs/evidence/platform-baseline-v1/qualification-focused-final.log`, `research/platform-security-v1/signing-recovery.json`, `docs/SIGNING_POLICY_AND_RECOVERY_V1.md`

Remaining: Unsigned local records are not provider-signed supply-chain attestations or release authorization.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 52 — Audit source and dataset rights

**Status: PARTIAL.**

Acceptance: Technically identifiable rights/provenance issues are cataloged and engineering-controlled distribution restrictions are enforced where appropriate.

Implementation: Real external measurement dataset pinned at upstream8957207b78d6ccd1b4654a9dd9c9041b657478ab with exact CSV hash and upstream CC0 license.

Tests: 21 passed; no missing gate promoted; Real external measurement dataset pinned at upstream8957207b78d6ccd1b4654a9dd9c9041b657478ab with exact CSV hash and upstream CC0 license.

Evidence: `docs/PUBLIC_RELEASE_RIGHTS_LEDGER.md`, `docs/evidence/platform-baseline-v1/qualification-focused-final.log`, `docs/PCS_RELEASE_PROVENANCE_INVENTORY.json`, `docs/PCS_SCIENTIFIC_WORKFLOW_V2_REPORT.md`

Remaining: No complete historical/institutional/legal rights conclusion; corpus license provenance only.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 53 — Strengthen evaluation firewalls

**Status: PARTIAL.**

Acceptance: Benchmark provenance and leakage controls are independently testable, with no misleading claims about private or untouched evaluation sets.

Implementation: Frozen training/final task hashes,alpha-duplicate checks and separately frozen RL split precede updates; stronger post-evaluation diagnostics clearly labeled.

Tests: Frozen144 comparisons completed and audited; full measured results in PCS_GENERALIZATION_AND_LEARNING_EVALUATION.md. No neural/RL gain inferred.; Frozen training/final task hashes,alpha-duplicate checks and separately frozen RL split precede updates; stronger post-evaluation diagnostics clearly labeled.

Evidence: `pcs/experimental/prover/data.py`, `research/prospective-hybrid-v2/protocol.json`, `research/prospective-hybrid-v2/summary.json`, `research/abstraction-repair-v2/protocol.json`, `docs/PCS_DAG_POLICY_V3_REPORT.md`

Remaining: Not a private evaluation firewall or exhaustive semantic near-duplicate detection; developer knows mathematical structures.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 54 — Reconcile public status and reality

**Status: PARTIAL.**

Acceptance: The public website accurately describes which capabilities have been demonstrated, their scope, and their limitations.

Implementation: Corrected stale website release-pending fields using exact prior protected runs/deployment/live replay; source record now states its last-qualified-release scope.

Tests: Protected releases and live evidence reconciled; website status still contains stale release-pending fields scheduled for correction.; Corrected stale website release-pending fields using exact prior protected runs/deployment/live replay; source record now states its last-qualified-release scope.

Evidence: `public/status.json`, `docs/evidence/protected-platform-release-v1/site-protected-release.json`, `docs/PCS_RESEARCH_PLATFORM_PROTECTED_RELEASE.md`

Remaining: New status correction still needs its own protected website CI/deployment; no prospective result asserted.

Prior protected release: 72a47c92d47c93249b6c8b9ec0dc70b95232f48c — https://github.com/Tommaso-R-Marena/proof-carrying-science-site/pull/116

## Task 55 — Build a general scientific reasoning agent

**Status: PARTIAL.**

Acceptance: PCS can execute a multi-obligation scientific reasoning workflow, including meaningful failures and independently checkable intermediate results, with no unsupported claim of autonomous scientific discovery.

Implementation: Bounded scientific plan includes actual data identity,units,filtering,numerical and empirical obligations; receiver propagates changed data/premises and keeps unsupported science OPEN.

Tests: 37 focused tests passed; three fresh scientific receiver processes; eight bounded numerical predicates PASS; Bounded scientific plan includes actual data identity,units,filtering,numerical and empirical obligations; receiver propagates changed data/premises and keeps unsupported science OPEN.

Evidence: `pcs/scheduler_v06.py`, `research/scientific-assurance-v1/SUMMARY.json`, `research/scientific-assurance-v1/ARTIFACT_SHA256.json`, `docs/PCS_SCIENTIFIC_WORKSTREAM_REPORT.md`, `docs/PCS_SCIENTIFIC_WORKFLOW_V2_REPORT.md`

Remaining: No autonomous novel discovery/general research planning or literature authority.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 56 — Integrate a real AI-safety assurance adapter

**Status: PARTIAL.**

Acceptance: One bounded AI-agent safety case is represented as explicit proof obligations and checked evidence, without overstating guarantees.

Implementation: Existing bounded reference-monitor/trace/AI-safety adapters and formal contracts preserved.

Tests: No new capability execution inferred from protected merge.

Evidence: `pcs/control_monitor_v1.py`

Remaining: No new independently executed multi-obligation deployed AI-agent safety case in this workstream.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 57 — Build a computational biology assurance library

**Status: COMPLETE_TESTED.**

Acceptance: At least one substantive computational-biology case study uses multiple reusable PCS domain contracts with independently checkable evidence.

Implementation: Substantive authored three-species/two-reaction biochemical library case uses eight independently replayed bounded predicates and actual signed authority packages.

Tests: 37 focused tests passed; three fresh scientific receiver processes; eight bounded numerical predicates PASS

Evidence: `pcs/adapters/pkpd.py`, `research/scientific-assurance-v1/SUMMARY.json`, `research/scientific-assurance-v1/ARTIFACT_SHA256.json`, `docs/PCS_SCIENTIFIC_WORKSTREAM_REPORT.md`

Remaining: Synthetic kinetic assumptions explicit; numerical claim remains OPEN in PCS, no empirical/clinical validity or continuous solver guarantee.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 58 — Investigate stronger proof-search architectures

**Status: COMPLETE_TESTED.**

Acceptance: At least one new architecture or search strategy is implemented, ablated, and evaluated rigorously; superiority is claimed only if supported.

Implementation: Added trained DAG/bag and genuine sequential RL plus actual frozen comparisons and strong Std baselines. Negative transfer and zero RL gain are preserved without promotion.

Tests: Frozen144 comparisons completed and audited; full measured results in PCS_GENERALIZATION_AND_LEARNING_EVALUATION.md. No neural/RL gain inferred.; Frozen 144 comparisons completed: hybrid 7/8, Std 5/8, structural and learned 4/8. Ablations attribute gains to symbolic/structural stages, no unique neural success.; Added trained DAG/bag and genuine sequential RL plus actual frozen comparisons and strong Std baselines. Negative transfer and zero RL gain are preserved without promotion.

Evidence: `pcs/experimental/prover/prospective_hybrid.py`, `research/prospective-hybrid-v2/protocol.json`, `research/prospective-hybrid-v2/summary.json`, `research/abstraction-repair-v2/protocol.json`, `docs/evidence/protected-platform-release-v1/core-protected-release.json`, `docs/PCS_DAG_POLICY_V3_REPORT.md`

Remaining: Small author-known corpus; learned Mathlib retrieval/action integration and broad superiority unresolved.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105

## Task 59 — Implement cross-project verification contracts

**Status: PARTIAL.**

Acceptance: At least two substantive PCS components exchange independently checkable proof/evidence contracts end-to-end, with invalid and mismatched cases rejected.

Implementation: Real external measurement workflow exchanges typed obligations,signed PCS packages,compiled dimension decisions and fresh independent numerical replay; contradictory signed reports/dimensions rejected.

Tests: 37 focused tests passed; three fresh scientific receiver processes; eight bounded numerical predicates PASS; Real external measurement workflow exchanges typed obligations,signed PCS packages,compiled dimension decisions and fresh independent numerical replay; contradictory signed reports/dimensions rejected.

Evidence: `pcs/certiforge_adapter_v1.py`, `pcs/scientific_contracts_v1.py`, `research/scientific-assurance-v1/SUMMARY.json`, `research/scientific-assurance-v1/ARTIFACT_SHA256.json`, `docs/PCS_SCIENTIFIC_WORKSTREAM_REPORT.md`, `docs/PCS_SCIENTIFIC_WORKFLOW_V2_REPORT.md`

Remaining: Executable scientific adapter refinement and broad learned PCS-CertiForge transfers remain open.

Prior protected release: fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722 — https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/105
