# Owned namespace: `incubation/pcs_next_v1/`

This directory is the exclusive write boundary for branch
`research/pcs-next-integrated-assurance-v1-20261017`.

## Guarantees established

1. **Git isolation** — dedicated branch and worktree rooted at recorded `origin/main`.
2. **File ownership** — all intentional edits confined to this namespace (enforced by `scripts/check_noninterference.py`).

## Guarantees not established by isolation alone

3. Runtime isolation from production credentials
4. Cryptographic authority of PCS production signing keys
5. Semantic correctness of bridged production verifiers
6. Scientific validity of domain claims
7. Independent external-lab evaluation
8. Production integration / merge authorization

See `docs/TRUST_BOUNDARY_ANALYSIS.md` and `docs/TCB_INVENTORY.md`.
