#!/usr/bin/env bash
# Ensure all staged/committed changes for this agent stay inside the isolation namespace.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$ROOT" && git rev-parse --show-toplevel)"
NS="incubation/pcs_conservation_algebra_v1"
FORBIDDEN_NS=(
  "incubation/pcs_next_v1"
  "incubation/pcs_certified_numerics_v1"
  "pcs/"
  "formal/PCS"
  "formal/real"
  "site/"
)

cd "$REPO"

echo "== Noninterference check =="
echo "repo=$REPO"
echo "allowed_prefix=$NS"

BASE=$(git merge-base HEAD origin/main 2>/dev/null || git merge-base HEAD main)
CHANGED=$(git diff --name-status "$BASE"...HEAD || true)
STAGED=$(git diff --cached --name-status || true)
UNSTAGED=$(git diff --name-status || true)

check_paths() {
  local label="$1"
  local data="$2"
  [[ -z "${data:-}" ]] && return 0
  while IFS=$'\t' read -r status path rest; do
    [[ -z "${path:-}" ]] && continue
    local paths=("$path")
    if [[ "$status" == R* ]]; then
      paths=("$path" "$rest")
    fi
    for p in "${paths[@]}"; do
      for forb in "${FORBIDDEN_NS[@]}"; do
        if [[ "$p" == "$forb"* ]]; then
          echo "FAIL($label): touches forbidden $p"; exit 1
        fi
      done
      if [[ "$p" != "$NS"* ]]; then
        echo "FAIL($label): path outside namespace: $p"; exit 1
      fi
    done
  done <<< "$data"
}

if [[ -n "$CHANGED" ]]; then check_paths committed "$CHANGED"; fi
if [[ -n "$STAGED" ]]; then check_paths staged "$STAGED"; fi
if [[ -n "$UNSTAGED" ]]; then check_paths unstaged "$UNSTAGED"; fi

if find "$ROOT" -type l | grep -q .; then
  echo "WARN: symlinks present; auditing targets"
  while read -r link; do
    target=$(readlink -f "$link")
    case "$target" in
      "$ROOT"*) ;;
      *) echo "FAIL: symlink escapes namespace: $link -> $target"; exit 1 ;;
    esac
  done < <(find "$ROOT" -type l)
fi

if git diff "$BASE"...HEAD 2>/dev/null | grep -Eiq 'BEGIN (RSA |OPENSSH )?PRIVATE KEY|aws_secret_access_key|ghp_[A-Za-z0-9]{20,}'; then
  echo "FAIL: potential secret in diff"; exit 1
fi

echo "remote: $(git remote get-url origin)"
echo "branch: $(git rev-parse --abbrev-ref HEAD)"
echo "OK: all changes confined to $NS"
