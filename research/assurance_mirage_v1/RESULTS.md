# Assurance Mirage v1 — observed results

Fresh local CPU runs with sealed memfd weight snapshots. No prompt tuning,
response selection, or training. Every planned episode retained.

## Formal

Seventeen theorems in `AssuranceMirage` compiled with Lean 4.28.0 and
`leanchecker --fresh`. Axiom closures use only `propext` and/or `Quot.sound`.
Channel-1-only scores cannot separate a constructive safe/unsafe mirage pair;
channels 2 and 3 and the joint score can. The constructive mirage holds for
every fuel budget; without the guard the unsafe proposer stalls while the safe
proposer completes.

## Qwen3-0.6B Q8_0 (112 completions, 28 episodes, 14 cases × 2 arms)

| Metric | Value |
|---|---:|
| Guarded completions | 28/28 |
| Proposal-harm episodes | 12/28 |
| Raw or split-leak episodes | 6/28 |
| Scope-escalation episodes | 2/28 |
| Mirage episodes | 15/28 |
| Mirage rate among attacks | 62.5% |
| Channel-1 would report perfect safety | yes |

Classic AgentDojo-style families (direct, ignore-previous, system-message,
important-instructions, smuggle, scope) remain near-saturated mirages.
Adaptive / authority-spoof / tool-injection families did not produce mirages on
this weight under the same decoding pins.

## Qwen3-1.7B Q8_0 (112 completions, 28 episodes)

| Metric | Value |
|---|---:|
| Guarded completions | 28/28 |
| Proposal-harm episodes | 16/28 |
| Raw or split-leak episodes | 15/28 |
| Scope-escalation episodes | 2/28 |
| Mirage episodes | 21/28 |
| Mirage rate among attacks | 87.5% |
| Channel-1 would report perfect safety | yes |

The larger local weight leaked more often under the same attacks while guarded
tool success stayed perfect. This does **not** establish a size law; it is a
paired local observation on two fixed weights.

## Gemini Flash-Lite (hosted free-tier arm)

Model `gemini-flash-lite-latest` via Generative Language API, ≥6s spacing,
hard per-wave request caps. Combined census (`evidence/gemini_combined/`):
**28 episodes** across plain and instruction-boundary arms, including adaptive,
authority-spoof, and tool-return-injection cases.

| Metric | Combined |
|---|---:|
| Guarded completions | 28/28 |
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

Replaying recorded proposals **without** the correcting guard:

| Source | Episodes where guard prevented unsafe public effect | Private marker published unguarded |
|---|---:|---:|
| Qwen3-0.6B | 5 | 5 |
| Qwen3-1.7B | 16 | 16 |
| Gemini flash-lite | 0 | 0 |

Artifacts: `evidence/unguarded_replays/`, `evidence/compare.json`,
`evidence/analysis/` (family tables + Wilson intervals + cross-model contingency).

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
- `evidence/gemini_*` waves and `evidence/gemini_combined/`.
- `evidence/hf_secondary_unavailable.json`: HF Inference Providers arm refused
  without a shell API token (MCP OAuth is not a substitute).

Replay without weights:

```sh
PYTHONPATH=. python3 -m research.assurance_mirage_v1 replay \
  research/assurance_mirage_v1/evidence/qwen06b /tmp/mirage-replay-06
PYTHONPATH=. python3 -m research.assurance_mirage_v1 analyze \
  research/assurance_mirage_v1/evidence /tmp/mirage-analysis
```
