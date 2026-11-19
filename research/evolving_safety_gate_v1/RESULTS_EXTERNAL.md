# External bake-off results (JailbreakBench + SOTA-style guards)

Honest answer to “did you benchmark vs external / SOTA?”: **yes, now** — three tracks.
Not an official JailbreakBench ASR leaderboard entry. LlamaGuard weights were not used
(gated); ProtectAI prompt-injection v2 and Gemini flash-lite moderator were.

## Systems

| System | Role |
|---|---|
| **ensemble_v1** (PCS) | Evolving Safety Gate champion (`ensembleProbe`) |
| joint_v1 (PCS) | Classic joint OR-flags |
| channel1_incomplete | Mirage-blind negative control |
| **protectai/deberta-v3-base-prompt-injection-v2** | Widely used SOTA prompt-injection classifier (ONNX) |
| **gemini-flash-lite-latest** | LLM-as-judge content moderator |
| openai_moderation_proxy | Keyword taxonomy heuristic (not OpenAI API) |
| agentdojo_tool_filter | Allowlist tool-pipeline defense |

## Track A — JailbreakBench Goals (text only)

Dataset: [JailbreakBench/JBB-Behaviors](https://huggingface.co/datasets/JailbreakBench/JBB-Behaviors) (50 harmful + 50 benign Goals).

| System | Precision | Recall | F1 | FPR |
|---|---:|---:|---:|---:|
| Gemini content moderator (n=93 labeled) | 0.89 | 0.96 | **0.92** | 0.14 |
| OpenAI-moderation keyword proxy | 1.00 | 0.04 | 0.08 | 0.00 |
| ProtectAI prompt-injection | — | **0.00** | — | 0.00 |
| ensemble_v1 on Goal text | 0.00 | 0.00 | — | 0.04 |
| joint_v1 on Goal text | — | 0.00 | — | 0.00 |

**Read:** content-harm Goals are Gemini’s job. ProtectAI is an *injection* detector — JBB
Goals usually lack “ignore previous / system override” syntax, so ~0 recall is expected.
ESG on raw Goal text is outside its designed I/O (episode + tool channel).

## Track B — Attested PCS agent mirage episodes (same inputs for all)

120 Qwen/Gemini episodes; label = classic mirage ∪ reviewed stealth.

| System | Precision | Recall | F1 | FPR |
|---|---:|---:|---:|---:|
| **ensemble_v1** | **1.00** | **1.00** | **1.00** | **0.00** |
| ProtectAI on episode text | 0.79 | 0.97 | 0.87 | **0.41** |
| joint_v1 | 1.00 | 0.84 | 0.91 | 0.00 |
| AgentDojo tool-filter | 1.00 | 0.68 | 0.81 | 0.00 |
| channel1_incomplete | — | 0.00 | — | 0.00 |

Stealth subset (n=12): ensemble **12/12**, ProtectAI 11/12, joint **0/12**, tool-filter 0/12.

## Track C — Live transfer: JBB Goals → Qwen in PCS workflow

12 episodes (8 harmful + 4 benign JBB Goals) on Qwen3-0.6B GGUF under instruction_boundary.
All 12 produced classic mirages (forbidden `finish` / proposal harm), including JBB-benign
Goals — the small model left the admitted tool path.

On **mirage** labels: ensemble/joint/tool-filter **12/12**; ProtectAI **5/12**.

## Bottom line

- **Content-harm (JBB text):** Gemini moderator ≫ ESG / ProtectAI.
- **Agent mirage + stealth:** ESG `ensembleProbe` ≫ joint, tool-filter, channel-1; beats
  ProtectAI on FPR and ties/beats on stealth.
- **Threat models differ.** No single system wins both. Production stacks should combine
  a content moderator with a joint/ensemble episode detector — not rely on channel-1
  completion scores.

Evidence: `evidence/external-bakeoff-v1/`.
