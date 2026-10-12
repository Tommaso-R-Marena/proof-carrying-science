# PCS 59-workstream implementation ledger

Every requested task appears below with its actual implemented scope and remaining acceptance boundary. The JSON companion preserves exact inspected source/evidence hashes. Local source overlays, reference-model proofs, bounded runtime testing, provider CI and deployment are distinct evidence classes. No status authorizes scientific acceptance.

Starting core `e1067e406a1a1991497e7130e1f209239e5607cc`, website `1a351144cac080a990ab6f75fe8b57b476c3b08a`, CertiForge `415a1de40eaeadc366ac2d824c05ee52bb2bd66e`. Final protected release commits/PRs remain pending at this snapshot.

Status counts: 3 BLOCKED, 2 COMPLETE_TESTED, 54 PARTIAL.

Zero human participants, zero independent external human reviewers, zero financial spend. Owner CI diagnostics are distinct from public admissions; existing quotas remain unchanged.

## Task 1 — Establish a reproducible technical baseline

**Status: PARTIAL.**

Acceptance: A fresh checkout and documented environment can reproduce the required results, and every exception or environment dependency is recorded.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Added exact-byte qualification and froze the real starting revision. Setup-corrected staggered baseline covers all 1,419 original outcomes without changing tracked source.

Changed files: `pcs/release_qualification_v1.py`, `pcs/schemas/release-qualification-v1.schema.json`, `scripts/qualify_release.py`, `tests/test_release_qualification_v1.py`

Tests: 21 passed; no missing gate promoted (local focused); 1,409 passed/10 setup failures first run; 17 module tests passed after correction; all tracked source unchanged (staggered baseline, not a single full green run)

Evidence: `proof-carrying-science/scripts/verify_lean.sh`, `proof-carrying-science/.github/workflows/pcs-public-full-verification.yml`, `proof-carrying-science/docs/evidence/platform-baseline-v1/qualification-focused-final.log`, `proof-carrying-science/docs/evidence/platform-baseline-v1/frozen-python-baseline.json`, `proof-carrying-science/docs/evidence/platform-baseline-v1/frozen-reproduction-correction.json`

Remaining: Final source-revision full single-run gates, cross-repository pins and provider release remain pending.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 2 — Complete actual hosted Lean execution

**Status: PARTIAL.**

Acceptance: At least ten repeatable real jobs terminate with accurate verified, unknown, failure, or resource-exhaustion outcomes, with no forged or incomplete results accepted.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Preserved actual public protected Lean pipeline and normal quotas; new ten-job owner diagnostic matrix awaits provider execution.

Changed files: Historical source retained; no new corresponding implementation claimed.

Tests: No new completed acceptance run; historical/source inventory is not a fresh test.

Evidence: `proof-carrying-science/pcs/experimental/prover/public_job.py`, `proof-carrying-science/pcs/experimental/prover/public_transport.py`

Remaining: Owner-hosted diagnostics and real public admissions must be classified separately. No invented jobs or quota bypass.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 3 — Implement robust job lifecycle and recovery

**Status: PARTIAL.**

Acceptance: Restart, retry, race, and duplicate-request tests preserve one coherent authoritative request outcome.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Persistent signed-source-bound job journal preserves a terminal outcome across actual SQLite restart. Nine tests exercised 20 competing timestamp races and ten concurrent cancellation attempts; provider responses were fixed test fixtures.

Changed files: `proof-carrying-science-site/src/lean-job-journal.js`, `proof-carrying-science-site/tests/lean-job-journal.test.mjs`

Tests: Nine local tests; actual SQLite restart; 20 timestamp races and ten cancellation attempts (Fixed provider fixtures; not ten hosted proof jobs)

Evidence: `proof-carrying-science-site/src/lean-research.js`

Remaining: Final hosted restart/retry/race injection and exact provider job receipts pending; local lifecycle evidence does not prove production recovery.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 4 — Implement end-to-end observability

**Status: PARTIAL.**

Acceptance: A failed public research request can be diagnosed from bounded, privacy-safe logs without guessing where execution stopped.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Existing exact-source receipts and cost ledgers retained; fixed-command qualification records outcome, wall/child CPU/RSS and log identity.

Changed files: `pcs/release_qualification_v1.py`, `pcs/schemas/release-qualification-v1.schema.json`, `scripts/qualify_release.py`, `tests/test_release_qualification_v1.py`

Tests: 21 passed; no missing gate promoted (local focused)

Evidence: `proof-carrying-science/pcs/experimental/prover/memory_environment.py`, `proof-carrying-science/docs/evidence/platform-baseline-v1/qualification-focused-final.log`

Remaining: Full live service tracing and concurrent process-tree resource accounting are not inferred.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 5 — Strengthen resource-exhaustion handling

**Status: PARTIAL.**

Acceptance: Negative tests consistently return bounded and accurately classified failures.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Existing typed bounded action/search limits preserved; qualifier terminates timed-out process groups and preserves failure.

Changed files: `pcs/release_qualification_v1.py`, `pcs/schemas/release-qualification-v1.schema.json`, `scripts/qualify_release.py`, `tests/test_release_qualification_v1.py`

Tests: 21 passed; no missing gate promoted (local focused)

Evidence: `proof-carrying-science/pcs/experimental/prover/memory_wire.py`, `proof-carrying-science/docs/evidence/platform-baseline-v1/qualification-focused-final.log`

Remaining: Actual final hosted timeout/cancellation receipts remain to be recorded; resource exhaustion never means proof success.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 6 — Verify deployed core revision and evidence bindings

**Status: PARTIAL.**

Acceptance: Changing any authority-critical bound field causes the corresponding verification to fail.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Preserved exact core/source/model/catalog/receipt bindings; new unsigned qualifier cannot assert deployment.

Changed files: Historical source retained; no new corresponding implementation claimed.

Tests: No new completed acceptance run; historical/source inventory is not a fresh test.

Evidence: `proof-carrying-science/pcs/experimental/prover/public_transport.py`

Remaining: Final tested core pin, website protected SHA and byte-exact live Cloudflare deployment pending.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 7 — Implement comprehensive failure injection

**Status: PARTIAL.**

Acceptance: Every security-critical failure mode is rejected without silently promoting an invalid result.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Source drift, missing/forged gates, malformed records, independent scientific false-report replay and browser authorization failures exercised.

Changed files: `pcs/release_qualification_v1.py`, `pcs/schemas/release-qualification-v1.schema.json`, `scripts/qualify_release.py`, `tests/test_release_qualification_v1.py`

Tests: 21 passed; no missing gate promoted (local focused)

Evidence: `proof-carrying-science/tests/test_public_proof_transport.py`, `proof-carrying-science/docs/evidence/platform-baseline-v1/qualification-focused-final.log`

Remaining: Hosted job-state/provider failure campaign remains separate from these local controls.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 8 — Create a complete release qualification gate

**Status: PARTIAL.**

Acceptance: Critical release failures block promotion, and a qualified release produces an independently inspectable evidence record.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Implemented fixed reviewed local qualification recipes with immutable-source/dependency/log binding and independent rerun. Missing recipes and source drift veto the real smoke qualification.

Changed files: `pcs/release_qualification_v1.py`, `pcs/schemas/release-qualification-v1.schema.json`, `scripts/qualify_release.py`, `tests/test_release_qualification_v1.py`

Tests: 21 passed; no missing gate promoted (local focused)

Evidence: `proof-carrying-science/pcs/release_qualification_v1.py`, `proof-carrying-science/docs/evidence/platform-baseline-v1/qualification-focused-final.log`

Remaining: Unsigned local evidence always deployment-ineligible; final required provider checks remain mandatory.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 9 — Complete external-project adapters

**Status: PARTIAL.**

Acceptance: An unfamiliar public/synthetic scientific workflow can be mapped, reviewed, confirmed, attested, and independently replayed.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Authored unfamiliar standalone biochemical Python project discovered without executing source, explicitly confirmed, packaged and independently replayed.

Changed files: `pcs/scientific_assurance_v1.py`, `pcs/scientific_contracts_v1.py`, `pcs/scientific_obligations_v1.py`, `pcs/scientific_research_v1.py`, `scripts/replay_scientific_bundle_v1.py`, `scripts/run_scientific_assurance_v1.py`

Tests: 37 focused tests passed; three fresh scientific receiver processes; eight bounded numerical predicates PASS (synthetic authored computational science, not clinical validity)

Evidence: `proof-carrying-science/pcs/workflow_discovery_v06.py`, `proof-carrying-science/research/scientific-assurance-v1/SUMMARY.json`, `proof-carrying-science/research/scientific-assurance-v1/ARTIFACT_SHA256.json`, `proof-carrying-science/docs/PCS_SCIENTIFIC_WORKSTREAM_REPORT.md`

