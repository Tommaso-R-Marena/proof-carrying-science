# EvidenceKernel v18 — Transcript-conditioned exact inference

**Research-only; non-authoritative.** Stacked on PCS draft PR #210 (v17), which is stacked on #208 (v16). This directory does **not** replace earlier research, alter Claim IR or Lean kernels, change production verification, or attest to physical randomization. Synthetic examples only.

## Result: eliminate the second randomness premise

V17 can improve the discrete-test power with a separately sampled uniform index `J`, but that introduces a new independent-randomness assumption and attack surface. V18 uses the *original, already-preregistered candidate-allocation transcript* as a conditional ancillary source of discrete tie randomness. The full ordered transcript is still assumed honestly generated and complete. To prevent an uncommitted reporter from swapping transcripts after outcomes are known, the executable **requires** a separately provided, protocol-bound SHA-256 commitment to the complete ordered attempt list. It must be independently retained before outcome inspection; the software cannot prove this chronology. No additional post-outcome randomization is requested from a researcher or beacon.

Let `Ω` be all length-`b` candidate sequences under the preregistered distribution (IID uniform with replacement or ordered uniform without replacement). Each sequence has probability `1/D`, where `D=N^b` or `(N)_b`, respectively, with `N = C(n,k)`. Let `f: Ω→Z` be the deterministic, preregistered outcome-blind selection rule. For selected assignment `z`, define:

- `m_z = #{ω : f(ω)=z}` (the v17 exact design histogram);
- `r_z(ω) = 1 + #{ω' <lex ω : f(ω')=z}` (its within-`z` lexicographic rank).

**Conditional fact:** given `Z=z`, the observed `ω` is uniform on those `m_z` transcripts. Thus `U_z=r_z(ω)/m_z` is discrete-uniform on `{1/m_z,...,1}`, and hence superuniform for every fixed `z`. It need not be independent of `Z` to provide a valid tie randomization: conditional on the test statistic's value (a function of `Z` for a fixed potential-outcome world), the distribution of `U_Z` is a mixture of superuniform distributions and is still superuniform.

For a fixed binary potential-outcome world `Y` define the exact test:

```
p_Y = P_mu(T_Y(Z') > T_Y(z)) + U_z * P_mu(T_Y(Z') = T_Y(z)).
```

It is superuniform under the correct assignment law. To test the composite null `ATE(Y) ≤ h` under uncertain binary observations and up to `K` missed intervals, take the **maximum** of `p_Y` over every compatible null world. The true world is among them on the calibration-coverage event, giving conditional false-positive control. Invert these monotone composite tests to obtain a one-sided lower confidence bound for the finite-population average causal effect without constant individual effects. The tautological upper endpoint `ATE≤1` is assigned `p=1` so the confidence set is nonempty.

If interval coverage fails with probability at most `δ` *jointly for the experiment*, the unconditional error guarantee is at most `α+δ`; `δ` is an externally justified premise, not calculated by this module.

## Efficient exact lexicographic counting

The direct method would enumerate the `D` candidate histories, often impossibly large. Instead, fix the observed prefix and compare each lexicographically smaller legal candidate at the first differing position. For that candidate's prefix, count all permitted suffixes grouped by final winner.

For score threshold `s` and `r` remaining draws, let `A_s` be the number of permitted candidates scoring `≥s`, `B_s` scoring `>s`, and `m_s` the permitted group of score exactly `s`. The number of suffixes whose winning candidate is a given member of a *strictly improving* group is:

```
with replacement:       (A_s^r - B_s^r) / m_s
without replacement:    ((A_s)_r - (B_s)_r) / m_s
```

If the existing prefix winner has score `g`, the number of suffixes that never improve it is `F(#{remaining candidates scoring ≥g})`. These counts are exact by exchangeability and disjoint minimal-score partition. Summing across the first differing position yields the rank `r_z` without materializing any full alternate candidate history.

The code deliberately bounds `n≤8`, `b≤4096`, and world-assignment evaluations to a limited finite research scope. Arbitrarily large effect-inference problems are **not** solved; this is finite exact computation with an explicit capacity bound.

## Reproduce

From the repository root, with Python ≥3.12 and Node.js ≥20:

