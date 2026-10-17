# Non-overlap report — Workstream A

Branch: `feature/independent-eval-protocol-adversarial-c8bb`  
Base: `origin/main`

## Writable scope

All changes are under:

- `independent_eval/README.md`
- `independent_eval/protocol_adversarial/**`

## Forbidden paths (not modified)

- `formal/**`
- `research/**`
- `pcs/**`
- `site/**`
- `.github/**`
- existing core tests, lockfiles, policies, release gates, production scripts
- PR #117 / PR #120 branches

## Overlap check

Re-run before merge review:

```bash
git diff --name-only origin/main...HEAD
```

Expected: only `independent_eval/**` paths.
