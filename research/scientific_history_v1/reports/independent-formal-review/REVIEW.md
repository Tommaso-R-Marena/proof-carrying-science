# Independent read-only review of the scientific/history formal join

Outcome: **PASS within explicit mathematical scope; no blocking proof defect
found.** This review does not approve a merge, deployment, empirical claim or
production authority change.

The reviewed original files are in
`/workspace/pcs-scientific-history-formal-v1/research/scientific_history_v1/formal`.
All writes and compiler output from this review are confined to this separate
scratch directory. The source snapshot and before/after identities are in
`SOURCE_REVIEW_SNAPSHOT.json`; `REVIEW_RESULT.json` records exact hashes and
actual axiom closures. The original join source hash is
`37fd1bc0f7f7296070f2625734a7d5cf63019cf647c85314d4b9a50afbf5d25e`.
The fixture source hash is
`433517bf4e2d0ecae4a2bdc3c59fffc975734112fd3fe81a17b2aa7cdd554052`.
All four reviewed source files stayed byte-identical throughout checking.

## Actual independent reproduction

Copied Join, Fixtures, library root and Audit into this scratch directory and
compiled each with official Lean 4.28.0 into a fresh local output directory.
Imports use the final qualified scientific receiver v3 `fresh-lean`, the existing
authenticated-history cache and the original baseline/Mathlib caches. No old
source, import cache or other worktree was modified. This is a fresh check of
new join proofs, not a fresh rebuild or independent attestation of the complete
compiler/dependency stack.

All **23 authored theorems** compile. The actual Audit output contains **42
axiom closures including generated declarations**, all subsets of `propext`,
`Classical.choice`, `Quot.sound`. Every authored theorem appears in that audit.
No new axiom, admitted claim or native-compiler proof shortcut is used by the
accepted join sources.

Seven additional reviewer-authored scratch theorems compile against those
freshly rebuilt join modules. Four representative control closures were queried
and contain only the same three permitted axioms. The final control run exits
zero. An initial reviewer proof script failed to close its final auxiliary scope
control; that failed log is retained as `review-controls-initial-failed.log` and
is not qualification evidence. The corrected final proof and log are separate.

## Findings

1. **Exact scientific candidate and commit identity are preserved.**
   `scientificTransition` calls the existing pure scientific `receive` on
   `e.payload.candidate`, rejects a nonempty auxiliary certificate, and only
   returns a result after the existing history `transition` accepts that same
   complete structured envelope. `accepted_checks` and `accepted_sound` imply
   canonical scientific soundness of those exact bytes, exact new incumbent,
   append of the exact envelope, and generation increment by one. No producer
   supplied proof flag, unrelated expression or alternate candidate is used.

2. **Science rejection cannot manufacture a history update.**
   Rejection returns the original state. Empty candidate bytes are independently
   proved to reject. The old history CAS, scope, signature and predecessor checks
   remain conjunctive; symbolic fixture signatures are explicitly finite test
   functions, not claims of real Ed25519 authorization.

3. **Old-history scientific validity is explicitly conditional.**
   `preserves_scientific_history` requires `ScientificHistory s`.
   `run_scientific` additionally requires `Checked s.incumbent`.
   `initial_run_scientific` requires a checked genesis incumbent. The empty
   history predicate is vacuous in the ordinary logical sense, but it does not
   silently validate the separate genesis incumbent.

   The scratch countermodel supplies a bad old envelope with empty candidate
   bytes, then accepts a genuinely checked new candidate. The resulting history
   remains non-scientific. A second control shows an empty trace cannot repair
   an invalid genesis. These are kernel-checked demonstrations that the stated
   premises are essential, not defects in the current conditional theorems.

4. **Opaque root scope is an explicit abstraction limit.**
   The inherited pure `Root` uses arbitrary byte lists for keys/checker identity.
   The new transition fixes the nonempty policy tag and pins envelope fields to
   that trusted root; it does not prove that root keys are valid, distinct or
   nonempty, that a checker digest has 32 bytes, or that such a digest names the
   actual executable/configuration. A scratch theorem demonstrates admission
   with empty opaque key/checker fields under a permissive symbolic verifier,
   while still executing the genuine pure scientific checker.

   This does not falsify `accepted_sound`: mathematical science remains checked,
   and cryptographic interpretation requires the separately stated
   `signatureSound` premise. It is not a runtime attack or real affirmative
   authorization test. Documentation must preserve the distinction between
   opaque formal pinning and the runtime constructor's 32-byte configuration
   identity. If a future theorem claims concrete root-shape or source/executable
   identity, it must add and discharge those obligations explicitly.

5. **Authentication, history and science remain distinct.**
   `accepted_authenticated` retains the explicit verifier-soundness premise.
   Preservation of authentication and predecessor links retains explicit initial
   invariants. New science checking does not certify old historical occurrence,
   external chronology, durable storage, compiler correspondence, database CAS,
   crash recovery or an independently protected root. No fixed-problem
   preservation, improvement, inference promotion or empirical validity follows.

## Readiness

The new mathematical join is appropriate for the next runtime-integration and
adversarial review step. There is no proof-based justification to broaden its
scope beyond the explicit contracts. Source identity, cached-object/source
correspondence, Lean/kernel/compiler, trusted root/configuration and host remain
assumptions. The parent coordinator retains integration authority.

Final source binding: commit `43e7d7198a72a4fd3a41312e845609974987370a` matches every independently reviewed source hash. Existing production, scientific receiver and authenticated-history formal source bytes are unchanged from parent baseline `cb9f4960cb7edbcc7c7ff92e96668d835646b4a1`.
