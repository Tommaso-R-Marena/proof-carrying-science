#!/usr/bin/env bash
# Re-extracts the final archive into a clean temporary directory and verifies it:
#   1. archive checksum matches dist/<name>.tar.gz.sha256;
#   2. the set of extracted files is exactly the manifest set (+ the SUMS file);
#   3. every file's SHA-256 matches PROOF_GATED_SHA256SUMS and PROOF_GATED_MANIFEST.json;
#   4. the full proof-gated CI (build from scratch, token scan, axiom audits, vectors,
#      authority tests) passes *inside the extraction*, with no build cache.
# Writes dist/ARCHIVE_VERIFICATION.json. Exit code 0 iff everything passed.
#
#   ./scripts/proof_gated_verify_archive.sh [dist/pcs_proof_gated_v7.tar.gz]
set -uo pipefail

ARCHIVE=${1:-dist/pcs_proof_gated_v7.tar.gz}
OUT=$(dirname "$ARCHIVE")/ARCHIVE_VERIFICATION.json
ROOT=$(pwd)
WORK=$(mktemp -d /tmp/pg_verify.XXXXXX)
STATUS=PASS
NOTES=()
note() { NOTES+=("$1"); echo "$1"; }
bad() { STATUS=FAIL; note "FAIL: $1"; }

echo "== 1. archive checksum"
(cd "$(dirname "$ARCHIVE")" && sha256sum -c "$(basename "$ARCHIVE").sha256") || bad "archive checksum mismatch"
ARCH_SHA=$(sha256sum "$ARCHIVE" | cut -d' ' -f1)

echo "== 2. extract into clean directory $WORK"
tar -xzf "$ARCHIVE" -C "$WORK" || bad "extraction failed"
cd "$WORK"
[ ! -e .lake ] || bad "extraction unexpectedly contains .lake"

echo "== 3. file set and hashes"
find . -type f | sed 's|^\./||' | LC_ALL=C sort > /tmp/pg_extracted.$$
{ cut -c67- PROOF_GATED_SHA256SUMS; echo PROOF_GATED_SHA256SUMS; } | LC_ALL=C sort > /tmp/pg_expected.$$
if cmp -s /tmp/pg_extracted.$$ /tmp/pg_expected.$$; then
  note "file set: $(wc -l < /tmp/pg_extracted.$$) files, identical to manifest"
else
  bad "file set differs from manifest"; diff /tmp/pg_expected.$$ /tmp/pg_extracted.$$ | head -n 20
fi
if sha256sum --quiet -c PROOF_GATED_SHA256SUMS; then
  note "sha256: all $(wc -l < PROOF_GATED_SHA256SUMS) entries of PROOF_GATED_SHA256SUMS match"
else
  bad "sha256 mismatch against PROOF_GATED_SHA256SUMS"
fi
# JSON manifest consistency: every (path, sha256) pair in the JSON appears in SUMS
grep -o '"path": "[^"]*", "bytes": [0-9]*, "sha256": "[0-9a-f]*"' PROOF_GATED_MANIFEST.json \
  | sed -E 's/"path": "([^"]*)", "bytes": ([0-9]*), "sha256": "([0-9a-f]*)"/\3  \1\t\2/' > /tmp/pg_json.$$
njson=$(wc -l < /tmp/pg_json.$$)
jbad=0
while IFS=$'\t' read -r line bytes; do
  grep -qxF "$line" PROOF_GATED_SHA256SUMS || jbad=$((jbad + 1))
  f=${line:66}
  [ "$(wc -c < "$f" | tr -d ' ')" = "$bytes" ] || jbad=$((jbad + 1))
done < /tmp/pg_json.$$
nsums=$(($(wc -l < PROOF_GATED_SHA256SUMS) - 1))
if [ "$jbad" = 0 ] && [ "$njson" = "$nsums" ]; then
  note "json manifest: $njson entries, hashes and sizes consistent"
else
  bad "json manifest inconsistent ($jbad mismatches, $njson entries vs $nsums)"
fi
rm -f /tmp/pg_extracted.$$ /tmp/pg_expected.$$ /tmp/pg_json.$$

echo "== 4. clean build + full CI inside the extraction"
start=$(date +%s)
PG_RESULTS="$WORK/ci_results.json" bash ./scripts/proof_gated_ci.sh > "$WORK/ci.log" 2>&1
CIRC=$?
end=$(date +%s)
tail -n 12 "$WORK/ci.log"
[ $CIRC = 0 ] || bad "CI inside extraction exited with $CIRC"
note "CI inside extraction: exit code $CIRC, $((end - start)) s"

cd "$ROOT"
{
  echo "{"
  echo "  \"archive\": \"$ARCHIVE\","
  echo "  \"archive_sha256\": \"$ARCH_SHA\","
  echo "  \"extraction_dir\": \"$WORK\","
  echo "  \"status\": \"$STATUS\","
  echo "  \"ci_exit_code\": $CIRC,"
  echo "  \"notes\": ["
  first=1
  for n in "${NOTES[@]}"; do [ $first = 1 ] || echo ","; printf '    "%s"' "${n//\"/\'}"; first=0; done
  echo ""
  echo "  ],"
  printf '  "ci_results": '
  if [ -f "$WORK/ci_results.json" ]; then sed '1!s/^/  /' "$WORK/ci_results.json"; else echo "null"; fi
  echo "}"
} > "$OUT"
echo "verification written to $OUT: $STATUS"
[ "$STATUS" = PASS ]
