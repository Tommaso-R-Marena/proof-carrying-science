# Verified Memory v1 — executed CPU / Lean experiment

Checked reusable memory raised the grounded structural prover from **3/16 to 6/16** final solves and changed its Lean execution attempts from 651 to 495. The development-selected trained policy, **supervised-17**, solved **5/16**, versus 6/16 for structural search with identical memory. The stronger ordinary Std tactic portfolio solved 10/16. These are elementary public mathematical transfer tasks, not a claimed breakthrough or new mathematics.

The alternate checked-successor beam solved 7/16 using 1182 attempts. It was not selected on the development criterion and is not retrospectively promoted using final results. Neural/RL training did not establish superiority; the stronger structural baseline remains available. The optional public model family is explicitly experimental and does not replace the default service.

## What actually runs

A restricted mathematical English parser lowers Nat, Int, lists, functions and predicates to typed IR and Lean. MemoryEnvironment exposes structured actual Lean goals, local contexts, 13 independently audited Std theorem aliases, and four fresh checked memory entries. The graph policy ranks constrained actions; Lean checks transitions and independently compiles every successful immutable goal. Unknown is retained as unknown. A finite witness search may return a counterexample only after Lean proves the negation of the original universal theorem.

Typed anti-unification was implemented and tried; both proposed generalizations were refuted by fresh Lean checks. Of 24 proposals overall, seven were admitted, eight refuted, seven excluded and two unresolved. All seven accepted candidates arose from existing kernel-state cuts. Three of four selected entries are whole training theorem reuse, not newly discovered mathematical abstractions. The other is a checked intermediate cut. No mathematical novelty claim is made.

Seven single-candidate paired utility experiments used eight distinct utility calibration problems. Four candidates had positive observed solve/call benefit; their combination was separately evaluated. Utility is observed bounded-search performance, not minimum proof cost or a submodular guarantee. The 14,773-parameter graph/bag networks include trainable message passing, grounded premise features, policy, value, uncertainty and verifier-cost heads. Actual utility and imitation training changed graph weights. Uncertainty is not calibrated.

## Frozen protocol and complete results

The initial 34-task freeze is retained. Before model fitting/final evaluation, training-only coverage probes justified adding hypothesis-driven induction to reach **44 tasks: 12 training, eight utility, eight development selection, 16 final**. All original tasks remain. Two declared negative selection tasks were used solely for falsifier smoke and explicitly disclosed; selection is development data. The registry selected a checkpoint before any final evaluation. The first evaluation completed, but process exit 137 during combined serialization lost its detailed evaluation archive. Frozen checkpoints, the registry and original console metrics survived. Unchanged evaluations were repeated solely for archival recovery in bounded per-policy files, with no refitting or reselection. No final proof enters fitting, retrieval, memory admission or checkpoint selection. This is not a once-only or private blind final test.

Every search policy used 96 candidate expansions, beam four, depth 18. The protocol's unused `utility_budget: 64` field did not control execution: paired utility search actually used the common 96 budget. This deviation is explicit. Std uses at most three fixed whole-goal tactics (simp_all, omega, grind), each under the checker heartbeat/timeout limits; it is a strong comparison, not identical deductive work per invocation. Logical/compiler execution attempts include failures and generated module builds; successful-response counts in older admission diagnostics are separate and must not be treated as complete costs.

| Policy | Final verified | Lean attempts | Candidates | Search seconds |
|---|---:|---:|---:|---:|
| all_verified_memory | 6/16 | 495 | 473 | 84.5 |
| bag-17 | 4/16 | 949 | 929 | 283.3 |
| bag-31 | 5/16 | 806 | 785 | 167.6 |
| bounded_Std_simp_omega_grind | 10/16 | 36 | 36 | 35.6 |
| checked_successor_beam | 7/16 | 1182 | 1159 | 132.3 |
| grounded_std_structural | 3/16 | 651 | 632 | 82.1 |
| lexical_retrieval | 1/16 | 690 | 673 | 85.8 |
| original_symbolic | 0/16 | 716 | 700 | 33.0 |
| rl1-17 | 5/16 | 736 | 715 | 147.0 |
| rl1-31 | 6/16 | 873 | 851 | 228.5 |
| rl2-17 | 5/16 | 736 | 715 | 146.3 |
| rl2-31 | 6/16 | 885 | 863 | 213.3 |
| selected_memory_structural | 6/16 | 495 | 473 | 78.1 |
| supervised-17 | 5/16 | 732 | 711 | 144.7 |
| supervised-31 | 6/16 | 873 | 851 | 229.9 |
| untrained-17 | 6/16 | 499 | 477 | 89.1 |
| untrained-31 | 5/16 | 559 | 538 | 101.8 |

The selected trained model regressed relative to the same-memory structural baseline on final tasks. A 16-task authored public suite is too small and narrow for a broad intelligence or statistical breakthrough claim. Shared primitive laws are disclosed. No private blind evaluation or newly imported external project is claimed. The previously reported external-project unknowns remain unresolved.

## Real sequential learning and feedback

Two seeds, 20 imitation epochs, ten actual paired-utility epochs, two eight-episode actor–critic generations per seed: **32 actual sequential RL episodes**. Episodes include seven- and eight-action proofs; they are not solely one-step bandits. RL samples the first eight ordered training tasks, so the appended generic predicate/function tasks are supervised/memory examples, not part of these RL episodes.

- rl1-17: 8/8 terminal verified episodes; actual step counts [1, 7, 1, 1, 1, 1, 1, 8]; weights changed: True.
- rl1-31: 7/8 terminal verified episodes; actual step counts [4, 7, 1, 1, 1, 1, 1, 8]; weights changed: True.
- rl2-17: 8/8 terminal verified episodes; actual step counts [1, 7, 1, 1, 1, 1, 1, 8]; weights changed: True.
- rl2-31: 8/8 terminal verified episodes; actual step counts [1, 7, 1, 1, 1, 1, 1, 8]; weights changed: True.

