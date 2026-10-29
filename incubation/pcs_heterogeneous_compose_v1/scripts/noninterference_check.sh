#!/usr/bin/env bash
# Fail if dirty/untracked paths exist outside this incubation package.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
OWNED="incubation/pcs_heterogeneous_compose_v1"
test -d "$ROOT/$OWNED"
cd "$ROOT"
# Allow: owned files, and the parent incubation/ directory marker when only HECK exists.
while IFS= read -r line; do
  # porcelain: XY <path>
  path="${line:3}"
  path="${path%% -> *}"
  case "$path" in
    "${OWNED}"|"${OWNED}/"*|incubation/)
      continue
      ;;
    *)
      # If the only incubation child is HECK, a bare incubation/ untracked entry is ok.
      if [[ "$path" == "incubation/" ]]; then
        continue
      fi
      echo "noninterference failure: $line" >&2
      exit 1
      ;;
  esac
done < <(git status --porcelain)
echo "noninterference ok: only ${OWNED}"
