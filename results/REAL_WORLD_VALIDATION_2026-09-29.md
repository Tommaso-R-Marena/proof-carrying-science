# Real-world validation — 2026-09-29

Verdict: **5 / 5 cases matched the expected outcome; 0 unexpected outcomes.**

This is the first PCS validation set built from public scientific examples rather
than only repository-authored synthetic fixtures.

## What was actually executed

The cases were executed in an isolated Python session using the current branch's
checker logic for:

- `reaction_balance`;
- `csv_disjoint`;
- `unit_compatible`;
- the restricted one-compartment analytic replay equation.

This was genuine checker-level execution. It was **not** a GitHub Actions run and
was **not** a full `attest-v06 -> verify-v06-bundle` round trip, because the
repository's hosted runners are still failing before allocation with
`runner_id=0` and no executed steps.

The permanent repository feature added alongside this run is
`pcs benchmark-v06 validation/real_world/registry.json`. It verifies exact local
fixture hashes before replay, records public source/citation metadata, compares
actual outcomes with predeclared expected outcomes, and emits a deterministic
hash-bound report.

## Cases

### 1. Haber-Bosch stoichiometry — PASS as expected

Public source: Chemistry LibreTexts, *The Haber Process*.

Published reaction:

```text
N2 + 3 H2 <=> 2 NH3
```

PCS result:

```text
reactants: N=2, H=6
products:  N=2, H=6
delta:     {}
PASS
```

This is a straightforward positive control for the chemistry checker.

### 2. UCI Iris deterministic split — PASS as expected

Public source: Fisher's Iris dataset, UCI Machine Learning Repository,
DOI 10.24432/C56C76, CC BY 4.0.

The public 150-row dataset was deterministically divided by its source row
identifier:

- left/train: rows 1-120;
- right/test: rows 121-150.

PCS result:

```text
left unique IDs:  120
right unique IDs: 30
overlap:           0
PASS
```

### 3. UCI Iris one-row contamination — FAIL as expected

The clean split was adversarially mutated by copying source row 120 into the test
set.

PCS result:

```text
overlap_count: 1
overlap_sample: ["120"]
FAIL
```

This case matters more than the clean PASS: the checker detected a single-record
train/test leakage in a real public biology dataset.

### 4. Indometh concentration units — PASS as expected

Public source: CRAN `pkr` documentation uses the Indometh dataset with
concentration represented in `mg/L`.

PCS compared:

```text
mg/L
g/m^3
```

Both reduce to identical mass/volume dimensions and identical SI scale:

```text
conversion_left_to_right = 1.0
PASS
```

### 5. Published IV indomethacin data vs exact single-exponential replay — FAIL as expected

Public source: R `datasets::Indometh`, originating from Kwan et al. (1976).
The dataset contains 66 measurements from six subjects after intravenous
indomethacin.

Subject 1 contributes 11 concentration/time observations. A best log-linear
single-exponential fit was constructed:

```text
C0  = 0.7959236856857457 mg/L
kel = 0.4186240014007021 / h
```

The dose was normalized to 1 mg and the v0.6 model's V and CL were chosen to
represent that fitted exponential exactly. The actual measured concentrations were
then intentionally supplied as though they were deterministic model output.

PCS result at its strict replay tolerance:

```text
rows: 11
mismatching rows: 11
max absolute concentration error: 0.7831638386902207 mg/L
max relative error: 1.0925283641651804
FAIL
```

This is an important **correct rejection**. The current PK/PD adapter proves/replays
a declared narrow analytic computation. It is not an empirical model-fitting or
clinical-validity engine. Passing measured patient/volunteer concentrations as
though they were exact deterministic model output should fail.

A system that returned PASS here would be overclaiming its scientific scope.

## Source commitments

Exact source CSV bytes used for the session were committed by SHA-256:

```text
Rdatasets Indometh.csv
aecce7eaa7fd2057ea5bf5a02943463ad5036354dd87a0808376ce502aaf0049

Rdatasets iris.csv
398fadb8f48750d386d670e0b15c65944919682373bcaba59650c33eb5474362
```

Derived local benchmark fixtures are separately SHA-256 pinned in
`validation/real_world/registry.json`.

## What this does and does not establish

**Established by this run**

- current stoichiometry logic handles a documented industrial reaction correctly;
- current CSV disjointness logic accepts a clean public-data split;
- it catches a one-record leakage mutation;
- current units logic recognizes an important concentration-unit equivalence;
- the narrow PK replay correctly rejects real measured IV PK data when it is
  misrepresented as exact deterministic model output.

**Not established**

- a complete v0.6 package/ZIP round trip on these real-world cases;
- clinical or pharmacological adequacy of the PCS PK model;
- broad chemical formula coverage;
- broad ML leakage detection beyond exact key disjointness;
- general scientific validity;
- hosted CI success.

## RL / adaptive scheduling

RL is intentionally **not** part of the acceptance boundary. A future contextual
bandit or RL scheduler could use benchmark history to order expensive checks for
faster failure discovery, but every mandatory check would still have to execute
before acceptance. Such a scheduler must remain untrusted with respect to the
scientific verdict.
