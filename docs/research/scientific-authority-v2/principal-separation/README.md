# Distinct-user witness boundary: executed follow-up

A newly observed working managed Docker daemon supplied a route that the earlier
native `setuid`/user-namespace probe had not established. The earlier captured
Profile B BLOCKED result applies to that direct route and its original review
scope. This follow-up demonstrates a narrower, actual container data-plane
boundary under one trusted host administrator; Profile C remains unavailable.

The exact source is `../independent-review/container_principal_replay.py`, whose
SHA256 was frozen in `preregistration.json` before authorization execution. Run
it with the qualified Lean fixture environment and working managed Docker daemon:

```sh
python docs/research/scientific-authority-v2/independent-review/container_principal_replay.py /new/output-directory
```

The harness builds a scratch image without network/base-image downloads, mounts
only declared runtime/source trees, uses an internal Docker network with verified
TLS and an independently pinned witness public key, and launches a UID1000
witness and UID65534 producer. Both have zero effective capabilities, readonly
application mounts, no Docker socket and no production credentials. The producer
gets hash-identical public Python/client/dependency copies; original owner-only
source/toolchain permissions are unchanged. The witness alone receives its key
and SQLite mount. A separate actual UID65534 read probe inside the witness's
mount namespace fails with PermissionError. This tests DAC in addition to the
producer's absent key mount.

The witness actually checks genesis and a genuinely co-signed one-step artifact
with Lean4.28.0, durably prepares/finalizes it, and returns independently verified
permanent receipts plus a nonce-fresh signed checkpoint. A genuinely co-signed
false-total candidate rejects without reserving/advancing state. The complete
public signed evidence is retained in `result.json`; private fixture keys,
containers, internal network and this scratch image are removed afterward.

Scope is the producer-to-witness boundary. The complete local-COMMIT/coordinator
crash protocol and full19,878-dependency profile remain separately qualified under
Profile A; this follow-up uses an explicit partial dependency inventory and does
not establish that full protocol under separate users. The Docker daemon,
host/kernel, readonly mounts, trusted operator, key handling and storage remain
TCB assumptions. The host administrator retains Docker control and can override
these restrictions. Containers, ordinary permissions and distinct UIDs do not
establish an immutable root or independent administration. Existing rollback/
clone counterexamples still apply.

Development preflights initially failed before authorization because the
zero-capability root helper could not traverse owner-only public paths. A later
negative-read probe initially used that inaccessible interpreter rather than the
public system interpreter. Neither is an authorization pass. An attempted broad
venv copy was stopped and its own incomplete copy removed to preserve disk
capacity. The final harness copies only required public client dependencies and
passed two real boundary executions; this directory contains the final
self-hashed source execution, not retroactively relabeled failed preflights.
