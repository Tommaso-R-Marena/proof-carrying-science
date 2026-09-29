# PCS v0.6 canonical JSON profile

Status: **research / not yet a released wire format**.

PCS v0.5 hash and signature semantics are frozen. Nothing in this document changes how an existing `pcs-0.5` certificate, package manifest, runtime snapshot, intake lock, or Ed25519 record is verified.

## Decision

PCS v0.6 uses RFC 8785 JSON Canonicalization Scheme (JCS) as the canonical JSON encoding for new versioned cryptographic payloads. The PCS profile identifier is `pcs-jcs-rfc8785-v1`.

JCS supplies the cross-language properties PCS needs: the I-JSON data model, ECMAScript-compatible primitive and binary64 number serialization, recursive deterministic object-property ordering by UTF-16 code units, no insignificant whitespace, and UTF-8 output.

## Normative PCS profile

1. Input MUST be JSON data: null, Boolean, binary64 number, Unicode string, array, or object with string keys.
2. Duplicate object names MUST be rejected before canonicalization, including names that become equal after JSON escape decoding.
3. NaN and positive or negative Infinity MUST be rejected.
4. Lone UTF-16 surrogates and Unicode noncharacters MUST be rejected.
5. Numbers use ECMAScript/JCS binary64 spelling. `-0` canonicalizes to `0`, `1.0` to `1`, and notation follows the ECMAScript `1e-6` and `1e21` boundaries.
6. Object keys are sorted recursively by unsigned UTF-16 code units. Array order is preserved.
7. Unicode strings are preserved as-is. PCS MUST NOT silently NFC/NFD-normalize strings before hashing.
8. Canonical text is encoded as UTF-8 with no BOM and no trailing newline.
9. Exact numbers whose semantics require precision beyond binary64 MUST be represented as schema-defined strings.

## Reference implementation and vectors

- Python canonicalizer and duplicate-aware parser: `pcs/canonical_json.py`
- Browser/ECMAScript canonicalizer: `site/jcs.mjs`
- Browser duplicate-aware raw JSON parser: `site/strict_json.mjs`
- Frozen vectors: `tests/canonical_json_vectors.json`
- Python tests: `tests/test_canonical_json_v06.py`
- Cross-language Node gate: `scripts/check_jcs_cross_language.mjs`
- Deterministic differential stress harness: `scripts/stress_jcs_against_node.py`

The frozen suite includes the RFC 8785 core example, UTF-16 property ordering, nested objects, integer/float equivalence, negative zero, Unicode normalization preservation, notation boundaries, and the RFC Appendix B number edge cases. During development the Python number serializer was additionally compared against Node/V8 over 20,000 random finite IEEE-754 values with no mismatch.

## Versioned hash and signature domains

v0.6 MUST introduce new format identifiers. A verifier MUST NOT reuse a v0.5 format name while changing the canonicalization underneath it.

Planned domain identifiers:

- `pcs-certificate-semantic-sha256-v2`
- `pcs-certificate-integrity-sha256-v2`
- `pcs-runtime-semantic-sha256-v2`
- `pcs-intake-semantic-sha256-v2`
- `pcs-certificate-signature-v2`
- `pcs-package-signature-v2`

Each domain binds an explicit format/version field inside the JCS payload. The research implementation is `pcs/crypto_domains_v06.py`: SHA-256 uses a `pcs-jcs-sha256-v1` envelope and Ed25519 payload bytes use a `pcs-jcs-ed25519-payload-v1` envelope. v0.5 verification remains unchanged.

## Boundary

Canonicalization does not prove parser, schema, SHA-256, or Ed25519 correctness. The intended v0.6 path is:

```text
raw JSON bytes
  -> duplicate-aware strict parser
  -> schema + format validation
  -> RFC 8785 canonical bytes
  -> SHA-256 / Ed25519
```

The Python and browser reference parsers are executable reference code, not formal parser-correctness proofs.

## Downgrade rule

A verifier MUST select hash/signature semantics from the explicit format/spec version. It MUST NOT try both v0.5 and v0.6 encodings and accept whichever verifies.

## Remaining integration work

1. Define concrete v0.6 certificate/package schemas that consume the new domain envelopes.
2. Integrate the Node cross-language gate into release verification where Node is available.
3. Decide whether Lean consumes canonical bytes directly or a separately checked digest/decoder relation.
4. Keep v0.6 changes off the v0.5 release path until the new certificate/package vectors are frozen.
