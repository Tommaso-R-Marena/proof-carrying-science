# Proof-carrying error envelopes for approximate transport traces

An exact trace can fail the old checker while remaining close to the declared
discrete model. This research extension certifies that distance. It adds files
only, stacked on frozen PR172 `c49308fa958703e8d90d8662232995ec6460a5cd`.
Every predecessor blob and mode, production authority, old parser/checker and
Aristotle module remains unchanged. No merge or deployment is included.

## Use an existing lab export

Save a case from the lab as `inspected-case.json`. From the research checkout,
activate the existing Lean4.28.0/Python environment, then:

```sh
# Fast exact diagnostic proposal; this does not run Lean.
python -m research.trace_envelope_v1 analyze inspected-case.json --tolerance 1/100

# Actual fresh Lean proofs, exact axiom inventories and captured evidence.
python -m research.trace_envelope_v1 check inspected-case.json ./envelope-evidence --tolerance 1/100

# Reviewer regenerates everything with reviewed local sources and runs Lean again.
python -m research.trace_envelope_v1 verify ./envelope-evidence ./independent-evidence
```

Use a fresh output directory every time. Exit0 means a Lean-checked envelope
within the requested tolerance. Exit10 means a Lean-checked envelope whose
**cumulative budget exceeds tolerance**. It does **not** prove that actual error
exceeds tolerance: cancellation and mixing can make the budget conservative.
Exit20 means refusal, unavailable tools or exhausted resources; no affirmative
kernel verdict. Argparse usage errors exit2. `analyze` exits0 for a successfully
computed diagnostic proposal, with `kernel_checked=false` regardless of its budget.

Tolerance has the same concentration units as the contract. It bounds the absolute
error of every coordinate at every recorded step against the **declared exact
discrete recurrence**, not a continuum solution, physical measurement, or solver
implementation. Timestamps must match the declared schedule exactly. This is a
separate research claim type; it cannot authorize or weaken the old exact checker.

## What is proved

Let P be the old `Certified` matrix, x0 the declared initial state, and yk the
recorded states. Given coordinatewise bounds

```
|y0 - x0| ≤ eta
|y(k+1) - P*yk| ≤ eps(k)
R(0) = eta; R(k+1) = R(k) + eps(k)
```

Lean proves `|yk - P^k*x0| ≤ R(k)` for each coordinate and k≤N. Nonnegative
local budgets imply R(k)≤R(N); therefore R(N)≤tolerance certifies a uniform
bound for the entire recorded trace. The rational result also lifts to the
corresponding real-valued recurrence. State bounds are expressed as two exact
inequalities in `Within`; no floating point or native proof reduction is used.

Thirteen ordinary theorems in `PCSTraceEnvelope`:

| Theorem | Guarantee |
| --- | --- |
| `step_sub` | Matrix updates distribute over differences. |
| `within_step` | A certified stochastic update cannot increase a uniform coordinate error bound. |
| `step_add_const` | A stochastic update preserves a uniform additive offset. |
| `coherent_residual` | A linearly drifting offset creates exactly the declared constant local residual. |
| `radius_constant` | Constant local budgets accumulate to eta+k*epsilon. |
| `coherent_sharp` | Coherent drift attains that radius exactly: worst-case linear accumulation is sharp. |
| `within_trans` | Error envelopes compose by addition. |
| `propagate` | Local residual bounds imply complete finite-trace error bounds. |
| `radius_mono` | Nonnegative local budgets make the radius monotone within the horizon. |
| `uniform` | A final-radius threshold implies a uniform bound throughout the trace. |
| `check_sound` | The finite rational checker implies recorded error bounds and exact times. |
| `check_uniform` | The checker plus final threshold implies uniform tolerance. |
| `real_bound` | Rational error inequalities transfer to the corresponding real recurrence. |

