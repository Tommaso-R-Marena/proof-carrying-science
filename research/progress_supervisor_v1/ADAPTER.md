# Transactional adapter refinement

Stacked on PR #182, exact parent `529c3bf1ea36accda42df14da2f6df8c774a5550`.
This research change retains all predecessor Lean statements, production authority,
codec/tool pins and trust policies. No Aristotle/PGSI module changes are included.

## Reproduced failure and implementation change

A fault-injected SQL handler in the parent called the original real handler,
inserted an unintended publication row, then returned its legitimate target.
The real Lean authority admitted the modeled action. The parent committed the
row, receipt and generation before its final materialized-history check raised
`materialized effects disagree with checked history`. The unintended row and
one committed receipt remained in SQLite. This is a transaction-ordering defect,
not a forged Lean verdict or a claim that an unprivileged model can patch Python.

The broker now computes the expected **entire materialized row state** before
calling the actual SQL handler. It validates the returned target's exact integer
type and all payload/public rows inside the same SQLite transaction, both after
the tool and after receipt/CAS writes. A mismatch raises before COMMIT, so SQLite
rolls back the effects, receipt and generation together. Missing/duplicate rows,
unknown strings, noninteger flags, unexpected publication and numeric target
aliases fail closed. The complete receipt/native/materialized-history audit also
runs before COMMIT against the prospective anchor. Metadata must contain exactly
one row; corrupted receipts, heads and duplicate metadata cannot be committed.
The live anchor advances only after COMMIT. A corrected retry retains its original
request identity.

`effects.py` supplies a small reference reducer independently of the existing
SQL statements in `Broker._apply`. It recognizes seven complete valid row/state
configurations. A snapshot is a frozen value; it is not a verifier or an immutable
host root. Native Lean authorization remains mandatory for every broker step.
No caller-selected verifier or positive response is added.

## Formal specification and exact scope

`Adapter.lean` represents the two fixed payload constants by a Boolean, flags by
Booleans and the number of fixed public rows by a natural number. `Valid` enumerates
the seven configurations; unknown strings/storage types are outside this model
and are rejected by the Python decoder. This describes the authored synthetic
SQL fixture, not semantic sanitization of arbitrary text.

The new ordinary-kernel theorems are:

- `PCSProgressAdapter.initial_valid`: both initial fixtures satisfy the invariant.
- `step_refines`: a successful modeled operation from a valid configuration
  preserves the complete row invariant, follows a progress edge and lowers rank.
- `valid_publication`: at most one publication, with a public, loaded, sanitized
  payload at the completed state.
- `goal_halts`: no modeled tool step from the completed state.
- `execution_invariant`: every finite modeled execution preserves validity and
  bounds its transition count plus remaining rank by its initial rank.
- `execution_no_private_publication`: the publication invariant holds after every
  such execution, conditional on initial validity.
- `completion_rows`: an execution reaching its initial rank has exactly the
  completed row configuration, including the single public output.
- `PCSProgressAdapterBridge.edges_declared`: every adapter edge is in the exact
  generated existing workflow model and its allowed action set.
- `step_declared`: a valid adapter step refines that existing model.
- `execution_path`: every valid adapter execution is an existing certified PCS path.

The bridge imports the exact generated `Data.lean`, so changes to the finite model
must pass this additional proof. It does not change the original certificate or
register an adapter for arbitrary models. These ten closures receive exact axiom
audits and a pinned `leanchecker --fresh AdapterTable` check. The existing
supervisor's 34 audited closures remain separate and unchanged.

This is **not a universal proof of the Python reducer or SQLite implementation**.
Python row decoding, transaction behavior, C compilation, IO and host enforcement
still require implementation correspondence and deployment assumptions. The
separate qualification is required in research CI; it supplies no runtime positive
authorization and does not replace the supervisor.

## Independent differential and fault controls

The bounded campaign enumerates 1,344 combinations: seven state IDs, eight action
IDs, both payload classes, both loaded/sanitized flags, and zero to two public
rows. This includes invalid/unreachable configurations. A freshly compiled Lean
table is compared with the **actual existing SQL handler**, while its validity
predicate is independently compared with the Python reference. For valid
configurations, both implementations must match the precomputed full row result.
Calling raw SQL in this campaign is explicitly an implementation test without a
verifier; it is never reported as authorization.

Separate real-Broker tests use the actual pinned Lean/native authority and inject
unintended rows, deletions, duplication, altered flags/content, incorrect or
Boolean/float targets, and receipt/CAS triggers, including receipt corruption and duplicate metadata. They require no committed effect
or event, unchanged state/head, closed transaction, and a successful corrected
retry. Both complete fixture branches are checked against the reference at every
step. Existing rollback, concurrency, process-crash, sealed-image, malformed codec,
replay and forged-proof controls remain required.

```sh
source scripts/activate_lean_428.sh
python -m research.progress_supervisor_v1.adapter /tmp/new-adapter-qualification
python -m research.progress_supervisor_v1.ci test adapter /tmp/new-adapter-tests
```

The qualification writes the actual tool execution log, ten axiom inventories,
source identities and machine-readable table. A generated executable is a
qualification observation, never an adopted producer verifier. No training,
external model evaluation, production deployment, external validation or general
AI safety claim follows. Captures are source-bound; earlier captures still require
their exact historical implementation. Historical evidence is retained.
