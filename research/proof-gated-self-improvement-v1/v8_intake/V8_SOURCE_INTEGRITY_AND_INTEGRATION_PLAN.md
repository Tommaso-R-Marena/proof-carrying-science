# PCS V8 independent intake / missing authoritative release

Source upload SHA-256: `1f606558f6a2db4ce6d751e9b696680bcc1d590d3208317252c3a10d12ae9d97`.
Embedded genuine V7 archive SHA-256: `e98448c4d9493c54b88c876ea715c4c66d653565bf60d553c9627b14b7a5f8f8` (matches supplied V7 root).

The outer Aristotle V8 workspace includes 11 new Lean files (10 research modules plus V8 audit), one V8 vector program, three technical reports, and an additive modification to `scripts/proof_gated_ci.sh`.

**Do not overwrite the existing PCS V7 branch using the outer archive.** Relative to its own embedded V7 release, five preexisting Lean sources differ: `PCS/V2/ProofGatedArtifacts.lean`, `PCS/V2/ProofGatedAudit.lean`, `PCS/V2/ProofGatedFullAudit.lean`, `PCS/V2/ProofGatedInference.lean`, `PCS/V2/ProofGatedV1Analysis.lean`. This contradicts the apparent workspace claim that earlier source files were unchanged; the *authoritative V8 release* might nevertheless preserve them, but is absent from the upload.

The upload also does **not** include the actual `dist/pcs_proof_gated_v8.tar.gz` bytes, V8 manifest/checksum files, the V8 audit generator `scripts/gen_v8_audit.sh`, or the 31 fixtures mentioned by `scripts/proof_gated_v8_vectors.lean`. The verification record at `dist/ARCHIVE_VERIFICATION_V8.json` reports these passed in another extraction, but no independent replay of that claimed V8 release can be performed from this upload alone.

`stage_v8_source_only.py` fail-closed stages only the V8 additions onto an EXACT V7 baseline. It refuses to overwrite any new file and rejects any changed preexisting theorem source or CI script. It deliberately labels output as incomplete.

**Needed for a full GitHub integration:** The exact `dist/pcs_proof_gated_v8.tar.gz` binary matching `f14d015998a50756eb47b74f432f2cc1ed0d5e3afb0f4793758aa225a954330f`, and its release manifest. CI must be rerun in GitHub on the integration branch, with independent source and wire verification.

## Local safe-staging check (2026-10-18)
- Re-extracted the hash-verified V7 release into a fresh directory.
- Applied only the isolated 11 V8 Lean files, vector script, three reports, and the additive CI update under exact V7 baseline checks.
- 49 proof-gated Lean modules present after staging; 280 `#print axioms` entries in V8 audit.
- Static scan found no targeted forbidden tokens.
- Could not run V8 `lake build`/CI from this upload: V8 audit generator, fixtures and actual V8 release tarball are absent.

## GitHub staging policy
This draft is **documentation-only** and does not change V7 formal sources. Rebase all actual V8 theorem integration on the already verified V7 PR #149 once the exact V8 release bytes are available. Import only the verified V8 delta; do not replace earlier Lean files from the stale outer workspace. Keep draft, do not merge into production. The V7 independent auditor remains separate as PR #151.