`within_step`, `propagate` and tolerance results use the unchanged `Certified`
contract: positive cell volumes, nonnegative coefficients, row sums1, invariant
volumes. The error argument needs the stochastic component; the old stronger
contract supplies it. Volume conservation is not a consequence of approximate
trace acceptance. Bounds apply only through the declared finite horizon. No new
axioms, `sorry`, native decision shortcut or modified mathematical specification.

## Evidence and trust boundary

Python is an untrusted proposer. It computes the maximum initial residual and
each row's maximum local residual using exact fractions. Generated Lean proves
every local inequality, cumulative displayed radius, model contract and timestamp.
It also proves the exact final-budget comparison, either direction. A dishonest
zero residual or radius fails actual Lean. The finite residual budget need not
be an optimal bound on the actual accumulated error.
Signed residual details and minimality of the proposed local maxima are diagnostic
Python results, not separately kernel-proved equalities; their proposed upper
bounds and every displayed cumulative radius are checked by Lean.

Each replay captures the original export bytes, interpretation, generated proof,
reviewed source bytes, tool hashes and complete theorem axiom inventories. Only
`propext`, `Classical.choice`, `Quot.sound` are allowed. Compiler and checker bytes
are pinned to the previously reviewed Linux x86_64 Lean4.28.0 binaries before and
after execution. Each replay compiles the captured transport, trace, envelope and
raw ordinary-kernel tactic modules afresh. The `audit` command additionally runs
official `leanchecker --fresh Envelope` and audits all34 old/new general statements.
Staged source copies are compared before/after compilation and again after replay;
review exports use the original captured bytes even if input paths change.

Reviewer replay snapshots bounded files once, checks the exact allowlisted hash
inventory and equality with its own reviewed sources, regenerates the proof, and
executes Lean. Stored `result.json` is never read as a verdict. Rehashed changes
to source or generated proof fail. Hashes identify bytes, not authors; evidence
is not a signed receipt. Python object privacy, same-user storage and binary pins
are not immutable or independently administered trust roots. Imported Mathlib
cache objects, compiler/OS and host control remain trusted. The audit is a replay
by the same kernel, not an external proof implementation or full Mathlib rebuild.

The old parser's interpretation is preserved. The relation between original
JSON/CSV bytes, decoded mathematical literals and external executable behavior is
still tested rather than formally refined. This phase does not close that gap.
Malformed/duplicate-key/unknown-format data, wrong timestamps and negative tolerance
are refused. Replay is capped at8 cells,16 steps,256KiB exports and the existing
4096-bit rational limits; numeric exponents are preflight-limited to±512 before
allocating powers. Larger models and the old exact replay remain separate paths.
This additional bounded subset does not change accepted artifacts elsewhere.

## Reproduce the tests and synthetic research

```sh
source scripts/activate_lean_428.sh
python -m research.trace_envelope_v1 audit ./new-general-audit
python -m research.trace_envelope_v1.experiment --out ./new-experiment
python -m pytest -q research/trace_envelope_v1/test_envelope.py research/portable_transport_v2/test_replay.py
python -m research.trace_envelope_v1.preservation
python -m research.integration_v1.source_gate
```

The deterministic experiment covers432 constructed cases: widths2,3,5,8;
horizons1,4,16; seeds0,1,20261022; decimal precisions2,4,8; coherent drift,
alternating cancellation, separately rounded reference rows and in-loop rounding.
An independent edge-flux implementation supplies reference states. It tests every
row against its envelope, confirms coherent-drift tightness, and preserves
conservative budget failures. The matrix P=2I negative control shows why dropping
row stochasticity invalidates a nonamplifying bound. These are synthetic rational
experiments, not population estimates, physical validation or learning evidence.
Selected instances and forged-proposer failures additionally execute real Lean;
the432-case experiment itself is not labeled kernel checked.

Next: formally verified decoding/list-to-vector refinement, larger-horizon proof
partitioning, and model-specific contraction certificates that can replace the
worst-case cumulative radius with tighter bounds. Future Aristotle codec work
remains an independent reviewable integration.
