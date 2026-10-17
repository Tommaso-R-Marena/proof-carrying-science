# Workstream A — Independent Protocol Verification and Adversarial Security

Black-box evaluation of PCS protocol surfaces. **Does not modify** production `pcs/`, `formal/`, or CI.

## Components

| Path | Purpose |
| --- | --- |
| `rust_jcs_ref/` | Independent Rust JCS/SHA-256 reference (`pcs-independent-jcs`) |
| `python_harness/` | Differential tests, ≥150 adversarial corpus, ZIP differential, intake chronology, policy confusion, resource bounds |
| `fixtures/` | Generated immutable campaign inputs |
| `results/` | Machine-readable campaign outputs |
| `tests/` | Pytest suite |

## Commands

```bash
# From repository root
source scripts/activate_lean_428.sh   # if needed for Lean authority
cd formal && lake build pcs-lean-authority && cd ..
python3 -m pip install -e '.[dev]'
cargo test --manifest-path independent_eval/protocol_adversarial/rust_jcs_ref/Cargo.toml
PYTHONPATH=independent_eval/protocol_adversarial python3 -m pytest -q independent_eval/protocol_adversarial/tests
PYTHONPATH=independent_eval/protocol_adversarial python3 -m python_harness.run_all
```

## Non-claims

This workstream does not claim production security, biological adequacy, or that a finite attack corpus is a security proof.
