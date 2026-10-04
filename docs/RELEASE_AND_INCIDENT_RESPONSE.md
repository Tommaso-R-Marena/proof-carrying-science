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

## Local release gate

Run from a clean committed checkout. The release gate now includes repository-metadata and governance validation before scientific/product checks:

```bash
python scripts/check_repository_integrity.py
python scripts/run_release_gate.py
```

This freezes the exact commit, runtime provenance, `pcs doctor`, Python tests, adversarial campaign, reference demo, formal placeholder audit, and a Lean `lake build` when Lake is available under `results/runs/<timestamp>-<commit>/`.

For a release where PCS will claim the Lean kernel is machine checked, require Lean explicitly:

```bash
python scripts/run_release_gate.py --require-lean
```

Do not promote inventory counts to executed claims without the retained run directory.

## Release procedure

1. Confirm the candidate is based on current `main`; inspect `git diff --summary origin/main...HEAD` for unexpected mode, rename, or path changes.
2. Run `python scripts/check_repository_integrity.py` and require PASS.
3. Freeze the pilot claim inventory and assumptions.
4. Start from an empty evidence output directory.
5. Verify source artifact hashes and scope.
6. Run the supported checks / proof adapters.
7. Produce the attestation.
8. Review all OPEN and failed claims; do not suppress them.
9. Confirm `LIMITATIONS.md` accurately reflects certificate scope.
10. Independently verify the evidence ZIP from a fresh temporary directory.
11. For signed pilots, verify against the pinned expected signer fingerprint.
12. Apply the reviewer-supplied acceptance policy.
13. Record bundle SHA-256 and release metadata.
14. Deliver only through the approved channel.
15. Complete retention/deletion obligations after reviewer acceptance/closeout.

## No silent overwrite

PCS attestation refuses non-empty output directories. A new run creates a new evidence package. If a result changes, use certificate/bundle comparison rather than mutating an already issued package.

## Incident classes

### Integrity/authenticity incident
Examples: signature mismatch, package-manifest mismatch, leaked signing key, altered report, unbound file.

Action: stop delivery/use of the affected package, preserve bytes/logs, determine affected signer/releases, rotate key if relevant, and reissue only after root cause is understood.

### Scientific-assurance incident
Examples: a check was unsound, a hidden dependency invalidates a claim, a workflow artifact was omitted, an accepted claim should have remained OPEN.

Action: reopen dependent claims, identify downstream packages, issue a corrected certificate/package, and record the reason. Do not preserve an incorrect supported status for reputational reasons.

### Repository-integrity / integration incident
Examples: executable-bit loss, line-ending drift, branch-only post-merge work, CI gate accidentally bypassed, stale branch merged wholesale, documentation claiming a green formal build for an untested commit.

Action: stop release promotion, identify the first affected commit, separate source-semantic changes from Git/CI metadata changes, reproduce the failure with the smallest independent check, repair the narrowest invariant, validate the exact production entrypoint, update the branch reconciliation record when relevant, and add a machine regression check whenever possible.

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

A discovered false accept is a research result as well as a product defect. Add a regression test/adversarial case whenever technically possible and update the trust-boundary documentation. Repository-integrity incidents follow the same rule: convert the failure mode into an automated invariant when technically possible.
