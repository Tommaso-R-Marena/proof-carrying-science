# Independent scientific pilot v1 — implementation report

## Verdict

A new reviewer can reproduce a **bounded, Lean-authoritative, synthetic PK/PD** PCS assurance path from a clean checkout: intake freeze → discovery/confirm → attestation → second-environment verify → adversarial fail-closed checks → archival/closeout planning. Empirical scientific validity, external partnership, legal clearance, and production key custody remain explicitly unclaimed.

## Baseline environment

See `BASELINE_ENVIRONMENT.json`.

| Component | Value |
| --- | --- |
| Git base (pre-change `main`) | `68d8351a326565496908bf76c8a8daf082b94ff9` |
| Feature branch HEAD | `936adcb` (see `git rev-parse HEAD` on the PR branch) |
| Pull request | https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/120 |
| Python (runtime) | 3.12.3 (pin file 3.12.14) |
| Lean | 4.28.0 (`7e01a1bf5c70`) |
| Authority | `formal/.lake/build/bin/pcs-lean-authority` |
| Lockfile | `requirements-dev.lock` (hash-pinned) |

### Environmental friction observed

1. Host lacked `zstd`; `scripts/activate_lean_428.sh` failed until `apt-get install zstd`.
2. Host lacked `python3-venv`; clean-room runner failed until `apt-get install python3.12-venv`.
3. Lean authority binary must be built locally (`lake build pcs-lean-authority`); not committed.
4. `formal/lake-manifest.json` has empty packages — Mathlib is **not** required for the production authority target used here.
5. Without a pinned `generated_at`, bundle SHA-256 differs across runs while `certificate_semantic_hash` remains stable; the pilot now pins `GENERATED_AT` for byte-stable packaging.

## Delivered workflow evidence (local run)

From `/tmp/pcs-independent-pilot-run4` (copied machine-readable extracts into this directory):

| Field | Value |
| --- | --- |
| Pilot ID | `PCS-INDEPENDENT-PILOT-SYNTHETIC-001` |
| Bundle SHA-256 | `acafa67973b77b7421a2c2f3dbe186bd15d39f953470b3828819b6878d8f7fe5` |
| Intake semantic hash | `ab9fec8d50a28c2d432f68ecc8d5fa01e7e3f4867bc061ba289b37947b3a14cd` |
| Signer fingerprint (demo) | `ff935ffffcf117c49bb0d5ef393b866ccb6da527b35f2abb38031aeceb89bb6a` |
| Claims | `C_PK_CONTRACT` / `C_PK_REPLAY` → `COMPUTATIONALLY_SUPPORTED` |
| Authoritative | `true` (Lean ACCEPT) |
| Adversarial | all listed attacks rejected |

## Tests

```bash
python -m pytest -q tests/test_independent_pilot_v1.py
# 7 passed (includes clean-room reconstruction)
```

Clean-room reconstruction also succeeded at `/tmp/pcs-cleanroom-pilot` with `pass: true` after installing `python3-venv` (see `CLEANROOM_SUMMARY.json`). Clean-room bundle SHA-256 matched the local pilot exactly after pinning `generated_at`.

## Commands for independent reproduction

```bash
python3 -m pip install -e '.[dev]'
python3 scripts/check_repository_integrity.py
# ensure zstd is installed on Linux before Lean extract
source scripts/activate_lean_428.sh
cd formal && lake build pcs-lean-authority && cd ..
export PCS_LEAN_AUTHORITY_BIN="$PWD/formal/.lake/build/bin/pcs-lean-authority"
python scripts/run_independent_scientific_pilot_v1.py \
  --output /tmp/pcs-independent-pilot --overwrite --apply-closeout \
  --lean-authority "$PCS_LEAN_AUTHORITY_BIN"
python scripts/run_cleanroom_independent_pilot_v1.py \
  --output /tmp/pcs-cleanroom-pilot --overwrite \
  --lean-authority "$PCS_LEAN_AUTHORITY_BIN"
python -m pytest -q tests/test_independent_pilot_v1.py
```

## Trust boundary

See `TRUST_BOUNDARY_ASSESSMENT.json` and `docs/TRUST_BOUNDARY_ASSESSMENT_INDEPENDENT_PILOT_V1.md`.

## Failed experiments during development

1. First adversarial campaign incorrectly mutated non-existent `predictions.csv` ZIP members; v0.6 packages store content-addressed `artifacts/<id>/payload`. Fixed by mutating payload members.
2. Absolute-path attack initially renamed missing `.csv` members (no-op). Fixed by injecting `/tmp/evil.bin`.
3. `build_closeout_plan(..., notes=...)` rejected — API has no `notes` parameter; removed.
4. Stale `__pycache__` briefly masked the closeout fix until cache cleared.

## Explicit non-closure

- Issue **#13** remains open: this is a synthetic stand-in, not a genuine external partner workflow.
- Issues **#9** / **#14** remain open for legal/counsel/payment/custody prerequisites beyond engineering demo keys.
- PR **#117** research branch untouched; PR **#119** CI dependency bumps not duplicated.
