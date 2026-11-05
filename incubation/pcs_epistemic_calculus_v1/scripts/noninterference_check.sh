#!/usr/bin/env bash
# Fail if this incubation tree touches production PCS surfaces.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$ROOT/../.." && pwd)"
cd "$REPO"

# Only incubation path for this workstream may appear as a new tracked change
# relative to main, aside from lake/python caches which must stay untracked.
mapfile -t dirty < <(git status --porcelain | awk '{print $NF}')
for path in "${dirty[@]:-}"; do
  [[ -z "${path:-}" ]] && continue
  case "$path" in
    incubation|incubation/|incubation/pcs_epistemic_calculus_v1|incubation/pcs_epistemic_calculus_v1/*|incubation/pcs_epistemic_calculus_v1/)
      # New incubation root is expected on this branch.
      ;;
    *)
      echo "NONINTERFERENCE FAIL: unexpected dirty path: $path" >&2
      exit 1
      ;;
  esac
done

# Hard ban: never modify these production / peer-incubation roots from this branch tip.
forbidden=(
  pcs/
  formal/PCS
  formal/real
  docs/PCS_
  .github/
  independent_eval/
  incubation/pcs_next_v1/
  incubation/pcs_certified_numerics_v1/
)
for pattern in "${forbidden[@]}"; do
  if git diff --name-only origin/main...HEAD 2>/dev/null | grep -E "^${pattern}" >/dev/null; then
    echo "NONINTERFERENCE FAIL: diff touches forbidden prefix: $pattern" >&2
    git diff --name-only origin/main...HEAD | grep -E "^${pattern}" >&2 || true
    exit 1
  fi
done

echo "NONINTERFERENCE OK: only incubation/pcs_epistemic_calculus_v1/"
