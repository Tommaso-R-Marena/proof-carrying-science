#!/usr/bin/env bash
# Ensure all staged/committed changes for this agent stay inside the isolation namespace.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$ROOT" && git rev-parse --show-toplevel)"
NS="incubation/pcs_certified_numerics_v1"
FORBIDDEN_NS="incubation/pcs_next_v1"

cd "$REPO"

echo "== Noninterference check =="
echo "repo=$REPO"
echo "allowed_prefix=$NS"

# Diff against merge-base with origin/main
BASE=$(git merge-base HEAD origin/main 2>/dev/null || git merge-base HEAD main)
CHANGED=$(git diff --name-status "$BASE"...HEAD)
STAGED=$(git diff --cached --name-status || true)
UNSTAGED=$(git diff --name-status || true)

check_paths() {
  local label="$1"
  local data="$2"
  while IFS=$'\t' read -r status path rest; do
    [[ -z "${path:-}" ]] && continue
    # handle renames: status R100, path old, rest new
    if [[ "$status" == R* ]]; then
      for p in "$path" "$rest"; do
        if [[ "$p" == "$FORBIDDEN_NS"* ]]; then
          echo "FAIL($label): touches forbidden $p"; exit 1
        fi
        if [[ "$p" != "$NS"* ]]; then
          echo "FAIL($label): path outside namespace: $p"; exit 1
        fi
      done
    else
      if [[ "$path" == "$FORBIDDEN_NS"* ]]; then
        echo "FAIL($label): touches forbidden $path"; exit 1
      fi
      if [[ "$path" != "$NS"* ]]; then
        echo "FAIL($label): path outside namespace: $path"; exit 1
      fi
    fi
  done <<< "$data"
}

if [[ -n "$CHANGED" ]]; then check_paths committed "$CHANGED"; fi
if [[ -n "$STAGED" ]]; then check_paths staged "$STAGED"; fi
if [[ -n "$UNSTAGED" ]]; then check_paths unstaged "$UNSTAGED"; fi

# Refuse symlink escapes in namespace
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

# Secrets heuristic
if git diff "$BASE"...HEAD | grep -Eiq 'BEGIN (RSA |OPENSSH )?PRIVATE KEY|aws_secret_access_key|ghp_[A-Za-z0-9]{20,}'; then
  echo "FAIL: potential secret in diff"; exit 1
fi

echo "remote: $(git remote get-url origin)"
echo "branch: $(git rev-parse --abbrev-ref HEAD)"
echo "OK: all changes confined to $NS"
