# Research Agenda

## Program A — Proof-Carrying Scientific Workflows

Develop a formal calculus for scientific workflows whose nodes transform typed artifacts under explicit preconditions/postconditions and emit evidence objects.

Candidate judgment:

```text
Gamma ; E |- C
```

Read: under explicit assumptions `Gamma`, evidence set `E` supports claim `C` at a specified assurance level.

Key research questions:

- compositionality: when can certificates for subworkflows be composed?
- invalidation: which claims become open when an artifact/evidence node changes?
- evidence heterogeneity: how should formal, computational, statistical, and empirical evidence coexist without conflation?
- minimal trusted computing base: which evidence formats can be independently checked?
- uncertainty: how are probabilistic/statistical claims represented without converting confidence into proof?
- refinement: when does implementation refine a declared mathematical model?

## Program B — Scientific Claim–Evidence Graphs

Represent publications/results as dependency graphs rather than prose-only assertions. Track invalidation transitively when data, code, assumptions, or proofs change.

## Program C — Verified Model Implementation

For restricted scientific DSLs, prove correspondence between declared equations and executable implementation. Initial targets: PK/PD ODE fragments, reaction networks, selected kinetic models, or dimension-safe workflow languages.

## Program D — Verified Numerical Scientific Computing

Investigate interval arithmetic, floating-point error proofs, validated numerics, and proof-producing solvers for selected scientific kernels.

## Program E — Adversarial Scientific Evaluation

Automate falsification checks for leakage, self-matching, duplicate structures/samples, split dependence, hyperparameter leakage, instability, and distribution shift. CASMI-style benchmark audits are an initial case study.

## Program F — Cross-Domain Assurance

After biopharma, test whether the same core semantics can support AI agent authority, medical-device modeling, aerospace simulations, chemistry, and other critical domains through domain packs rather than kernel forks.

## First paper target

**Proof-Carrying Scientific Workflows: A Formal Architecture for Verifiable Computational Science**

Minimum credible paper:

- formal definitions and threat model;
- explicit verification-vs-validation separation;
- executable reference kernel;
- certificate format;
- adversarial tests;
- 3 case studies (e.g. software equivalence, MS/omics evaluation, AI-policy trace);
- limitations and open obligations;
- reproducibility package.
