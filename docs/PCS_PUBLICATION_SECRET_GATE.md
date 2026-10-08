# PCS: Gate before making this repository public

**Status:** PREPARATION ONLY. No history has been certified clean, no credentials have been rotated by this change, and this branch must NOT be interpreted as approval to publish.

## Required order

1. Keep both PCS repositories private. Freeze pushes during the final audit; inventory the default branch, every remote branch and tag, PR head refs, Actions logs/artifacts, releases, Git LFS, and any connected service credentials.
2. Make independent full Git clones for analysis; run `bash scripts/scan_before_public.sh` with current Gitleaks v8 in **each** repository. The script fetches remote refs and PR heads, scans Git patches and the worktree, and blocks publication on any findings *or errors*. Scanner output is intentionally not committed. Do not rely on scanner output alone: manually review configuration, historical diffs, sample datasets, and admin email/privacy content.
3. Investigate each finding privately without posting secret bytes in issues or PRs. Revoke and rotate any real compromised token/key FIRST, including Cloudflare, GitHub, email sender, OAuth, signing material, or runtime credentials as applicable. Confirm all dependent services use the replacements. Rewriting Git does not revoke credentials.
4. If sensitive committed bytes are found, first make verified offline backups and identify all affected paths/versions and refs. Use an isolated checkout with `git-filter-repo --sensitive-data-removal` and its `--replace-text` or `--invert-paths --path` options as appropriate. Do **not** mass-delete source or force-push a guessed rewrite. Review changed PR refs, tags, release artifacts, commit signatures and dependent branch conflicts. Coordinate rebases (never merge tainted ancestors back in).
5. If necessary, work with GitHub Support to remove cached objects and stale pull-request references. A force push alone cannot guarantee erasure from other clones or forks. Re-run independent history and worktree scans from a fresh clone, and separately inspect Actions logs/artifacts, issues, PR comments, secrets versus variables, and Cloudflare configuration.
6. Confirm public CI never grants production credentials to untrusted code. Review `pull_request_target`, write permissions, environment approvals, Actions artifacts, branch protections/rulesets, and deployment triggers. Retest the combined PCS PR stack with credential-free workflows.
7. Only after documented sign-off: change repository visibility and rerun read-only security checks as a public repository. Make the public visibility change manually through repository Settings, after reviewing GitHub's visibility change warnings. No script here changes visibility.

## About this branch

The added `.gitignore` patterns only prevent **future untracked** local secrets from being committed. They do not remove a file from past commits, PRs, tags, CI logs, or clones. The scripts do not remove secrets or assert the repository is clean. Avoid storing scanner results in the repository or sharing real secret values with an AI coding assistant.

Reference: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository
