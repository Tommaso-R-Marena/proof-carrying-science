# Launch Readiness Scorecard

Use PASS / PARTIAL / OPEN rather than a marketing score.

| Gate | Current v0.5 state |
|---|---|
| Self-contained replayable certificate | PASS |
| Artifact integrity and path safety | PASS for current supported formats |
| Claim/evidence semantic binding | PASS for current built-in predicates |
| Stable semantic identity | PASS |
| Ed25519 certificate signing | PASS |
| Signed package manifest binds report + delivered files | PASS |
| Signer fingerprint pinning | PASS |
| External reviewer acceptance policy | PASS |
| Reproducible evidence ZIP | PASS |
| Certificate diff | PASS |
| Private-key material refused from evidence ZIPs | Implemented; full suite rerun pending CI |
| Non-empty/stale attestation output refused | Implemented; full suite rerun pending CI |
| Runtime provenance bound into attestations | Implemented; full suite rerun pending CI |
| Generated limitations statement bound into attestations | Implemented; full suite rerun pending CI |
| PK + direct-Emax restricted adapter | PASS for declared scope |
| Automated-test inventory | 66 tests currently in repository |
| Last retained full Python execution | PASS (44/44 before later decision/refinement/security/provenance additions); current 60-test inventory pending full rerun |
| New decision vectors | PASS in direct evaluation; full repository suite pending CI |
| Frozen adversarial campaign inventory | 23 cases currently encoded |
| Last fully executed adversarial campaign | PASS (16/16 rejected, 0 false accepts in that finite campaign); not a proof |
| New private-key, stale-output, and ZIP-namespace cases | Implemented; full 23-case campaign pending execution |
| Machine-compiled Lean kernel | OPEN |
| Python-to-Lean whole-claim refinement | PARTIAL: source architecture + conformance vectors; machine proof OPEN |
| External design-partner workflow | OPEN |
| Paid pilot agreement | OPEN |
| Entity/banking/legal operations | OPEN |
| GxP validated product | OPEN / not required for early pilot |
| Regulatory endorsement | NOT CLAIMED |


Authoritative execution bookkeeping: `results/EXECUTION_LEDGER.md`.
