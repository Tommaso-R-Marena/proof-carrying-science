# EvidenceKernel v26 — exact pretrial calibration feeding anytime scientific inference

**Research draft; not a PCS production verifier or a claim of a major new probability theorem.** This module composes a statewise exact binomial calibration certificate with EvidenceKernel v25's anytime lower bound for a fixed ordered cohort.

## Main advance

V25 accepted probability ceilings asserted by the experimental operator. V26 derives those ceilings from a separately pinned, preregistered prestudy assignment sample. The verifier computes exact one-sided binomial tails, chooses the smallest valid grid ceiling, checks the entire original study's pinned input, and requires each v25 ceiling to agree **exactly** with the derived value. Any mismatch is rejected.

A second extension handles **optional stopping during calibration**. The registration must either fix the sample count per state, or specify a prospective lower/upper sample-count range. The latter mode divides each state's calibration error budget across every permitted check, so selecting a favorable-looking calibration sample length cannot silently invalidate coverage. See [the exact counterexample and proof argument](MATHEMATICS.md).

## Current synthetic results

Three separate synthetic calibration streams (512 assignments each; 1,536 calibration draws overall) give exact statewise propensity ceilings:

```
state 0: 167/250 = 0.668
state 1: 481/1000 = 0.481
state 2: 267/500 = 0.534
```

A 512-unit registered-cohort study terminates after 457 observed units. The resulting v25 anytime ATE lower bound is the exact rational:

```
5682515118032078393 / 19000741375306629120 ≈ 0.29906
```

The experiment data are deliberately synthetic and should not be used to claim a real positive treatment effect. The fully composed **conditional** error budget is `α + δ_measure + β_propensity = 1/20 + 1/100 + 1/100 = 7/100`.

`δ_measure` is an unverified external premise; `β_propensity` comes from exact binomial tail inversion under a **strong, also externally unverified, stationary per-state conditional Bernoulli assumption**. The SHA pins alone do not attest chronology, complete logs, independence or physical experimental design.

## Layout

- `kernel.py`: independently auditable Python exact calibration, pin checks and v25 receiving gate.
- `independent.js`: separate Node BigInt calibration implementation and calls to independent v25 JS receiver.
- `make_demo.py`, `calibration_*`, `study_*`, `example_report.json`: full synthetic reproducer.
- `test_kernel.py`, `test_differential.py`: exact coverage and optional-stop counterexamples, adversarial checks and cross-language agreement.
- `MATHEMATICS.md`, `AUDIT.md`: premises, theorem argument, falsification and limitations.
- The path-scoped GitHub workflow is `.github/workflows/pcs-evidencekernel-calibrated-v26.yml`.

## Run

Python 3.12+ and Node 20+ standard libraries; code depends on earlier v25 research module on this **stacked** branch. From PCS repository root:

```sh
python -m unittest discover -s research/evidencekernel_calibrated_v26 -p 'test_*.py' -v
D=research/evidencekernel_calibrated_v26
CP="$(cat "$D/calibration_contract_pin.txt")"
RP="$(cat "$D/calibration_records_pin.txt")"
SP="$(cat "$D/study_protocol_pin.txt")"
EP="$(cat "$D/study_records_pin.txt")"
python -m research.evidencekernel_calibrated_v26.kernel \
    "$D/calibration_contract.json" "$D/calibration_records.json" \
    "$D/study_protocol.json" "$D/study_records.json" \
    --calibration-contract-pin "$CP" --calibration-records-pin "$RP" \
    --study-protocol-pin "$SP" --study-records-pin "$EP" > /tmp/v26-python.json
node "$D/independent.js" \
    "$D/calibration_contract.json" "$D/calibration_records.json" \
    "$D/study_protocol.json" "$D/study_records.json" \
    "$CP" "$RP" "$SP" "$EP" > /tmp/v26-node.json
python - <<'PY'
import json
assert json.load(open('/tmp/v26-python.json')) == json.load(open('/tmp/v26-node.json'))
print('Independent exact reports match')
PY
```

To regenerate **synthetic** examples:

```sh
python -m research.evidencekernel_calibrated_v26.make_demo
```

## Trust and integration

Only isolated research paths are added; no Lean proof, production verifier, scientific receiver, deployment, or protected authority boundary changes. No private key is packaged. The PR must remain draft until independent reviewers establish data custody and prospective registered assignment conditions in a genuine experiment. For a change of statewise treatment probabilities during the study, this calibration transfer is invalid; v25's upper-bounds **must not** be regarded as proven by this module in that case.
