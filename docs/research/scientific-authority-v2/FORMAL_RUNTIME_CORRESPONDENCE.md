# Scientific Authority V2: exact formal scope and runtime obligations

## Source boundary and execution

This work adds only the isolated `research/scientific_authority_v2/formal/`
project and its checker. Its parent is PR158 at
`7be674df70eb3108c9dbd8b0b97f42a728bde000`. All existing scientific, history,
join, production and source-profile files are unchanged. The new standalone Lake
project imports the unchanged `PCSScientificHistoryV1` project and its pinned
dependencies. The toolchain is Lean 4.28.0 with the same nine Git revisions.

`FORMAL_THEOREM_INVENTORY.json` contains the complete statements, source lines,
source digests and actual axiom closures for authored and generated theorems.
The fresh checker also writes `formal-report.json` and the unabridged
`statements-and-axioms.log` under the new project's own `.lake/build/lib/lean/`.

For local checking with source-identical read-only imports:

```sh
python research/scientific_authority_v2/check_formal.py \
  --lean /absolute/path/to/lean-4.28.0/bin/lean \
  --dependency-checkout /absolute/path/to/reviewed-integration-checkout \
  --receiver-qualification /absolute/path/to/reviewed-receiver-qualification \
  --history-checkout /absolute/path/to/reviewed-history-checkout \
  --join-checkout /absolute/path/to/reviewed-PR158-checkout
```

The direct mode checks all old formal import source bytes, exact dependency
revisions, source admission, the compiler hash, qualified scientific artifacts
and the retained history/join artifact hashes. It rebuilds every new module and
audits every theorem in the new namespace. It does not rebuild all Mathlib or
prove prebuilt object/source correspondence. Outputs are never written into an
import checkout. For a standalone dependency build, use the same checker with
only `--lean`; it runs `lake build PCSScientificAuthorityV2` before the audit.

## Complete scientific audit: a genuinely checked starting point

The previous join's trace theorem required a scientifically valid starting
history. New `PCSScientificAuthorityV2.audit` accepts no such premise. It:

1. Checks the fixed scientific-history root policy.
2. Calls the actual `PCSScientificReceiver.receive` on the root's genesis bytes.
3. Starts at the root-bound empty-history initial state.
4. Runs `scientificTransition` on every supplied envelope in order.
5. Rejects the whole audit on the first rejected envelope, rather than skipping it.

`audit_sound` proves that success implies checked genesis; scientific validity of
every retained candidate; both root-pinned signature checks on every event;
exact authority/witness/policy/checker scope; predecessor linkage; exact envelope
history; generation equal to genesis plus event count; and final incumbent equal
to the last supplied candidate, or genesis for an empty list.

For every member, `audited_entry_scientific` obtains the existing exact-wire
`ScopedScientificClaimHolds` conclusion and empty auxiliary certificate.
`audited_incumbent_scientific` obtains the same property for the final incumbent.
`audited_signatures_authenticated` additionally requires the explicit soundness
premise connecting the abstract signature verifier's true result to the chosen
authentication predicate. No cryptographic axiom is silently introduced.

The mathematical auditor covers every finite typed envelope list whose checks
succeed. Runtime limits (for example maximum history count/bytes and wall time)
restrict execution to a supported subset. The scientific semantics remain the
existing bounded rational, finite discrete A→B model. They do not establish
empirical adequacy, general kinetics, continuous-time accuracy or physical units.

## Honest serial witness and commitment phases

`Witness` contains a committed history state and at most one `Prepared` record.
`prepare` executes the actual joined scientific/authorization decision before
creating that pending record. An identical retry can reuse it; an incompatible
pending request leaves state unchanged. No committed state changes during prepare.

`finalize` can atomically advance only the exact pending envelope whose stored
predecessor still equals the committed state. True means a **new advancement**;
a network endpoint may instead return an old idempotent receipt without such an
advancement. The model does not equate an idempotent read with a second commit.

`PendingSound` and `WitnessInvariant` are proved by checked initialization and
preserved by every model prepare/finalize action. The invariant's complete audit
is constructed using `audit_append_accepted`; it is not received as a producer's
unchecked assertion. `finalize_prepared_science` therefore derives the exact
candidate's mathematical soundness. A corrupted arbitrary pending object need
not satisfy this invariant; honest durable-state continuity is a real premise.

`no_conflicting_finalization_later` proves that after one successful finalization,
no envelope from that consumed predecessor generation can be finalized after any
later serial prepare/finalize trace. It relies on the same retained witness
state, fixed root/verifier and its established invariant. It is not consensus
between replicas, resistance to witness rollback, or protection after witness
key/OS compromise. Root/key/checker rotations are absent from the action language.

## Local commit, serving and recovery

`Authority` separates local state from witness state. `localCommit` changes only
the local state and only for the exact pending predecessor/envelope.
`local_commit_without_finalization_not_serving` proves that this state is not
serving-eligible. The deliberately conservative serving rule also halts the old
state while any prepare is pending.

