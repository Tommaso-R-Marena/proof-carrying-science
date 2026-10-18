# CertNum — PCS Certified Numerics (v1 incubation)

Standalone **certified scientific computation engine**: exact rational interval arithmetic, typed expressions, forward AD, root isolation, global optimization, linear/ODE/Markov/thermo certificates, and an independent checker.

**Independence:** this tree lives only under `incubation/pcs_certified_numerics_v1/`. It does **not** modify PCS production, the website, `incubation/pcs_next_v1/`, FoldBounds, CertiForge, or Aristotle workstreams. Preferred destination is a separate private repo `Tommaso-R-Marena/pcs-certified-numerics` (creation blocked by token scopes in this environment; fallback isolation used).

## Quick start

```bash
# Isolated Python venv (do not reuse PCS envs)
python3 -m venv ~/.venvs/pcs-certified-numerics
source ~/.venvs/pcs-certified-numerics/bin/activate
cd incubation/pcs_certified_numerics_v1
pip install -e ".[dev]"
pytest -q

# Lean 4.28.0 + Mathlib (own lake cache)
export PATH="$HOME/.elan/bin:$PATH"
export LAKE_CACHE_DIR="$HOME/.cache/certnum-lake"
lake exe cache get
lake build

# CLI
certnum prove-interval examples/optimization/problem_interval.json
certnum isolate-roots examples/roots/x2_minus_2.json
certnum optimize examples/optimization/quad1d.json
certnum verify path/to/certificate.json
```

## What is verified in Lean

| Result | Status |
|---|---|
| Rational interval ops (neg/add/sub/mul/…) | Implemented |
| Soundness: `mem_neg`, `mem_add`, `mem_sub`, `mem_mul`, hull/inter | **Proved, no sorry** |
| Expression language / certificate checker in Lean | Partial / Python reference checker first |
| ODE / thermo / Markov | Python certified algorithms + certificates |

## Trust boundary

- **Untrusted:** Python generators, heuristics, search, host `math.*` diagnostics.
- **Trusted for proved claims:** Lean theorems on interval membership; Python checker recomputes obligations (Lean checker expansion is ongoing).
- Floating-point is **never** a proof.

See `docs/` for architecture, certificate spec, ledger, and research notes.
