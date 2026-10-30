# Independent host containment review and retest

Reviewed baseline: `7a48fa34441641b0cd28dad3753c72ccf9dceabc`.
Baseline host SHA-256: `9a8e10d0500b4c63cec57006d5bc6821084c9ce583b129829cc00eabda0645d0`.
Fixed working-tree host SHA-256: `90c5b677744b7c6a59a4d2ad8caa01a4d4ccb55503cbbb72f616b23601614bdd`.

The reviewer authored the mathematical codec/semantics and does not characterize review of those proofs as independent. This review covers other authors' host, qualifier, full-profile bootstrap, transport controls, and the separately authored intake test follow-up. No worktree source was edited by this reviewer.

| Finding | Historical reproduction | Independent fixed-source retest |
|---|---|---|
| MEDIUM: bounded nested JSON escapes signed rejection | A 24,002-byte negative-child output caused uncaught `RecursionError` for a valid one-step request. | Returns a signed rejection with `HostRejected: JSON nesting exceeds parser resource limit`. |
| MEDIUM: leader exit skips same-group descendant cleanup | A rejected diagnostic child left its sleeping descendant running after the configured deadline; `/proc` state was `S`. | Descendant is terminated; state is `Z`, not running. Rejection signature verifies. |

Both findings concern verifier-fault containment. No false mathematical acceptance or scientific-input execution exploit was demonstrated. The data-only fixed Lean Main has no request-controlled process-spawn path. The first fix normalizes parser recursion errors and defensively catches them at the service boundary. The second always attempts process-group cleanup; descendants escaping their process group remain outside this mechanism.

The reproduction loads the exact historical host from the pinned Git object into the review process, then exercises the current working-tree host with identical rejection-only diagnostic children. It checks process state, rather than treating a terminated zombie as a live workload. Each reproducer cleans its own sleeping child. Machine-readable evidence is `findings-and-retest.json`; the runner is `audit_repro.py`.

No additional critical issue was found in fixed operator/request separation, raw/result binding, strict JSON field/type checks, or receipt-byte signatures. Receipt authenticity under a separately pinned ephemeral key does not prove historical execution; current code documents that limit. The qualification SHA now binds both environment and transitive declared-module inventory; full-profile bootstrap checks those identities before service construction. Module/object/IR pinning remains distinct from OS-loaded mapping and source-to-prebuilt-object attestation. Child IO/time limits are not an address-space sandbox, and pre/post inventory hashing remains outside the child deadline.

The `ba07e16` intake follow-up was reviewed relative to `45c22c9`: its implementation predecessor changes only actual-authority test path handling, real isolated-binary tests, and the exact test-source digest progression. It introduces no fake verifier fallback and does not change production authority bytes. This statement does not self-approve the earlier receipt repair or authorize deployment.
