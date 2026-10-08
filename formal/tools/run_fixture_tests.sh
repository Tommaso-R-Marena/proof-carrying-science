#!/usr/bin/env bash
# Operational regression test of the compiled `pcs-lean-authority` binary on the committed
# fixtures, in both modes.  This is a test of the compiled program, not a proof; the verdicts
# are kernel-checked for the pure decision functions (see PCS_FAIL_CLOSED_REPORT.md).
# Usage (from the project root, after `lake build`): bash tools/run_fixture_tests.sh
set -u
BIN=.lake/build/bin/pcs-lean-authority
fail=0
check() { # name mode expected
  local d=fixtures/$1 out
  if [ "$2" = zip ]; then
    out=$($BIN --zip "$d/archive.zip" "$(cat "$d/pk.b64")" "$d/observations.json" "$(cat "$d/fingerprint.hex")")
  else
    out=$($BIN "$d/package" "$(cat "$d/pk.b64")" "$d/observations.json" "$(cat "$d/fingerprint.hex")")
  fi
  if [ "$out" = "$3" ]; then echo "ok   $1 [$2] $out"; else echo "FAIL $1 [$2] got '$out' expected '$3'"; fail=1; fi
}
check ai_safety_golden zip ACCEPT
check ai_safety_golden dir ACCEPT
check ai_safety_tampered zip REJECT:package
check ai_safety_insider zip REJECT:replay
check ai_safety_counterexample zip REJECT:unsupported_check_type
check ai_safety_counterexample dir REJECT:unsupported_check_type
check failclosed_unknown_type_safe_trace zip REJECT:unsupported_check_type
check failclosed_unknown_type_safe_trace dir REJECT:unsupported_check_type
check failclosed_missing_type zip REJECT:unsupported_check_type
check failclosed_missing_type dir REJECT:unsupported_check_type
check failclosed_unrequired_unknown_evidence zip REJECT:unsupported_check_type
check failclosed_unrequired_unknown_evidence dir REJECT:unsupported_check_type
check failclosed_claim_binding_mismatch zip REJECT:claim_binding
check failclosed_claim_binding_mismatch dir REJECT:claim_binding
exit $fail
