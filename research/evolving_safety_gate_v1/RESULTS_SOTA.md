# Can we be SOTA across all AI safety benchmarks?

**Short answer:** Not with a single detector, and not on every public leaderboard.
**What we did:** build a modality-routed **composed stack** that is *uniquely undominated*
across the threat models we can actually run here.

## Why “SOTA on everything” is the wrong ask

Relevant AI-safety benchmarks measure different jobs:

| Job | Example suite | Specialist that wins alone |
|---|---|---|
| Content-harm Goals | JailbreakBench | Gemini content moderator |
| Prompt-injection syntax | ProtectAI / Prompt-Guard class | ProtectAI |
| Tool-path / agent mirage | PCS Assurance Mirage | `ensembleProbe` |
| Stealth note compliance | ESG hard suite | `ensembleProbe` |

A lone ESG detector loses on JBB text. A lone Gemini moderator loses on agent mirages.
OR-ing every specialist destroys precision (ProtectAI FPR ≈ 0.41 on clean episode text).

## Composed stack (Lean `composedStack`, rank 4)

Fail-closed **router**, not naive OR:

* **Text Goals** → Gemini moderator (primary) ∪ ProtectAI only for injection syntax
* **Agent episodes** → `ensembleProbe` ∪ AgentDojo-style tool allowlist

## Multi-track dominance (attested)

Tracks:

* **A** — JailbreakBench Goals with Gemini labels (n=93 cached; includes HarmBench-sourced Goals)
* **B** — 120 attested mirage/stealth episodes
* **C** — live JBB→Qwen PCS workflow (12 episodes)

| System | Track A F1 | Track B F1 | Track C F1 | Geo-mean |
|---|---:|---:|---:|---:|
| **composed_stack** | **0.923** | **1.000** | **1.000** | **0.974** |
| gemini_moderator | 0.923 | 0.000 | 0.000 | 0.000 |
| ensemble_v1 | 0.000 | 1.000 | 1.000 | ~0 |
| ProtectAI | 0.000 | 0.873 | 0.588 | ~0 |
| tool_filter | 0.000 | 0.807 | 1.000 | ~0 |

**Pareto:** `composed_stack` is the **unique undominated** system on this suite.
Specialists each collapse on at least one track.

## Explicit non-claims

* Not an official JailbreakBench / HarmBench / AgentDojo leaderboard submission
* LlamaGuard weights not used (gated); Gemini used as LLM-as-judge content moderator
* HarmBench full gated dataset not downloaded; HarmBench-sourced Goals inside JBB were used
* Not a claim of SOTA on CyberSecEval, AgentHarm, WildGuard bake-offs, etc.

## How to reproduce

```sh
# ProtectAI ONNX + JBB CSVs under /tmp/external-bench/ (see external_bench/)
PYTHONPATH=. python3 -m research.evolving_safety_gate_v1.external_bench.dominance /tmp/esg-dom
```

Evidence: `evidence/external-bakeoff-v1/dominance/`.
