# Incremental Certificate Revalidation v0

Research-only PCS subsystem for **formally verified incremental revalidation** of
computation-DAG certificates. Exclusive namespace — not production-integrated.

## What this is

A Lean 4 model (`PCSIncremental`) plus an independent Python verifier that:

1. Fully verifies a finite DAG under restricted synthetic ops (exact Int/Rat).
2. Records an authoritative local `ValidState` cache (`FreshWitness` in Lean).
3. Applies a complete change set; invalidates Affected on the **updated** graph.
4. Reuses only **eligible ∧ prior-accepted** certificates; rechecks Affected nodes.
5. Proves `IncrementalAccept` premises ⇒ `FreshValid` (does not assume fresh validity).
6. Differs against an independent fresh oracle (differential testing ≠ refinement).
7. Assumption-removal counterexamples + adversarial suite; expensive-check speedups.

## What this is not

Not ClaimCheck, EvidenceKernel, checked-lemma proof search, scientific intake,
SVB, or production PCS authority. See `OVERLAP_AUDIT.md`.

## Reproduce

```bash
# From repository root (this branch / worktree)
export PATH="$HOME/.local/lean-4.28.0/bin:$PATH"   # or scripts/activate_lean_428.sh
export PYTHONPATH=research/incremental_certificate_revalidation_v0

bash research/incremental_certificate_revalidation_v0/scripts/check_lean.sh
python -m pytest -q research/incremental_certificate_revalidation_v0/tests
python research/incremental_certificate_revalidation_v0/scripts/run_demo.py
python research/incremental_certificate_revalidation_v0/scripts/run_adversarial.py
python research/incremental_certificate_revalidation_v0/scripts/run_benchmarks.py
python -m benchmarks.expensive_suite   # from this package with PYTHONPATH set
```

Pinned Lean: **4.28.0** (repository `lean-toolchain`).

## Layout

| Path | Role |
|---|---|
| `formal/PCSIncremental/` | Lean model + soundness theorems |
| `model/` `verifier/` `cache/` `reference/` | Executable research prototype |
| `adversarial/` | Cache-poisoning campaign |
| `benchmarks/` | Synthetic DAG scaling |
| `docs/` | Spec, theorems, trust, refinement, performance |
| `paper/manuscript.md` | Research write-up |
| `OVERLAP_AUDIT.md` | Mandatory conflict audit |
| `HANDOFF.md` | Continuity checkpoint |

## Status

Research draft. No merge to `main`, no production authority, no public disclosure
without separate clearance.
