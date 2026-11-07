# Delegated effect finality v2 — experimental, offline successor to PCS PR #204

**Status: research only. Not a breakthrough claim, production authorization service, general agent-safety proof, or proof of a real provider integration.** This v2 successor is designed to be stacked on the six-file v1 draft contribution. It imports its canonical JSON codec, Ed25519 grant-chain validation, and basic fail-closed parser, without altering production `pcs/`, `formal/`, CI gates or existing draft PRs.

## The question

Can a *specific signed multi-agent instruction* remain bounded after a gateway approves it, but before an external provider makes its effects final — including a lost response, redelivery, concurrent retry, state change, and authorization revocation?

The same user instruction may be retried under a new request identifier. Idempotency per request ID alone does not prevent this form of duplication. V2 therefore binds an independent `intent` identifier to every signed action; a new reservation for that intent is refused while any previous attempt is still `RESERVED`, `IN_FLIGHT`, or `APPLIED`. A successor becomes admissible only after the old attempt is formally marked `NO_EFFECT` by a provider-attested *post-fence absence certificate*, or `ABANDONED` when **no dispatch permit was ever issued** and the old epoch has been fenced.

## Trust path

1. **Principal:** the root signs an attenuating delegation chain; the agent signs the exact action including intent, provider snapshot digest, provider version, authority epoch and gateway version.
2. **Reviewer:** a distinct key signs a one-use approval binding the exact action and entire chain. This is a cryptographic test token; in the local tests, this is not a real human.
3. **Gateway:** validates authority and a signed provider snapshot under a `BEGIN IMMEDIATE` lock. Reservation and idempotent permit issuance are hash-audited. Retry returns *the same signed permit bytes*. The gate refuses another action for an unresolved intent.
4. **Provider:** a separate SQLite file stands in for an idempotent provider that authenticates gateway permits, verifies the provider-state preimage and epoch at effect time, and atomically stores one effect and its signed result under a stable idempotency key.
5. **Recovery:** response loss leaves the gateway `IN_FLIGHT`. The provider may return the existing signed receipt, but an absent response or a simple failed lookup never authorizes replacement.
6. **Revocation:** a root-signed gate epoch increment enters `cut_pending`. The revocation is **not final** until the provider has processed and signed a matching monotone epoch fence. A previously issued permit may still execute *between those events*; the included test demonstrates this limitation. Only after the fence may the provider attest no prior effect, assuming complete mediation, provider linearizability and correct replayed-permit rejection.

Reviewer and delegation expiry are both embedded in the immutable dispatch permit as the **minimum signed expiry** and checked again by the provider at effect time. A previously committed result remains discoverable even after expiry; an expired yet uncommitted permit cannot newly execute. The host and provider clocks are separate trusted monotone assumptions, with on-host rollback checks.

An independent read-only verifier in `independent_audit.py` uses its **own JSON, Ed25519, state-machine, grant and receipt-checking implementation**, and checks both SQLite ledgers for correspondence. It can detect a mismatched gateway index, modified signed events, an unknown provider effect, inconsistent provider body/version, and mismatched sink fence evidence; it cannot validate the real OS/provider behavior, key custody or the truth of a provider's own attestation.

The sink implements only a **local simulated append to private notes**; no external network, cloud tool, real email, filesystem deletion, shell execution, or LLM inference occurs. Signatures use Ed25519 from `cryptography`. Persistent database trust-configuration pins reject accidental signer substitutions upon restart. Gateway receipts and history are hash-linked; independent external head anchoring is optional and necessary to recognize wholesale rollback. A changed SQLite database and its trusted anchor can still defeat this audit model.

## Conditional assurance scope

For a fixed `intent`, under uncompromised roots/reviewer/sink/gateway keys, monotone gate clock, exact source/runtime assumptions, exclusive effect mediation, no unauthorized out-of-band provider writes, atomic and persistent provider idempotency, unforgeable receipts, and linearizable provider fences:

- Each authenticated gateway issuance binds exactly one signed user action, immutable provider preimage, delegate chain and one-use review.
- A provider reservation ID produces at most one simulated effect even if delivered repeatedly or concurrently.
- No replacement for an intent is issued while the prior request is unsettled or applied. If a replacement is allowed after `NO_EFFECT`, the old epoch is fenced and old permits cannot later apply.
- Root revocation is **not** reported as completed until a signed provider fence is received and verified.
- No `NO_EFFECT` certificate is issued from read-absence alone; it requires an epoch fence and absence under the provider lock.