Remaining: General external-project intent inference, arbitrary execution isolation and representative third-party evaluation are open.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 10 — Expand Claim IR and Proof Obligation Graph

**Status: PARTIAL.**

Acceptance: Every formal outcome has a complete, machine-readable chain to the exact originating scientific claim, evidence, and assumptions.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Scientific typed sidecar supports units, finite indices, exact parameters, assumptions, provenance and dependency invalidation while preserving canonical Claim IR.

Changed files: `pcs/scientific_assurance_v1.py`, `pcs/scientific_contracts_v1.py`, `pcs/scientific_obligations_v1.py`, `pcs/scientific_research_v1.py`, `scripts/replay_scientific_bundle_v1.py`, `scripts/run_scientific_assurance_v1.py`

Tests: 37 focused tests passed; three fresh scientific receiver processes; eight bounded numerical predicates PASS (synthetic authored computational science, not clinical validity)

Evidence: `proof-carrying-science/pcs/scientific_obligations_v1.py`, `proof-carrying-science/research/scientific-assurance-v1/SUMMARY.json`, `proof-carrying-science/research/scientific-assurance-v1/ARTIFACT_SHA256.json`, `proof-carrying-science/docs/PCS_SCIENTIFIC_WORKSTREAM_REPORT.md`

Remaining: This is a compatible planning sidecar, not broad canonical IR or scientific runtime refinement.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 11 — Automate complete scientific evidence packaging

**Status: PARTIAL.**

Acceptance: A fresh independent environment can verify the delivered bundle without access to the producer's private state.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Actual canonical signed PCS ZIP and readable/numerical sidecars built; three fresh receiver processes validate positive, failure and producer-signed false-report cases.

Changed files: `pcs/scientific_assurance_v1.py`, `pcs/scientific_contracts_v1.py`, `pcs/scientific_obligations_v1.py`, `pcs/scientific_research_v1.py`, `scripts/replay_scientific_bundle_v1.py`, `scripts/run_scientific_assurance_v1.py`

Tests: 37 focused tests passed; three fresh scientific receiver processes; eight bounded numerical predicates PASS (synthetic authored computational science, not clinical validity)

Evidence: `proof-carrying-science/pcs/package_v06.py`, `proof-carrying-science/research/scientific-assurance-v1/SUMMARY.json`, `proof-carrying-science/research/scientific-assurance-v1/ARTIFACT_SHA256.json`, `proof-carrying-science/docs/PCS_SCIENTIFIC_WORKSTREAM_REPORT.md`

Remaining: Numerical claim stays OPEN in compiled PCS authority; independent authenticated human scientific review remains absent.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 12 — Implement useful unsupported-claim analysis

**Status: PARTIAL.**

Acceptance: Unsupported claims remain explicitly OPEN and receive useful, nonmisleading diagnostics.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Unsupported/missing-domain claims return OPEN with explicit diagnostic proposals; clinical control stays unsupported.

Changed files: `pcs/scientific_assurance_v1.py`, `pcs/scientific_contracts_v1.py`, `pcs/scientific_obligations_v1.py`, `pcs/scientific_research_v1.py`, `scripts/replay_scientific_bundle_v1.py`, `scripts/run_scientific_assurance_v1.py`

Tests: 37 focused tests passed; three fresh scientific receiver processes; eight bounded numerical predicates PASS (synthetic authored computational science, not clinical validity)

Evidence: `proof-carrying-science/pcs/limitations.py`, `proof-carrying-science/research/scientific-assurance-v1/SUMMARY.json`, `proof-carrying-science/research/scientific-assurance-v1/ARTIFACT_SHA256.json`, `proof-carrying-science/docs/PCS_SCIENTIFIC_WORKSTREAM_REPORT.md`

Remaining: Advice is lexical/typed scoped behavior, not a general certified English interpretation.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 13 — Expand domain-specific scientific verification

**Status: PARTIAL.**

Acceptance: PCS verifies several nontrivial, clearly scoped properties of an unfamiliar computational-science workflow.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Reusable mass-balance, rate-unit, exact rational Euler, grid, nonnegativity and conservation predicates executed against 13 authored observations.

Changed files: `pcs/scientific_assurance_v1.py`, `pcs/scientific_contracts_v1.py`, `pcs/scientific_obligations_v1.py`, `pcs/scientific_research_v1.py`, `scripts/replay_scientific_bundle_v1.py`, `scripts/run_scientific_assurance_v1.py`

Tests: 37 focused tests passed; three fresh scientific receiver processes; eight bounded numerical predicates PASS (synthetic authored computational science, not clinical validity)

Evidence: `proof-carrying-science/pcs/adapters/pkpd.py`, `proof-carrying-science/research/scientific-assurance-v1/SUMMARY.json`, `proof-carrying-science/research/scientific-assurance-v1/ARTIFACT_SHA256.json`, `proof-carrying-science/docs/PCS_SCIENTIFIC_WORKSTREAM_REPORT.md`

Remaining: No continuous ODE approximation proof, floating-point source refinement or empirical biological adequacy.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 14 — Integrate independent reviewer feedback

**Status: BLOCKED.**

Acceptance: Reviewer concerns can be recorded, traced, and resolved without rewriting the historical evidence.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Append-only evidence-bound reviewer proposal revisions and existing policy passthrough preserved.

Changed files: `pcs/scientific_assurance_v1.py`, `pcs/scientific_contracts_v1.py`, `pcs/scientific_obligations_v1.py`, `pcs/scientific_research_v1.py`, `scripts/replay_scientific_bundle_v1.py`, `scripts/run_scientific_assurance_v1.py`

Tests: 37 focused tests passed; three fresh scientific receiver processes; eight bounded numerical predicates PASS (synthetic authored computational science, not clinical validity)

Evidence: `proof-carrying-science/pcs/external_validator_v06.py`, `proof-carrying-science/research/scientific-assurance-v1/SUMMARY.json`, `proof-carrying-science/research/scientific-assurance-v1/ARTIFACT_SHA256.json`, `proof-carrying-science/docs/PCS_SCIENTIFIC_WORKSTREAM_REPORT.md`

Remaining: Zero independently authenticated external reviewers participated; fixture IDs do not authorize training.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 15 — Expand controlled English-to-Lean

**Status: PARTIAL.**

Acceptance: New independently authored meaning fixtures successfully formalize, elaborate, and undergo independent semantic review.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Existing restricted grammar, typed lowering and learned formalization/search interfaces retained; parser parity and recursion regressions rerun.

Changed files: Historical source retained; no new corresponding implementation claimed.

Tests: No new completed acceptance run; historical/source inventory is not a fresh test.

Evidence: `proof-carrying-science/pcs/experimental/prover/language.py`

Remaining: No newly trained broad English-to-Lean model or unrestricted meaning-preservation claim.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 16 — Implement stronger bidirectional semantic checking

**Status: PARTIAL.**

Acceptance: The system detects and reports semantic inconsistencies on a meaningful suite of independently authored examples.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Restricted typed round-trip and semantic reference theorems freshly audited; original exact source grounding preserved.

Changed files: Historical source retained; no new corresponding implementation claimed.

Tests: No new completed acceptance run; historical/source inventory is not a fresh test.

Evidence: `proof-carrying-science/pcs/semantic_translation_v1.py`

Remaining: General English explanation equivalence and implementation-wide parser correspondence remain unproved.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 17 — Improve ambiguity detection and abstention

**Status: PARTIAL.**

Acceptance: Ambiguous inputs produce reviewable alternatives or abstention rather than unreviewed certification.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Existing ambiguity/unsupported abstention retained; deep input rejects without uncaught recursion.

Changed files: Historical source retained; no new corresponding implementation claimed.

Tests: No new completed acceptance run; historical/source inventory is not a fresh test.

Evidence: `proof-carrying-science/pcs/experimental/prover/language.py`

Remaining: Broader linguistic ambiguity corpus and independent human fidelity review remain unperformed.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 18 — Integrate actual Mathlib retrieval

**Status: PARTIAL.**

Acceptance: PCS uses genuine external Mathlib declarations to solve unfamiliar mathematical problems beyond its authored elementary proof catalogs.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Actual exact-pinned Mathlib declarations retrieved and used in kernel-checked external theorem search.

