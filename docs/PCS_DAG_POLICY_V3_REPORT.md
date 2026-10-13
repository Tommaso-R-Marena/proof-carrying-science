# Expression DAG policy and sequential RL v3

This release actually trains a position-sensitive DAG policy on real Lean proof
states and loads it into the existing checked-successor proof-search engine.
It does **not** improve on the strongest symbolic baseline. All checkpoints stay
experimental; no model or scientific acceptance rule is promoted.

## Executed results

The protocol and twelve final challenge statements were written before any
new gradient updates. Eight pre-existing, authored Apache-2.0 logic training
trajectories were independently reconstructed by the current Lean 4.28
kernel. Arithmetic and function training examples were excluded. The resulting
39 valid transitions trained two 6,099-parameter networks for twenty epochs with
seed 43 and two CPU Torch threads. The DAG policy's message, update and edge-type
parameters changed through genuine gradient updates. The bag ablation has the
same serialized parameter schema; its unused graph parameters do not change.

| Policy | Twelve final typed tasks solved | Comparison |
|---|---:|---|
| Receiver symbolic action ranking | 5/12 | Fixed 48 expansion, depth 18, beam 4 budget |
| Trained expression DAG | 4/12 | Same receiver actions and search budget |
| Trained bag ablation | 3/12 | Same receiver actions and search budget |
| Ordinary Std tactics | 12/12 | Additional post-evaluation diagnostic; three whole-goal tactics, different internal work |

All twelve successful runs in the 36 primary comparisons were independently
re-elaborated against the immutable original statement in separate compiler
invocations. The final tasks contain natural-number congruence and existential
witnesses, integer order and antisymmetry, function/predicate transport and list
identities. These are author-known elementary mathematics. The corpus is a
bounded domain-transfer challenge, **not** a private blind benchmark, novel
mathematics, or evidence of general English-to-Lean capability. Alpha duplicates
are rejected between training and final splits; semantic near-duplicate
contamination is not exhaustively excluded.

The primary experiment used 1,555 measured physical compiler/worker requests,
110.43 seconds total wall time, 47.79 child user CPU seconds and 23.27 child system
CPU seconds. Peak Python process RSS was 273,004 KiB. Eight training proofs cost
16 Lean requests and 18.26 seconds; gradient training cost 3.46 seconds for DAG
and 1.18 seconds for bag. Per-search and independent-replay costs are separate
in `results.json.gz`. Construction is separately recorded in `training.json`.
These are execution costs on this shared CPU environment, not paid-service
costs or accelerator benchmarks.

## Actual sequential reinforcement learning

A separate protocol froze four additional final statement structures before
RL updates. The old twelve outcomes were not tuned against. Existing
`LeanEnvironment.step` generated all observations, rewards and terminal statuses;
only its kernel verification can generate the terminal +1 reward. The DAG policy
ran eight sequential on-policy actor-critic episodes on the eligible logic
training set, with seed 59 and twelve-step episode limit. Seven episodes completed
kernel-checked proofs; one invalid episode was preserved. Episode lengths were
3, 6, 4, 7, 5, 5, 4 and 5 actions. All seven positive terminals were independently
rechecked. Weights changed and a real updated JSON checkpoint was saved.

| Policy | Four new final tasks solved |
|---|---:|
| Symbolic action ranking | 2/4 |
| Supervised DAG | 2/4 |
| RL-updated DAG | 2/4 |
| Separately measured ordinary Std | 4/4 |

RL consumed 54 measured Lean requests and 18.27 seconds for actual training,
with independent terminal replay recorded separately. Evaluation consumed 438
requests including action-search proof checks and the separate standard baseline
calls. Fresh standard replay helpers create their own environments and their
calls are retained in each replay receipt; they are additional to that 438.
This single-seed, four-task result shows **no measured RL improvement**. It does
not support a self-improvement claim. Both supervised and RL checkpoints remain
available for honest comparison; the stronger symbolic/Std systems are retained.

## Actual Mathlib diagnostics

