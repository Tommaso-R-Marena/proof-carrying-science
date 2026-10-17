# Test inventory — Workstream A

| Suite | Result |
| --- | --- |
| `cargo test` (rust_jcs_ref) | **3 passed** |
| `pytest independent_eval/protocol_adversarial/tests` | **8 passed** (see `results/TEST_RUN.txt`) |
| Adversarial corpus cases | **151** (10 positive accepted, 141 negatives rejected after attempted verify, 0 false accepts, 0 not_attempted) |
| New mutation families (this deepening) | truncated/bit-flipped signature fields; swapped fingerprint vs signer; member rename breaks lock; duplicate critical member conflict; empty certificate/signature/normalized-index bytes |
| JCS differential vectors | 16 (2 observed spelling disagreements recorded) |
| ZIP differential cases | 8 (5 acceptance asymmetries recorded) |

See `results/TEST_RUN.txt` and JSON reports under `results/`.
