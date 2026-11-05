# HECK v1 implementation ledger

| Component | Path | Status |
| --- | --- | --- |
| Level lattice + no-promotion | `formal/PCSCompose/Levels.lean` | proved |
| Composition receiver IR | `formal/PCSCompose/Compose.lean` | proved + controls |
| Predictive obligations | `formal/PCSCompose/Predictive.lean` | proved |
| Executable controls (14) | `formal/PCSCompose/Controls.lean` | native_decide |
| Audit target list | `formal/PCSCompose/Audit.lean` | 49 names |
| Python levels/compose | `heck/levels.py`, `heck/compose.py` | implemented |
| Predictive + Theory IR | `heck/predictive.py`, `heck/theory_ir.py` | implemented |
| Attack campaign (8) | `heck/falsify.py` | implemented |
| Package receiver + CLI | `heck/receiver.py`, `heck/cli.py` | implemented |
| Composition campaign | `experiments/compose_campaign/` | implemented |
| Pytest suite | `tests/` | implemented |
| Noninterference script | `scripts/noninterference_check.sh` | implemented |

## Boundaries

- No production `pcs/` edits
- No website / CertNum / PCS Next / PGSI coupling
- Leaf `supported` bits are upstream inputs in v1
- Scientific closure ≠ formal truth ≠ PCS package ACCEPT
