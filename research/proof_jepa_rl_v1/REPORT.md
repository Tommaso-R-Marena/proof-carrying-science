# Executed Proof-JEPA / RL experiment

This system trained real neural models, searched with them, and checked their
proofs through Lean. **The primary experiment did not improve verified reasoning
per computation over PCS symbolic search.** Predictive loss reduction and nonconstant
embeddings do not establish better mathematical reasoning.

## Experiment and evidence

Base: protected main `bc78660b5fac857fce3873eb6cda0445d1903da1`.
Primary numerical run: implementation commit `383ad23`; its original protocol and
source manifest remain in `evidence/protocol.json`. Later parser/provenance,
replay and measurement corrections do not change those historical measurements.
Final research source qualification: `6aaa0d3` (37 tests passed).
A fresh-cache bundle replay independently rechecked **all 97 proof occurrences**
(23 training + 4 fresh-name + 70 test), plus one probe compilation: 98 calls.
The generated demo also compiled directly with `import Lean` and no axioms.
The old `pcs/` and `formal/` trees are unchanged; no production authority is added.

CPU Python 3.12 / PyTorch 2.7.1+cpu / Lean 4.28.0. No GPU was available.
The new neural arms have **31,780 trainable parameters** plus frozen EMA targets;
retained JSON checkpoints are about 867 KiB each. Full run: 15 real trained models
(5 arms × seeds 17,31,47), plus existing deterministic/published policies.

Frozen corpus: 24 training, 6 validation, 12 test records, 37 declared template
families. Exact alpha-normalized AST duplicates and cross-split families are
rejected. Test comprises **10 target theorems and 2 false controls**; raw `/12`
completion therefore has a ceiling of 10/12. Repeated seeds do not create 30
independent theorem problems. Related tactics and logically equivalent tautologies
can cross partitions. These are small public authored structural holdouts.
The published baseline overlaps 11 new training theorems and no new validation/test
alpha-normalized theorem; its older training quantity is a comparison confound.

Actual collection: **23/24 training theorems kernel-accepted and independently
replayed**, 264 transitions (122 valid observations, 142 invalid), 98 transitions
on complete accepted trajectories, 4 separately checked fresh-name trajectories.
Collection took 55.21 s and 347 completed Lean calls. `truth_pair` remained unsolved
under the original candidate mask; it was retained rather than relabelled or removed.
Warmup took 66.42 s across 15 models. Nine RL continuations used 1,237 completed
checker calls and 129.29 s. Setup, validation and final evaluation are additional.

## Primary results

All policies receive a 32-action-attempt budget, depth 16 and beam 4. Observation
caches are cleared between tasks. Every accepted proof is independently replayed
again. Counts below include completed initial/verification work and unsuccessful
spend over all 12 tasks. Lower wall time with fewer proofs is not better proof
efficiency. Timing is host dependent; Python CPU excludes Lean children.

| Method | Target theorems proved, seeds 17 / 31 / 47 | Completed checker calls per solve, pooled | Mean evaluation wall seconds |
|---|---:|---:|---:|
| PCS symbolic | 5/10 (one deterministic run) | 46.00 | 13.84 |
| Published PCS graph ranker | 3/10 (one checkpoint) | 73.33 | 9.72 |
| New supervised graph policy | 4 / 5 / 4 of 10 | 52.08 | 12.42 |
| JEPA, no RL | 4 / 5 / 4 of 10 | 52.23 | 12.57 |
| RL, no JEPA | 3 / 5 / 4 of 10 | 56.58 | 11.72 |
| JEPA + RL | 4 / 4 / 2 of 10 | 66.80 | 10.54 |
| Proof-guided JEPA + RL | 5 / 5 / 4 of 10 | 49.14 | 13.83 |

**False controls accepted: 0/2 in every policy**, 0/34 policy–control evaluations.
There are **70 accepted held-out proof occurrences and 70 separate kernel replay
receipts**. These are repeated elementary theorems, not 70 newly discovered results.
Every neural solve belongs to the symbolic baseline's solved set. Symbolic solves:
`four_chain`, `contrapositive`, `or_absorption`, `nat_mixed_identity`,
`existential_reflexivity`. Missing a proof does not establish that a theorem is false.

The validation-only selection chose `rl-17`, which solved just **3/10** at test.
The best proof-guided validation choice is `proof_guided-17`, which solved **5/10**.
Both are retained; no selection was changed using test results. The latter matches
symbolic coverage, with 232 completed calls versus 230; it does not beat symbolic
search. Mean neural rank latency was roughly 3.7–5.0 ms per ranking call; the
published ranker was 1.43 ms. Process-wide Python peak RSS was 301,064 KiB; this
excludes Lean-child memory and is not a per-policy peak or utilization measurement.

## What the implementation establishes

