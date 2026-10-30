# PCS Lean libraries and verification boundary

The repository pins **Lean 4.28.0**. From the repository root:

```sh
source scripts/activate_lean_428.sh
lake -d formal build PCS pcs-lean-authority pcs-semantic-check
```

`PCS` builds the umbrella library and Golden obligations. `pcs-lean-authority`
is the production v0.6 executable; `pcs-semantic-check` supports the separately
scoped semantic correspondence checks. Follow [the kernel status](../docs/LEAN_KERNEL_STATUS.md)
for the exact current authority and remaining assumptions. Do not replace actual
Lean execution with a Python verdict or a caller-provided verifier.

Transport and real-analysis research also require the root project's pinned
Mathlib dependencies. Prepare them from the repository root before those tests:

```sh
source scripts/activate_lean_428.sh
lake exe cache get
```

The public full gate prepares this dependency and requires actual transport kernel
execution. Missing dependencies must fail the required lane, rather than skip it.

Research projects with their own lakefiles and namespaces are built separately.
The [research guide](../research/README.md) identifies isolated PGSI, epistemic,
numerical and experimental authority projects. Their mathematical specifications
are not interchangeable, and their proofs do not automatically extend production
claims. PR #117 remains held; newer unavailable Aristotle artifacts are not assumed
integrated. Avoid editing its formal modules to obtain a convenient test result.

The latest public-study analysis is additive and does not change this library's
production authority. Rebuild its exact dependencies, audit its six theorem
closures and run a fresh object check with:

```sh
PYTHONPATH=. python research/public_study_validation_v1_results/check_proofs.py /tmp/new-output-boundary-proofs
```

The result applies to the explicit modeled trace and coupled outcome resolver.
It does not prove neural computation, Python/C/SQLite/OS refinement, raw-output
confidentiality, empirical model safety or scientific validity.

Required qualification retains source checks, axiom audits, genuine negative
controls and fresh checks where specified. No proof holes, new axioms or unsafe
proof shortcuts may be added to make a check pass. Historical source artifacts
and their original assumptions remain inspectable. Aristotle-assisted sources
retain their attribution and provenance; [Aristotle](https://aristotle.harmonic.fun)
is an external development system whose outputs require independent checking.
