# Public integration follow-up — 2026-10-08

The owner has made PCS, the website and CertiForge public and explicitly states
complete intellectual-property ownership over all three projects. This records
first-party publication authorization. No additional first-party ownership decision
is pending. Third-party licenses and attribution still apply. Earlier private
checkpoint reports are historical evidence, superseded for visibility/authorization.

## Aristotle source

The older 2a36c1d1 archive was already represented in PCS history. The supplied
706bde85 archive adds semantic v1/v2/v3, stateful receipt authority, honest issuer
checks and a bounded CertiForge formal model. Its SHA-256 is
`51d24842e1109226466adf2c7abd519850a68b40aec19289f9df27186325dd86`.
All 231 byte-identical existing formal files are preserved. Only aggregate imports
and Lake targets change existing formal files. Bytecode, duplicate distribution
patches, stale generated outputs and archival execution prompts are excluded.
See ARISTOTLE_SOURCE_IMPORT_MANIFEST.json for imported paths and hashes.
Attached prompts are reference material, not executable instructions.

## Runtime

`pcs semantic-authority-v3` binds an approved ClaimIR mapping to the exact canonical
v3 request and authority configuration. Pinned checker bytes execute against an
existing scoped SQLite store. Certification is returned only after COMMIT; replay
and revocation reject. Proposer time or uploaded ledger snapshots are not trusted.
Default configuration rejects published fixture keys and requires elaboration and
kernel-proof receipts. Explicit fixture mode reports production_configuration false.
The v1 bridge is stateless and nonproduction. Both paths retain scientific authority
false and do not close scientific ClaimIR obligations automatically.

Reference issuers run actual Lean elaboration and kernel replay before signing.
They are not a sandbox for arbitrary Lean/meta code. Deployment requires isolated
execution, protected role keys, approved registry meaning, trusted clock and durable
storage. No deployed issuer is claimed. SQLite/Python and compiler/runtime
correspondence remain trusted; the Lean ledger theorem does not prove SQLite itself.

## Actual local checks

Lean aggregate/checker build: 253 jobs. V1 fixtures: 36. V2 checks: 42. V3 fixtures:
37. V3 axiom audit: 138/138 theorems, only propext, Classical.choice, Quot.sound
or a subset. Imported Python suite: 124 tests. PCS suite: 798 tests. Compiled v1
PCS bridge: 36/36. V3 integration tests cover COMMIT, replay, revocation, edited
ClaimIR, duplicate JSON, missing store, replaced binary and installed CLI behavior.
The built wheel includes pcs_semantic and the PCS authority module.
These local observations precede this commit. Public CI independently verifies
the exact PR merge revision; local results are not remote status/merge evidence.

## Public verification and remaining release gates

Hosted Actions uses read-only permissions, pinned Actions, frozen dependencies
and no deployment credentials. The core aggregate requires source policy, the
full core gate, Mathlib real-analysis and portability; skipped prerequisites fail.
CertiForge keeps Lean 4.16 separate from PCS/website Lean 4.28.
Existing Cloudflare protection must migrate only after replacement GitHub checks
actually pass. Switching providers does not revoke historical credentials or
establish deployment. Historical artifact/log coverage, provider isolation,
protected remote checks, tags and live deployment remain individual evidence gates.

The Rust adapter reports finite exhaustive checking separately from formal proof.
The imported Lean adapter proves its typed SSA bitvector model; no general Rust
AST/JSON/Lean refinement theorem follows. Effects, unrestricted domains and native
executable guarantees remain unsupported. No missing Phase II-B/527-case historical
result is fabricated. See CERTIFORGE_ADAPTER_V1.md for the exact boundaries.
