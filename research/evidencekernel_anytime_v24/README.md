# EvidenceKernel v24 — exact-rational predictable-policy confidence sequences

**Research draft only.** This directory introduces an independent inference route
for Proof-Carrying Science (PCS). It is neither part of PCS's production trust
boundary nor a replacement for its Lean-scoped scientific receiver. No external
study, deployment, independence, physical treatment assignment, measurement,
chronology or laboratory result is authenticated by these files.

## Why this is different from v23

V23 performs exact randomization inference by enumerating every binary scientific
potential-outcome schedule and every binary potential-report schedule. It is
limited to five registered units. V24 computes an **anytime-valid one-sided
lower confidence bound for the finite registered-population average treatment
effect** using a linear pass through the observed experimental history. Its
model supports registered cohorts up to 100,000 units.

V24 assumes sequential treatment probabilities are **predictable and physically
correct**, but the reports used to update those probabilities may be noisy,
stochastic, or adversarial. It does not require a stable counterfactual binary
report schedule. The fixed cohort, stable scientific potential outcomes, and
conditional treatment randomization are still required. Early stopping may
depend on the recorded report, treatment, and state. An independently valid
bound on simultaneous interval-coverage failures is an additional premise.

The mathematics is a straightforward construction from Horvitz–Thompson
inverse-probability weighting, Hoeffding's conditional lemma, exponential test
supermartingales, Ville's inequality, and Bonferroni composition. **Those
statistical methods are not new.** The research implementation contribution is
exact-rational replay and validation of this combination for PCS with reported
uncertainty, a deterministic registered feedback policy, conditional audit
boundaries, and an explicit false-propensity attack.

## Model and limitations

1. There is a prospectively fixed, ordered list of `n` experimental units. Every
   unit has fixed binary potential scientific outcomes `Y_i(0),Y_i(1)`. No
   interference, anticipation, subject replacement, outcome drift, or adaptive
   selection/reordering of future units is allowed.
2. Before assignment `i`, the registered finite-state policy determines a
   positive `p_i=P(A_i=1 | past)`. The **actual** treatment assignment uses
   fresh randomization with that conditional probability. The entire past may
   include noisy, action-dependent, stochastic reports. The report for the
   current unit cannot influence its own prior treatment draw.
3. Reports and treatment determine the registered stopping time. All observed
   assignments, reports and binary measurement intervals are provided in one
   complete committed prefix. A reported stopping time inconsistent with the
   registered rule is rejected.
4. Among observed outcome intervals, at most `K` may be incorrect on an event
   whose externally established failure probability is at most `delta`. V24
   **does not establish `delta`** and cannot certify that intervals represent
   real measurements.
5. The family of test-supermartingale tuning choices (`lambda`, `alpha_spend`,
   `log_upper`) is frozen in the protocol. The verifier *proves with exact
   rational arithmetic* that a finite positive Taylor sum for `exp(log_upper)`
   is at least `1 / alpha_spend`. Total spending cannot exceed `alpha`.

The confidence bound covers the ATE of **all `n` registered units**, including
those unobserved after an early stop. The `n-t` absent contributions receive
the scientifically honest worst-case bound `-1` per unit. No clinical efficacy,
experimental success, or real-world false-positive rate is claimed.

## Reproduce (Python >=3.12, Node >=20; standard library only)

From the repository root:

```bash
python -m unittest discover -s research/evidencekernel_anytime_v24 -t . -v
python -m research.evidencekernel_anytime_v24.counterexample

D=research/evidencekernel_anytime_v24
P=$(cat "$D/example_protocol_pin.txt")    # locally generated SYNTHETIC pin
E=$(cat "$D/example_evidence_pin.txt")    # locally generated SYNTHETIC pin
python -m research.evidencekernel_anytime_v24.kernel \
  "$D/example_protocol.json" "$D/example_evidence.json" \
  --protocol-pin "$P" --evidence-pin "$E"
node "$D/independent.js" "$D/example_protocol.json" \
  "$D/example_evidence.json" "$P" "$E"
```

Both independently implemented verifiers emit the same exact-rational JSON
report. The `SOURCE_SHA256.json` checksums permit byte-for-byte review of the
source files in this research snapshot. Files in the same repository as the
synthetic records **are not independent external witnesses**. In real research
all commitments must be supplied from independently retained and timestamped
records; the CLI cannot attest that the supplied pins were frozen before data.

The generator reproduces the examples without outside data:

```bash
python -m research.evidencekernel_anytime_v24.make_demo
```

A 512-unit synthetic study stops at unit 457 after 55 registered units remain
unobserved. The exact one-sided lower ATE bound is `6009709/11796480`
(approximately 0.50945), **conditional on the assumptions**. A separately
regenerated 4096-unit synthetic full-horizon case produces a lower bound of
`42380819/47185920` (approximately 0.89817). These are artificial positive-
effect potential-outcome schedules, not empirical findings. The generator's
pseudorandom seed is not an independent trial randomizer.

## Computational accounting

- Runtime is linear in observed length, apart from the `K`-largest interval
  penalty sort (`O(t log t)`). Memory is linear in observed length; model work
  does **not** grow as `4^n`.
- All checked p-values, weights, penalty terms, boundaries and final bounds
  are exact rational numbers. The program never evaluates an exponential or
  a floating-point logarithm for its guarantee.
- The 110-case Python/JavaScript differential check, exact finite-model
  enumeration, tamper controls and 64-unit propensity counterexample run in
  the dedicated workflow. They are software tests and finite experiments, not
  a proof that the physical assumptions hold.

## Major remaining obstacles

V24 verifies the consistency of an asserted assignment policy with a *recorded*
transcript. It cannot tell whether the physical allocation device actually
sampled that policy, whether researchers selectively omitted attempts or
subjects, whether external calibration coverage holds, whether units influence
one another, or whether observed outcomes are authentic. The included
counterexample shows that lying about the physical propensity can generate a
false-positive rate approaching 100% despite perfectly replayable arithmetic.

Statistical prior art: Howard, Ramdas, McAuliffe & Sekhon (2021), *Time-uniform,
nonparametric, nonasymptotic confidence sequences*, Annals of Statistics,
DOI 10.1214/20-AOS1991; Cook, Mishler & Ramdas (2024), *Semiparametric
Efficient Inference in Adaptive Experiments*, CLeaR, PMLR 236:1033–1064.

This is an engineering research extension; novel mathematical priority,
proof-carrying Lean formalization, and prospective scientific validity have
not been established.
