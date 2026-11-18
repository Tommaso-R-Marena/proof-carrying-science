# V23: Assurance Mirage research census successor

V23 is a reviewed whole-tree census successor of immutable V22. It admits the
additions-only `research/assurance_mirage_v1/` package and the `research/README.md`
index row. Production authority, the formal root, and historical V22/V21/V20
manifest bytes are unchanged.

## What changed

- New research package: Lean channel-independence / guarded-vs-unguarded theorems,
  attested local Qwen red teams, capped Gemini free-tier arm, unguarded replay
  controls, and comparison artifacts.
- Control manifest path advances to `RECONCILIATION_V23.json`.
- Frozen `RECONCILIATION_V22.json` moves into the snapshot (predecessor record).

## What did not change

- No production PCS authority or signing-root change.
- No rewrite of historical PR census entries.
- Receiver cleanup test successor binding remains exact.
- Hosted CI still fail-closed on census/bytes/mode mismatch.

This successor is source reconciliation for research admission, not scientific
acceptance, external validation, or deployment authority.
