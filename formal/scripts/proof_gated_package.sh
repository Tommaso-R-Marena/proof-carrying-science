#!/usr/bin/env bash
# Builds the final archive from the exact committed project files.
#
#   ./scripts/proof_gated_package.sh            # writes dist/pcs_proof_gated_v7.tar.gz
#
# 1. requires a clean git working tree (so the archive is exactly the commit HEAD);
# 2. writes PROOF_GATED_SHA256SUMS (sha256sum format, every archived file except itself)
#    and PROOF_GATED_MANIFEST.json (path, bytes, sha256, category of every archived file
#    except the two manifest files) at the project root;
# 3. creates a reproducible tar.gz (sorted names, fixed mtime/owner, gzip -n) containing
#    precisely: every git-tracked file + the two manifest files;
# 4. writes dist/pcs_proof_gated_v7.tar.gz.sha256.
# Verify with ./scripts/proof_gated_verify_archive.sh.
set -euo pipefail

NAME=pcs_proof_gated_v7
DIST=dist
ARCHIVE=$DIST/$NAME.tar.gz
SUMS=PROOF_GATED_SHA256SUMS
MANIFEST=PROOF_GATED_MANIFEST.json

# The manifest files and dist/ are generated here; anything else must be committed.
dirty=$(git status --porcelain --untracked-files=all | grep -vE " ($SUMS|$MANIFEST|dist/.*)$" || true)
if [ -n "$dirty" ]; then
  echo "refusing to package: uncommitted changes:"; echo "$dirty"; exit 1
fi
COMMIT=$(git rev-parse HEAD)

mkdir -p "$DIST"
LIST=$(mktemp)
git ls-files | grep -vxE "$SUMS|$MANIFEST|dist/.*" | LC_ALL=C sort > "$LIST"

category() {
  case "$1" in
    PCS/V2/ProofGated*Audit.lean) echo "proof_gated_audit" ;;
    PCS/V2/ProofGated*.lean) echo "proof_gated_source" ;;
    fixtures/proof_gated/*) echo "proof_gated_fixture" ;;
    scripts/proof_gated_*|scripts/gen_full_audit.sh) echo "proof_gated_script" ;;
    ci/proof-gated-*) echo "proof_gated_ci" ;;
    results/*) echo "test_results" ;;
    PCS_PROOF_GATED_*.md) echo "proof_gated_report" ;;
    lakefile.toml|lean-toolchain|lake-manifest.json) echo "build_config" ;;
    *.lean) echo "other_lean_source" ;;
    *) echo "other" ;;
  esac
}

# JSON manifest (all archived files except the two manifest files)
{
  echo "{"
  echo "  \"archive\": \"$NAME.tar.gz\","
  echo "  \"source_commit\": \"$COMMIT\","
  echo "  \"lean_toolchain\": \"$(cat lean-toolchain)\","
  echo "  \"file_count\": $(wc -l < "$LIST"),"
  echo "  \"files\": ["
  first=1
  while IFS= read -r f; do
    h=$(sha256sum "$f" | cut -d' ' -f1)
    b=$(wc -c < "$f" | tr -d ' ')
    [ $first = 1 ] || echo ","
    printf '    {"path": "%s", "bytes": %s, "sha256": "%s", "category": "%s"}' \
      "$f" "$b" "$h" "$(category "$f")"
    first=0
  done < "$LIST"
  echo ""
  echo "  ]"
  echo "}"
} > "$MANIFEST"

# sha256sum-format list: every archived file except the SUMS file itself
{ cat "$LIST"; echo "$MANIFEST"; } | LC_ALL=C sort | while IFS= read -r f; do sha256sum "$f"; done > "$SUMS"

# reproducible archive
{ cat "$LIST"; echo "$MANIFEST"; echo "$SUMS"; } | LC_ALL=C sort > "$LIST.all"
tar --sort=name --mtime='2026-01-01 00:00:00Z' --owner=0 --group=0 --numeric-owner \
  --mode='u+rw,go+r' -cf - -T "$LIST.all" | gzip -n -9 > "$ARCHIVE"
(cd "$DIST" && sha256sum "$NAME.tar.gz" > "$NAME.tar.gz.sha256")

echo "archive: $ARCHIVE ($(wc -l < "$LIST.all") files, $(wc -c < "$ARCHIVE") bytes)"
echo "sha256:  $(cut -d' ' -f1 "$ARCHIVE.sha256")"
echo "source commit: $COMMIT"
rm -f "$LIST" "$LIST.all"