```bash
python -m unittest discover -s research/evidencekernel_transcript_v18 -p 'test_*.py' -v
PIN=$(cat research/evidencekernel_transcript_v18/example_pin.txt) # DEMO ONLY
ATTEMPTS_PIN=$(cat research/evidencekernel_transcript_v18/example_attempts_pin.txt) # DEMO ONLY
python -m research.evidencekernel_transcript_v18.kernel \
  research/evidencekernel_transcript_v18/example_protocol.json \
  research/evidencekernel_transcript_v18/example_evidence.json \
  --protocol-pin "$PIN" --attempts-pin "$ATTEMPTS_PIN" > /tmp/ekv18-py.json
node research/evidencekernel_transcript_v18/independent.js \
  research/evidencekernel_transcript_v18/example_protocol.json \
  research/evidencekernel_transcript_v18/example_evidence.json "$PIN" "$ATTEMPTS_PIN" > /tmp/ekv18-js.json
python -c "import json; assert json.load(open('/tmp/ekv18-py.json'))==json.load(open('/tmp/ekv18-js.json'))"
```

## Synthetic results and adversarial controls

For the inherited 6-unit, 3-treated, 2-IID-candidate design:

| Calculation | Result |
| --- | ---: |
| Candidate transcripts | 400 |
| Selected assignment | `(0,1,2)` |
| Transcripts selecting this assignment | 2 |
| Observed within-selection rank | 1 of 2 |
| Nonrandomized v17 weak-null p | `1/200` |
| Conditional transcript-tie weak-null p | `1/400` |
| Nonrandomized v17 lower ATE bound | `1/3` |
| Conditional transcript-tie lower ATE bound | `1/2` |
| Detection probability under extreme positive binary world | `364/400 = 91%` |

The example is **synthetic** and the observed allocation is deliberately rare; it is not a prospective causal finding. The last power number is specific to this design/world, not a general improvement guarantee. The original v17 auxiliary randomizer achieves `87.625%` power under its different source of randomness, while the nonrandomized version achieves `1%`.

**Adversarial result:** if the operator can rewrite its claimed candidate-draw transcript after the selected allocation is known, it can always choose the lexicographically earliest transcript mapping to that allocation. For the all-null zero-effect world in this 6-unit design, this creates an exact **396/400 = 99%** false-positive probability at a 5% threshold. The executable now rejects any substituted transcript against a *separately supplied* genuine attempt commitment, but a self-generated post-hoc commitment cannot establish a real-world guarantee.

An earlier global-transcript-rank construction could return an empty confidence set in this example. The conditional-within-selected-allocation rank is deliberately used instead, and the tautological null `ATE≤1` is explicitly nonrejected.

Tests include exact lexicographic histogram comparison to brute-force enumeration (both candidate laws), complete sharp-null rank calibration on **all 256 binary potential-outcome tables** for a 4-unit design, a composite-null exact finite level check, 80 independently generated cross-language full-inference comparisons, the 99% forging counterexample and fail-closed attempt-pin mismatch, malformed/tampered evidence rejection, and algebraic counting with `70^128` possible candidate sequences without enumerating them.

## Trust boundary and limitations

1. The candidate allocation sequence must genuinely be drawn as preregistered, independently of potential outcomes; baseline covariates and selection rule must be fixed in advance. **Checking that a transcript is internally consistent is not proof of these premises.**
2. The researcher must not discard or alter earlier candidate sequences, choose a favorable trial, stop and restart secretly, choose the covariate/selection rule after seeing outcomes, or reset a trial without external accountability. V15's selective-retry problem remains.
3. Externally pinned protocol hash is required. The bundled protocol and attempt hashes are not independently retained and do not establish preregistration or pre-outcome chronology. Evidence is not signed or externally witnessed in this v18 example; earlier PCS projects have separate witnessing prototypes.
4. Binary potential outcomes, finite-population ATE, and externally justified simultaneous interval coverage are assumed. No real biological data or laboratory calibration used.
5. Exact conditional error control is a mathematical argument supported by bounded exhaustive tests. It is **not** a Lean-kernel proof, security audit, or empirical validation.
6. The randomized p-value itself is not a new concept; this conditional-ancillary implementation and algebraic ranking are engineering/research contributions. Formal novelty and broader utility require an independent literature and experimental review.

Relevant prior art: Fisher randomization inference; Morgan & Rubin (2012) rerandomization; randomized p-values and tie randomization (Habiger 2011); selective randomization inference for adaptive experiments. No claim of an unprecedented mathematical theorem or a world-changing discovery is made.
