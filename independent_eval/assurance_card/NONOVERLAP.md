# Non-overlap — Workstream F (`assurance_card`)

| Item | Value |
| --- | --- |
| Branch | `feature/independent-eval-assurance-card-c8bb` |
| Base | `main` |
| Writable scope | `independent_eval/assurance_card/**` only |

## Explicitly out of scope (do not modify)

- `independent_eval/README.md` — owned by Workstream A PR
- `formal/**`
- `research/**`
- `pcs/**`
- `site/**`
- `.github/**`
- Repository-root `tests/**` / `main` package trees
- Lockfiles (`requirements-*.lock`, `uv.lock`, etc.)
- Sibling workstream trees (do not create or edit their content):
  - `independent_eval/protocol_adversarial/**`
  - `independent_eval/scientific_falsification/**`
  - `independent_eval/repro_tcb/**`
  - `independent_eval/reviewer_adoption/**`
  - `independent_eval/program_assurance/**`

## Sibling workstreams (no file overlap)

| Workstream | Path | Branch |
| --- | --- | --- |
| A — protocol & adversarial | `independent_eval/protocol_adversarial/` | `feature/independent-eval-protocol-adversarial-c8bb` |
| B — scientific falsification | `independent_eval/scientific_falsification/` | `feature/independent-eval-scientific-falsification-c8bb` |
| C — reproducibility & TCB | `independent_eval/repro_tcb/` | `feature/independent-eval-repro-tcb-c8bb` |
| D — reviewer & adoption | `independent_eval/reviewer_adoption/` | `feature/independent-eval-reviewer-adoption-c8bb` |
| E — program assurance | `independent_eval/program_assurance/` | `feature/independent-eval-program-assurance-c8bb` |
| F — offline assurance card (this) | `independent_eval/assurance_card/` | `feature/independent-eval-assurance-card-c8bb` |

## Tasks owned here

- Offline Assurance Card builder (JSON + static HTML)
- Authority-lane black-box `pcs verify` recorder
- Non-authority inspection_class lattice + claim parser
- Content-addressed `card_integrity` seal + `schema/pcs-assurance-card-v1.json`
- Optional non-authority `--attach-results` program_context digests (ABSENT ≠ PASS)
- Fresh CC0 synthetic fixtures + optional pkpd certify→verify demo test
- Docs: README, NONOVERLAP, TEST_INVENTORY, TECHNICAL_REPORT, BUGS_AND_AMBIGUITIES
