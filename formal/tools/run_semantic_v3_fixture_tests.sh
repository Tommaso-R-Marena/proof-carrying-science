#!/usr/bin/env bash
# Operational regression test of `pcs-semantic-check --v3` (stateful receipt authority) on the
# committed fixtures (fixtures/semantic_authority_v3/expected.json):
#   outcome, exit code (0 certified / 3 verified counterexample / 1 otherwise), receipt-phase
#   status (VALID / INVALID / NOT_REACHED) and failure reason, and that nothing is consumed
#   unless the outcome is CERTIFIED_TRANSLATION.
# This tests the compiled program.  The pure function it runs (`semanticCheckV3`) is proved in
# PCS/V2/TranslationV3Json.lean; tools/CheckSemanticV3Fixtures.lean evaluates the same fixtures
# on that pure function.
# Usage (from the project root, after `lake build`):  bash tools/run_semantic_v3_fixture_tests.sh
set -u
BIN=.lake/build/bin/pcs-semantic-check
DIR=fixtures/semantic_authority_v3
fail=0; n=0
while IFS='|' read -r name auth req st outcome status reason; do
  n=$((n+1))
  out=$($BIN --v3 "$DIR/$auth" "$DIR/$req" "$DIR/$st"); rc=$?
  got=$(printf '%s' "$out" | python3 -c '
import json,sys
d=json.load(sys.stdin)
rp=d["receipt_phase"]
reason=""
if rp["status"]=="INVALID":
    f=rp["failure"]; reason=f.get("reason", f["kind"])
print(d["outcome"]); print(rp["status"]); print(reason); print(len(d["consumed_nonces"]))')
  go=$(printf '%s\n' "$got" | sed -n 1p); gs=$(printf '%s\n' "$got" | sed -n 2p)
  gr=$(printf '%s\n' "$got" | sed -n 3p); gn=$(printf '%s\n' "$got" | sed -n 4p)
  ok=1
  [ "$go" = "$outcome" ] || ok=0
  [ "$gs" = "$status" ] || ok=0
  [ "$gr" = "$reason" ] || ok=0
  case "$outcome" in
    CERTIFIED_TRANSLATION) [ $rc -eq 0 ] || ok=0; [ "$gn" != 0 ] || ok=0;;
    VERIFIED_COUNTEREXAMPLE) [ $rc -eq 3 ] || ok=0; [ "$gn" = 0 ] || ok=0;;
    *) [ $rc -eq 1 ] || ok=0; [ "$gn" = 0 ] || ok=0;;
  esac
  if [ $ok = 1 ]; then echo "ok   $name $go $gs $gr rc=$rc"; else echo "FAIL $name got '$go' $gs '$gr' rc=$rc consumed=$gn; expected '$outcome' $status '$reason'"; fail=1; fi
done < <(python3 -c '
import json
for f in json.load(open("fixtures/semantic_authority_v3/expected.json"))["fixtures"]:
    print("|".join([f["name"], f["authority"], f["request"], f["state"], f["outcome"], f["receipt_status"], f["reason"]]))')
echo "semantic v3 fixtures: $n checked, failures=$fail"
exit $fail
