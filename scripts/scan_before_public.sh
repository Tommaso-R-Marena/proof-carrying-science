#!/usr/bin/env bash
# Read-only prepublication check. Run in a FULL Git checkout with gitleaks v8.
# Do not publish this script's reports. Findings require human review.
set -euo pipefail
umask 077
command -v git >/dev/null || { echo "git is required" >&2; exit 2; }
command -v gitleaks >/dev/null || { echo "gitleaks v8 is required" >&2; exit 2; }
root="$(git rev-parse --show-toplevel)"
cd "$root"
[ "$(git rev-parse --is-shallow-repository)" = "false" ] || { echo "Refusing shallow clone" >&2; exit 2; }
# Fetch tracked remote branches, tags, and GitHub PR heads before scanning.
git fetch --all --tags --prune
git fetch origin '+refs/pull/*/head:refs/remotes/origin/security-scan-pr/*'
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
status=0
# Both scans are required: historical Git patches and current filesystem.
gitleaks git --source . --log-opts='--all' --redact --report-format json --report-path "$tmp/history.json" >"$tmp/history.log" 2>&1 || status=1
gitleaks dir --source . --redact --report-format json --report-path "$tmp/worktree.json" >"$tmp/worktree.log" 2>&1 || status=1
if [ "$status" -ne 0 ]; then
  echo "SECURITY_GATE_BLOCKED: scanner reported findings or an error; inspect private, redacted logs and records." >&2
  echo "Rerun manually with reports saved securely outside Git. Rotate/revoke confirmed credentials before any history rewrite." >&2
  exit 1
fi
echo "Prepublication gitleaks scans reported no findings on locally fetched refs and current files."
echo "NOT clearance for publication: audit Actions logs/artifacts, issues, PRs, inaccessible refs, LFS, and embedded secrets separately."
