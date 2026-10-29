# Aristotle v4 — self-contained Lean-only research assignment (17 October 2026)

**This file travels *inside the attached formal/ folder*. Do not request GitHub
access, the surrounding repository, Python scripts, local user directories, or
non-attached files. All relevant starting code is already in this folder.**

## Goal

Advance the formal foundations of a recursively proof-gated, neural-symbolic
self-modification mechanism. Seek genuinely strong theorems and substantive
nontrivial executable witnesses. Rigorously separate certified properties of
a mathematical objective from real-world intelligence, performance, or
deployment security, none of which follow automatically.

## Toolchain and working root

Treat the directory containing **this file**, `lakefile.toml`,
`lake-manifest.json`, `lean-toolchain`, and `PCS/` as the project root.
Use the pinned Lean **4.28.0** toolchain. Do not assume Mathlib; the project's
Lake dependencies are exactly those attached. Do not fetch unrelated packages.
Build the original targets first:

```bash
cd <attached-formal-folder>
lake build PCS.V2.ProofGatedSelfImprovement PCS.V2.ProofGatedArtifacts PCS.V2.ProofGatedPromotion PCS.V2.ProofGatedInference PCS.V2.ProofGatedSymbolic PCS.V2.ProofGatedMultilayer
lake env lean PCS/V2/ProofGatedAudit.lean
```

If `lake` / `elan` is inaccessible, report exactly what is unavailable and
use the strongest execution environment provided. Never claim a build was run
without having run it.

## Existing verified sources to READ FIRST

- `PCS/V2/ProofGatedSelfImprovement.lean`: exact single-neuron model;
  gate soundness, preservation, strict loss, arbitrary strategies, certified
  trace length bounds, and an out-of-corpus counterexample.
- `PCS/V2/ProofGatedArtifacts.lean`: canonical `PGSI1|R|w|b` or
  `PGSI1|L|w|b` string protocol, `decode_canonical`,
  `decode_bounded`, `acceptWire_sound`. It does **not** yet prove full
  decode-after-encode roundtrip for arbitrary bounded neurons.
- `PCS/V2/ProofGatedPromotion.lean`: pure exact-text compare-and-swap
  state machine, stale state rejection, soundness of accepted promotion.
- `PCS/V2/ProofGatedInference.lean`: exact canonical-artifact inference
  semantics and preservation of previously correct predictions on commit.
- `PCS/V2/ProofGatedSymbolic.lean`: universally valid semantic rewrites,
  decreasing expression-node cost.
- `PCS/V2/ProofGatedMultilayer.lean`: **new** exact integer network with
  two ReLU hidden neurons and affine output, seven bounded integer weights,
  boundedness precondition, executable sound acceptance, strict improvement,
  arbitrary-strategy invariants, swapping hidden units without changing
  semantics, and TWO verified updates reducing benchmark loss
  `26 -> 10 -> 0`. Do not redo those established theorems.
- `PCS/V2/ProofGatedAudit.lean`: source axiom audit. Extend it for every
  mathematically interesting new result.

## Priority A — full serialization correctness, injectivity and inference

Develop checked auxiliary lemmas for Lean core's signed integer decimal
rendering/parser and string delimiter protocol. **Prove**, without
assumptions disguised as axioms:

```lean
theorem decode_encode_of_bounded (m : Neuron)
    (h : valid m = true) : decode (encode m) = some m := ...
```

Here `valid` is in `PCS.V2.ProofGatedArtifacts`, so ensure correct
namespacing. If exact source notation requires adjustments, state them.
Derive `encode` injectivity on bounded models and
`infer (encode m) x = some (predict m x)` for ALL `x : Int`.
Aim to characterize decoding rejection of noncanonical forms and boundary
weights. Avoid proving only a finite list of illustrative values and
claiming a universal theorem.

## Priority B — substantial generalization of the two-hidden-unit network

The two-hidden-unit model already has a sound gate and nontrivial certified
two-generation witnesses. Build something **beyond** it:

- Preferred: a bounded, versioned family of exact integer or fixed-point
  multilayer networks parameterized by a finite hidden width or depth
  (e.g. `Fin n` vectors), with a total mathematical evaluator.
  Use no floating-point arithmetic without an explicit and formally
  modeled rounding semantics.
