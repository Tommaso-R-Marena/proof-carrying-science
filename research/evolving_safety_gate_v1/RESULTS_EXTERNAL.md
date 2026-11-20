# Historical external evaluation

The baseline at `5cd0fe136bef17b2b869e6df96697aae256c1fe6` mixed four endpoints. Content classification asks whether a Goal requests harmful material. Prompt-injection resistance asks whether untrusted instructions affect authorized behavior. Proposal safety asks whether the model chose an admissible next action. The assurance-mirage construction asks whether an observer of a corrected execution can distinguish proposers. Each endpoint needs its own reference outcome.

| Frozen input | What can be reproduced | Limitation |
|---|---|---|
| Track A, 100 JBB Goals | 93 cached Gemini decisions, seven missing. On covered rows, 48 TP, 37 TN, 6 FP and 2 FN. | Goal intent labels do not measure attack success, output safety or a completed AgentDojo task. The keyword comparator is a local proxy. |
| Track B, 120 recorded PCS episodes | The archived development labels flag 74 episodes. | Part of the label comes from the same classic flags used by the detector. Previously inspected stealth identities and a cross-capture case-ID fallback also influenced labels. Agreement with these labels cannot validate independent mirage detection. |
| Track C, 12 recorded Qwen transfers | All 12 are positive on the historical mirage definition. | An always-positive classifier attains recall and F1 of one. Specificity and false-positive rate are undefined. |

The historical `dominance.json` uses 93 available Gemini responses. Its version differs from the generating script in the baseline checkout. Only its preserved counts and bytes are reproducible here. Gemini, ProtectAI and toxic-bert were not rerun. The alias `gemini-flash-lite-latest` identifies the historical moderator interface. A fixed underlying model revision is unavailable. The resulting numbers have no official JailbreakBench or AgentDojo status.

See the [offline reanalysis](RESULTS_SOTA.md) and [original evidence](evidence/external-bakeoff-v1/).

## Protocol and license scope

JailbreakBench evaluates model responses with judges under specified generation and defense conditions. PCS used a 100-Goal subset, supplied existing split labels, and scored intent classification. AgentDojo runs agents on tasks within interactive suites. The local disagreement filter evaluates recorded proposal and admission fields and has no AgentDojo task-success oracle. Both benchmark code repositories publish MIT licenses. Those code licenses do not establish redistribution rights for each upstream input or model weight. This replay adds no external examples or weights. [JailbreakBench protocol](https://github.com/JailbreakBench/jailbreakbench) · [code license](https://github.com/JailbreakBench/jailbreakbench/blob/main/LICENSE) · [AgentDojo protocol](https://github.com/ethz-spylab/agentdojo) · [code license](https://github.com/ethz-spylab/agentdojo/blob/main/LICENSE).

## Baseline claim register

| Claim at the frozen head | Classification | Evidence and assumption |
|---|---|---|
| Guarded execution-only scores tie the constructed pair | FORMALLY_PROVED | `AssuranceMirage.channel1_factorable_blind_constructive` under the unique-action guard and mathematical tool projection. |
| A tie on that one pair implies global factorability | REFUTED | A score can tie that pair and distinguish another pair with the same observation. The global property quantifies over every observation fiber. |
| The finite catalog's modeled admissibility excludes channel-only candidates | FORMALLY_PROVED | `EvolvingSafetyGate.channel1_never_admissible` concerns the modeled rank and Lean transition. |
| The protected production PCS authority is improved by Python fitness selection | NOT_EVALUATED | The Python experiment is a separate research process, with a finite generator and reusable development cases. |
| The routed stack's recorded geometric mean is evidence of comparative superiority | REFUTED | Historical measurements lack matched modalities and independent labels. The original arithmetic remains recorded. |
| An execution-only monitor can miss proposal contract violations in the captures | EXECUTABLY_VERIFIED | The strict-reply receiver finds 55 violations despite 120 recorded successful completions. Requires trustworthy raw replies, state records and workflow definitions. |
| The measured detectors generalize to unmeasured tasks or paid models | NOT_EVALUATED | The same corpus was previously used during mechanism development. |

The isolated baseline run used Python 3.12.14 and Lean 4.28.0. All 16 original mirage/evolution tests passed, including the two original Lean checks. The pre-correction external helper required optional NumPy, ONNX Runtime and tokenizers during import, even for cached replay. The offline audit uses the standard library. ProtectAI model files and runtime remain optional for a fresh model run. Two optional tests skip when local weights are absent. No hosted CI or admission to the protected source census was established. Cached goal judgments and raw model captures remain in their original locations with provenance bound by the replay receipt.