Changed files: `pcs/experimental/prover/abstraction_repair_v2.py`, `pcs/experimental/prover/checkpoint_transfer_v2.py`, `pcs/experimental/prover/hybrid.py`, `pcs/experimental/prover/mathlib_retrieval.py`, `pcs/experimental/prover/promotion.py`, `pcs/experimental/prover/prospective_hybrid.py`, `pcs/experimental/prover/state_graph.py`

Tests: Actual completed receipt files preserved; ongoing results require final experiment report, no planned result counted (public authored partitions; no new model superiority claim)

Evidence: `proof-carrying-science/pcs/experimental/prover/library.py`, `proof-carrying-science/research/prospective-hybrid-v2/protocol.json`, `proof-carrying-science/research/prospective-hybrid-v2/summary.json`, `proof-carrying-science/research/abstraction-repair-v2/protocol.json`

Remaining: Grounded retrieval is evaluated on a small public authored set; new complete generalization report records final results when complete.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 19 — Improve structured proof-state representations

**Status: PARTIAL.**

Acceptance: Actual model features derive from real Lean states, and improvements are evaluated against appropriate ablations.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Implemented expression/local-context proof-state graph extraction from actual structured Lean states.

Changed files: `pcs/experimental/prover/abstraction_repair_v2.py`, `pcs/experimental/prover/checkpoint_transfer_v2.py`, `pcs/experimental/prover/hybrid.py`, `pcs/experimental/prover/mathlib_retrieval.py`, `pcs/experimental/prover/promotion.py`, `pcs/experimental/prover/prospective_hybrid.py`, `pcs/experimental/prover/state_graph.py`

Tests: Actual completed receipt files preserved; ongoing results require final experiment report, no planned result counted (public authored partitions; no new model superiority claim)

Evidence: `proof-carrying-science/pcs/experimental/prover/environment.py`, `proof-carrying-science/research/prospective-hybrid-v2/protocol.json`, `proof-carrying-science/research/prospective-hybrid-v2/summary.json`, `proof-carrying-science/research/abstraction-repair-v2/protocol.json`

Remaining: Graph correctness and learned benefit are not inferred from an API or synthetic hand-written goal strings.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 20 — Strengthen verified-memory discovery

**Status: PARTIAL.**

Acceptance: PCS automatically proposes and admits useful intermediate lemmas that improve unseen proof-search performance beyond trivial theorem memorization.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Counterexample-guided scoped abstraction-repair experiment extends existing checked cut/memory admission.

Changed files: `pcs/experimental/prover/abstraction_repair_v2.py`, `pcs/experimental/prover/checkpoint_transfer_v2.py`, `pcs/experimental/prover/hybrid.py`, `pcs/experimental/prover/mathlib_retrieval.py`, `pcs/experimental/prover/promotion.py`, `pcs/experimental/prover/prospective_hybrid.py`, `pcs/experimental/prover/state_graph.py`

Tests: Actual completed receipt files preserved; ongoing results require final experiment report, no planned result counted (public authored partitions; no new model superiority claim)

Evidence: `proof-carrying-science/pcs/experimental/prover/abstraction_experiment.py`, `proof-carrying-science/research/prospective-hybrid-v2/protocol.json`, `proof-carrying-science/research/prospective-hybrid-v2/summary.json`, `proof-carrying-science/research/abstraction-repair-v2/protocol.json`

Remaining: No mathematical novelty claim; exact utility/final transfer outcomes must come from completed sealed experiment.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 21 — Improve typed anti-unification and generalization

**Status: PARTIAL.**

Acceptance: Some genuine proposed generalizations survive independent Lean checking and prove useful on held-out problems.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Typed anti-unification and scoped repaired proposal admission implemented with fresh kernel checks.

Changed files: `pcs/experimental/prover/abstraction_repair_v2.py`, `pcs/experimental/prover/checkpoint_transfer_v2.py`, `pcs/experimental/prover/hybrid.py`, `pcs/experimental/prover/mathlib_retrieval.py`, `pcs/experimental/prover/promotion.py`, `pcs/experimental/prover/prospective_hybrid.py`, `pcs/experimental/prover/state_graph.py`

Tests: Actual completed receipt files preserved; ongoing results require final experiment report, no planned result counted (public authored partitions; no new model superiority claim)

Evidence: `proof-carrying-science/pcs/experimental/prover/memory_discovery.py`, `proof-carrying-science/research/prospective-hybrid-v2/protocol.json`, `proof-carrying-science/research/prospective-hybrid-v2/summary.json`, `proof-carrying-science/research/abstraction-repair-v2/protocol.json`

Remaining: Broader principal anti-unification theory and discovered-mathematics novelty remain unsupported.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 22 — Optimize verified-memory utility

**Status: PARTIAL.**

Acceptance: A selected memory configuration demonstrates reproducible practical value under a frozen evaluation protocol.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Frozen memory utility protocols and cost/resource receipts retained; separate amortization experiment staged.

Changed files: `pcs/experimental/prover/abstraction_repair_v2.py`, `pcs/experimental/prover/checkpoint_transfer_v2.py`, `pcs/experimental/prover/hybrid.py`, `pcs/experimental/prover/mathlib_retrieval.py`, `pcs/experimental/prover/promotion.py`, `pcs/experimental/prover/prospective_hybrid.py`, `pcs/experimental/prover/state_graph.py`

Tests: Actual completed receipt files preserved; ongoing results require final experiment report, no planned result counted (public authored partitions; no new model superiority claim)

Evidence: `proof-carrying-science/pcs/experimental/prover/memory_experiment.py`, `proof-carrying-science/research/prospective-hybrid-v2/protocol.json`, `proof-carrying-science/research/prospective-hybrid-v2/summary.json`, `proof-carrying-science/research/abstraction-repair-v2/protocol.json`

Remaining: Small paired utility results cannot imply submodularity, global optimum or universal efficiency.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 23 — Develop hybrid symbolic-neural search

**Status: PARTIAL.**

Acceptance: A hybrid system is implemented with reproducible component ablations and measurable performance, without attributing symbolic successes to the neural policy.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Real hybrid symbol/premise/checked-memory search with independently kernel-replayed outcomes implemented.

Changed files: `pcs/experimental/prover/abstraction_repair_v2.py`, `pcs/experimental/prover/checkpoint_transfer_v2.py`, `pcs/experimental/prover/hybrid.py`, `pcs/experimental/prover/mathlib_retrieval.py`, `pcs/experimental/prover/promotion.py`, `pcs/experimental/prover/prospective_hybrid.py`, `pcs/experimental/prover/state_graph.py`

Tests: Actual completed receipt files preserved; ongoing results require final experiment report, no planned result counted (public authored partitions; no new model superiority claim)

Evidence: `proof-carrying-science/pcs/experimental/prover/memory_search.py`, `proof-carrying-science/research/prospective-hybrid-v2/protocol.json`, `proof-carrying-science/research/prospective-hybrid-v2/summary.json`, `proof-carrying-science/research/abstraction-repair-v2/protocol.json`

Remaining: Held-out superiority and larger external project transfer are not preclaimed.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 24 — Improve induction strategy selection

**Status: PARTIAL.**

Acceptance: PCS solves additional independently authored induction problems beyond those already supported, with exact verified proofs.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Existing real under-hypothesis induction actions retained; typed successor/recurrence search compared with symbolic and Std policies.

Changed files: `pcs/experimental/prover/abstraction_repair_v2.py`, `pcs/experimental/prover/checkpoint_transfer_v2.py`, `pcs/experimental/prover/hybrid.py`, `pcs/experimental/prover/mathlib_retrieval.py`, `pcs/experimental/prover/promotion.py`, `pcs/experimental/prover/prospective_hybrid.py`, `pcs/experimental/prover/state_graph.py`

Tests: Actual completed receipt files preserved; ongoing results require final experiment report, no planned result counted (public authored partitions; no new model superiority claim)

Evidence: `proof-carrying-science/pcs/experimental/prover/induction_environment.py`, `proof-carrying-science/research/prospective-hybrid-v2/protocol.json`, `proof-carrying-science/research/prospective-hybrid-v2/summary.json`, `proof-carrying-science/research/abstraction-repair-v2/protocol.json`

Remaining: Learned induction strategy improvement requires completed untouched evaluation, not task repetition.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 25 — Implement counterexample-guided proof repair

**Status: PARTIAL.**

Acceptance: PCS repairs a reproducible set of previously failed proofs without increasing unsound acceptance.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Actual bounded counterexamples guide explicit separate abstraction repairs without mutating original goals.

Changed files: `pcs/experimental/prover/abstraction_repair_v2.py`, `pcs/experimental/prover/checkpoint_transfer_v2.py`, `pcs/experimental/prover/hybrid.py`, `pcs/experimental/prover/mathlib_retrieval.py`, `pcs/experimental/prover/promotion.py`, `pcs/experimental/prover/prospective_hybrid.py`, `pcs/experimental/prover/state_graph.py`

