# Synthetic PK/PD translation benchmark

This workspace is a **synthetic methods benchmark**, not a clinical study and not evidence for treatment efficacy or safety.

The declared computational model is a one-compartment IV-bolus PK model with a direct Emax PD layer:

- C(t) = (Dose / V) * exp(-(CL / V) * t)
- E(C) = E0 + Emax * C / (EC50 + C)

The project contains both a model-generated prediction table and a noisy synthetic observation table. Both tables intentionally expose the columns `time`, `concentration`, and `effect`. This makes file role assignment ambiguous to a simple deterministic column detector and tests whether a grounded proposer can select the intended prediction artifact without gaining proof authority.

The benchmark distinguishes four scientific statements:

1. The declared PK/PD model satisfies the restricted PCS positivity and dimensional contract.
2. The prediction table reproduces the declared analytic equations within the committed numeric tolerance.
3. The restricted model adequately describes the synthetic observations.
4. The peak predicted concentration does not exceed 12 mg/L.

PCS already has theorem-backed checkers for (1) and (2). Statement (3) intentionally requires an external empirical/statistical validation policy. Statement (4) is computationally concrete but intentionally has no certified PCS checker in this benchmark version.

A correct PCS result therefore **must not** turn all four statements green. Success means proving the narrow computational claims while exposing the empirical and unsupported-checker boundaries explicitly.
