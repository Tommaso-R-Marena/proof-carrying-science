# Witness bootstrap, keys and executable operation

The operator prepares these files outside the untrusted request interface:

- Existing root JSON from `root.encode()`, pinned to exact scientific genesis,
  intent principals, fixed policy and checker configuration identity.
- Exact `OperatorConfig` JSON in the unchanged host's configuration format.
- A fresh third Ed25519 private key as exactly 32 raw bytes, regular nonsymlink
  file, mode 0600. It must differ from both existing intent keys.
- A dedicated witness SQLite path. Existing state is never silently overwritten
  or replaced by a new genesis.
- Out-of-band receiver-pinned root and witness public key. The key in a server
  ready file or response is informational; it is not trusted bootstrap evidence.

Explicit initialization, then separate-process operation:

```sh
python -m research.scientific_witness_v1.server init \
  --db /operator/witness.sqlite --root /operator/root.json \
  --config /operator/verifier.json --key /operator/witness.key
python -m research.scientific_witness_v1.server serve \
  --db /operator/witness.sqlite --root /operator/root.json \
  --config /operator/verifier.json --key /operator/witness.key \
  --bind 127.0.0.1 --port 0 --ready-file /operator/ready.json
```

Initialization executes actual fixed-verifier genesis checking. Serving an
existing store authenticates its state and actually rechecks genesis. Missing or
corrupt state fails; operator recovery must be explicit. The ready file uses
exclusive creation and contains port/public key/Profile A label, no private key.
Producer clients receive no key-file path or server configuration arguments.

A receiver constructs:

```python
client = WitnessClient(url, pinned_root, fixed_config, pinned_witness_public_key)
view = client.checkpoint()  # Fresh challenge generated inside client.
```

Each response is verified under the independently retained key/root/configuration,
action domain and nonce. Permanent prepared/finalized receipts are historical;
only a fresh checkpoint can support current serving decisions.

For remote reference deployment add `--cert` and `--tls-key`, bind the designated
TLS address, and give clients the verified HTTPS URL and operator-trusted CA if
needed. No certificate-verification bypass is provided. TLS identity and witness
Ed25519 key bootstrap are separate and both must be administered intentionally.
The reference supports remote operation but this work does not provision a host,
change production infrastructure, or claim external independent administration.

For a separately owned Linux reference, an administrator should install immutable
reviewed verifier sources/imports under an operator-owned read-only tree, create a
nonprivileged witness OS user, place witness key/store/config under that user's
private directory and keep producer users unable to write those paths or read the
key. The witness process needs only its fixed scientific verifier, read-only
imports, its own store and transport listener. Do not give it producer signing
keys. These deployment directions are not evidence that a separate-user or host
experiment was executed; such evidence must include actual UIDs/access checks.
Host root compromise and simultaneous replacement of all bootstrap material remain
outside the protection even after ordinary-user separation.

Key rotation, policy upgrades, historical checker migration, revocation and
Byzantine multiwitness consensus are unsupported. New keys/configurations in an
old stream are rejected. A future reviewed protocol version must specify their
mathematics and implementation; they cannot be silently accepted as metadata.
