# Live retained-checkpoint hardening

Use `from research.causal_firewall_v1.checkpoint import Session` for the guarded
research interface. It delegates every positive effect to the unchanged native
byte authority and transactional broker, while retaining the last observed receipt
prefix in host memory. Every attempted operation and audit must extend that exact
prefix. Denied attempts are anchored too, even though generation does not change.
The staged receipt is captured before commit and adopted only after successful
commit; failed transactions do not advance it. A per-instance lock protects the
commit/anchor handoff across host threads. Valid descendants from other instances
remain acceptable and observing one advances the retained prefix.

This was added after the registered model experiment found a further exploratory
counterexample: roll back an active unanchored database after read_private, then
trust its old generation. The frozen broker admits a public write of the previously
read synthetic secret. Retaining the correct generation already refuses; this
wrapper additionally refuses even when the caller supplies the rolled-back value.
The seven actual-authority tests retain that baseline counterexample, verify the
fix, cover denied-receipt rollback, failed private transactions, concurrency,
reopening, observed descendants and rollback immediately after a real commit,
and preserve rollback of both roots as a
negative control. No fake affirmative authority is used.

The **134-request / 96-history primary experiment uses the frozen parent broker**;
its source freeze, capture and metrics have not been rewritten to imply the wrapper
was used. The subsequent wrapper is separately tested with real native decisions
and CI. The unchanged general Lean theorems apply to admitted modeled transitions;
the wrapper itself and Python/SQL/host correspondence are not kernel proved.

This is host-memory consistency, not an independently controlled trust root.
Same-process code can mutate Python state. Administrator rollback of both database
and memory/checkpoint still defeats it; process restart must supply the externally
retained expected checkpoint to `Session.reopen`. There is no automatic secure
persistence, external monotonic service or uninterrupted power-loss guarantee for
the memory anchor. If commit succeeds and the process dies before retaining its
checkpoint, recovery requires an independently retained expectation. Logs, timing
and all other exclusions in the parent formal theorem still apply. No production
authority changes, merge or deployment.
