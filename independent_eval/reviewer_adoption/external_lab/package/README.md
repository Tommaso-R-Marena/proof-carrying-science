# External laboratory challenge package (Task 18)

| Document | Purpose |
| --- | --- |
| `SETUP.md` | Lab environment provisioning |
| `WORKFLOW.md` | End-to-end sequence + read-only example pointers |
| `VERIFY.md` | Inspect evidence (non-authority) |
| `REPRO.md` | Attempt reconstruction; record divergences |
| `LIMITATIONS.md` | Explicit non-claims |
| `TROUBLESHOOTING.md` | Common blockers |
| `SUCCESS_FAILURE.md` | Dry-run success vs failure criteria |
| `CHECKLIST.json` | Machine-readable steps for `burden_tracker` |

Track manual effort:

```bash
python3 -m independent_eval.reviewer_adoption.external_lab.burden_tracker \
  --package independent_eval/reviewer_adoption/external_lab/package \
  --log /tmp/pcs-external-lab-burden.jsonl --list-steps
```
