# Aristotle maximal task — push PCS toward end-to-end proof-carrying verification

This is intentionally an **extremely ambitious** pass.

Do not stop after solving the first staged theorem. Continue down the trust boundary
as far as Lean 4.28.0 and the repository permit. The goal is to discover how much
of the remaining serialized/executable PCS chain can be made machine-checked in a
single coordinated push.

Do **not** weaken theorem statements, silently change semantics, introduce global
axioms, or hide external trust behind a renamed predicate. If a target is false,
produce the counterexample. If a component is too large to verify in this pass,
reduce it to the smallest explicit parameterized interface and state exactly what
remains trusted.

## Already established — do not re-prove by weakening

The following foundation has already been independently compiled and audited:

```text
DecisionWire
  + PCS.WireCheck.wireCheck w = true
  -> PCS.Wire.WellFormed w
  -> PCS.Normalized.DecisionInput
  -> PCS.Assures Γ L C E
```

In particular:

```lean
PCS.WireCheck.wireCheck_sound :
  wireCheck w = true -> WellFormed w
```

is production code and machine-checked under Lean 4.28.0.

The production formal root is placeholder-free and has no PCS-specific axioms.
Preserve that invariant.

The current checked frozen PK/PD normalized-wire values are:

```text
certificate_semantic_hash =
0fc13509d27c7b31e45ed9a841bfacddc9ca8a1a6c7e3a2af66e0b434cb36a8a

wire_semantic_hash =
c5d3da1f6296a62e3affe9f7d43c3c8d50f51b0b99f75da459ca613d0e5580a7

predicate commitment =
pcs-predicate-sha256:8cc9e0b74e7361040ed704b89f6753399f9c07573fe51198f0f093c6017f2c4c
```

The previously verified executable gate was 113/113 full Python tests and 35/35
targeted normalized-wire/trust/attestation tests.

---

# Ultimate objective

Push toward a theorem whose useful shape is as close as possible to:

```text
delivered normalized-wire bytes
  -> strict parser
  -> schema/version/enum validation
  -> RawDecisionWire
  -> checked decoder
  -> DecisionWire
  -> wireCheck = true
  -> WellFormed
  -> Assures Γ L C E
```

and, if feasible, continue farther outward toward package/certificate/hash/signature
binding.

The strongest desirable theorem is an executable checked function from actual
serialized bytes to an accepted assurance result, with a proof that every successful
return corresponds to the existing `Assures` semantics.

Do not claim scientific/model adequacy. Domain scientific replay soundness remains a
separate obligation unless you actually verify a specific domain checker.

---

# Phase 0 — independently reproduce the inherited baseline

Before changing anything:

```text
cd formal
lake env lean ProofTasks/WireCheck.lean
lake env lean ProofTasks/WireRefinementChecks.lean
lake build
bash scripts/verify_lean.sh
cd ..
python -m pytest -q
python -m pytest -q \
  tests/test_normalized_wire.py \
  tests/test_v05_trust.py \
  tests/test_attestation_finalization.py
```

Record exact versions and exit codes.

If the inherited branch does not reproduce, stop only long enough to isolate the
minimal cause, fix it without semantic weakening, then continue.

---

# Phase 1 — close and promote CheckedRawWire completely

Start with:

```text
formal/ProofTasks/CheckedRawWire.lean
```

Prove every staged theorem and promote a clean production module
`PCS/CheckedRawWire.lean`.

Required chain:

```lean
checkedDecodeRawWire raw = some w
  -> decodeRawWire raw = some w

checkedDecodeRawWire raw = some w
  -> wireCheck w = true

checkedDecodeRawWire raw = some w
  -> WellFormed w
```

Then prove computational/formal/empirical/mixed `Assures` corollaries.

Add adversarial closed examples for:
- bad wire format;
- bad spec version;
- bad checker version;
- unknown claim/evidence/outcome/decision tokens;
- forged decision;
- wrong evidence scope;
- duplicate evidence IDs;
- wrong context scope;
- mismatched predicate commitment;
- frozen valid PK/PD vector.

