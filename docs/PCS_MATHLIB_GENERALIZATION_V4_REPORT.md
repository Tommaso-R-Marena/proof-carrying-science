# PCS Mathlib generalization v4

This continuation extends the existing PCS proof environment with real elaborated Mathlib signatures, structured Lean proof states, receiver-controlled multi-step actions, trainable premise/goal DAG representations, sequential actor–critic updates, and independent final kernel replay. The external-source comparison is frozen before training. It measures the present bounded engine; it does not establish general mathematical intelligence.

## Executable interfaces

`pcs.experimental.prover.mathlib_environment_v4.MathlibEnvironmentV4` reads 3,294 actual theorem declarations from selected Mathlib namespaces. Each entry carries its actual Lean expression, signature, universe parameters and source module. The exact approved revision is `8f9d9cff6bd728b17a24e163c9402775d9e6a365`, Lean 4.28.0. The seven fixed imports and compiled import digests bind the catalog, worker requests, state cache and receipts. This is selected-namespace retrieval, not a complete Mathlib index.

The resident worker `formal/PCSMathlibWorkerV4.lean` exposes actual structured goals, local declarations, expressions and errors. The Python receiver permits bounded introductions, local/catalog apply or exact, constructors, controlled simplification, explicit rewrite direction/occurrence and Nat/List Nat induction. Policies submit typed actions, never arbitrary shell commands or Lean source. Formal statements are trusted developer-local inputs; this release creates no public arbitrary-Lean execution endpoint.

Search uses bounded best-first exploration with backtracking. Invalid attempts count against the budget. Universal/implication introduction is invertible and handled before policy ranking. The immutable original theorem and reconstructed final proof compile in two separate ordinary Lean processes. Only approved standard axioms are allowed. Alpha comparison ignores generated binder/universe presentation names while preserving constants, scope and types; it does not substitute a neural judgment for verification. Resource failures remain UNKNOWN.

An immutable local library admits at most six twice-checked lemmas; actual resulting signatures are extracted from Lean. Every dependent state and proof includes the exact admitted-library identity. Provenance or an optimizer's output cannot authorize a proof.

## Frozen external-source benchmark

`benchmarks/mathlib-v4/` seals 22 authentic public Mathlib statements from List, Finset, Nat factorial, Group and Real modules. Actual extracted expressions were compared by Lean definitional equality against their declarations before training. Source revision, file, license, universes, exposure, split and duplicate records are retained. No proof bodies enter the training data or policy observations.

The corpus seal is `f03dd1014cee61b2f4bd62d49e730a007a7f5427ef5a191f988a7ca59409e9a4`. The protocol file byte SHA-256 is `86d53d20433479942602f5c71e7a73ca7f232b26ec8d07b7709fcbddf03663c4`; the separate evaluation-import overlay SHA-256 is `c0ae9f1b7fe2c066bbfa1a5e5a4bd790d9fcfee5a26d33c7d434862a09720819`. The original six signature imports remain preserved; the separate search overlay adds Mathlib.Tactic.

All target declarations and alpha-equivalent answer aliases are excluded from primitive premise retrieval. Training consists of eight PCS-authored Set/function/logic tasks with 35 checked transitions. Module/family/alpha-statement overlap checks pass. Imported library proof dependencies and tactic automation are not disjoint. These are public source-selected, developer-exposed statements, not private blind tests or novel mathematical problems.

All ten frozen methods run each task once: structural and lexical retrieval, untrained graph seed 71, supervised graph/bag seeds 71/79, sequential RL graph seeds 71/79, and the strong `simp_all`/`omega`/`aesop`/`grind`/`ring`/`linarith` portfolio. Primitive methods share 48 attempts, depth 18, beam four, six retrieved premises, 12-second individual checker limit and 90-second search limit. The portfolio has five whole-goal tactic trials, each with the same per-checker limit; its stronger action vocabulary is explicitly different. Transition caches are cleared per method/task. Cold worker initialization is separately measured and amortized, not silently counted as free.

## Final results

| Method | Verified / 22 | Lean calls | Search and replay wall seconds |
| --- | ---: | ---: | ---: |
| symbolic_structural | 0 | 1003 | 130.136 |
| symbolic_lexical | 0 | 972 | 122.376 |
| untrained_graph_71 | 0 | 1003 | 144.256 |
| graph_71 | 0 | 1003 | 142.548 |
| graph_79 | 0 | 1003 | 142.291 |
| bag_71 | 0 | 1003 | 110.556 |
| bag_79 | 0 | 1003 | 110.588 |
| rl_71 | 0 | 1003 | 119.429 |
| rl_79 | 0 | 1003 | 115.400 |
| strong_portfolio | 9 | 91 | 807.684 |

All nine verified statements came from the strong portfolio. None of the other methods solved a final task; neither graph training nor sequential RL established a verified solve-rate gain. No checkpoint is selected or promoted.

