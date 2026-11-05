# Proof-carrying discrete transport

PCS can now freshly kernel-check invariants of a declared finite transport matrix
for **every natural-number time step**, including its action on arbitrary real
initial states within supplied bounds. This extends the existing v3 workflow's
exact replay of a finite recorded trajectory. The new result is a mathematical
matrix theorem, with implementation correspondence and scientific adequacy kept
as separate obligations.

The implementation is first-party research continuation. The external AI-safety
research and Aristotle development traces are not training inputs to this work.
The example is the existing authored CC0 synthetic computation; no empirical
observations, independent human review or new scientific discovery are claimed.

## Mathematical contract

For a finite index type, cell volumes `v` and a transition matrix `P`,
`PCSReal.Transport.Certified v P` requires:

- Strictly positive volumes.
- Nonnegative matrix entries.
- Every row sums to one.
- `sum_i (v_i * P_ij) = v_j` for every column.

`of_detailed_balance` derives the last property from row stochasticity and
`v_i * P_ij = v_j * P_ji`, a sufficient condition for symmetric exchange models.
It is not a requirement for the more general invariant-matrix theorem.

The update is `x'_i = sum_j P_ij * x_j`. The general proofs establish:

| Theorem | Meaning |
| --- | --- |
| `step_lower`, `step_upper` | Each update preserves any common concentration interval. |
| `step_nonnegative` | An update preserves nonnegative concentrations. |
| `amount_step` | `sum_i v_i*x_i` is preserved exactly. |
| `row_quadratic_bound` | A row's squared concentration is bounded by its weighted input squares. |
| `quadratic_step` | `sum_i v_i*x_i^2` is nonincreasing. |
| `amount_all_times`, `bounds_all_times`, `nonnegative_all_times`, `quadratic_all_times` | The corresponding invariants hold for every natural-number iteration count. |
| `all_times_contract` | Conservation, bounds and both one-step and initial quadratic bounds composed. |
| `check_sound` | A successful exact-rational finite certificate implies the matrix contract. |
| `rational_certificate_real` | The checked rational coefficients satisfy the same contract after exact embedding into the reals. |

These 14 general theorems are in
[`Transport.lean`](../formal/real/PCSReal/Transport.lean). Seven additional
[`kernel controls`](../formal/real/PCSReal/TransportControls.lean) cover a valid
model, its universal consequence, negative entries, nonconservation, wrong row
sums, zero volume and a CFL-boundary oscillation. The last preserves the quadratic
functional; the theorem does not imply strict dissipation or convergence.

The quantity preserved is amount in mol. The decreasing functional has units
`mol^2/m^3`; it is not thermodynamic energy.

## Receiving verification

[`pcs/transport_kernel_v1.py`](../pcs/transport_kernel_v1.py) consumes the existing
v3 typed contract. It independently reconstructs the matrix by incidence sums,
using a different construction from v3's incremental matrix update. An optional
producer matrix certificate must match this reconstruction and the exact source
contract bytes. Boolean/numeric confusion, extra fields, changed volumes,
initial states, hashes and proof-text injection cannot authorize a different
model. Both current-input reconstructions must agree exactly on matrix
coefficients, cell volumes and the initial vector before any model proof is
accepted. This executed handoff check is distinct from universal Python source
refinement.

The receiver generates only bounded rational literals and fixed proof text.
It copies its own general theorem source to a private directory, compiles that
snapshot, then compiles and audits four regenerated literal-model theorems:

- `PCSTransportReplay.matrix_checked`.
- `PCSTransportReplay.initial_bounds`.
- `PCSTransportReplay.declared_all_times`.
- `PCSTransportReplay.all_real_initial_states`.

The last theorem quantifies over arbitrary real initial vectors and every
natural-number time, rather than enumerating a submitted trajectory. No producer
Lean file, proof-generation transcript or project executable is run by receiving
verification. Mathlib and the Lean compiler are separately trusted dependencies.

All 21 static declarations and all generated declarations have their exact axiom
inventories checked against `propext`, `Classical.choice` and `Quot.sound`.
Ordinary `decide +kernel` reduction checks the rational literals in four
separate obligations, with sequential elaboration to bound interpreter memory. No native
reduction oracle is admitted by this audit. Dependency mismatch, changed tracked
Mathlib sources, compilation failure, source substitution, exhausted resources
and incomplete inventories grant no model support.

