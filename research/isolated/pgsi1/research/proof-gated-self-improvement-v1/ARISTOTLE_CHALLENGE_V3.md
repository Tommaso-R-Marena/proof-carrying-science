# Aristotle challenge: verified neural self-modification v3

## Environment and nonnegotiable rules

Work on the **research-only** PCS branch
`research/proof-gated-self-improvement-v1-20261016` of
`Tommaso-R-Marena/proof-carrying-science` (draft PR #117).
The Lean project is in `formal/`, uses **Lean 4.28.0** and **does not depend on Mathlib**.
Read the actual sources before writing proofs:

- `formal/PCS/V2/ProofGatedSelfImprovement.lean`
- `formal/PCS/V2/ProofGatedArtifacts.lean`
- `formal/PCS/V2/ProofGatedPromotion.lean`
- `formal/PCS/V2/ProofGatedInference.lean`
- `formal/PCS/V2/ProofGatedSymbolic.lean`
- `formal/PCS/V2/ProofGatedAudit.lean`
- `research/proof-gated-self-improvement-v1/{proof_gate,promotion_v2,sealed_inference}.py`

Do **not** change production PCS authority or relax its checks. Do not create new axioms,
`sorry`, `admit`, `unsafe`, `@[implemented_by]`, or hypothesized "soundness"
without clearly exposed assumptions. You may use standard Lean foundations
`propext`, `Classical.choice`, `Quot.sound` where needed. Every proposed result
must be kernel-checked with a clean `lake build` and a `#print axioms` audit.
Do not mislabel finite benchmark gains or AST-cost gains as universal intelligence
improvement. Do not merge the experimental branch.

## Priority 1: verified canonical model roundtrip and injectivity

Currently we prove `decode raw = some m -> encode m = raw` and bounds, but
the converse and injectivity have not been established in Lean.

1. Prove a theorem such as
   `valid m = true -> decode (encode m) = some m` for every
   bounded `Neuron` (including `-32`, `32`, `0`, ReLU and linear).
   If necessary, split into clean reusable helper lemmas for
   `String.toInt?`, integer signs, separators and canonical text.
2. Prove `encode` injective on valid neurons, preferably as a corollary.
3. Prove precise failure conditions for noncanonical encodings; provide
   separately checked counterexample fixtures for leading zero, negative
   zero, sign ambiguity, spurious delimiters and whitespace.
4. Tie this to `infer`: roundtrip execution reproduces exactly
   `predict m x` for *every integer x*, not just the seven benchmarks.
   The Python and OS bytes correspondences must remain explicitly
   external unless actually formalized.

## Priority 2: generalize from one neuron to a small quantized neural network

Design an exact, finite, versioned fixed-point or integer architecture,
preferably a network with **two hidden neurons** and a shared output layer.
Use a total evaluator (no floating-point ambiguities); specify
activation and arithmetic explicitly and bound every parameter.

Prove an executable Lean gate's soundness:
- on a frozen `List Int` / finite vector corpus, every previously
  correct prediction remains correct;
- at least one newly correct example is gained;
- total exact loss decreases strictly;
- accepted chains preserve correctness, decrease a natural-valued
  potential and have a finite upper length bound;
- rejected proposals do not mutate the incumbent;
- adversarially changing proposers cannot bypass the checks.

Ensure candidate architectural changes are part of the typed
candidate object and checked. Supply at least one explicit accepted
multi-generation witness and one blocked case, both checked in Lean.
If construction of such a witness is difficult, do not fabricate it.
Separate computational tractability from mathematical soundness.

## Priority 3: separate proof-carrying semantics from executable deployment

Extend the pure `ProofGatedPromotion` / `ProofGatedInference` story:
- prove successful CAS always binds the current generation and exact
  active artifact, and non-commit is identity;
- prove exact-artifact inference for an accepted candidate and
  preservation of all previously correct outputs;
- investigate sequence invariants for arbitrary interleavings of
  accepted/rejected proposals;
- state an explicit *refinement relation* for a content-addressed
  implementation. If SHA-256 collision resistance, I/O fidelity,
  atomicity, trusted loader, monotonic anchoring or process separation
  are required, state them as named **assumptions**, not axioms
  smuggled into a theorem or claims of production security.

## Priority 4: adversarial and epistemic falsification

Formalize at least one same-target out-of-domain counterexample:
an update accepted on the frozen benchmark worsens exact error on
an external integer input. Existing `same_target_ood_regression`
is the reference. Distinguish a universal, finite-domain theorem
from any empirical claim about generalization or intelligence.
Investigate genuine search obstructions: local moves that cannot
improve the certified frontier despite the existence of a beneficial
larger edit. Avoid claiming perpetual recursive improvement.

## Deliverables and verification

Create focused Lean modules under `formal/PCS/V2/` (with separate
test/control modules), import them in an appropriately scoped audit,
and write a concise, technical report with exact theorem names,
their statements, trusted assumptions, tests and **negative** findings.

Run and report exact commands:
`cd formal && lake build <your targets>`
`lake env lean PCS/V2/ProofGatedAudit.lean`
`cd .. && python -m unittest discover -s research/proof-gated-self-improvement-v1/tests -v`

Provide clean proof-source changes or a git patch/branch; explain
all unproved obligations and performance constraints. Do not assume
direct GitHub write access. Do not overwrite another worker's code
or change `main`/production authority unilaterally. Only claim
theorems that really kernel-check; negative results are valuable.
