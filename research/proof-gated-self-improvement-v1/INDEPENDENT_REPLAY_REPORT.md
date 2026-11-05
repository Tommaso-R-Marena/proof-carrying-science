# Independent scalar-ReLU certificate replay (experimental v1)

**Status: research reference only. NOT Lean-kernel-checked. NOT a signed
certificate. NOT a protected automatic promotion authority.**

This small subproject adds a distinct, self-contained Python replay verifier
for the existing one-dimensional, integer-weight ReLU reference analyzer.

## Why

The original \`universal_relu.py\` analytically decides, for finite sums of
scalar-input ReLU units and exact integer inputs, whether a candidate loses
any previously correct prediction and what the exact maximum absolute error
is in a chosen bounded integer window. Until the mathematical checker is
proved in Lean, trusting its reported result directly would enlarge the
trusted computing base.

\`relu_certificate_export.py\` now produces a canonical, content-digested
JSON *evidence record* containing all model coefficients, every activation
boundary, each interval's old/new affine error coefficients, the endpoints
needed for the bounded-window maximum, and the claimed result.

\`relu_certificate_replay.py\` independently reconstructs and checks the
coverage. It does **not** import \`universal_relu.py\` or the certificate
producer. It uses exact \`fractions.Fraction\` threshold arithmetic rather
than the producer's integer-division implementation, computes affine
branches anew, checks every supplied region, recomputes endpoint maxima,
and validates claimed lost-correctness witnesses.

The body digest is SHA-256 over domain-separated canonical JSON. It binds
the body to the checksum but is **not** a digital signature, an anti-rollback
mechanism, or evidence that the generator or replay binary was trustworthy.
An attacker can freely recompute this digest, so the replay must verify the
claims independently.

## Scope and claims

Supported: arbitrary finite-width networks

\[
f(x)=c+\sum_i a_i\max(0,w_i x+b_i), \quad x\in\mathbb{Z}
\]

with exact integer parameters and a target of the **same** architecture.
Two properties are replayed:

1. **No forgetting on all integers:** every input where the incumbent
   exactly equals the target must remain correct after modification.
   A failure certificate supplies a concrete integer counterexample.
2. **Nonincreasing maximum absolute error on a specified closed integer
   window:** calculate the exact maxima for old/new models and compare.

The existing seven-example Lean admissibility condition is separate.
A successfully replayed document is not a Lean-authorized transition, and
a correct reference proof of no-forgetting still does not guarantee an
improvement on every previously incorrect example.

## Protocol and exact replay

Version tag \`PCS-RELU-REPLAY-v1\`; signed parameters, intervals and
counterexamples are **canonical decimal strings**. Reject leading zeros,
negative zero, explicit plus signs, Unicode, unrecognized fields, duplicate
keys, noncanonical JSON, malformed SHA-256 digests, forged affine
coefficients, missing cells, altered cut points, invalid window coverage,
and false Boolean or counterexample claims. Limit certificate files to 4
MiB, model width to 512 units, and integer fields to 120 decimal digits
(with an optional minus sign).

The verifier reconstructs activation boundaries by exact rational
arithmetic. A finite partition suffices because each ReLU term and model is
affine on every cell. To validate universal preservation, each old-target
affine difference is either identically zero on a cell, never zero there,
or has one possible integer zero; these cases are checked exhaustively.
The maximum of absolute affine error on a bounded interval occurs at one
of its endpoints.

This paragraph is a mathematical rationale, **not** a kernel-checked proof
of the Python algorithm or its interpreter/OS semantics. Independent Lean
theorems may later discharge that proof obligation.

## Reproduction

From the research directory:

\`\`\`bash
python -m unittest discover -s tests -v
python - <<'PY'
from universal_relu import Net, Term
from relu_certificate_export import build_certificate
from relu_certificate_replay import replay
target = Net((Term(1,2,1),))
old = Net((Term(1,3,-3),))
candidate = Net((Term(1,3,-1),))
cert = build_certificate(old,candidate,target)
decision = replay(cert)
assert not decision.no_forgetting and decision.counterexample == 4
print(decision)
PY
\`\`\`

Independent negative tests mutate model coefficients, a positive decision,
individual affine coefficients, interval coverage, endpoint samples and
canonical encodings **then recompute the digest**. The replay must still
reject them. Randomized tests compare against direct integer enumeration;
a distant root at 1,000,000, 220-unit hidden-layer permutation and a
trillion-scale bounded interval are covered.

## Next authority upgrade

1. Integrate Aristotle's **final verified source**, not stale exported
   snapshots, and independently reproduce the kernel build.
2. Define a versioned certificate checker in Lean that verifies these
   piecewise-affine statements, particularly bounded-window worst error.
3. Establish canonical Python–Lean byte equivalence and bounded resource
   usage for the checker.
4. Run it under independent authority credentials with verified artifact
   identity and immutable policy. None of those host security guarantees
   follow from this Python prototype.

Keep this work on a **separate stacked draft branch** until independent
verification. It should not interfere with Aristotle's \`formal/\` modules
or Codex's wider PR #117 security work.
