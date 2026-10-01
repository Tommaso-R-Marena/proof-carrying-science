# PCS v0.6/v2 full formalization report

Scope: the Lean refinement of the **current** PCS v0.6/v2 artifact format and
end-to-end verifier (`pcs/verifier_v06.py::verify_end_to_end_v06`,
`pcs/verifier_zip_v06.py`) into the existing v1 semantic theorem stack
(`PCS.Wire`, `PCS.WireCheck`, `PCS.DecisionExtraction`, `PCS.SerializedBridge`).

All v0.6 material lives in `formal/PCS/V2/` (30 files, about 6 500 lines). Nothing in
the v1 layer was re-proved or replaced. The v2 wire is mapped into it by `toV1`, and
`wireCheck_sound` and the `wire_*_sound` theorems are reused as they are.

Gate: `./scripts/verify_lean.sh`, which runs `lake build`, the placeholder audit and
the forbidden-declaration audit. **It passes.**

---

## A. Exactly proved

Every theorem below is proved in Lean with no `sorry`, no project axiom and no
`native_decide`. "Unconditional" means the statement has no hypothesis beyond
acceptance by the Lean checker. Oracles (`Oracles`) are *parameters*: such a theorem
holds for **every** choice of Unicode tables, Ed25519 primitive, capture function,
workflow checker and replay executor.

### A1. Canonical JSON / bytes (`Json`, `JsonRoundtrip`, `Canonical`, `Hex`, `Base64`)
| Theorem | Meaning |
|---|---|
| `Json.parse_ser`, `Json.parseVal_ser` | The canonical parser inverts the canonical serializer, so the parser accepts every canonical value. |
| `Json.ser_injective`, `Json.jcsBytes_injective` | Two different JSON values never have the same canonical text or the same UTF-8 bytes. |
| `Canonical.parseCanonicalBytes_sound` | Accepted bytes are exactly `jcsBytes v`. Object keys are strictly increasing in UTF-16 order, so there are no duplicates. Strings contain no noncharacters. Numbers are safe integers only. The size limit holds. |
| `Canonical.parseCanonicalBytes_unique` | The accepted value is the only value whose canonical bytes equal the input. The result does not depend on which parser is used. |
| `Canonical.parseCanonicalBytes_complete` | Every canonical value that is within the limits is accepted. |
| `Hex.hexDecode_hexEncode`, `Hex.hexEncode_of_hexDecode` | A 64-hex field denotes exactly one 32-byte value. Upper-case, truncated or padded spellings are not accepted. |
| `Base64.decodeCanonical_sound`, `Base64.decodeCanonical_unique` | Each signature has exactly one accepted base64 spelling. |

### A2. Domain separation and hash binding (`Domains`, `Binding`)
| Theorem | Meaning |
|---|---|
| `hashEnvelopeBytes_injective`, `hash_domain_separation` | The hashed bytes determine both the domain and the payload. Different domains never produce the same preimage. |
| `hash_sig_separation`, `Signature.signed_message_not_hash_preimage` | A hash preimage is never a signature message, and the reverse also holds. |
| `digest_binding`, `domainSha256_binding` | If two domain digests are equal, then the domains and payloads are equal, **or** an explicit SHA-256 collision exists (`Sha256Collision`). |
| `cross_domain_digest_collision` | A digest that matches across two different domains is itself a SHA-256 collision. |
| `wire_hash_binding`, `wire_hash_binds_bytes` | Two accepted wires with the same `wire_semantic_hash` are identical, or a collision exists. |
| `claim_/predicate_/evidence_/context_/decision_/source_substitution_needs_collision` | Changing any one of these parts of an accepted wire while keeping its hash requires a collision. |
| `predicate_commitment_binding`, `evidence_bound_to_claim_predicate`, `evidence_predicate_unique` | A predicate commitment fixes the committed predicate JSON (up to a collision). Every evidence item is bound to the same predicate. |
| `wire_digest_not_predicate_digest` | A decision-domain digest cannot also serve as a predicate commitment without a collision. |

