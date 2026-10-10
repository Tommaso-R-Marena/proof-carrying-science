# PCS reasoning network v1

10,419 allocated parameters: 257×24 shared token embeddings, 14×24 action embeddings, two genuinely trainable message-passing rounds, graph mean pooling, action-conditioned MLP policy, value and uncertainty heads. A bag-of-terms ablation shares the policy/head interface but bypasses graph message/update layers. JSON tensors are digest-pinned and loaded without pickle. CPU gradients and all checkpoints actually ran. Graph superiority, calibrated uncertainty and GPU throughput remain unestablished.

See [the consolidated execution report](PCS_OMEGA_FULL_INSTANTIATION_REPORT.md) and [exact artifacts](../research/lean-learning-v1/SHA256.json) for commands, measured results and boundaries.