Promote only after a clean build and axiom audit.

Then **continue automatically to Phase 2**.

---

# Phase 2 — parse the actual normalized-wire serialization

The current normalized decision schema is unusually favorable: it contains only
objects, arrays, strings, booleans, and null. It does **not** require arbitrary JSON
number semantics.

Exploit that.

Attempt to define a small, strict parser for the actual normalized-wire serialized
representation rather than introducing a huge general-purpose JSON library.

Preferred target:

```lean
parseNormalizedDecisionWire : ByteArray -> Option RawDecisionWire
```

If a direct `ByteArray` parser is genuinely impractical in core Lean, first close a
`String -> Option RawDecisionWire` parser and then isolate UTF-8 decoding as a
separate explicit boundary. But try bytes first.

Required parser properties:
- reject duplicate object keys;
- reject unknown keys where the JSON schema uses `additionalProperties: false`;
- reject missing required keys;
- reject trailing garbage;
- reject malformed strings/escapes;
- reject unknown wire/spec/checker versions through the existing decoder path;
- reject unknown enum tokens;
- preserve array ordering exactly;
- preserve all string values exactly;
- do not trust the recorded invariant booleans;
- do not trust the recorded wire hash;
- reject structurally ambiguous input.

Support JSON whitespace as required by the emitted/accepted format. Handle JSON
string escapes correctly. If full Unicode escape handling is too large, either prove
the supported subset exactly and modify the executable exporter to emit that subset,
or clearly isolate the missing Unicode decoder boundary. Do not silently accept a
partial parser as "JSON".

Desirable theorem:

```lean
parseNormalizedDecisionWire bs = some raw
  -> RawWireSchemaValid raw
```

where `RawWireSchemaValid` captures the exact representable schema constraints not
already enforced by `decodeRawWire`.

Then compose:

```lean
checkedDecodeWireBytes bs = some w
  -> WellFormed w
```

and the four assurance corollaries.

If this phase succeeds, promote it and **continue to Phase 3**.

---

# Phase 3 — prove canonical serialization / parser round-trip

Define a canonical serializer for the normalized wire.

Because the wire schema uses fixed ASCII object keys and contains no JSON numbers,
this should be substantially easier than general RFC 8785.

Target functions may look like:

```lean
encodeRawDecisionWireCanonical : RawDecisionWire -> ByteArray
parseNormalizedDecisionWire    : ByteArray -> Option RawDecisionWire
```

Strong desired results:

```lean
parseNormalizedDecisionWire (encodeRawDecisionWireCanonical raw) = some raw
```

for schema-valid raw values, and, if feasible, a canonicality theorem saying every
accepted canonical byte sequence round-trips to the identical bytes.

The canonical encoder should:
- use UTF-8;
- use deterministic object key order;
- use JSON escaping compatible with the executable exporter;
- emit booleans/null/arrays/objects deterministically;
- never normalize Unicode silently.

Inspect the separate repository branch `v06/canonical-json` if useful. It contains
an RFC 8785/JCS research implementation and cross-language vectors. Do not merge
v0.6 semantics into v0.5 silently. The current normalized-wire schema's lack of
numbers may permit a much smaller exact encoder whose bytes are already compatible
with v0.5 canonical hashing.

Add frozen Python/Lean golden vectors if needed.

Then **continue to Phase 4**.

---

# Phase 4 — move wire semantic-hash verification into Lean

Today the raw wire contains:

```text
wire_semantic_hash
```

but the Lean structural decoder deliberately ignores it.

Try to verify it formally.

The Python definition is SHA-256 over the canonical JSON of the wire object with
`wire_semantic_hash` removed.

Preferred target:

```lean
recomputeWireSemanticHash : RawDecisionWire -> Digest256
wireHashMatches : RawDecisionWire -> Bool
```

and a checked path that requires the recomputed digest before acceptance.

