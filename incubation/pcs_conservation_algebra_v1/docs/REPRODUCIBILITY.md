# Reproducibility

```bash
cd incubation/pcs_conservation_algebra_v1
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
bash scripts/run_all.sh
```

Pinned Lean: `leanprover/lean4:v4.28.0`  
Mathlib: tag `v4.28.0` (see `lakefile.toml`)

All example contracts are CC0-1.0 synthetic. No private data.