`research/verified-memory-demonstration/` contains a post-training, separately authored cubic-index function-recurrence problem absent from all 44 tasks: English → IR → six-action proof → fresh Lean kernel replay → explanation → independently checked, explicitly licensed feedback → further two-epoch experimental gradient update. Learned and same-memory structural search both prove it; structural search without memory returns unknown. The feedback checkpoint is isolated and unevaluated on a new untouched holdout, never promoted and never labelled self-improvement. A separate original-goal negation proof verifies that arbitrary addition cannot always leave its first argument unchanged. CPU Adam moments and Torch RNG are saved/restored in hash-bound bounded JSON, with no pickle. An actual interrupted feedback cycle reproduced the uninterrupted candidate checkpoint digest exactly; a regression test also checks bitwise final-weight equality and rejects forged optimizer state.

## Resource and verification evidence

Recorded recovery-finalization wall time: **254.5 seconds**. Recorded recovery policy execution attempts and fresh replay: **16323**. CPU threads: 2; PyTorch 2.7.1+cpu; no GPU. The original training/discovery/failed-serialization aggregate cost and early recovery construction totals were not preserved and are not fabricated. Gradient time, energy/FLOPs and peak memory were not separately instrumented. This is not a full-cycle cost total; finalization time starts after the recorded policy archives had completed. Per-policy search times are reported individually and overlap during the three-worker recovery. Concurrent integration checks make wall time noisy, so call counts and verified outcomes are the primary comparisons. Financial spend: **0**.

The final independent replay step freshly reconstructed the checked libraries and replayed **14** selected/model and structural proof receipts. This count includes duplicate theorems across policies, not that many distinct theorem discoveries. Each final solve additionally had a kernel proof during search. Six Lean reference-boundary theorems compile in `formal/PCSVerifiedMemoryBoundary.lean`; they prove typed contracts for checked reuse, immutable goals, ranking independence and failed-attempt accounting, not Python/JavaScript refinement.

The first cost-counter attempt was stopped before any selection/final evaluation because failed/compiler-build attempts were omitted. Its partial evidence is preserved outside the repository in `.onboarding/verified-memory/incomplete-counter-attempt`, with a measurement restart receipt. The sealed package contains the preserved actual training/checkpoints and the fully archived, independently replayed recovery evaluations; it does not claim the failed original run completed successfully.

## Artifacts and reproduction

- [Frozen protocol](../research/verified-memory-v1/protocol.json), tasks and initial snapshots.
- [Metrics](../research/verified-memory-v1/summary.json), registry, checkpoint digests and independently replayed final receipts.
- `evaluations.json` is a small index of immutable per-policy compressed evaluation files; `paired-utility.json.gz`, `training.json.gz`, candidate pool and admission audit contain actual observations.
- `source-manifest.json` and `source-overlay.tar.gz` freeze the original executed algorithm at 68bac9b0d6e2d04cb16968fdb24e8308473c5485 plus the committed research changes; `EVIDENCE_SHA256.json` seals file membership/bytes. The final release adds integration code and fixes fresh hole-name allocation; those do not retroactively alter the frozen run.

```bash
source scripts/activate_lean_428.sh
python scripts/check_memory_evidence.py
python scripts/check_memory_runtime.py
python -m pcs.experimental.prover.memory_cli \
  'For all functions from natural numbers to natural numbers f, if (∀ (k : Nat), f(the successor of k) equals (f(k) + 1)) then (∀ (n : Nat), f(((n * n) * n) + 2) equals (f(0) + (((n * n) * n) + 2))).' \
  --models research/verified-memory-v1 --output /tmp/pcs-memory-loop.json
```

To reproduce training, make a fresh output directory containing only the frozen `tasks.json` and `protocol.json`, use the released streaming-recorder implementation in an isolated checkout, and run `python -m pcs.experimental.prover.memory_experiment --output <directory>`. The original source overlay preserves the pre-failure combined serializer for audit; the released driver writes each policy incrementally. The completed original directory refuses overwrite. CPU training is real; exact wall times are not reproducible constants.

## Public interface and assurance limits

Memory Workshop has four real checked missions, including seven/eight-step induction, an explicit tutorial, hint/undo tracking, keyboard/click/drag navigation, exact proof download and fresh protected public checks. The browser replays a finite catalog of real Lean transitions; it does not invoke Lean on each click. Adult CC0 opt-in sessions require a verified account, bounded server replay, identity-free Owner export and fresh independent kernel intake before training. Utility-calibration missions retain the utility split and cannot silently enter ordinary behavior-cloning training. Deletion removes active rows; earlier exports/weights are a separate issue. Integration fixtures are synthetic, with zero human participants.

The optional `verified-memory-v1` public workflow compares the actual trained model, same-memory structural search and structural search without memory. The packet losslessly interns repeated premise catalogs, checks their digests and bounds expansion to four MB; wire bounds remain one MB decoded and 48 KB compressed. Exact statement, goal, model-family, human-action and protected source/workflow ticket bindings remain mandatory. A fourth explicit comparison invokes fixed ordinary Lean tactics with fresh kernel checking; it is never attributed to the learned model. No production secrets, financial input, paid runners, paid GPU or new provider resources are used.

English intent and general language semantics remain outside kernel certification. Learned weights cannot authorize proof success, rewards, model promotion or PCS scientific authority. Runtime extraction/refinement, JSON/hash/authentication/browser semantics, larger Mathlib domains, learned formalization generalization and calibrated uncertainty remain open obligations. Existing Aristotle proofs and protected gates are preserved.
