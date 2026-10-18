# Certificate specification (`certnum-cert-v1`)

Independent of PCS production assurance certificates.

```json
{
  "format": "certnum-cert-v1",
  "kind": "interval_enclosure",
  "claim": { },
  "witness": { },
  "meta": { }
}
```

## Kinds

| Kind | Claim meaning | Checker action |
|---|---|---|
| `interval_enclosure` | ∀x∈box, f(x)∈enclosure (via natural/MV extension soundness) | Re-eval enclosure; require recomputed ⊆ claimed; check samples |
| `root_isolation` | Listed intervals have EXCLUDED/EXISTS/UNIQUE status | Reclassify each interval |
| `global_optimization` | L ≤ min f ≤ U on domain with coverage | Recompute leaf lowers; check incumbent |
| `linear_residual` | ‖Ax̂−b‖_∞ ≤ bound | Recompute residual |
| `markov_step` | π′ = πP exactly | Recompute |
| `thermo_partition` | Z ∈ claimed interval | Recompute enum/bins |
| `ode_linear_scalar` | x(t)∈enclosure for x'=ax+b | Recompute via certified exp |
| `expression_equivalence` | Evidence of equality | Simplify or samples (samples ≠ universal proof) |

Malformed kinds, wrong formats, and tightened-false enclosures must be **rejected**.
