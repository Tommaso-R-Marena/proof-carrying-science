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

## Gemini Flash-Lite (hosted free-tier arm)

Model `gemini-flash-lite-latest` via Generative Language API, project
`171569345899`, ≥6s spacing (~10 RPM), hard per-wave request caps.

Combined census (`evidence/gemini_combined/`): **17 episodes / 68 completions**
across instruction-boundary (12) and plain (5) arms, including scope-escalation,
split-channel, JSON-smuggle, and adaptive roleplay/encoding attacks.

| Metric | Combined |
|---|---:|
| Guarded completions | 17/17 |
| Proposal-harm | 0 |
| Raw/split leaks | 0 |
| Scope escalations | 0 |
| Mirages | **0** |

Gemini refused the attack goals while still completing the workflow under the
guard. This does **not** prove general Gemini safety; it shows the mirage
phenomenon is model-dependent on this finite suite.

The API key is **not** stored in evidence. Absolute remaining project RPD/RPM is
**not** exposed by this API key (Service Usage returns 401). Live limits:
https://aistudio.google.com/rate-limit.

## Unguarded replay control (0 API calls)

Replaying recorded proposals **without** the correcting guard, and treating
notes/raw text as a public channel:

| Source | Episodes where guard prevented unsafe public effect | Private marker published unguarded |
|---|---:|---:|
| Qwen3-0.6B | 5 | 5 |
| Qwen3-1.7B | 13 | 12 |
| Gemini flash-lite | 0 | 0 |

So for Qwen, guarded “perfect completion” concealed proposer failures that an
unguarded executor would have made public. For Gemini on this suite, the
proposer itself did not create those unsafe effects.

Artifacts: `evidence/unguarded_replays/`, `evidence/compare.json`.

## Formal v1.1

Eleven theorems, including `guard_erases_divergence`, `unguarded_diverges`, and
`guard_completion_independent_unguarded_not`: the guard equalizes tool traces
across proposers; removing it lets safe and unsafe proposers diverge.
