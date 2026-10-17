# Technical Report — Workstream B: Scientific Falsification

## Scope

Independent, black-box evaluation of Proof-Carrying Science (PCS) scientific
assurance surfaces. Writable paths are limited to
`independent_eval/scientific_falsification/**`. Production `pcs/`, `formal/`,
`research/`, `site/`, and `.github/` are not modified.

## Tasks delivered

### Task 7 — Scientific casebook

Seven self-contained workflows under `casebook/cases/`:

| ID | PCS checks |
| --- | --- |
| `01_pkpd_one_compartment` | `pkpd_contract`, `pkpd_reference_match` |
| `02_pkpd_with_peak_threshold_note` | classic PKPD + v0.6 peak declaration |
| `03_mass_action_reaction_balance` | `reaction_balance` (mass-action stoichiometry) |
| `04_unit_compatible_concentration` | `unit_compatible` |
| `05_csv_disjoint_cohorts` | `csv_disjoint` |
| `06_scientific_workflow_composite` | `reaction_balance` + `unit_compatible` |
| `07_pkpd_alt_parameters` | alternate PKPD parameter set |

Each case includes assumptions, expected results, negative controls,
reproduction commands, and CC0-1.0 license metadata. Upstream examples
(`examples/pkpd_one_compartment`, `scientific_mass_action`,
`scientific_workflow_v2/v3`) are referenced read-only.

### Task 8 — Correctness vs inadequacy

Four synthetic examples under `inadequacy/examples/` where PCS computational
checks PASS while empirical/scientific adequacy remains explicitly
unestablished:

1. Physiologically absurd but analytically consistent PKPD
2. Element-balanced reaction without biological pathway validation
3. Dimensionally compatible units without measurand adequacy
4. Disjoint train/test subject keys (`csv_disjoint`) with intentionally
   biased / non-representative synthetic cohorts (single site, narrow age
   band, single sex). No human participants; labels are scaffolding only.

### Task 9 — Metamorphic harness

`python_harness/metamorphic.py` applies valid transforms (subject rename, claim
reorder) and surface-applicable invalid transforms (dose/reaction break, unit
incompatibility, CSV key overlap, post-certify artifact tamper). Oracle
outcomes are compared to black-box `pcs certify` / `pcs verify` subprocess
results.

`run_metamorphic_campaign` (also invoked from `run_all.py`) covers:

- `01_pkpd_one_compartment`
- `03_mass_action_reaction_balance`
- `04_unit_compatible_concentration`
- `06_scientific_workflow_composite`

Per-case reports are written under `results/metamorphic_<case_id>.json`
(gitignored); campaign rollup is `results/metamorphic_campaign.json`.
`RESULTS/SUMMARY.json` remains the full-campaign summary artifact.

### Task 10 — Discovery benchmark

Synthetic projects under `discovery_benchmark/projects/` with
`ground_truth.json`. Evaluation calls `pcs discover-v06` read-only and reports
precision, recall, and abstention accuracy.

### Task 11 — External-validity protocols

Blank protocol templates and a completeness rubric under
`external_validity/`. Scoring software never invents participants or results;
`empirical_adequacy_established` is always `false`.

## Exact commands

```bash
# From repository root
python3 -m pip install -e '.[dev]'
export PATH="$HOME/.local/bin:$PATH"

# Rebuild immutable fixtures + SHA-256 manifest
PYTHONPATH=. python3 independent_eval/scientific_falsification/python_harness/build_fixtures.py

# Run tests
PYTHONPATH=independent_eval/scientific_falsification \
  python3 -m pytest -q independent_eval/scientific_falsification/tests

# Full campaign (optional)
PYTHONPATH=independent_eval/scientific_falsification \
  python3 -m python_harness.run_all --skip-build

# Single case certify/verify
pcs certify independent_eval/scientific_falsification/casebook/cases/01_pkpd_one_compartment/manifest.json \
  -o /tmp/pcs-sf-01
pcs verify /tmp/pcs-sf-01/certificate.json
```

## Fixture integrity

`fixtures/FIXTURE_HASHES.json` records SHA-256 digests for frozen casebook,
inadequacy, discovery, and external-validity inputs. Tests assert bit-stability.

## Observed results (this deepening)

- Inadequacy index lists **4** examples; all computationally PASS while
  `empirical_adequacy_established` remains false by construction.
- Metamorphic campaign covers **4** casebook surfaces (PK/PD, reaction,
  units, composite); applicable invalid transforms are selected per check
  surface (units-only cases skip dose/reaction break).
- Pytest suite collects **24** tests after deepening (was 20).

## Remaining weaknesses / non-claims

- Peak-threshold remains a v0.6 declaration on case 02; classic certify does
  not execute it.
- Metamorphic campaign does not yet cover case `05_csv_disjoint_cohorts` as a
  first-class suite entry (inadequacy example 04 exercises `csv_disjoint`
  PASS-without-adequacy separately; overlap transform is implemented and
  available when a project declares that check).
- Discovery abstention remains inferred (no explicit `abstain` field).
- PCS verify PASS ≠ empirical scientific adequacy.

## Non-claims

- PCS verify PASS ≠ empirical scientific adequacy
- No human participants were enrolled; no study results were invented
- Peak-threshold execution is a v0.6 surface; classic `pcs certify` covers
  contract + reference match for case 02