### A3. Normalized decision wire `pcs-normalized-decision-v2` (`NormalizedWire*`, `Binding`)
| Theorem | Meaning |
|---|---|
| `verifyWireBytes_canonical`, `_nonmalleable`, `_parser_independent` | Accepted bytes are exactly `encodedBytes w`. One typed wire corresponds to one byte string. |
| `verifyWireBytes_schema`, `verifyWireBytes_wellFormed` | Acceptance implies the full JSON-Schema field constraints and the v1 `WellFormed` predicate. |
| `verifyWireBytes_hash` | The stored hash is the domain-separated SHA-256 of the exact projection. |
| `verifyWireBytes_scope`, `verifyWireBytes_evidence_commitments` | The claim, evidence and context scope are exact. Evidence IDs are unique. Each evidence item carries the claim's predicate commitment. The decision is the recomputed one. |
| `verifyWireBytes_assures` | An accepted decision level `L` gives the v1 kernel judgement `Assures Γ L C E`. |
| `verifyWireBytes_{computational,formal,empirical,mixed}_sound` | Soundness for each claim mode, by reusing `DecisionExtraction`/`SerializedBridge`. |

### A4. Normalized index and set (`Index`, `IndexProofs`)
`verifyNormalizedSet_sound` and `verifyNormalizedSet_assures` cover the following:
- The index binds to the certificate.
- Each index entry points to the wire stored at the path derived from its claim ID.
- That wire's bytes are accepted, and its decision matches the index decision.
- Missing, extra and duplicate members are rejected.
- Paths and claims cannot be confused with each other.

`lookup_unique` covers lookups in a name-unique map.

### A5. Signatures (`Signature`, `Ed25519`, `SHA512`)
These theorems give **(C): PCS's use of Ed25519**, proved unconditionally.
- `verifySigRecordBytes_sound`, `_signs_exact`, `_determined`: the bytes passed to the
  primitive are exactly `signaturePayloadBytes d p`, and the domain and payload are the
  expected ones. The fingerprint is the SHA-256 of the key.
- `verifySigRecordBytes_nonmalleable`: the record bytes are unique.
- `verifySigRecordBytes_domain_unique`, `certificate_package_messages_disjoint`:
  domains cannot be confused.

Two further theorems depend only on the named hypotheses (A) `Ed25519ImplCorrect` and
(B) `NoForgery`, which is stated for a single public key:
- `verifySigRecordBytes_authentic`: the key holder signed exactly these bytes.
- `verifySigRecordBytes_intended`: the same, plus `SignsOnlyEnvelopes`.

`Ed25519.ed25519ImplCorrect_self` discharges (A) when the checker runs with the Lean
RFC 8032 implementation. In that case only (B) remains.

### A6. Package (`Package`, `PackageProofs`)
- `namespace_no_traversal`, `namespace_no_alias`, `namespace_no_parent`: no `..`, no
  aliases after case folding or NFC normalization (for *any* folding tables), and no
  file that is also a parent directory.
- `verifyCertBytes_sound`: canonical certificate bytes, with the semantic and integrity
  hashes recomputed over the exact production projections.
- `cert_semantic_binding`, `cert_integrity_binding`, `cert_semantic_not_integrity`.
- `verifyManifestBytes_sound`, `verifyManifestBytes_nonmalleable`.
- `fileMapOK_sound`, `fileMap_exact_names`, `fileMap_member_digest`: the set of
  delivered members equals the set of signed members, with exact sizes and digests.
- `certificate_member_bound`, `member_bytes_binding`.
- `verifyPackage_sound`.
- `package_authentic`, `package_intended`: these require (A) and (B) only.

### A7. Archive layer (`Archive`, new in this pass)
| Theorem | Meaning |
|---|---|
| `fromArchiveEntries_sound` | The partition of decoded members is exact. Member names are unique. The four control records are the archive's members of those names. The signed file map is the archive minus the three self-referential control files. |
| `archive_no_duplicate_members` | An accepted archive never has two members with the same name, so a ZIP shadow entry cannot be ambiguous. |
| `archive_members_signed` | Every non-control archive member is signed by the manifest with its exact size and SHA-256. |
| `archive_manifest_members_present` | Every signed member is present in the archive. |
| `archive_certificate_member` | The verified certificate is the archive's `certificate.json`, which is itself a signed member. |
| `pcs_archive_scientific_assurance_exact` | All of the above together with `ScientificAssurance`. |
| `pcs_raw_archive_assurance` | The same, stated for the archive's *semantic* member list, under `ZipDecoderFaithful`. |
| `production_raw_archive_assurance` | The same for the production verifier, under `ProductionRefinesLean`. |

