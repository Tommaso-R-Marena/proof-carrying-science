# EvidenceKernel v16 — exact outcome-blind selection-aware causal audit (research)

**Status:** isolated prototype, non-authoritative. This is a design-aware extension to the externally developed EvidenceKernel v15 line, **not** an upstream import of the 518-file release, a PCS science receiver, a proof of real-world trial validity, or a production trust root. It does not modify PCS theorem checking, authorization, CI policy, or scientific adjudication. All observations, covariates and attempt records in this directory are synthetic.

## Research question and result

When a registered randomization protocol generates several candidate treatment allocations and selects the allocation with the **best pre-treatment covariate balance**, treating the choice as if researchers peeked at outcomes on every attempt is conservative but potentially wasteful. Instead of paying a generic retry penalty, v16 **exactly enumerates the induced selected-assignment distribution**, then evaluates causal evidence under that distribution.

In a deliberately extreme six-unit synthetic trial, two independent uniformly drawn candidate assignments are selected by minimum absolute baseline imbalance (first candidate wins a tie). The registered selected assignment is `(0,1,2)`, the recorded binary outcomes are `[1,1,1,0,0,0]`, and the proposed weak null is finite-population average treatment effect `<= 0`. The worst-case p-value over **all** compatible binary potential-outcome tables is **`1/200 = 0.005`**. The generic v15 two-try adjustment to a uniform single-assignment p-value of `1/20` is `39/400 = 0.0975`. These apply to **different selection assumptions**; the improvement is not universal.

### Conditional mathematical guarantee

Let `Y` be any fixed vector of binary potential outcomes for registered units and `mu` be the **exact selected-assignment distribution** induced by a fixed, outcome-blind, precommitted sampling/selection algorithm. Define `T_Y(z)` as the difference-in-means statistic (scaled to an integer) and

`p_Y(z) = sum_{z': T_Y(z') >= T_Y(z)} mu(z')`.

Because this is the upper-tail mass in its own finite distribution, `Pr_{Z~mu}(p_Y(Z) <= a) <= a` for every `a` in `[0,1]`, including ties and nonuniform selected allocations.

For observed assignment `z` and compatible latent tables `M(z, intervals, K)` with no more than `K` incorrect binary observation intervals, define

`p_robust(z) = max { p_Y(z) : Y in M, ATE(Y) <= h }`.

If the registered weak null is true and the true fixed `Y` lies in `M`, then `p_robust >= p_Y`, so the test has conditional type-I error at most `a`. If simultaneous interval coverage is only guaranteed with failure probability at most `delta`, the unconditional bound is at most `a + delta`, **provided** that calibration covers the complete selected experimental process with the necessary conditioning. This repository does **not** compute or establish `delta`; `K` is a registered sensitivity parameter. The statistical reasoning follows established design-based randomization inference, not an asserted new theorem.

### What is independently checked

- The registered method, baseline covariates, weak null, allowable interval misses, draw count and candidate law are all bound to a required SHA-256 **external** protocol pin.
- All candidate allocation attempts are present **in the supplied transcript**, and the selected assignment follows the preregistered outcome-blind choice rule (including deterministic tie handling).
- The entire selected-assignment probability histogram is recomputed using **integer combinatorial counts**: ordered draws either with replacement (IID) or without replacement.
- The weak-null p-value is maximized over every compatible **unit-specific** binary potential-outcome table using exact rational arithmetic; no constant-effect assumption, asymptotic approximation, or iid-outcome assumption.
- Two independently written implementations (Python and Node.js) agree on seeded differential cases and the published example. Exhaustive small-world error-control tests check each attainable p-value threshold, not just selected confidence levels.
- Unsupported designs, inconsistent transcript selection, noncanonical nulls, tampered pins and resource overflows fail closed. A `INCONSISTENT_NULL` diagnostic is **not** promoted to a discovery.

### External trust boundaries

A hash pinned only by the experimenter is not independent preregistration. A supplied attempt transcript is not proof that no other attempts occurred. Baseline covariates must genuinely precede treatment and be unavailable for outcome-dependent manipulation. Random candidate allocations must actually follow the stated registered law and be complete; selective trial disclosure, participant attrition, unobserved interference, outcome mismeasurement, false intervals and counterfactual violations are **not** authenticated here. No confidence bound on average effect is yet implemented under the new design. These must be addressed before any claim of scientific validity.

## Reproduction

```bash
cd research/evidencekernel_selective_v16
python -m unittest discover -v -p 'test_*.py'
python kernel.py example_protocol.json example_evidence.json --protocol-pin "$(cat example_pin.txt)"
node independent.js example_protocol.json example_evidence.json "$(cat example_pin.txt)"
```

Requires Python 3.12+ and Node.js 20+; no third-party packages. Python CLI rejects missing external trust pins. `example_pin.txt` is explicitly a **demo-only local pin** and should never be used to establish real-world preregistration.

### PCS integration status

This draft creates only an isolated `research/` experiment and a path-scoped CI test. It does not connect to the PCS authority kernel or v15's external signing/receipt layers. A later integration should consume externally validated acquisition receipts through an explicitly typed, fail-closed adapter and preserve the distinction between `math replay verified` and `real-world design verified`. No merge or deployment is proposed.

### Prior art and novelty limits

- Fisher randomization tests and weak-null potential-outcome maximization are established methods.
- Covariate-balancing rerandomization and finite selection designs predate this work; see Morgan and Rubin (2012), *Rerandomization to improve covariate balance in experiments*; and the 2026 JRSS A finite selection model discussion: https://doi.org/10.1093/jrsssa/qnag040.
- This is a **new bounded executable capability for the EvidenceKernel prototype**, not a demonstrated novel fundamental theorem or scientific breakthrough. External review and independent prospective trials are required.