# Consistent storage observation and fixed schema enforcement

Stacked on PR #184 at `80767f6708d5a8eb44d077c031d6321ec0b88ccc`.
No Lean theorem statement, production authority, codec, tool pin or axiom policy
changes. The native supervisor still requires all 52 audited closures.

## Two actual parent failures

Both reproductions used the real pinned Lean authority and actual SQLite:

1. After a valid four-step workflow completed, a trusted-host schema fault renamed
   the public table, inserted the synthetic private canary into the renamed table,
   and installed a filtering view under the old table name. The parent returned a
   successful completed snapshot with only the approved summary, without detecting
   the substituted observation schema or the hidden underlying row.
2. An independent SQLite connection committed a row after the parent's final
   verification query but before `snapshot()` reread public output. The parent
   returned state/generation zero together with that unverified row.

These are storage/observer consistency defects. They are not producer SQL
injection, false Lean theorems or evidence that an unprivileged model can modify
the host. The producer interface still accepts only bounded action proposals.

## Implemented boundary

Every verified snapshot now owns an explicit read transaction covering schema,
receipt history, materialized rows and the returned public output. Verification
and output cannot observe different WAL snapshots. A concurrent foreign commit
can occur, but the current result reflects its checked read snapshot; the next
verification sees the changed database and refuses inconsistent state. A snapshot
is not a guarantee that no foreign writer can subsequently modify storage.

Step execution already uses `BEGIN IMMEDIATE`; pending-state validation remains
inside that transaction. Post-commit verification now also uses the owned snapshot
path. Nested/borrowed transactions and closed brokers refuse. Initialization
creates schema and seed rows in one transaction; failure rolls back and closes the
connection while retaining the failed ledger file. Existing ledgers still cannot
be adopted after restart without a protected external anchor.

`storage.py` checks the exact four table definitions and the two expected unique
indexes. Views, extra tables/indexes/triggers, missing or modified columns, TEMP
shadows and attached databases refuse before model-table observation or tool
execution. Catalog SQL is compared as data; no submitted schema code is adopted.
The check runs in the same owned transaction as the state observation.

Connection policy is fixed and rechecked: WAL, FULL synchronization, untrusted
schema callbacks disabled, ordinary committed reads, a 128-page logical database
budget, and SQLite limits for value/SQL length, attachments, trigger execution and
bound variables. Extensions are disabled on initialization. These are connection
and logical database defenses, not an OS disk quota, malicious-host sandbox or an
independently administered immutable root. SQLite itself remains trusted.

Stored events are bounded to four (the fixed workflow's rank bound). Receipt text
is bounded, strict JSON with exact shared fields, exact integer/Boolean types,
canonical lowercase digests/packets and exact canonical JSON storage bytes. Deep,
duplicate-key, nonfinite, malformed and ambiguous values refuse before hashing or
native verification. The existing digest/native-action/native-row checks still
run; strict storage parsing supplies no positive Lean verdict.

## Regression controls

New tests use actual SQLite to exercise schema drift, TEMP shadows, connection
policy changes, attachment limits, receipt/resource bounds and numeric aliases.
Real-Broker tests use the actual Lean/native authority for deterministic WAL
interleavings, the completed-ledger view substitution, malformed stored receipts,
closed/nested transactions and atomic failed initialization.

Existing pending-history corruption controls now inject corrupt data immediately
after actual INSERT/CAS statements, rather than installing a now-forbidden
trigger. This preserves testing of the independent precommit history audit.
Existing trigger controls additionally require snapshot refusal while the bad
schema exists, no committed effects, and a correct snapshot/retry after repair.
The worker reports the specific `StorageIntegrityError` for missing-schema faults;
no unauthorized effect or continuation is allowed.

```sh
python -m research.progress_supervisor_v1.ci test intake /tmp/new-storage-structural-tests
source scripts/activate_lean_428.sh
python -m research.progress_supervisor_v1.ci test replay /tmp/new-storage-runtime-tests
```

The source fingerprint includes the new storage contract. Capture/session/result
formats remain version 2; older captures still require their exact old source
revision. Historical evidence is retained. No production merge, website deployment,
protected restart availability, universal SQLite correctness proof, real-model
safety improvement, external scientific validation or training endorsement is
claimed. Faithful observation, compiler/Std/IO/OS behavior and complete mediation
remain explicit implementation/deployment obligations.
