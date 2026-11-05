# Reproducibility

```bash
git fetch origin research/pcs-certified-numerics-v1-20261017
# worktree or checkout that branch
cd incubation/pcs_certified_numerics_v1

python3 -m venv ~/.venvs/pcs-certified-numerics && source ~/.venvs/pcs-certified-numerics/bin/activate
pip install -e ".[dev]"
pytest -q

curl https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh -sSf | sh -s -- -y --default-toolchain leanprover/lean4:v4.28.0
export PATH="$HOME/.elan/bin:$PATH"
export LAKE_CACHE_DIR="$HOME/.cache/certnum-lake"
lake exe cache get && lake build

bash scripts/run_all.sh
```

No paid proprietary services required for core verification.
