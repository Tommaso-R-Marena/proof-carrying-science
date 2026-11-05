# External lab — TROUBLESHOOTING

| Symptom | Likely cause | Action |
| --- | --- | --- |
| `ModuleNotFoundError: independent_eval` | Running outside repo root | `cd` to repo root; ensure `independent_eval/reviewer_adoption` is present |
| Workbench finds no certificate | Wrong `--evidence` path | Point at a directory containing `certificate.json` |
| Hash mismatch on artifacts | Corrupt copy or wrong file | Re-copy from source; do not disable checks |
| Blind score `missing_response` | Response sheet incomplete | Fill all `case_id` entries; do not invent human results |
| Tabletop exit code 2 | Forbidden live-action markers | Remove live credential/infra actions from response sheet |
| Burden tracker unknown step | Typo in `--step` | Run `--list-steps` and use a printed id |

If blocked more than a lab shift, log minutes under `--step troubleshoot` and
escalate to the PCS evaluation steward — do not bypass integrity checks.
