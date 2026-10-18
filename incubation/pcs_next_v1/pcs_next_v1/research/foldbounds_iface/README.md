# FoldBounds interface proposal (no cross-repo import)

This is an **interface proposal only**. It does not edit external repositories
or import unreviewed results.

## Candidate externally verifiable statements

1. Finite-model free-energy inequalities under explicit Hamiltonian assumptions.
2. Certified numerical bounds for a declared energy function on a finite conformation set.

## Required inputs

- Explicit finite conformation enumeration or certified covering.
- Declared energy parameters with units.
- Proof artifact in a pinned Lean/Mathlib revision.

## Remaining physical assumptions

- Force-field adequacy is scientific, not formal.
- Temperature/ensemble assumptions remain undischarged unless formalized.

## Artifact protocol sketch

`foldbounds-evidence-v1` carrying: model hash, statement id, Lean theorem name,
kernel receipt, receiver policy hash.

## Independent replay

Receiver pins toolchain + theorem statement hash and reruns `lake build` /
checker; producer PASS ignored.
