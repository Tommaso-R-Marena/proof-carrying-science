# Kernel-checked recorded transport traces

The existing all-time matrix assurance now has an opt-in receiving extension:
`pcs transport-trace-kernel-v1`. It freshly proves that **every parsed recorded
state and timestamp** agrees with the declared recurrence and time grid. A false
Python arithmetic report cannot grant this new finite-trace support.

The receiver accepts the same typed v3 contract and CSV, or an existing signed
v3 package. The positive example is the existing CC0-authored synthetic numerical
computation. This is not empirical validation, external human review, or a new
scientific discovery. External AI-safety research remains deferred; no Aristotle
proof-development traces are training inputs.

## Exact new mathematics

All names below have prefix `PCSReal.TransportTrace`:

| Theorem | Result |
| --- | --- |
| `bounded_recurrence_unique` | Initial equality and every bounded one-step equality uniquely determine every recorded state. |
| `check_sound` | A true exact-rational finite Boolean certificate implies state equality to iteration and the exact timestamp grid at every recorded index. |
| `recorded_invariants` | The recorded states inherit amount conservation, common bounds, and the initial quadratic bound from the certified matrix. |
| `adjacent_quadratic` | The quadratic functional is nonincreasing between each recorded pair. |
| `cast_step` | Exact rational update commutes with embedding into the reals. |
| `cast_evolve` | The same embedding commutes with every natural-number iteration. |
| `real_trace_sound` | The checked rational recorded states agree exactly with the real-valued model initialized by the embedded initial state. |

Five static controls in `PCSReal.TransportTraceControls` are `good_trace`,
`good_trace_evolves`, `wrong_initial_rejected`, `wrong_step_rejected`, and
`wrong_time_rejected`. The complete 12-name audit permits only `propext`,
`Classical.choice`, and `Quot.sound`, or fewer.

For each supported CSV, five new named literal theorems in
`PCSTransportTraceReplay` are regenerated: `trace_checked`,
`recorded_states_and_times`, `recorded_invariants`, `adjacent_quadratic`, and
`recorded_real_states`. Together with the existing matrix declarations and new
general library, a positive receiving run audits 30 exact theorem identities.
An incorrect trace can instead receive the actual kernel proof
`PCSTransportTraceReplay.trace_rejected`. Compiler failure or resource exhaustion
alone never establishes this negative result.

## Receiving protocol and trust boundary

The receiver parses only bounded data. It compares all current-input rational
scalars with the existing v3 parser, checks contract/model/data byte identities,
and independently retains the prior matrix/finite arithmetic replay. It then
copies its own matrix and trace theorem sources into a private directory,
compiles both afresh, and compiles fixed proof text containing only canonical
rational literals and validated hash comments. No submitted Lean or project code
is run. All complete theorem inventories are audited. Pinned Lean 4.28.0,
Mathlib `8f9d9cff6bd728b17a24e163c9402775d9e6a365`, and their installed
compiler/dependency artifacts remain trusted infrastructure.

The four literal predicates are positive matrix certification, initial bounds,
finite recurrence, and timestamp equality. Matrix certification remains distinct
from finite trace support: an invalid CSV can have a valid model and a separately
kernel-refuted trace. An existing v3 signed package must first pass its original
receiving authority and replay before the new extension can accept it. A private
bounded ZIP snapshot binds signed verification and trace extraction to the same
bytes. Base schemas and verification authority are unchanged.

Each Lean process retains the 2,048 MiB cap and sequential elaboration. The
existing model stage and new trace stage each have a separate total kernel wall
budget of at most 180 seconds (default 120 each); parsing and existing signature/
package replay are outside those kernel budgets. Intake remains 2–16 cells,
1–64 steps, 2 MiB raw artifacts, and 4,096-bit rational scalars; signed ZIPs are
bounded to 32 MiB. These are input ceilings, not a promise that every maximum-size
certificate completes within the resource caps. Exhaustion grants no support.

Theorems concern the exact numeric literals reconstructed by the receiver.
Universal correspondence of the CSV parser, Python execution, native floating
point, compiler, OS, physical model and measurements is not established.
Implementation correspondence, continuum accuracy, empirical validity, and the
base C_NUMERICAL/C_CONTINUUM/C_EMPIRICAL claims remain OPEN.
`scientific_acceptance` and `pcs_authority` remain false.

## Replay and review

Use the setup for the [all-time matrix kernel](PCS_TRANSPORT_KERNEL_V1.md), then:

```sh
python -m pcs.cli transport-trace-kernel-v1 \
  --contract examples/scientific_workflow_v3/contract.json \
  --trajectory examples/scientific_workflow_v3/trajectory.csv \
  --output /tmp/pcs-trace-receipt-new
```

For a signed package, substitute `--bundle FILE --public-key PUBLIC.pem
--fingerprint PINNED_FINGERPRINT`; build the existing native authority first.
A new output directory is required. It contains the canonical report, exact data
certificate, regenerated Lean source, receiving-source snapshots and SHA-256
inventory; negative runs retain the separately proved rejection source.

The required real-analysis CI lane builds the full real bridge, checks all 12
new static declarations, executes required-kernel tests including forged Python
success and 64-step/16-cell boundaries, and runs fresh receiving processes with
actual signed package controls. New evidence is versioned separately from all
prior matrix/scientific executions. Research adoption remains experimental in
this exact-rational model fragment.
