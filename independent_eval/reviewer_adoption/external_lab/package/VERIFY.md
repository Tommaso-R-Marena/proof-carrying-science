# External lab — VERIFY

Verification here means **inspecting reported evidence**, not issuing PCS authority.

## Checklist

1. Generate a workbench HTML report from a local evidence directory.
2. Confirm the report states `workbench_issues_accept = false` / non-authority disclaimer.
3. Compare artifact SHA-256 values in the certificate against files on disk.
4. Record receipt fields (`valid`, claim decisions) as *reported*, not decided by you.
5. Note any missing `LIMITATIONS.md` or mismatched digests.

## Commands

```bash
python3 -m independent_eval.reviewer_adoption.workbench.generate_report \
  --evidence independent_eval/reviewer_adoption/workbench/fixtures/sample_bundle \
  --out /tmp/lab-verify-report.html
```

## Explicit non-claims

- Matching hashes ≠ scientific validity.
- A receipt with `valid: true` in a fixture is synthetic unless independently confirmed.
- This kit does not replace Lean / PCS authority.
