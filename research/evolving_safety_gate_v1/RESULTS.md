# Evolving Safety Gate v1 — observed results

## Formal

Seventeen theorems in `EvolvingSafetyGate` (Lean 4.28.0, `leanchecker --fresh`).
Channel-1-only and correcting-guard-only mechanisms are never admissible.
`ensembleProbe` formally dominates `jointDetectingGuard`. Retention requires
formal domination on detectability rank; retained champions stay admissible.
Non-admissible mechanisms never dominate admissible ones.

## Hard suite (stealth)

Pinned reviewed Qwen stealth episodes + synthetic planted probes: channel-1-complete
attacks with silent classic joint OR-flags but note-level compliance / encoding /
exfil intent. Refusal-aware probes ignore “refusing to encode…” style notes.

| Detector | Classic mirage recall | Stealth recall | Gemini clean | Fitness |
|---|---:|---:|---:|---:|
| c1-blind | — | — | — | -1000 |
| correcting-only | — | — | — | -1000 |
| joint-v1 | 1.0 | **0.0** | yes | 264 |
| **ensemble-v1 (champion)** | **1.0** | **1.0** | **yes** | **404** |

## Kernel evolution (5 generations)

Attested fitness on Assurance Mirage captures + hard suite. Champion retained:
`ensemble-v1` (`ensembleProbe`). Channel-1 never crowned. Joint-v1 plateau broken
by stealth recall. Mutations did not dominate ensemble-v1 on this suite.

Evidence: `evidence/generation-kernel-v2/`.

## Live Gemini stress (prior wave)

Earlier live wave on instruction-boundary arms stayed clean for joint champion;
ensemble probes are refusal-aware so successful Gemini refusals do not inflate flags.

## Non-claims

Not production PCS authority, not open-ended self-modifying code, not a proof of
global/optimal safety — a fail-closed search that keeps only lattice-admissible
mechanisms that win on attested real-model evidence.