### A8. SHA-256 implementation structure (`SHA256`, `SHA256Padding`, new in this pass)
| Theorem | Meaning |
|---|---|
| `pad_length_mod`, `pad_prefix`, `pad_marker`, `pad_length_field`, `pad_suffix` | FIPS 180-4 §5.1.1 padding layout. |
| `be64_injective` | The 64-bit big-endian length field is injective below 2^64. |
| `pad_injective`, `chunks_pad_injective` | Padding and block parsing are injective for messages shorter than 2^61 bytes, so padding is unambiguous. |
| `chunks_join`, `pad_blocks_64` | Block parsing neither loses nor duplicates bytes, and every block is exactly 512 bits. |
| `words_length`, `schedule_size`, `pad_schedule_size` | Every block has exactly 64 message-schedule words, so the compression function never reads past the end of the schedule array. |
| `sha256_length` | Every digest is exactly 32 bytes. |
| `sha256_collision_is_block_collision` | A SHA-256 collision between two admissible messages is a collision of the iterated compression function on two *different* block sequences. |

### A10. Verified replay executor for `reaction_balance` (`Chemistry`, new in this pass)
`chemExecWith fb` is the Lean transcription of `_replay_one` for
`check_spec.type == "reaction_balance"`. It covers `pcs/checks/chemistry.py`: the
`([A-Z][a-z]?)([0-9]*)` tokenizer, positive integer coefficients (default 1), and the
per-element balance. Every other check type is delegated to `fb`.

| Theorem | Meaning |
|---|---|
| `tokenize_sound`, `tokenize_complete` | The executable tokenizer decides the declarative token grammar `Tokens`. |
| `tokens_functional` | A formula has at most one parse, so its chemical meaning is unambiguous. |
| `balancedB_iff` | The executable balance test decides `Balanced` (∀ element, equal totals on both sides). |
| `chemExecWith_faithful` | `ReplayFaithful fb H → ReplayFaithful (chemExecWith fb) (ChemHolds H)`. For chemistry items the replay assumption becomes a **theorem**. |
| `chemExec_faithful` | With the all-`UNVERIFIED` fallback, faithfulness holds with no hypothesis. |
| `pcs_reaction_evidence_balanced` | If the Lean checker runs this executor and accepts, every passing `reaction_balance` evidence item denotes an atom-balanced reaction. |

Executable checks in `ChemistryVectors` confirm that the golden package is accepted
when the Lean checker **replays its chemistry evidence itself**. The differential
driver `tools/LeanVerifyDir.lean` now uses this executor too.

### A9. End to end (`EndToEnd`, `Flagship`, `Reproducibility`, `TCB`)
| Theorem | Assumptions | Meaning |
|---|---|---|
| `acceptPCS_sound` | none | Acceptance gives `StructuralAssurance`: every stage succeeded, with its witnesses. |
| `pcs_claims_assured` | none | For each accepted claim, all of the following hold. The wire is delivered at its derived path, and its bytes are accepted. The claim, kind, predicate commitment, required evidence, assumptions and decision are the certificate's. The wire is bound to the certificate's semantic and integrity hashes. `Assures` holds. Evidence scope is exact. Each evidence outcome is the **fresh** executor observation on a request built from the verified certificate and the digest-checked artifact bytes. |
| `pcs_claim_scope`, `pcs_artifacts_bound` | none | There is exactly one decision per certificate claim. Replayed artifacts are the delivered, manifest-signed bytes. |
| `pcs_authentic`, `pcs_intended` | (A), (B), (+ discipline) | The key holder signed this manifest and this certificate payload. |
| `pcs_environment_bound` | none | Declared environment = `capture(inventory of the delivered, digest-checked sources)`, and the confirmation flags hold. |
| `pcs_environment_described` | `CaptureSound` | The declaration means what `Describes` says. |
| `pcs_evidence_holds` | `ReplayFaithful` | Every passing evidence item's scientific predicate `Holds` on the committed request. |
| `pcs_accept_implies_scientific_assurance` | `ExternalContracts` | **Flagship** (see B). |
| `pcs_archive_accept_implies_scientific_assurance` | `ExternalContracts` | The flagship stated from the raw archive bytes, with the ZIP decoder as an oracle. |
| `same_commitment_same_requests` | none | The same certificate semantic hash gives the same model, artifact bytes and replay requests, unless SHA-256 collides. |
| `acceptance_reproducible`, `same_commitments_same_observation` | `DeterministicModulo run Equiv` | If the runtime is deterministic modulo an explicit equivalence, the whole verdict is reproducible. |
| `byte_repro_implies_normalized`, `normalized_not_byte` | none | Byte reproducibility implies normalized reproducibility. A formal counterexample shows the converse fails. |
| `verdict_depends_only_on_observations` | none | Freshness: the verdict depends only on the executor's answers at verification time. |
| `requestFor_injective`, `wire_reuse_same_certificate` | none | Anti-substitution: a wire accepted in two packages forces equal certificate hashes. Requests are injective in (certificate, evidence, artifacts). |
| `production_accept_implies_scientific_assurance` | `ProductionRefinesLean` + contracts | The result transported to the Python verifier. |

