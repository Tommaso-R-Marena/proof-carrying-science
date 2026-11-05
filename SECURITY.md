# Security policy

PCS is an experimental scientific assurance system, not a medical device, regulatory validation, or proof of arbitrary AI safety.

## Private vulnerability reports

Please report security vulnerabilities **privately** by emailing **marenatommaso@gmail.com** with subject `PCS security report`. Do **not** open a public GitHub issue containing exploit details, credentials, unpublished partner data, or active vulnerabilities.

Helpful details: affected revision/commit, affected package/CLI/checker, bounded reproducer using synthetic data, plausible security impact, and contact information. Never send real private signing keys, patient data, or production credentials.

The project will acknowledge reports as capacity permits; it does not currently promise a contractual response time, bounty, or coordinated disclosure date. Reporters and maintainers should agree on a safe disclosure timeline if a finding is confirmed.

## Supported status

The repository is **pre-release research software**. Security fixes are tracked by exact commit and reproducible evidence, not by an unverified “latest version.” The scope of proof is explicitly limited by documented assumptions and trust boundaries.

## Response

On a credible false-accept, checker-binding, supply-chain, or key compromise:
1. Stop promotion or release of affected attestations.
2. Preserve minimal incident evidence privately.
3. Determine affected artifacts, signers, and versions.
4. Repair the defect and create regression/adversarial tests.
5. Re-run the exact-source Lean/executable/Python gate.
6. Publish an advisory and rotate/revoke compromised keys when appropriate, without leaking credentials.

See `docs/RELEASE_AND_INCIDENT_RESPONSE.md` and `docs/PUBLIC_RELEASE_GATE.md`. Do not attach sensitive reproducer data to public CI or GitHub issues.
