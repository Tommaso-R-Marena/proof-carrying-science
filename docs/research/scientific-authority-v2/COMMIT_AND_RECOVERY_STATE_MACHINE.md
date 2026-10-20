# Staged commitment, eligibility and executed crash matrix

## Ordering and meaning

1. The operator pins the scientific root/profile and a third distinct witness
   public key. Requests carry only exact canonical signed intent bytes.
2. Coordinator authentication/CAS/resource preflight checks the entire prospective
   history before requesting any durable reservation.
3. PREPARE authenticates both intent signatures, actually runs the fixed Lean
   receiver, and durably reserves one exact checked successor in the witness.
4. The unchanged local `History.append` independently repeats authentication,
   predecessor/freshness/generation/incumbent CAS and commits exact original bytes.
5. FINALIZE durably advances the witness to its own previously checked pending
   record. It does not attest observation of the coordinator's SQLite commit.
6. Complete local scientific audit and a nonce-fresh pinned witness view must
   agree before an eligible snapshot is returned. Any pending witness record
   halts eligibility, including eligibility of the previous matching state.

The linearization points are separate SQLite COMMITs. No atomic transaction
spans the two processes. A returned snapshot is an immutable checked artifact
and authenticated observation, not a perpetual lease or production-serving API.
Later readers need their own fresh witness challenge to establish currentness.

## Executed failure windows

The table is backed by actual `os._exit(71)` in coordinator or witness processes,
including SQLite trace callbacks after real INSERTs and before COMMIT. Fault
injection only terminates real execution; it never synthesizes a positive verifier.
All ten cases pass as part of the17-test coordinator suite (385.10s).

| Crash point | Local generation | Witness generation | Pending | Explicit recovery |
| --- | --- | --- | --- | --- |
| Before PREPARE |0|0|No| Remains0; no reserved candidate is invented |
| After PREPARE |0|0|Yes| Exact retained intent materialized and finalized to1 |
| During local transaction |0 after SQLite recovery|0|Yes| Exact pending recovery to1 |
| After local COMMIT |1|0|Yes| Exact local successor checked and witness finalized to1 |
| After FINALIZE |1|1|No| Re-audit matching finalized state1 |
| Before eligibility |1|1|No| Re-audit matching finalized state1 |
| After eligibility, before return |1|1|No| Lost return introduces no new authorization |
| During witness PREPARE transaction |0|0|No| Reservation rolled back; remains0 |
| During witness FINALIZE transaction |1|0|Yes| Final transaction rolled back; exact recovery to1 |
| After witness FINALIZE COMMIT, before response |1|1|No| Fresh witness view resolves lost response at1 |

Machine-readable states, exit codes and observed durations are in
`DISTRIBUTED_CRASH_MATRIX.json`. Per-case timing starts after fixture setup;
the suite duration includes setup. This is process-crash evidence, not physical
power loss, drive-flush verification or a theorem of real distributed durability.

## Recovery algorithm

`recover` obtains a fresh authenticated witness export, checks genesis and every
retained artifact through the actual receiver, and authenticates the exact intent
sequence. It compares the local database against the bounded list of exact known
witness prefixes, including the one unique pending successor where applicable.
Exactly one match is required. Unknown forks, suffixes, altered bytes, missing
material, wrong keys/roots/profiles or unavailable witness cause refusal.

Missing locally materialized finalized records may be appended from the exact
witness-retained signed envelopes. This replays existing authorization; no new
signature, candidate or policy is created. A pending reservation requires explicit
`resolve_pending=True`; its entire prospective history receives real scientific
replay before the exact reserved intent can be materialized/finalized. It cannot
be replaced by another proposed artifact.

The recovery invocation reuses only its own immutable actual scientific results,
then rechecks exact local bytes/authentication and obtains another fresh witness
checkpoint. No caller-supplied audit cache can skip checks. Concurrent witness
advancement makes the result fail closed; safe refusal is not general liveness.

Missing databases are not silently initialized. Operator-authorized genesis
creation is a different explicit operation. Replacing both stores and every
latest checkpoint can restore an indistinguishable old world; external monotonic
continuity is necessary to exclude that adversary.
