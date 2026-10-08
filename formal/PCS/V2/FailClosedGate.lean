import PCS.V2.Witnesses.Instances
import PCS.V2.CanonicalArchive

/-!
# Fail-closed gates of the authoritative verifier

Before this file, the authority executed by `pcs-lean-authority` dispatched every replay
request to the verified built-in checkers, then to the registered domain checkers, and
**fell back to the host transcript** for any request no certified checker handles.  An
evidence item whose `check_spec.type` is unregistered (or missing) therefore passed replay
whenever the transcript reported the recorded outcome ‚Äî even `PASS` over data that violates
the declared property (`PCS.V2.GoldenCx`).  A second, related gap existed at the claim
level: a claim recorded as supported could cite `PASS` evidence whose certified check
concerns *other* parameters than the claim's own predicate (only the evidence's declared
`predicate` field is bound to the claim, not its `check_spec`).

This file defines the two gates the authoritative verifier now enforces, and the strict
acceptance function built from them.

* **Check-type gate** (`supportedEvidenceB`): every evidence item of the certificate ‚Äî
  whatever its recorded outcome, and whether or not any claim requires it ‚Äî must be handled
  by a certified Lean checker (one of the six verified built-ins or a registered,
  proof-carrying domain checker).  Otherwise the archive is rejected with stage
  `unsupported_check_type`, *before* replay.
* **Claim-binding gate** (`claimsBoundB`): every certificate claim recorded at an assurance
  level (`FORMALLY_PROVEN`, `COMPUTATIONALLY_SUPPORTED`, `EMPIRICALLY_SUPPORTED`,
  `MIXED_SUPPORTED`) whose predicate is decoded by a registered domain adapter must be
  domain-accepted by that adapter, from its own required evidence, through the deterministic
  canonical obligation graph of a `ClaimBinder`.  Otherwise: stage `claim_binding`.

`acceptPCSStrictWith fb` runs the existing acceptance pd—P–ÄL@ıﬂç4r´