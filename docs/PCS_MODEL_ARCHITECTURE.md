# PCS reasoning network v1

10,419 allocated parameters: 257×24 shared token embeddings, 14×24 action embeddings, two genuinely trainable message-passing rounds, graph mean pooling, action-conditioned MLP policy, value and uncertainty heads. A bag-of-terms ablation shares the policy/head interface but bypasses graph message/update layers. JSON tensors are digest-pinned and loaded without pickle. CPU gradients and all checkpoints actually ran. Graph superiority, calibrated uncertainty and GPU throughput remain unestablished.

See [the consolidated execution report](PCS_OMEGA_FULL_INSTANTIATION_REPORT.md) and [exact artifacts](../research/lean-learning-v1/SHA256.json) for commands, measured results and boundaries.

## Expanded implementation v2

V2 additionally trains on projected quantified premise use and injective function composition. Parameters remain 10,419; graph message/update parameters change in real training. Three seeds show final graph 4/6, 5/6, 5/6; bag 5/6 each and symbolic 5/6. Structural advantage is not demonstrated.

See [v2 reproducible artifacts](../research/lean-learning-v2/SHA256.json).

## Checked mathematical reuse and verified feedback

ReuseNetwork adds 1,201 trainable goal/premise matching parameters to the existing network (11,620 total), consuming actual audited Lean theorem signatures. Graph/bag and RL negative results are preserved. [Training, checkpoints and comparison](PCS_CHECKED_REUSE_REPORT.md).

## October 11 induction and grounded abstraction update

See the [consolidated executable results and limitations](PCS_OMEGA_FULL_INSTANTIATION_REPORT.md#induction-grounded-abstraction-and-bridge-builder--october-11-2026) and [complete prospective experiment](../research/induction-abstraction-v2/REPORT.md). This supersedes earlier absence of implemented list/Nat induction, trainable binding graphs, independently checked state-derived lemma admission and sequential induction RL. It does not supersede the documented limits on unrestricted English, autonomous discovery or runtime refinement.

GroundedNetwork has 12,924 parameters, trainable message/update layers, binding edges, selected local/global premise attention, policy/value/uncertainty heads and checker-response training. Bag and ungrounded ablations solve the same 4/8; structural superiority remains unestablished.


## Verified Memory v1, October 12, 2026

MemoryNetwork adds a learned verifier-cost head to grounded trainable term/context graphs and a bounded residual over structural action ranking. Graph weights changed through real utility and imitation gradients; bag, untrained, supervised and successive RL checkpoints are retained. Neural ranking did not beat same-memory structural search.

Final structural solve count: 3/16 without discovered memory, 6/16 with memory; development-selected trained checkpoint supervised-17: 5/16. [Complete measured report and reproducible artifacts](VERIFIED_MEMORY_V1_REPORT.md).

Archival recovery repeated the frozen evaluations after a serialization resource failure; no weights or checkpoint selection changed. Full-cycle compute totals were not preserved and are not invented.