## SHA-256 stretch target

Implement a small pure Lean SHA-256 over bytes and test it against standard published
SHA-256 vectors plus PCS frozen vectors.

The objective here is **functional correctness of the digest computation**, not a
cryptographic collision-resistance proof.

If feasible, define the SHA-256 specification and prove the implementation refines
that specification. If a full implementation-correctness theorem is too large, still
produce:
- a pure Lean implementation;
- FIPS/NIST-style known-answer vectors;
- exact PCS cross-language vectors;
- a sharply stated residual assumption.

No `native_decide`, `extern`, or opaque foreign hash function is allowed in the
formal theorem path.

Then compose:

```text
serialized wire bytes
  -> parse
  -> recompute canonical payload
  -> SHA-256 equality
  -> checkedDecodeRawWire
  -> WellFormed
  -> Assures
```

Then **continue to Phase 5**.

---

# Phase 5 — bind the normalized wire to its source certificate as far as possible

Current Python verification requires the normalized wire to reproduce exactly from a
replay-verified source certificate.

Try to formalize the strongest useful subset.

At minimum:
- formalize the source certificate semantic-hash field as an exact 256-bit/hex value,
  not an unconstrained arbitrary string if practical;
- prove the parsed wire preserves source claim identity;
- prove source certificate hash and claim ID are carried unchanged through the
  checked decoder;
- model a minimal verified-certificate summary sufficient to reproduce the
  claim-scoped RawDecisionWire;
- prove normalization of that summary produces the same checked wire.

A useful target is:

```lean
normalizeVerifiedSummary summary claim = some raw
  ->
checkedDecodeRawWire raw = some w
  ->
source binding + WellFormed w
```

Do not pretend this proves Python scientific replay. Treat "verified certificate
summary" as a typed boundary unless you actually formalize the verifier below it.

Then **continue to Phase 6**.

---

# Phase 6 — attack certificate/package bytes

Push farther if feasible.

Explore a small formal model for:
- normalized index parsing;
- exact claim ordering/scope;
- package manifest file binding;
- certificate semantic/integrity hash equality;
- normalized wire path safety;
- no missing or unexpected normalized files.

If direct ZIP parsing is too large, isolate ZIP extraction as a byte/file-map boundary
and prove the rest over a typed finite map of filenames to bytes.

Strong useful target:

```text
PackageFileMap
  + verified manifest hashes
  + parsed certificate summary
  + parsed normalized wires
  -> exact normalized-source binding
  -> checked raw wire
  -> Assures
```

Again: do not call this raw ZIP end-to-end if ZIP decoding remains external.

Then **continue to Phase 7**.

---

# Phase 7 — cryptographic signature boundary

Attempt Ed25519 only if technically plausible.

Preferred goal:
- pure Lean signature-message construction;
- exact domain/version separation;
- exact public-key fingerprint/hash binding;
- if feasible, a verified/pure Lean Ed25519 verifier or a mechanically checked small
  verifier.

If full Ed25519 is not realistically closable in this pass, do **not** add an axiom.

Instead parameterize the higher-level theorem over an explicit proof object such as:

```lean
SignatureAuthentic publicKey message signature
```

and prove everything above it conditionally, so the residual cryptographic TCB is one
named hypothesis rather than hidden implementation trust.

The same rule applies to SHA-256 if necessary: explicit theorem hypotheses are
acceptable; new global axioms are not.

Then **continue to Phase 8**.

---

# Phase 8 — scientific replay boundary

Do not make a universal claim that arbitrary Python/R/C++ computation is verified.

Instead try to formalize the interface required of a domain adapter.

A useful shape might be:

```lean
structure ReplayCertificate where
  evidenceId : String
  predicateCommitment : ...
  outcome : Outcome
  sound : ...
```

or another explicit proof-carrying adapter interface.

Show that a domain adapter supplying a valid proof/replay certificate can enter the
same normalized assurance chain without broadening the trusted kernel.