The graph encoder learns embeddings, ordered role-aware message passing and pooling.
Actual accepted successor states supervise an action-conditioned predictor against
an EMA target, not reconstruction of the source text. Policy scores use predicted
latents and learned local-premise compatibility. All available trained arms changed
the online encoder and predictor tensors; target tensors changed via EMA with
`requires_grad=False`. Shared verified imitation warmup makes comparisons explicit. All new arms retain
the same architecture; “no JEPA” omits its predictive objective, rather than
removing the latent predictor from policy scoring.
RL then uses existing PCS on-policy actor–critic with actual checker rewards.

JEPA did not improve completion over same-capacity supervised training. RL often
degraded the policy. Proof guidance mitigated the combined arm's degradation but
introduced additional supervision and compute, without exceeding symbolic coverage.
The bounded action library cannot express some useful steps (for example the
unseen distributivity probe lacks `Nat.mul_add`); not every failure diagnoses the
representation. This experiment does not isolate each proof-guided loss separately.

The proof-guided objective uses multi-step teacher-forced action/premise contexts,
completion-horizon and rejection labels, unit checker-action cost, and fresh-name
alignment of two fully checked proofs of the **same original theorem**. It is not a
kernel theorem about arbitrary open-state equivalence. The target receives EMA
updates during warmup only; RL is a subsequent continuation, not simultaneous
online JEPA/RL. No learned policy can approve a proof or supply its reward.

## Exploratory improvement: decorrelation

A training-only diagnostic, declared before final results were inspected, increased
the covariance coefficient from .02 to .5. It read only the same 98 completed-proof
training states, used the same six epochs and seeds 17/31, and wrote no checkpoint.
No validation/test state was used and the primary benchmark was not changed.

| Seed | Covariance participation dimension, original → stronger penalty | Off-diagonal penalty, original → stronger |
|---|---:|---:|
| 17 | 2.2976 → 3.4207 | .18847 → .02375 |
| 31 | 1.5666 → 3.2198 | .17381 → .01289 |

This is a reproducible improvement in finite training covariance, **not** proof of
non-collapse, semantic quality, held-out performance or safety. Effective dimension
remains about 3/24. Different checkpoints from this exploratory diagnostic were not
promoted or substituted into the primary comparison.

## Verification, failures and limits

- Existing baseline: **75 passed** after memory cleanup. The first run had
  14 failures / 61 passes; raw Lean worker exit -9 and host OOM events implicated
  memory exhaustion. Only disposable Git fixtures and regenerable browser/npm
  caches were removed; the checker and mathematical statements were unchanged.
  `RESOURCE_FAILURES.json` distinguishes this observation from retained raw logs.
- New package: **37 tests passed** in final local qualification, including actual
  Lean receipt/false-claim/provenance tests, seeded real training reproducibility,
  frozen EMA checks, AST argument order, strict checkpoint/JSON integrity and
  bounded archive reads. No mock affirmative verifier is used.
- GitHub research CI at `00424b6`: **32 tests passed**, plus real one-seed smoke
  training and held-out evaluation; [run 42141801240](https://github.com/Tommaso-R-Marena/proof-carrying-science/actions/runs/42141801240).
  Its smoke uses one epoch, two RL episodes and budget 24; its scores are not the
  three-seed experiment above. Final-head CI is tracked on PR #199 and also rebuilds/replays the retained proof bundle.
- The source-policy job correctly fails with `combined tracked file census differs`
  because the protected historical contracts freeze the entire tree. Downstream
  core gates consequently skip. This draft needs a separately reviewed successor
  source contract before integration. No guard or required check was weakened.
- Primary `physical_call_attempts` is a wrapper counter that omits one nested worker
  bootstrap per policy. Raw artifacts are preserved. The completed-call table
  above includes bootstrap and avoids that undercount; wire counts are also retained.
  Future runs use explicit initialization-inclusive measurement version 2.
- Host/storage, toolchain and input provenance remain assumptions. Hashes are not
  immutable custody. Lean proves the rendered theorem, not intended English,
  Python correctness, neural generalization, scientific validity or general safety.
  Existing Claim IR keeps intent-grounding and registered-authority obligations open.

## Reproduce and next milestone

See README for full and bounded CPU commands. `evidence/` retains tasks, exact
protocol/source hashes, full compressed transition and result records, all nine RL
logs, two real checkpoints, selection, failures and a model-generated proof demo.
Use `python -m research.proof_jepa_rl_v1.replay --directory research/proof_jepa_rl_v1/evidence`
to check the bundle; add `--cache /tmp/fresh-jepa-replay` to kernel-replay the original
training proofs, augmentations and all accepted test proofs independently.

The next justified milestone is a pre-registered larger corpus with adequately
expressive actions and harder retrieval distractors, paired cost measurements,
separate ablations of multi-step/alpha/horizon losses, and genuinely interleaved
predictive learning on new RL trajectories. Use another untouched test set before
claiming a gain. Expanding architecture or promoting these weights now is not
supported by this experiment.
