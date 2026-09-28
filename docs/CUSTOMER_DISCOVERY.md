# Customer Discovery Plan

## First hypothesis

Computational biopharma teams will pay to reduce the risk that custom scientific code, model implementations, data splits, provenance, and validation packages contain errors that undermine consequential R&D or regulatory decisions.

## First interview roles

- pharmacometricians / clinical pharmacology modeling leads;
- computational biology leaders;
- bioinformatics/omics platform leads;
- computational chemistry leaders;
- scientific software/quality leads;
- CRO modeling leads;
- regulatory-science / model-governance personnel.

## Do not pitch first

Ask about a recent expensive computational failure, review bottleneck, model handoff, reproducibility incident, regulatory documentation burden, or internal audit.

## Core questions

- Which scientific computations would be most damaging if subtly wrong?
- How do you verify user-generated analysis code today?
- How are model equations tied to their implementation?
- What evidence must survive handoff between scientists, quality, and regulators?
- How often do environment/data/version mismatches occur?
- What classes of validation are manual?
- What would an independent machine-checkable evidence bundle need to contain to be useful?
- Who owns the budget for solving this?

## Falsification criteria

Reconsider the initial wedge if, after ~20-30 strong interviews:

- errors are not painful/expensive enough to fund prevention;
- no identifiable buyer owns the problem;
- current validation tooling already solves the problem adequately;
- integration burden overwhelms perceived benefit;
- customers consistently value generic provenance but not stronger assurance.
