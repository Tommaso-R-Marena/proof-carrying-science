# PCS public-core and contributor charter

**License selection — founder policy, 2026-10-08:** Apache License 2.0 is the intended release license for the genuinely open verification foundation. This is a policy decision; no assertion is made that confidential history or third-party material has passed the disclosure gate.

## 1. What belongs to the open standard

The public reference core should include:
- signed evidence/certificate byte formats, canonicalization, package schemas, and validation rules;
- the independently usable reference verifier, CLI, and its executable authority;
- Lean 4 proof sources, verified assumptions, axiom audits, deterministic fixtures, and a reproducible toolchain;
- core Claim IR and proof-obligation specifications, plus interoperability formats;
- adversarial/conformance tests, public-compatible replay examples, release-gate scripts, and audit evidence;
- documentation that accurately distinguishes established proofs from external trust assumptions and empirical scientific claims.

All public Apache-2.0 material may be used and redistributed commercially by third parties under that license. No public page or paid offering may imply that a license-free verification result can be independently checked only with a PCS subscription.

## 2. Commercial and separately licensed work

Subject to ownership/third-party rights, revenue may come from hosted compute, managed deployments, enterprise access controls, SLA/support, custom adapters, regulated process documentation, and separately authored commercial domain products. Separate code must live behind an explicit **file/repository/license boundary**; merely listing an item in a roadmap does not exempt previously Apache-2.0-distributed code.

PCS must not downgrade reproducible scientific truth, safety-critical verification or public certificate checking in order to force payments. Third-party commercial adoption of Apache-2.0 public code is permitted.

## 3. Contributors and technical authority

PCS proposes DCO v1.1 signed-off commits (`git commit -s`) for new open-source contributions, not blanket assignment of contributor copyrights. The DCO confirms a contributor's claimed right to submit code under the applicable project license; it does not independently establish university, employer, collaborator or dataset ownership.

Contributors may use AI assistants with disclosure where required. Acceptance into public GitHub `main` depends on independently executed exact-source CI, sound checker semantics, signed byte-contracts and review appropriate to risk—not a badge, user level, number of tasks or commercial payment. No single automatic score or game leaderboard may confer Lean proof authority.

## 4. Website and data separation

The public core repository and website repository are distinct. Publicly accessible source code does **not** make production Cloudflare Worker secrets, D1 database rows, account sessions, private research submissions, contributor training records, draft task solutions or admin interfaces public.

The website can openly link to public verifier/proof source, specs and issues **without** allowing unauthenticated access to private user data, unreleased submissions or reviewer authorization. The website source may stay private under its own rights/security decision; users can still inspect the public PCS core on GitHub.

Training-data collection from contributors requires transparent consent, provenance and use constraints. Public GitHub contributions do not automatically authorize redistribution of private PCS Arena user data.

## 5. Security and research honesty

- Reject all unregistered executable checker types; never substitute signed provenance for semantic correctness.
- Publish precise scope, kernel assumptions, test limitations, false-accept disclosures and reproducibility instructions.
- No credential or production account access in untrusted GitHub Actions or Cloudflare PR builds.
- A release is not approved unless the documented license/rights, full-history disclosure, secret isolation and full CI gates pass for the exact revision.
- Apache-2.0 does not grant permission to impersonate the PCS project, claim certification, or violate applicable trademark law.

## 6. Release status

As of this charter's drafting date the existing core repository remains private. A founder declaration of original IP ownership is on record, but the complete history, upstream third-party asset rights, and privileged-CI isolation require separate verification. Public conversion must be an explicit release event with a dated evidence manifest.

See `LICENSE`, `NOTICE`, `SECURITY.md`, `CONTRIBUTING.md`, `docs/PUBLIC_RELEASE_EXECUTION_2026-10-08.md` and `docs/PUBLIC_RELEASE_RIGHTS_LEDGER.md`.
