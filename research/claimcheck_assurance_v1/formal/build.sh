#!/usr/bin/env bash
# Compile the reviewed ClaimCheck checker and the assurance modules with plain Lean 4.28.0 (no lake,
# no Mathlib, no network).  Every module is checked by the Lean kernel; .olean files go to $OUT.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../../.." && pwd)"
OUT="${PCS_ASSURANCE_BUILD:-$here/.build}"
mkdir -p "$OUT/ClaimCheckAssurance"
lean --version | grep -q 'version 4.28.0' || { echo "Lean 4.28.0 is required" >&2; exit 2; }
sha256sum --check --status <(echo "$(cut -d' ' -f1 "$root/research/claimcheck_v1/formal/ClaimCheck.lean.sha256")  $root/research/claimcheck_v1/formal/ClaimCheck.lean")
export LEAN_PATH="$OUT"
(cd "$root/research/claimcheck_v1/formal" && lean -o "$OUT/ClaimCheck.olean" ClaimCheck.lean)
for m in ${PCS_ASSURANCE_MODULES:-SourceBinding Authority Selection Audit}; do
  [ -f "$here/ClaimCheckAssurance/$m.lean" ] || continue
  (cd "$here" && lean -o "$OUT/ClaimCheckAssurance/$m.olean" "ClaimCheckAssurance/$m.lean")
done
echo "CLAIMCHECK_ASSURANCE_BUILD_OK"
