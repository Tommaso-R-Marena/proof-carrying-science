# Publication sequence and synthesis policy

The company/research architecture is a **synthesis layer**, not a replacement for the constituent research papers.

## Stage 1 — constituent research stands on its own

Before this repository imports project-specific algorithms, proofs, benchmark findings, or biological conclusions, the relevant project should be frozen for authorship/IP review and pursued as its own paper/preprint where appropriate. Current examples include CertiForge, CASMI/QFD, proof-carrying AI-safety work, protein/biochemistry projects, and the independent mathematics programs.

The purpose is both scientific and strategic: each contribution should be evaluated on its own novelty rather than first appearing only as a component of a broader startup framework.

## Stage 2 — framework paper uses independent examples

The first Proof-Carrying Scientific Workflows paper can be developed using only generic assurance semantics plus synthetic/public examples. The restricted one-compartment IV-bolus PK/direct-Emax PD adapter is intentionally designed for this role.

This stage may publish the *general ideas* of explicit assumptions, typed evidence classes, claim/evidence binding, replay, provenance, and invalidation without disclosing the unpublished mechanisms or results of the constituent projects.

## Stage 3 — post-publication adapters

After a constituent project has a citable public version and its IP status is clear, add an adapter rather than copying its internals. The adapter should consume the project's public proof/evidence artifact and express what assurance claim that artifact can discharge.

Examples:

- CertiForge artifact → program-transformation/equivalence evidence adapter;
- published MS work → evaluation-integrity / spectral-workflow assurance adapter;
- published agent-safety work → authority/trace assurance adapter;
- published protein pipeline → provenance/model/experimental-validation adapter.

## Stage 4 — synthesis research

Only then should the broad synthesis paper make comparative claims about the common architecture across sectors. The scientific thesis is that these domains share reusable **assurance structure**, not that their scientific contents collapse into one theory.

## Permanent boundary

Formal verification establishes properties relative to a specification and assumptions. Empirical validation establishes whether a model is adequate for a real context of use. The synthesis must never erase that distinction.