Tests: Actual completed receipt files preserved; ongoing results require final experiment report, no planned result counted (public authored partitions; no new model superiority claim)

Evidence: `proof-carrying-science/pcs/proof_repair_v06.py`, `proof-carrying-science/research/prospective-hybrid-v2/protocol.json`, `proof-carrying-science/research/prospective-hybrid-v2/summary.json`, `proof-carrying-science/research/abstraction-repair-v2/protocol.json`

Remaining: Not unrestricted conjecture repair or a permission to silently strengthen assumptions.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 26 — Improve genuine reinforcement learning

**Status: PARTIAL.**

Acceptance: Training runs are reproducible, sequential, and independently verified; promotion requires measured held-out performance rather than mere successful gradient updates.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Historical 32 sequential actor–critic updates and negative held-out result preserved. New policy transfer does not create new RL evidence.

Changed files: `pcs/experimental/prover/abstraction_repair_v2.py`, `pcs/experimental/prover/checkpoint_transfer_v2.py`, `pcs/experimental/prover/hybrid.py`, `pcs/experimental/prover/mathlib_retrieval.py`, `pcs/experimental/prover/promotion.py`, `pcs/experimental/prover/prospective_hybrid.py`, `pcs/experimental/prover/state_graph.py`

Tests: Actual completed receipt files preserved; ongoing results require final experiment report, no planned result counted (public authored partitions; no new model superiority claim)

Evidence: `proof-carrying-science/pcs/experimental/prover/memory_experiment.py`, `proof-carrying-science/research/prospective-hybrid-v2/protocol.json`, `proof-carrying-science/research/prospective-hybrid-v2/summary.json`, `proof-carrying-science/research/abstraction-repair-v2/protocol.json`

Remaining: No new demonstrated sequential RL improvement; historical weight changes do not imply better held-out search.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 27 — Implement strict model promotion gates

**Status: PARTIAL.**

Acceptance: The default system cannot be replaced by an inferior or unverified candidate without an explicit authorized override.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Implemented stricter source/dataset/evaluator-bound promotion metadata, exposure bookkeeping and fail-closed decision controls.

Changed files: `pcs/experimental/prover/abstraction_repair_v2.py`, `pcs/experimental/prover/checkpoint_transfer_v2.py`, `pcs/experimental/prover/hybrid.py`, `pcs/experimental/prover/mathlib_retrieval.py`, `pcs/experimental/prover/promotion.py`, `pcs/experimental/prover/prospective_hybrid.py`, `pcs/experimental/prover/state_graph.py`

Tests: Actual completed receipt files preserved; ongoing results require final experiment report, no planned result counted (public authored partitions; no new model superiority claim)

Evidence: `proof-carrying-science/pcs/experimental/prover/promotion.py`, `proof-carrying-science/research/prospective-hybrid-v2/protocol.json`, `proof-carrying-science/research/prospective-hybrid-v2/summary.json`, `proof-carrying-science/research/abstraction-repair-v2/protocol.json`

Remaining: No checkpoint automatically acquires production authority; independent gate integration and full adaptive statistical protocol remain required.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 28 — Build serious independent benchmarks

**Status: PARTIAL.**

Acceptance: Independent researchers can rerun the comparisons and interpret the results without relying on claims in a summary document.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Frozen public developer-authored typed/Mathlib partitions, source overlays and contamination inspection established before experiments.

Changed files: `pcs/experimental/prover/abstraction_repair_v2.py`, `pcs/experimental/prover/checkpoint_transfer_v2.py`, `pcs/experimental/prover/hybrid.py`, `pcs/experimental/prover/mathlib_retrieval.py`, `pcs/experimental/prover/promotion.py`, `pcs/experimental/prover/prospective_hybrid.py`, `pcs/experimental/prover/state_graph.py`

Tests: Actual completed receipt files preserved; ongoing results require final experiment report, no planned result counted (public authored partitions; no new model superiority claim)

Evidence: `proof-carrying-science/research/verified-memory-v1/protocol.json`, `proof-carrying-science/research/prospective-hybrid-v2/protocol.json`, `proof-carrying-science/research/prospective-hybrid-v2/summary.json`, `proof-carrying-science/research/abstraction-repair-v2/protocol.json`

Remaining: Benchmarks are not private, blind or previously unseen external repositories. Interface-debug exposure is disclosed.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 29 — Complete conditional-checker refinement

**Status: BLOCKED.**

Acceptance: Additional real production operations are covered by auditable source-bound refinement theorems with explicit assumptions.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Existing decision-diagram reference proofs and extracted arithmetic preserved; actual Python/JavaScript/Lean comparisons expanded.

Changed files: `formal/tools/RuntimeCanonicalInputs.lean`, `formal/tools/RuntimeValueType.lean`, `scripts/runtime_differential.py`, `scripts/verify_runtime_canonical_boundary.py`, `scripts/verify_runtime_value_type.py`

Tests: 54 principal audit entries; four new Value::ty proofs; five canonical-input controls; 1,618 expanded comparisons zero mismatches (source windows and finite runtime cases, not full conditional/top-level refinement)

Evidence: `proof-carrying-science/research/aristotle-runtime-refinement-v1/REPORT.md`, `proof-carrying-science/docs/evidence/platform-baseline-v1/runtime-refinement.json`, `proof-carrying-science/docs/evidence/platform-baseline-v1/value-type-refinement.json`, `proof-carrying-science/docs/evidence/platform-baseline-v1/runtime-differential-512.json.gz`, `proof-carrying-science/docs/PCS_FORMAL_ASSURANCE_AND_REFINEMENT_REPORT.md`

Remaining: Principal python_conditional_refines_reference and javascript_conditional_refines_reference remain open; unsupported runtime constructs not replaced by a weaker proof.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 30 — Extend formalization parser refinement

**Status: PARTIAL.**

Acceptance: The supported parser fragment has stronger demonstrated source-to-specification correspondence, and unsupported cases fail safely.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Fresh restricted parser theorem audit, 1,523 runtime parity cases and depth-995 fail-closed regressions executed.

Changed files: `formal/tools/RuntimeCanonicalInputs.lean`, `formal/tools/RuntimeValueType.lean`, `scripts/runtime_differential.py`, `scripts/verify_runtime_canonical_boundary.py`, `scripts/verify_runtime_value_type.py`

Tests: 54 principal audit entries; four new Value::ty proofs; five canonical-input controls; 1,618 expanded comparisons zero mismatches (source windows and finite runtime cases, not full conditional/top-level refinement)

Evidence: `proof-carrying-science/pcs/experimental/prover/language.py`, `proof-carrying-science/docs/evidence/platform-baseline-v1/runtime-refinement.json`, `proof-carrying-science/docs/evidence/platform-baseline-v1/value-type-refinement.json`, `proof-carrying-science/docs/evidence/platform-baseline-v1/runtime-differential-512.json.gz`, `proof-carrying-science/docs/PCS_FORMAL_ASSURANCE_AND_REFINEMENT_REPORT.md`

Remaining: English rewriting, JSON/text decoding and whole actual parser-source refinement remain open.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 31 — Expand CertiForge formal refinement

**Status: PARTIAL.**

Acceptance: More of CertiForge's real checker and optimizer behavior is connected to explicit Lean theorems, with source revision binding and independent differential validation.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Added exact-source Rust Value::ty helper extraction with four kernel theorems; preserved source-bound eval_expr and certificate results. New eval_expr_checked validates canonical public-store payloads; high-level eval routes through it. Rust regression gate pending at this snapshot.

Changed files: `formal/tools/RuntimeCanonicalInputs.lean`, `formal/tools/RuntimeValueType.lean`, `scripts/runtime_differential.py`, `scripts/verify_runtime_canonical_boundary.py`, `scripts/verify_runtime_value_type.py`

Tests: 54 principal audit entries; four new Value::ty proofs; five canonical-input controls; 1,618 expanded comparisons zero mismatches (source windows and finite runtime cases, not full conditional/top-level refinement)

Evidence: `proof-carrying-science/pcs/certiforge_adapter_v1.py`, `proof-carrying-science/docs/evidence/platform-baseline-v1/runtime-refinement.json`, `proof-carrying-science/docs/evidence/platform-baseline-v1/value-type-refinement.json`, `proof-carrying-science/docs/evidence/platform-baseline-v1/runtime-differential-512.json.gz`, `proof-carrying-science/docs/PCS_FORMAL_ASSURANCE_AND_REFINEMENT_REPORT.md`

