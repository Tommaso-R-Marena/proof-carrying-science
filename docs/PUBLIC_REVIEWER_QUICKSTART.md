# PCS public verifier quickstart (pre-release draft)

**Research software, scoped assurance only. Not a certification of arbitrary scientific or AI-system safety.**

## Reproduce verification from a pinned source checkout

The reference repository has a pinned Lean toolchain in `lean-toolchain` and `formal/lean-toolchain`. Reviewers should record the commit and retain complete build logs and environment metadata. Do not treat a theorem statement, a CI badge, or a reported Aristotle run as interchangeable evidence.

```bash
git rev-parse HEAD
python3 --version
python3 -m pip install -e '.[dev]'
python3 scripts/check_repository_integrity.py
bash scripts/verify_lean.sh
cd formal && bash tools/run_fixture_tests.sh && cd ..
python3 -m pytest -q
python3 scripts/adversarial_campaign.py
python3 scripts/adversarial_v06_hardening.py
```

For the integrated release candidate with all source and binary audits, use `bash scripts/core_ci_cloudflare.sh` on a trustworthy Linux environment. That script installs missing tools and checks source identity; review what it downloads before executing untrusted code. The commands above are a readable breakdown, not an assertion that the latest unmerged PR has passed.

## Interpreting the result

- A successful Lean kernel build checks the included proof terms against their formal declarations. It does **not** show that assumptions match the external world.
- The compiled verifier and ZIP/directory golden and adversarial campaigns establish observed executable behavior in tested environments, not arbitrary-program correctness.
- Signed artifacts bind exact bytes to a signer identity only under trusted key/fingerprint assumptions.
- An external scientific reviewer must select acceptance policies and validate domain appropriateness and assumptions independently.
- The PR #74 fail-closed source integration and AI-safety guarantee cannot be described as in `main` until it is merged under executed exact-revision gates.
- A CI no-op or skipped workflow is **not** evidence of execution.

See `LIMITATIONS.md` when present in evidence bundles, `docs/LEAN_KERNEL_STATUS.md`, `docs/PUBLIC_RELEASE_GATE.md`, and `SECURITY.md`.

## Scientific users and contributors

Start with synthetic/public-domain examples. Do not commit private datasets, unpublished constituent projects, actual patient identifiers or signing keys. File separate issues for bugs, missing adapters and evaluation gaps; follow `SECURITY.md` for vulnerability reports. Contributor level or game leaderboard position confers no Lean authority.
