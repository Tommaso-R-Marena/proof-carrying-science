# PCS v0.6 reviewer verifier

The reviewer-facing path is intentionally narrower than the producer/development
surface.

## One-command verification

Create a local trust profile next to the public key and, optionally, the receiver's
acceptance policy:

```json
{
  "format": "pcs-verifier-trust-v1",
  "public_key": "trusted-producer.pem",
  "expected_signer_fingerprint": "<64-hex-ed25519-public-key-fingerprint>",
  "policy": "reviewer-policy.json",
  "lean_authority": "pcs-lean-authority"
}
```

Then run:

```bash
pcs-verifier-v06 delivered.pcs.zip --trust trust.json --receipt receipt.json
```

The equivalent full PCS command is:

```bash
pcs verify-local-v06 delivered.pcs.zip --trust trust.json --receipt receipt.json
```

The trust profile is receiver-owned and external to the delivered package. Paths are
resolved relative to the trust-profile file. `lean_authority` is optional when using
the standalone verifier because that artifact embeds the compiled Lean authority; it
is useful when the receiver wants to pin a separately managed authority executable.

A successful Python precheck is not an authoritative PCS result. The reviewer path
returns authoritative `valid: true` only after the Lean authority accepts the same
decoded package-member bytes and a canonical observation transcript bound to the
certificate semantic hash and checker version. Missing, crashing, malformed, or
rejecting authority execution fails closed.

## Standalone artifacts

Build locally (Lean/Lake is required at build time):

```bash
python -m pip install -e '.[standalone]'
cd formal && lake build pcs-lean-authority && cd ..
python scripts/build_verifier_artifact.py -o dist/pcs-verifier-v06
```

The build produces a single executable and an adjacent
`pcs-verifier-v06[.exe].manifest.json` containing its SHA-256, platform, Python
version, entry point, whether the Lean authority is embedded, the authority
executable SHA-256, and the authority transcript protocol.

The main CircleCI product-hardening gate builds the Linux single-file artifact,
executes its `--help` smoke test, and stores the executable plus SHA-256 manifest as
CI artifacts. `.github/workflows/build-verifier-artifacts.yml` also defines Linux,
Windows, and macOS builds; those cross-platform jobs remain a configured packaging
path and should not be described as observed runtime evidence until their runs are
available.

## Boundary

A standalone executable improves deployability and prevents Python-only acceptance,
but it does **not** prove the ZIP decoder, Python-to-Lean materialization/invocation,
environment capture, static workflow analysis, or non-chemistry replay semantics
correct. Those remain explicit external contracts. Lean independently checks the
canonical package/signature/hash/index/decision structure and independently replays
`reaction_balance`; the observation transcript supplies the external stages that
the theorem already models as oracles. The artifact also does not expand the
scientific claim types PCS supports.
