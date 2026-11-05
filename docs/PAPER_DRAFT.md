# Paper Draft v0.4

## Working title

**Proof-Carrying Scientific Workflows: A Formal Architecture for Verifiable Computational Science**

## Draft abstract

Computational results increasingly influence scientific and regulatory decisions, yet the evidentiary chain connecting a reported claim to data, code, model assumptions, software environments, validation procedures, and formal guarantees is commonly fragmented across prose, scripts, and platform-specific provenance records. We propose **proof-carrying scientific workflows**, an architecture in which scoped scientific-computational claims are packaged with explicit assumptions, content-addressed artifacts, machine-readable workflow dependencies, and independently replayable evidence. The framework deliberately separates formal verification, finite computational checking, empirical/statistical validation, and provenance rather than collapsing these categories into a single notion of correctness. We define a claim–evidence representation, a small acceptance-kernel direction, compositional and invalidation semantics, and an executable reference implementation that replays built-in evidence rather than trusting producer-declared outcomes. A computational-biopharma prototype demonstrates subject-level leakage checks, dimensional compatibility, chemical-balance constraints, artifact integrity, workflow validation, evidence-derived claim status, transitive claim invalidation, and a restricted one-compartment IV-bolus PK/direct-Emax PD contract with independent equation replay. An initial adversarial suite targets artifact substitution, forged evidence outcomes, semantic evidence misbinding, workflow-summary tampering, path traversal, and related attacks. The broader research program is to connect restricted scientific workflow languages to proof assistants and proof-producing analyzers while retaining empirical validation as a distinct context-of-use obligation.

## Main contributions to target

1. **Typed claim–evidence model.** A scientific-computational claim is not merely text; it includes a machine-readable predicate and explicit evidence obligations.
2. **Evidence-class separation.** Formal, computational, empirical/statistical, and provenance evidence have distinct semantics and cannot be silently substituted.
3. **Small-checker architecture.** Untrusted producers search for evidence; acceptance relies on independently replayable/checkable artifacts.
4. **Claim invalidation graph.** Changes to data/code/artifacts conservatively reopen downstream claims.
5. **Domain-neutral kernel, domain-specific packs.** The core remains stable while scientific meaning enters through typed predicates and adapters.
6. **Adversarial reference implementation.** Demonstrate the architecture against concrete forgery/misbinding attacks.

## Theorem targets

- Formal acceptance requires independently accepted formal evidence.
- `UNVERIFIED` required evidence cannot discharge an obligation.
- Failed required evidence prevents accepted claim status.
- Claim assessment is deterministic under normalized claim/evidence state.
- Workflow acceptance implies acyclicity and unique producers.
- Adapter-soundness + evidence composition yields compositional support.
- Under dependency completeness, changed upstream artifacts force reopening of every reachable dependent claim.

## Case-study plan and publication firewall

The first paper version should stand on **independent synthetic/public examples**, including the restricted PK/PD adapter. Existing unpublished projects are not required for the framework paper and should retain their own novelty.

Only after the relevant constituent papers have citable public versions should the synthesis add adapters such as:

- a program-transformation proof artifact from CertiForge, without duplicating its internal novelty;
- a mass-spectrometry evaluation-integrity case study derived from already-published CASMI/QFD work;
- an AI-agent authority/trace case study derived from already-published proof-carrying-agency work.

This ordering lets each constituent project be judged and published on its own contributions before the synthesis demonstrates the common assurance structure. See `PUBLICATION_FIREWALL.md`.

## Evaluation metrics

- false accepts under adversarial mutation;
- false rejects on valid packages;
- replay time;
- certificate/package size;
- fraction of claim dependencies machine-readable;
- human review time saved;
- cross-implementation hash/check agreement;
- invalidation precision/recall under injected dependency changes.

## Claims explicitly out of scope

- Formal verification proves that a biological model is true.
- A certificate replaces empirical validation.
- A certificate automatically confers regulatory compliance.
- Arbitrary Python/R/C++ scientific programs are fully verified.
- Initial adversarial tests constitute a security proof.
