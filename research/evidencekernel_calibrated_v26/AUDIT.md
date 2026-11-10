# EvidenceKernel v26 — adversarial research audit

## Tested invariants

1. **Exact single-look coverage:** 16- and 20-draw binomial calibration experiments, multiple off-grid true probabilities and nominal risk budgets, all possible success counts.
2. **Optional-stop failure:** 16–48 calibration peeks at a true Bernoulli(1/2) produce exact undercoverage `17440361441103/281474976710656 > 1/20` when a fixed-sample 5% bound is reused.
3. **Corrected optional-stop coverage:** explicit error spending across registered looks, exact finite-DP tests over several true probabilities.
4. **Cross-language arithmetic:** independently written Python exact integer/Fraction and Node BigInt calibration formulas on 130 generated finite cases; comparison of complete synthetic v25 and v26 reports, including a registered optional-size run.
5. **Fail-closed capture:** altered original calibration bits/lengths, mismatched SHA-256 pins, wrong study propensity ceilings, modified study observations, duplicate JSON keys, unsupported contracts, vacuous ceilings under `require_nontrivial_ceiling` and altered state counts.
6. **Inherited inference:** v25 study executed by the existing Python verifier and independently by the existing Node.js implementation after calibration ceilings are bound. No production PCS authority paths changed.

## Known security and epistemic limitations

**External stationarity remains the TCB.** The method assumes a fixed per-state probability across the calibration and subsequent study, conditional on all relevant histories. A policy whose parameters drift, adapt within state, or depend on unobserved current-unit characteristics can invalidate coverage. This cannot be inferred from a source signature, timestamp assertion or SHA-256 digest.

**Attested records are not complete-history evidence by themselves.** SHA-256 detects alteration relative to a genuinely external trusted pin. It does not prove that unrecorded draws, deleted pilot studies, unobserved calibration visits or multiple unpublished registration attempts never occurred. Prospective independent custody is required.

**Calibration risk and measurement risk are different.** The 1% statewise propensity-calibration failure budget in the synthetic demo is derived mathematically, conditional on stationarity and recorded data. Its separate 1% measurement-calibration risk is merely an external assertion. The reported 7% aggregate bound is valid only if both physical premises actually hold.

**No formal kernel proof or real experiment.** Tests include finite-model exact enumeration; they do not prove arbitrary Python or JS program correctness or wet-lab effects. A negative result or calibration ceiling of 1 must not be hidden.

### Reproduction

Run from PCS repository root after merging the stacked research branches into a test checkout (not production):

```sh
python -m unittest discover -s research/evidencekernel_calibrated_v26 -p 'test_*.py' -v
D=research/evidencekernel_calibrated_v26
python -m research.evidencekernel_calibrated_v26.kernel \
  "$D/calibration_contract.json" "$D/calibration_records.json" \
  "$D/study_protocol.json" "$D/study_records.json" \
  --calibration-contract-pin "$(cat "$D/calibration_contract_pin.txt")" \
  --calibration-records-pin "$(cat "$D/calibration_records_pin.txt")" \
  --study-protocol-pin "$(cat "$D/study_protocol_pin.txt")" \
  --study-records-pin "$(cat "$D/study_records_pin.txt")"
```
