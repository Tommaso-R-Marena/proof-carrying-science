# Independence audit

## Attempted preferred repository

- Target: `Tommaso-R-Marena/pcs-certified-numerics` (private)
- Result: **403** — personal access token cannot create repositories
- Decision: fallback isolation inside PCS worktree

## Fallback isolation

- Worktree: `/home/ubuntu/pcs-certified-numerics-worktree`
- Branch: `research/pcs-certified-numerics-v1-20261017`
- Write namespace: `incubation/pcs_certified_numerics_v1/` **only**
- Forbidden: `incubation/pcs_next_v1/`, `pcs/`, `formal/` (PCS), website repo

## Checks

- `scripts/noninterference_check.sh` before push
- No PCS submodule links
- Own Lean lake packages under this directory’s `.lake/`
- Own Python venv `~/.venvs/pcs-certified-numerics`
- Own lake cache `~/.cache/certnum-lake`

## Sibling repos

- `/agent/repos/proof-carrying-science` main checkout: not modified for feature work
- `/agent/repos/proof-carrying-science-site`: not modified
