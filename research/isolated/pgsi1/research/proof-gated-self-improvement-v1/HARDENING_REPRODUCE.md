# Reproduce the PR #117 hardening research

Use a Linux host with unprivileged user namespaces, Bubblewrap, `/usr/bin/cc`,
`strip`, Python 3.12 and the existing pinned Lean 4.28 toolchain. No Mathlib,
model API, GPU, production credentials or new service subscription is needed.
An unavailable sandbox is a failed isolation qualification, not permission to
replace the verifier or claim a successful authorization.

From the repository root:

```sh
source scripts/activate_lean_428.sh
cd formal
lake build PCS.V2.ProofGatedSelfImprovement PCS.V2.ProofGatedSymbolic PCS.V2.ProofGatedArtifacts PCS.V2.ProofGatedPromotion PCS.V2.ProofGatedInference PCS.V2.ProofGatedMultilayer
lake env lean PCS/V2/ProofGatedAudit.lean > /tmp/pgsi-axioms.log
cd ../research/proof-gated-self-improvement-v1
python validate_formal_boundary.py --audit /tmp/pgsi-axioms.log
# Every output directory must be NEW; existing evidence is never replaced.
python build_authority.py --output /tmp/pgsi-native-owner
export PCS_PGSI_AUTHORITY_BUNDLE=/tmp/pgsi-native-owner
export PCS_PGSI_REQUIRE_NATIVE=1
python -m unittest discover -s tests -v
python check_hardening_evidence.py
python scientific_campaign.py --bundle "$PCS_PGSI_AUTHORITY_BUNDLE" --output /tmp/pgsi-experiment-new
```

The build uses the original formal module C outputs, renames only the old CLI's
C entry point to avoid a duplicate host `main`, and links a small reviewed IO
adapter. System C compilation/runtime correctness is a named trusted assumption.
The native manifest records actual binary/tool/source pins; different rebuild
pins do not establish a scientific difference. Quantitative semantic decisions
must reproduce; wall-clock measurements need not.

`TransactionalStore` is the new research path. The original
`ResearchPromotionStore` remains compatible and retains its historical
fail-closed orphan-receipt behavior; no silent v2 data migration occurs.
A new store requires a fresh owner-selected genesis and pinned authority. An
existing v3 store refuses a changed authority manifest; future upgrades require
an explicitly reviewed state/policy migration.

## Separate service and pinned client

An owner launches `authority_service.py --bundle BUNDLE --database NEW.sqlite
--socket PRIVATE.sock --initialize` in a private directory. The owner retains
the actual `subprocess.Popen.pid`, then constructs
`PinnedClient(socket_path, server_pid)` and calls `.request(...)`. Do not discover
a trusted PID from an arbitrary socket or give the proposer control of launch
configuration. Use `with PinnedClient(...) as client` or close its retained pidfd.

Accepted request shapes are exact:

- `{"op":"status"}` returns a replayed current head and owner authority identity.
- `{"op":"promote","candidate_hex":"...","expected":HEAD,"request_id":"32 lowercase hexadecimal digits"}` returns both the historical committed head and the current head. Retrying an old acknowledgement does not activate that old model.
- `{"op":"infer","expected":HEAD,"checkpoint":HEAD_OR_NULL,"xs":[-20,0,20]}` returns predictions from a single validated snapshot. Retain expected heads through an independently trusted channel if rollback protection is required.

All response provenance still depends on the trusted owner/kernel/process. Same-
UID database modification and full-history rollback remain possible; the system
is not a separately administered immutable root. Test code demonstrates this
limitation rather than hiding it.

## Fresh independent receiver

`store.export_history(expected=retained_head)` returns exact canonical receipt
bytes, model bytes and the producer's declared manifest. Save that object using
`promotion_v2.canonical(package)` to a new history file. Save the independently
retained head separately, also canonically; do not obtain a supposed trust anchor
only from the untrusted package.

```sh
python replay_history.py --bundle RECEIVER_OWNED_BUNDLE \
  --history history.json --expected-head independently-retained-head.json \
  --output new-receiver-report.json
```

The receiver can rebuild its own pinned executable. It checks source identity,
chain/request bindings, every transition with its own actual native authority,
and active Python/Lean predictions on receiver-selected integer inputs. It
reports **producer_history_authenticated=false** because receipts are unsigned.
Semantic replay is useful even though it cannot prove the producer historically
ran that code or establish an external monotonic checkpoint by itself.

## Future Aristotle integration

`ARISTOTLE_INTEGRATION_BOUNDARY.json` pins the actual seven formal files at the
inspected PR head. A source change intentionally stops qualification. New PGSI1
serialization/roundtrip results or generalized architectures must arrive as
final source artifacts, build independently, retain explicit assumptions, and
pass all 8,450 original-model cases, malformed encodings, native prediction and
transition comparisons. Do not silently loosen parsing or accept a newer magic
version. Keep old valid artifacts and historical evidence available.
