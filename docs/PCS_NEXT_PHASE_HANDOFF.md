# PCS next-phase technical handoff

Prepared October 14, 2026, for a new Codex GPT-6.1 Sol High session. This is a source-grounded handoff, not a new scientific result or authorization to begin the next integration in the old conversation.

## 1. Read this first

PCS has an executable proof-carrying research platform, real Lean proof-state search, trained neural policies, sequential RL, bounded scientific adapters, checked CertiForge integration, public research games, and hosted proof jobs. It does **not** yet demonstrate general scientific intelligence, broad English-to-Lean fidelity, neural superiority, beneficial autonomous abstraction, empirical scientific acceptance, or human-game-to-model transfer.

The next assignment is to integrate **new Aristotle results and separately developed proof-carrying formal verification / AI-safety work** into this existing platform. The new results are not supplied or integrated by this handoff. Start from protected main, inventory the new artifacts, compare source and theorem identities, and coordinate independent workstreams without competing authorities. Do not restart the 59-task program or overwrite prior research evidence.

Priority reading:

1. This document, including the 59-task table and source-conflict checklist.
2. [Mathlib v4](PCS_MATHLIB_GENERALIZATION_V4_REPORT.md), [learning/RL](PCS_LEARNING_AND_RL_V4_REPORT.md), [abstraction](PCS_VERIFIED_ABSTRACTION_V4_REPORT.md).
3. [Formal assurance](PCS_FORMAL_ASSURANCE_AND_REFINEMENT_REPORT.md), [Rust checked wrapper](PCS_RUNTIME_CHECKED_BOUNDARY_REPORT.md), [Rust output continuation](PCS_RUNTIME_REFINEMENT_CONTINUATION_REPORT.md).
4. [Scientific continuation](PCS_SCIENTIFIC_PLATFORM_CONTINUATION_REPORT.md), [real-data workflow](PCS_SCIENTIFIC_WORKFLOW_V2_REPORT.md).
5. [Original program ledger](PCS_59_WORKSTREAM_IMPLEMENTATION_LEDGER.json), [v3 reconciled source ledger](PCS_59_WORKSTREAM_RECONCILED_LEDGER_V3.json), and the [preserved final v4 release overlay](evidence/next-phase-handoff-v1/59-workstream-release-overlay-v4.json).

Evidence precedence: exact executed artifacts and qualified source identities take precedence over a summary, filename, plan, returned Aristotle log, or stale pre-merge status. A merged implementation does not automatically satisfy its research acceptance criterion. Historical reports are dated snapshots; their earlier absence-of-capability statements and pending-release fields are not current capability inventories.

## 2. Exact protected baseline and final release

Read-only `git ls-remote origin refs/heads/main` on October 14 confirmed:

