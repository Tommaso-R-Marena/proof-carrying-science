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
  "policy": "reviewer-policy.json"
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
resolved relative to the trust-profile file.

## Standalone artifacts

Build locally:

```bash
python -m pip install -e '.[standalone]'
python scripts/build_verifier_artifact.py -o dist/pcs-verifier-v06
```

The build produces a single executable and an adjacent
`pcs-verifier-v06[.exe].manifest.json` containing its SHA-256, platform, Python
version, and entry point.

The main CircleCI product-hardening gate builds the Linux single-file artifact,
executes its `--help` smoke test, and stores the executable plus SHA-256 manifest as
CI artifacts. `.github/workflows/build-verifier-artifacts.yml` also defines Linux,
Windows, and macOS builds; those cross-platform jobs remain a configured packaging
path and should not be described as observed runtime evidence until their runs are
available.

## Boundary

A standalone executable improves deployability; it does **not** remove its runtime,
OS, Python/PyInstaller, cryptography-library, or platform behavior from the trusted
computing base. It also does not expand the scientific claim types PCS supports.
