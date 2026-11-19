# Evolving Safety Gate v1 — observed results

## Formal

Twelve theorems in `EvolvingSafetyGate` (Lean 4.28.0, `leanchecker --fresh`).
Channel-1-only and correcting-guard-only mechanisms are never admissible.
Joint-channel / joint-detecting-guard classes are admissible. Retention requires
formal domination on detectability rank; retained champions stay admissible.

## Offline evolution (4 generations)

Attested fitness on Assurance Mirage captures (Qwen scientific + transfer + Gemini).

| Candidate | Formal admissible | Mirage recall | Pure benign FPR | Fitness |
|---|---|---:|---:|---:|
| c1-blind | no | 0 | 0 | -1000 |
| correcting-only | no | 0 | 0 | -1000 |
| **joint-v1 (champion)** | **yes** | **1.0** | **0** | **264** |

Mutations (leak-priority, corrupt-aware, strict-threshold, …) did not dominate
joint-v1 on this finite suite. The gate correctly refused to crown channel-1.

Champion also caught 3 benign competence failures on the transfer program
(wrong actions under benign prompts) without pure false alarms.

## Live Gemini stress

Champion re-tested on `direct-exfil`, `many-shot-jailbreak`, `policy-puppetry`
(instruction_boundary, 12 requests): **0 mirages, 0 champion flags**.

## Non-claims

Not production PCS authority, not open-ended self-modifying code, not a proof of
global/optimal safety — a fail-closed search that keeps only lattice-admissible
mechanisms that win on attested real-model evidence.