- Implement a finite-domain executable acceptance decision that verifies
  preservation of all previously correct cases, attainment of at least
  one newly correct case, strict decrease in natural-valued error, and
  parameter/range validity.
- Prove acceptance soundness; arbitrary accepted-trace correctness
  preservation and bounded length; failure to mutate on rejection;
  invariants under an arbitrary sequence of changing or adversarial
  proposal strategies.
- Include at least one actual checked improvement chain on a network
  using MULTIPLE hidden units, and a blocked regression/invalid parameter
  fixture. Reuse the existing network as regression test, not as a
  substitute for the generalization.
- Where tractable, prove a semantics-preserving structure transform
  (hidden-neuron permutation, adding an exactly zero-output hidden unit,
  or program rewrite) that holds on ALL inputs, not only the corpus.
- Clearly distinguish a theorem of fixed-policy preservation from
  the unsupported assertion that the model's ability to invent future
  improvements will accelerate or improve.

If full arbitrary-depth generalization cannot be completed, prove a
smaller genuinely general mathematical lemma and document precise
remaining proof obligations rather than producing partial unsound code.

## Priority C — complete model-artifact-to-decision formal refinement

Within pure Lean, specify and prove relations between (1) canonical
serialized model, (2) decoded mathematical parameters, (3) evaluation,
(4) checker decision, and (5) successful exact-identity generation commit.
Seek a formal statement that binds an accepted serialized candidate to
the SAME encoded mathematical model whose predictions are then executed.
For a network extension, specify a versioned canonical encoding and a
decoder. Prefer a proof of roundtrip plus parser soundness and complete
coverage of accepted certificate fields.

**Crucial:** OS filesystems, SHA-256 collision resistance, atomic disk writes,
race freedom, executable authenticity, cryptographic signatures,
anti-rollback anchoring, and an external Python/GPU runtime are NOT proved
merely by Lean soundness. If you introduce an abstract host model, identify
the assumptions in the theorem signature as ordinary hypotheses, not new
global axioms. Mark which aspects are truly formalized and which are open.

## Priority D — limits, adversarial falsification and liveness

- Derive a formal finite-improvement bound for accepted traces as a
  consequence of strict decrease in a Nat-valued potential.
- Identify counterexamples where accepted on-corpus updates worsen the
  SAME target on held-out inputs. Existing single-neuron theorem is a
  starting point; analyze whether an analogous multilayer case exists.
- Investigate whether fixed finite correctness-frontier requirements
  can trap a local proposer despite a beneficial larger edit. Do not
  claim everlasting improvement is possible under the bounded loss.
- Explain why a certificate of a fixed benchmark objective does NOT
  imply improvements in general reasoning, scientific correctness,
  or unrestricted ability.

## Nonnegotiable proof quality

- No `sorry`, `admit`, `unsafe`, `native_decide` as a replacement
  for kernel soundness without explicitly discussing its trusted base,
  no new axioms, no `@[implemented_by]` or invented compiler correctness.
- Use the standard Lean 4.28.0 environment; any built-in foundations
  must be reported by `#print axioms`. Do not claim unconditional
  independence from `propext`, `Classical.choice`, `Quot.sound` if
  the theorem uses them.
- Do not modify original production-sensitive PCS authority files.
  Add isolated Lean modules under `PCS/V2/` and extend only the
  research axiom audit as needed.
- Build from the **attached** folder and report exactly:
  commands, exit codes, theorem names and full statements, axiom
  dependencies, positive/negative tests, missing proof obligations,
  and any unsupported implicit claims.
- Return the COMPLETE changed Lean files and report in your
  deliverables. You may give a patch/zip. You do not need any remote
  GitHub permission and must not silently alter the user's other files.

## Success criterion

A real advance is at least one **new general, kernel-checked theorem**
about serialization/refinement, larger quantized models, semantic
self-modification or trusted decision composition, supported by
nontrivial computational witnesses and an honest threat/limitation
analysis. We favor a smaller rigorously proven result over a grander
unsupported claim.
