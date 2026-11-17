# Scope — Proof-Carrying Scientific Reasoning v0

**Branch:** `research/proof_carrying_scientific_reasoning_v0`  
**Exclusive write path:** `research/proof_carrying_scientific_reasoning_v0/`  
**Base main:** `bc78660b5fac857fce3873eb6cda0445d1903da1`  
**Integration / deployment:** NONE

## In scope

- Typed scientific *argument* language with explicit claim classes and authority levels.
- Lean 4 object-level calculus: soundness, authority non-escalation, contradiction non-explosion (no ex falso), dependency recording, retraction invalidation.
- Deterministic Python reference evaluator + certificate emitter.
- Independent checker that does not import the reference evaluator.
- Adversarial tests, synthetic scientific case studies, prior-art/novelty assessment.
- Draft PR only; no production authority.

## Explicitly out of scope / do not reinvent

| Active work | Boundary |
|---|---|
| ClaimCheck #212 / assurance #216 | Do not modify; do not reimplement reported-statistic mismatch proofs |
| Incremental Certificate Revalidation #217 | Do not implement competing DAG cache/revalidation engine; only logical retraction semantics |
| Writ #209 | Do not modify claim-linked execution readback |
| EvidenceKernel #208/#210 | Do not duplicate causal selection-aware verification |
| Scientific intake/semantics/understanding #201–#203 | Study only; different problem (source grounding / interpretation) |
| Epistemic lattice / scientific authority on main | Related trust themes; do not edit; do not claim production authority |
| FoldBounds / SVB / website | Untouched |

## Non-goals

- Declaring empirical claims “scientifically true.”
- LLM-as-verifier.
- Paid APIs / Aristotle.
- Weakening CI or sealed census policies.
