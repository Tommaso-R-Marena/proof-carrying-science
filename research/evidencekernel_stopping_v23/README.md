# EvidenceKernel v23 — Exact response-adaptive trials with report-dependent stopping

**Research-only / draft / not production authority.** No new Lean theorem, no independently witnessed randomization, no real treatment-effect finding, no verified physical calibration, and no proof of mathematical novelty. Intended as an isolated extension on top of PCS research draft PR #210 (v17–v22).

## Why this matters

EvidenceKernel v22 models treatment allocation based on earlier reports **with a fixed enrollment length**. It does not analyze trials where the reported response can *terminate enrollment itself*. It is generally invalid to treat an observed, report-dependent stopping time as if it were an externally chosen fixed study length.

V23 treats the **entire terminal path, including its stopping time**, as the randomization outcome. It accounts for both (i) unobserved potential scientific outcomes and (ii) unobserved reports that would have influenced alternative allocations and alternative stopping times. Scientific outcomes `Y_i(0),Y_i(1)` are distinguished from policy-driving potential reports `R_i(0),R_i(1)`.

A finite-state policy supplies per-state randomization weights, the state transition after each observed report, and a `stop_after_by_state_action_report` boolean table. Before `min_enrollment` no voluntary stop is allowed; at `registered_units` stopping is mandatory. The code independently reconstructs the probability of every possible **terminal** assignment history under each compatible complete report schedule.

## Concrete synthetic example

Four units preregistered; the third assigned unit triggers the stop. Unknown potential scientific outcomes of the unenrolled fourth unit still enter the finite-population ATE and composite-null maximization.

- Observed terminal history: assignments `[0,1,1]`, reports `[0,0,1]`.
- True-outcome labels: `['0','1','1']`, allowing zero interval misses.
- Compatible report schedules: **32**; joint report/scientific models checked: **1,024**.
- Exact robust composite weak-null p-value for registered-population ATE ≤ 0: **15/32**.
- One-sided 95% lower bound on the four-unit ATE: **0**, a **synthetic** and conditional calculation, **not** a causal finding.
- The actual observed terminal history has probability `3/64` under *each compatible complete potential-report schedule*, and both independent implementations reproduce the exact report.

No results above are claimed to have biological significance; the example intentionally has low power.

## Separate counterexample to optional peeking

Under a **different**, deliberately invalid analysis that checks a fixed-length p-value after each enrollment and reports a discovery after *any* p≤0.05, the sharp-null potential-outcome vector `(0,0,0,0,1,0,1)` causes a false-positive probability of exactly `8/128 = 6.25%` under seven independent uniform allocations. The calculation is included in `test_kernel.py` and reproduced by `counterexample.py`.

This illustrates a general pitfall. The seven-unit peek-on-p-value stopping rule is **not** part of the currently supported v23 finite-state stopping table (the research engine caps `registered_units` at 5); it is not represented as an internally verified example of the v23 model. V23's actual guarantee covers the bounded policies it explicitly validates.

## Run

Python ≥3.12, Node.js ≥20; only standard libraries.

```sh
# From PCS repository root
python -m unittest research.evidencekernel_stopping_v23.test_kernel research.evidencekernel_stopping_v23.test_differential -v

DIR=research/evidencekernel_stopping_v23
PROTOCOL_PIN="$(cat "$DIR/example_protocol_pin.txt")"  # synthetic, not independent custody
EVIDENCE_PIN="$(cat "$DIR/example_evidence_pin.txt")"
python -m research.evidencekernel_stopping_v23.kernel "$DIR/example_protocol.json" "$DIR/example_evidence.json" --protocol-pin "$PROTOCOL_PIN" --evidence-pin "$EVIDENCE_PIN"
node "$DIR/independent.js" "$DIR/example_protocol.json" "$DIR/example_evidence.json" "$PROTOCOL_PIN" "$EVIDENCE_PIN"
python "$DIR/counterexample.py"
```

### Fail-closed behavior

The exact protocol and record are both SHA-256-pinned to externally supplied values, with strict schemas. The verifier rejects wrong or incomplete pins, duplicate JSON keys, JSON floating-point values, unsupported experiment sizes, nonpositive realized treatment probabilities, premature stops, and enrollment records that continue after the precommitted stopping condition. An independent source of those pins is necessary for prospective assurance; including them in the synthetic example directory does not provide that source.

Work is bounded to `2 ≤ registered_units ≤ 5`, `1 ≤ states ≤ 5`, a minimum enrollment of 2, binary observed actions/reports, and a cap on compatible-model work. Potential scientific outcomes and potential reports are assumed deterministic for each unit and action, with no interference across units. The inference rule is conservative and may lose substantial power.

## Limitations

- This does **not** verify a real preregistration timestamp, independent allocation generator, complete recording of attempts, authenticity of scientific measurements, or correct calibration of any asserted interval-coverage failure probability.
- Supports only finite *preregistered* stopping tables and fixed potential-report schedules. It does not justify arbitrary outcome-driven changes to the protocol, adaptive reporting manipulation, unbounded optional stopping, survival-time endpoints, delays, continuous outcomes, or an unknown sampling population.
- `max_interval_misses` is a deterministic assumed bound, not a probability derived by this module. Any failure-probability allowance `δ` requires separate, independently justified calibration and union-bound accounting (`α+δ`).
- Neither the Python nor JS code is a formal proof; independent implementation agreement, finite exhaustive tests and a conditional mathematical argument are distinct evidence types.
- Current research follows established randomization-test and stopping-time ideas, and does not claim foundational novelty.

See `MATHEMATICS.md` and `AUDIT.md` for the exact proof argument and concrete attack boundaries. No production PCS path or existing EvidenceKernel research module is modified.
