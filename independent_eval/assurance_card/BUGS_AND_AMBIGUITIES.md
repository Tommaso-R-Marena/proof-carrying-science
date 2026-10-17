# Bugs and ambiguities — Workstream F

## Design ambiguities (documented, not silent)

1. **Fixture vs real attest package.** The sample bundle uses
   `pcs-assurance-card-fixture-certificate-v1`. Authority-lane `pcs verify` on
   this fixture will typically fail schema/attest checks. Tests that need a
   defined authority outcome monkeypatch the runner; production use should point
   `--evidence` at a real certify output (see pkpd demo test).
2. **Receipt overrides certificate status.** When a verification-receipt is
   present, reported claim decisions from the receipt replace certificate
   assessment statuses before classification. This matches reviewer expectation
   that the latest reported decision is what humans see, but it is still
   non-authority.
3. **Scientific claims with COMPUTATIONALLY_SUPPORTED status.** Lattice maps
   these to `scientific_adequacy_open` (not a separate empirically_unsupported
   class). Computational labels never elevate scientific adequacy.
4. **`pcs` binary vs module.** Resolution prefers `pcs` on PATH, else
   `python -m pcs.cli`. Different environments may produce different argv
   strings; both are recorded.
5. **Git HEAD provenance.** If `.git` is absent (exported tarball), `git_head`
   is `null`. Card generation still succeeds.

## Observed hazards

- Treating `lane_consistency.overall == agreement` as scientific acceptance —
  **incorrect**. Agreement only means inspection classes do not contradict the
  authority-lane verify outcome.
- Treating receipt `lean_authority.reported_result: ACCEPT` as card-issued
  ACCEPT — **incorrect**. Inspection copies reported fields only;
  `card_issues_accept` remains false.
- Running with network-enabled wrappers or Lean rebuild scripts — out of scope;
  this harness deliberately calls verify only.

## Non-claims reminder

No clinical validity, no external lab completion, no security proof, no merge
recommendation.
