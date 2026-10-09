#!/usr/bin/env bash
# Operational regression test of the compiled `pcs-semantic-check` binary on the committed
# PCS Semantic Translation Contract v1 fixtures (fixtures/semantic_translation_v1/expected.json).
# This tests the compiled program; the same verdicts are kernel-checked for the pure checker in
# PCS/V2/TranslationFixtures.lean.  Usage (from the project root, after `lake build`):
#   bash tools/run_semantic_fixture_tests.sh
set -u
BIN=.lake/build/bin/pcs-semantic-check
DIR=fixtures/semantic_translation_v1
fail=0
while IFS=$'\t' read -r name auth req verdict codes; do
  out=$($BIN "$DIR/$auth" "$DIR/$req"); rc=$?
  got=$(printf '%s' "$out" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["verdict"]); print(" ".join(x["code"] for x in d["diagnostics"]))')
  gv=$(printf '%s\n' "$got" | sed -n 1p); gc=$(printf '%s\n' "$got" | sed -n 2p)
  ok=1
  [ "$gv" = "$verdict" ] || ok=0
  if [ "$verdict" = ACCEPTED ]; then [ $rc -eq 0 ] || ok=0; else [ $rc -eq 1 ] || ok=0; fi
  for c in $codes; do case " $gc " in *" $c "*) ;; *) ok=0;; esac; done
  if [ $ok = 1 ]; then echo "ok   $name $gv"; else echo "FAIL $name got '$gv' [$gc] rc=$rc expected '$verdict' [$codes]"; fail=1; fi
done < <(python3 -c '
import json
for f in json.load(open("fixtures/semantic_translation_v1/expected.json"))["fixtures"]:
    print("\t".join([f["name"], f["authority"], f["request"], f["verdict"], " ".join(f["codes"])]))')
exit $fail
