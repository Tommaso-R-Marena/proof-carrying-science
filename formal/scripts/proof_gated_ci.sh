#!/usr/bin/env bash
# Proof-gated V7 replay (includes the full V5 and V6 suites): build, forbidden-token scan, axiom audits, codec vectors, checker
# vectors and file-based PGSI1 authority tests. Run from the Lean project root.
# Writes machine-readable results to results/proof_gated_ci_results.json (override with
# PG_RESULTS=path). Exit code 0 iff every step passed.
set -uo pipefail

RESULTS=${PG_RESULTS:-results/proof_gated_ci_results.json}
mkdir -p "$(dirname "$RESULTS")"
LOGDIR=$(mktemp -d)
STEPS=()

finish() { # overall-status
  {
    echo "{"
    echo "  \"lean_toolchain\": \"$(cat lean-toolchain)\","
    echo "  \"overall\": \"$1\","
    echo "  \"steps\": ["
    local first=1
    for s in "${STEPS[@]}"; do
      if [ $first = 0 ]; then echo ","; fi
      printf '    %s' "$s"; first=0
    done
    echo ""
    echo "  ]"
    echo "}"
  } > "$RESULTS"
  echo "results written to $RESULTS"
}

record() { # name rc detail
  local detail=${3//\"/\'}
  STEPS+=("{\"step\": \"$1\", \"exit_code\": $2, \"detail\": \"$detail\"}")
}

fail() { record "$1" "$2" "$3"; echo "FAILED: $1 ($3)"; finish FAIL; exit 1; }

MODULES=(
  PCS.V2.ProofGatedSelfImprovement PCS.V2.ProofGatedSymbolic PCS.V2.ProofGatedArtifacts
  PCS.V2.ProofGatedPromotion PCS.V2.ProofGatedInference PCS.V2.ProofGatedMultilayer
  PCS.V2.ProofGatedGeneric PCS.V2.ProofGatedWide PCS.V2.ProofGatedDeep
  PCS.V2.ProofGatedCodec PCS.V2.ProofGatedV1Analysis PCS.V2.ProofGatedNetArtifacts
  PCS.V2.ProofGatedLimits PCS.V2.ProofGatedNoForget PCS.V2.ProofGatedRobust
  PCS.V2.ProofGatedStrongGate PCS.V2.ProofGatedDeepCert PCS.V2.ProofGatedStrongArtifacts
  PCS.V2.ProofGatedAudit PCS.V2.ProofGatedNoForgetAudit PCS.V2.ProofGatedStrongAudit
  PCS.V2.ProofGatedBytes PCS.V2.ProofGatedCertificate PCS.V2.ProofGatedCertCodec
  PCS.V2.ProofGatedProtocol PCS.V2.ProofGatedInterpreter PCS.V2.ProofGatedDeepCertGen
  PCS.V2.ProofGatedV6Limits PCS.V2.ProofGatedV6EndToEnd
  PCS.V2.ProofGatedSweepCert PCS.V2.ProofGatedCert7 PCS.V2.ProofGatedPolicy
  PCS.V2.ProofGatedBoundary PCS.V2.ProofGatedReceipt PCS.V2.ProofGatedRuntimeContract
  PCS.V2.ProofGatedV7EndToEnd PCS.V2.ProofGatedV7Limits
  PCS.V2.ProofGatedFullAudit
)

echo "== 1. build (${#MODULES[@]} modules)"
lake build "${MODULES[@]}" > "$LOGDIR/build.log" 2>&1
rc=$?
grep -E '^(warning|error)' "$LOGDIR/build.log" | head -n 40
warnings=$(grep -c '^warning' "$LOGDIR/build.log" || true)
[ $rc = 0 ] || fail build $rc "lake build failed"
record build 0 "${#MODULES[@]} modules built; $warnings warning(s)"

echo "== 2. forbidden tokens"
FILES=(PCS/V2/ProofGated*.lean scripts/proof_gated_vectors.lean scripts/proof_gated_checker_vectors.lean scripts/proof_gated_v6_vectors.lean scripts/proof_gated_v7_vectors.lean)
if grep -nE '\b(sorry|admit|native_decide|unsafe|implemented_by|extern)\b|^\s*axiom\b' "${FILES[@]}"; then
  fail forbidden_tokens 1 "forbidden token found"
fi
record forbidden_tokens 0 "${#FILES[@]} files scanned: no sorry/admit/native_decide/unsafe/implemented_by/extern/axiom"

echo "== 3. axiom audits"
# the full audit must list every public top-level theorem of the current sources
cp PCS/V2/ProofGatedFullAudit.lean "$LOGDIR/full_audit_committed.lean"
bash scripts/gen_full_audit.sh > /dev/null
cmp -s PCS/V2/ProofGatedFullAudit.lean "$LOGDIR/full_audit_committed.lean" || fail axiom_audit 1 "ProofGatedFullAudit.lean is stale (rerun scripts/gen_full_audit.sh)"
total=0
for f in PCS/V2/ProofGatedAudit.lean PCS/V2/ProofGatedNoForgetAudit.lean PCS/V2/ProofGatedStrongAudit.lean PCS/V2/ProofGatedFullAudit.lean; do
  out=$(lake env lean "$f" 2>&1); arc=$?
  [ $arc = 0 ] || fail axiom_audit $arc "$f did not elaborate"
  flat=$(tr -s '\n ' ' ' <<<"$out")
  n=$(grep -o "depends on axioms\|does not depend on any axioms" <<<"$flat" | wc -l)
  expected=$(grep -c '^#print axioms' "$f")
  echo "$f: $n of $expected #print axioms entries"
  [ "$n" = "$expected" ] || fail axiom_audit 1 "$f: $n results for $expected entries"
  used=$(grep -o '\[[^]]*\]' <<<"$flat" | tr -d '[] ' | tr ',' '\n' | sort -u)
  echo "axioms used: $(tr '\n' ' ' <<<"$used")"
  bad=$(grep -vxE 'propext|Classical.choice|Quot.sound' <<<"$used" || true)
  [ -z "$bad" ] || fail axiom_audit 1 "unexpected axioms in $f: $bad"
  record "axiom_audit:$f" 0 "$n declarations; axioms used: $(tr '\n' ' ' <<<"$used")"
  total=$((total + n))
done
echo "audit entries (the full audit overlaps the three focused audits): $total"

echo "== 4. codec vectors (8,450 canonical PGSI1 + negatives + PGSI2-WIDE)"
out=$(PGSI_MODE=check lake env lean scripts/proof_gated_vectors.lean 2>&1); vrc=$?
echo "$out" | tail -n 3
[ $vrc = 0 ] || fail codec_vectors $vrc "codec vectors failed"
record codec_vectors 0 "$(echo "$out" | tail -n 1)"

echo "== 5. checker vectors (interval error, no-forgetting, deep certificates, strong gate)"
out=$(CHK_MODE=check lake env lean scripts/proof_gated_checker_vectors.lean 2>&1); vrc=$?
echo "$out" | tail -n 3
[ $vrc = 0 ] || fail checker_vectors $vrc "checker vectors failed"
record checker_vectors 0 "$(echo "$out" | tail -n 1)"

echo "== 6. V6 vectors (byte artifacts, PGSC6 certificates, protocol, reference interpreter)"
out=$(V6_MODE=check lake env lean scripts/proof_gated_v6_vectors.lean 2>&1); vrc=$?
echo "$out" | tail -n 3
[ $vrc = 0 ] || fail v6_vectors $vrc "V6 vectors failed"
record v6_vectors 0 "$(echo "$out" | tail -n 1)"

echo "== 6b. V7 vectors (policy authority, PGSC7, boundary, PGSR7 receipts, sweep certificates, runtime contract)"
out=$(V7_MODE=check lake env lean scripts/proof_gated_v7_vectors.lean 2>&1); vrc=$?
echo "$out" | tail -n 2
[ $vrc = 0 ] || fail v7_vectors $vrc "V7 vectors failed"
record v7_vectors 0 "$(echo "$out" | tail -n 1)"

echo "== 7. file-based PGSI1 authority"
P=fixtures/proof_gated/pgsi1_pairs
ncli=0
run_cli() { out=$(lake env lean --run PCS/V2/ProofGatedArtifacts.lean "$@" 2>&1); rc=$?; }
expect() { # expected-rc expected-output args...
  local erc=$1 eout=$2; shift 2; run_cli "$@"
  if [ "$rc" != "$erc" ] || [ "$out" != "$eout" ]; then
    fail authority_cli 1 "$* -> rc=$rc out=$out (expected $erc $eout)"; fi
  ncli=$((ncli + 1))
}
for i in 0 1 2; do expect 0 ACCEPT "$P/accept_${i}_old.txt" "$P/accept_${i}_new.txt"; done
for i in 0 1 2; do expect 1 REJECT:invalid_artifact_or_update "$P/reject_${i}_old.txt" "$P/reject_${i}_new.txt"; done
T=$(mktemp -d)
expect 2 REJECT:read_failure "$T/missing.txt" "$P/accept_0_new.txt"
expect 2 REJECT:read_failure "$P/accept_0_old.txt" "$T"
expect 2 REJECT:bad_arity "$P/accept_0_old.txt"
expect 2 REJECT:bad_arity
: > "$T/empty.txt"
expect 1 REJECT:invalid_artifact_or_update "$P/accept_0_old.txt" "$T/empty.txt"
printf 'PGSI1|R|1|1\n' > "$T/newline.txt"
expect 1 REJECT:invalid_artifact_or_update "$P/accept_0_old.txt" "$T/newline.txt"
printf '\xef\xbb\xbfPGSI1|R|1|1' > "$T/bom.txt"
expect 1 REJECT:invalid_artifact_or_update "$P/accept_0_old.txt" "$T/bom.txt"
ln -s "$(pwd)/$P/accept_0_new.txt" "$T/link.txt"
# symlinks are followed by the reader: the decision is about the bytes read (documented boundary)
expect 0 ACCEPT "$P/accept_0_old.txt" "$T/link.txt"
rm -rf "$T"
record authority_cli 0 "$ncli file-based authority cases"

rm -rf "$LOGDIR"
echo "ALL PROOF-GATED CHECKS PASSED"
finish PASS
exit 0
