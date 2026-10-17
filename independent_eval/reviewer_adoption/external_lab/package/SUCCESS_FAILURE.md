# External lab — SUCCESS / FAILURE criteria

## Success (lab dry-run)

- Environment provisioned per `SETUP.md`
- Workbench report generated with explicit non-authority disclaimer
- At least one VERIFY pass recorded with hash comparison notes
- Burden log JSONL contains dated steps with minutes
- No live credentials or infrastructure modified
- Outcome write-up states whether reconstruction matched or diverged

## Failure / incomplete (still useful)

- Cannot provision Python environment under lab policy
- Evidence digests mismatch and no trusted alternate source
- Attempted live credential changes (exercise failure — stop)
- Claiming PCS ACCEPT/PASS from local tools (protocol failure — retract)

## Forbidden claims

| Claim | Allowed? |
| --- | --- |
| "External lab validation of PCS is complete" | **No** (unless separately stewarded) |
| "Workbench ACCEPTed the bundle" | **No** |
| "Human blind-review accuracy is X%" based only on fixtures | **No** |

Record honest incompleteness; it is a valid evaluation outcome.
