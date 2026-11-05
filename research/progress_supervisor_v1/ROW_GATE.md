# Native row refinement before SQL commit

Stacked on PR #183 at `453c29e4b7aaf666d16d47c5510d423cb524347f`.
The preceding adapter specification and all protected PCS/Aristotle/PGSI theorem
statements remain unchanged. Production authority is not modified or registered.

## Executable boundary

The fixed broker now requires **both** the existing native action decision and an
actual native Lean decision on the complete before/after row snapshots. The row
gate runs in a fixed `--rows-v1` mode of the same source-qualified, fresh-kernel-
checked, Linux-sealed executable. There is no caller-selected verifier or binary.
The original action mode runs with no arguments and retains its existing bytes.
The Python projection and full pending-history checks remain additional defenses.
A negative, malformed, missing or failed row response aborts before SQL COMMIT.

The row request is exactly 16 bytes:

| Bytes | Meaning |
| --- | --- |
| 0–4 | ASCII `PCSR` and version byte 1 |
| 5–6 | State and selected action |
| 7–10 | Before: public-payload flag, loaded flag, sanitized flag, public row count |
| 11 | Observed target state |
| 12–15 | After: the same four row fields |

Flags have exactly the encodings 0/1. State/action/count fields fit one byte;
this is the fixed synthetic workflow, not a replacement for the existing general
16-bit action wire format. Unknown versions, malformed lengths and alternate
flag encodings refuse. A response `[2,1]` means that decoded before-rows satisfy
the existing `Adapter.Valid` invariant and the exact specified operation produces
the decoded target/after-rows. `[2,0]` refuses. Raw batch observation APIs do not
independently authorize tools; the broker requires the exact fixed model and
certificate and separately verifies its native action decision.

The SQL observer rejects unknown strings, missing/extra rows, invalid storage
types and flags before encoding. Public rows represent the literal fixed public
summary, not arbitrary sanitized text. The mapping from SQLite values to those
fields remains trusted/tested Python. This is not a universal proof of SQL or a
semantic sanitizer.

## New ordinary-kernel theorems

`PCSProgressRows` adds eleven named closures:

- `flag_bit`: recovering a canonical flag returns its original bounded number.
- `request_roundtrip`, `request_canonical`, `request_injective`: bounded typed
  requests round-trip; every successfully decoded request has one exact encoding.
- `check_sound`: a positive typed check supplies initial validity and the exact
  modeled row operation.
- `raw_acceptance`: positive raw bytes decode canonically and satisfy that check.
- `raw_refines`: accepted bytes preserve the row invariant, follow the adapter
  edge and decrease rank.
- `malformed_refuses`: decoding failure cannot produce acceptance.
- `process_octets`, `batch_octets`, `native_octets_roundtrip`: native output
  conversion cannot silently truncate a response.

The seven existing adapter closures are now compiled, audited and fresh-checked
in the native supervisor's actual import closure. Together with the unchanged
34 closures and eleven new wire closures, this makes **52 required runtime
closures**. The separate fixed-model bridge qualification remains required; it
connects adapter edges to the exact generated workflow certificate. No new axiom,
`sorry`, `admit`, `native_decide`, source gate relaxation or tool-pin change is used.

## Replayable row evidence and explicit migration

New receipts include `row_request_hex` and `row_reply_hex`. Pending-history audits
reconstruct these snapshots, rerun the actual native gate, and compare both byte
strings. Replay validates all row claims before creating output files, then
rebuilds its own executable and reruns the action/row gates and actual SQL tools.

Publication additionally generates `CaptureRows.actual`, an ordinary-kernel proof
of the exact observed row packets and replies. Batch/process output includes this
proof alongside the existing wire/path proofs. Workflows own their proof paths;
no generated producer proof or executable is adopted as receiving authority.

Captures/results/session envelopes advance explicitly to version 2. Version 1
captures must use their exact historical source revision; current intake refuses
them. Existing model/certificate formats, action-only producer inputs and the
original native action wire remain unchanged. Historical evidence is retained.

## Qualification and limits

The new required rowgate CI shard checks 225,792 bounded combinations of before
and after snapshots, including invalid/unreachable configurations. Exactly six
transition shapes are accepted. It additionally checks 4,096 field-byte mutations,
partial/trailing frames, exact integer types, staged-object substitution, actual
kernel refusal of forged acceptance, and a faulty SQL operation paired with an
incorrect agreeing Python projection. That last control must still be refused by
the real native row gate with no committed effect or receipt.

```sh
source scripts/activate_lean_428.sh
python -m research.progress_supervisor_v1.ci test rowgate /tmp/new-row-gate-tests
python -m research.progress_supervisor_v1 demo /tmp/new-row-gated-capture
python -m research.progress_supervisor_v1 replay /tmp/new-row-gated-capture/capture.json /tmp/new-row-gated-replay
```

The formal specification, actual native observations and host correspondence are
separate claims. Python/SQLite observation and transaction fidelity, C compilation,
Std/IO, OS and mediation remain trusted/tested. A malicious same-user host can
replace enforcement; a sealed executable is not an independently administered
immutable root. Existing ledgers still refuse unanchored restart. No production
deployment, real-model safety improvement, external scientific validation or
training-data endorsement follows from the synthetic experiment.
