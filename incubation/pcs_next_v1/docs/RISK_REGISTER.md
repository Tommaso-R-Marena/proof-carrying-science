# Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| Overlap with PRs #117–#135 | High | Owned namespace only; complementary designs |
| Accidental shared-file edit | High | `check_noninterference.py` before every push |
| Overclaiming external validation | High | Explicit OPEN status + documentation |
| Policy self-authorization | High | Receiver pin; producer PASS ignored |
| Lean/toolchain drift | Medium | Pin 4.28.0 in isolated workspace |
| Local hash chain treated as immutable history | Medium | Documented caveat in evidence store |