When a proposed literal matrix fails, a separate generated theorem can establish
`check volume matrix = false`. Only that successful negative kernel proof yields
`CERTIFICATE_FALSIFIED` and `negative_kernel_checked: true`. A compiler failure
alone is not reported as a mathematical counterexample.

The receiving process uses pinned Lean 4.28.0 and Mathlib revision
`8f9d9cff6bd728b17a24e163c9402775d9e6a365`. Each Lean process has a 2,048 MiB
memory limit, and the replay has a total wall budget of at most 180 seconds.
The supported intake retains v3's 2–16 cells, 64 edges, 64 recorded time steps,
2 MiB artifact and 4,096-bit rational bounds. Signed input ZIPs are bounded to 32 MiB. The theorem's iteration count is
unbounded; the submitted CSV is still checked within the existing finite limits.

## Use from a repository checkout

Install the locked Python dependencies, activate the pinned Lean toolchain and
obtain the pinned public Mathlib cache. No paid service is needed:

```sh
python -m pip install --require-hashes -r requirements-build.lock -r requirements-dev.lock
python -m pip install --no-deps --no-build-isolation -e .
source scripts/activate_lean_428.sh
lake exe cache get
```

Replay the authored example into a new evidence directory:

```sh
python -m pcs.cli transport-kernel-v1 \
  --contract examples/scientific_workflow_v3/contract.json \
  --trajectory examples/scientific_workflow_v3/trajectory.csv \
  --output /tmp/pcs-transport-kernel-new
```

Omitting `--trajectory` requests model-only verification. `--proposal FILE` adds
an untrusted `pcs-transport-matrix-certificate-v1` data proposal. The receiver
always regenerates the proof.

For an existing signed v3 workflow, build the existing authority and replay using
the producer's pinned experimental identity:

```sh
lake -d formal build pcs-lean-authority
python -m pcs.cli transport-kernel-v1 \
  --bundle /path/to/transport.pcs.zip \
  --public-key /path/to/producer-public.pem \
  --fingerprint PINNED_FINGERPRINT \
  --output /tmp/pcs-signed-transport-kernel-new
```

The signed path takes one private snapshot of the exact bounded ZIP bytes, then
executes the existing v0.6 authority and v3 independent
replay, including exact source, claim and premise binding. It then adds the fresh
matrix proof over the same immutable snapshot. Contract, trajectory and ZIP
hashes must match across the two receiving stages. Changes to the original file
during verification cannot substitute the input to the second stage. Existing
historical signed evidence remains unchanged.

The output retains `report.json`, regenerated `Replay.lean`, matrix data,
receiving source snapshots and a byte inventory. `acceptance_scope` distinguishes
model-only, model-plus-finite-trajectory and signed-package verification.
`all_time_model_supported`, `bounded_trajectory_supported` and
`pcs_package_valid` remain separate fields. The unsigned output inventory is
byte-consistency metadata, not an outside endorsement or trusted producer claim.

## Verification and limits

```sh
lake build +PCSReal.TransportControls:leanArts
python scripts/verify_transport_formal.py --output /tmp/transport-static-new.json
PCS_REQUIRE_TRANSPORT_KERNEL=1 python -m pytest -q tests/test_transport_kernel_v1.py
python scripts/run_transport_kernel_v1.py --output /tmp/transport-campaign-new
```

The required `real-analysis-bridge` CI lane builds and audits the library, builds
the existing compiled authority, runs the required-kernel tests and retains the
fresh receiving campaign. The campaign includes unsigned and signed positive
cases, authentically signed false reports and trajectories, changed model data,
proof injection, a CFL violation, a CFL-boundary oscillation, the 16-cell domain
bound and an actual kernel proof falsifying an incorrect matrix certificate.
The existing core, Aristotle, source-integrity and cross-language gates remain
required.

The Python parser, incidence constructor, CSV decoder and update loop do not yet
have universal source-refinement theorems. Source hashes bind their operational
provenance; they do not discharge that correspondence obligation. The theorem
applies to the exact rational matrix literals, not automatically to native
floating-point execution, arbitrary mesh geometry, continuous PDE accuracy or
real material behavior.

The original `C_NUMERICAL`, `C_CONTINUUM` and `C_EMPIRICAL` PCS claims remain
`OPEN` in the base authority. Specialized receiving reports label the new
mathematical model support explicitly. No certificate schema, existing authority
registry, historical evidence or learned-model promotion rule is changed.
