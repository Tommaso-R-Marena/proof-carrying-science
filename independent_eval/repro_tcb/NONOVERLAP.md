# Non-overlap — Workstream C (`repro_tcb`)

| Item | Value |
| --- | --- |
| Branch | `feature/independent-eval-repro-tcb-c8bb` |
| Base | `main` |
| Writable scope | `independent_eval/repro_tcb/**` only |
| Optional shared doc | `independent_eval/README.md` (append-only / non-conflicting) |

## Explicitly out of scope (do not modify)

- `formal/**` — Lean sources; Task 13 is **read-only** audit only
- `research/**`
- `pcs/**` — production Python package
- `site/**`
- `.github/**`
- Existing repository tests under `tests/**`
- Lockfiles (`requirements-*.lock`, `uv.lock`, etc.)
- PR #117 (research proof-gated self-improvement)
- PR #120 (independent scientific pilot)

## Sibling workstreams (no file overlap)

| Workstream | Path |
| --- | --- |
| A — protocol & adversarial | `independent_eval/protocol_adversarial/` |
| B — scientific falsification | `independent_eval/scientific_falsification/` |
| C — reproducibility & TCB (this) | `independent_eval/repro_tcb/` |
| D — reviewer & adoption | `independent_eval/reviewer_adoption/` |

## Tasks owned here

- **12** Cross-environment reconstruction harness
- **13** Trusted computing base dependency atlas
- **14** Independent evidence traceability auditor
