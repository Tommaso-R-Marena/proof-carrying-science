# PCS grounded Mathlib learning and sequential RL v4

The new policy learns from actual goal/context DAGs and actual elaborated premise signatures, without theorem-name embeddings. The fixed imported environment, typed receiver grammar and independently compiled original proposition decide proof validity. Nothing is promoted automatically.

## Executed training

`research/mathlib-training-v4-kernel-scope/` contains eight explicitly PCS-authored supervised Set/function and logic traces, 35 checked transitions, actual source-overlay hashes and license records. They use existing mathematical facts; they are not externally authored training problems. All labels were regenerated through actual Lean states and four separate kernel compilations per theorem. The pretraining recheck independently regenerated the complete observations/options/labels and all eight proofs: 32 standalone compiler invocations plus 43 structured worker requests, 141.563 seconds. The module/family and alpha-statement firewall against the external 22 final statements passed; proof dependencies/imported library facts are not disjoint.

Four 10,627-parameter models actually trained for 20 epochs each, seeds 71/79 × graph/bag. Each saves and reloads Adam state and Torch RNG at epoch 10 before continuing. Graph edge/message/update weights changed; the bag ablation leaves those allocated components unused. The parameter count is allocated parameters, not identical effective capacity. Model training/resumption wall times: graph 71 14.056s, bag 71 9.626s, graph 79 11.209s, bag 79 5.141s. Exact logs, epoch losses, changes and checkpoint digests are in `research/mathlib-learning-v4-kernel-checked/training-summary.json`.

The first provenance-shape failure and subsequent task-list firewall error are preserved in earlier collection generations. A development Group case exposed a false-negative comparison of generated binder names; the pre-gradient run was stopped and its source overlay preserved. Kernel types now compare binder/universe alpha structure while retaining constant names, domains, scope and axiom sets. An actual Group kernel control passes. Earlier unknown results are not overwritten.

## Executed sequential RL and failure recovery

The initial RL run lost its durable result when an additional cold replay timed out. Its trace is retained. The corrected version handles kernel/replay failure as a nonpositive terminal before updating, and saves model, Adam and RNG after every completed episode. This change used training/development failures, before any external final outcome.

`research/mathlib-rl-v4/` freezes the amended failure policy and records actual sequential actor–critic training on the eligible eight training tasks. Each of two seeds ran 8 episodes; each produced 6 verified and independently replayed terminals and 2 invalid terminals. Both saved model weights changed. Seed 71 used 24 standalone kernel invocations and 40 structured requests, 89.955s wall/78.885s child CPU; seed 79 used 24 and 2, 97.879s/89.147s. Seed 79 reused source-bound exact transition cache entries from seed 71; this is not a claim of reduced learning cost or improved policy. Per-episode checkpoints and complete trajectories preserve that distinction. Both seeds still require fresh kernel replay for terminal success.

## Evaluation firewall and results

The 22 externally sourced public Mathlib final statements and separate seven-import environment overlay were frozen before fitting. The final matrix runs all fixed symbolic/lexical/untrained/supervised graph/bag/RL seeds and strongest Std/Mathlib portfolio, with transition cache cleared for every method/task. No result selects a checkpoint. Outcome report: PCS_MATHLIB_GENERALIZATION_V4_REPORT.md. The completed 220-comparison matrix scores every primitive/supervised/RL method 0/22 versus the strong portfolio 9/22. No verified generalization, superiority or RL improvement is demonstrated, and no model is promoted.

## Scope and reproducibility

Use pinned Lean 4.28, Mathlib 8f9d9cff6bd728b17a24e163c9402775d9e6a365, Torch 2.7.1+cpu and source/model digests. Safe JSON tensors/optimizer states execute no pickle. Ordinary PR checks run pinned checkpoint inference and adversarial boundaries; heavy fitting/evaluation is separate. Reports distinguish structured requests, compiler invocations, replay, initialization and model inference. Per-segment costs are measured; earlier crashed prototype CPU costs are not fully accounted and are not treated as zero. Source overlays preserve old supervised code when subsequent RL failure handling changes its module bytes.

## Independent weight reproduction

Fresh retraining reproduced all 15 parameter tensors bit for bit for each of four supervised checkpoints, including actual Adam/RNG save and resume. Original checkpoint bytes remain unchanged. `research/mathlib-weight-reproduction-v4/summary.json` records outcomes and timings; `scripts/reproduce_mathlib_weights_v4.py` repeats the operation. This checks reproducibility from previously verified labels, not generalization. All model-registry entries remain experimental and carry the actual 0/22 result.