---

## B. Flagship theorem (exact Lean statements)

```lean
theorem PCS.V2.Flagship.pcs_accept_implies_scientific_assurance {O : Oracles} {T : TrustAnchor}
    (K : ExternalContracts O T) {inp : PackageInput} {r : AcceptedResult}
    (h : acceptPCS O T inp = some r) : ScientificAssurance O T K inp r

theorem PCS.V2.Archive.pcs_raw_archive_assurance {O : Oracles} {zip : ZipDecoder} {T : TrustAnchor}
    {ZipSemantics : ByteArray → List (String × ByteArray) → Prop}
    (hZ : ZipDecoderFaithful zip ZipSemantics) (K : ExternalContracts O T) {raw : ByteArray}
    {inp : PackageInput} {r : AcceptedResult} (h : acceptArchive O zip T raw = some (inp, r)) :
    ∃ entries, ZipSemantics raw entries ∧ ArchivePartition entries inp ∧
      (∀ n b, (n, b) ∈ entries → n ∉ controlNames →
        ∃ fm, (n, fm) ∈ r.pkg.manifest.files ∧ b.size = fm.size ∧
          sha256 b.data.toList = fm.sha256) ∧
      (∀ n ∈ manifestNames r.pkg.manifest, ∃ b, (n, b) ∈ entries ∧ n ∉ controlNames) ∧
      ScientificAssurance O T K inp r
```

`ScientificAssurance` (in `PCS/V2/Flagship.lean`) is not a wrapper around acceptance.
Its fields are:
- `structural`: all stage witnesses.
- `certificateCanonical`: the certificate bytes are canonical, `inp.certificateBytes = jcsBytes (.obj r.pkg.cert.members)`.
- `manifestCanonical`: the manifest bytes are canonical in the same sense.
- `memberSetExact`: the delivered member set equals the signed member set.
- `memberDigests`: exact size and SHA-256 for every member.
- `manifestBindsCertificate`: the manifest carries the certificate's semantic and integrity hashes.
- `claimScope`: one decision per certificate claim, in order.
- `claims`: a `ClaimAssurance` for every accepted claim (see `pcs_claims_assured`), including the kernel `Assures` judgement.
- `authentic`: the key holder signed the manifest envelope and the certificate envelope.
- `environment`: declared environment = capture of the delivered sources, and `describes` holds for it.
- `evidenceHolds`: the scientific predicate `holds` on the exact committed request of every passing evidence item.

`ExternalContracts O T` bundles exactly these four items, and nothing else:
- `Ed25519ImplCorrect`;
- `NoForgery` for the trust-anchor key;
- `CaptureSound`;
- `ReplayFaithful`.

`TCB.contractsWithLeanEd25519` removes `Ed25519ImplCorrect` when the Lean
Ed25519 implementation is used.

---

## C. Proof chain

```
raw archive bytes
  ↓ ZIP decoder (oracle `ZipDecoder`)                        CONDITIONAL (ZipDecoderFaithful)
decoded members
  ↓ fromArchiveEntries                                       PROVED (fromArchiveEntries_sound, archive_*)
control records + signed file map
  ↓ parseCanonicalBytes (strict canonical JSON)              PROVED (parse_ser, *_sound/_unique/_complete)
canonical JSON values
  ↓ typed decoders (cert / manifest / sig record / index / wire)  PROVED (*_sound, schema, hex/base64 uniqueness)
typed v2 objects
  ↓ verifyPackage / normalizedOK / verifyNormalizedSet       PROVED (verifyPackage_sound, verifyNormalizedSet_sound)
structural verification
  ↓ claim/predicate/evidence binding                         PROVED (Binding.*, pcs_claims_assured)
  ↓ hash binding vs. malicious collisions                    PROVED up to explicit `Sha256Collision` witness
integrity (Lean SHA-256 recomputed)                          PROVED (wiring); SHA-256 = FIPS spec: KAT-validated only
  ↓ authenticity                                             CONDITIONAL (Ed25519ImplCorrect [dischargeable], NoForgery)
environment declared = captured                              PROVED (pcs_environment_bound)
environment meaning                                          CONDITIONAL (CaptureSound)
replay: fresh observation on digest-bound request            PROVED (pcs_claims_assured.evidenceReplayed)
replay: observation means predicate holds                    PROVED for reaction_balance (chemExecWith_faithful);
                                                             CONDITIONAL (ReplayFaithful) for other check types
  ↓ v1 kernel
semantic assurance `Assures`                                 PROVED (verifyWireBytes_assures via wireCheck_sound)
Python verifier = Lean checker                               CONDITIONAL (ProductionRefinesLean; differentially tested)
```

