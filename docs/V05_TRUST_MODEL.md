# v0.5 Trust Model

## Three independent questions

1. **Did the scientific certificate replay correctly?** `verify_certificate` re-runs supported checks and validates artifact bindings.
2. **Is this the exact package the signer issued?** `package_manifest.json` hashes all delivered files and `package_signature.json` authenticates that manifest.
3. **Does the reviewer accept these results?** A separate acceptance policy applies reviewer-defined claim/status and signer requirements.

These layers are intentionally separate. A valid signature does not make a scientific claim true, and a replay-valid certificate does not force a reviewer to accept it.

## Threats covered in the frozen v0.5 campaign

- artifact modification;
- certificate/hash rewriting;
- forged PASS/status/details;
- semantic evidence misbinding;
- workflow-summary forgery;
- package report tampering;
- package-manifest recomputation without signing key;
- signer substitution against pinned identity;
- producer-supported claim rejected by external reviewer policy.

The campaign is evidence about these concrete attacks, not a proof of absence of vulnerabilities.