If the existing restricted PK/PD analytic checker is small enough, consider
formalizing that **specific** model/checker as a demonstration, but do not let this
block the serialization work.

---

# Phase 9 — strongest integrated theorem obtainable

At the end of the pass, construct the strongest theorem actually justified by the
work.

Ideal unconditional form:

```lean
verifyNormalizedWireBytes bytes = some accepted
  -> Assures accepted.Γ accepted.level accepted.claim accepted.evidence
```

Stronger package-level form if feasible:

```lean
verifyPackageFileMap package = some accepted
  -> Assures ...
```

If some lower component remains external, produce the strongest **parameterized**
theorem with each residual TCB hypothesis visible in the theorem arguments.

Do not bury assumptions in definitions.

---

# Phase 10 — adversarial / falsification campaign

For every new parser/checker layer, add attacks for at least:

- duplicate keys;
- reordered keys;
- extra unknown keys;
- missing required keys;
- trailing bytes;
- malformed escapes;
- Unicode edge cases;
- forged invariant booleans;
- forged wire hash;
- altered source certificate hash;
- altered claim ID;
- duplicate evidence;
- evidence reorder/substitution;
- context reorder/substitution;
- predicate commitment substitution;
- decision substitution;
- unknown enum/version tokens;
- validly rehashed but semantically forged objects;
- downgrade between serialization/hash/signature versions.

Prefer closed Lean examples where possible, plus Python cross-language fixtures where
needed.

---

# Phase 11 — promotion and repository hygiene

For every layer that closes:

1. promote it from `ProofTasks` to `PCS/`;
2. import it from `PCS.lean`;
3. add permanent `#print axioms` coverage;
4. remove/replace staged `sorry` files with regression examples;
5. document exact scope/non-claims;
6. keep production formal root free of:
   - `sorry`
   - `admit`
   - new `axiom`
   - `unsafe`
   - `implemented_by`
   - `extern`
   - `native_decide`.

Do not promote speculative/incomplete modules.

---

# Phase 12 — full independent verification

Run all existing gates plus every new one.

Minimum:

```text
cd formal
lake build
bash scripts/verify_lean.sh
cd ..
python -m pytest -q
python scripts/adversarial_campaign.py
```

Run any new parser/hash/cross-language vector tests explicitly.

If Node is available and JCS/canonical JSON work is used, run the cross-language JS
vectors too.

Freeze a new verification report under `results/` containing:
- exact commit/tree;
- tool versions;
- commands and exit codes;
- theorem list;
- axiom dependencies;
- adversarial results;
- frozen vector hashes;
- residual TCB matrix.

---

# Required final report format

Return a boundary table with one row per layer:

```text
raw ZIP bytes
ZIP extraction
raw JSON bytes
UTF-8 decoding
JSON parsing
duplicate-key rejection
schema validation
canonical serialization
SHA-256
Ed25519
certificate replay
normalized-wire derivation
RawDecisionWire decode
wireCheck
WellFormed
Normalized.DecisionInput
Assures
```

For every row label it exactly one of:
- PROVED
- EXECUTABLY TESTED
- CONDITIONAL ON EXPLICIT HYPOTHESIS
- OPEN
- FALSIFIED

For PROVED rows give the exact Lean theorem.
For EXECUTABLY TESTED rows give exact tests/vectors.
For conditional rows give the exact theorem hypothesis.
For OPEN/FALSIFIED rows explain the minimal blocker/counterexample.

Also give the strongest integrated theorem now available and a plain-language
statement of exactly what PCS can and cannot honestly claim after this pass.

---

# Research behavior

Be aggressive.

Do not stop merely because the initial requested theorem has been solved.
Search for the next compositional theorem, prove it, promote it, and continue until a
genuine technical blocker is reached.

But falsification has priority over completion. If a desired theorem is false, find
the counterexample and redesign the boundary explicitly rather than weakening the
claim.

The objective is not to make the report look green. The objective is to shrink the
real trusted computing base as far as possible.
