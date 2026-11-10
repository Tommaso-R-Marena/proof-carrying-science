# EvidenceKernel v24 — adversarial audit

**Status:** bounded, research-only Python/Node.js inference; no externally
witnessed physical randomization, independent source custody, clinical trial,
Lean proof, or novel probability theorem.

## The biggest correctness gain

V23 can only enumerate the possible worlds of a small stopped response-adaptive
experiment. V24 uses a conditional martingale argument that does not require
models for counterfactual *reports*. Reports may be noisy or stochastic; the
registered treatment probability need only be predictable from the observed
past and correct for the real physical allocation process. The certificate is
linear in enrolled cohort size plus a `K`-largest-cost sort, rather than
exponential in potential outcomes and reporting schedules.

The 512-unit SYNTHETIC early-stopped example yields a lower 95% confidence
bound `6009709/11796480` (~0.509), with an additional **asserted**, not
verified, 1% simultaneous interval calibration failure budget. Thus the
conditional mathematical familywise false-positive bound is 5%; it would
be at most 6% after incorporating physically justified calibration failure.
The 4096-unit synthetic full-horizon study returns
`42380819/47185920` (~0.898), independently in both implementations.

## Exact counterexample: false propensities

For `n=64`, fixed scientific potentials `Y_i(0)=Y_i(1)=1` for every unit,
so `ATE=0`. Suppose assignments actually use `p=9/10`, but the analyst
computes inverse-propensity weights using a **false** registered `p=1/2`.
Choose one preregistered `lambda=1/8`, `alpha=1/20`, and the certified upper
logarithm witness `c=3` (16 Taylor terms, exactly checked).

With `k` treated subjects, the reported uniform-propensity Horvitz–Thompson
sum is `4k-128`, and the Hoeffding boundary is exactly `40`.
A false positive arises for every `k>=43`. Its **exact** actual probability is

`sum_(k=43..64) C(64,k) * (9/10)^k * (1/10)^(64-k)`

`= 0.9999998797925386...`.

This is a failure of **the false physical-assignment premise**, not a bug in
the v24 arithmetic under its stated assumptions. It proves how close to
worthless a precise-looking numerical certificate is when an experimenter can
lie about how randomization actually occurred. The included program evaluates
the probability with exact `Fraction`, not Monte Carlo.

## Implemented attack and control suite

- Complete independent Node BigInt replay of 110 varied synthetic adaptive
  policies, stopped histories and outcome interval records, including 4096
  registered synthetic units and four parallel tuning choices.
- Exhaustive finite-cohort coverage check for every one of the `4^5` binary
  potential-outcome schedules under an adaptively stopped 5-unit trial.
- Exhaustive small-label validation of the `K`-miss worst-case interval
  correction.
- Fail-closed rejection of forged external pin, altered registration,
  substituted report, premature stop, truncated records, unknown interval
  label, a zero-probability treatment arm, noncanonical fraction, invalid
  Taylor proof, and confidence spending above declared alpha.
- Duplicate JSON-key rejection in Python and Node.js. No floating-point
  arithmetic in the inference certificate.

## Trust boundary / unsolved issues

Source checksums and two-language correspondence do not independently attest
real treatment probabilities, raw outcome accuracy, ordered-cohort selection,
chronology, completeness of laboratory events, noninterference, or calibration
coverage. A SHA256 pin supplied from the same local demonstration does not
establish independent custody or prior registration. The explicit delta budget
is a premise, not a statistical estimate.

The next major scientific task is a prospective experiment whose allocation
service independently records each conditional propensity and action *before*
outcome/reports are disclosed, with external event retention and blinded
measurement. Until then, the implementation is an audited research prototype.
