#!/usr/bin/env bash
# Source this file. The download hash is the official Lean 4.28.0 release digest.
set -euo pipefail
if command -v lean >/dev/null 2>&1 && lean --version 2>/dev/null | grep -q 'version 4.28.0'; then
  return 0 2>/dev/null || exit 0
fi
test "$(uname -s)" = Linux && test "$(uname -m)" = x86_64
pcs_lean_stage="$(mktemp -d "${RUNNER_TEMP:-${TMPDIR:-/tmp}}/pcs-lean-428.XXXXXX")"
curl --fail --location --retry 3 --output "$pcs_lean_stage/lean.tar.zst" \
  https://github.com/leanprover/lean4/releases/download/v4.28.0/lean-4.28.0-linux.tar.zst
echo "ceb3a3f844f7aebf63245e2b51c28d5b0ed38942c19f93cf3febd520302160bd  $pcs_lean_stage/lean.tar.zst" | sha256sum --check --status
tar --zstd -xf "$pcs_lean_stage/lean.tar.zst" -C "$pcs_lean_stage"
rm "$pcs_lean_stage/lean.tar.zst"
export PATH="$pcs_lean_stage/lean-4.28.0-linux/bin:$PATH"
lean --version | grep 'version 4.28.0'