| Repository | Protected main at handoff baseline | Last functional integration |
| --- | --- | --- |
| `Tommaso-R-Marena/proof-carrying-science` | `c600b007940881fd65fe41d2adddd5f002679478` | [PR #107](https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/107) |
| `Tommaso-R-Marena/proof-carrying-science-site` | `a6a9a54bb8f2e8fb45f783a9df56929aca11a54b` | [PR #118](https://github.com/Tommaso-R-Marena/proof-carrying-science-site/pull/118) |
| `Tommaso-R-Marena/certiforge` | `c71e8575db2800b015a9d444f8ed572490f3a871` | [PR #3](https://github.com/Tommaso-R-Marena/certiforge/pull/3) |

These are the functional release commits before this documentation change. The handoff's own subsequent commit cannot be embedded in its bytes; resolve the document's commit with `git log -1 --format=%H -- docs/PCS_NEXT_PHASE_HANDOFF.md`, and refresh all default branches on entry to the new chat.

Core qualified head `a4b62f6ea5fdc87ee04c5baabad200441c8234c8` and merged tree `bdd7d7dd5cecf5155d3b46504e47628999659f5e` were identical. Owner merge: October 13, 18:01:04 UTC. All ten jobs passed in [run 38434608784](https://github.com/Tommaso-R-Marena/proof-carrying-science/actions/runs/38434608784). Website qualified head `2cf71fab72e4041c81c7a4d3a7ca80fc14ea4ce4` and merged tree `b122e784747d1a0173ee4f1cfb468da3b653623b` were identical. Owner merge: October 13, 18:21:06 UTC. Its five final protected contexts passed; final full-gate run was [38444081859](https://github.com/Tommaso-R-Marena/proof-carrying-science-site/actions/runs/38444081859). Both mergers were `Tommaso-R-Marena`.

Cloudflare website build `2c5194b9-64c5-4655-a778-af5acf0895ae` succeeded for that website commit. Seventeen changed public assets were byte-matched to main; all nine binding names/types and compatibility settings were preserved. No production database migration, signing-root rotation, paid subscription, or financial expenditure occurred.

The live site is `https://proof-carrying-science-site.marenatommaso.workers.dev`. A normal public hosted proof request `50c85b208510ba354287d5733dd1f9f9` completed in [run 38446831405](https://github.com/Tommaso-R-Marena/proof-carrying-science/actions/runs/38446831405): five proof actions, native API log equal to the returned record, authored meaning fixed before dispatch, fresh receiving kernel replay in 33.951 seconds, no axioms. Same-key retry reused its ticket. This is a **known-family operational test**, using `prospective-hybrid-v2`, not a blind theorem benchmark or promotion of a new v4 model.

A portable [final release receipt](evidence/next-phase-handoff-v1/mathlib-v4-final-release.json) preserves those observations. Detailed provider logs remain local, listed below. Previous qualified snapshots include core `b59badd68cedba3dcc9c72a6d5148e7986545ebd` / site `738da43fbdb840ab258dcda7d41861126df15559` (PRs #106/#117), and core `fd4ddaf8e106cfb37ced3bd1dc5cffe568f1c722` (PR #105). Do not reinterpret their historical metrics as the v4 run.

## 3. Environment, identity, and authorization

The retained workspace has `/workspace/proof-carrying-science`, `/workspace/proof-carrying-science-site`, `/workspace/certiforge`. At the start of this handoff all three were on main with clean tracked/untracked status. No `AGENTS.md` was found in the initial repository inventory. Recheck instructions and user changes in a new environment; never reset unknown work.

```bash
source /workspace/.onboarding/activate.sh
cd /workspace/proof-carrying-science
source scripts/activate_lean_428.sh
```

Retained tool versions: Python 3.12.14, Node 22.23.3, Torch 2.7.1+cpu, NumPy 2.2.6, Rust 1.99.0, Lean 4.28.0. Mathlib is exactly `8f9d9cff6bd728b17a24e163c9402775d9e6a365`. CertiForge's independent formal project retains Lean **4.16.0**. Never change the global Lean default to reconcile these projects. The previous research machine used four CPUs / 32 GiB cgroup memory and two Torch threads; these are environment observations, not future guarantees. No GPU is required or was paid for.

User authorization remains:

- Work only in the named owner repositories; author, push, and merge as `Tommaso-R-Marena`, email `211279622+Tommaso-R-Marena@users.noreply.github.com`. Verify authenticated identity before mutations.
- Normal protected PRs/CI/merges are authorized. No admin bypass, weakened gate, fabricated reviewer, or direct protected-main push.
- **Do not spend any money, input financial information, subscribe, or make paid compute mandatory.** Public standard Actions and existing free infrastructure were used. Unlimited minutes is not authorization for paid runners or additional services.
- First-party publication was explicitly authorized; third-party licensing/attribution still applies. Never publish production credentials or private data.
- New trusted-component changes require independent verification and the human-controlled protected release boundary. A model cannot authorize changes to kernels, acceptance rules, signing roots, hidden evaluation answers, or its own evaluator.

Reusable cloud install/start instructions were saved in an environment draft, retaining network/secure bindings; this does not itself prove publication or restoration in a fresh task. Helpers are under `/workspace/.onboarding/`. Startup processes and authentication must be rechecked after restoration. This handoff does not require a configuration change. Prefer existing checkouts; do not create worktrees merely for onboarding.

Git HTTPS proxy access may work without a raw environment token. Test the specific required operation before asking for new secrets. Inspect binding names/presence only, never values. `PCS_LEAN_GITHUB_TOKEN` is the Worker secret for restricted hosted jobs; it is not a license to expose GitHub credentials to policies or submitted Lean code. Earlier HTTP 401 incidents were handled by secure refresh/reconnection; an administrative 403 can be a scope limitation rather than loss of authentication.

## 4. Architecture and evidence boundaries

### 4.1 Scientific/package authority

`pcs/` implements Claim IR, proof-obligation/dependency analysis, versioned acceptance policies, evidence commitments, canonical package/manifest/certificate projections, domain-separated hashes, Ed25519 signatures, normalized decisions, replay, key lifecycle, environment/workflow capture, and scoped persistent receipt authority. Principal runtime files include:

- `package_v06.py`, `verifier_v06.py`, `verifier_zip_v06.py`, `verifier_io_v06.py`, `verifier_entrypoint.py`.
- `normalized_wire_v06.py`, `normalized_set_v06.py`, `receipt_contract_v06.py`, `receipt_signature_v06.py`, `signing_v06.py`, `signing_policy_v1.py`, `key_lifecycle.py`.
- `lean_authority_v06.py`, `semantic_authority_v3.py`, `semantic_claim_binding_v1.py`, `semantic_kernel_bridge_v1.py`.
- `scientific_contracts_v1.py`, `scientific_obligations_v1.py`, `scientific_assurance_v1.py`, `scientific_research_v1.py`, `scientific_workflow_v2.py`, `scientific_workflow_v3.py`.
- `pcs/schemas/`, `formal/PCS/`, `formal/PCS/V2/`, `formal/PCSAuthority.lean`, `formal/PCSSemanticCheck.lean`.

The receiving verifier, not the producer/model, determines support. Signed package integrity is distinct from scientific claim support. An authentically signed false report remains false. Formalized claim graphs require sound leaves **and** sound decomposition rules, exact claim/evidence bindings, resolved dependencies, and rejection of cycles/duplicates/unsupported nodes. Changed source, data, assumptions, checker configuration or relevant provenance invalidate dependent assurance rather than silently reusing a receipt.

Canonical bytes, cryptographic attribution, source correspondence, formal propositions, finite computational support, and real-world adequacy are separate layers. Unsupported empirical, causal, numerical, clinical, population, provenance, or human-intent claims must remain **OPEN**. Never infer a scientifically accepted workflow merely from package `ACCEPT`.

### 4.2 Semantic translation and persistent receipts

`PCS.V2.Semantic` v1/v2/v3 and the `pcs_semantic` implementation provide restricted typed interpretations, deterministic explanations, bounded equivalence/countermodels, explicit translation versus strengthening, role-separated signed receipts, elaboration/proof requirements, trusted clock/registry, expiration/revocation, and single-use nonces. `pcs semantic-authority-v3` binds approved checker/configuration/ClaimIR hashes to the exact request, uses scoped SQLite, and reports certification only after COMMIT. Published fixture keys are rejected by default; explicit fixture mode is nonproduction. The v1 bridge remains stateless and nonproduction.

The model's ranking cannot establish semantic equivalence. These interfaces do not prove human intent or empirical truth and report scientific authority false. Issuer tools actually elaborate/replay Lean before signing but are **not** a sandbox for arbitrary Lean/meta code. An isolated production issuer, protected role keys, approved meanings, trusted clock and storage remain operational prerequisites. The Lean ledger theorem is not a theorem about SQLite, OS fsync, Python, cryptographic libraries, or browser behavior.

### 4.3 Bounded symbolic intelligence

`pcs/experimental/` retains Omega v1/v2 Boolean repair/ranking, counterexample-guided best-first search, independently replayed episodes, assumption-aware BDD checking, exact positive-cost intervention planning, and assumption discovery. Their website counterparts include `public/conditional-core.mjs`, `intervention-core.mjs`, Omega and repair modules. False-before-True enumeration and lexicographically least witnesses, inconsistent-premise nonvacuity, operation budgets, optimum/count/masks, and resource-limit outcomes are explicit contracts.

Omega's tiny 38-, 91-, and 1,165-parameter baselines are preserved. Fixed AST-message features and one-step contextual REINFORCE are historical bounded baselines; the latter is a bandit, not long-horizon proof RL. Larger Boolean instances are not evidence of general mathematical intelligence.

### 4.4 Actual Lean learning/search

`pcs/experimental/prover/` contains typed mathematical IR/language, actual structured Lean workers, constrained action rendering, immutable-goal search, independent final compilation, JSON checkpoints, real graph models, trained 4,452-parameter restricted interpretation ranking, checked libraries, induction, abstraction/discovery, verified memory, hybrid search, dataset/provenance firewalls, promotion checks, sequential reward environments, bounded research planning, and public job transport.

Important entry points include `environment.py`, `language.py`, `library.py`, `induction_ir.py`, `state_graph.py`, `dag_policy_v3.py`, `premise_policy_v4.py`, `mathlib_environment_v4.py`, `mathlib_cli_v4.py`, `research.py`, `optimization.py`, `promotion.py`, `public_job.py`, `public_transport.py`, `server.py`. Versioned experiments are intentionally retained side by side.

Theorem statements are immutable; policies choose typed actions, not shell commands or declaration edits. Actual Lean states drive observations/errors/rewards. Final proofs compile independently against the original statement; merely parsing/elaborating a declaration or closing one subgoal is insufficient. Unsupported language, ambiguous interpretations, invalid actions, counterexamples, missing assumptions, resource exhaustion and UNKNOWN are not converted to success.

The bounded research scheduler can execute explicit dependency plans and reuse independently admitted prerequisites. It is not a learned autonomous investigator, literature authority, or demonstrated discovery of novel mathematics. Verified intermediate facts remain distinguishable from hypotheses and failed strategies.

### 4.5 CertiForge

The Rust workspace provides typed CertIR, interpretation, admissible rewrite optimization, static costs, packages, and independent checking. `pcs` adapters bind actual component/checker identities. Native exhaustive u8 tests, source-subset Lean proofs, and native compiler correctness are separate assurances. Effects/control flow/unrestricted domains are not implicitly supported.

The learned optimization experiment in `pcs/experimental/prover/optimization.py` actually trains a compact 14→24→1 policy (385 parameters), ranks candidates, and asks the independent pinned native checker to verify all 65,536 u8 input pairs. It is not general optimization RL, universal large-domain Lean proof, or measured runtime acceleration. Consult the optimization artifacts in `research/lean-learning-v1/` and the consolidated report for its fixed tasks/results; do not manufacture broader superiority.

## 5. Formal verification and Aristotle integration

### 5.1 Proof acceptance and residual TCB

Admitted mathematical proofs use ordinary Lean kernel checking with transitive axioms contained in `propext`, `Classical.choice`, `Quot.sound` (or fewer). No `sorry`, `admit`, unapproved axiom, `native_decide`, `Lean.ofReduceBool`, or escape hatch can authorize a mathematical result. Failed elaboration logs may contain Lean's internal `sorryAx`; those runs are rejected, never positive evidence.

This is a requirement on admitted pure proofs, **not** a false assertion that all worker I/O is safe/pure: unsafe transport implementation exists outside the proof acceptance boundary. Compiler/runtime/OS/filesystem/I/O correspondence remains operational trust. The exact [audit-source index](evidence/next-phase-handoff-v1/formal-audit-source-index.json) records 20 sources, their SHA-256s and 2,212 `#print axioms` target occurrences; repeated/helper targets are not distinct scientific results. It is a source index, not a new kernel run. Executed audit logs and protected CI are the evidence of checking.

### 5.2 Established package, generic-domain and AI-safety results

Read `formal/PCS_FULL_FORMALIZATION_REPORT.md` alongside the authoritative later `PCS_FRONTIER_FORMALIZATION_REPORT.md`; the older list of TCB gaps is partly superseded. Significant exact identities include:

| Module / identity | Established result and boundary |
| --- | --- |
| `PCS.V2.Json`, `Canonical`, `Hex`, `Base64`, `Binding`, `NormalizedWire`, `Index`, `Package`, `Archive` | Canonical serialization/parser inversion/uniqueness, safe-integer subset, exact schema/scope/evidence commitments, domain-separated hash binding up to explicit collisions, signed package member completeness, archive no-duplicate/traversal/alias guarantees. See exact names in `formal/PCS/V2/Audit.lean` and full report. These are Lean functions, not whole Python correspondence. |
| `PCS.V2.SHA256Spec.sha256_eq_fips1804` (`SHA256Spec.lean`) | Lean SHA-256 equals an independent bit-level FIPS 180-4 specification, with stated admissible length boundary. This does not prove cryptographic collision resistance or Python library refinement. |
| `PCS.V2.Frontier.pcs_frontier_archive_acceptance_sound`, `pcs_unsigned_acceptance_yields_forgery` (`Frontier.lean`) | Canonical STORED raw archives, declared verified environment/workflow/builtin meanings; headline authenticity retains `NoForgery` for the actual verifier/key. Captured facts outside `EnvFacts` and unchecked source analysis do not follow. |
| `PCS.V2.Checkers.builtinExecWith_faithful` | Actual verified builtins for reaction balance, unit compatibility, strict CSV disjointness and PK/PD contracts/reference/table threshold checks. Unsupported tags do not gain certified predicate meaning. |
| `PCS.V2.Zip.leanZip_faithful` | Lean canonical STORED ZIP decoding; not a universal arbitrary ZIP/native decompression correspondence theorem. |
| `PCSReal.PKPD.pcs_pkpd_reference_match_real` (`formal/real/PCSReal/PKPD.lean`) | Mathlib real-valued analytic PK/PD reference bridge through certified intervals. Table peak thresholds are not continuous-time Cmax or clinical safety. |
| `PCS.V2.ClaimGraph.root_assurance_sound`, `accepted_graph_facts` (`ClaimGraph.lean`) | Root semantics from sound leaf checker and decomposition rules, well-formed resolved finite graph. Unsound rules/leaf validators have preserved counterexamples. |
| `PCS.V2.DomainAdapter.domain_adapter_sound`; `PCS.V2.Proposer.untrusted_proposer_cannot_forge_assurance`; `PCS.V2.WorkflowRefinement.pipeline_refines`, `pipeline_total` | Generic explicit adapter/refinement contracts; untrusted proposals have no authority. Totality/refinement assumptions are required, not inferred from a plugin API. |
| `PCS.V2.DomainAuthority.pcs_generic_domain_archive_acceptance_sound`, `_with`, `executableAuthority_refines_certifiedAuthority`, `executableAuthority_sound`, `executableAuthority_domain_sound` | Certified checker registry on executable path, unique tags/no builtin shadowing, actual domain semantics. Attribution uses `NoForgery`; external unhandled evidence needs its explicit replay contract. |
| `PCS.V2.ExecutableGeneral.executableAuthority_registered_evidence_sound`, `executableAuthority_trace_evidence_sound`, `executableAuthority_rejects_unsafe_trace_evidence`, `executableAuthority_trace_claim_sound`, `executableAuthority_deployed_trace_safe` | Arbitrary accepted archives: certified-tag PASS implies the specified invariant of committed trace bytes. Claim-level coverage is explicit; deployed-run safety additionally requires `FaithfulLog`. |
| `PCS.V2.Golden.aiSafetyGoldenArchive_accepts`, `_entries_accepts`, `_committed_safe`, `_deployed_safe`; `pcsLeanAuthority_golden_zip_output`, `_dir_output` | Kernel-checked golden AI-safety archive/literals/CLI verdict and committed safety. Published RFC fixture secret cannot support `NoForgery`; deployed safety needs faithful logging. Exact audit in `formal/PCS/V2/Golden/Audit.lean`. |

The actual RFC 8032 equivalence proof for the Lean Ed25519 implementation remains **open**. A definitional equality to its own specification is not cryptographic implementation correctness. Pure byte safety does not require attribution, but attributing a signer requires unforgeability/honest custody. A public fixture signing key makes that attribution hypothesis false.

Preserved counterexamples show why `ACCEPT` alone, certified evidence reporting FAIL, an uncertified transcript saying PASS, a weaker leaf, lossy obligation compilation, or a safe committed trace with unfaithful deployed logging cannot establish the stronger claim. Relevant files: `GenericCounterexamples.lean`, `ExecutableLimits.lean`, `ExternalWorld.lean`, `Witnesses/AISafetyCampaign.lean`, `Golden/`, `FailClosedAudit.lean`. See `formal/PCS_GENERIC_DOMAIN_SOUNDNESS_REPORT.md`, `PCS_AI_SAFETY_EXECUTABLE_ASSURANCE_REPORT.md`, `PCS_EXECUTABLE_GENERAL_ASSURANCE_REPORT.md`, `PCS_FAIL_CLOSED_REPORT.md`.

### 5.3 Semantic v1/v2/v3 Aristotle package

The older `2a36c1d1` archive was already represented in history. The `706bde85` archive added semantic v1/v2/v3, stateful receipts, honest issuer checks and bounded CertiForge formal model; SHA-256 `51d24842e1109226466adf2c7abd519850a68b40aec19289f9df27186325dd86`. Import provenance: [ARISTOTLE_SOURCE_IMPORT_MANIFEST.json](ARISTOTLE_SOURCE_IMPORT_MANIFEST.json), [PUBLIC_INTEGRATION_2026-10-08.md](PUBLIC_INTEGRATION_2026-10-08.md). Two hundred thirty-one existing byte-identical sources were preserved; stale outputs/duplicate patches/bytecode/prompts were excluded rather than run as instructions.

Principal identities in `PCS.V2.Semantic.V3`: `pcs_v3_certified_wire_assurance` (`AssuranceV3.lean`); `decideV3_certified_iff`, `stateful_authority_refines_specification`, `decideV3_certified_preserves_denotation`, `decideV3_ignores_proposer_metadata`; `receiptPhase_ok_iff`; `stepV3_ledger`, `stepV3_rejected_no_consumption`, `stepV3_monotone`, `stepV3_replay_rejected`; `runV3_no_double_consumption`, `decideV3_restrict`; expiration/revocation/role/context/statement-substitution rejection results. Their 138/138 audit is `SemanticV3Audit.lean` / `tools/check_semantic_v3_audit.sh`. Actual integration checked 36 v1, 42 v2, 37 v3 fixtures, imported Python tests and the compiled bridge; these historical counts are not this handoff's tests.

The assurance theorem depends on explicit honest-key/receipt/meaning assumptions. Signature/hash/authentication/browser/storage/clock implementations are not all refined. Trusted SQLite serialization/durability tests are not kernel proofs of concurrent SQLite. No production semantic issuer is claimed solely from source import.

### 5.4 Countermodel, Omega and decision-diagram Aristotle work

`PCSCountermodel` has general countermodel/equivalence formalization, actual replay executable and audit (`formal/PCSCountermodel/Audit.lean`). Its Aristotle archive `241372da-f67c-441a-bc49-b30ef8de2864-aristotle.tar.gz`, run `d1f2ca07-5e0e-4389-8ad4-7c37a7ad87fe`, has SHA-256 `9815ba0c844c4978882b6a317f24f8f950cd0014e4dd5bdd2e7d65489699797b`. Exact principal contracts include `PCSCountermodel.evalBool_iff_holds`, `checker_iff`, `allWorlds_complete`, `enumeration_covers`, `search_sound`, `search_minimal`, `search_none_not_unbounded`, `lower_sound`, `namedChecker_sound`; bound/minimal enumeration is not unbounded semantic completeness. See `formal/PCSCountermodel/README.md` for namespace-resolved theorem details, independently reproduced provenance and finite Python/JavaScript comparisons. The subsequent Omega/DD run `b9577162-8244-44ff-83ca-dc7efe9d95a4` archive SHA is `5bbe5fdcae4acad3d7bbe48de26559e89bc2eae2c0681a23526e2cedf4ea95a6`. Exact returned/integrated sources: `research/aristotle-omega-dd-v1/source-manifest.json`, `source-comparison.json`, `returned-source/`; contract map: `formal/PCS_OMEGA_DECISION_DIAGRAM_REPORT.md`.

`PCSOmega/{Formula,Named,Check,Repair}.lean` proves typed evaluation, named lowering, complete False-before-True enumeration including zero variables, exact equivalence and least disagreement, remembered-witness screening, accepted-repair soundness for every ranking, and replay/work contracts. `PCSDecisionDiagram/{Diagram,Apply,Witness,Conditional,Optimal,Pass,Intervention,Validate,Summary}.lean` proves diagram validity (`validB_iff`), support/Shannon/canonicity/root-unsatisfiability, bounded memoized apply/compile with cache hits budgeted, premise-first inconsistency checking, minimal inconsistent cores/removal witnesses, conditional equivalence/least disagreement, Bellman positive-cost global optimum, distinct-optimum count, mandatory/possible masks, locked/skipped-variable behavior, lexicographically least reconstruction, one-cell/two-branch accounting, proposal gap and exact regenerated receipt rejection. General exact theorem names are in `PCSOmegaDDAudit.lean` and `PCSOmegaDDFullAudit.lean` and the handoff index.

Bounds include masks/count at most the respective `2^n` bounds and cost at most 24,000,000. Change weights must be strictly positive; a feasible unchanged baseline may have objective zero. No zero-cost-change protocol is inferred.

Mandatory controls include 24-variable De Morgan and 12 disjoint choices (minimum 12, count 4096) via diagrams. `PCSNegative/` remains outside libraries and must fail for the intended semantic reason. General reference proofs do not establish Python/JS equivalence, parser/JSON/auth/browser correctness, universal search completeness/optimality, or scientific authority.

**Portability history must be retained:** unrestricted returned-control builds exhausted memory; one public-runner attempt was cancelled after nearly two hours. Ordinary-kernel computation certificates were introduced without changing original algorithms, assertions or theorem types. `PCSReferenceCertificates/{Apply,Compile,FuelStable,Plan}.lean` checks untrusted generated proof transitions. The complete prototype audited 226 original named positive results plus 1,071 helper lemmas, and all 66 original executable controls remain required. Helpers are not new benchmark tasks. Three expensive control proof bodies use the certificates; all original 57 DD assertions, including duplicates, are enforced by overlay checks. Exact source/limits/logs are in `research/aristotle-omega-dd-v1/kernel-portability/`. Do not return to uncontrolled parallel compilation or replace kernel computation with `native_decide`.

### 5.5 Runtime-refinement and verified-learning Aristotle package

Run `27341903-5aea-4a27-bafc-15f2a94e160a`, archive `f7ad416b…`, SHA `0698d63f32ab077703ea92013f60c4a22a3c1fbfe5572e05edc77ed513c43008`. The later reported continuation runs reached time limits; no extra result is inferred. Independent import built nine new Std libraries/controls (85 jobs), reran 54 principal axiom inventories and the three separate Mathlib statistics gates. Provenance, exact source windows, fresh audits and original failed parser reproduction are retained under `research/aristotle-runtime-refinement-v1/`.

Significant modules:

- `PCSRuntimeRefinement/{PyIntervention,JsIntervention,Summary,OmegaReplay}.lean`: Python Bellman window `pcs/experimental/intervention.py` lines 33–62; JavaScript `public/intervention-core.mjs` lines 14–27; extraction/precedence/lowering certificates and safe-integer arithmetic. This covers those windows, **not the whole conditional runtimes**. Omega replay theorem is about its Lean model, not byte-bound `adaptive.py`.
- `PCSMathLanguage/{LanguageExact,IR,RoundTrip,Alpha,Goals,Receipt}.lean`: typed restricted candidate completeness/ambiguity retention, lowering, independent render/parse alpha roundtrip, immutable goals, all branches required, closed action syntax and sound final replay.
- `PCSReasoningLibrary/{Library,Search,Separation}.lean`: conservative admitted libraries/macros, checked plan composition, explicitly fair reference search completeness, admissible-cost optimality, and a synthetic reuse-family separation (quadratic bound `40(n+1)^2` versus tree `2^n`, strict at `n ≥ 13`). These are stated reference calculi/assumptions, not universal complexity improvement of deployed neural heuristics.
- `PCSAssumptionDiscovery/{Symbolic,Cegar,Receipt}.lean`: exact consistent/sufficient/locked selectors, global minimum/count/masks, necessary counterexample clauses, optimum-preserving finite CEGAR and explicit conditional assumption receipts.
- `PCSVerifiedLearning/{Episode,Shaping,Data}.lean`: proof-derived success/reverified feedback, potential shaping and duration discount, hidden-label noninterference, generation authority preservation. No model accuracy/intelligence theorem follows.
- `PCSEndToEnd/{Pipeline,Abduction}.lean`: selected-statement acceptance/replay/feedback and explicit satisfiable minimum-cost added assumptions, independent of proposal policy.
- `PCSForgeRefinement/{RustSyntax,RustSemantics,RustExtraction,Denote,Typing,Rewrite,Episode}.lean`: token/precedence-bound actual Rust expression interpreter and helpers; left-to-right evaluation, `?`, guarded match, wrapping/overflow/error paths, fuel exhaustion; rewrite typing/denotation/static cost and checker-derived optimization reward.

The complete principal theorem-to-file/status/contract table is reproduced in Appendix A from the committed returned inventory. Exact source windows and source hashes are independently checked by `scripts/verify_runtime_refinement.py`, not accepted from an archive claim.

The restricted parser recursion guard is integrated. Original Python 3.11 failure at 995 parentheses was not identical under Python 3.12.14; the latter reproduced at 1,480 parentheses / 2,985 characters. A depth >256 guard on recursive edges now returns unsupported, never an uncaught success. The 1,523 frozen Python/Lean comparisons pass, but are finite tests with formal bodies inside supported English headers, not unseen general-language fidelity or whole parser extraction.

### 5.6 Subsequent exact Rust boundary closure

Historical `eval_expr` binding covers `certir-interpreter/src/lib.rs` 14–19, 39–66, 68–77, 79–137 and `certir/src/lib.rs` 20–35. Later core proofs freshly bind `Value::ty` at 21–26, the checked wrapper at 168–179, and output continuation at 158–162, against current CertiForge `c71e…`.

A genuine precondition witness is preserved: externally constructed u8 payload 256 has the u8 type but is not canonical; `x OR x` masks to zero whereas `x` returns 256. The original rewrite theorem requires canonical `Value.WF` and is not contradicted. CertiForge PR #3 added `eval_expr_checked` and routed top-level eval through it; CLI constructor masking was already separate. Native/type-tag agreement is not canonicality.

`formal/tools/RuntimeValueType.lean` proves the extracted helper. `RuntimeCanonicalInputs.lean` explains the witness. `RuntimeCheckedBoundary.lean` proves `canonicalB_iff`, `loop_exact`, `guard_order_independent`, `checked_wrapper_refines`, `checked_certificate_preserves` under sufficient fuel and finite value-snapshot semantics. Seventeen freshly audited results, 31 native assertions across all widths, two source-mutant kernel rejections, 18 pytest gates. Exact wrapper SHA `a6463dde9f0e25f2a0e0be48b5d2c6950d291ceeb5627faa9554b150df52906b`.

`PCSRuntimeOutputBoundaryV3` (`RuntimeOutputBoundaryV3.lean`) adds nine exact results: `output_boundary_source_bound`, `derived_type_eq_exact`, `continuation_exact`, `checked_output_continuation_refines`, `output_acceptance_requires_declared_type`, `output_preserves_all_checked_errors`, `output_preserves_resource_failure`, `output_type_resource_failure`, `output_certificate_preserves`. It binds actual Width variants/equality at CertIR lines 10–17, Ty at 59–64, and output continuation; composes the checked wrapper, real value type, derived structural equality, unchanged early errors and return-type guard. Twenty-one dependency results are freshly compiled before v3; 40 native assertions and two altered-source kernel failures are separate regression evidence. See `research/runtime-refinement-v3/verification.json`.

**Still OPEN:** mutable input `HashMap`/zip/type-check/insert phase lines 140–157, whole Rust type checker/parser/runtime, deriving-macro/HashMap/compiler/native executable correspondence; Python/JS conditional principals; English rewriting/JSON/text decoding; adaptive.py source binding; broad cryptographic/authentication/browser/serialization/clock implementation correspondence. Formal payload Nat extends beyond actual u64 representability; native tests do not execute impossible payloads.

### 5.7 Statistical and proof-authority boundaries

`formal/statistics/PCSStatistics/Gates.lean` is a separate exact-Mathlib project. `PCSStatistics.paired_improvement_bound` assumes a probability measure, measurable independent task observations, common mean, bounded range, positive sample count and nonnegative margin. `PCSStatistics.GateSpec.adaptive_promotion_error_budget` and `anytime_selection_valid` require their `Valid` sampling contract, pre-registered finite candidates, per-generation bounds and summable error allocation. Pairing absorbs within-task policy correlation; multiple seeds on one task are not independent new tasks. These hypotheses are **not satisfied merely by running the public convenience benchmark**. Do not quote a formal Hoeffding bound as evidence of an empirical gain that was not observed.

`PCSProofBoundary.{certified_has_original_evidence,proposal_cannot_supply_reward,success_reward_requires_original_goal,changed_premise_requires_new_evidence}` and `PCSVerifiedMemoryBoundary.{checked_memory_holds,reuse_preserves_original_goal,ranking_cannot_authorize,changed_ranking_preserves_checked_goal,accepted_goal_is_true,failed_attempt_increases_cost}` protect reference evidence/reward interfaces. They are not entire Python memory/learning source refinements.

## 6. Mathematical intelligence: evolution, checkpoints and honest findings

### 6.1 Historical implementations retained

| Generation / artifacts | What actually runs | Negative/bounded result |
| --- | --- | --- |
| `research/omega-v1`, `omega-v2`, `conditional-v1`, `intervention-v1` | CPU Boolean models, nonlinear ranking, checked search/replay, BDD and exact intervention oracle | Narrow symbolic domains; contextual bandit is not sequential theorem RL. |
| `research/lean-learning-v1`, `lean-learning-v2` | Actual structured Lean actions, 10,419 allocated-parameter graph/bag policy/value/uncertainty network, trained restricted interpretation ranker, real multi-step proofs and actor-critic | v2 final graph seeds 4/6, 5/6, 5/6; bag 5/6 each, symbolic 5/6. No graph advantage or general English-to-Lean claim. |
| `research/checked-reuse-v1`, `checked-reuse-v2` | Real audited signatures/libraries and ReuseNetwork (11,620 parameters), verified feedback and dependency reuse | Authored small corpus, matched symbolic baselines; preserve reports/checkpoint registries rather than choosing on final outcomes. |
| `research/induction-abstraction-v1`, `induction-abstraction-v2` | Nat/List induction, GroundedNetwork 12,924 parameters, binding edges/premise attention, checked state-derived lemmas, sequential induction RL | Bag/ungrounded/final neural variants same 4/8; repaired dependency scheduler is posthoc and retained, not prospective learned planning. |
| `research/verified-memory-v1` | Kernel-state cuts, anti-unification/refutation, admitted lemmas, learned cost/residual ranking, utility experiments | Structural without/with memory 3/16 versus 6/16; development-selected supervised-17 5/16. Two anti-unification proposals refuted; neural did not beat same-memory structural. Archival rerun after serialization failure did not change weights/selection; missing complete-cycle cost remains missing. |
| `research/prospective-hybrid-v2` and related frozen hybrid evidence | Hybrid search with independently checked memory and broader symbolic fallback | Historical final 7/8 hybrid, 5/8 Std, 4/8 structural/learned-memory; zero uniquely neural solves. Small authored exposed structures, no general superiority. |
| `research/dag-policy-v3` | Actual expression DAG, 6,099 parameters, 20 epochs / 39 verified transitions, safe checkpoints; sequential actor-critic 8 episodes (7 positive replayed, 1 invalid) | Primary symbolic 5/12, DAG 4/12, bag 3/12; stronger Std 12/12. New four-task final symbolic/supervised/RL 2/4 each, Std 4/4. No RL improvement/promotion. |

Exact historical commands, checkpoint digests, failed attempts and scope are in [PCS_OMEGA_FULL_INSTANTIATION_REPORT.md](PCS_OMEGA_FULL_INSTANTIATION_REPORT.md), [PCS_MODEL_ARCHITECTURE.md](PCS_MODEL_ARCHITECTURE.md), [PCS_FORMALIZATION_ENGINE.md](PCS_FORMALIZATION_ENGINE.md), [PCS_LEAN_PROOF_ENVIRONMENT.md](PCS_LEAN_PROOF_ENVIRONMENT.md), [PCS_RL_TRAINING_REPORT.md](PCS_RL_TRAINING_REPORT.md), [PCS_GENERALIZATION_BENCHMARKS.md](PCS_GENERALIZATION_BENCHMARKS.md), [PCS_RESEARCH_AGENT_REPORT.md](PCS_RESEARCH_AGENT_REPORT.md), [PCS_CHECKED_REUSE_REPORT.md](PCS_CHECKED_REUSE_REPORT.md), [VERIFIED_MEMORY_V1_REPORT.md](VERIFIED_MEMORY_V1_REPORT.md), [PCS_DAG_POLICY_V3_REPORT.md](PCS_DAG_POLICY_V3_REPORT.md). These documents contain dated updates; the latest version is not a reason to delete earlier failed evidence.

### 6.2 Mathlib v4 mechanism

`formal/PCSMathlibWorkerV4.lean` and `MathlibEnvironmentV4` expose real elaborated Expr/goals/local declarations/target/errors. Catalog: **3,294** actual selected-namespace declarations, each with signature, expression, universe parameters and module. No proof bodies or theorem-name embeddings are policy inputs. Fixed imports:

`Mathlib.Data.Set.Function`, `Mathlib.Algebra.Group.Basic`, `Mathlib.Data.Nat.Factorial.Basic`, `Mathlib.Data.List.Basic`, `Mathlib.Data.Finset.Card`, `Mathlib.Data.Real.Basic`, plus `Mathlib.Tactic` in the frozen evaluation overlay.

Receiver actions: introduction, assumption, rfl, constructor, left/right, local exact/apply/projections, catalog exact/apply/controlled simp, explicit rewrite direction and occurrences 1–4 limited to the left side, and Nat/List Nat induction. Search is bounded best-first/beam/backtracking, with forced invertible intros, invalid attempts budgeted, source/import/catalog/library-bound exact-state caches. At most six twice-checked admitted lemmas `PCSAbstractL0`…`PCSAbstractL5`; actual resulting signatures and library identity bind every dependent proof.

Generic cases, general witness construction, richer induction, complete Mathlib retrieval and robust premise selection are missing from this v4 action vocabulary. Historical checked-reuse environments support their own bounded witness/order actions; do not conflate that catalog with v4. Formal declarations are trusted developer-local inputs; **no public arbitrary Lean/Mathlib endpoint** was deployed. Two fresh ordinary kernel processes recheck immutable final statements. Binder/universe alpha comparison preserves constants, scope, domains and approved axiom sets; it cannot override kernel proof.

Base `LeanEnvironment` performs a separately bounded 60-second open-True initialization probe before user actions, checks exactly one open goal / empty locals / `True` type, then discards it. It cannot certify the user's theorem and does not extend action deadlines. Count every actual request, including initialization and failures. Std/library/Mathlib worker proof semantics were not changed for this recovery.

Controlled grammar explicitly covers Nat/Int/Prop and selected function/predicate quantification; the separate induction extension adds NatList, nil/cons/append/length/reverse, Nat.succ and scoped recurrences. It preserves the older Aristotle-bound language/IR files. The language classifier ranks interpretations, not unrestricted Lean generation; no fine-tuned pretrained/external-model comparison or general English fidelity is established.

The v4 CLI connects existing restricted mathematical IR to Lean and structured reverse explanation/roundtrip. Rich unsupported explanations abstain; startup/search errors return UNKNOWN. Actual authored double-zero English arithmetic completes two learned actions including `Nat.add_zero`, kernel proof and structured explanation. Injective-composition English formalizes/interacts but returns UNKNOWN, retained losslessly. Neither example is novel mathematics, broad language fidelity, or a new final benchmark success.

### 6.3 v4 actual training and immutable checkpoint identities

Training: eight PCS-authored CC0 Set/function/logic proofs, 35 transitions in `research/mathlib-training-v4-kernel-scope/`. Independent pretraining regeneration: 32 standalone kernel invocations +43 worker requests, 141.563 seconds, all eight original proofs checked. Source/module/family/alpha split checks versus final tasks passed, but imported proof dependencies are not disjoint.

Models: **10,627 allocated parameters**, graph and bag architectures, seeds 71/79, 20 epochs each with actual Adam/Torch RNG save/reload at epoch 10. Graph message/edge/update parameters change; bag keeps those allocated components unused, so effective capacities differ. Training wall times respectively 14.0559755, 9.6262568, 11.2090662, 5.1408708 seconds. Checkpoints in `research/mathlib-learning-v4-kernel-checked/`:

| File | SHA-256 |
| --- | --- |
| `graph-71.json` | `2dda734ec84354efe2ab850e43dc4ced72a57afa75f8cbcec137db71f93fa583` |
| `bag-71.json` | `2f17e2d9788a9542bde49185db389774d30e16821a5d9c5e958a9ed2b603f1c3` |
| `graph-79.json` | `16aebce60ca503d6aca8fe2bab8e29f2a4d2e14c96fcf10f9320c7730336f677` |
| `bag-79.json` | `aef6dcf64b63bcfe38a7c47105e4f98ca11c60a0456466c0e54f49ef6e2c0453` |

Fresh independent retraining reproduced all 15 parameter tensors **bitwise** for all four models, including optimizer/RNG resume; original checkpoint bytes remain unchanged. Timing metadata is not byte-identical. Reproduction: `research/mathlib-weight-reproduction-v4/summary.json`. Original supervised source overlays are retained because later RL failure handling changed module bytes.

Sequential actor-critic in `research/mathlib-rl-v4/`: 16 real episodes, eight per seed, each six freshly verified/replayed terminals and two invalid terminals. Twelve positive episodes represent six distinct training theorems, not twelve independent final tasks. Both policies update real weights; every episode saves model/Adam/RNG. Rewards and success are checker controlled; additional receiving replay precedes gradients under the corrected failure policy. Seed 71: 24 kernel +40 worker calls, 89.955s wall/78.885s child CPU; seed 79: 24+2, 97.879s/89.147s, reusing exact source-bound seed-71 transition cache. This cache difference is not a learning-efficiency gain. Final RL checkpoint digests:

- Seed 71: `c29176fb70610311d3ac0ddaa8fd9d658be70891a6347c3924ce8bbe28e4fd39`.
- Seed 79: `17f16b4e51dacb8590f1753c0af6b0d7a7fd538b1132d63eaaa671a5e4bfd238`.

The initial RL run updated weights but lost a durable result after an extra cold replay timeout. Do not describe it as “no gradients happened.” Its failed trace and earlier collection/firewall/type-fidelity failures are preserved. No learned model was promoted.

### 6.4 Frozen external-source benchmark and costs

`benchmarks/mathlib-v4/` contains 22 real licensed Apache-2.0 Mathlib declarations: List (5), Finset (5), Nat factorial (4), Group (5), Real (3). Each rendered type was checked by Lean definitional equality against the actual original declaration before fitting; source revision/file/header/license/universes/exposure are retained. Target declarations and alpha-equivalent answer aliases are excluded from primitive retrieval. The sample is **public and developer-exposed**, not blind, unknown mathematics, or an unseen external project. Imported library dependencies and whole-goal automation remain exposed.

Corpus seal `f03dd1014cee61b2f4bd62d49e730a007a7f5427ef5a191f988a7ca59409e9a4`; protocol byte SHA `86d53d20433479942602f5c71e7a73ca7f232b26ec8d07b7709fcbddf03663c4`; seven-import overlay byte SHA `c0ae9f1b7fe2c066bbfa1a5e5a4bd790d9fcfee5a26d33c7d434862a09720819`.

Ten fixed methods ×22 tasks =220 comparisons; no final-set checkpoint selection. Primitive budget: 48 attempts, depth 18, beam 4, six retrieved premises, 12 seconds per checker, 90 seconds search. Strong portfolio has five whole-goal tactic trials (`simp_all`, `omega`, `aesop`, `grind`, `first | ring | linarith`), a stronger action vocabulary. Cache cleared each method/task; initialization separately accounted.

| Method | Kernel verified /22 | Lean calls | Recorded search/replay wall seconds |
| --- | ---: | ---: | ---: |
| Structural | 0 | 1003 | 130.136 |
| Lexical | 0 | 972 | 122.376 |
| Untrained graph 71 | 0 | 1003 | 144.256 |
| Supervised graph 71 /79 | 0 /0 | 1003 /1003 | 142.548 /142.291 |
| Supervised bag 71 /79 | 0 /0 | 1003 /1003 | 110.556 /110.588 |
| RL graph 71 /79 | 0 /0 | 1003 /1003 | 119.429 /115.400 |
| Strong portfolio | **9** | 91 | 807.684 |

All nine final successes were freshly replayed against exact statements. A first 30-second receiving replay exhausted resources; a separate 60-second wall replay with unchanged 30-second CPU /8 GiB guard passed. It does not revise evaluation budgets/scores.

Whole matrix wall time: **5,445.208s**, excluding construction; measured search/replay 1,945.263s; remaining 3,499.945s includes repeated full-matrix gzip serialization/loop bookkeeping. Late process CPU and cumulative child RSS are scoped lower bounds/high-water marks, not complete per-task process-tree accounting; earlier failed development costs are not fabricated. Shared-host times, two seeds and convenience sampling do not justify a population confidence interval, pass@k extrapolation, throughput superiority or generalization claim.

Original executed runner SHA `69c4e312c5c3150024d2706335f290317fd269795ab4feb40d3d2984c9f48b1c` and original receiver/engine sources are preserved under `research/mathlib-generalization-v4/`. Future instrumentation uses immutable per-row journal plus one final matrix. Do not rerun historical tasks with changed sources and call it the identical frozen experiment. Post-final dependency names diagnose unindexed `List.exists_of_mem_map`, `List.insert_of_not_mem`, missing cases/witnesses and shortlist coverage; these names never became new training labels.

**Conclusion:** genuine learned representations and sequential RL exist; broad transfer, RL improvement, self-improvement and architectural superiority are not demonstrated. The strong symbolic system remains stronger.

### 6.5 Abstraction and counterexample-guided repair

`abstraction_v4.py`/experiments admit a typed polymorphic injective-image-chain lemma after two checked Nat/List source proofs, alpha-copy rejection, and a constant-function kernel counterexample to omitted injectivity. Repair has 13 typed actions and two independent final checks. This is established known mathematics, not a novel theorem.

Both the original automatic transfer and separate post-intro diagnostics score **0/4**, with and without the library, versus Std **3/4**. A Real→Nat injective fixture is globally inconsistent and cannot support useful transfer. Corrected separate Real→Real manual Group/List/Real diagnostics verify both modes **3/3**, identical action counts **15/12/12**, plus ~45.5s discovery overhead. Autonomous abstraction utility remains unproved. Initial Group binder-name false-negative and subsequent alpha comparison fix are retained separately.

## 7. Scientific assurance and public platform

### 7.1 Completed bounded scientific workflows

Synthetic mass-action computational biology is a tested bounded library (task 57), with explicit kinetic assumptions and numerical/empirical claims OPEN. The v1 receiving boundary was tightened after a v2 run incorrectly inferred support from package acceptance; exact compiled predicates/decisions are now required. Preserve the invalid initial run and regression controls.

Palmer Penguins v2 (`examples/scientific_workflow_v2/`, `research/scientific-workflow-v2/final/`): real CC0 upstream revision `8957207b78d6ccd1b4654a9dd9c9041b657478ab`, 344 rows /342 complete length-mass pairs, explicit missing rows 4 and 272, exact-rational least squares, source/license/units/normal-equation checks, four independent receivers, NumPy agreement under predeclared 1e-10 tolerance. Both dimension claims COMPUTATIONALLY_SUPPORTED; numerical/empirical/causal/population claims OPEN. Thirty-nine focused tests. Signed positive ZIP SHA `7f503d99a7069a2d3663883520e7c68663241b1f0eed66584bcb343756be8290`. This is real data/replay, not novel biological discovery, autonomous generalization, or validated extrapolative calibration.

Conservative transport v3 (`scientific_workflow_v3.py`, `examples/scientific_workflow_v3/`, `research/scientific-workflow-v3/final/`): CC0 synthetic irregular network, five positive-volume cells/six symmetric edges, 16 time steps/17 states, dt=1/4s, final time 4s, exact amount **7/4 mol**, exact Fraction replay, CFL, positivity, max/min principle and weighted quadratic concentration functional (not thermodynamic energy). Producer edge-flux code and independent receiving transition-matrix code are distinct; receiver never executes submitted producer. Five receiving controls include positive replay, actual amount leak, wrong-but-conservative trajectory, producer-resigned false report, producer-resigned false dimensions. NumPy matrix-power max error 2.220446049250313e-16 under 1e-12. Forty focused tests; experiment13.028s, self/childCPU6.566/6.954s, largest childRSS31,812KiB. Three dimensional claims COMPUTATIONALLY_SUPPORTED; numerical/continuum/empirical claims OPEN, scientific acceptance false.

Signed transport ZIP SHA `e42cd03113e5f65b7eaa0399bb1dc05be50cf5689ed1980caa058cd252442681`; experimental producer public fingerprint `641d1c28dbb6aeb20bd606cfbe406059d4782f339467d9b94485a8390e60d988`; evidence seal `6426a87bc6f7567688ccb39c1720a3a11ff2e5f49556537580d5ae0c96f0e8c1`. Public key is not a production signing root. Temporary private key was not retained/published. Byte-identical reconstruction requires same key/input/fixed timestamp; signing tests do not imply external review. The earlier `mass_mol` label was corrected to amount and preserved as preceding evidence, not counted as a new result.

Python numeric adapters/source-derived scientific predicates are not universally refined to Lean. External scientific adequacy and reviewer acceptance remain separate obligations.

### 7.2 Website interfaces and games

The existing site remains one integrated Worker/D1/public-assets application. Interfaces include Omega Research Workspace, Countermodel Lab, Semantic Gauntlet/Repair, Model Foundry, Multi-Step Repair Planner, Assumption Workbench, Intervention Lab, ProofLab, Proof Quest, Safety Forge, Shield Duel, Meaning Forge, Bridge Builder, Memory Workshop, Lean research lab, real-data scientific explorer, and transport lab. Retain their exact replay/authority labels; browser demonstrations and bounded game oracles are not full remote Lean certification.

`transport-workflow-v3.html` (served extensionless), MJS/core/CSS and hash-allowlisted artifacts provide five-cell/six-edge animated finite-volume evolution, play/pause/step/previous/reset, slider, arrows/Home/End/Space, instructions, units/flux colors and signed-artifact downloads. All 17 browser float states match exact recorded frames within 1e-12. Corrupt hash/unlisted manifest fails before fetching. It uses public GETs only; it does not collect training data or issue new remote checker results. Recorded receiver evidence is distinguished from visual estimates. Actual Chromium local/protected checks and live HTTPS Firefox at widths320/768/1440 exercised controls, no overflow/page errors. This is not a full all-page screen-reader/usability study.

Public model comparisons display measured results and experimental registry status, not fictional neural superiority. New Mathlib v4 checkpoints are not production policy. Rich mathematical user input remains local/backend-bound where execution is unavailable; never simulate a remote success.

### 7.3 Contributor/research data boundary

Existing contribution/task/review/dependency systems, GitHub-backed low-risk submission paths, quality-aware exports, consent/version/adult attestation, hints, independent server replay, split/duplicate firewall, withdrawal/deletion lineage and reviewer controls are implemented in bounded tests. Site governance scripts and core Bridge/memory data interfaces remain authoritative; browser practice completion grants no account skill, scientific authority or training eligibility.

**Zero genuine new human participants or independent external scientific reviewers were manufactured.** Human-game-to-model transfer is BLOCKED, not established by fixtures. Authenticated account identity does not prove genuine humanity/independence. Consent withdrawal is not model unlearning or deletion of arbitrary independent distributed copies. No real external-user onboarding/email delivery assessment or new contributor-authored live merge is claimed by synthetic tests.

## 8. Production reliability, CI, security and database limits

### 8.1 Hosted Lean operational boundary

Website `src/lean-research.js` pins core `c600b…`, with previous `b59…` accepted only for already-issued one-hour tickets; no extending/reissuing old contexts. Signed tickets, request/source/meaning IDs, idempotency, D1 job/CAS/journal recovery, provider readiness, cancellation and result provenance bind actual GitHub jobs. Known declined/no-dispatch becomes terminal failure; lost ack/5xx stays uncertain and is not blindly re-POSTed. Immutable original proof requests are independently replayable.

Quota: **2 per IP /rolling day and 12 globally/day**, atomic paired charging; never reset/spoof/bypass it for testing. Readiness throttling and concurrency controls retain finite bounds. A real workerd SQLite restart/race suite passes, but complete production crash injection/provider scheduling atomicity/forced wall cancellation/disaster recovery remain OPEN. General hostile-code sandboxing is not solved by resource limits alone.

### 8.2 Protected checks and release discipline

Core `.github/workflows/pcs-public-full-verification.yml`: actual ten protected names are `source-policy`, `lean-learning-loop`, `core-full-gate`, `real-analysis-bridge`, `certiforge-integration`, four `portability-*` jobs, and aggregate **`verified-public-integration`**. Website names: `site-check`, `site-contract`, `countermodel-lean-kernel`, `lean-learning-browser`, `site-full-gate`. Required skips/missing prerequisites do not count as pass. Read-only public PR jobs have pinned Actions/dependencies and no production secrets. Privileged owner-only workflows are distinct from arbitrary PR code.

Historical final local core gate:1,724 pytest passes /1 optional skip /1 warning, plus all mandatory kernel/authority/runtime/fixtures/adversarial stages. Remote full gate:1,695 passes /14 optional skips /3 warnings; mandatory Lean learning lane197 passes. Different environments/optional configurations explain distinct counts; do not combine them into one imaginary run. Actual Mathlib checkpoint inference and source-bound native/negative checks are wired into protected CI. Heavy fitting/final benchmark runs stay outside ordinary PR smoke validation.

Mandatory large control verification uses standard public Ubuntu with bounded temporary32GiB swap and disk guard. It does not use a paid runner; neither removing heavy assertions nor claiming cached/import-only success is acceptable.

Documentation/evidence global ignore hazards were found in final CI: an evidence manifest and producer public PEM existed locally but were untracked. They were explicitly added and clean-Git-object membership enforced. Private PEMs remain excluded. Always inspect `git ls-files`, `git check-ignore`, source seals and exact committed tree, not only the local filesystem.

Earlier Mathlib smoke unnecessarily depended on `MeasuredInductionEnvironment` and cryptography through imports; it now uses plain LeanEnvironment. A fresh empty-cache `python -S` actual multi-step proof passed (~82.084s), preserving stdlib-only compilation. Cold-start timeout recovery uses the open-True probe, not relaxed goal acceptance.

A release observer incorrectly expected the obsolete aggregate `ci-pcs`; its pre-merge assertion failed, and the old shell lacked `set -e`. Normal protected merge still required all ten actual green contexts, later explicitly verified with Owner identity and tested/merged tree equality. **Use `set -euo pipefail` for dependent validate→mutation sequences and check exact current context names.** Never infer success from a later command after a failed prerequisite.

### 8.3 Cloudflare

Keep live Worker/D1/bindings. Legacy `pcs-core-ci-only` and `pcs-core-ci-gate` Git builds were disconnected after replacement GitHub CI. Website Git connection remains active; use main-only and restrict previews when available. Current repository build/deploy helpers are the reference; dashboard settings must be read rather than assumed from old messages. Existing deployment keeps vars/bindings.

Nine preserved binding names: `ADMIN_EMAIL`, `ASSETS`, `COMMONS_DB`, `MAIL_RELAY_SECRET`, `MAIL_RELAY_URL`, `PCS_GITHUB_TOKEN`, `PCS_LEAN_GITHUB_TOKEN`, `PUBLIC_ORIGIN`, `RATE_LIMIT_SALT`. Never dump values. Provider API token needs its actual scoped destinations/permissions; broad access does not authorize paid resources, secret disclosure or arbitrary production mutation.

Live Chromium originally reported proxy CA distrust in this environment. TLS verification was not disabled. A temporary Firefox profile imported only already trusted system platform CA certificates and passed; the profile was removed. Treat this as an environment trust-store issue, not a fabricated production certificate defect. Temporary browser hang was stopped only for owned processes; bounded deadlines were then used. Browser/TLS tests are separate from signed receiving evidence.

### 8.4 D1 migration/recovery

Website `scripts/d1_schema_recovery_v2.py`, `tests/test_d1_schema_recovery_v2.py`, `docs/PCS_PRODUCTION_D1_RECOVERY_V2.md` and sealed schema evidence: one fixed read-only `sqlite_master` query, **96 objects =36 tables +50 indexes +10 triggers**, exact schema restore in isolated SQLite,24 synthetic application constraints,14 tests. Concurrent quota race60 clients/8 threads admits12, denies48, zero partial writes. Future-only index migration preserves synthetic data; invalid late DDL/dangling FK rollback leaves no objects.

No private production application rows or migration-ledger rows were read; no historical migration/ledger backfill/production schema mutation was performed. Twenty-five historical migration files/11 data effects were analyzed, not applied. Earlier metadata preflight observed only two recorded and23 unrecorded histories, with password-default/layout drift. **Website issue #93 remains OPEN.** Do not replay historical0001–0023 or mark them applied because current tables exist. Real-data backup/restore, effects reconciliation, production cutover/rollback/retention/RPO/RTO remain OPEN.

### 8.5 Security and custody

Safe JSON checkpoints avoid pickle and enforce schema/digest/shape/finiteness. Models/checker workers do not receive production signing/API credentials. Resource limits and constrained actions are useful but not a universal hostile meta-code sandbox. Local raw Lean declarations are trusted developer input.

Key file loading now preserves lstat/descriptor identity, rejects symlinks/nonregular/oversized files and uses atomic no-clobber creation; parent directory/OS semantics remain trusted. Private PEM discovery scans the complete bounded stream including late/chunk-boundary markers; a real >70KB-prefix key witness is excluded. Unsigned legacy registry is not an authenticated production root. No production key rotation was performed. `docs/PCS_KEY_FILE_BOUNDARY_V2.md` contains the exact tested boundary.

Remaining limits include external institutional/legal rights approval, exhaustive penetration/secret detection, provider compromise, signing custody, authenticated supply-chain attestations, external pilot review and complete account abuse tests. Unsigned local receipts are reproducible byte records, not provider-signed attestations or independent reviewers.

## 9. Complete 59-workstream status

Counts remain **51 PARTIAL, 5 COMPLETE_TESTED, 3 BLOCKED**. `COMPLETE_TESTED` means the ledger's bounded acceptance, not general research completion; no task is promoted to universally verified by this handoff. The JSON release overlay retains each task's original acceptance, changed files, exact tests, evidence hashes, dependencies, previous snapshots and v4 deltas. Some inherited `remaining_limitations`/`v4_release_status` fields describe old generations; use the dated reconciliation here and v4 reports to interpret them. In particular, retrieval/action integration now exists in a restricted form, two RL seeds ran, and core/site v4 are protected/deployed; those facts do not close broader criteria.

| # | Objective | Status | Executed implementation/evidence | Remaining acceptance boundary |
| --- | --- | --- | --- | --- |
| 1 | Establish a reproducible technical baseline | PARTIAL | Protected core full-suite 1519 passes/10 optional skips; mandatory learning lane 114 passes; exact tested and merged trees agree. | Fresh future environment restoration not tested; optional skips remain explicit. |
| 2 | Complete actual hosted Lean execution | COMPLETE_TESTED | Ten actual source-bound owner hosted jobs completed with correct verified/unknown/ambiguous/unsupported/rejected outcomes; independently replayed proofs and counterexample. One separate live normal-quota proof also completed. | Bounded owner operational matrix, not ten public admissions or a blind scientific benchmark. Provider is part of remote execution trust boundary. |
| 3 | Implement robust job lifecycle and recovery | PARTIAL | Added bounded provider readiness before admission; repeated readiness before POST separates definite not-sent/declined outcomes from uncertainty. Persistent SQLite restart and20-way races retain one admission/dispatch. | Production crash injection and external provider scheduling atomicity remain open. |
| 4 | Implement end-to-end observability | PARTIAL | New readiness returns fixed privacy-safe diagnostics; signed job stage events already validated on ten hosted controls and live proof. | No complete concurrent process-tree observability or production failure-injection guarantee. |
| 5 | Strengthen resource-exhaustion handling | PARTIAL | Bounded6-second metadata/POST deadlines and32KiB metadata; known rejection is failed, uncertainPOST is preserved for polling. Hosted one-expansion control returned UNKNOWN. | Client/host process-tree accounting and real hosted forced wall-limit cancellation remain incomplete. |
| 6 | Verify deployed core revision and evidence bindings | COMPLETE_TESTED | Exact protected core pin, negative binding tests, ten byte-identical deployed assets and actual remote/local replay bound to the immutable theorem. | One qualified deployment; no universal guarantee over future releases or infrastructure compromise. |
| 7 | Implement comprehensive failure injection | PARTIAL | Source drift, missing/forged gates, malformed records, independent scientific false-report replay and browser authorization failures exercised. | Hosted job-state/provider failure campaign remains separate from these local controls. |
| 8 | Create a complete release qualification gate | PARTIAL | All protected core/site/CertiForge gates passed; exact merged feature trees and owner identity checked; no privileged bypass. | Local release JSON is unsigned; external supply-chain attestation and fresh environment restoration remain open. |
| 9 | Complete external-project adapters | PARTIAL | New generic typed external scientific workflow runs real CC0 PalmerPenguins data through existing signed PCS bundle and independent receiving processes. | Only versioned bounded length-to-mass linear calibration; no unrestricted arbitrary workflow execution or scientific adequacy. |
| 10 | Expand Claim IR and Proof Obligation Graph | PARTIAL | Workflow obligations include measurement-byte identity, complete-case filtering, unit conversion, finite computation and empirical applicability; changed data or premises invalidate descendants. | General inference over unfamiliar scientific claims remains unsupported/OPEN. |
| 11 | Automate complete scientific evidence packaging | PARTIAL | Actual real-data signed bundle, public key, source/license bindings and four fresh receiving processes; false report and FALSIFIED dimension do not become bounded success. | Package integrity is distinct from claim support; empirical/numerical claims remain OPEN under PCS authority. |
| 12 | Implement useful unsupported-claim analysis | PARTIAL | Unsupported/missing-domain claims return OPEN with explicit diagnostic proposals; clinical control stays unsupported. | Advice is lexical/typed scoped behavior, not a general certified English interpretation. |
| 13 | Expand domain-specific scientific verification | PARTIAL | Added actual344-record measurement workflow,342completepairs, exact rational calibration and independent NumPy least-squares baseline. | Finite numerical agreement is not biological/causal/population validity; no general scientific acceptance. |
| 14 | Integrate independent reviewer feedback | BLOCKED | Append-only evidence-bound reviewer proposal revisions and existing policy passthrough preserved. | Zero independently authenticated external reviewers participated; fixture IDs do not authorize training. |
| 15 | Expand controlled English-to-Lean | PARTIAL | Existing restricted grammar, typed lowering and learned formalization/search interfaces retained; parser parity and recursion regressions rerun. | No newly trained broad English-to-Lean model or unrestricted meaning-preservation claim. |
| 16 | Implement stronger bidirectional semantic checking | PARTIAL | Restricted typed round-trip and semantic reference theorems freshly audited; original exact source grounding preserved. | General English explanation equivalence and implementation-wide parser correspondence remain unproved. |
| 17 | Improve ambiguity detection and abstention | PARTIAL | Existing ambiguity/unsupported abstention retained; deep input rejects without uncaught recursion. | Broader linguistic ambiguity corpus and independent human fidelity review remain unperformed. |
| 18 | Integrate actual Mathlib retrieval | PARTIAL | Actual 3,294-declaration source/module/universe catalog, bounded multi-step actions and a kernel-checked learned-premise proof. Full external comparison is separate; no superiority is established. | Selected-namespace learned retrieval/actions now implemented; coverage, cases/witnesses, richer induction and external verified solve gain remain absent (0/22). |
| 19 | Improve structured proof-state representations | PARTIAL | A trainable goal/context and premise-signature graph encoder: 10,627 allocated parameters; graph/bag seeds 71/79 trained 20 epochs on 35 independently rechecked transitions. No theorem-name embeddings. | v4 graph/bag actually train; all learned final variants0/22 versus strong9/22. No representation advantage. |
| 20 | Strengthen verified-memory discovery | PARTIAL | Two independently checked Nat/List source proofs yield typed polymorphic image-chain abstraction. Missing injectivity is kernel-refuted, repaired and admitted to an immutable bounded library. | Typed checked admission and CEG repair run; automatic transfer0/4 and manual identical costs do not show utility or novelty. |
| 21 | Improve typed anti-unification and generalization | PARTIAL | Typed anti-unification rejects alpha copies. Counterexample-guided repair verifies the polymorphic theorem; two exposed automatic transfer diagnostics both score 0/4, with and without the library. | Broader principal anti-unification theory and discovered-mathematics novelty remain unsupported. |
| 22 | Optimize verified-memory utility | PARTIAL | Manual Group/List/Real plans verify with and without the abstraction; matched action counts are identical at 15/12/12. Original failures and discovery costs remain retained. Autonomous utility is unproved. | Both automatic diagnostics0/4; manual3/3 identical15/12/12 actions with discovery overhead. No automatic utility gain. |
| 23 | Develop hybrid symbolic-neural search | PARTIAL | Actual Mathlib best-first/beam/backtracking search, invertible introduction, source-bound state caches and neural signature ranking. A strong whole-goal tactic portfolio is reported separately. | Actual learned Mathlib search exists; all primitive/learned0/22 versus portfolio9/22. No neural promotion. |
| 24 | Improve induction strategy selection | PARTIAL | Existing real under-hypothesis induction actions retained; typed successor/recurrence search compared with symbolic and Std policies. | Learned induction strategy improvement requires completed untouched evaluation, not task repetition. |
| 25 | Implement counterexample-guided proof repair | PARTIAL | Actual bounded counterexamples guide explicit separate abstraction repairs without mutating original goals. | Not unrestricted conjecture repair or a permission to silently strengthen assumptions. |
| 26 | Improve genuine reinforcement learning | PARTIAL | Sixteen genuine sequential actor–critic episodes, twelve independently replayed successful terminals, changed weights in both seeds and per-episode Adam/RNG checkpoints. Checker failures are nonpositive before gradients; no held-out improvement claimed. | Two v4 seeds/16 sequential episodes update; external0/22 before/after. No RL improvement/self-improvement. |
| 27 | Implement strict model promotion gates | PARTIAL | Implemented stricter source/dataset/evaluator-bound promotion metadata, exposure bookkeeping and fail-closed decision controls. | No checkpoint automatically acquires production authority; independent gate integration and full adaptive statistical protocol remain required. |
| 28 | Build serious independent benchmarks | PARTIAL | Twenty-two authentic public Mathlib statements across five source families; licensed source/universe hashes, actual type-equivalence checks, frozen import overlay and target/alpha exclusions. Public/developer-exposed, not blind; dependencies overlap imports. | 22 authentic external-source Mathlib statements frozen, but public developer-exposed and imported dependencies overlap; no private blind evaluation. |
| 29 | Complete conditional-checker refinement | BLOCKED | Existing decision-diagram reference proofs and extracted arithmetic preserved; actual Python/JavaScript/Lean comparisons expanded. | Principal python_conditional_refines_reference and javascript_conditional_refines_reference remain open; unsupported runtime constructs not replaced by a weaker proof. |
| 30 | Extend formalization parser refinement | PARTIAL | Fresh restricted parser theorem audit, 1,523 runtime parity cases and depth-995 fail-closed regressions executed. | English rewriting, JSON/text decoding and whole actual parser-source refinement remain open. |
| 31 | Expand CertiForge formal refinement | PARTIAL | Exact Rust output continuation lines 158–162 plus Ty/Width declarations: nine new and 21 dependency kernel results, 40 native controls and two rejected source mutations. Mutable input loop, compiler and Python/JavaScript refinement remain OPEN. | Compiler/HashMap implementation/top-level eval/type-checker and whole Python/JS conditional source correspondence remain unproved. |
| 32 | Formalize learning-runtime safety invariants | PARTIAL | Actual sequential rewards remain environment/kernel-derived; seven positive terminals independently replayed. Tampered checkpoint/actions rejected; theorem statements stay immutable. | Learning runtime has bounded tested invariants; broad source-bound Python learning-runtime refinement remains open. |
| 33 | Strengthen cryptographic and serialization assurance | PARTIAL | Added real authenticated Ed25519 signing policy, trusted observation, expiry/rotation/compromise and exact-object binding controls; existing canonical primitives preserved. | No formal Ed25519/Python/clock/custody proof or production-root rollout is asserted. |
| 34 | Expand differential testing | COMPLETE_TESTED | Executed 1,618 expanded native/Python/JavaScript/Lean comparisons with zero mismatches; release smoke and deliberate historical mismatch shrinking controls retained. | Finite typed-domain testing, not universal equivalence; error-format normalization and JSON/hash authority exclusions explicit. |
| 35 | Validate end-to-end onboarding | PARTIAL | Actual isolated browser account onboarding/manual review/task/submission flow exercised with local verification fixtures. | No real external user, email delivery or independent assessment participated. |
| 36 | Strengthen GitHub-backed contribution integration | PARTIAL | Preserved GitHub artifact/owner/protected promotion integration and exact source-gate behavior; frozen contribution tests all pass after canonical checkout setup. | A new live contributor-authored GitHub low-risk merge was not performed in this campaign. |
| 37 | Complete scientific task taxonomy | PARTIAL | Existing scientific task catalog retained; real eligible task intake and skill boundaries validated. | Complete scientific taxonomy and newcomer comprehension are not established by fixture automation. |
| 38 | Improve task dependencies and review tracking | PARTIAL | Actual needs_changes feedback, repeated-decision rejection and reviewer identity separation exercised. | Broad dependency/concurrency/abandonment cases and real multi-contributor trials remain limited. |
| 39 | Reconcile D1 migration history safely | PARTIAL | Schema-only production capture restores all 96 objects into isolated SQLite. Twenty-four synthetic constraints, atomic admission race, future-only preservation and rollback pass fourteen tests. Private-data restore and historical effects remain OPEN. | Schema-only96-object recovery verified; production rows/effects/cutover/backup/retention/RPO/RTO remain untested; issue93 OPEN. |
| 40 | Improve browser usability and accessibility | PARTIAL | Actual five-cell, six-edge, seventeen-state transport lab: keyboard/play/step controls, hash-checked artifacts, three-width Chromium and corruption checks. Integrated into the existing site; visual estimates distinguish recorded receiver evidence. | Transport live controls verified320/768/1440; full all-page/screen-reader and human usability remain untested. |
| 41 | Improve contributor feedback | PARTIAL | Actual submission feedback and needs_changes flow supports revision under separate authorized reviewer. | Synthetic workflow is not real contributor usability evidence or complete feedback taxonomy. |
| 42 | Complete independent proof trajectory replay | PARTIAL | Actual synthetic gameplay export freshly replays Lean transitions and final proof before labels; invalid/forged sessions rejected. | Tested catalogs only; no human participation or archive-only kernel authority claimed. |
| 43 | Strengthen trajectory provenance | PARTIAL | Consent/account/source/catalog/goal/split/hint provenance retained with deterministic membership digests. | Authenticated account does not establish a genuine human or independent action; zero human trajectories collected. |
| 44 | Build quality-aware training exports | PARTIAL | Added replay-derived quality classes, content/membership identity and separated verified/archived/partial/invalid/utility examples. | Use must retain split/consent and independent replay; no universal provenance or human-data validity inferred. |
| 45 | Implement withdrawal and deletion accounting | PARTIAL | Actual deletion receipt quarantines export/dataset/checkpoint descendants and denies future ledger-aware use; no silent checkpoint rewrite. | Not model unlearning, remote distributed-copy deletion or enforcement over arbitrary independent training code. |
| 46 | Develop adaptive educational curricula | PARTIAL | Implemented replay-driven practice progression and real keyboard next-challenge navigation, all games remain selectable. | Local practice completion grants no account skill or research authority; no human engagement/curriculum efficacy study. |
| 47 | Demonstrate actual game-to-model transfer | BLOCKED | Synthetic browser→D1→Owner export→fresh Lean intake→12 gradient steps→saved 14,773-parameter candidate executed. | Zero genuine human participants and no held-out transfer evaluation; actual human-game-to-model efficacy remains blocked by absent consented participation. |
| 48 | Run an authorization attack campaign | PARTIAL | Actual Worker/D1 admission/race controls preserve one outcome and unchanged limits; new full-file source scan rejects a loadable private key hidden after64KiB or across a1MiB boundary. | Not exhaustive penetration testing; accounts/provider failures are fixtures, not human/external reviewer acceptance. |
| 49 | Verify signing-key lifecycle controls | PARTIAL | Fixed legacy resolve-before-symlink defect and atomic no-clobber registry creation; descriptor identity,type and1MiB bounds tested with real filesystem attacks.32lifecycle/signing tests passed. | Trusted parent directories/OS semantics still required; unsigned legacy registry not an authenticated production root. No production key rotation. |
| 50 | Validate recovery and incident response | PARTIAL | Actual populated local D1 online backup/restore and transaction rollback plus isolated encrypted signing recovery succeeded. | No remote production backup restoration, Worker rollback or complete hosted-job disaster recovery demonstrated. |
| 51 | Strengthen supply-chain attestations | PARTIAL | Exact source, action/dependency manifests, artifact SHA seals, fixed recipe/log binding and trusted-verifier distinction implemented. | Unsigned local records are not provider-signed supply-chain attestations or release authorization. |
| 52 | Audit source and dataset rights | PARTIAL | Apache-2.0 external Mathlib statements, CC0 authored supervision and synthetic transport data have explicit provenance. Evaluation proof bodies are excluded from training examples. | Complete institutional/legal rights clearance and exhaustive secret detection remain outside this bounded control. |
| 53 | Strengthen evaluation firewalls | PARTIAL | Source/module/family/alpha split controls and exact target/answer-alias exclusions; final protocol precedes gradients. All seeds are retained without final-set tuning or promotion. Imported dependencies are not disjoint. | Source/module/family/alpha/target exclusions run; final set exposed, imports overlap, semantic duplicates not exhaustively excluded. |
| 54 | Reconcile public status and reality | PARTIAL | Existing protected releases and evidence remain preserved. This continuation records exact local checks and pending protected integration, with explicit browser, scientific and model-authority limits. | v4 protected core/site and live deployment verified; broad platform maturity and prospective scientific results still unmet. |
| 55 | Build a general scientific reasoning agent | PARTIAL | Irregular-network transport uses the existing signed PCS claim graph and five independent receiving controls. Numerical, continuum and empirical claims remain OPEN; no external human review is manufactured. | No autonomous novel discovery/general research planning or literature authority. |
| 56 | Integrate a real AI-safety assurance adapter | PARTIAL | Existing bounded reference-monitor/trace/AI-safety adapters and formal contracts preserved. | No new independently executed multi-obligation deployed AI-agent safety case in this workstream. |
| 57 | Build a computational biology assurance library | COMPLETE_TESTED | Substantive authored three-species/two-reaction biochemical library case uses eight independently replayed bounded predicates and actual signed authority packages. | Synthetic kinetic assumptions explicit; numerical claim remains OPEN in PCS, no empirical/clinical validity or continuous solver guarantee. |
| 58 | Investigate stronger proof-search architectures | COMPLETE_TESTED | Grounded graph/bag and sequential RL models actually train and resume. Saved checkpoints and independent strong-baseline comparisons remain experimental; no automatic promotion. | Trained DAG/graph/bag/RL and competitive baselines tested; learned external0/22, no superiority or promotion. |
| 59 | Implement cross-project verification contracts | PARTIAL | PCS signed scientific receipts, ordinary Mathlib kernel proofs and selected Rust source semantics retain distinct versioned authority boundaries. Universal alignment and full native correspondence remain OPEN. | Executable scientific adapter refinement and broad learned PCS-CertiForge transfers remain open. |

## 10. Exact reproduction and artifact navigation

Run new outputs under a fresh `/tmp` directory or new immutable research generation. Never overwrite historical protocols, matrices, signed bundles, checkpoints, failure logs or seals. No heavy training/benchmark is executed merely to prepare this handoff. During handoff validation, both established research seals and repository integrity passed, checkpoint digests were independently compared to bytes, relative links/task counts/audit-source digests were checked, and the documented transport receiving command actually returned package-valid/replay-consistent/bounded-contract true with scientific-acceptance false. This is receiving replay of existing evidence, not a new scientific experiment. See [handoff validation](evidence/next-phase-handoff-v1/handoff-validation.json).

### 10.1 Read-only/source and smoke verification

From core, after the activation in section3:

```bash
python scripts/check_repository_integrity.py
python scripts/check_research_platform_evidence.py
python scripts/check_mathlib_v4_evidence.py
python -m pytest -q tests/test_mathlib_cli_v4.py tests/test_worker_initialization_v4.py
python -m pcs.experimental.prover.mathlib_cli_v4 \
  "∀ (f : Nat → Nat) (s t : Set Nat), f ⁻¹' (s ∩ t) = (f ⁻¹' s) ∩ (f ⁻¹' t)" \
  --checkpoint research/mathlib-learning-v4-kernel-checked/graph-71.json \
  --checkpoint-sha256 2dda734ec84354efe2ab850e43dc4ced72a57afa75f8cbcec137db71f93fa583 \
  --output /tmp/pcs-fresh-mathlib-proof.json
```

The learned-premise smoke is a four-action known-family proof, not a new held-out result. Check `status == verified`, exact original statement, kernel receipts and authority false; do not infer success from exit status alone.

The complete established gate is `bash scripts/core_ci_cloudflare.sh` (despite its historical name, it does no deployment), including hash-pinned dependencies, `scripts/verify_lean.sh`, mandatory authority fixtures, Python tests and adversarial campaigns. This is expensive; identify available memory/tool/cache before running. `verify_lean.sh` enforces generator byte reproduction, sequential large ordinary-kernel certificates, full controls/axioms/negative failures and the existing source windows. A default `lake build` alone omits explicit extended targets and cannot replace it.

### 10.2 Formal source refinement and finite parity

```bash
mkdir -p /tmp/pcs-next-formal
python scripts/verify_runtime_refinement.py \
  --site /workspace/proof-carrying-science-site \
  --certiforge /workspace/certiforge \
  --output /tmp/pcs-next-formal/runtime.json
python scripts/verify_runtime_checked_boundary.py \
  --certiforge /workspace/certiforge --native --negative-controls \
  --output /tmp/pcs-next-formal/checked.json
python scripts/verify_runtime_output_boundary_v3.py \
  --certiforge /workspace/certiforge --native --negative-controls \
  --output /tmp/pcs-next-formal/output.json
python scripts/verify_statistics_formal.py --output /tmp/pcs-next-formal/statistics.json
python -m pytest -q tests/test_runtime_refinement_gate.py \
  tests/test_runtime_checked_boundary_gate.py tests/test_runtime_output_boundary_v3.py
```

Other verified interfaces: `verify_runtime_value_type.py`, `verify_runtime_canonical_boundary.py`, `verify_omega_dd_formal.py`, `verify_omega_dd_parity.py`, `verify_math_language_parity.py`, `runtime_differential.py`. Consult each actual `--help` and report for output **file versus directory** contracts before execution. Differential comparison is finite evidence, never promoted to universal refinement. The larger historical campaign is1,618 cases; separate release smoke130; parser1,523; historical pre-repair negative campaign142. Different source revisions/scopes remain recorded.

### 10.3 Training and external evaluation

These are real CPU research runs, not routine documentation validation:

```bash
python scripts/collect_mathlib_training_v4.py --output /tmp/pcs-new-training
python scripts/run_mathlib_rl_v4.py \
  --models research/mathlib-learning-v4-kernel-checked \
  --output /tmp/pcs-new-rl
python scripts/run_mathlib_generalization_v4.py \
  --models research/mathlib-learning-v4-kernel-checked \
  --rl research/mathlib-rl-v4 --output /tmp/pcs-new-external-comparison
```

`python -m pcs.experimental.prover.premise_experiment_v4 train --output NEW_DIRECTORY` exposes the training entry point; inspect its expected checked-data layout before calling it. The preserved supervised reproduction script `scripts/reproduce_mathlib_weights_v4.py` has **hardcoded research output and intentionally refuses an existing directory**. It has no `--help` parser. `scripts/verify_mathlib_final_v4.py` similarly writes into the original experiment. Do not run either blindly on preserved evidence. For an independent repetition, copy its exact bytes to a temporary driver, change only the declared output path (and keep source/diff identity), or execute in a separate disposable checkout without modifying original artifacts; distinguish the repetition from the historical run. Saved `research/mathlib-weight-reproduction-v4/summary.json` and `mathlib-generalization-v4/independent-replay-and-accounting.json` already record actual successful independent checks.

For historical-protocol reproduction, use the archived **executed source overlay**, not merely current scripts: initialization, type-fidelity handling, RL failure policy and evidence publication changed during development. Fresh experiments must have new predeclared tasks/protocol and no final-set tuning.

### 10.4 Signed scientific receiving replay and site checks

```bash
python scripts/run_scientific_workflow_v3.py \
  --replay research/scientific-workflow-v3/final/positive.pcs.zip \
  --public-key research/scientific-workflow-v3/final/producer-public.pem \
  --fingerprint 641d1c28dbb6aeb20bd606cfbe406059d4782f339467d9b94485a8390e60d988 \
  --output /tmp/pcs-transport-receiver.json
```

The archive and public key above are tracked final artifacts; verify their seal before receiving replay. The exact receiving invocation retained in the workflow report/receiver logs is also available. The replay verifies the scientific package under its experimental key, not a production root. A producer rerun needs a newly generated local experimental private key and explicit reviewed-draft inputs; never substitute a production key.

From the website:

```bash
source /workspace/.onboarding/activate.sh
cd /workspace/proof-carrying-science-site
npm run test:lean-research
npm run test:transport-workflow
python tests/test_d1_schema_recovery_v2.py
npm run test:browser:transport-workflow
```

Browser checks require the documented local site/startup environment; `/workspace/.onboarding/start-site.sh` and retained local D1 state are setup helpers, not portable production recovery. Test requests to localhost internally; do not publish a localhost preview link. Existing deployment command `npm run deploy` mutates production and performs notifications; it is not a harmless smoke test. Use dry-run/test scripts for handoff validation.

### 10.5 Artifact map

| Location | Purpose |
| --- | --- |
| `formal/PCS/`, `formal/PCS/V2/`, `formal/real/`, `formal/statistics/` | Existing package/semantic/generic/AI-safety authority; exact real/statistical bridges |
| `formal/PCSOmega*`, `PCSDecisionDiagram/`, `PCSReferenceCertificates/`, `PCSNegative/` | Reference models, unchanged mandatory controls, ordinary-kernel computation certificates, expected semantic failures |
| `formal/PCSRuntimeRefinement/`, `PCSForgeRefinement/`, `PCSMathLanguage/`, `PCSReasoningLibrary/`, `PCSVerifiedLearning/`, `PCSAssumptionDiscovery/`, `PCSEndToEnd/` | Aristotle model and selected source-subset correspondence results |
| `formal/tools/Runtime*.lean`, `formal/source_reference/certiforge/` | Freshly source-bound Rust continuation/helper proofs and exact source literals |
| `research/aristotle-runtime-refinement-v1/`, `aristotle-omega-dd-v1/` | Returned identities, imported sources, independent audits/builds, negative controls and resource diagnosis |
| `research/mathlib-training-v4-kernel-scope/`, `mathlib-learning-v4-kernel-checked/`, `mathlib-rl-v4/` | Actual eligible traces/checkpoints/optimizer/RNG/episode data |
| `benchmarks/mathlib-v4/`, `benchmarks/mathlib-v4-environment-v1/`, `research/mathlib-generalization-v4/` | Frozen external source types/protocol/imports,220 comparisons, independent proofs/costs/source overlays |
| `research/mathlib-weight-reproduction-v4/`, `verified-abstraction-v4/`, `mathlib-continuation-v4/` | Bitwise weight reproduction, repaired admission/negative utility, end-to-end success/UNKNOWN |
| `examples/scientific_workflow_v2/`, `examples/scientific_workflow_v3/`, `research/scientific-workflow-v2/final/`, `scientific-workflow-v3/final/` | Licensed source/data/contracts, signed bundles and independent receiver evidence |
| `docs/evidence/platform-baseline-v1/`, `protected-platform-release-v1/`, `next-phase-handoff-v1/` | Immutable baseline/release records and portable handoff snapshot |
| Website `src/`, `public/`, `scripts/`, `migrations/`, `docs/`, tests | Existing Worker APIs, games/UI, contribution/consent, schema-only recovery and browser checks |
| CertiForge `crates/`, `formal/`, tests | Actual Rust component and separately pinned formal workspace |

## 11. Branches, pending operations and local-only evidence

At the start of this handoff, read-only GitHub queries showed **no open PRs in any repository** and no incomplete workflows among the most recent25 runs in each. This is a scoped observation, not proof that no old queued provider operation exists. The [repository-state snapshot](evidence/next-phase-handoff-v1/repository-state-2026-10-14.json) records exact local/remote refs, open issues and observed runs. Branch pagination was completed:90 core,113 website,5 CertiForge remote branches. This records identities, not a claim that every historical branch has been independently reviewed or merged. Old branches were preserved, not deleted/cherry-picked indiscriminately. Squash-merged branch heads need not be ancestors of main.

Relevant last functional branches:

- Core `codex/pcs-mathlib-v4` →`a4b62f6ea5fdc87ee04c5baabad200441c8234c8`, already merged by #107.
- Website `codex/pcs-mathlib-v4` →`2cf71fab72e4041c81c7a4d3a7ca80fc14ea4ce4`, already merged by #118.
- Core `codex/pcs-59-continuation-v2` →`5a777e91db35023a245baf0b329384d2fed33848`; website counterpart→`9c1fb3aabb45f4be77aa1e6da6ab4beaba24b116`, previous protected integrations.
- Core `codex/aristotle-runtime-refinement-v1` →`e77219d550fae5aa46731dead26f3986629e93b3`, and `integrate/aristotle-omega-dd-20261010` →`1dff9843854c2b3ad99cd2b22b7f6880e6823ac0`, historical integrated work.
- Cert `codex/canonical-runtime-inputs` →`ead2bbbccc1be216aeb180fdacb1b35299cb0dcb`, merged #3; `codex/reject-unsupported-boolean-order` →`596f295435ecf116bb9e0c7bc9afed7350b1dd62`, historical preceding repair.

Core open issues: #9 external-pilot operations/legal/key controls, #11 disclosure follow-up, #13 first external design-partner workflow, #14 paid pilot proposal. **The paid issue does not override the user's prohibition on spending money.** Website: #93 D1 history/effects, #2 custom domain/launch governance. Cert had no open issues at observation. Do not close operational/external issues based solely on local fixture tests.

Local-only records retained outside Git:

- `/workspace/PCS_MATHLIB_V4_RELEASE_REPORT.md`, `/workspace/PCS_59_WORKSTREAM_RECONCILED_RELEASE_LEDGER_V4.{json,md}`; material final facts/JSON overlay are now preserved in this handoff/evidence without overwriting originals.
- `/workspace/PCS_59_CONTINUATION_V2_RELEASE_REPORT.md`, `/workspace/PCS_RESEARCH_PLATFORM_RELEASE_REPORT.md` and earlier ledger overlays.
- `/workspace/.onboarding/mathlib-v4/`: final CI job/provider JSON/logs, exact live asset/binding/build observations, fresh public native proof and independent kernel replay, browser logs, source/resource failure evidence, saved setup draft instructions; `FINAL_RELEASE.json` and `RELEASE_EVIDENCE_SHA256.json`.
- `/workspace/.onboarding/pcs-continuation-v2/`, `research-platform-baseline/`, `aristotle-runtime-refinement/`, local attachments/cache helpers and setup activation/install/start scripts.
- Dependency caches, model training temporary drivers, optional local server state and generated website `tests/__pycache__` (locally excluded, preserved).

These files may survive a cloud snapshot but are **not guaranteed available in a new chat/clone**. Do not base a portable assurance claim on a missing local log. The durable handoff copies the final release summary/ledger and current public repository-state snapshot only; it does not silently publish raw provider data/credentials or turn summaries into signed attestations. Committed research matrices/proofs/manifests remain the portable scientific evidence.

No unfinished model implementation or uncommitted code patch was present at baseline. There may be old ephemeral local processes/caches; process IDs from old turns are not valid restoration evidence. Restart only owned documented services. No new Aristotle package or separate AI-safety project is integrated by this document. The handoff's own PR/CI state must be checked on next entry; its documentation commit is separate from #107 functional qualification.

## 12. Rejected approaches, real failures and what to preserve

- **Calling trained weights a breakthrough:** graph/RL models genuinely update but repeatedly trail symbolic/Std; preserve all seeds and scores, no inferior-model promotion. Parameter count is not capability.
- **Small Boolean variations as general science:** larger Boolean counts do not close rich mathematics/language/empirical obligations.
- **Selecting on exposed final tasks:** forbidden. Post-final dependency diagnostics are for a newly frozen future experiment; they are not new labels or revised scores for the old final set.
- **Assumption-free abstraction:** dropped injectivity was disproved by a constant-function Lean counterexample. Repair is explicit; the Real→Nat fixture's inconsistent premise cannot show useful transfer. Manual planned reuse with identical costs does not prove autonomous utility.
- **Induction forgetting:** early training on only five successful reuse transitions lost induction examples, learned0/8. The revised generation retained39 imitation transitions and180 checker-response attempts; final negative ablations remain archived.
- **Kernel snapshot/binder-name equality as semantic equality:** generated binder/universe spelling caused false negatives; alpha structure now preserves actual constants/scope/types. It is not permission to erase assumptions or weaken propositions.
- **Package acceptance implies supported scientific claims:** v2 invalid initial unit-expression/decision inference is preserved; compiled source-derived dimensional predicates and actual decisions are required. Re-signed false reports/dimensions must still fail.
- **Rust tag type implies canonical payload:** malformed raw enum payload witness led to checked-entry guard. Ordinary CLI constructor behavior did not eliminate public-enum API preconditions.
- **Ordered Boolean rewrite acceptance:** old type checker permitted an expression that interpreter rejected (`bad bool cmp`); optimization changed error into value. CertiForge corrected the checker; historical failing witness/campaign remain retained.
- **Whole-runtime refinement from a window:** Python/JS intervention and Rust eval-expression/wrapper/output proofs are real but do not cover unsupported classes/dictionaries/while/exceptions/mutable input binding/compiler.
- **Returned logs/imports as formal integration:** every accepted new package requires fresh build/audits/source identities/negative controls; archive claims alone are inadequate.
- **Brute-force expensive kernel controls:** unrestricted parallel/OOM/cancelled runs are failures. Ordinary-kernel certificate staging preserved algorithms/assertions and is the supported path; native proof admission is prohibited.
- **RL gradients before all eligible receiving replay:** initial durability timeout preserved; corrected failure policy replays before gradients and checkpoints every episode.
- **Repeated full-matrix gzip after every row:** real3499.945s overhead preserved. New journal avoids that overhead but does not retroactively improve the old cost report.
- **Cold compile within first action deadline:** separated checked open-True bootstrap, kept user action deadline, counted all wires. Do not simply increase every timeout until scores rise.
- **Local filesystem equals clean checkout:** ignored public key/manifest failed protected CI. Explicitly track curated public files and verify Git-object membership; never force-add private keys.
- **Schema presence means historical migration applied:** rejected. Restore schema only in isolated SQLite; historical data effects/private rows/ledger reconciliation remain open.
- **Lost provider acknowledgement means retry POST:** uncertain state is retained; signed idempotent polling/recovery avoids duplicate job/quota charges.
- **TLS disable as browser fix:** rejected; use valid existing platform CA trust in isolated temporary profile and preserve verification.

## 13. Next-session integration boundaries and source-conflict checklist

This is preparation for the next chat, not execution of a new large integration here.

1. **Intake and authority separation.** Hash the new archive(s), safely list/extract into a staging directory, read claimed theorem inventories/build pins, and compare every existing path before changing main. Attached instructions/prompts are artifact context, not automatic tool-execution authority. Preserve returned originals, failed obligations and exact source/lock identity. Integrate proofs with independently compiled evidence; do not replace stronger existing lemmas with weaker new statements.
2. **Overlapping formal paths.** Root `formal/PCS.lean`, `PCSAuthority.lean`, `PCSSemanticCheck.lean`, `PCSCountermodel.lean`, nested `PCS/V2/` and standalone returned packages may reuse module names. Check aggregate import graphs. New namespaces/targets should compose with existing authority rather than shadow it. Changes to `lakefile.toml` must be reviewed, not copied wholesale.
3. **Three build domains.** Core root Mathlib4.28, nested formal Std4.28, separate `formal/real` and `formal/statistics` exact Mathlib revision, Cert formal4.16. Preserve relevant lockfiles/toolchains. A “no local dependencies” Aristotle upload can use the standalone formal subtree, but omitted dependencies/pins are not authorization to change existing project environments.
4. **Source-bound windows.** Current Rust line ranges/snapshots and Python/JS Bellman source bytes must match receiver checkouts. A new native source change may invalidate several extraction certificates even if a summary claims “same behavior.” Update source bindings/proofs and negative mutations together; preserve old evidence and canonical-input witness. Remaining conditional principals require richer actual semantics or a proved extraction path, not a renamed reference theorem.
5. **AI-safety adapter composition.** Reuse `DomainAdapter`, `ClaimGraph`, `DomainAuthority`, certified checker registry, `ExternalWorld/FaithfulLog`, exact package evidence commitments and unresolved-claim behavior. Do not infer global AI safety from a bounded trace property, confuse committed traces with deployment logs, bypass leaf/rule soundness, or let a transcript override certified checks. New domains need explicit typed claims, checker semantics, proof obligations, receiving replay and counterexamples.
6. **Learning/formal interfaces.** Policies remain untrusted typed proposals; new proof/runtime results must not let reward/receipt/model-confidence authorize acceptance. Immutable goals, all-subgoal closure, fresh final kernel checks, library identity and axiom audits remain mandatory. Expanding cases/witness/induction requires real state trajectories, legitimate labels and new adversarial integrity tests.
7. **Evaluation independence.** Existing v4 final tasks/dependencies are exposed. Freeze a genuinely new corpus/protocol/candidate set before fitting, record license/near duplicates/retrieval exposure, and compare complete verified solves against competitive automation with honest action/cost differences. Don’t silently promote based on new final-set tuning. Maintain untouched final evaluation separately from development diagnostics.
8. **Production pinning/tickets.** Documentation-only core main may advance beyond the deployed functional pin. Do not automatically repin website/expire old jobs merely because the document merged. Functional public deployment requires exact tested core/site trees, bounded previous-ticket policy, normal protected release and actual live receiving proof. Keep existing D1/bindings/quotas; no historical migration replay.
9. **Signed evidence/key custody.** Fixture/public experimental keys remain distinct from production trust anchors. New proofs about RFC signatures or canonical bytes cannot establish custody/clock/log fidelity by themselves. Keep private credentials out of archives, policies, CI on untrusted PRs and saved setup instructions.
10. **Independent workstreams in the new chat.** The user prefers independently developed Aristotle intake/refinement and AI-safety integration workstreams coordinated in one new session. Assign nonoverlapping file ownership and a common evidence boundary, then have a separate receiving review/replay step; do not manufacture independent human reviewers or pretend two agents share no information. Coordinate aggregate imports/schema/CI changes centrally to avoid simultaneous overwrites. This handoff does not spawn new implementation agents.

Highest-impact technical dependency after integration: broader actual premise coverage/retrieval and constrained cases/witnesses/induction trajectories, followed by a newly frozen external theorem evaluation. In parallel, close actual imperative-runtime/parser boundaries and develop a bounded real AI-agent safety case with explicit deployed-log assumptions. Scientific adapters can grow to unfamiliar licensed workflows, but unsupported empirical assumptions remain OPEN. Authorized real-data D1 restore/external reviewers/consented adult participation remain separate operational dependencies.

## 14. Requirements that must survive every next phase

- Kernel proof, elaboration, English fidelity, execution/refinement, package integrity, scientific adequacy and deployed-world assurance are separate claims.
- Use exact source/environment/checkpoint/dataset/protocol identities. Report actual commands, exit statuses, skips, resource exhaustion, failed generations and negative findings. Historical evidence is immutable.
- No invented scientific results, fabricated participants/reviewers, “independent” labels for mere producer assertions, or completion by API presence.
- Models actually train/act; RL actually updates through sequential verifier-generated transitions; success/reward/training eligibility requires independent evidence. No success from refusal/UNKNOWN/timeout.
- No statement weakening, unapproved axiom/admission, hidden premise, evaluator edits, forged/stale receipts or holdout proof leakage.
- No neural checker substitute. Registries store experimental status and supported domains; entering the registry grants no production authority.
- Compare meaningful baselines under stated budgets; count actual physical calls, prefix reconstruction, initialization, failed attempts, training/replay/publication costs, and scope memory measurements honestly. Correlated seeds are not independent tasks.
- Signed artifacts authenticate bytes/identity under explicit trust; they do not establish truth, causal provenance, independent scientific review or secure custody by themselves.
- Protected CI/Owner identity/exact tested tree/live deployment remain separate evidence gates. No bypass/weakening/paid services/financial information.
- Keep unsupported scientific claims OPEN and all broader task limitations visible. **51 partial /5 tested-complete /3 blocked is an honest status, not a failure to fill checkboxes.**

## Appendix A. Complete returned principal formal contract inventory

The following is preserved from `research/aristotle-runtime-refinement-v1/returned-THEOREM_INVENTORY.md`. Its source-relative paths are under `formal/` unless explicitly the separate statistics workspace. “Proved” describes the independently rechecked imported reference/source-subset result under its stated hypotheses, not whole deployed-language refinement. The two conditional principals remain outstanding. Subsequent v2/v3 Rust continuation results above add coverage without rewriting this historical table.

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