---

## D. Axiom audit

Running `lake env lean PCS/V2/Audit.lean` prints the axioms for 65 v0.6 theorems.
Every one of them uses only a subset of `{propext, Classical.choice, Quot.sound}`. The
results are as follows (abbreviated: `[pcq]` = `[propext, Classical.choice, Quot.sound]`,
`[pq]` = `[propext, Quot.sound]`, `[p]` = `[propext]`).

- `[pcq]`:
  - JSON: `Json.parse_ser`, `Json.jcsBytes_injective`.
  - Canonical gate: `Canonical.parseCanonicalBytes_sound`, `_unique`, `_complete`.
  - Domains: `Domains.hash_domain_separation`, `hash_sig_separation`, `digest_binding`, `cross_domain_digest_collision`.
  - Wire: `NormalizedWire.verifyWireBytes_accepted`, `_assures`, `_computational_sound`, `_formal_sound`, `_empirical_sound`, `_mixed_sound`.
  - Binding: `Binding.wire_hash_binding`, `predicate_commitment_binding`, `evidence_bound_to_claim_predicate`.
  - Index: `Index.verifyNormalizedSet_sound`, `_assures`.
  - Signatures: `Base64.decodeCanonical_unique`, `Signature.verifySigRecordBytes_sound`, `_nonmalleable`, `_domain_unique`, `_authentic`, `_intended`.
  - Package: `Package.namespace_no_traversal`, `namespace_no_alias`, `namespace_no_parent`, `verifyPackage_sound`, `fileMap_exact_names`, `member_bytes_binding`, `package_authentic`.
  - End to end: `EndToEnd.acceptPCS_sound`.
  - Flagship: `Flagship.pcs_claims_assured`, `pcs_authentic`, `pcs_environment_bound`, `pcs_evidence_holds`, `pcs_accept_implies_scientific_assurance`, `pcs_archive_accept_implies_scientific_assurance`.
  - Reproducibility: `Reproducibility.same_commitment_same_requests`, `acceptance_reproducible`, `wire_reuse_same_certificate`.
  - Correspondence: `TCB.production_accept_implies_scientific_assurance`.
  - SHA-256 schedule: `SHA256.schedule_size`, `pad_schedule_size`.
  - Archive: `Archive.archive_no_duplicate_members`, `archive_members_signed`, `archive_manifest_members_present`, `archive_certificate_member`, `pcs_archive_scientific_assurance_exact`, `pcs_raw_archive_assurance`, `production_raw_archive_assurance`.
  - Chemistry: `Chemistry.tokenize_complete`, `tokens_functional`, `chemExecWith_faithful`, `chemExec_faithful`, `pcs_reaction_evidence_balanced`.
- `[pq]`: `Ed25519.ed25519ImplCorrect_self`, `SHA256.be64_injective`, `pad_injective`, `chunks_pad_injective`, `Chemistry.tokenize_sound`, `Chemistry.balancedB_iff`.
- `[p]`: `Archive.fromArchiveEntries_sound`.

No theorem depends on `sorryAx`, `Lean.ofReduceBool`, `Lean.trustCompiler` or any
project axiom. The v1 audit (`PCS/Audit.lean`) is unchanged and also uses only the
standard axioms.

Source scan of `formal/PCS.lean` and `formal/PCS/**`:
- **0** `sorry` / `admit`.
- **0** `axiom`, `unsafe`, `implemented_by`, `extern`, `native_decide`.

The only `sorry`s in the whole `formal/` tree are in `formal/ProofTasks/CheckedRawWire.lean`
(7 occurrences). That file is a pre-existing task-statement file. It is not part of the
`PCS` library and no PCS theorem imports it.

