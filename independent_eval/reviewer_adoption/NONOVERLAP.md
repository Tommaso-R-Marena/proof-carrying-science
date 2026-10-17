# Non-overlap — Workstream D (`reviewer_adoption`)

| Item | Value |
| --- | --- |
| Branch | `feature/independent-eval-reviewer-adoption-c8bb` |
| Base | `main` |
| Writable scope | `independent_eval/reviewer_adoption/**` only |

## Explicitly out of scope (do not modify)

- `formal/**`
- `research/**`
- `pcs/**`
- `site/**`
- `.github/**`
- Repository-root `tests/**`
- Lockfiles (`requirements-*.lock`, `uv.lock`, etc.)
- PR #117 (research proof-gated self-improvement)
- PR #120 (independent scientific pilot)
- Top-level `independent_eval/__init__.py` (avoid cross-PR overlap; namespace package import from repo root)

## Sibling workstreams (no file overlap)

| Workstream | Path |
| --- | --- |
| A — protocol & adversarial | `independent_eval/protocol_adversarial/` |
| B — scientific falsification | `independent_eval/scientific_falsification/` |
| C — reproducibility & TCB | `independent_eval/repro_tcb/` |
| D — reviewer & adoption (this) | `independent_eval/reviewer_adoption/` |

## Tasks owned here

- **15** Offline reviewer workbench (`workbench/`) — inspect-only; never ACCEPT/PASS
- **16** Blind challenge (`blind_challenge/`) — synthetic cases + scorer; no invented human results
- **17** Tabletop (`tabletop/`) — offline only; no live credentials/infra
- **18** External lab kit (`external_lab/`) — package + burden tracker; no completed-validation claim
