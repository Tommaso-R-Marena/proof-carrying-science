# Authority V2 shared implementation contract

Frozen parent: `7be674df70eb3108c9dbd8b0b97f42a728bde000` (PR158).
All old modules, policies, theorem statements and source fences remain unchanged.
One writer per worktree. New files only. No merges, production changes or deploys.

## Whole history

`research.scientific_history_v2.audit.audit_history(path, root, anchor, config, ...)`
performs real bounded replay from root-bound checked genesis through every exact
signed envelope. Root policy is existing `PCS-SCI-HISTORY-V1`; checker equals
SHA256 of canonical fixed `OperatorConfig.identity()`. No requester callback or
checker registry/upgrade. Use unchanged `History.snapshot()` for canonical,
cryptographic, scope, link, generation/incumbent and exact external-anchor checks.
Every auxiliary certificate must be empty. Run actual `ReceiverService` on every
artifact, verify scoped signed receipt/raw/config/result binding, no untrusted
cache bypass. Retrospective math != authenticated historical verification.
Return explicit separate statuses and immutable results/progress; maximum32events
by default, max wire8192, aggregate262144, bounded whole-audit time, safe refusal.

## Witness protocol

New `research.scientific_witness_v1` owns protocol/store/server/client.
Policy roots and fixed scientific config are operator bootstrap only. Three key
roles: two existing signed-intent keys, plus a distinct post-verification witness
key. Protocol `PCS-SCI-WITNESS-V1`; data-only canonical bounded JSON, strict types,
no arbitrary commands/paths/key/policy/config in requests.

API desired: `WitnessStore.create(path, root, config, witness_key)` explicit
initialization only; `WitnessStore(path, root, config, witness_key)` never creates
missing state. `prepare(intent_bytes)` verifies exact old dual-signed intent and
actual science, reserves one durable pending successor. Repeating identical intent
is idempotent; conflicting pending/final descendants reject. `finalize(intent_sha256)`
finalizes only that checked pending record. Finalize attests witness commitment,
NOT observation of coordinator SQLite commit. Store full candidate/envelope bytes,
actual Lean result/response digest and prepare/final witness statements atomically.
`checkpoint(nonce)` signs current state + fresh receiver nonce; stale signed views
cannot count as fresh current state. `export(nonce)` returns bounded retained
envelopes/receipts and exact checkpoint. All responses bound to root/config/key.
Root/checker/key rotations unsupported and rejected.

Witness service must independently execute real Lean for genesis/new science.
One honest serial durable witness prevents conflicting descendants within that
state continuity. Witness rollback/compromise or replacement of ALL trusted
bootstrap state remains outside this property. SQLite termination tests !=
physical power-loss durability. Profiles A/B/C must be separately labeled.

Witness runtime agent will communicate exact constructor/client/response schemas
early; parent integrates against that version. Prefer bounded loopback HTTP local
demo and optional verified TLS remote mode. Receiver-pinned witness public key +
fresh challenge is mandatory, regardless of transport. Never silently initialize
new genesis if witness storage disappears. New server subprocess is mandatory.

## Coordinator (parent-owned)

`research.scientific_authority_v2`: PREPARE -> unchanged local History.append
COMMIT -> WITNESS FINALIZE -> eligible snapshot. Eligibility requires local exact
checkpoint/candidate matching a nonce-fresh pinned witness checkpoint/final record.
No serving on prepared-only/local-only state. Witness need not trust a caller's
claim that local commit occurred. Recovery examines exact durable witness material
and signed intent: recreate only a uniquely justified prefix/successor or refuse;
never invent intent/signature/science. Finalized witness with old local store can
be reconstructed from exact retained envelopes under pinned root, followed by
whole-history science audit. Missing evidence/unknown suffixes refuse.

## Lean (formal-agent-owned)

New isolated project `research/scientific_authority_v2/formal/` imports unchanged
scientific receiver, history and join projects. Define actual executable pure
genesis-and-list auditor (not opaque whole-history premise); prove success gives
all artifact science, exact history links and final incumbent. Model one honest
serial witness pending/final phases, eligible local/witness equality, rejection,
no conflicting later finalization and recovery safety. Cryptographic/OS/storage
assumptions explicit. Pure fixture symbolic signatures are not real crypto tests.
No admissions/new axioms/unsafe/native_decide. Audit all theorem statements/closures.

## Resource and reproducibility rules

Lean4.28.0 and existing9 dependency pins. Do not copy7GB Mathlib caches: use
read-only checked imports and fresh own outputs; standalone Lake builds in CI.
RAM9.7GB: coordinate actual receiver tests, maximum two heavy Lean processes total.
Parent baseline suite runs first; agent science-heavy tests wait for quiet slot.
New workflow and integration/public-CI qualification are parent-owned. Every
positive claimed real authorization must use actual Lean; fault injection only
for clearly labeled rejection/crash tests. No independently administered host is
currently available; deliver reference plus actual multi-process local execution.