The `#guard` checks in `PCS/V2/Vectors.lean` are executable tests. They are not proofs,
and no theorem depends on them.

---

## E. Trusted computing base

This table restates `PCS.V2.TCB.tcbStatus`.

| # | Item | Status |
|---|---|---|
| 1 | Lean kernel / logic | foundation (`propext`, `Classical.choice`, `Quot.sound`) |
| 2 | Parser / codec | **proved**. Acceptance re-checks `jcsBytes v = raw` byte for byte, so it does not depend on any UTF-8 decoder or JSON parser. |
| 3 | Canonicalizer | **proved** (`parse_ser`, `jcsBytes_injective`) |
| 4 | SHA-256 implementation | The Lean checker *uses* the Lean FIPS 180-4 transcription. Wiring is proved. Spec-faithfulness is checked by KATs only. Python `hashlib` agreement is `Sha256ProductionAgrees` (completeness only). |
| 5 | Collision / second preimage | Explicit `Sha256Collision` disjunct only. It is never assumed. |
| 6 | Ed25519 implementation | Lean RFC 8032 transcription. (A) is discharged by `rfl` for it. Faithfulness is checked by KATs and golden signatures. |
| 7 | Ed25519 unforgeability | `NoForgery Spec pk Signed`, for one key. |
| 8 | Archive extractor | `ZipDecoder` + `ZipDecoderFaithful`. The partition logic is proved. |
| 9 | Filesystem / OS | Not used by the Lean checker, which reads no filesystem state. Delivery of the bytes is the input. |
| 10 | Python runtime | Only inside `ReplayFaithful` / `CaptureSound` (executors), and inside `ProductionRefinesLean`. |
| 11 | R runtime | Only inside `ReplayFaithful`. |
| 12 | Container runtime | Not applicable. v0.6 replay builds and runs no containers. |
| 13 | Capture fidelity | `CaptureSound capture Describes` |
| 14 | Reconstruction fidelity | Not applicable. v0.6 never reconstructs an environment, so the theorems claim only *declared = captured*. |
| 15 | Replay executor fidelity | **Proved** for `reaction_balance` (`chemExecWith_faithful`). `ReplayFaithful fb Holds` for the other check types. |
| 16 | Scientific predicate | The user-supplied `Holds` / `Describes` relations |
| 17 | Freshness authority | Not applicable. Freshness comes from re-execution during verification, and no stored state is consulted. Rollback resistance is **not** claimed. |
| 18 | Unicode tables (NFC/casefold) | `UnicodeOps` parameter. Namespace theorems hold for *any* tables. |
| 19 | Production ↔ Lean correspondence | `ProductionRefinesLean`. Differentially tested (`tests/test_formal_v2_differential.py`, 18 package variants + 1 wrong-key case). |

---

## F. Counterexamples found (all preserved as regression tests)

1. **Integers parsed as binary64 floats.**
   - Production `parse_jcs_json` used `parse_int=float`. The golden certificate's
     `"coefficient": 2` became `2.0`, the type-strict chemistry check rejected it, and
     the end-to-end verifier **rejected its own golden package** at replay.
   - Minimal witness: `parse_jcs_json('{"a":2}') == {"a": 2.0}`.
   - Repair: `_parse_int_jcs` in `pcs/canonical_json.py` parses integers with
     |n| ≤ 2^53 as Python `int`. Canonical bytes and all hashes are unchanged, and larger
     integers keep their binary64 meaning.
   - Lean side: the verified fragment admits only safe integers.
   - Tests: `test_safe_integers_parse_as_int_and_keep_canonical_bytes`,
     `test_unsafe_integer_keeps_binary64_interpretation_and_noncanonical_spelling_fails`,
     `test_golden_certificate_integers_reach_replay_as_integers`,
     `test_golden_package_is_accepted_end_to_end`.
2. **Malleable base64 signature spelling.**
   - `base64.b64decode(..., validate=True)` ignores the unused low bits of the last
     symbol. A 64-byte signature therefore has 16 spellings (`…AQ==` vs `…AR==`). Each
     gives a different, still canonical-JCS signature-record byte string that verified,
     which breaks "one accepted byte representation per signed object".
   - Repair: `decode_canonical_signature_b64` in `pcs/signing_v06.py` (also used by
     `receipt_signature_v06.py`) requires `b64encode(b64decode(s)) == s`.
   - Lean side: `Base64.decodeCanonical_unique` and `verifySigRecordBytes_nonmalleable`.
   - Tests: `test_noncanonical_base64_signature_is_rejected_by_decoder`,
     `test_malleated_{certificate,package}_signature_record_is_rejected`, plus the
     differential case `noncanonical_base64_signature`.

