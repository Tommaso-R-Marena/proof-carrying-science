# PCS Next v1 — Integrated Scientific Assurance (Isolated Candidate)

**Status:** research / draft integration candidate only.  
**Owned namespace:** `incubation/pcs_next_v1/`  
**Branch:** `research/pcs-next-integrated-assurance-v1-20261017`  
**Base:** see `BASE_SHA.txt`

This tree must not modify production PCS authority, signing keys, CI, Cloudflare,
or shared roots (`formal/`, `pcs/`, `.github/`, etc.).

## Quick start

```bash
export PYTHONPATH=incubation/pcs_next_v1:$PYTHONPATH
python incubation/pcs_next_v1/scripts/run_synthetic_pilot.py
python incubation/pcs_next_v1/scripts/validate_all.py
```

## CLI

```bash
python -m pcs_next_v1.cli run-pilot FIXTURES/project --intake ... --policy ... --work ...
python -m pcs_next_v1.cli review PACKAGE --policy POLICY
python -m pcs_next_v1.cli assurance-card REPORT --out DIR
```

## Reviewer UI

Open `pcs_next_v1/reviewer/workbench/index.html` in a browser (static demo) or serve locally.
Verification authority remains the CLI.

## Documentation

See `docs/` especially `CAPABILITY_INVENTORY.md`, `IMPLEMENTATION_LEDGER.md`, and reports.
