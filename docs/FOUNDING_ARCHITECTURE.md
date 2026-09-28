# Founding Architecture v0.4

## 1. Company thesis

The company exists to make high-consequence computational systems independently auditable and increasingly machine-checkable.

**Long-term category:** assurance infrastructure for critical computation.  
**Initial market:** computational biopharma.  
**Initial product:** Verifiable Scientific Pipeline CI.  
**Research program:** Proof-Carrying Scientific Workflows.

The key narrowing decision is to avoid claiming that biology or chemistry themselves can be “formally verified.” The company verifies computational properties under explicit assumptions and binds those proofs/checks to provenance and empirical validation evidence.

## 2. Four evidence layers

A scientific claim may depend on four distinct classes of assurance:

1. **Formal correctness** — theorem proving/model checking/static proofs of specified properties.
2. **Computational correctness** — executable checks, tests, dimensional analysis, leakage checks, numerical bounds.
3. **Empirical validation** — comparison with observations/experiments and context-of-use evidence.
4. **Provenance/integrity** — exact data, code, environment, transformations, authorship, and hashes.

These evidence classes must never be silently conflated.

## 3. Core objects

- `Claim`: a scoped assertion whose status is derived from evidence.
- `Assumption`: an explicit condition under which a claim/evidence relation is meaningful.
- `Artifact`: immutable content-addressed data, code, model, proof, report, or result.
- `Evidence`: output from a checker/experiment/reviewer attached to one or more claims.
- `Workflow`: typed graph of artifact-transforming operations.
- `ProofObligation`: a property that an adapter or prover must discharge.
- `Certificate`: portable, independently checkable bundle binding the above.

## 4. Trust boundary

The long-term target is a very small acceptance kernel.

Untrusted components may include AI systems, workflow engines, optimizers, domain-specific analyzers, SMT/SAT solvers where proof-producing modes are available, statistical pipelines, and model generators.

They may *discover* evidence. Acceptance should depend on a smaller independently auditable checker wherever technically possible.

## 5. Platform layers

### L0 — Assurance kernel
Open specification and checker. Minimal semantics. Certificate verification. Hash/reference integrity.

### L1 — Assurance IR
Domain-neutral typed representation for claims, assumptions, artifacts, workflows, obligations, and evidence.

### L2 — Proof/check adapters
Lean, SMT proof checking, model checking, abstract interpretation, interval arithmetic, numerical error bounds, property-based testing, statistical checks, reproducibility checks.

### L3 — Domain packs
Biopharma first; chemistry, biology/omics, AI, devices, aerospace, energy, and other critical sectors later.

### L4 — Enterprise plane
Policy, orchestration, identity, permissions, audit trails, private deployment, integrations, validated release processes, dashboards, reporting, support.

## 6. Initial biopharma wedge

Target organizations making consequential decisions using custom computational workflows:

- pharmacometrics / PK-PD;
- model-informed drug development;
- computational biology and bioinformatics;
- omics/MS pipelines;
- computational chemistry;
- CRO scientific computing.

V0 does not promise full program verification. It packages and checks narrow, expensive failure modes first: data leakage, artifact provenance, environment pinning, unit/dimensional consistency, workflow integrity, selected domain invariants, and independently checkable proof artifacts.

## 7. Why this can broaden without becoming vague

The **kernel stays domain-neutral**; domain-specific meaning enters through contracts and packs. The architecture therefore supports broad long-term scope without building all sectors at once.

## 8. Relationship to existing projects

- **CertiForge** supplies the proof-carrying philosophy, small-checker trust model, formal semantics experience, and program-equivalence research.
- **CASMI/QFD** supplies a real scientific adversarial-validation case: spectacular metrics can be invalidated by evaluation artifacts, demonstrating why scientific claims need evidence graphs and automated falsification checks.
- **Proof-carrying agency / AI safety** supplies authority, state-transition, trace, and implementation/refinement verification concepts.
- Protein/biochemistry projects supply future domain workflows but should remain research-first until validation supports productization.

Existing repositories should remain independent publications/research artifacts. This project imports principles/adapters, not ownership of the underlying science.
