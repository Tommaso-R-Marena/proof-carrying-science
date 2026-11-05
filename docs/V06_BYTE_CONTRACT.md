# PCS v0.6 frozen byte contract

Status: **research contract; not yet the released PCS wire format**.

This layer makes the executable side of the v0.6 trust boundary explicit enough
for independent implementations and formalization to target identical bytes.

## Acceptance chain

A v0.6 signed certificate is accepted only through:

```text
raw certificate bytes
  -> strict UTF-8, no BOM
  -> duplicate-aware JSON parse
  -> byte-for-byte RFC 8785 JCS canonicality
  -> v0.6 JSON Schema / version-domain checks
  -> domain-separated semantic + integrity SHA-256 verification
  -> canonical signature-record parse
  -> Ed25519 domain/payload/fingerprint verification
```

A package-file-map acceptance additionally requires:

```text
canonical package manifest bytes
  + canonical certificate bytes
  + canonical package signature bytes
  + exact signed member byte map
  -> portable/collision-free namespace
  -> exact member set
  -> exact byte sizes + SHA-256
  -> certificate.json byte identity
  -> certificate hash binding
  -> package-signature domain binding
```

The implementation is `pcs/byte_contract_v06.py`.

## Why canonical bytes are required here

The ordinary package tooling may parse semantically equivalent JSON for usability.
The cryptographic interchange boundary is intentionally stricter: an accepted v0.6
contract file must already equal its RFC 8785 canonical byte representation.

That gives every implementation, including Lean, one byte sequence for a given
accepted object. Pretty-printing, key reordering, alternate escaping, BOMs and
trailing newlines are rejected at this boundary rather than normalized silently.

## Frozen corpus

`tests/v06_golden/` contains:

- `certificate.json`
- `certificate_signature.json`
- `package_manifest.json`
- `package_signature.json`
- `artifacts/fixture.bin`
- `metadata.json`

The Ed25519 key is a deterministic **test-only** key. No private production key is
stored in the corpus.

`scripts/generate_v06_golden_contract.py` deterministically reconstructs the
corpus from the v0.6 code and refuses drift in check mode.

## Adversarial contract tests

`tests/test_v06_byte_contract.py` includes rejection checks for:

- noncanonical leading/trailing whitespace;
- UTF-8 BOM and invalid UTF-8;
- duplicate decoded object names;
- pretty-printed but semantically equivalent JSON;
- v0.5-to-v0.6 downgrade attempts;
- artifact modification;
- unsigned extra files;
- missing signed files;
- certificate member byte substitution;
- signature-domain substitution.

These complement the existing strict-parser, JCS, crypto-domain, schema,
certificate, signature, package and namespace tests.

## Gate

Run:

```text
python scripts/run_v06_contract_gate.py
```

A passing gate requires:

1. exact golden-corpus reproduction;
2. the full v0.6 Python test set;
3. Node/browser cross-language vectors;
4. deterministic Python-versus-Node JCS differential stress (default 20,000 finite
   IEEE-754 values and 500 randomized Unicode objects);
5. the PCS adversarial campaign;
6. the complete Python test suite;
7. a clean Git working tree.

The gate freezes command outputs and a machine-readable result under
`results/v06-contract-runs/`.

## Formal meeting point

This contract is intentionally shaped to match the formal research target:

```text
PackageFileMap / canonical JSON bytes
       -> RawDecisionWire / checked serialized state
       -> DecisionWire
       -> wireCheck
       -> WellFormed
       -> Assures
```

The executable contract does **not** prove the correctness of UTF-8 decoding,
the JSON parser, RFC 8785 implementation, SHA-256, Ed25519, JSON Schema engine,
or scientific replay. Those remain explicit formal/TCB targets rather than hidden
inside the acceptance claim.


## Typed scientific certificate layer

The v0.6 certificate is no longer an arbitrary nested JSON envelope. The certificate
schema now gives exact shapes to assumptions, claims, predicates, evidence,
artifacts and workflow nodes, and `pcs/certificate_semantics_v06.py` enforces the
cross-object invariants JSON Schema cannot express.

In particular:

- claim, assumption, artifact, evidence and workflow-node IDs are unique;
- claim/assumption scope is bidirectional;
- claim/evidence support binding is bidirectional;
- every claim has an explicit typed predicate;
- every required evidence object carries the exact same predicate as its claim;
- evidence predicates are derived exactly from their check specifications;
- built-in evidence artifact bindings are exact;
- claim assessments are recomputed by the pure decision kernel;
- artifact paths are canonical relative paths;
- workflow artifact references, single-producer semantics, acyclicity and the
  topological summary are recomputed.

This is still a structural/logical consistency layer. It does not turn a recorded
PASS into a scientifically established PASS; domain replay remains a distinct
verification boundary.
