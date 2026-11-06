# Experimental model card

**Intended use:** local research on ranked typed proof actions. Not a registered
PCS authority, general theorem prover, AI safety guarantee or production model.

The online graph encoder, predictor and policy are trainable PyTorch modules.
The target encoder starts as a copy and receives exponential moving averages.
The policy uses action-conditioned successor predictions and learned local-premise
compatibility. Proof acceptance always requires the existing PCS Lean environment
and final kernel/axiom audit of the original theorem. No model chooses reward labels.

**Data:** PCS-authored Apache-2.0 typed elementary propositions and natural-number
problems. Exactly 24 training tasks; no external Aristotle development traces,
private data, external research results or test trajectories enter training.
Training uses actual Lean transitions and independently replayed complete proofs.
Invalid actions are negative checker observations; open states are not certificates.
Four fresh-local-name augmentations are checked as whole proofs of the same theorem.

**Limitations:** small public corpus; related primitive tactics across partitions;
logical equivalence of tautologies; 257 token-hash buckets; limited permitted actions;
no general semantic injectivity; host-controlled compiler/storage; warmup-only EMA;
RL relies on the existing research reward and budget design. No assurance that the
neural representation or Python implementation is kernel-proved. Learned value,
cost and rejection heads can be wrong. Unit-cost targets do not predict latency.
No real-model LLM safety experiment, scientific generalization or self-improvement
acceleration is claimed. Numerical test results are in REPORT.md.

**Checkpoint handling:** bounded JSON, no executable deserialization. The expected
SHA-256 must come from a trusted local record; digest checks alone cannot provide
independent provenance or protect a compromised host. Checkpoint metadata identifies
method, seed and exact compressed training-corpus/protocol digests. Only the
validation-selected overall and proof-guided checkpoints are retained to limit weight size;
the reproduction command regenerates every comparison checkpoint.
