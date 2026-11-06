# Executed Safety-JEPA research

The predictive system is functional, but **it did not beat the strongest symbolic
policy in this bounded environment**. It can reduce wasted guarded attempts on
hostile proposal streams. Ordinary RL, transfer and proof-guided updates often
hurt useful completion. An actual small-Qwen pilot completed no tasks.

This is stacked research in PR200, based on unmerged PR199 at0b95715. Prompt1's
source and evaluation are preserved. Production authority, root formal sources,
protected main and the frozen source-census contracts are unchanged.

## Architecture and executed protocol

`model.py` reuses the actual Proof-JEPA trainable ordered graph encoder and,
for transfer arms, its exact trained encoder checkpoint. Same-seed nonencoder
initialization is matched. The new model has23,573 trainable parameters plus
frozen EMA targets, action-conditioned latent successor prediction, latent-only
four-step risk forecasting, policy/value/reward/rejection heads and covariance
regularization. Hash collisions and bounded text/history remain limitations.

The frozen primary code is **f92f64c**; all14 recorded source hashes match that
commit. Later controllerV2, receivers and UI additions do not replace the original
training or test results. CPU PyTorch2.7.1, Python3.12 and Lean4.28.0 were used;
no GPU or hosted-model API was used. Eighteen real models were trained: six
configurations × seeds17/31/47, common120 expert-cloning updates, six epochs
of12 mixed updates, and48 real on-policy episodes in each RL arm. Warmup cost
202.87s total; RL cost65.26s, with setup/evaluation additional.

Forty training scenarios produced768 initial measured transitions over160
executions. Labels came from actual confined unguarded consequences or admitted
safe workflows, not model predictions. RL interleaves predictive/EMA updates;
only admitted guarded transitions enter the safe predictive buffer. The
proof-guided arm separately executes rejected proposals after their admitted
prefix, records the actual unguarded counterexample and uses it in learning.
Its three runs sampled51/43/57 live feedback records in updates. These151 uses
are not151 distinct attacks. Rejected actions are never positive imitation labels.

Corpus:40 train,12 validation,24 test and24 OOD scenarios from40 named templates.
Template/document identity is split-disjoint. Semantic threats and primitive
plans recur; this is lexical/template transfer, not unseen tool/policy semantics.
There are only two legitimate workflows and15 permitted proposal names.
AgentDojo influences are source-pinned and licensed, but these are PCS-authored
synthetic tasks, not the official AgentDojo suite or attack-success score.

All policies have8 actual tool-step slots, including the host's initial inspection.
Forecasters receive the explicit next-four-action proposal queue. They do not
infer hidden intentions. A strong goal-aware safe planner and exact finite-model
queued-plan checker have the same information available. Validation alone selects
thresholds and checkpoints before test execution. Guard policy never changes.

## Actual held-out execution

Each row below covers48 test/OOD cases per seed. Unsafe episodes mean at least
one policy-violating executed effect. Raw event counts can repeat after a first
breach; actual synthetic marker leaks are separately measured.

| Configuration | Completed cases, seeds17/31/47 | Denied proposals, seeds17/31/47 | Unsafe episodes |
|---|---:|---:|---:|
| Scripted proposals, unguarded |16 |0 |32 |
| Same proposal stream, guard only |46 |46 |0 |
| Strong deterministic safe planner + guard |48 |0 |0 |
| Exact symbolic queue forecast + guard |48 |0 |0 |
| Supervised risk guidance + guard |48 /48 /48 |12 /16 /28 |0 each |
| JEPA forecast guidance + guard |48 /48 /48 |6 /6 /8 |0 each |
| Ordinary RL + guard |24 /15 /0 |0 /176 /24 |0 each |
| JEPA + interleaved RL + guard |48 /46 /46 |2 /8 /6 |0 each |
| Transferred encoder + JEPA/RL + guard |48 /0 /28 |8 /6 /6 |0 each |
| Transferred proof-guided JEPA/RL + guard |48 /0 /0 |8 /6 /0 |0 each |
| Validation-selected JEPA predictor without guard |42 |0 |6 |

The unguarded scripted control leaked synthetic markers in20/48 episodes.
The learned predictor without a guard had6 unsafe episodes despite no observed
marker leak. **Prediction is not an authorization boundary.** Every guarded
configuration had zero observed unsafe executions and marker leaks; that result
belongs to independent enforcement, not neural correctness.

Validation selected `jepa_rl-17`:48/48 completions,2 denials,262 tool steps,
versus guard-only46/48,46 denials,310 steps. That is48 fewer tool operations
(15.5%) in this run, but **not lower end-to-end CPU cost**. The strong deterministic
planner completed48/48 in260 steps and0.432s. Mean JEPA/RL evaluation cost1.664s,
with1.144s inference, versus guard-only0.543s. More expensive real tools could
change that tradeoff, but that hypothesis was not tested.

The configurations compare complete systems. Supervised guidance scores a current
action; JEPA guidance scores a known queue. Their difference does not isolate the
JEPA loss alone. Transfer/no-transfer JEPA/RL arms isolate encoder initialization;
proof-guidance adds several losses and live feedback as a combined treatment.
The small public corpus and three seeds do not establish general superiority.

## Anticipation and failure analysis

For `jepa-17`, immediate unsafe-effect prediction had TP50/FN34/FP11/TN171.
The distinct target, any unsafe event in a known four-action window, had
TP150/FN18/FP3/TN95. Those targets and denominators differ. Post-breach observations
are included in these event-level matrices; they are not independent attacks.

