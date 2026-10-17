# Bugs and ambiguities — Workstream B

Observed during independent scientific falsification evaluation. These are **evaluation findings**, not production patches.

## Ambiguities

1. **Classic `pcs certify` vs v0.6 check surface**  
   Case `02_pkpd_with_peak_threshold_note` documents `pkpd_peak_concentration_threshold` as a v0.6-certified check that the classic certify kernel does not execute. Scientific users may confuse “declared in docs” with “executed by `pcs certify`.”

2. **Discovery ground truth is synthetic**  
   Precision/recall in `discovery_benchmark/` measure agreement with evaluator-authored labels on synthetic projects, not with human scientific intent.

3. **Inadequacy examples still use PCS-supported checks**  
   “Scientifically inadequate” models that still satisfy `pkpd_contract` positivity constraints are intentionally extreme but still mathematically well-formed. PCS correctly verifies the declared computational claim; empirical inadequacy is out of band by design.

## Observed behaviors (not claimed defects)

1. **Tampered prediction tables** produce certificates where at least one claim is not `COMPUTATIONALLY_SUPPORTED` (expected rejection path).
2. **Post-certify artifact byte tamper** causes `pcs verify` to fail (expected).
3. **Blank external-validity templates** score as incomplete on empty population/endpoint fields; `empirical_adequacy_established` is always `false` in the scorer.

## Non-findings

- No production `pcs/` or `formal/` code was modified to accommodate this harness.
- No human participant results were invented for external validity.
