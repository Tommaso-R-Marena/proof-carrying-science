# Composite scientific workflow checks (balance + units)

**Case ID:** `06_scientific_workflow_composite`
**PCS checks:** `reaction_balance`, `unit_compatible`
**License:** CC0-1.0

## Assumptions

- Composite computational claims only.

## Expected results

- Both claims COMPUTATIONALLY_SUPPORTED.

## Negative controls

- mol/L vs s unit check fails.

## Reproduction instructions

```bash
pcs certify independent_eval/scientific_falsification/casebook/cases/06_scientific_workflow_composite/manifest.json -o /tmp/pcs-sf-06_scientific_workflow_composite
pcs verify /tmp/pcs-sf-06_scientific_workflow_composite/certificate.json
```

## License metadata

```json
{
  "spdx": "CC0-1.0",
  "statement": "All authored fixtures under independent_eval/scientific_falsification are dedicated to the public domain under CC0-1.0. No human participants; no private data."
}
```
