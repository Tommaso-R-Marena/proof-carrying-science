# PCS V7: independent external runtime and mathematical-semantics audit

**Date:** 2026-10-18. **Scope:** Read-only standalone V7 fixture replay and independent reference behavior. **Production changes:** None.

## Verification summary

The supplied authoritative PCS V7 archive was verified by SHA-256 to match the digest `e98448c4d9493c54b88c876ea715c4c66d653565bf60d553c9627b14b7a5f8f8`. This audit was conducted *outside Lean* with independently authored Python code, not by reusing the original Lean checker source or porting Lean's sweep routine.

The independent verifier reproduces strict canonical integer-byte encoding for PGPOL7, PGSC6, PGSC7, PGSR7, and PGSI2-WIDE. For semantic validation, it computes integer ReLU networks with arbitrary-precision integers and converts the difference of two networks to a finite partition of affine integer intervals. Universal no-forgetting reduces to finding integer roots of the incumbent-target affine function within each interval, then checking the candidate-target difference at those roots (or over the entire interval when the incumbent-target difference is identically zero). Maximum absolute error on any finite integer interval occurs at the endpoint of one of the affine cells, so the independent oracle evaluates those endpoints.

### Executed results

The default fixed-seed run yielded:

| Test family | Result |
|---|---:|
| Canonical policies | 6/6 round-trip |
| Canonical PGSC7 certificates | 3/3 round-trip |
| Canonical PGSR7 receipts | 7/7 round-trip |
| Published V7 receipt decisions | 7/7 semantically consistent |
| Admitted transitions | 3, ending at generation 3 |
| Rejected transitions | 4, unchanged state |
| PGSC7 valid fixtures | 3/3 semantic acceptance |
| Random exact-affine vs bounded brute-force cases | 6,000/6,000 agreement |
| Byte-mutation trials | 20,000 (15,659 rejected / 4,341 other valid canonical encodings) |
| Semantic receipt mutation trials | 42 (38 rejected / 4 equivalent rejection receipts) |
| Far-tail regression witnesses | 3/3 detected (x = 1e3, 1e6, 1e12) |

**Interpretation:** zero mismatches in this campaign on the checked properties, not proof of complete Lean/Python runtime equivalence.

## Finding 1 — a valid receipt does not prove authentic rejected-request history

V7 `checkReceipt` proves that a record corresponds to *some* actual abstract proposal and response. However, a rejected record binds an untrusted certificate that was not accepted, and many alternative malformed certificate bytes would be rejected from exactly the same old state. Such replacements can themselves produce valid rejected receipts with identical old and new state, generation and policy. Our experiment created four such substitutions, each of which remained mathematically valid under independent semantics.

This is a form of **rejection-history equivocation**. It is **not** a failure of the claimed Lean theorems, and it cannot authorize an inadmissible model. It matters for audit scenarios where proving exactly which invalid request was received, or who submitted it, is required. Signatures, trusted append-only event capture, and authenticated monotonic anchors are separate external obligations.

## Finding 2 — bounded testing can approve a universally destructive improvement

Define an exact integer bump:

\[
 h_N(x)=\operatorname{ReLU}(x-N+1)-2\operatorname{ReLU}(x-N)+\operatorname{ReLU}(x-N-1).
\]

This equals the Kronecker delta at integer input N. For target h_0, old model 0, and new model h_0+h_N, with N much larger than any practical probe interval, the candidate improves the nine-input corpus `[-4,4]` from error 1 to 0 and has zero error on `[-100,100]`. However, the incumbent was correct at x=N and the candidate is wrong there. Three deterministic experiments (N=1e3, 1e6, 1e12) found the exact distant witness with the independent all-integer cell solver.

This is **not** a new logical gap in V7: V7's universal no-forgetting checker exists precisely to reject these cases. The experiments provide an additional non-vacuous adversarial control for future runtime translations and any new adaptive policy.

## Finding 3 — resource and authenticated-history engineering remain independent risks

Canonical parsing and a mathematical gate do not by themselves impose bounds on adversarial wire sizes, wall-clock execution, memory, or numeric bit lengths. While V7's model architecture bounds restrict accepted models, receiving a maliciously large malformed input can still consume resources *before* it is rejected. This is an identified threat requiring real-resource testing; it was not independently exploited or timed in this work.

An external host must enforce a pinned policy's maximum message sizes and resource budgets, without altering the mathematical meaning of the certified subset. The published V7 model cannot itself prove OS-enforced resource limits, authentication, durable monotonic state, or actual deployment isolation.

## Recommendation for V8 / separate runtime hardening

Keep Aristotle's mathematical V8 work isolated. Add this audit's distant-integer bump vectors and rejection-history equivocation vectors to the *untrusted test corpus* of a future V7 receiver implementation. Independently compare actual compiled Lean decisions against the Python oracle for generated valid/invalid certificates, including distant-input witnesses and policy-bounded architectures. Add a constrained receiver with pinned byte-length and integer-digit budgets and explicit 2-process failure tests, but do not merge with the V8 theorem-development source tree until independent checks pass.

## Verification commands

```bash
python3 v7_independent_audit.py --fixtures fixtures/proof_gated/v7 --mutations 20000
```

All results here are reproducible without contacting GitHub. The exact V7 archive digest and original fixture sources should be retained separately for provenance.

## Mathematical observation — open-ended capability growth requires expandable capacity

For a fixed V7-style architecture with maximum hidden width `W` and all integer parameters in `[-B,B]`, the number of *syntactically distinct* one-hidden-layer `WideNet` models is exactly

\[
 M(W,B)=\sum_{k=0}^{W}(2B+1)^{3k+1}.
\]

There are `3k` hidden-unit parameters for a width-`k` model, plus one output bias. Two syntactically different models may be functionally equal, so the number of distinct semantic functions is **at most** `M(W,B)`.

Consequently, if an accepted capability-extension transition must genuinely satisfy a semantic obligation that the immediately prior model did not satisfy, while preserving every previously certified obligation, no semantic function can reappear later in that trace. Otherwise a later model equal to an earlier one would satisfy all of the intermediate model's already certified obligations but fail the requirement that some newly acquired capability was previously unsatisfied. A trace therefore has **at most `M(W,B)-1` strict semantic gains** for fixed `W,B`, regardless of how the capability ledger evolves.

This is an elementary finite-state argument, **not** a new Lean-checked theorem and not a claim about efficiency or intelligence. It is an important sanity check for V8's open-ended-growth research: expanding width, parameter range, or another genuinely new representational resource is necessary for an unbounded strict-gain trace in this finite integer network family. Merely changing the objective cannot circumvent this combinatorial bound.
