# PCS Semantic Intelligence v3 — integration guide for the production PCS core

This package is the standalone `formal/` Lake package `PCS` (Lean `leanprover/lean4:v4.28.0`,
no Mathlib).  The production repository (Python `proof_translation_v06.py`, Claim IR, Proof
Obligation Graph, `pcs-proof-proposals-v1`, CLI, CI) is **not** present here.  Everything below
that touches those components is an *instruction*, not something that was executed in this
package.

## 1. Files to bring over

| Path | Kind | Notes |
|---|---|---|
| `PCS/V2/ReceiptAuthorityV3.lean` | Lean (proved) | stateful receipt phase, `AuthorityV3`, `LedgerV3`, statements, `receiptPhase_ok_iff` |
| `PCS/V2/TranslationV3.lean` | Lean (proved) | `decideV3`, `stepV3`, `CertifiedV3`, refinement + replay theorems |
| `PCS/V2/ReceiptThreatModelV3.lean` | Lean (proved) | adversarial rejection theorems, honest-key / quorum threat model |
| `PCS/V2/TranslationV3Json.lean` | Lean (proved) | canonical wire codecs, `semanticCheckV3`, wire soundness |
| `PCS/V2/LeanSyntaxV3.lean` | Lean (proved) | Lean syntax model, name resolution, `lean_reading_correspondence` |
| `PCS/V2/AssuranceV3.lean` | Lean (proved) | **`pcs_v3_certified_wire_assurance`** (centerpiece) |
| `PCS/V2/EntailmentV3.lean` | Lean (proved) | `↔` sugar, entailment checker, separate strengthening mode |
| `PCS/V2/CertiForgeAdapterV1.lean` | Lean (proved) | CertiForge equivalence-certificate adapter contract |
| `PCS/V2/SemanticV3Audit.lean` | Lean | `#print axioms` for all v3 theorems |
| `PCS.lean` | Lean | new `import` lines appended (nothing removed) |
| `PCSSemanticCheck.lean` | Lean exe | new modes `--v3`, `--v3-strengthen`; v1/v2 modes kept, documented NON-PRODUCTION |
| `tools/CheckElaborationV3.lean` | meta tool | env fingerprint; real-Lean elaboration check; kernel-replay proof check |
| `tools/gen_semantic_v3_fixtures.py`, `tools/run_semantic_v3_fixture_tests.sh` | fixtures | 37 signed v3 fixtures |
| `tools/gen_semantic_v3_audit.py`, `tools/check_semantic_v3_audit.sh` | audit | mechanical axiom audit |
| `fixtures/semantic_authority_v3/` | data | authority configs, requests, ledger states, `expected.json`, `env_fingerprint.txt` |
| `python/pcs_semantic/receipts_v3.py` | Python | statements, envelopes, test keys, independent oracle |
| `python/pcs_semantic/receipt_store.py` | Python | SQLite persistent store (atomic check-and-consume), CLI |
| `python/pcs_semantic/issuer_v3.py` | Python | reference elaboration / kernel-check issuers |
| `python/tests/test_semantic_authority_v3.py`, `test_elaboration_v3.py`, `test_issuer_v3.py`, `test_strengthening_v3.py`, `test_schema_v3.py` | tests | |
| `schemas/semantic_authority_v3.schema.json` | schema | interface documentation (the Lean decoders are authoritative) |
| `docs/PCS_CERTIFORGE_ADAPTER_V1.md` | spec | adapter contract for the CertiForge integration |

`lakefile.toml` is **unchanged** (the `pcs-semantic-check` executable already existed; it now
also imports `PCS.V2.EntailmentV3`).  No new dependency, no Mathlib.

## 2. The production acceptance path (replaces stateless receipts)

```
proposal (model, untrusted) ──► Claim IR / interpretation candidates
        │
        ▼
human / authorized process selects interpretation ──► CONFIRMATION receipt (Ed25519, role confirmation,
        │                                              statement = exact interpretation + context,
        │                                              context = scope, env fingerprint, toolchain, registry)
        ▼
candidate formalization (model or deterministic, untrusted)
        │
        ├─► elaboration issuer: tools/CheckElaborationV3.lean check  ──► ELABORATION receipt
        ├─► proof issuer:       tools/CheckElaborationV3.lean prove  ──► PROOF receipt (kernel-check record)
        ▼
ReceiptStore.certify(authority_bytes, request_v3_bytes)      # BEGIN IMMEDIATE … COMMIT
        └─ runs pcs-semantic-check --v3 authority request snapshot
           certified only if outcome == CERTIFIED_TRANSLATION and the nonces were consumed atomically
```

**Do not** use `pcs-semantic-check --v3` alone as the authority: without the store, replay
protection holds only relative to the snapshot passed in.  A certified result must be released
only after the store's `COMMIT`.

### Mapping from existing objects

* **Claim IR → `SemanticClaim`**: the v1 mapping (`PCS_SEMANTIC_TRANSLATION_V1_REPORT.md`) is
  unchanged.  Biconditionals may be written in the proposer layer and desugared with
  `Formula.iff` (`(φ → ψ) ∧ (ψ → φ)`; meaning proved by `Formula.iff_denote`) before encoding.