3. **Unicode decimal digits in molecular formulas (found in this pass).**
   - `_TOKEN = ([A-Z][a-z]?)(\d*)` matches every Unicode decimal digit, and `int()`
     converts them. Python therefore read `"H\u0662"` (U+0662 ARABIC-INDIC DIGIT TWO) as
     H₂, while every ASCII-based reading, including the Lean executor, rejects it.
   - Minimal witness: `reaction_balanced([{"formula":"H\u0662","coefficient":2},
     {"formula":"O2","coefficient":1}], [{"formula":"H2O","coefficient":2}])` returned
     PASS.
   - The witness is not blocked earlier: the golden certificate with that formula
     passes `validate_v06_certificate_shape`. The meaning of a signed scientific
     predicate therefore depended on Python's Unicode tables, so it was not
     language-neutral.
   - Repair: `pcs/checks/chemistry.py` now uses `[0-9]*`.
   - Lean side: `isDig` is ASCII, and `tokens_functional` gives a unique meaning.
   - Tests: `test_unicode_digit_formula_is_rejected_by_parser`,
     `test_unicode_digit_formula_is_schema_valid_but_fails_replay`, and the
     `ChemistryVectors` `#guard` on `"H\u0662"`.
4. **Boolean coefficients (found in this pass).**
   - `isinstance(True, int)` is true in Python, so `"coefficient": true` meant 1 to
     `reaction_balanced`.
   - In v0.6 the certificate JSON-Schema (`"type": "integer"`) already rejects it before
     replay. However, `reaction_balanced` is also used by the legacy `pcs/kernel.py`
     path.
   - Repair: booleans are rejected explicitly.
   - Lean side: only `JVal.num n` with `n > 0` is a coefficient.
   - Tests: `test_boolean_coefficient_is_not_one` and a `ChemistryVectors` `#guard`.

Some invariants were attacked in this pass and **held**. In each case both the Lean
checker and production reject the attack:
- duplicate JSON keys in the certificate;
- a non-canonical integer spelling (`2.0`);
- upper-case hex digests in the manifest and in the index;
- whitespace in the normalized wire;
- a truncated artifact;
- a case-alias member;
- extra and missing members;
- a substituted artifact;
- a package signature that is really the certificate signature (domain confusion);
- a wrong trust anchor.

Formal negative result: `normalized_not_byte` shows that normalized reproducibility
does not imply byte reproducibility, so PCS must never conflate the two.

---

## G. Open gaps (exact statements still needed)

1. **Production ↔ Lean is now architecturally narrowed.** The high-assurance
   production path no longer promotes Python-only acceptance. Python performs its
   fail-closed archive/precheck and external replay/capture/workflow stages, writes a
   canonical observation transcript bound to the certificate semantic hash and
   checker version, and authoritative `valid: true` requires the compiled Lean
   authority to accept the exact decoded package-member bytes plus that transcript.
   `PCS.V2.Authority.gatedProduction_refinesLean` proves the abstract
   `precheck ∧ LeanAccept` construction satisfies `ProductionRefinesLean`; and
   `acceptPCSWithTranscript_implies_acceptPCS` proves transcript-gated acceptance is
   genuine `acceptPCS` acceptance for the selected oracles. This deliberately avoids
   a whole-Python-semantics refinement proof. It does **not** prove the operational
   Python ZIP decoder/materializer/process invocation correct: raw ZIP →
   decoded-member fidelity remains the `ZipDecoderFaithful` boundary, and the
   transcript's scientific meaning remains governed by `CaptureSound`,
   `ReplayFaithful`, and the workflow-oracle boundary.
2. **SHA-256 spec faithfulness.** `∀ m, PCS.V2.SHA256.sha256 m = FIPS180_4.SHA256 m`
   against an independent, mathematically stated FIPS 180-4 specification (for
   example one stated over bit-vectors or `ZMod (2^32)`). What is proved so far is
   structural: padding, blocks, schedule size and digest length.
3. **Python hashlib.** `Sha256ProductionAgrees hashlib`. This is needed only for
   completeness on honest inputs.