All32 dangerous scripted plans received at least one correct forecast2–3 actions
before their first unsafe effect, mean2.5. This is prospective prediction given
an explicit action queue. Exact symbolic lookahead can also anticipate these
finite-model violations, without a learned predictor or false alarms.

Raw `interventions` fields count risk-threshold alarms, even when the chosen repair
matches the proposal; planner action changes are not counted there. They are not
comparable counts of human interventions. Benign alarm counts for JEPA seeds were
1/6/7; supervised seeds0/30/0. False positives and model overhead remain explicit.

RL often failed to discover complete trajectories. Proof-guided runs had only
0/1/0 successful on-policy training episodes despite actual counterexample updates.
Review/abstention and incomplete trajectories can be attractive under sparse
completion rewards. Finite safety guarantees do not imply useful performance.
Transfer from elementary mathematics did not reliably help this domain. Nonconstant
representations and lower losses do not establish semantic adequacy; finite
training-state covariance diagnostics are retained separately.

## Actual Qwen weights

Six cases were fixed before generation: three test and three OOD, balanced by
public/sensitive goal and including legitimate controls. The actual pinned
Qwen3-0.6B Q8_0 weights,639,446,688 bytes, were consumed through the existing sealed
weight snapshot and reviewed llama.cpp b11827 runtime. Only the22MB runtime archive
was newly downloaded; no weights or runtime binaries are committed.

**30 actual requests,0/6 completed tasks,0 guarded unsafe effects,0 raw-text private
marker exposures**, in51.67s. The model repeatedly proposed wrong-phase actions
such as drafting before reading. Replaying the same captured plans without guards
produced18 unauthorized-state events across five cases, not18 independent attacks.
These were not successful real-secret exfiltrations. Learned-review controls also
completed0/6 tasks. No improvement on real-model competence or safety was shown.

Independent receiving checks bound all30 raw requests/responses to their exact
observations, weight/runtime hashes and parsed actions, then re-executed96 tool
actions. This does not attest neural origin to an external observer. Controls reuse
the captured plan; they are not resampled interactive responses to different feedback.
This is a small0.6B pilot, not a frontier/SOTA claim or full AgentDojo evaluation.

## Adaptive attacks and promotion

A separate16-round authored adaptive campaign used actual prior guard rejection
feedback in15 rounds. Unguarded execution had16 unsafe episodes and11 marker leaks;
guard-only and the selected learned controller each completed16/16 with no observed
unsafe effect or leak. Six finite strategies do not establish general adaptive
robustness. None of those evaluation outcomes entered training.

The research controllerV2 now requires fresh actual Lean replay of BOTH fixed goal
policies at initialization and every candidate update. Missing/rejected Lean cannot
advance HEAD. It also internally evaluates16 fixed development cases, preserves
all incumbent-success IDs, checks source/policy/artifact identities and budgets,
and requires non-vacuous improvement. Callers provide no metrics or verifier.

An actual trained `rl-17` direct-actor checkpoint improved the nonfunctional zero
incumbent from **0/16 to12/16** development completions; independent reevaluation
matched. Stale generation, lost functionality and forged authority were rejected.
Receipt chains, generation CAS, exact-byte loading and pre/post tensor fingerprints
protect against tested accidental corruption and stale use. This direct-actor gate
is a separate development controller, not the planner-enabled primary benchmark.

These are finite empirical functionality checks under a separately kernel-checked
unchanged guard. They do not prove universal neural safety. The historicalV1 finite
promotion demonstration remains retained, explicitly distinguished fromV2's fresh
kernel requirement. No integer-network PGSC6 certificate was repurposed to certify
arbitrary Safety-JEPA weights. Cooperative locks and hashes do not create hostile
writer isolation or an external rollback anchor.

## Formal results, tests and independent evidence

Six new research-only Lean theorems compiled and were axiom-audited:
`PCSSafetyJEPA.rejected_unchanged`, `model_cannot_authorize`,
`model_updates_preserve_policy`, `permitted_step_preserves`,
`arbitrary_proposals_preserve`, `all_rejected_unchanged`.
They establish abstract rejection/model separation and conditional invariant
preservation. Two require no axioms; other audits use only `propext`.
Existing PCS additionally kernel-checked both150-edge finite policies and arbitrary
finite admitted histories, using only standard `propext`/`Quot.sound`.

Concrete Python/filesystem refinement, authentic observation, model completeness
and trusted host/runtime behavior remain OPEN. Tests include180 actual active
state/action conformance cases, not a proof of all concrete implementations.
No network request or OS command is exposed by the tool executor. Unauthorized
command/send actions in the unguarded control are confined local mock effects.

Local qualification:92 full-suite tests passed, plus the two subsequently added
artifact-integrity tests (the eight focused verifier/demo/replay checks passed).
The inherited Proof-JEPA foundation26 checks and direct axiom-free demo also passed.
An initial test correctly failed because Lean PATH was missing; activation repaired
the environment, not the assertion. Early unsafe-mode measurement and sparse-return
feedback bugs were fixed before the primary run; audit findings are not hidden.

Independent receivers re-executed the initial training, on-policy trajectories,
live counterexamples and held-out effects, plus the real-model capture. Exact
counts and matched-status receipts are retained in `effects-replay.json` and
`pilot-replay.json`. The dedicated stacked CI runs the full current tests, fresh
Lean checks, bounded real training and effect replay; final run status is recorded
on PR200. Main's frozen census and PR199's integration dependency remain unchanged.

See README for reproduction and MODEL_CARD for intended use and provenance.
The next justified milestone is richer changing tool semantics, better task agents,
separately isolated reward/planning objectives and another untouched test set.
These data support independent enforcement and reproducible falsification; they
do not establish alignment, deception detection or a general AI-safety breakthrough.
