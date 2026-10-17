# Test inventory — Workstream A

| Suite | Result |
| --- | --- |
| `cargo test` (rust_jcs_ref) | **3 passed** |
| `pytest independent_eval/protocol_adversarial/tests` | **7 passed** |
| Adversarial corpus cases | **104** (10 positive accepted, 94 negatives rejected after attempted verify, 0 false accepts) |
| JCS differential vectors | 16 (2 observed spelling disagreements recorded) |
| ZIP differential cases | 8 (5 acceptance asymmetries recorded) |

See `results/TEST_RUN.txt` and JSON reports under `results/`.
