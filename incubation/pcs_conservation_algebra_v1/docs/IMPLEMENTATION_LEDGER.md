# Implementation ledger

| Component | Path | Status |
| --- | --- | --- |
| Stoichiometric Lean core | `lean/PCCA/Stoich.lean` | Implemented |
| Elemental Lean bridge | `lean/PCCA/Elemental.lean` | Implemented |
| Controls + audit | `lean/PCCA/Controls.lean`, `Audit.lean` | Implemented |
| Rational matrix / nullspace | `python/pcca/stoich/matrix.py` | Implemented |
| Formula tokenizer | `python/pcca/formula.py` | Implemented |
| Certificate + checker | `python/pcca/certificate/` | Implemented |
| Independent receiver | `python/pcca/receiver/replay.py` | Implemented |
| CLI | `python/pcca/cli/main.py` | Implemented |
| Examples | `examples/**` | Implemented |
| Tests | `tests/**` | Implemented |
| Noninterference | `scripts/noninterference_check.sh` | Implemented |
| Continuum bridge proofs | — | Deferred (OPEN) |
| Claim IR coupling | — | Out of scope |
