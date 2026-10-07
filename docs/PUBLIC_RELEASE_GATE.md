# PCS public-release decision gate

**Status: HOLD / NOT APPROVED.** The repo is intentionally private pre-publication. Public visibility cannot be treated as a temporary CI workaround.

## Founder decisions and external clearances required
- **Scientific publication/IP firewall:** Review `docs/PUBLICATION_FIREWALL.md` against all tracked files, **every reachable Git history commit**, branches, tags, PR logs and artifacts. Clear externally unpublished mechanisms, theorem statements, private research datasets and figures in constituent research projects before release. Check employment, academic institutional and collaborator IP rights.
- **License:** Repository `LICENSE` and `pyproject.toml` currently say **Apache-2.0**, which permits commercial use. That is materially different from a non-commercial/community license + paid commercial permission. Resolve licensing with counsel and contributors before public release. Existing rights already distributed under Apache-2.0 may not be retractable for those copies.
- **Secrets and disclosure:** Search *all Git history* for API keys, SSH/private keys, passwords, tokens, database exports, real customer/participant information, private email data, code-signing keys, security implementation weaknesses, credentials in Actions logs. Rotate leaked credentials **before** changing visibility; simply deleting from the latest commit is insufficient.
- **Assurance scope:** Freeze precise statement of what Lean proves, what is computationally reproduced, what remains OPEN, and trust assumptions. Run exact-source Lean kernel, Python regression, adversarial, provenance/signature and reproducibility campaigns, preferably on a second host. Have an independent reviewer compare public claims to their proofs and test receipts.
- **Governance/security:** Enable fork PR approval, least-privilege `GITHUB_TOKEN`, read-only untrusted PR workflows, no production secrets in PR jobs, no untrusted self-hosted runners, pin/check GitHub Actions supply chain, protect branches/tags and release signing, add a SECURITY.md reporting policy, a clear CONTRIBUTING.md and a published license decision.
- **Visibility consequence:** GitHub warns that switching from private to public makes code and Actions logs public, enables forks, and disables push rulesets. Audit protections and restore applicable rules immediately after a deliberate release decision.
- **Release approval:** Founder marks each clearance as done with dated audit evidence; record license/IP ownership, source commit SHA, SHA-bound CI results, initial version/release notes, and an explicit public decision.

Until all are complete: **keep the core private** and use a narrow public tutorial/sample repository or a sanitized snapshot (as a separate repository) for community onboarding if necessary. Neither action occurs automatically from this document.

Source: GitHub official docs on [repository visibility](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility) and [Actions usage](https://docs.github.com/en/actions/concepts/billing-and-usage).
