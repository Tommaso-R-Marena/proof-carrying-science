# Reproducibility

## Versions

* Lean `leanprover/lean4:v4.28.0` (see `lean-toolchain`)
* Mathlib commit `8f9d9cff6bd728b17a24e163c9402775d9e6a365` (pinned in `lake-manifest.json`)
* Python 3.11. Only the standard library is needed (`fractions`, `json`, `random`, `unittest`).

## Steps

```bash
# 1. Lean: library, verified checker, the four certificate theorems, axiom audit
lake exe cache get        # optional: download Mathlib build cache
lake build                # prints the #print axioms output of AxiomAudit.lean

# 2. Python tests (18 unit/adversarial tests)
PYTHONPATH=python python3 -m unittest discover -s tests -v

# 3. Benchmarks + certificates (full run about 6 min, dominated by synthesis)
python3 scripts/run_all.py            # or --quick, --no-ssa
python3 scripts/run_all.py --lean     # also regenerates Examples/*.lean and re-checks them in Lean
```

Outputs:
* `certificates/*.json`: exact rational certificates
* `results/benchmarks.json`: raw output
* `results/summary.md`: summary table
* `results/axiom_audit.txt`: axioms used by the headline theorems

SSA uses a fixed seed (`seed=1`). Synthesis is deterministic.

## Checking a certificate independently

```python
import json, sys; sys.path.insert(0, "python")
from aion import checker
print(checker.check_certificate(json.load(open("certificates/C_modulated_growth_N30.json"))))
```

For the Lean-verified path, see `RequestProject/AION/Examples/XYmain.lean`. It defines the network and certificate
data, and proves `sandwich` using `checkUpper_sound` / `checkLower_sound` together with `native_decide`.
