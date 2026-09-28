# Product v0.1 — Verifiable Scientific Pipeline CI

## Customer promise

For a declared computational workflow, produce a portable evidence package showing exactly what ran, what assumptions were declared, which automated checks passed or failed, and which obligations remain open.

## CLI target

```text
pcs certify manifest.json -o evidence/
pcs verify evidence/certificate.json
pcs inspect evidence/certificate.json
```

## First failure classes to catch

- dataset identity mistakes and train/test overlap;
- unpinned or changed artifacts;
- broken provenance chains;
- workflow cycles / ambiguous multiple producers;
- unit/dimensional mismatches;
- simple chemical stoichiometry violations;
- selected numerical/domain invariants;
- missing proof/validation obligations;
- certificate tampering.

## Explicit non-goals for v0.1

- proving arbitrary Python/R/C++ correct;
- claiming model biological/clinical validity from code checks;
- replacing GxP/quality systems;
- acting as a regulator;
- executing arbitrary third-party proof-checker commands inside the trusted verifier.

## Next adapters

1. Lean proof artifact checker / replay.
2. SMT proof-producing adapter with independently checkable proof format where feasible.
3. container/environment/SBOM capture.
4. numerical interval/error-bound adapter.
5. PK/PD dimensional and ODE contract adapter.
6. omics/MS leakage + replicate-aware split adapter.
7. GitHub CI integration.
8. signed certificates + append-only transparency log.
