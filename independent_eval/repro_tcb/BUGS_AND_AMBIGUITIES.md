# Bugs and ambiguities — Workstream C

## Ambiguities

1. **Identical-archive replay vs regeneration** — Regenerated ZIP bytes may differ from an original archive even when member digests match, unless a canonical encoder is used. The harness records both identities explicitly.
2. **TCB classification is an audit judgment** — Labels such as `kernel-proved` / `externally trusted` are derived from read-only inspection of `formal/` and `pcs/` documentation/code references; they are not Lean kernel certificates of the atlas itself.
3. **Cross-Python sampling** — Available interpreters on a host are opportunistic; absence of an alternate interpreter is recorded, not treated as a pass.

## Observed behaviors

1. Canonical re-pack of fixture members yields a stable archive digest across clean temp directories on this host.
2. Non-canonical ZIP encoding produces a different archive digest with identical member digests (expected).
3. Traceability auditor flags claims lacking commit/theorem/test/hash/assumption links without inventing support.

## Non-findings

- No production `pcs/` or `formal/` files were modified.
- No claim that cross-environment byte identity holds for regenerated production certificates without measurement.
