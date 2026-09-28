# Runtime Provenance

## Purpose

PCS records the computational environment that produced an attestation so a reviewer can distinguish **scientific evidence** from **execution context** and can diagnose reproducibility differences between runs.

A runtime match is provenance evidence. It is **not** proof that a scientific result is correct.

## v0.5 runtime snapshot

`pcs snapshot-env -o runtime.json` records a deterministic, secrets-free snapshot containing:

- Python implementation and version;
- operating-system family/release;
- machine architecture;
- normalized installed Python package names and versions;
- a semantic hash of the normalized snapshot.

PCS deliberately does **not** record environment variables, credentials, tokens, home-directory contents, command history, or arbitrary host files.

`pcs attest` automatically writes `runtime.json` into the evidence package **before** the package manifest is created. Therefore the signed package manifest cryptographically binds the runtime provenance delivered to a reviewer.

## Integrity

A runtime snapshot has format:

```text
pcs-runtime-v1
```

Its `semantic_hash` is recomputed over the normalized snapshot excluding the hash field itself. `env-diff` refuses snapshots whose recorded semantic hash no longer matches their contents.

## Comparison

```bash
pcs snapshot-env -o run-a.json
pcs snapshot-env -o run-b.json
pcs env-diff run-a.json run-b.json
```

The diff reports:

- Python metadata changes;
- platform metadata changes;
- packages added;
- packages removed;
- package-version changes.

PCS does not automatically convert any of those differences into scientific claim failure. A reviewer or domain policy may decide that a particular workflow requires a matching runtime, while another workflow may be robust across environments.

## Trust boundary

The current snapshot is descriptive. It trusts Python/platform metadata exposed by the runtime and package metadata exposed by installed distributions. Future work may add independently attested container digests, SBOMs, signed build provenance, or hardware/runtime identity.

Those stronger mechanisms should remain separate from the scientific claim calculus: reproducibility context and scientific correctness are related but not interchangeable.


## Mid-attestation drift guard

The attestation path now snapshots the runtime **before** certificate generation/replay and snapshots it again before any certificate/package signature is issued. If the runtime semantic hash changes during that interval, attestation fails closed and no evidence ZIP is produced.

This guard does not prove that the runtime is correct or uncompromised. It establishes the narrower property that one signed attestation is not silently assembled across two different recorded Python/platform/package environments.
