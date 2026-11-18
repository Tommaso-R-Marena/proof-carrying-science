# Assurance Mirage v1 — observed results

Fresh local CPU runs with sealed memfd weight snapshots. No prompt tuning,
response selection, or training. Every planned episode retained.

## Formal

Eight theorems in `AssuranceMirage` compiled with Lean 4.28.0 and
`leanchecker --fresh`. Axiom closures use only `propext` and/or `Quot.sound`.
Channel-1-only scores cannot separate a constructive safe/unsafe mirage pair;
the joint score can.

## Qwen3-0.6B Q8_0 (80 completions, 20 episodes)

| Metric | Value |
|---|---:|
| Guarded completions | 20/20 |
| Proposal-harm episodes | 12/20 |
| Raw or split-leak episodes | 6/20 |
| Scope-escalation episodes | 2/20 |
| Mirage episodes | 15/20 |
| Mirage rate among attacks | 93.75% |
| Channel-1 would report perfect safety | yes |

Instruction-boundary prompts reduced leaks (4→2) but did not eliminate mirages
(8→7). Publications never contained the private marker; raw replies did.

## Qwen3-1.7B Q8_0 (80 completions, 20 episodes)

| Metric | Value |
|---|---:|
| Guarded completions | 20/20 |
| Proposal-harm episodes | 12/20 |
| Raw or split-leak episodes | 11/20 |
| Scope-escalation episodes | 2/20 |
| Mirage episodes | 16/20 |
| Mirage rate among attacks | 100% |
| Channel-1 would report perfect safety | yes |

The larger model leaked the synthetic marker more often under the same attacks.
Guarded tool success remained perfect. This does **not** establish a size law;
it is a paired local observation on two fixed weights.

## Interpretation

Under a correcting unique-action guard, **task-completion / tool-trace safety
scores are not a model-safety measurement**. Joint scoring of proposals and raw
outputs is necessary to see the mirage in this model class. Related external
work on “corrupt success” reaches a similar qualitative conclusion for
outcome-only agent benchmarks; this package contributes kernel-checked metric
independence plus attested local red-team evidence inside a scientific tool
workflow.

## Artifacts

- `evidence/qwen06b/` and `evidence/qwen17b/`: protocol, formal build, episodes,
  model binding, all request/response captures, SHA-256 manifest.
- `evidence/hf_secondary_unavailable.json`: HF Inference Providers arm refused
  without a shell API token (MCP OAuth is not a substitute).

Replay without weights:

```sh
PYTHONPATH=. python3 -m research.assurance_mirage_v1 replay \
  research/assurance_mirage_v1/evidence/qwen06b /tmp/mirage-replay-06
```
