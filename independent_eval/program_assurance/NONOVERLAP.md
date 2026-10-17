# Non-overlap — Workstream E (`program_assurance`)

| Item | Value |
| --- | --- |
| Branch | `feature/independent-eval-program-assurance-c8bb` |
| Base | `main` |
| Writable scope | `independent_eval/program_assurance/**` only |

## Explicitly out of scope (do not modify)

- `independent_eval/README.md` — owned by Workstream A PR
- `formal/**`
- `research/**`
- `pcs/**`
- `site/**`
- `.github/**`
- Repository-root `tests/**`
- Lockfiles (`requirements-*.lock`, `uv.lock`, etc.)
- PR #117 (research proof-gated self-improvement)
- PR #120 (`feature/independent-scientific-pilot-c8bb`) — must remain non-overlapping
- Sibling workstream trees (do not create or edit their content):
  - `independent_eval/protocol_adversarial/**`
  - `independent_eval/scientific_falsification/**`
  - `independent_eval/repro_tcb/**`
  - `independent_eval/reviewer_adoption/**`

## Sibling workstreams (no file overlap)

| Workstream | Path | Branch |
| --- | --- | --- |
| A — protocol & adversarial | `independent_eval/protocol_adversarial/` | `feature/independent-eval-protocol-adversarial-c8bb` |
| B — scientific falsification | `independent_eval/scientific_falsification/` | `feature/independent-eval-scientific-falsification-c8bb` |
| C — reproducibility & TCB | `independent_eval/repro_tcb/` | `feature/independent-eval-repro-tcb-c8bb` |
| D — reviewer & adoption | `independent_eval/reviewer_adoption/` | `feature/independent-eval-reviewer-adoption-c8bb` |
| E — program assurance (this) | `independent_eval/program_assurance/` | `feature/independent-eval-program-assurance-c8bb` |
| Pilot (PR #120) | (pilot paths; not this tree) | `feature/independent-scientific-pilot-c8bb` |

## Tasks owned here

- Case-insensitive path collision scanner
- Branch nonoverlap auditor (read-only git)
- Program inventory aggregator (PRESENT / MISSING only)
- Prioritized proposals catalog (proposals ≠ completed claims)
- Pytest coverage for scanner + auditor (+ inventory/proposals helpers)