Four additional developer-owned proposition types were fixed in a separate
post-evaluation diagnostic protocol. The existing `MathlibRetriever` used the
approved Mathlib revision `8f9d9cff6bd728b17a24e163c9402775d9e6a365`, real
elaborator-extracted theorem signatures and a three-lemma structural retrieval
budget. Preimage intersection and preimage union were proved and independently
kernel replayed. Group inverse-product and right-cancellation queries remained
UNKNOWN at that budget. All four actual rich Mathlib states round-tripped
losslessly through the DAG representation, including binder edges.

This verifies the representation against actual Mathlib expressions. It does
**not** integrate the learned DAG ranking with Mathlib theorem retrieval: the
current policy ranks the existing receiver action language, whose admissible
named lemma catalog is narrower. Extending that typed action/catalog interface
and training on module-disjoint Mathlib trajectories is an outstanding dependency.

## Interfaces and evidence

`pcs/experimental/prover/dag_policy_v3.py` exposes `DAGPolicy.rank(state, options)`
and digest-checked `DAGPolicy.load(path, sha256)`. This directly plugs into the
existing `memory_search` engine; it does not create a competing checker. Position
and binder edge relations are trainable. Checkpoints are bounded JSON tensors;
shape, schema, non-finite values and digests are validated. No pickle or model
supplied tactic/source is executed. The Lean environment alone renders typed
actions, retains the immutable goal and checks final proofs.

Primary checkpoint digests:

- DAG: `4af8b94a6be4996d3f08e73b9b0d6a91610ef5c4b88d783f185c630076a8d8a6`
- Bag: `8d18bd319a6da1626bedf84e95480668790e71e7b4800218ab9f1d204d2720f2`
- RL DAG: `875b5af533e297a85d71f33e3d1444c6b86297ecc43230aa94093d9052aaa343`

All artifacts are in `research/dag-policy-v3/`: frozen protocols and typed tasks,
checked training states, actual checkpoints, compressed full search attempts,
independent proof receipts, Mathlib/Std diagnostics, RL trajectories and summaries.
`checkpoint-cli.json` is a real loaded-checkpoint search and fresh kernel replay
of an already published final challenge, an operational check rather than an
additional unseen test. `manifest.json` binds the exact retained artifact bytes;
it is an unsigned integrity manifest, not an independent attestation.

Reproduce into a **new** output directory to preserve historical evidence:

```bash
source /workspace/.onboarding/activate.sh
source scripts/activate_lean_428.sh
python -m pcs.experimental.prover.dag_experiment_v3 freeze --output /tmp/pcs-dag-reproduction
python -m pcs.experimental.prover.dag_experiment_v3 run --output /tmp/pcs-dag-reproduction
python -m pcs.experimental.prover.dag_diagnostics_v3 --output /tmp/pcs-dag-reproduction
python -m pcs.experimental.prover.dag_rl_v3 --output /tmp/pcs-dag-reproduction
python -m pytest -q tests/test_dag_policy_v3.py tests/test_dag_policy_v3_research.py
```

Saved-checkpoint execution:

```bash
python -m pcs.experimental.prover.dag_experiment_v3 solve \
  --checkpoint research/dag-policy-v3/dag.json \
  --sha256 4af8b94a6be4996d3f08e73b9b0d6a91610ef5c4b88d783f185c630076a8d8a6 \
  --goal research/dag-policy-v3/checkpoint-cli-goal.json \
  --output /tmp/pcs-loaded-dag-proof.json
```

Nine focused tests pass, including actual graph gradients, binder/edge behavior,
checkpoint tampering and invalid actions, frozen split/checkpoint/receipt
integrity, and RL positive-reward binding to independently checked terminal
receipts. These fast tests validate artifact integrity; they do not substitute
for the executed kernel proof campaigns.

The next technical dependency is a richer, receiver-controlled Mathlib action
catalog and module-disjoint multi-step trajectories. The negative transfer and
RL results favor strengthening grounded premise/action representations before
scaling this small architecture or claiming an intelligence breakthrough.