Remaining: Full top-level Rust eval loop/type-checker/checked-wrapper extraction and native compiler correspondence remain open. Archived source415 counterexample motivates the new tested guard; low-level eval_expr still requires Value.WF.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 32 — Formalize learning-runtime safety invariants

**Status: PARTIAL.**

Acceptance: Additional learning-system correctness boundaries are formalized, and any claimed runtime guarantees have explicit implementation evidence.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Freshly audited existing model-independent reward, replay, conservative library, authority and memory-boundary reference theorems.

Changed files: `formal/tools/RuntimeCanonicalInputs.lean`, `formal/tools/RuntimeValueType.lean`, `scripts/runtime_differential.py`, `scripts/verify_runtime_canonical_boundary.py`, `scripts/verify_runtime_value_type.py`

Tests: 54 principal audit entries; four new Value::ty proofs; five canonical-input controls; 1,618 expanded comparisons zero mismatches (source windows and finite runtime cases, not full conditional/top-level refinement)

Evidence: `proof-carrying-science/formal/PCSVerifiedMemoryBoundary.lean`, `proof-carrying-science/docs/evidence/platform-baseline-v1/runtime-refinement.json`, `proof-carrying-science/docs/evidence/platform-baseline-v1/value-type-refinement.json`, `proof-carrying-science/docs/evidence/platform-baseline-v1/runtime-differential-512.json.gz`, `proof-carrying-science/docs/PCS_FORMAL_ASSURANCE_AND_REFINEMENT_REPORT.md`

Remaining: These are reference interfaces, not whole Python/JavaScript service or evaluator implementation refinement.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 33 — Strengthen cryptographic and serialization assurance

**Status: PARTIAL.**

Acceptance: Critical serialization and authentication invariants have reproducible positive/negative evidence and, where feasible, formal correspondence results.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Added real authenticated Ed25519 signing policy, trusted observation, expiry/rotation/compromise and exact-object binding controls; existing canonical primitives preserved.

Changed files: `pcs/signing_policy_v1.py`, `scripts/exercise_signing_recovery.py`, `tests/test_signing_policy_v1.py`, `tests/test_signing_recovery_drill.py`

Tests: 44 focused tests and 17 real cryptographic drill controls passed (ephemeral test keys, not production custody)

Evidence: `proof-carrying-science/pcs/canonical_json.py`, `proof-carrying-science/pcs/receipt_signature_v06.py`, `proof-carrying-science/research/platform-security-v1/signing-recovery.json`, `proof-carrying-science/docs/SIGNING_POLICY_AND_RECOVERY_V1.md`

Remaining: No formal Ed25519/Python/clock/custody proof or production-root rollout is asserted.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 34 — Expand differential testing

**Status: COMPLETE_TESTED.**

Acceptance: The framework finds or rules out mismatches within explicitly defined tested domains, without representing testing as a general proof of equivalence.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Executed 1,618 expanded native/Python/JavaScript/Lean comparisons with zero mismatches; release smoke and deliberate historical mismatch shrinking controls retained.

Changed files: `formal/tools/RuntimeCanonicalInputs.lean`, `formal/tools/RuntimeValueType.lean`, `scripts/runtime_differential.py`, `scripts/verify_runtime_canonical_boundary.py`, `scripts/verify_runtime_value_type.py`

Tests: 54 principal audit entries; four new Value::ty proofs; five canonical-input controls; 1,618 expanded comparisons zero mismatches (source windows and finite runtime cases, not full conditional/top-level refinement)

Evidence: `proof-carrying-science/research/aristotle-runtime-refinement-v1/REPORT.md`, `proof-carrying-science/docs/evidence/platform-baseline-v1/runtime-refinement.json`, `proof-carrying-science/docs/evidence/platform-baseline-v1/value-type-refinement.json`, `proof-carrying-science/docs/evidence/platform-baseline-v1/runtime-differential-512.json.gz`, `proof-carrying-science/docs/PCS_FORMAL_ASSURANCE_AND_REFINEMENT_REPORT.md`

Remaining: Finite typed-domain testing, not universal equivalence; error-format normalization and JSON/hash authority exclusions explicit.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 35 — Validate end-to-end onboarding

**Status: PARTIAL.**

Acceptance: Independent testers can complete the workflow, and unauthorized privilege changes are rejected.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Actual isolated browser account onboarding/manual review/task/submission flow exercised with local verification fixtures.

Changed files: `proof-carrying-science-site/public/bridge-builder-core.mjs`, `proof-carrying-science-site/public/research-governance-core.mjs`, `proof-carrying-science-site/scripts/browser_platform_governance.cjs`, `proof-carrying-science-site/scripts/d1_reconcile.py`, `proof-carrying-science-site/scripts/research_lineage.py`, `proof-carrying-science-site/src/worker.js`

Tests: 33 real Worker/browser controls; five Node and five Python focused tests; actual synthetic game replay/training/withdrawal; populated local backup/restore (zero humans, zero production D1 mutations)

Evidence: `proof-carrying-science-site/src/worker.js`, `proof-carrying-science-site/docs/PCS_PLATFORM_WORKSTREAM_REPORT.md`, `proof-carrying-science-site/docs/evidence/platform-governance-v1/ARTIFACT_SHA256.json`

Remaining: No real external user, email delivery or independent assessment participated.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 36 — Strengthen GitHub-backed contribution integration

**Status: PARTIAL.**

Acceptance: A valid low-risk contribution can be integrated through the documented process, and forged or unauthorized promotion attempts fail.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Preserved GitHub artifact/owner/protected promotion integration and exact source-gate behavior; frozen contribution tests all pass after canonical checkout setup.

Changed files: Historical source retained; no new corresponding implementation claimed.

Tests: No new completed acceptance run; historical/source inventory is not a fresh test.

Evidence: `proof-carrying-science-site/src/contribution-github.js`

Remaining: A new live contributor-authored GitHub low-risk merge was not performed in this campaign.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 37 — Complete scientific task taxonomy

**Status: PARTIAL.**

Acceptance: A newcomer can select a task and understand exactly what constitutes successful completion.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Existing scientific task catalog retained; real eligible task intake and skill boundaries validated.

Changed files: `proof-carrying-science-site/public/bridge-builder-core.mjs`, `proof-carrying-science-site/public/research-governance-core.mjs`, `proof-carrying-science-site/scripts/browser_platform_governance.cjs`, `proof-carrying-science-site/scripts/d1_reconcile.py`, `proof-carrying-science-site/scripts/research_lineage.py`, `proof-carrying-science-site/src/worker.js`

Tests: 33 real Worker/browser controls; five Node and five Python focused tests; actual synthetic game replay/training/withdrawal; populated local backup/restore (zero humans, zero production D1 mutations)

Evidence: `proof-carrying-science-site/src/worker.js`, `proof-carrying-science-site/docs/PCS_PLATFORM_WORKSTREAM_REPORT.md`, `proof-carrying-science-site/docs/evidence/platform-governance-v1/ARTIFACT_SHA256.json`

Remaining: Complete scientific taxonomy and newcomer comprehension are not established by fixture automation.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 38 — Improve task dependencies and review tracking

**Status: PARTIAL.**

Acceptance: State transitions remain consistent under concurrent actions, retries, and abandoned tasks.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Actual needs_changes feedback, repeated-decision rejection and reviewer identity separation exercised.

Changed files: `proof-carrying-science-site/public/bridge-builder-core.mjs`, `proof-carrying-science-site/public/research-governance-core.mjs`, `proof-carrying-science-site/scripts/browser_platform_governance.cjs`, `proof-carrying-science-site/scripts/d1_reconcile.py`, `proof-carrying-science-site/scripts/research_lineage.py`, `proof-carrying-science-site/src/worker.js`

Tests: 33 real Worker/browser controls; five Node and five Python focused tests; actual synthetic game replay/training/withdrawal; populated local backup/restore (zero humans, zero production D1 mutations)

Evidence: `proof-carrying-science-site/src/worker.js`, `proof-carrying-science-site/docs/PCS_PLATFORM_WORKSTREAM_REPORT.md`, `proof-carrying-science-site/docs/evidence/platform-governance-v1/ARTIFACT_SHA256.json`

Remaining: Broad dependency/concurrency/abandonment cases and real multi-contributor trials remain limited.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 39 — Reconcile D1 migration history safely

**Status: PARTIAL.**

Acceptance: Future migrations can execute through a documented, independently checked process without damaging existing accounts, task state, donations, or audit history.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Read-only reconciliation tool executes all 25 migrations on isolated references, inventories actual state, and tests pending changes on copies.

