# Proposed CI integration (DO NOT APPLY in this PR)

Add a non-required job:

```yaml
# conceptual only — live in owned namespace proposal
pcs-next-validate:
  steps:
    - run: python incubation/pcs_next_v1/scripts/validate_all.py
```

Do not alter required checks on `main` without coordination.