These are **implementation-oriented, conditional properties**: bounded model exploration and authored tests are not Lean kernel proofs, proof of the Python implementation, external provider contracts, untracked side effects, or model alignment. Another signed `intent` may refer to the same semantic task; protecting against such aliasing requires trusted task identity and review semantics beyond this model.

## Reproduce

At the repository root with Python 3.11+ and `cryptography>=42,<47`:

```bash
python -m unittest research.delegated_action_gate_v1.test_gate -q
python -m unittest research.effect_finality_v2.test_protocol research.effect_finality_v2.test_modelcheck -q
python -m research.effect_finality_v2.modelcheck
python -m research.effect_finality_v2.demo
```

The independent abstract model explores all reachable states for two possible authorized attempts at one intent, at most two revocations, and at most two delivery/retry steps per attempt. It deliberately includes broken-provider idempotency to produce a minimal duplicate-effect witness. This is *finite exhaustive exploration*, not an unbounded model-checking proof.

## Findings and preserved negative controls

- **Signature encoding malleability discovered during development.** Uppercasing an ASCII hex digit in an Ed25519 signature preserves the signature bytes but changes a canonical JSON object hash used to bind a provider receipt. In the first V2 draft this could commit an effect that the gateway then could not reconcile. Fixed by rejecting non-lowercase signature encodings at the v2 boundary, and regression-tested. The v1 module is left unchanged.
- **Revocation-before-fence gap is real.** An old gateway-issued permit can still commit at the simulated sink after a local root rotation but before the sink processes the remote epoch fence. The gateway's `cut_pending` is deliberate; do not call local revocation "complete".
- **No provider idempotency cannot deliver both at-most-once safety and automatic retry.** The abstract counterexample is `reserve first → issue a → deliver a → deliver a` with a deliberately broken sink. More generally, lost response after a possibly executed irreversible effect makes successful execution and no-effect indistinguishable to the client without a provider contract, query or reconciliation protocol.
- **Expiry-only-at-admission vulnerability fixed.** The first successor iteration allowed a signed permit to execute after its reviewer token expired; the final version binds permit expiry to the earlier of reviewer and delegation expiry, rechecks at gateway issuance and at sink commit, and permits old results to be reconciled without new effects.
- **Fresh ID replacement vulnerability blocked only within trusted intent identity.** A valid new reviewer token for the same declared `intent` is rejected while its earlier request is unknown. The gate cannot infer whether two different intent labels refer to one real-world purpose.
- A signed provider snapshot can still be stale by dispatch time: the sink must revalidate the exact preimage under its own lock. Gateway admission is not effect approval by the provider.

## Do not promote this to production until

1. An independent Lean 4.28 formal state machine and proof for reservation, revocation, retries and intent non-duplication is actually compiled and audited; plus a genuine Python/refinement argument.
2. A real provider adapter proves its advertised idempotency, verified dispatch custody, linearizable fencing, and post-fence absence semantics, including real crash windows.
3. A trusted separate auditor retains a state-root checkpoint and has independent access to provider receipts; same-process SQLite replay is insufficient for host compromise.
4. Independent adversaries create held-out tool-use tasks with realistic utility and latency requirements; compare an unmediated baseline, ordinary capability tokens, v1, and v2, reporting false refusals and unknown outcomes.
5. A security/rights review checks Python deserialization, races, persistent key storage and recovery; an operating system sandbox and exact dependency lock are added.

## Related work / overlap, not a novelty assertion

- [Tenuo](https://github.com/tenuo-ai/tenuo) already implements signed attenuating AI-agent warrants and human approval.
- [AID-Guard, August 2026](https://arxiv.org/abs/2608.21159) studies authorization-to-effect closure across retry/recovery and provider contracts. Our small synthetic prototype does not supersede its evaluations.
- [Root-Scoped Quiescence, September 2026](https://arxiv.org/abs/2609.21284) covers root-scoped revocation fences in long-running agent paths.
- [Where Does Exactly-Once Live?, September 2026](https://www.alphaxiv.org/abs/2609.29095) studies duplicate side effects across models, harnesses and tool contracts.

The immediate potential PCS value is **composability and reproducibility** with its existing signed delegation/history work, not claiming priority over this active research field.