The complete matrix took 5445.208 seconds excluding construction. Measured per-comparison search/replay segments total 1945.263 seconds; the remaining 3499.945 seconds include repeated evidence serialization/compression and loop bookkeeping. This overhead is not hidden as free computation. Model inference, child CPU, compiler requests, replay-prefix work and memory scope are retained in independent-replay-and-accounting.json. Late Python process CPU samples are lower bounds, not a complete reconstruction of earlier failed development runs.

This public convenience sample and two reused seeds do not justify a population confidence interval, broad transfer claim or pass@k extrapolation. Strong automation and primitive search have different action vocabularies. The shared CPU host and timing overhead prevent a clean throughput superiority conclusion.

The original frozen matrix, protocol, exclusions, construction and executed source overlay are in research/mathlib-generalization-v4/. Post-evaluation proof-dependency names diagnose missing retrieval coverage; they authorize neither retraining on these tasks nor a revised final score.

## Reproducible artifacts and commands

Activate the retained tools and pinned Lean environment before executing:

```bash
source /workspace/.onboarding/activate.sh
source scripts/activate_lean_428.sh
python -m pcs.experimental.prover.mathlib_cli_v4 "∀ (f : Nat → Nat) (s t : Set Nat), f ⁻¹' (s ∩ t) = (f ⁻¹' s) ∩ (f ⁻¹' t)" --checkpoint research/mathlib-learning-v4-kernel-checked/graph-71.json --checkpoint-sha256 2dda734ec84354efe2ab850e43dc4ced72a57afa75f8cbcec137db71f93fa583 --output /tmp/pcs-new-mathlib-proof.json
python scripts/run_mathlib_generalization_v4.py --models research/mathlib-learning-v4-kernel-checked --rl research/mathlib-rl-v4 --output /tmp/pcs-new-external-comparison
python scripts/check_mathlib_v4_evidence.py
```

Use new output paths. The executed benchmark script is retained separately in the experiment's source overlay; future evidence logging is changed to immutable per-row publication to avoid repeated full-matrix compression. That instrumentation change does not rerun or revise this experiment.

Training, actual optimizer resumption and sequential reward handling are described in PCS_LEARNING_AND_RL_V4_REPORT.md. Checked anti-unification, counterexample-guided repair and negative transfer results are described in PCS_VERIFIED_ABSTRACTION_V4_REPORT.md. Historical failed prototypes remain preserved.

## Independent replay and diagnosis

All nine final baseline proofs were independently rebuilt against the exact original statements in fresh kernel processes. A first 30-second post-evaluation replay attempt exhausted resources; that failure remains retained. The receiving replay then used a 60-second wall allowance with the same 30-second CPU and 8 GiB address-space guard. This additional verification does not change the frozen evaluation budgets or scores.

The post-final dependency-name diagnostic identifies omitted catalog facts such as `List.exists_of_mem_map` and `List.insert_of_not_mem`, along with existential/case structure absent from the current action language. Indexed facts can also miss the six-premise shortlist. The diagnostic is developer-exposed and excluded from training.

A fresh English injective-composition problem produced the restricted typed interpretation and interacted with real Lean states, but the learned policy returned UNKNOWN. Its full trajectory is retained; no end-to-end success is claimed for that demonstration.

## Operational continuation after the frozen comparison

Repeated cold-start timeouts in legacy checked-reuse regression tests motivated a separate bounded receiver initialization probe. It verifies one open True state, discards it, and retains the original per-action deadline. Forged or malformed bootstrap states fail before the user input is sent. Mathlib counts every wire request attempt, including bootstrap, and the CLI separates initialization from search metrics. The complete checked-reuse module passes 25 tests after the change. No Lean worker, kernel or mathematical acceptance condition changed. Original engine, receiver and executed runner sources are retained in the final experiment source overlay; these post-evaluation transport changes do not rerun the frozen tasks.

The CLI uses the existing mathematical IR parser/renderer for supported-fragment explanations and round-trip checks; richer declarations explicitly abstain from unsupported explanations. A fresh authored double-zero arithmetic sentence is kernel-verified using the saved graph checkpoint and an actual `Nat.add_zero` action. It is a functional known-identity check, not a new benchmark or discovery. Its kernel receipts, explanation, states and separately counted initialization are retained in research/mathlib-continuation-v4/.

## Remaining capability gaps

The present action vocabulary lacks generic cases, witness construction and rich induction; rewrite is limited to the left side and a bounded occurrence grammar. Retrieval covers selected namespaces and offers only six premises per state. The eight authored training problems are too narrow to establish broad transfer. The next dependency is verified, diverse premise/case/induction trajectories and independent fresh tasks, rather than selecting a model on this exposed final set. There is no production model promotion, automatic training authorization or scientific PCS authority.
