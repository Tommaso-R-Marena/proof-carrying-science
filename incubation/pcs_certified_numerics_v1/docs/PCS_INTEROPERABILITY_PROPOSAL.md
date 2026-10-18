# Optional future PCS interoperability (proposal only)

**Not enacted.** No production integration in this assignment.

Suggestion: treat `certnum-cert-v1` as a *mathematical witness attachment* that a future PCS Claim IR field could hash and point to. PCS production signing and policy remain authoritative for organizational assurance; CertNum remains the mathematical checker for numerical claims.

Interface sketch:

1. PCS claim references `certnum` certificate digest.
2. Reviewer runs `certnum verify` in an isolated environment.
3. No shared signing keys; no submodule coupling.