Changed files: `proof-carrying-science-site/public/bridge-builder-core.mjs`, `proof-carrying-science-site/public/research-governance-core.mjs`, `proof-carrying-science-site/scripts/browser_platform_governance.cjs`, `proof-carrying-science-site/scripts/d1_reconcile.py`, `proof-carrying-science-site/scripts/research_lineage.py`, `proof-carrying-science-site/src/worker.js`

Tests: 33 real Worker/browser controls; five Node and five Python focused tests; actual synthetic game replay/training/withdrawal; populated local backup/restore (zero humans, zero production D1 mutations)

Evidence: `proof-carrying-science-site/migrations`, `proof-carrying-science-site/docs/PCS_PLATFORM_WORKSTREAM_REPORT.md`, `proof-carrying-science-site/docs/evidence/platform-governance-v1/ARTIFACT_SHA256.json`

Remaining: Issue #93 production reconciliation remains pending; current schema does not authorize historical ledger backfill.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 40 — Improve browser usability and accessibility

**Status: PARTIAL.**

Acceptance: Critical workflows work at representative viewport sizes without blocking usability defects.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Keyboard/reduced-motion game completion and recommendation exercised at 320/768/1440 pixels with no overflow/page exceptions.

Changed files: `proof-carrying-science-site/public/bridge-builder-core.mjs`, `proof-carrying-science-site/public/research-governance-core.mjs`, `proof-carrying-science-site/scripts/browser_platform_governance.cjs`, `proof-carrying-science-site/scripts/d1_reconcile.py`, `proof-carrying-science-site/scripts/research_lineage.py`, `proof-carrying-science-site/src/worker.js`

Tests: 33 real Worker/browser controls; five Node and five Python focused tests; actual synthetic game replay/training/withdrawal; populated local backup/restore (zero humans, zero production D1 mutations)

Evidence: `proof-carrying-science-site/public/memory-workshop.html`, `proof-carrying-science-site/docs/PCS_PLATFORM_WORKSTREAM_REPORT.md`, `proof-carrying-science-site/docs/evidence/platform-governance-v1/ARTIFACT_SHA256.json`

Remaining: Not exhaustive all-page or screen-reader accessibility validation; final release browser gates pending.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 41 — Improve contributor feedback

**Status: PARTIAL.**

Acceptance: Contributors can meaningfully revise their submissions based on system feedback.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Actual submission feedback and needs_changes flow supports revision under separate authorized reviewer.

Changed files: `proof-carrying-science-site/public/bridge-builder-core.mjs`, `proof-carrying-science-site/public/research-governance-core.mjs`, `proof-carrying-science-site/scripts/browser_platform_governance.cjs`, `proof-carrying-science-site/scripts/d1_reconcile.py`, `proof-carrying-science-site/scripts/research_lineage.py`, `proof-carrying-science-site/src/worker.js`

Tests: 33 real Worker/browser controls; five Node and five Python focused tests; actual synthetic game replay/training/withdrawal; populated local backup/restore (zero humans, zero production D1 mutations)

Evidence: `proof-carrying-science-site/src/worker.js`, `proof-carrying-science-site/docs/PCS_PLATFORM_WORKSTREAM_REPORT.md`, `proof-carrying-science-site/docs/evidence/platform-governance-v1/ARTIFACT_SHA256.json`

Remaining: Synthetic workflow is not real contributor usability evidence or complete feedback taxonomy.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 42 — Complete independent proof trajectory replay

**Status: PARTIAL.**

Acceptance: Every promoted gameplay success can be independently checked, and forged trajectories are rejected.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Actual synthetic gameplay export freshly replays Lean transitions and final proof before labels; invalid/forged sessions rejected.

Changed files: `proof-carrying-science-site/public/bridge-builder-core.mjs`, `proof-carrying-science-site/public/research-governance-core.mjs`, `proof-carrying-science-site/scripts/browser_platform_governance.cjs`, `proof-carrying-science-site/scripts/d1_reconcile.py`, `proof-carrying-science-site/scripts/research_lineage.py`, `proof-carrying-science-site/src/worker.js`

Tests: 33 real Worker/browser controls; five Node and five Python focused tests; actual synthetic game replay/training/withdrawal; populated local backup/restore (zero humans, zero production D1 mutations)

Evidence: `proof-carrying-science/pcs/experimental/prover/bridge_data.py`, `proof-carrying-science-site/docs/PCS_PLATFORM_WORKSTREAM_REPORT.md`, `proof-carrying-science-site/docs/evidence/platform-governance-v1/ARTIFACT_SHA256.json`

Remaining: Tested catalogs only; no human participation or archive-only kernel authority claimed.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 43 — Strengthen trajectory provenance

**Status: PARTIAL.**

Acceptance: Each training example is traceable to genuine, authorized, independently validated events.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Consent/account/source/catalog/goal/split/hint provenance retained with deterministic membership digests.

Changed files: `proof-carrying-science-site/public/bridge-builder-core.mjs`, `proof-carrying-science-site/public/research-governance-core.mjs`, `proof-carrying-science-site/scripts/browser_platform_governance.cjs`, `proof-carrying-science-site/scripts/d1_reconcile.py`, `proof-carrying-science-site/scripts/research_lineage.py`, `proof-carrying-science-site/src/worker.js`

Tests: 33 real Worker/browser controls; five Node and five Python focused tests; actual synthetic game replay/training/withdrawal; populated local backup/restore (zero humans, zero production D1 mutations)

Evidence: `proof-carrying-science/pcs/experimental/prover/bridge_data.py`, `proof-carrying-science-site/docs/PCS_PLATFORM_WORKSTREAM_REPORT.md`, `proof-carrying-science-site/docs/evidence/platform-governance-v1/ARTIFACT_SHA256.json`

Remaining: Authenticated account does not establish a genuine human or independent action; zero human trajectories collected.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 44 — Build quality-aware training exports

**Status: PARTIAL.**

Acceptance: The research export pipeline reliably produces labeled, provenance-preserving datasets without silently mixing incompatible evidence classes.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Added replay-derived quality classes, content/membership identity and separated verified/archived/partial/invalid/utility examples.

Changed files: `proof-carrying-science-site/public/bridge-builder-core.mjs`, `proof-carrying-science-site/public/research-governance-core.mjs`, `proof-carrying-science-site/scripts/browser_platform_governance.cjs`, `proof-carrying-science-site/scripts/d1_reconcile.py`, `proof-carrying-science-site/scripts/research_lineage.py`, `proof-carrying-science-site/src/worker.js`

Tests: 33 real Worker/browser controls; five Node and five Python focused tests; actual synthetic game replay/training/withdrawal; populated local backup/restore (zero humans, zero production D1 mutations)

Evidence: `proof-carrying-science/pcs/experimental/prover/bridge_data.py`, `proof-carrying-science-site/docs/PCS_PLATFORM_WORKSTREAM_REPORT.md`, `proof-carrying-science-site/docs/evidence/platform-governance-v1/ARTIFACT_SHA256.json`

Remaining: Use must retain split/consent and independent replay; no universal provenance or human-data validity inferred.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 45 — Implement withdrawal and deletion accounting

**Status: PARTIAL.**

Acceptance: The platform can accurately explain what data was deleted, retained, exported, or previously used, with enforceable controls for future use.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Actual deletion receipt quarantines export/dataset/checkpoint descendants and denies future ledger-aware use; no silent checkpoint rewrite.

Changed files: `proof-carrying-science-site/public/bridge-builder-core.mjs`, `proof-carrying-science-site/public/research-governance-core.mjs`, `proof-carrying-science-site/scripts/browser_platform_governance.cjs`, `proof-carrying-science-site/scripts/d1_reconcile.py`, `proof-carrying-science-site/scripts/research_lineage.py`, `proof-carrying-science-site/src/worker.js`

Tests: 33 real Worker/browser controls; five Node and five Python focused tests; actual synthetic game replay/training/withdrawal; populated local backup/restore (zero humans, zero production D1 mutations)

Evidence: `proof-carrying-science-site/src/worker.js`, `proof-carrying-science-site/docs/PCS_PLATFORM_WORKSTREAM_REPORT.md`, `proof-carrying-science-site/docs/evidence/platform-governance-v1/ARTIFACT_SHA256.json`

Remaining: Not model unlearning, remote distributed-copy deletion or enforcement over arbitrary independent training code.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 46 — Develop adaptive educational curricula

**Status: PARTIAL.**

Acceptance: Users can progress from beginner exercises toward meaningful formal proof contributions while the research evaluation firewall remains intact.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Implemented replay-driven practice progression and real keyboard next-challenge navigation, all games remain selectable.

