# Certificate format `pcca-cert-v1`

```json
{
  "format": "pcca-cert-v1",
  "kind": "conservation_law | trajectory_conservation | conservation_refutation",
  "claim": { "...": "..." },
  "witness": { "...": "..." },
  "limitations": ["..."],
  "sha256": "<hash of canonical claim body without this field>"
}
```

## Kinds

### `conservation_law`

Claim contains `species`, `reactions`, rational `matrix` (rows = species),
and `weights`. Checker accepts iff `weights · column_r = 0` for every reaction.
Optional witness sample fire must preserve the pool.

### `trajectory_conservation`

Additionally contains `states` (length T+1) and `xis` (length T). Checker
accepts iff each consecutive pair equals `fire(S, ξ_k, x_k)` **and** the pool is
constant. Producer-declared PASS fields are rejected.

### `conservation_refutation`

Accepted only when weights demonstrably fail to annihilate `S`. Used for
adversarial mass-leak evidence.

## Hard rejects

- Wrong `format` or unknown `kind`
- Producer `verdict` / `pass` / `accepted` fields
- Executable fields (`lean_source`, `python_code`, `shell`, …)
- Boolean or non-canonical rationals
- Dimension mismatches

## Authority

Certificates never set `pcs_authority` or `scientific_acceptance` to true.
