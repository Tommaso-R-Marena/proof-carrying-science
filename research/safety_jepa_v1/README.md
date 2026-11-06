# Safety-JEPA research

This experiment runs an agent that reads synthetic files, prepares a report and
publishes it. A learned model predicts the consequences of proposed actions.
A separate PCS guard decides what can execute. A model prediction never grants
permission.

The experiment is functional, but **learning did not beat the strongest
symbolic baseline**. The selected controller completed48/48 held-out workflows,
with2 denied proposals instead of46 for the hostile-stream guard baseline.
A deterministic safe planner also completed48/48, with no denials and less CPU
work. The actual small-Qwen pilot completed0/6 tasks. See REPORT.md for failures.

## Run a short demonstration

From the repository root, activate the existing Python3.12 CPU environment and
Lean4.28.0. The inherited hashed environment is unchanged:

```bash
python -m pip install --require-hashes -r requirements-build.lock -r requirements-dev.lock -r requirements-prover.lock
python -m pip install --no-deps --no-build-isolation -e .
source scripts/activate_lean_428.sh
python -m research.safety_jepa_v1.demo --output /tmp/safety-demo
```

The demo uses real files inside a new disposable directory. Private markers are
synthetic; external sends and command execution are local mocks. It prints what
completed and which proposed actions were refused. It never operates on your
actual documents, email or accounts. Choose a new output directory each time.

Run the retained learned controller:

```bash
python -m research.safety_jepa_v1.demo --policy jepa_rl \
  --checkpoint research/safety_jepa_v1/evidence/jepa_rl-17.json \
  --sha256 61611bd810b746c03695c1cee70e809b90d30d6735294c72cecae19d8974e07a \
  --output /tmp/safety-neural-demo
```

Use `--policy deterministic` for the strong safe-planner baseline. All demo
policies pass the same guard. There is no production deployment command.

## Train and reproduce

```bash
python -m pytest -q research/safety_jepa_v1
python -m research.safety_jepa_v1 --output /tmp/new-safety-run \
  --seeds 17 31 47 --epochs 6 --rl-episodes 48
python -m research.safety_jepa_v1.replay --directory /tmp/new-safety-run
python -m research.safety_jepa_v1.diagnostics adaptive \
  --run-directory /tmp/new-safety-run --output /tmp/new-adaptive.json.gz
python -m research.safety_jepa_v1.diagnostics promotion \
  --run-directory /tmp/new-safety-run --output /tmp/new-promotion
```

A bounded CPU run uses `--seeds 17 --epochs 1 --rl-episodes 4`. No GPU was used;
the CLI currently supports CPU training. Full runs retain every comparison
checkpoint locally. The review bundle keeps only three selected checkpoints.
Promotion diagnostics require the full regenerated run directory because they
compare every candidate under their fixed development gate.

## Independently inspect retained evidence

```bash
python -m research.safety_jepa_v1.verify \
  --directory research/safety_jepa_v1/evidence
python -m research.safety_jepa_v1.replay \
  --directory research/safety_jepa_v1/evidence
python -m research.safety_jepa_v1.pilot_replay \
  --directory research/safety_jepa_v1/evidence/real-qwen-pilot
lean research/safety_jepa_v1/formal/SafetyBoundary.lean
```

Effect replay rebuilds fresh directories and checks action admission, protected
file hashes, actual effects and task outcomes, including initial training,
on-policy episodes, live counterexamples and held-out execution. It does not
attest that neural computation originally generated the recorded proposals.
Fresh temporary-directory paths in exception strings are location metadata;
exception, errno, fixed filename and all protected-file identities still match.

The Qwen receiver verifies30 raw request/response bindings and replays96 tool
actions without downloading weights or running a model. To generate new samples,
use `real_model.py prepare` for the exact existing resource pins and `real_model.py
run --cases ...`; generation is optional, bounded to32 calls, CPU-only and uses
about640MB weights plus native-engine memory. The retained pilot used six
predeclared cases, five model calls each. Controls replay those same captured
plans; they are not independently sampled interactive model trajectories.

## Implementation and trust boundaries

- `environment.py`:15 typed actions, actual confined filesystem effects, immutable
  verified output-byte snapshots, generation/digest checks, environment-owned
  rewards and existing PCS finite admission. Two goal-specific150-edge models.
- `model.py`:reused trainable Proof-JEPA graph encoder, optional exact trained
  encoder transfer, EMA targets, action-conditioned successor prediction,
  latent-only four-step forecasts, policy/value/reward/rejection heads.
- `experiment.py`:six configurations, common actual-expert cloning, supervised
  prediction and genuine on-policy actor-critic interleaved with predictive
  updates. Proof guidance learns from separately executed rejected-action
  counterfactuals. No evaluation feedback enters gradient training.
- `promotion.py`:research-only controllerV2 with fresh actual Lean qualification
  at initialization and every update, finite utility/regression testing, exact
  artifact/source/policy bindings, generation CAS and receipt chains. Snapshot
  inference checks tensor identity before and after use without reopening paths.
- `replay.py`, `pilot_replay.py`, `verify.py`:independent execution and capture
  integrity checks; hashes are not signatures, external custody or proof of origin.

The promotion gate preserves every incumbent success on16 development cases,
requires non-vacuous improvement and rejects lost functionality, stale generations,
forged authority, missing Lean and corrupted history. It certifies neither universal
neural safety nor generalization. Replacing an entire coherent store cannot be
detected without an independent anchor. Locks and Python objects are not immutable
security boundaries.

The six Lean theorems establish abstract rejection, model/authority separation and
conditional invariant preservation. Existing PCS proves all finite admitted modeled
histories safe. Python/filesystem correspondence, authentic observation, complete
modeling and an uncompromised host remain OPEN premises.

This branch is stacked on **draft PR199**, exact parent0b95715. Prompt1, production
code, root formal libraries and frozen source-census gates remain unchanged. Neither
PR should merge without separate review of the integration/source contract.
