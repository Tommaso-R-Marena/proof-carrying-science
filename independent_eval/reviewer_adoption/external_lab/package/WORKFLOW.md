# External lab — WORKFLOW

## Representative workflow (read-only pointer)

Do **not** copy large example trees into this package. Use the repository’s
existing examples as a read-only reference:

- Example workflows: `examples/` at the repository root (read-only)
- Workbench sample evidence: `independent_eval/reviewer_adoption/workbench/fixtures/sample_bundle/`
- Blind challenge materials: `independent_eval/reviewer_adoption/blind_challenge/`
- Tabletop scenarios: `independent_eval/reviewer_adoption/tabletop/scenarios/`

## Suggested sequence

1. **Inspect** a fixture bundle with the offline workbench (Task 15).
2. **Verify** hashes / receipt fields per `VERIFY.md` (inspection only).
3. **Reproduce** what you can under `REPRO.md`; record divergences.
4. **Classify** success/failure using `SUCCESS_FAILURE.md` without inventing authority.
5. Log each manual step with `burden_tracker.py`.

## Minimal pointer script (documentation only)

```text
repo_root/
  examples/                          ← read-only reference for domain workflows
  independent_eval/reviewer_adoption/
    workbench/fixtures/sample_bundle ← synthetic evidence for dry runs
    external_lab/package/            ← this kit
```
