#!/usr/bin/env bash
# Noninterference audit: ensure changes stay within incubation namespace.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
# ROOT is proof-carrying-science when script is in incubation/.../scripts
LAB_PREFIX="incubation/pcs_causal_laboratory_v1/"
cd "$ROOT"

echo "=== Noninterference Audit ==="
echo "repo: $(git rev-parse --show-toplevel)"
echo "branch: $(git branch --show-current)"
echo "head: $(git rev-parse HEAD)"
echo "remote:"
git remote -v
echo
echo "status:"
git status -sb
echo
echo "changed files vs origin/main:"
mapfile -t CHANGED < <(git diff --name-only origin/main...HEAD; git diff --name-only; git ls-files --others --exclude-standard)
violations=0
for f in "${CHANGED[@]:-}"; do
  [[ -z "${f}" ]] && continue
  echo "  $f"
  case "$f" in
    ${LAB_PREFIX}*) ;;
    *)
      echo "VIOLATION: path outside isolation namespace: $f" >&2
      violations=$((violations + 1))
      ;;
  esac
done

echo
echo "symlinks under lab:"
find incubation/pcs_causal_laboratory_v1 -type l -print 2>/dev/null || true

if [[ "$violations" -gt 0 ]]; then
  echo "AUDIT FAILED: $violations violation(s)" >&2
  exit 1
fi
echo "AUDIT OK: all changes under ${LAB_PREFIX}"