4. **Ed25519 spec faithfulness.** `Ed25519.verify = RFC8032.verify` against a group-law
   specification. That requires curve-arithmetic correctness (field inverse, point
   addition formulas, point decoding).
5. **Ed25519 unforgeability.** `NoForgery Ed25519.verify pk Signed` is a cryptographic
   assumption, for example EUF-CMA. It cannot be proved inside Lean.
6. **ZIP.** `ZipDecoderFaithful zip ZipSemantics`. Discharging it needs a Lean ZIP
   decoder (local headers, central directory, DEFLATE) proved against a format
   semantics, or production use of such a decoder.
7. **Capture.** `CaptureSound O.capture Describes`. This needs a Lean model of each
   capture rule (lockfile and pin extraction) and a proof against `Describes`.
8. **Replay.** `ReplayFaithful fb Holds` for the check types other than
   `reaction_balance`: `unit_compatible`, `csv_disjoint`, `pkpd_contract`,
   `pkpd_reference_match`, and the external validators. `reaction_balance` is
   discharged by `chemExecWith_faithful`. `unit_compatible` and `csv_disjoint` are
   deterministic and could be transcribed the same way. The PK/PD checks involve
   floating point and need a floating-point semantics. Production also has to *run*
   the Lean executor (or be proved equal to it) for this to cover production
   replays. The differential driver already runs it.
9. **Workflow oracle.** `O.workflow` (static workflow-dependency replay) is a Boolean
   oracle. Its acceptance is recorded in `StructuralAssurance.workflow`, but no
   semantic meaning is attached to it yet.
10. **Unicode tables.** These affect only portability (alias rejection), never
    soundness of the other theorems.

---

## H. Metrics

| Metric | Value |
|---|---|
| v0.6 Lean files (`formal/PCS/V2/`) | 31, including the production authority bridge `Authority.lean` |
| v0.6 Lean declarations (top-level `theorem/def/structure/…`) | 710 |
| v0.6 theorems | 281 source declarations after adding the two authority-bridge theorems; hosted compilation remains the acceptance criterion |
| authority integration files | `V2/Authority.lean`, `PCSAuthority.lean`, `pcs/lean_authority_v06.py`, verifier/CLI propagation, standalone embedding, authority tests, and hosted packaging gates |
| `sorry`/`admit` in the PCS library | 0 |
| project-specific axioms | 0 |
| Lean executable vectors (`#guard`) | 39 in total. `Vectors`: 27 (SHA-256/SHA-512/Ed25519 known-answer and negative vectors, canonical base64, golden-package acceptance, and 17 adversarial package rejections). `ChemistryVectors`: 12 (tokenizer, executor, and golden acceptance with the chemistry replayed in Lean). |
| differential production-vs-Lean cases | 19 (golden + 17 mutations + wrong key), all passing. 6 mutations were added in this pass. |
| formal-regression tests | 10, all passing (3 added in this pass) |
| full Python suite | **PASS** in the hosted `formal-v06-integration` CircleCI gate after integration repair. |
| formerly failing regression group | 99 / 99 passing locally across `test_package_v06`, `test_signing_v06`, `test_kernel`, `test_discover_v06`, `test_environment_v06`, and `test_workflow_discovery_v06`. |

Lean-authoritative production note: source-level metrics above are updated by this
authority branch; the final evidence line should be read together with the hosted
Lean/full-Python/standalone gates for the branch or merge commit.

Post-integration repair of the 13 pre-existing failures preserved production safety
behavior rather than weakening it:
- **Error-message expectations (3).** Tests now accept the current JSON-Schema-first
  rejection path; invalid inputs are still rejected.
- **Example/fixture layout (2).** Kernel tests were made self-contained rather than
  depending on a mutable example-folder layout.
- **Overwrite-guard cases (7).** Tests that intentionally replace a confirmed manifest
  now pass `overwrite=True`; the production refusal-by-default guard remains intact.
- **Workflow-selection threshold (1).** The static-workflow test now explicitly uses
  the documented `minimum_workflow_confidence=0.90` threshold. Production inference
  behavior was not loosened.

The exact integrated branch then passed `./scripts/verify_lean.sh`, the full Python
suite, and all 19 Python↔Lean differential cases in CircleCI before merge. The merge
commit `91b35d4d81a6e77ea8d20b221b555aafe5988e32` subsequently passed the normal
mainline formal, product-hardening, and restoration/ABI gates.