* **`pcs-proof-proposals-v1`**: keep the existing schema; add an optional, versioned object
  `"semantic_translation_v3": <request-v3>` (schema `pcs-semantic-translation-v3`).  A proposal
  carrying only v1/v2 stateless receipt fields must be classified **non-production**; the v3
  decision rejects non-null legacy receipt fields (`legacy_receipt_rejected`).
* **`proof_translation_v06.py`**: after it produces the candidate, build the v3 request (the
  candidate's `lean_source` must equal the decision's `expected_lean_source`, i.e.
  `renderClaimLean registry claim`), obtain the three receipts from the *separately deployed*
  issuers, then call the store:

```python
from pcs_semantic.receipt_store import ReceiptStore
from pcs_semantic.semantic_translation_v1 import canonical_json

store = ReceiptStore.open(DB_PATH, AUTHORITY["context"]["scope"])   # fails closed if missing
res = store.certify(canonical_json(AUTHORITY), canonical_json(request_v3), now=trusted_clock())
if res.certified:                     # only after COMMIT
    emit_certified_translation(res.decision)
else:
    emit_feedback(res.outcome, res.decision)   # diagnostics, countermodel, receipt failure
```

* **Strengthening** (deliberately stronger formalization):
  `store.certify(..., mode="strengthening")` runs `--v3-strengthen`; the confirmation-role receipt
  must attest `receipts_v3.strengthening_statement(...)` (purpose `strengthening-authorization`,
  binding the exact candidate).  The outcome `CERTIFIED_STRENGTHENING` (exit 4) must be surfaced as
  a **different** result class from a translation.

## 3. Exact changes needed in the main PCS authority and CLI

1. Route semantic-translation authority decisions through `ReceiptStore.certify` (or a port, §5)
   and the `--v3` binary; treat outcome `CERTIFIED_TRANSLATION` + exit 0 + successful commit as
   the *only* translation acceptance.
2. Label v1 (`pcs-semantic-check <a> <r>`) and v2 (`--v2`) decisions **non-production** in CLI
   output and in any persisted record (they verify stateless receipts only).
3. Add a distinct result class for `CERTIFIED_STRENGTHENING` (exit 4); never map it to a
   translation acceptance.
4. Authority configs `pcs-semantic-authority-v3`: per-role keys with validity windows, quorums,
   `allowed_axioms`, scope, and the `env_fingerprint` printed by
   `lake env lean --run tools/CheckElaborationV3.lean fingerprint <authority.json>` in the
   production Lean environment.  Re-pin after any change to imports, toolchain or registered
   definitions; receipts bound to the old fingerprint then stop verifying (intended).
5. Deploy the elaboration and proof issuers as **separate services with their own keys**, running
   `tools/CheckElaborationV3.lean check|prove` in the pinned environment
   (`python/pcs_semantic/issuer_v3.py` is the reference).  The authority never trusts an issuer
   beyond the stated threat model (fewer than quorum dishonest keys).
6. CI: `lake build`, `bash tools/check_semantic_v3_audit.sh`,
   `bash tools/run_semantic_v3_fixture_tests.sh`, `python3 -m unittest discover -s python/tests`.

## 4. Compatibility plan for PCS PR #78 / the consolidated core

* All v3 Lean modules are new files.  The only edits to existing files are appended imports in
  `PCS.lean` and new match arms + documentation in `PCSSemanticCheck.lean`; re-apply those by hand
  if the branch moved.  No existing theorem statement, module name or import was changed or
  removed.
* v1/v2 wire formats, fixtures and binaries are unchanged; their suites pass on this revision.
* If `PCS.V2.ReceiptLedger` or the v2 request types changed on the target branch, the v3 modules
  are the only dependants; rebuild and repair there.
* Apply on a new branch with `git am` on the patch series (or unpack the source archive), then run
  the CI list in §3.6.

## 5. Porting the persistent store

The SQLite store is a *reference* (tested, not verified).  A port must keep:

* a uniqueness constraint on `(scope, nonce)`;
* check-and-consume in **one** serializable transaction (SQLite `BEGIN IMMEDIATE`; Postgres
  `SERIALIZABLE`, or `SELECT … FOR UPDATE` plus the unique index);
* passing the authority only the consumed nonces **restricted to the request's nonces**
  (`decideV3_restrict` proves the decision is unchanged);
* release of a certified result only after commit; rollback on every non-certified outcome,
  error or exception;
* fail-closed open (missing database / wrong scope), explicit re-initialization with a new
  `genesis`, monotone trusted clock (`CLOCK_REGRESSION` otherwise), run-time key revocation.

## 6. What this package does not supply

Real signing keys and their custody (HSM/KMS), the human confirmation UI and its
authentication, deployed issuer services, a trusted time source, the production database, and the
Python integration inside `proof_translation_v06.py`.  None of these was invented here.
