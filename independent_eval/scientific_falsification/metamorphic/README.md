# Metamorphic scientific testing (Task 9)

Harness: `python_harness/metamorphic.py`

Black-box oracle: `pcs certify` / `pcs verify` via subprocess.

Campaign coverage (via `run_metamorphic_campaign` / `run_all.py`):

- `01_pkpd_one_compartment`
- `03_mass_action_reaction_balance`
- `04_unit_compatible_concentration`
- `06_scientific_workflow_composite`

Per-case reports are written under `results/metamorphic_<case_id>.json` (gitignored); campaign rollup is `results/metamorphic_campaign.json`.
