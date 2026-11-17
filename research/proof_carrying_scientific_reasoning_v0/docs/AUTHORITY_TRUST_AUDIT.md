# Authority and trust-boundary audit

## Declared vs established

| Field | Meaning | Trusted? |
|---|---|---|
| `declared_authority` on premises | Author-supplied label | **No** |
| Reconstructed `declared_authority` on judgments | Meet of cited declared labels | Deterministic from untrusted inputs |
| `math_established` | Kernel/external attestation that content is math-verified | Always `false` for Hyp in v1 |

Finding F: a certificate may declare `mathVerified` on an empirical atom; Hyp accepts the
**declaration** but sets `math_established=false`. Consumers must not treat declared math
as established verification.

## Meet vs max (Finding C)

Spec and Lean/Python v1 use **meet** (rank-min + commutative tie-break). Max-rank bounds are forbidden.

## Rank ties (Finding G)

`assumption` and `empiricalAsserted` share rank; commutative `tie` order selects a unique meet.
Equal ranks ≠ equal classifications.

## External attestation (deferred)

Establishing `math_established=true` would require an independently qualified attestation
boundary (e.g., Lean kernel receipt binding). Not implemented in v1 — trust boundary explicit.
