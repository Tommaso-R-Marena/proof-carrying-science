# Executed local evidence — delegated effect finality v2

**Date:** 2026-11-07. **Scope:** one offline, SQLite-backed, synthetic provider; cryptographic signatures are real and model-driven/tool-inference behavior is not tested. Mainline PCS runtime is untouched.

## Primary local checks

- 53 successor tests passed (51 stateful/protocol tests and 2 independent abstract-model tests).
- All 39 inherited delegated-action v1 tests passed without modifying the v1 sources.
- 400 seeded one-bit permit mutations exercised; noncanonical signature spelling is now rejected. Mutations that encode the *same exact signed object* after parsing are not claimed attacks. This is an authored mutation set, not an unbiased adversarial benchmark.
- Real concurrent SQLite delivery using ten threads: one provider effect and identical replayed receipts. Twelve concurrent `issue` requests yielded one recorded issuance and stable permit bytes.
- Provider-response-loss after successful commit: duplicate retry preserved exactly one provider effect. Pre-delivery absence remained `IN_FLIGHT`, not mistaken for `NO_EFFECT`.
- Genuine local-cut/provider-fence race retained: old permit executed after gateway rotation but before provider fencing. No early revocation-completeness claim is made.
- A separately written **read-only auditor** revalidated complete signed gateway histories against independent provider SQLite receipts, idempotency keys, version-by-version append effects, provider final body, rotation receipts and trust-root pins. Negative tests altered provider body, gateway index and auditor root, each causing rejection. This independent source checker is not an independent trusted machine or an OS-level attestation.
- **Approval/delegation expiry enforced at provider commit, not merely at gateway admission**; late delivery is rejected, while an already-applied effect may still be reconciled after expiry. Historical gateway clock regression and provider clock regression are rejected by separate mechanisms.
- A separate signed-rotation + sink-fence + no-effect certificate sequence allowed a successor with the same logical intent, while the old permit could not execute after the fence.
- Full on-host gateway audit replay, forged-receipt/gateway-permit rejection, malformed action/reflection tests, signer mismatch on restart, clock rollback, and rehashed historical corruption refusal passed.

## Finite abstract state model

| Configuration | Reachable states | Transitions | Result |
| --- | ---: | ---: | --- |
| Signed issuance + provider idempotency + fenced absence | 131 | 161 | No modeled invariant violations |
| Deliberately broken provider idempotency | 20 before counterexample | 20 before counterexample | Duplicate effect on second delivery |

The checker enumerates two attempt IDs for one intent, at most two epoch cuts, at most two deliver/retry events per attempt, and all enabled transitions to a fixed point. This is a finite abstract model with authored rules, not kernel verification and not a proof of agreement with SQLite.

## Claims that are explicitly *not established*

No real-provider execution, no artificial-intelligence model behavior, no large-scale attacker evaluation, no upstream isolation from a compromised host, no Lean4.28 verification, no end-to-end irrevocable effect guarantee, no universal noninterference, no novel theorem, and no world-changing AI safety breakthrough. Provider fencing and idempotency are trusted properties in this experiment. The synthetic reviewer signature is not evidence of actual human review. If keys, provider behavior or execution isolation fail, all stated conditional safety properties can fail.
