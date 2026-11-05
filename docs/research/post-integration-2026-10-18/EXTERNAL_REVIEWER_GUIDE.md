# Independent reviewer reproduction

Review draft #156 against the pinned PR153 base
`b916eec1b9d0d5c02c9cc19b070f7a47df5e5d87`. Review the receipt repair (#154)
and independent original audit (#155) separately. Do not merge or deploy these
experiments as part of reproduction. No external reviewer has been recruited or
reported as validating this work.

Use a fresh checkout, Python 3.12 and Lean 4.28.0. From the repository root:

```sh
python -m pip install --require-hashes -r research/integration_v1/requirements.lock
python -m pip install --no-deps --no-build-isolation -e .
source scripts/activate_lean_428.sh
lake exe cache get
python -m research.integration_v1.prepare_mathlib_cache --project incubation/pcs_certified_numerics_v1
python -m research.integration_v1.prepare_mathlib_cache --project incubation/pcs_conservation_algebra_v1
python -m research.integration_v1.prepare_mathlib_cache --project research/integration_v1/formal
python -m research.integration_v1.prepare_mathlib_cache --project research/scientific_receiver_v1/formal
python -m research.scientific_receiver_v1.qualify --out /tmp/pcs-review-formal
export LEAN_PATH="$(lake -d research/scientific_receiver_v1/formal env printenv LEAN_PATH)"
export PCS_SCIENTIFIC_LEAN="$(command -v lean)"
export PCS_SCIENTIFIC_MAIN="$PWD/research/scientific_receiver_v1/formal/Main.lean"
export PCS_SCIENTIFIC_CWD="$PWD/research/scientific_receiver_v1/formal"
python -m pytest -q research/scientific_receiver_v1/tests
python -m research.scientific_receiver_v1.differential --checker "$PCS_SCIENTIFIC_LEAN" --checker-arg=--run --checker-arg="$PCS_SCIENTIFIC_MAIN" --checker-cwd "$PCS_SCIENTIFIC_CWD" --out /tmp/pcs-review-differential
python -m research.scientific_receiver_v1.pilot --checker "$PCS_SCIENTIFIC_LEAN" --checker-arg=--run --checker-arg="$PCS_SCIENTIFIC_MAIN" --checker-cwd "$PCS_SCIENTIFIC_CWD" --out /tmp/pcs-review-pilot
python -m research.integration_v1.source_gate
```

Choose new output paths; experiments refuse to overwrite prior evidence. The
full differential campaign took 801 seconds locally, largely due to 256 isolated
oversize-frame process launches. Compare the seed, corpus and preregistration
SHA256 values in `research/scientific_receiver_v1/reports/EVALUATION.md`.
Compressed originals and their hashes are retained in `EVIDENCE_INDEX.json`.

Inspect `statements-and-axioms.log` and `qualification.json`, not just printed
test totals. The full formal audit includes generated declarations; the authored
theorem names and statements are explained in `RECEIVER_FORMAL_SOUNDNESS.md`.
`module-artifacts.json` records the actual declared direct/transitive Lean import
inventory, while `environment.json` is itself bound by the qualification hash.
Cached dependency objects and compiler/IO/OS assumptions remain explicit.

The separately launched host is documented in `receiver-service.md`. The optional
`full_profile` experiment consumes an operator-reviewed qualification and its
**independently retained SHA256**, pins every inventoried module artifact, and
replays a positive case and wrong-environment negative case. Computing a digest
from an attacker-supplied qualification is not independent trust establishment.
Receipt-signature replay requires an externally pinned public key; replaying a
signature does not rerun Lean or prove historical occurrence.

The three synthetic pilot cases have different scopes: exact A→B receiving,
four sampled analytic PK values, and a finite nonidentifiability witness. The
SCM example lacks positive observational treatment support. No patient data,
clinical safety result, kinetic validation or external empirical adoption follows.
The scoped falsification report uses real HECK/PCSNext engines and explicitly
synthetic observations. A contrary observation reopens applicability; it does
not invalidate the conditional mathematics.
