# Proof-JEPA + RL research

A CPU-compatible, end-to-end trainable predictor of **actual Lean successor
proof states**, coupled to a proof-action policy. Neural outputs propose actions;
Lean checks them. Nothing here registers production PCS authority.

## Try it

From the repository root, use Python 3.12 with PyTorch 2.7.1 CPU and Lean 4.28.0:

```bash
python -m pip install --require-hashes -r requirements-build.lock -r requirements-dev.lock -r requirements-prover.lock
python -m pip install --no-deps --no-build-isolation -e .
source scripts/activate_lean_428.sh
python -m pytest -q research/proof_jepa_rl_v1
python -m research.proof_jepa_rl_v1 train --output /tmp/my-proof-jepa --seeds 17 31 47 --epochs 6 --rl-episodes 24 --budget 32
```

Choose a fresh output directory; training refuses overwrite. A bounded smoke run
uses `--seeds 17 --epochs 1 --rl-episodes 2 --budget 24`. Training writes real JSON
checkpoints, exact provenance, checked trajectories, validation selection and
held-out results. GPU acceleration is not currently wired into the CLI; the
PyTorch module can be moved to CUDA programmatically, but no GPU result is claimed.

After training, obtain the selected checkpoint name from `selection.json` and
its SHA-256 from the corresponding `results.json.gz` entry. Then:

```bash
python -m research.proof_jepa_rl_v1 solve \
  --statement 'For all propositions A and B, if (A and B) then A.' \
  --checkpoint /tmp/my-proof-jepa/CHOSEN.json --sha256 CHECKPOINT_SHA256 \
  --cache /tmp/my-proof-jepa/lean-cache --output /tmp/my-proof.json
python -m research.proof_jepa_rl_v1 replay \
  --evidence /tmp/my-proof.json --cache /tmp/independent-lean-cache
```

`--task-id identity` is an alternative to `--statement`. The controlled English
parser rejects ambiguous or unsupported input. Search may honestly return
`unknown`; this produces no accepted proof. Independent replay rebuilds the probe
and invokes the kernel on the original typed theorem and exact proof actions.

## What runs

- `data.py`: frozen 42-task corpus, 24 train / 6 validation / 12 test; 37 template
  families; alpha-AST and family firewalls; actual Lean transitions and receipts.
  Four bounded fresh-local-name augmentations use independently checked complete
  proofs of the same theorem. This is not a kernel theorem about arbitrary open
  state equivalence.
- `model.py`: learned token and child-role embeddings; two trained message-passing
  layers; trainable pooling; frozen EMA target; action/premise-conditioned latent
  predictor; learned premise compatibility, policy, value, rejection and unit-cost
  heads. It retains AST argument order and normalizes local identities. A 257-bucket
  token hash can collide; no injective semantic representation is claimed.
- `experiment.py`: common verified imitation warmup, optional one-step JEPA loss
  with variance/covariance regularization, then existing PCS sequential on-policy
  actor–critic for RL arms. Proof-guided warmup adds multi-step targets, checked
  fresh-name alignment, completion horizon and checker rejection supervision.
  The EMA is updated in warmup, not during the subsequent RL-only phase. This is
  predictive pretraining plus RL continuation, not simultaneous online JEPA/RL.
- `cli.py`: trained search, explicit evidence export, existing Canonical Claim IR /
  obligation graph and independent receipt replay. English-intent grounding and
  registered scientific authority remain blocking obligations.

All neural arms share imitation warmup. Therefore the arm labelled `rl` means
**imitation + RL without JEPA**, not pure reward-only training from scratch. The
JEPA arm has imitation plus prediction without RL. The proof-guided arm adds
supervision and computation; compare its measured cost as well as completion.
The cost head learns a unit checker-action proxy, not measured machine latency.

## Measurement protocol

Symbolic PCS search, its published graph ranker, supervised neural ranking,
JEPA, RL, JEPA+RL and proof-guided JEPA+RL receive identical 32-action-attempt,
16-depth, 4-beam limits. Initial probes, final kernel checks, failed physical
attempts, independent replays, inference time and wall time are recorded
separately. Observation caches are cleared between tasks; each policy uses its
own worker. Worker import/initialization affects the first task; timing is host-
and order-dependent even with seeded interleaving. Python CPU excludes child
Lean CPU; process-wide RSS is not per-policy memory. No GPU utilization is invented.

The held-out corpus is frozen before training. Selection uses validation only;
all final checkpoints are evaluated once. The published baseline overlaps 11 new
training theorems, with no alpha-AST overlap in new validation/test. Different
propositional tautologies can be logically equivalent; these are public structural
and template holdouts, not a secret semantic holdout or a new scientific dataset.
Two false controls and two intentionally novel quantifier/law tasks remain in test.

## Trust and review status

The host chooses the pinned PCS adapter and Lean executable. A model cannot supply
an executable, tactic source, import, reward, receipt, authority or checker policy.
Safe JSON loading checks digest, exact parameter keys, finite numbers and shapes;
it executes no pickle. A hash is not immutable storage or independent custody.
The training process trusts its host and the freshly collected records. Binary,
probe source/object and worker identities are recorded and checked during replay.

No protected source or Lean theorem file is modified. The existing V22/full-intake
reconciliation contracts freeze the complete source census and intentionally reject
new files. **This draft requires a separately reviewed successor source contract
before integration.** This work does not weaken those gates or claim protected
CI is green. The dedicated research workflow runs actual Lean and a small real
training/evaluation campaign without deployment or secrets.

See `REPORT.md`, `MODEL_CARD.md` and `evidence/` for the executed run and its limits.
