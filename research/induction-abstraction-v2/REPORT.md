# Induction and checked abstraction experiment v2

The frozen validation-selected checkpoint is `graph-17`. All outcomes below are fresh Lean-verified solutions under a maximum of 96 expansions, beam 4 and depth 18. Unknown results are not proofs or counterexamples.

| Policy | Final verified / 8 | Expansions | All Lean calls incl. initial states | Search wall s |
|---|---:|---:|---:|---:|
| bag-17 | 4 / 8 | 238 | 250 | 19.77 |
| bag-31 | 4 / 8 | 209 | 221 | 17.45 |
| graph-17 | 4 / 8 | 227 | 239 | 19.90 |
| graph-31 | 4 / 8 | 210 | 222 | 17.83 |
| previous_graph | 1 / 8 | 328 | 337 | 8.93 |
| random_discovery | 0 / 8 | 64 | 72 | 2.47 |
| rl1-17 | 4 / 8 | 243 | 255 | 21.72 |
| rl1-31 | 4 / 8 | 206 | 218 | 16.93 |
| rl2-17 | 4 / 8 | 259 | 271 | 21.86 |
| rl2-31 | 4 / 8 | 207 | 219 | 18.50 |
| symbolic | 5 / 8 | 366 | 379 | 14.21 |
| symbolic_discovery | 1 / 8 | 237 | 246 | 16.32 |
| ungrounded-17 | 4 / 8 | 230 | 242 | 20.84 |
| ungrounded-31 | 4 / 8 | 310 | 322 | 28.67 |
| untrained-17 | 0 / 8 | 576 | 584 | 87.97 |
| untrained-31 | 0 / 8 | 128 | 136 | 12.78 |

## Evidence and reproducibility

- Frozen protocol: [protocol.json](protocol.json); authored typed tasks: [tasks.json](tasks.json).
- Every checkpoint and digest: [registry.json](registry.json). Weights are safe JSON tensors, not executable pickle.
- Exact executed source snapshot: [source-overlay.tar.gz](source-overlay.tar.gz), [source-manifest.json](source-manifest.json). Reproduction must use this snapshot, rather than assume later source changes reproduce historical metrics.
- Checker-derived trajectories and RL reports are in `initial-trajectories.json[.gz]`, `training-trajectories.json[.gz]`, and `training.json[.gz]`. The `.gz` suffix is used for large artifacts.
- Full per-problem searches: [evaluations.json.gz](evaluations.json.gz). Independently reconstructed final proofs: [independent-final-replay.json](independent-final-replay.json).
- Candidate proposals, actual states and admission results: `discovery.json[.gz]`; admitted typed proofs: [library.json](library.json). Whole training theorems are distinguished from genuinely smaller cuts. No novel mathematics is claimed.
- Complete byte seal: [EVIDENCE_SHA256.json](EVIDENCE_SHA256.json). Artifact checking alone is not kernel verification.

```bash
source scripts/activate_lean_428.sh
python -m pcs.experimental.prover.abstraction_experiment --output <new-folder-containing-frozen-protocol-and-tasks>
python scripts/check_induction_evidence.py
```

## Resource accounting

CPU execution took 876.05 seconds after source capture, with 8031 training/search/evaluation/replay Lean requests or compiler calls. The independent replays omitted from the original aggregate counter are accounted for in [COST_AUDIT.json](COST_AUDIT.json). This includes unsuccessful searches and library compilation; it excludes dependency installation. Memory peak was not measured. No GPU, paid model service, artifact upload or financial expenditure was used.
Offline candidate discovery consumed 940 expansions and admitted 8 lemmas. Library construction cost 9 calls and 7.76 seconds. Search tables amortize this fixed compiled library; they are not cold end-to-end latency or total training cost.

## Interpretation and trust boundary

These are small public authored compositions with disjoint declared composition families and alpha-duplicate checks. They share underlying laws and are not private/external benchmarks. Two seeds are insufficient for a general architectural superiority claim; correlated tasks do not justify an IID confidence interval. Validation selects one checkpoint before final evaluation. No model enters production authority or edits the evaluator.
Lean verifies the exact typed theorem. It does not certify unrestricted English intent, Python/JavaScript refinement, scientific novelty, consent, empirical claims, or deployed systems. The new list/successor grammar is outside the earlier Aristotle language-reference theorem. Existing BDD, semantic and Rust formalizations are preserved.

## Grounded model and sequential learning

The binding-aware network has 12,924 parameters. Its expression graph links variable occurrences to their declarations and bound variables to their binders. A selected-premise graph head grounds local exact/apply/rewrite actions. A learned checker-response head trains on 180 real valid/invalid attempts. Imitation retains 39 checked transitions, including the original induction proofs. Two seeds each run two eight-episode actor–critic generations; 32 genuine sequential episodes include 24 verified training proofs and up to ten actions. No policy supplies its own rewards.
The trained and RL variants solve 4/8, untrained variants 0/8, the previous model 1/8 and symbolic search 5/8. Graph and bag encoders tie on solve count. Binding-aware encoding reduces expansion counts in some comparisons but does not establish a consistent superiority result. RL changes weights and sometimes costs; it does not increase final solve count. The validation-selected supervised checkpoint remains selected.

## Operational pipeline and follow-up checks

[unseen-multistep-end-to-end.json](unseen-multistep-end-to-end.json.gz) records a newly authored, untrained English list-length congruence problem solved with five learned actions and a fresh kernel check. [explicit-feedback/report.json](explicit-feedback/report.json) records independent feedback intake and a real additional candidate training update. That candidate is unapproved, not deployed and not called an improvement without held-out evaluation.
[external-results.json](external-results.json) records three previously untrained types extracted from the exact Lean 4.28 standard library (Apache-2.0). Both policies return unknown on all three. Source reference proofs are used only for independent type extraction, never passed into training or retrieval. This exposes missing cancellation, reversal and disjointness capabilities; it is not general Mathlib competence.
The three-obligation research plan, original failed memory and repaired memory are in `research-plan.json`, `research-memory.json[.gz]` and `research-memory-repaired.json.gz`. A retrieval priority bug starved introductions under list binders. The repaired explicit scheduler proves the dependent chain; it remains a human-supplied plan, not learned autonomous research. `posthoc-retrieval-repair.json.gz` reevaluates the corrected deterministic retrieval only; those results do not alter frozen checkpoint selection.
Bridge Builder exposes four public training missions built from actual Lean transitions. Practice replays the archived forest; a separate protected workflow freshly compiles the exact human path. Adult CC0 donation, owner-only export, active erasure, hint tracking and independent Lean training intake are implemented. No real participant data is fabricated or claimed to have trained these models.

A separate [cold end-to-end run](cold-end-to-end.json.gz) includes fresh environment construction, fixed-library compilation and model loading: the new five-action statement verifies in 16.18 s using the learned policy/library and 5.38 s using symbolic search. Offline discovery/training costs remain additional.

The posthoc deterministic retrieval repair solves 5/8 of the v2 final set, versus its original 1/8. This is a human scheduler fix after inspecting failures, separately labeled and not evidence of autonomous model self-improvement.