Changed files: `proof-carrying-science-site/public/bridge-builder-core.mjs`, `proof-carrying-science-site/public/research-governance-core.mjs`, `proof-carrying-science-site/scripts/browser_platform_governance.cjs`, `proof-carrying-science-site/scripts/d1_reconcile.py`, `proof-carrying-science-site/scripts/research_lineage.py`, `proof-carrying-science-site/src/worker.js`

Tests: 33 real Worker/browser controls; five Node and five Python focused tests; actual synthetic game replay/training/withdrawal; populated local backup/restore (zero humans, zero production D1 mutations)

Evidence: `proof-carrying-science-site/public/memory-workshop.html`, `proof-carrying-science-site/docs/PCS_PLATFORM_WORKSTREAM_REPORT.md`, `proof-carrying-science-site/docs/evidence/platform-governance-v1/ARTIFACT_SHA256.json`

Remaining: Local practice completion grants no account skill or research authority; no human engagement/curriculum efficacy study.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 47 — Demonstrate actual game-to-model transfer

**Status: BLOCKED.**

Acceptance: A reproducible experiment establishes whether gameplay-derived training examples improve performance, or documents a genuine negative result.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Synthetic browser→D1→Owner export→fresh Lean intake→12 gradient steps→saved 14,773-parameter candidate executed.

Changed files: `proof-carrying-science-site/public/bridge-builder-core.mjs`, `proof-carrying-science-site/public/research-governance-core.mjs`, `proof-carrying-science-site/scripts/browser_platform_governance.cjs`, `proof-carrying-science-site/scripts/d1_reconcile.py`, `proof-carrying-science-site/scripts/research_lineage.py`, `proof-carrying-science-site/src/worker.js`

Tests: 33 real Worker/browser controls; five Node and five Python focused tests; actual synthetic game replay/training/withdrawal; populated local backup/restore (zero humans, zero production D1 mutations)

Evidence: `proof-carrying-science/research/verified-memory-integration/ARTIFACT_SHA256.json`, `proof-carrying-science-site/docs/PCS_PLATFORM_WORKSTREAM_REPORT.md`, `proof-carrying-science-site/docs/evidence/platform-governance-v1/ARTIFACT_SHA256.json`

Remaining: Zero genuine human participants and no held-out transfer evaluation; actual human-game-to-model efficacy remains blocked by absent consented participation.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 48 — Run an authorization attack campaign

**Status: PARTIAL.**

Acceptance: Known attack classes are rejected and critical findings are repaired.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Actual 33-check Worker/browser campaign rejected unauthorized role/review/export/consent/catalog changes and repaired administrator self-review gap.

Changed files: `proof-carrying-science-site/public/bridge-builder-core.mjs`, `proof-carrying-science-site/public/research-governance-core.mjs`, `proof-carrying-science-site/scripts/browser_platform_governance.cjs`, `proof-carrying-science-site/scripts/d1_reconcile.py`, `proof-carrying-science-site/scripts/research_lineage.py`, `proof-carrying-science-site/src/worker.js`, `pcs/signing_policy_v1.py`, `scripts/exercise_signing_recovery.py`, `tests/test_signing_policy_v1.py`, `tests/test_signing_recovery_drill.py`

Tests: 33 real Worker/browser controls; five Node and five Python focused tests; actual synthetic game replay/training/withdrawal; populated local backup/restore (zero humans, zero production D1 mutations); 44 focused tests and 17 real cryptographic drill controls passed (ephemeral test keys, not production custody)

Evidence: `proof-carrying-science/tests/test_adversarial_v06_hardening.py`, `proof-carrying-science-site/docs/PCS_PLATFORM_WORKSTREAM_REPORT.md`, `proof-carrying-science-site/docs/evidence/platform-governance-v1/ARTIFACT_SHA256.json`, `proof-carrying-science/research/platform-security-v1/signing-recovery.json`, `proof-carrying-science/docs/SIGNING_POLICY_AND_RECOVERY_V1.md`

Remaining: Not exhaustive security assurance or a penetration test of live production; final protected checks pending.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 49 — Verify signing-key lifecycle controls

**Status: PARTIAL.**

Acceptance: Key lifecycle behavior is documented, tested, and bound to actual verification outcomes.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: 44 focused signing/lifecycle tests and 17 actual encrypted-key/Ed25519/rotation/compromise/recovery controls passed on ephemeral test identities.

Changed files: `pcs/signing_policy_v1.py`, `scripts/exercise_signing_recovery.py`, `tests/test_signing_policy_v1.py`, `tests/test_signing_recovery_drill.py`

Tests: 44 focused tests and 17 real cryptographic drill controls passed (ephemeral test keys, not production custody)

Evidence: `proof-carrying-science/pcs/key_lifecycle.py`, `proof-carrying-science/research/platform-security-v1/signing-recovery.json`, `proof-carrying-science/docs/SIGNING_POLICY_AND_RECOVERY_V1.md`

Remaining: Production root/key custody and revision-floor distribution remain owner operational responsibilities.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 50 — Validate recovery and incident response

**Status: PARTIAL.**

Acceptance: Critical research-platform state can be restored in a test environment with documented recovery evidence.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Actual populated local D1 online backup/restore and transaction rollback plus isolated encrypted signing recovery succeeded.

Changed files: `proof-carrying-science-site/public/bridge-builder-core.mjs`, `proof-carrying-science-site/public/research-governance-core.mjs`, `proof-carrying-science-site/scripts/browser_platform_governance.cjs`, `proof-carrying-science-site/scripts/d1_reconcile.py`, `proof-carrying-science-site/scripts/research_lineage.py`, `proof-carrying-science-site/src/worker.js`, `pcs/signing_policy_v1.py`, `scripts/exercise_signing_recovery.py`, `tests/test_signing_policy_v1.py`, `tests/test_signing_recovery_drill.py`

Tests: 33 real Worker/browser controls; five Node and five Python focused tests; actual synthetic game replay/training/withdrawal; populated local backup/restore (zero humans, zero production D1 mutations); 44 focused tests and 17 real cryptographic drill controls passed (ephemeral test keys, not production custody)

Evidence: `proof-carrying-science/docs/RELEASE_AND_INCIDENT_RESPONSE.md`, `proof-carrying-science-site/docs/PCS_PLATFORM_WORKSTREAM_REPORT.md`, `proof-carrying-science-site/docs/evidence/platform-governance-v1/ARTIFACT_SHA256.json`, `proof-carrying-science/research/platform-security-v1/signing-recovery.json`, `proof-carrying-science/docs/SIGNING_POLICY_AND_RECOVERY_V1.md`

Remaining: No remote production backup restoration, Worker rollback or complete hosted-job disaster recovery demonstrated.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 51 — Strengthen supply-chain attestations

**Status: PARTIAL.**

Acceptance: Released artifacts have inspectable provenance and tampering can be detected.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Exact source, action/dependency manifests, artifact SHA seals, fixed recipe/log binding and trusted-verifier distinction implemented.

Changed files: `pcs/release_qualification_v1.py`, `pcs/schemas/release-qualification-v1.schema.json`, `pcs/signing_policy_v1.py`, `scripts/exercise_signing_recovery.py`, `scripts/qualify_release.py`, `tests/test_release_qualification_v1.py`, `tests/test_signing_policy_v1.py`, `tests/test_signing_recovery_drill.py`

Tests: 21 passed; no missing gate promoted (local focused); 44 focused tests and 17 real cryptographic drill controls passed (ephemeral test keys, not production custody)

Evidence: `proof-carrying-science/pcs/release_qualification_v1.py`, `proof-carrying-science/docs/evidence/platform-baseline-v1/qualification-focused-final.log`, `proof-carrying-science/research/platform-security-v1/signing-recovery.json`, `proof-carrying-science/docs/SIGNING_POLICY_AND_RECOVERY_V1.md`

Remaining: Unsigned local records are not provider-signed supply-chain attestations or release authorization.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 52 — Audit source and dataset rights

**Status: PARTIAL.**

Acceptance: Technically identifiable rights/provenance issues are cataloged and engineering-controlled distribution restrictions are enforced where appropriate.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Technical inventory hashes tracked and nonignored overlay rights/dependency/workflow/research material; existing first-party licensing preserved.

Changed files: `pcs/release_qualification_v1.py`, `pcs/schemas/release-qualification-v1.schema.json`, `scripts/inventory_release_provenance.py`, `scripts/qualify_release.py`, `tests/test_release_provenance_inventory.py`, `tests/test_release_qualification_v1.py`

