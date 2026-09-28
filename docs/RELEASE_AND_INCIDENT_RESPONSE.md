# Release and Incident Response — Pilot Baseline

## Release identity

Every pilot delivery should record:

- PCS semantic version;
- repository commit SHA;
- certificate semantic/integrity hashes;
- package SHA-256;
- signer fingerprint;
- reviewer policy version;
- Python/runtime provenance hash;
- Lean-kernel status for that release.

Do not imply that a source-formalized Lean component was machine checked unless the recorded release has successful build evidence.

## Release procedure

1. Freeze the pilot claim inventory and assumptions.
2. Start from an empty evidence output directory.
3. Verify source artifact hashes and scope.
4. Run the supported checks / proof adapters.
5. Produce the attestation.
6. Review all OPEN and failed claims; do not suppress them.
7. Confirm `LIMITATIONS.md` accurately reflects certificate scope.
8. Independently verify the evidence ZIP from a fresh temporary directory.
9. For signed pilots, verify against the pinned expected signer fingerprint.
10. Apply the reviewer-supplied acceptance policy.
11. Record bundle SHA-256 and release metadata.
12. Deliver only through the approved channel.
13. Complete retention/deletion obligations after reviewer acceptance/closeout.

## No silent overwrite

PCS attestation refuses non-empty output directories. A new run creates a new evidence package. If a result changes, use certificate/bundle comparison rather than mutating an already issued package.

## Incident classes

### Integrity/authenticity incident
Examples: signature mismatch, package-manifest mismatch, leaked signing key, altered report, unbound file.

Action: stop delivery/use of the affected package, preserve bytes/logs, determine affected signer/releases, rotate key if relevant, and reissue only after root cause is understood.

### Scientific-assurance incident
Examples: a check was unsound, a hidden dependency invalidates a claim, a workflow artifact was omitted, an accepted claim should have remained OPEN.

Action: reopen dependent claims, identify downstream packages, issue a corrected certificate/package, and record the reason. Do not preserve an incorrect supported status for reputational reasons.

### Data-handling incident
Examples: unauthorized sensitive data entered a workspace, retention exceeded agreement, access scope was wrong.

Action: stop processing, preserve minimal incident evidence, restrict access, follow the governing agreement and applicable legal/security procedures, and notify the appropriate responsible parties.

## Severity heuristic

- **Critical:** credible signer compromise, false assurance on a consequential workflow, or sensitive-data exposure.
- **High:** issued package integrity failure, unsound checker affecting supported claims.
- **Medium:** reproducibility/provenance defect that does not alter current claim status.
- **Low:** documentation/UI defect with no evidence or policy impact.

The severity label is operational triage, not a legal determination.

## Post-incident rule

A discovered false accept is a research result as well as a product defect. Add a regression test/adversarial case whenever technically possible and update the trust-boundary documentation.
