#!/usr/bin/env bash
# Operational regression test of the compiled `pcs-semantic-check` binary on the committed
# PCS Proof-Carrying Semantic Intelligence v2 fixtures
# (fixtures/semantic_intelligence_v2/expected.json):
#   * `--v2` on every request: outcome, exit code (0 certified / 3 verified counterexample /
#     1 otherwise), required diagnostic codes and feedback label;
#   * `--check-countermodel` on every countermodel bundle: expected validity and exit code.
# This tests the compiled program.  The pure functions it runs are the ones proved correct in
# PCS/V2/TranslationV2Json.lean, and the fixture writer checked the same outcomes on them.
# Usage (from the project root, after `lake build`):
#   bash tools/run_semantic_v2_fixture_tests.sh
set -u
BIN=.lake/build/bin/pcs-semantic-check
DIR=fixtures/semantic_intelligence_v2
fail=0; n=0
while IFS='|' read -r name req outcome codes label; do
  n=$((n+1))
  out=$($BIN --v2 "$DIR/authority.json" "$DIR/$req"); rc=$?
  got=$(printf '%s' "$out" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["outcome"]); print(" ".join(x["code"] for x in d["diagnostics"])); print(d["label"])')
  go=$(printf '%s\n' "$got" | sed -n 1p); gc=$(printf '%s\n' "$got" | sed -n 2p); gl=$(printf '%s\n' "$got" | sed -n 3p)
  ok=1
  [ "$go" = "$outcome" ] || ok=0
  [ "$gl" = "$label" ] || ok=0
  case "$outcome" in
    CERTIFIED_TRANSLATION) [ $rc -eq 0 ] || ok=0;;
    VERIFIED_COUNTEREXAMPLE) [ $rc -eq 3 ] || ok=0;;
    *) [ $rc -eq 1 ] || ok=0;;
  esac
  for c in $codes; do case " $gc " in *" $c "*) ;; *) ok=0;; esac; done
  if [ $ok = 1 ]; then echo "ok   $name $go rc=$rc"; else echo "FAIL $name got '$go' [$gc] label=$gl rc=$rc expected '$outcome' [$codes] $label"; fail=1; fi
done < <(python3 -c '
import json
for f in json.load(open("fixtures/semantic_intelligence_v2/expected.json"))["fixtures"]:
    print("|".join([f["name"], f["request"], f["outcome"], " ".join(f["codes"]), f["label"]]))')
while IFS='|' read -r name bundle valid; do
  n=$((n+1))
  out=$($BIN --check-countermodel "$DIR/authority.json" "$DIR/$bundle"); rc=$?
  if [ "$valid" = True ]; then exp=VALID_COUNTERMODEL; erc=0; else exp=INVALID_COUNTERMODEL; erc=1; fi
  case "$out" in "$exp"*) ok=1;; *) ok=0;; esac
  [ $rc -eq $erc ] || ok=0
  if [ $ok = 1 ]; then echo "ok   $name $out"; else echo "FAIL $name got '$out' rc=$rc expected $exp"; fail=1; fi
done < <(python3 -c '
import json
for f in json.load(open("fixtures/semantic_intelligence_v2/expected.json"))["countermodels"]:
    print("|".join([f["name"], f["bundle"], str(f["valid"])]))')
echo "semantic v2 fixtures: $n checked, failures=$fail"
exit $fail
