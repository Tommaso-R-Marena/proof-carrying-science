# Hosted contribution verification

Public core `verified-public-integration` is the strict required GitHub Actions
aggregate. It actually builds Lean authorities and Mathlib, checks imported
Aristotle sources, executes Python/adversarial/byte-contract/portability suites,
replays the pinned CertiForge checker and trains/evaluates/checks Omega examples.
The successful exact main run 37899732877 establishes replacement coverage;
Cloudflare Builds is not required for that assurance.

Dedicated `pcs-submission.yml` and `pcs-promotion.yml` previously listened only
for PRs while requiring a non-PR private-runner event. They now use disposable
hosted runners for public owner repositories without production secrets or
persisted checkout credentials. Existing job/step identities are preserved for
the Commons backend. Core dependencies use hash-locked requirements. Actual Lean
contribution elaboration and production kernel/regression checks remain intact.

The required source-policy job additionally executes
`scripts/check_pr_contributions.py` on PRs. Changed archive or promotion paths
run the actual digest/exact-diff validators against the exact event base SHA.
Deleting an archive does not skip the checker. Seven real temporary-history
tests cover valid cases, tampering, unexpected mapped-file changes, deletion and
invalid repository/baseline metadata. File-provenance validation grants no
scientific authority.

The legacy `pcs-core-ci-only` and `pcs-core-ci-gate` Cloudflare Git integrations
should be disconnected after protected replacement verification. Website
hosting, D1 and Worker bindings remain separate. Provider readback is needed to
close issue #75; a failed administration request or source edit alone does not
prove trigger retirement or credential revocation. Historical failed checks
must not be relabeled successful.