Serving returns a full state only when the local state equals the witness's
finalized state and no pending record remains. `serving_artifact_scientific`
derives a complete checked archive and exact scientific soundness from the
witness invariant. `initialized_trace_serving_scientific` closes that invariant
through actual checked initialization and an arbitrary model action trace: its
premises do not include the desired scientific validity as an opaque proposition.

Finalization explicitly does **not** assert observation of a remote SQLite
commit: `witness_finalize_does_not_assert_local_commit` leaves local state alone.
If final witness state and local state disagree, serving rejects. Two independent
atomic database commits are never treated as a single distributed transaction.

`recover` reruns the actual complete mathematical auditor, requires its exact
result to equal the pinned finalized witness state, and requires no pending
record. It cannot create a new witness authorization. `recovery_sound` proves
the unchanged witness identity, exact audited archive/local checkpoint,
no-pending condition, serving eligibility and full scientific audit facts.
Missing events, invalid science, an unknown suffix or a different checkpoint
reject. The runtime must resolve a legitimate prepared transaction through the
actual witness protocol before this final recovery rule can succeed.

## Transition-correspondence table

| Executable boundary | Pure formal operation/result | Evidence status and remaining obligation |
| --- | --- | --- |
| Canonical scientific wire → decoded contract/result | Existing `receive` / `verifiedWireSound` | Kernel-proved pure bytes/semantics; actual framing/IO/compiler correspondence remains tested |
| Historical store/export → typed root/envelope list | Inputs of `audit` | Python JSON, signatures, storage and artifact retrieval are not Lean-refined |
| Genesis and every candidate actually reexecuted | `audit`, `auditFrom`, `audit_sound` | Pure accepting function proved; host/process execution and time budgets are runtime tests |
| Fixed root and historical intent authentication | `scientificTransition`, `audited_signatures_authenticated` | Signature callback origin requires explicit soundness; Ed25519/library/role-domain code remains trusted/tested |
| Durable witness prepare | `prepare` and preserved `PendingSound` | Atomic honest record modeled; SQLite transaction/persistence/error behavior remains tested |
| Local SQLite COMMIT | `localCommit` | Separate atomic action, never external witness publication |
| Durable witness finalization | `finalize` | Exact prepared successor proved; honest retained state and atomic storage assumptions remain |
| Fresh signed witness checkpoint + exact local match | `serve` | Model uses a trusted current witness state; nonce, transport, pinned public key and freshness are runtime obligations |
| Lost return, rollback or mismatched local checkpoint | `mismatched_local_checkpoint_not_serving` | Safe refusal proved in model; actual process-crash cases are separate evidence, not power-failure tests |
| Verified retained archive reconstruction | `recover`, `recovery_sound` | Actual audit and exact witness equality proved; authenticated export, retrieval and materialization remain tested |

The model does not prove Python-to-Lean, JSON-to-typed-envelope, cryptographic,
SQLite, networking, source-to-object, compiler or operating-system refinement.
It does not prove nonce freshness or independently administered witness keys.
The third post-verification witness key and signed response codec are runtime
components; the old `Root.witness` field is still the second **intent** signer.

## Nonvacuity and negative models

Kernel fixtures demonstrate a real pure-science accepted genesis and nonempty
audit, prepare, local commit, finalized serving and exact recovery. They also
reject duplicated history, malformed old science followed by valid final bytes,
invalid genesis, serving during preparation/local-only commitment, missing
recovery data and a rolled-back local checkpoint.

`simultaneous_root_replacement_countermodel` constructs two distinct authority/
checker bootstraps whose valid genesis passes self-consistency. This is a
restricted root-substitution countermodel: self-consistency cannot identify an
externally intended root when that trusted reference was replaced. It is not a
general cryptographic impossibility or a theorem about the runtime witness codec.

`mathematical_acceptance_not_empirical` supplies a logical countermodel in which
the actual mathematical audit succeeds while an extra empirical predicate is
false. It proves logical independence, not physical falsification of A→B.

Fixture signature verification is a finite symbolic allowlist. It is explicitly
not Ed25519, an executed service attestation or independently administered
authorization. Runtime positive tests must use actual Lean and real signatures.

## Trust and historical meaning

The new pure audit establishes **retrospective mathematical validity** under the
pinned scientific interpretation. It does not establish that anyone ran the
checker when a historical event was committed. A post-verification witness
signature can support that stronger interpretation only with separate honest
witness execution, cryptographic, trusted-bootstrap and durable-state assumptions.
Root/checker/key byte strings in Lean are opaque and need not have the runtime
codec's concrete widths or SHA256 interpretation. Whole-history completeness is
relative to the receiver's independently retained final checkpoint and root.

The honest single-witness non-equivocation result ceases to apply if its durable
state is rolled back or cloned into divergent instances. Simultaneous replacement
of every trusted bootstrap/checkpoint is outside detection. Same-host processes,
ordinary hashes, filesystem permissions and Python object privacy do not establish
an immutable or independently administered root.
