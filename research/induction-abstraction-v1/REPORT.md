# Induction and checked abstraction experiment v1

The frozen validation-selected checkpoint is `graph-31`. All outcomes below are fresh Lean-verified solutions under a maximum of 96 expansions, beam 4 and depth 18. Unknown results are not proofs or counterexamples.

| Policy | Final verified / 8 | Expansions | All Lean calls incl. initial states | Search wall s |
|---|---:|---:|---:|---:|
| bag-17 | 0 / 8 | 108 | 116 | 5.20 |
| bag-31 | 0 / 8 | 144 | 152 | 6.64 |
| graph-17 | 0 / 8 | 212 | 220 | 10.72 |
| graph-31 | 0 / 8 | 212 | 220 | 11.64 |
| previous_graph | 0 / 8 | 358 | 366 | 10.74 |
| random_discovery | 0 / 8 | 40 | 48 | 0.59 |
| rl1-17 | 0 / 8 | 216 | 224 | 11.81 |
| rl1-31 | 0 / 8 | 348 | 356 | 33.66 |
| rl2-17 | 0 / 8 | 268 | 276 | 15.52 |
| rl2-31 | 0 / 8 | 288 | 296 | 24.48 |
| symbolic | 2 / 8 | 346 | 356 | 12.66 |
| symbolic_discovery | 0 / 8 | 228 | 236 | 13.87 |
| untrained-17 | 0 / 8 | 600 | 608 | 79.76 |
| untrained-31 | 0 / 8 | 68 | 76 | 2.26 |

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

CPU execution took 454.37 seconds after source capture, with 6541 training/search/evaluation/replay Lean requests or compiler calls. The independent replays omitted from the original aggregate counter are accounted for in [COST_AUDIT.json](COST_AUDIT.json). This includes unsuccessful searches and library compilation; it excludes dependency installation. Memory peak was not measured. No GPU, paid model service, artifact upload or financial expenditure was used.
Offline candidate discovery consumed 940 expansions and admitted 8 lemmas. Library construction cost 9 calls and 7.57 seconds. Search tables amortize this fixed compiled library; they are not cold end-to-end latency or total training cost.

## Interpretation and trust boundary

These are small public authored compositions with disjoint declared composition families and alpha-duplicate checks. They share underlying laws and are not private/external benchmarks. Two seeds are insufficient for a general architectural superiority claim; correlated tasks do not justify an IID confidence interval. Validation selects one checkpoint before final evaluation. No model enters production authority or edits the evaluator.
Lean verifies the exact typed theorem. It does not certify unrestricted English intent, Python/JavaScript refinement, scientific novelty, consent, empirical claims, or deployed systems. The new list/successor grammar is outside the earlier Aristotle language-reference theorem. Existing BDD, semantic and Rust formalizations are preserved.

## Negative result

Every learned final checkpoint solved 0/8; symbolic search solved 2/8. The first incomplete run exceeded the state graph bound during validation; its log and checkpoint fingerprints are preserved in `incomplete-attempt.log` and `implementation-repair.json`. The corrected run retained only five reuse imitation transitions. This experiment does not establish self-improvement.

The release preserves the exact Aristotle-bound legacy `language.py` and `ir.py`; current induction consumers explicitly import `induction_language.py` and `induction_ir.py`. The archived experimental source snapshot retains its actual original file layout for reproducibility and does not acquire the legacy parser proof by this later relocation. Neither extension is covered by that refinement theorem.
