# Epistemic Obligation Lattice v1 — research package

Isolated experimental line. Does not modify production package authority.

## Contents

| Path | Role |
| --- | --- |
| `fixtures/` | Positive/negative control packages + expectations |
| `campaign/` | Executed campaign receipts (generated) |
| `REPORT.md` | Theory, architecture, experiment outcomes, limits |
| `PROTOCOL.json` | Frozen evaluation protocol |

## Run

```bash
python -m pytest tests/test_epistemic_lattice_v1.py -q
pcs epistemic-lattice-v1 --campaign research/epistemic-lattice-v1/fixtures \
  --output research/epistemic-lattice-v1/campaign/report.json --force
```

Optional Lean library (no Mathlib; no PCS authority import):

```bash
cd formal && lake build PCSEpistemic
```
