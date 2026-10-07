# PCS Commons — Claim Invalidation v1

This directory is the core-repository anchor for the first public PCS Commons research program.

## Real core target

PCS already has executable conservative invalidation in `pcs/impact.py`. The research backlog still explicitly asks PCS to formalize claim/evidence graph semantics and invalidation propagation. The theorem target in `docs/FORMAL_SEMANTICS_DRAFT.md` is:

> declared downstream dependencies must reopen when an upstream artifact changes; any stronger conclusion that an unreachable claim remains unaffected requires an explicit dependency-completeness assumption.

This program is intentionally separate from the executable AI-safety work.

## Authority boundary

Contributors may propose fixtures, tests, definitions, reviews, and Lean proofs. Contributor output is never authoritative merely because it was submitted. PCS reviews accepted work against the task-specific acceptance criteria; the final formal theorem must compile in Lean and pass the proof-escape audit.

The negative-control cases in `seed-corpus.json` are especially important: graph reachability can tell PCS what must reopen from *declared* dependencies, but cannot discover a dependency that was never represented.

## Public stages

- **INV-001 · L0** — add one minimal hand-checkable invalidation fixture.
- **INV-002 · L1** — build a minimal hidden-dependency counterexample.
- **INV-003 · L2 / Python** — extend the differential/adversarial corpus.
- **INV-004 · L3 / Research** — specify the dependency-completeness contract.
- **INV-005 · L4 / Review** — independently attack the corpus and semantics.
- **INV-006 · L5 / Lean** — formalize invalidation reachability soundness.

INV-005 is hard-gated on accepted INV-003 and INV-004 outputs. INV-006 is hard-gated on accepted INV-003, INV-004, and INV-005 outputs.

## Files

- `seed-corpus.json` — public seed cases and one deliberate hidden-dependency negative control.
- `reference_impact.py` — a small snapshot of the current executable invalidation semantics used by the packet.
- `fixture-schema.json` — structural requirements for corpus contributions.

## Submission

The website exposes the public task packet even while the core repository remains private during the pilot. Accepted contributions can be imported into this directory after review. AI assistance is permitted, but contributors must disclose it and independently check their work.
