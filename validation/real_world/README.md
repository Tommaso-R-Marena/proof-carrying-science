# PCS real-world validation registry

This directory contains the initial public-data validation cases for the v0.6 replay
kernel.

Run:

```bash
pcs benchmark-v06 validation/real_world/registry.json \
  -o real-world-validation.json
```

The registry format is `pcs-real-world-benchmark-registry-v1`. Each case records:

- a stable case ID;
- public source name, HTTPS source URL, and citation;
- source-data SHA-256 when exact source bytes were captured;
- deterministic derivation notes for local fixtures;
- SHA-256 for every local fixture;
- the executable PCS check specification;
- the expected PASS/FAIL/UNVERIFIED outcome;
- an interpretation explaining why that outcome is scientifically meaningful.

The benchmark runner verifies fixture hashes *before* invoking the replay kernel.
Expected FAIL cases are first-class: a benchmark run passes when observed outcomes
match the predeclared expectations, not when every scientific check returns PASS.

## Public sources

### Iris

Source: UCI Machine Learning Repository, Iris dataset.

- DOI: 10.24432/C56C76
- UCI page: https://archive.ics.uci.edu/dataset/53/iris
- UCI lists the dataset under CC BY 4.0.
- Exact CSV used for the 2026-09-29 execution was obtained through the public
  Rdatasets mirror and committed by source SHA-256 in the registry.

Derived fixtures:

- `iris_train_1_120.csv`: source row IDs 1-120;
- `iris_test_121_150.csv`: source row IDs 121-150;
- `iris_test_contaminated.csv`: the clean test split plus source row ID 120,
  intentionally creating one leakage event.

### Indometh

Source: R `datasets::Indometh`, originally from:

Kwan KC, Breault GO, Umbenhauer ER, McMahon FG, Duggan DE (1976),
“Kinetics of Indomethacin Absorption, Elimination, and Enterohepatic Circulation
in Man,” *Journal of Pharmacokinetics and Biopharmaceutics* 4(3):255-280.

R documentation:
https://stat.ethz.ch/R-manual/R-patched/library/datasets/html/Indometh.html

The public data contain 66 concentration/time observations from six subjects after
intravenous indomethacin. Subject 1 contributes 11 rows used here.

The fitted model fixture is **not** asserted to recover the true clinical dose,
volume, or clearance. Dose is normalized to 1 mg and V/CL are parameterized only
to represent the best log-linear single-exponential fit. The negative-control test
then asks whether the measured concentrations are exact deterministic outputs of
that narrow model. They are not, and PCS is expected to return FAIL.

The CRAN `pkr` manual is used as the source reference for the `mg/L`
concentration representation:
https://stat.ethz.ch/CRAN/web/packages/pkr/pkr.pdf

### Haber-Bosch

Source: Chemistry LibreTexts, “The Haber Process”:
https://chem.libretexts.org/Courses/Brevard_College/LNC_216_CHE/05%3A_Chemical_Reactions/5.04%3A_The_Haber_Process

The documented equation `N2 + 3 H2 <=> 2 NH3` is transcribed directly into the
PCS atom-balance predicate.

## Scope

This registry is a falsification/validation surface for the executable checkers. It
does not establish clinical validity, general model adequacy, general chemistry
coverage, or broad ML leakage detection.

The first direct checker-level execution is frozen in:

- `results/REAL_WORLD_VALIDATION_2026-09-29.json`
- `results/REAL_WORLD_VALIDATION_2026-09-29.md`

The hosted repository gate has not yet run these cases because GitHub has continued
to report `runner_id=0` with zero executed steps.
