# Architecture

```
Untrusted generators (Python CLI / search)
        │  certificates (JSON, certnum-cert-v1)
        ▼
Independent checker (Python now; Lean expanding)
        │  accepts only if recomputed obligations hold
        ▼
Mathematical claim (enclosure / root / opt / …)

Lean kernel: ℚ interval ops + membership soundness theorems
```

## Layers

1. **Semantic core (Lean):** `Interval`, arithmetic, `mem_*` soundness.
2. **Expression IR (Python):** typed AST, parser, simplify, AD.
3. **Algorithms (Python):** roots, BnB, ODE, Markov, thermo, linalg.
4. **Certificates:** versioned JSON; checker does not trust verdicts.
5. **Isolation:** all files under `incubation/pcs_certified_numerics_v1/`.

## Non-goals

PCS Claim IR, production signing, website, NL translation, self-improvement loops.
