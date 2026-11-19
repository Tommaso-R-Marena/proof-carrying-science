#!/usr/bin/env bash
set -euo pipefail
root=$(git rev-parse --show-toplevel)
gate="$root/research/evolving_safety_gate_v1/formal"
mirage="$root/research/assurance_mirage_v1/formal"
test "$#" -eq 1 || { echo "usage: $0 NEW_OUTPUT_DIRECTORY" >&2; exit 2; }
mkdir -- "$1"
out=$(cd -- "$1" && pwd)
export LEAN_PATH="$out"
cd "$out"
lean --version | tee lean-version.txt
grep -Fq 'version 4.28.0,' lean-version.txt
for src in "$mirage"/{AssuranceMirage,ObservationAdequacy}.lean "$gate"/{EvolvingSafetyGate,PromotionReplay,CheckLineage}.lean; do
  file=$(basename "$src")
  cp -- "$src" "$file"
  lean -DwarningAsError=true -o "${file%.lean}.olean" "$file" >"${file%.lean}.log"
done
sha256sum *.lean > sources.sha256
for module in ObservationAdequacy PromotionReplay; do
  python3 - "$module" <<'PY'
import pathlib, re, sys
name = sys.argv[1]
source = pathlib.Path(name + ".lean").read_text()
audit = pathlib.Path(name + ".log").read_text()
theorems = set(re.findall(r"^theorem (\w+)", source, re.M))
records = re.findall(r"^'" + name + r"\.(\w+)' (?:does not depend on any axioms|depends on axioms: \[([^\]]+)\])$", audit, re.M)
if {decl for decl, _ in records} != theorems or not records:
    sys.exit("missing or unexpected theorem closure")
for decl, closure in records:
    if closure and set(closure.split(", ")) - {"propext", "Quot.sound"}:
        sys.exit("unexpected dependency for " + decl)
PY
done
fixtures="$gate/lineage_fixture"
check() { lean --run CheckLineage.lean "$1" "$2"; }
check "$fixtures/review.txt" "$fixtures/offers.txt" | tee verdict.txt
grep -Fxq 'accepted champion=2 generation=2 correct=2/2' verdict.txt
reject() {
  local expected="$1"
  shift
  local rc=0
  check "$@" > negative.log 2>&1 || rc=$?
  test "$rc" -eq 1 && grep -Fxq "$expected" negative.log
}
# Reuse of a licensed receipt after its parent changes.
cat "$fixtures"/offers.txt "$fixtures"/offers.txt > stale.offers
reject 'lineage rejected' "$fixtures/review.txt" stale.offers
# A successful candidate lacks one independent observation.
sed '/^observed 2 1 /d' "$fixtures/review.txt" > missing.review
reject 'lineage rejected' missing.review "$fixtures/offers.txt"
sed 's/^offer 9 /offer 8 /' "$fixtures/offers.txt" > old.offers
reject 'lineage rejected' "$fixtures/review.txt" old.offers
sed 's/^class 2 jointDetectingGuard/class 2 channel1Only/' "$fixtures/review.txt" > blind.review
reject 'lineage rejected' blind.review "$fixtures/offers.txt"
sed 's/^observed 2 1 0$/observed 2 1 1/' "$fixtures/review.txt" > tie.review
reject 'lineage rejected' tie.review "$fixtures/offers.txt"
cat "$fixtures/review.txt" <(echo 'observed 2 1 1') > ambiguous.review
reject 'duplicate row identity' ambiguous.review "$fixtures/offers.txt"
echo 'Six negative controls passed.'
# One fresh replay checks both proof modules and their shared imports together.
printf '%s\n' 'import ObservationAdequacy' 'import PromotionReplay' > ReviewProofs.lean
lean -o ReviewProofs.olean ReviewProofs.lean
leanchecker --fresh --verbose ReviewProofs > ReviewProofs.fresh.log 2>&1
echo 'Fresh checking completed.'
