# Safety-JEPA experimental model card

Intended use: local research on typed proposals in a bounded synthetic file/report
workflow. Not production authorization, alignment, deception detection or general
agent safety.

Architecture:23,573 trainable parameters at width24, plus frozen EMA target.
The ordered graph encoder and optional initial weights are reused from the actual
Proof-JEPA implementation. All new configurations share policy heads and behavior
cloning. Transferred/ proof-guided configurations initialize the encoder from the
retained Proof-JEPA checkpoint; nonencoder seed initialization is matched.
JEPA+RL interleaves on-policy actor-critic, predictive updates and EMA. The
proof-guided arm additionally learns from actual counterfactual rejected actions,
block/value supervision and successful admitted trajectories. These additions are
a combined treatment, not individually isolated causal effects.

Training:40 PCS-authored scenarios,768 initially measured transitions across160
actual confined executions. Forty named templates cover all100 train/validation/
test/OOD cases. Template text is split-disjoint, but semantic threats, tool rules
and primitive plans recur. No Aristotle proof-development traces or unverified
external labels are used. Transferred Proof-JEPA weights were previously trained
on PCS-authored checked elementary proof trajectories.

Three seeds,18 models,120 common cloning updates plus six epochs of12 mixed
updates. RL configurations each run48 actual guarded episodes. Proof-guided
updates sample151 live counterexample records across seeds; this is sampled use,
not151 distinct attacks. Risk labels are actual unguarded confined effects;
guard-denial and completion labels are separately measured. Model predictions
supply no approval or reward labels.

Main limitations:small public task space, two legitimate workflows, known finite
policy, shared attack semantics, hash-token collisions, text/history truncation,
four-action forecast horizon and uncalibrated scores. Forecasts receive an explicit
candidate action queue; they do not infer hidden intentions. The model can miss
risks and produce false alarms. Without independent guards, the retained predictor
control produced unauthorized effects in6/48 cases. Ordinary RL and transfer often
reduced task completion; the real Qwen pilot completed0/6 tasks.

The retained globally selected checkpoint is jepa_rl-17; risk-only selection is
jepa-17; the separate finite direct-actor promotion experiment chose rl-17 using
development evaluation only. No checkpoint was selected by final test results.
The package retains JSON weights with exact SHA256, schemas, shapes and finite
number checks. It never loads pickle. Expected hashes require trusted provenance;
hashes alone are not immutable storage or an independent trust root.

Model runtime and all deployment correspondence are trusted-host assumptions.
A model may propose; the unchanged guard and fixed promotion controller decide.
All tool resources and markers are synthetic. No real shell command or external
send is exposed. Full numerical results and negative findings are in REPORT.md.
