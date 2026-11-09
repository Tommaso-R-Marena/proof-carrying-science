# EvidenceKernel v25 — externally bounded propensity inference

**Experimental research only.** This standalone PCS overlay weakens v24's exact physical assignment-probability requirement to externally justified, time-predictable **upper bounds**, while preserving optional-stopping safety, bounded incorrect outcome intervals and finite-population target semantics. It adds a completely rational **sensitivity frontier** reporting how far those asserted bounds can rise before a strict scientific finding is lost. The implementation is not a PCS kernel theorem, a physically witnessed experiment, or a production authority.

## What was built

- An exact Python verifier in `kernel.py` and separately implemented JavaScript/BigInt auditor in `independent.js`; strict JSON decoding rejects duplicate keys and decimals.
- Preregistered `propensity_upper_by_state`, with strategy-specific `reference_weights_by_state` for `q`, allowing either conservative `q≥upper` (zero one-sided bias penalty) or smaller references with an explicit exact bias correction.
- A registered family of tuning strategies, independently verified non-floating-point exponential threshold certificates, and exact Bonferroni spending. A one-sided martingale bound applies **at all stopped times** without knowing the actual `p_i` precisely.
- Correction for up to `max_interval_misses` incorrect binary outcome intervals and conservative `-1` effects for every unobserved member of the pre-fixed ordered cohort.
- A computed exact-rational common-upper-slack supremum for all state ceilings, with a separate strict boundary inclusion flag.
- An explicit `90%` actual versus false `50%` nominal propensity attack, with a repaired *conditional* sensitivity result.

## How to reproduce

From PCS repository root (Python 3.12+ and Node.js 22+, standard library only):

```sh
python -m unittest discover -s research/evidencekernel_anytime_v24 -t . -v
python -m unittest discover -s research/evidencekernel_propensity_v25 -t . -v

DIR=research/evidencekernel_propensity_v25
P=$(cat "$DIR/example_protocol_pin.txt")
E=$(cat "$DIR/example_evidence_pin.txt")
python -m research.evidencekernel_propensity_v25.kernel \
  "$DIR/example_protocol.json" "$DIR/example_evidence.json" \
  --protocol-pin "$P" --evidence-pin "$E" > /tmp/v25-python.json
node "$DIR/independent.js" "$DIR/example_protocol.json" \
  "$DIR/example_evidence.json" "$P" "$E" > /tmp/v25-node.json
python - /tmp/v25-python.json /tmp/v25-node.json <<'PY'
import json,sys
with open(sys.argv[1]) as a, open(sys.argv[2]) as b:
    assert json.load(a) == json.load(b)
print('independent replay matched')
PY
```

`make_demo.py` deterministically reuses the earlier v24 **synthetic** 512-unit example and writes a new preregistration and report. These pins are stored beside their examples for reproducibility, not externally timestamped or witnessed.

## Measured software results (synthetic only)

| Checked property | Result |
| --- | --- |
| Fixed cohort size | 512 |
| Stopped enrolled prefix | 457 |
| V24 reference with assumed exact propensities | lower ATE `6009709/11796480` ≈ 0.50945 |
| V25 with allowed upper ceilings `[31/50,21/50,13/25]` | lower ATE `8515174471273905593/19000741375306629120` ≈ 0.44815 |
| Additional *simultaneous* ceiling slack preserving rejection, exact supremum | `8515174471273905593/69762177483835200000` ≈ 0.12206 |
| 64-unit all-null false-registration counterexample | ≈ 99.999988% nominal false-positive under invalid 1/2 claim; no rejection in this construction when registered ceiling 9/10 |

The real assignment probabilities in the synthetic generator lie below those asserted ceilings; this has **not** been established for any external experiment. For this example the exact strict rejection stops at the computed slack frontier; equality does not qualify as rejection.

## Trust boundary

The **true conditional probability** of treatment, including conditioning on the fixed potential outcomes and all prior reports, must not exceed the asserted state ceiling. External randomization operation, pre-outcome freezing of caps and reference strategies, the existence of the fixed cohort, no interference, sound measurement, and the claimed simultaneous calibration error budget all remain independently unverified. SHA-256 verification is not evidence of any of those premises.

In particular, an observed treatment fraction below the cap is not proof that each sequential conditional probability was below it. This is **not** observational-confounding correction and not an estimate of biological efficacy. It is a conditional sensitivity analysis for experiments with externally bounded treatment randomization probabilities. The code can identify forged or structurally inconsistent records, but not concealed enrollments, unrecorded randomness resets or false laboratory measurements.

Mathematical derivation: `MATHEMATICS.md`. Counterexamples and validation scope: `AUDIT.md`. The underlying probability results have prior art. Integration is isolated under `research/` with a path-scoped workflow, not a PCS production or Lean authority change.
