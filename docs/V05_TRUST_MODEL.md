# v0.5.1 Trust Model

## Five independent questions

1. **Did the scientific certificate replay correctly?**  
   `verify_certificate` re-runs supported checks, validates artifact bindings, and re-derives claim status.

2. **Does each required evidence object actually refer to the same predicate as the claim?**  
   v0.5.1 requires full required-evidence predicate binding; one matching witness can no longer hide unrelated required evidence.

3. **Does the delivered normalized formal handoff exactly reproduce from that certificate?**  
   Every attestation emits claim-scoped `pcs-normalized-decision-v1` states. Bundle verification independently re-normalizes the certificate and requires exact equality. The receipt reports this separately as `normalized_refinement`.

4. **Is this the exact package the signer issued?**  
   `package_manifest.json` hashes all delivered files and `package_signature.json` authenticates that manifest.

5. **Does the reviewer accept these results?**  
   A separate acceptance policy applies reviewer-defined claim/status and signer requirements.

These layers are deliberately independent. A valid signature does not make a scientific claim true; a replay-valid certificate does not force a reviewer to accept it; and a correctly signed normalized state is rejected if it does not actually derive from the delivered certificate.

## Machine-checked boundary

The following implication layer is machine-checked under Lean 4.28.0:

```text
Normalized.DecisionInput
   + accepted decide status
   -> Assures Γ L C E
```

PR #17 extends the executable/formal interface with a typed claim-scoped `DecisionWire`. The finite theorem target is:

```text
wireCheck w = true
   -> PCS.Wire.WellFormed w
   -> Normalized.DecisionInput
   -> Assures Γ L C E
```

Raw JSON parsing, Python domain replay, SHA-256/Ed25519 implementations, and the JSON-text → raw typed-wire construction remain explicit lower TCB boundaries.

## Threats covered by the current encoded campaign

The campaign includes attacks against:

- artifact modification;
- certificate/hash rewriting;
- forged PASS/status/details;
- partial and unrelated semantic evidence binding;
- workflow-summary forgery;
- PK/PD output tampering;
- package report tampering;
- package-manifest recomputation without the signing key;
- signer substitution against pinned identity;
- external reviewer-policy rejection;
- private-key leakage into bundles;
- stale output contamination;
- duplicate/colliding/nonportable ZIP namespaces;
- duplicate JSON object keys;
- post-hoc claim rewriting after intake freeze;
- rehashed normalized-decision forgery;
- **validly re-signed normalized-state substitution**.

This finite campaign is executable falsification evidence, not a proof of absence of vulnerabilities.
