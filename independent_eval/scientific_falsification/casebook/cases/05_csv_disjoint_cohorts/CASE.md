# CSV key disjointness for train/test cohorts

**Case ID:** `05_csv_disjoint_cohorts`
**PCS checks:** `csv_disjoint`
**License:** CC0-1.0

## Assumptions

- Opaque subject IDs; no sampling validity.

## Expected results

- Disjoint train/test PASS.

## Negative controls

- Overlapping subject_id FAIL.

## Reproduction instructions

```bash
pcs certify independent_eval/scientific_falsification/casebook/cases/05_csv_disjoint_cohorts/manifest.json -o /tmp/pcs-sf-05_csv_disjoint_cohorts
pcs verify /tmp/pcs-sf-05_csv_disjoint_cohorts/certificate.json
```

## License metadata

```json
{
  "spdx": "CC0-1.0",
  "statement": "All authored fixtures under independent_eval/scientific_falsification are dedicated to the public domain under CC0-1.0. No human participants; no private data."
}
```
