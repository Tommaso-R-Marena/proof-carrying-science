# Open trust assumptions — Workstream C

This list is derived from the read-only TCB atlas (`python_harness/tcb_atlas.py`)
and `formal/PCS/V2/TCB.lean`. It is an **independent evaluation** inventory, not a
new formal proof obligation set.

## Cryptographically assumed

| ID | Meaning |
| --- | --- |
| `Sha256Collision` | Collision / second-preimage resistance of SHA-256 |
| `NoForgery` / `ed25519Unforgeability` | Unforgeability of Ed25519 for the trust-anchor key |
| `ZipDecoderFaithful` | Archive extractor returns exact `(name, bytes)` members |
| `ProductionRefinesLean` | Production acceptance implies Lean `acceptArchive` |

## Externally trusted

| ID | Meaning |
| --- | --- |
| OS / filesystem I/O | Bytes delivered to the verifier match the intended archive |
| Lean kernel foundation | `propext`, `Classical.choice`, `Quot.sound` |
| Python runtime | Interpreter and stdlib/`cryptography` used by production paths |
| Reviewer policy document | Out-of-band acceptance criteria and pinned signer fingerprints |
| Scientific predicate | User-supplied `Holds` / `Describes` meaning |

## Executable-tested (not kernel-proved for production wiring)

| ID | Meaning |
| --- | --- |
| SHA-256 / Ed25519 Lean transcriptions | Spec faithfulness via KATs / known-answer vectors |
| Production hashlib / JCS differential suites | Finite tested correspondence, not universal refinement |
| Authority transcripts / verification receipts | Format and harness checks |

## Unresolved / not claimed by v0.6 Lean model

| ID | Meaning |
| --- | --- |
| Environment reconstruction fidelity | Lean marks `reconstructionFidelity` as not applicable; cross-host hermetic rebuild is an engineering obligation (Task 12 measures what this checkout can show) |
| Lean authority binary identity | Task 12 records `pcs-lean-authority` path + SHA-256 when present; absence is explicit. Byte identity across hosts is never assumed without comparing digests |
| Container / R runtimes | Named hypotheses only when used; containers N/A for v0.6 replay |
| Freshness / anti-rollback | Not claimed via stored freshness authority |

## What this workstream does *not* claim

- That PCS is free of residual TCB.
- That identical semantic member digests imply identical ZIP bytes (Task 12 shows the opposite for noncanonical regeneration).
- That assumption-only claim links are sufficient evidence (Task 14 flags them ambiguous).