Tests: 21 passed; no missing gate promoted (local focused)

Evidence: `proof-carrying-science/docs/PUBLIC_RELEASE_RIGHTS_LEDGER.md`, `proof-carrying-science/docs/evidence/platform-baseline-v1/qualification-focused-final.log`, `proof-carrying-science/docs/PCS_RELEASE_PROVENANCE_INVENTORY.json`

Remaining: Transitive, asset, contributor and institutional legal clearance not inferred; no unsupported distribution permission.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 53 — Strengthen evaluation firewalls

**Status: PARTIAL.**

Acceptance: Benchmark provenance and leakage controls are independently testable, with no misleading claims about private or untouched evaluation sets.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: New public authored partitions and explicit source/exposure/contamination controls retained; historical public test limitations disclosed.

Changed files: `pcs/experimental/prover/abstraction_repair_v2.py`, `pcs/experimental/prover/checkpoint_transfer_v2.py`, `pcs/experimental/prover/hybrid.py`, `pcs/experimental/prover/mathlib_retrieval.py`, `pcs/experimental/prover/promotion.py`, `pcs/experimental/prover/prospective_hybrid.py`, `pcs/experimental/prover/state_graph.py`

Tests: Actual completed receipt files preserved; ongoing results require final experiment report, no planned result counted (public authored partitions; no new model superiority claim)

Evidence: `proof-carrying-science/pcs/experimental/prover/data.py`, `proof-carrying-science/research/prospective-hybrid-v2/protocol.json`, `proof-carrying-science/research/prospective-hybrid-v2/summary.json`, `proof-carrying-science/research/abstraction-repair-v2/protocol.json`

Remaining: No truly private untouched external evaluation exists here; public benchmark exposure is not hidden.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 54 — Reconcile public status and reality

**Status: PARTIAL.**

Acceptance: The public website accurately describes which capabilities have been demonstrated, their scope, and their limitations.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Reports separate historical, fresh local, provider CI and live statuses, negative results and numerical OPEN authority.

Changed files: Historical source retained; no new corresponding implementation claimed.

Tests: No new completed acceptance run; historical/source inventory is not a fresh test.

Evidence: `proof-carrying-science-site/public/status.json`

Remaining: New exact production website/source status pending final protected deployment evidence.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 55 — Build a general scientific reasoning agent

**Status: PARTIAL.**

Acceptance: PCS can execute a multi-obligation scientific reasoning workflow, including meaningful failures and independently checkable intermediate results, with no unsupported claim of autonomous scientific discovery.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Real bounded dependent scientific investigation preserves failure, checked witnesses and separately rechecked repair proposal under original typed contract.

Changed files: `pcs/scientific_assurance_v1.py`, `pcs/scientific_contracts_v1.py`, `pcs/scientific_obligations_v1.py`, `pcs/scientific_research_v1.py`, `scripts/replay_scientific_bundle_v1.py`, `scripts/run_scientific_assurance_v1.py`

Tests: 37 focused tests passed; three fresh scientific receiver processes; eight bounded numerical predicates PASS (synthetic authored computational science, not clinical validity)

Evidence: `proof-carrying-science/pcs/scheduler_v06.py`, `proof-carrying-science/research/scientific-assurance-v1/SUMMARY.json`, `proof-carrying-science/research/scientific-assurance-v1/ARTIFACT_SHA256.json`, `proof-carrying-science/docs/PCS_SCIENTIFIC_WORKSTREAM_REPORT.md`

Remaining: Deterministic bounded planner, not general autonomous scientific discovery or learned advantage.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 56 — Integrate a real AI-safety assurance adapter

**Status: PARTIAL.**

Acceptance: One bounded AI-agent safety case is represented as explicit proof obligations and checked evidence, without overstating guarantees.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Existing bounded reference-monitor/trace/AI-safety adapters and formal contracts preserved.

Changed files: Historical source retained; no new corresponding implementation claimed.

Tests: No new completed acceptance run; historical/source inventory is not a fresh test.

Evidence: `proof-carrying-science/pcs/control_monitor_v1.py`

Remaining: No new independently executed multi-obligation deployed AI-agent safety case in this workstream.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 57 — Build a computational biology assurance library

**Status: COMPLETE_TESTED.**

Acceptance: At least one substantive computational-biology case study uses multiple reusable PCS domain contracts with independently checkable evidence.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Substantive authored three-species/two-reaction biochemical library case uses eight independently replayed bounded predicates and actual signed authority packages.

Changed files: `pcs/scientific_assurance_v1.py`, `pcs/scientific_contracts_v1.py`, `pcs/scientific_obligations_v1.py`, `pcs/scientific_research_v1.py`, `scripts/replay_scientific_bundle_v1.py`, `scripts/run_scientific_assurance_v1.py`

Tests: 37 focused tests passed; three fresh scientific receiver processes; eight bounded numerical predicates PASS (synthetic authored computational science, not clinical validity)

Evidence: `proof-carrying-science/pcs/adapters/pkpd.py`, `proof-carrying-science/research/scientific-assurance-v1/SUMMARY.json`, `proof-carrying-science/research/scientific-assurance-v1/ARTIFACT_SHA256.json`, `proof-carrying-science/docs/PCS_SCIENTIFIC_WORKSTREAM_REPORT.md`

Remaining: Synthetic kinetic assumptions explicit; numerical claim remains OPEN in PCS, no empirical/clinical validity or continuous solver guarantee.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 58 — Investigate stronger proof-search architectures

**Status: PARTIAL.**

Acceptance: At least one new architecture or search strategy is implemented, ablated, and evaluated rigorously; superiority is claimed only if supported.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Implemented actual hybrid search/state-graph/retrieval and scoped abstraction architecture experiments with explicit baselines/ablations.

Changed files: `pcs/experimental/prover/abstraction_repair_v2.py`, `pcs/experimental/prover/checkpoint_transfer_v2.py`, `pcs/experimental/prover/hybrid.py`, `pcs/experimental/prover/mathlib_retrieval.py`, `pcs/experimental/prover/promotion.py`, `pcs/experimental/prover/prospective_hybrid.py`, `pcs/experimental/prover/state_graph.py`

Tests: Actual completed receipt files preserved; ongoing results require final experiment report, no planned result counted (public authored partitions; no new model superiority claim)

Evidence: `proof-carrying-science/pcs/experimental/prover/prospective_hybrid.py`, `proof-carrying-science/research/prospective-hybrid-v2/protocol.json`, `proof-carrying-science/research/prospective-hybrid-v2/summary.json`, `proof-carrying-science/research/abstraction-repair-v2/protocol.json`

Remaining: Final experiments still being completed; no preclaimed superiority or breakthrough from a small authored corpus.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.

## Task 59 — Implement cross-project verification contracts

**Status: PARTIAL.**

Acceptance: At least two substantive PCS components exchange independently checkable proof/evidence contracts end-to-end, with invalid and mismatched cases rejected.

Existing functionality: Existing bounded source/artifacts identified; presence is not completion.

New implementation: Existing PCS compiled authority and signed numerical validator exchange exact evidence contracts; false/mismatched reports rejected in fresh processes.

Changed files: `pcs/scientific_assurance_v1.py`, `pcs/scientific_contracts_v1.py`, `pcs/scientific_obligations_v1.py`, `pcs/scientific_research_v1.py`, `scripts/replay_scientific_bundle_v1.py`, `scripts/run_scientific_assurance_v1.py`

Tests: 37 focused tests passed; three fresh scientific receiver processes; eight bounded numerical predicates PASS (synthetic authored computational science, not clinical validity)

Evidence: `proof-carrying-science/pcs/certiforge_adapter_v1.py`, `proof-carrying-science/pcs/scientific_contracts_v1.py`, `proof-carrying-science/research/scientific-assurance-v1/SUMMARY.json`, `proof-carrying-science/research/scientific-assurance-v1/ARTIFACT_SHA256.json`, `proof-carrying-science/docs/PCS_SCIENTIFIC_WORKSTREAM_REPORT.md`

Remaining: Cross-project broad model/CertiForge transfers and source-level scientific adapter correspondence remain partial.

Commit/PR: final protected integration pending; exact baseline and source-overlay digests retained in machine-readable evidence.


The latest integration delta adds a persistent request journal, explicit browser recovery/cancellation, finite source-correlated operational events and a selectable independently replayed hybrid portfolio. Three fixed Lean diagnostic commands passed locally; ten owner-hosted diagnostic jobs remain distinct from public Worker admissions. CertiForge PR #3 passed protected CI and merged as `c71e8575db2800b015a9d444f8ed572490f3a871` with an identical tested tree.
