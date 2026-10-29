# PCS V7: Independent authority-history coverage analysis

**Date:** October 18, 2026.  **Disposition:** Research-only, external semantic reproductions and source-derived counterexamples.  **Original PCS code changed:** None.

## Executive conclusion

The V7 Lean formalization has strong, coherent guarantees for **authorization under a pinned policy** and **replay of proposal receipts under one policy**. Its event/receipt abstraction does **not** claim, and does not supply, complete provenance of (a) the fields of the actual untrusted request or (b) trusted governance changes. The distinction is relevant to V8's evolving capability policies and to independent external auditors. The findings below are **not counterexamples** to existing V7 soundness theorems; they are negative results about an important *stronger, currently unsupported* audit contract.

### Tested evidence

| Experiment | Actual result |
|---|---:|
| Released receipt bytes reconstructed from independent oracle | 7/7 exact byte matches |
| Requests with contradictory policy/generation/active that yield the **same accepted** receipt | 90/90 |
| Same for rejected receipts | 120/120 |
| Extra request-event evidence distinguishes the attempted inputs | 210/210 |
| Trusted supported policy changes with no proposal receipt | 2/2 |
| Replay/authorization controls | 4/4 |
| Cross-policy regression with independently reconstructed PGSC6 artifact | 1/1 |
| Anchor-preserving event tampering (5 representative classes + 2,000 deterministic mutations) | 2,005/2,005 rejected |

`boundary_results.json` records hashes, deterministic test counts and scope restrictions. `v7_boundary_falsification.py` is reproducible on Python 3.11+ using only standard-library modules plus the independently authored accompanying `v7_independent_audit.py` and published V7 fixtures.

## 1. Accepted and rejected request-history equivocation

Exact V7 source (`PCS/V2/ProofGatedPolicy.lean`):

```lean
def safeDecide (pinned : Policy) (g : Nat) (active : Bytes) (r : Request) : Option Bytes :=
  runChecker pinned g active r.certificate
```

Exact V7 source (`PCS/V2/ProofGatedBoundary.lean`):

```lean
def propose (s : AState) (r : Request) : AState × Receipt :=
  match safeDecide s.policy s.generation s.active r with
  | some cand => (⟨s.policy, s.generation + 1, cand⟩, mkReceipt s r.certificate (some cand))
  | none => (s, mkReceipt s r.certificate none)
```

`mkReceipt` receives only the certificate bytes, not `r.requestedPolicy`, `r.requestedGeneration`, or `r.requestedActive`. Therefore the following proposition is **definitionally true**, for every authority state `s` and pair of requests `r` and `r'`:

> If `r.certificate = r'.certificate`, then `propose s r = propose s r'`, even when every other proposer-controlled field differs.

This is a direct consequence of the implementation; the stronger equality of **full state and emitted receipt**, not merely verdict, is worth making explicit in the next audit specification. In V7's threat model, ignoring those fields is an excellent defense against their changing authorization. It simultaneously prevents the resulting receipt from being evidence of which values were submitted in those fields.

The independent experiment constructs 30 inconsistent request-metadata variants for **each** of the seven released V7 receipt cases. All 210 variants reproduce the identical canonical receipt bytes of the original request. For 90 of these, the result is the **same accepted transition**. An external observer possessing only that receipt cannot distinguish genuine submitted metadata from malicious substitution attempts. The independent `strictDecide` model rejects every inconsistent variant, corresponding to V7's explicitly defined optional strict design.

This does not mean a malicious request can promote a different model under the pinned V7 policy. It cannot. The missing information matters specifically for forensic accuracy, provenance, and policy-governance evidence.

## 2. Invisible governance changes in proposal receipts

Exact V7 source (`PCS/V2/ProofGatedBoundary.lean`):

```lean
def govern (s : AState) (p : Policy) : AState :=
  if p.supported ∧ (decodeBytes p.arch s.active).isSome then { s with policy := p } else s

def runEvents : AState → List Event → AState × List Receipt
  | s, [] => (s, [])
  | s, .propose r :: es =>
    let p := propose s r
    let rest := runEvents p.1 es
    (rest.1, p.2 :: rest.2)
  | s, .govern q :: es => runEvents (govern s q) es
```

Suppose `q ≠ s.policy`, `q.supported` and the incumbent decodes under `q.arch`. Then:

- `runEvents s [] = (s, [])`;
- `runEvents s [.govern q] = (⟨q, s.generation, s.active⟩, [])`.

These traces have the **same emitted receipt list, model, and generation**, but different policies. In particular, `ProofGatedReceipt.Anchor` is just `(Nat × Bytes)` for `(generation, active)`; it cannot itself record the policy epoch or event-log root. The independent `pinnedBytes` argument can still be authoritative when supplied securely, but the pair `(generation, active)` does not identify a cross-policy event history.

Two explicit released V7 policies (`mal_target.pgpol7`, `mal_interval.pgpol7`) are both supported and can govern the genesis model according to the stated rules. The independent reference reproduces two such state transitions with no emitted proposal receipts. These are *trusted governance operations*, not proposer-origin attacks. The purpose is to show why an external auditor needs a separate, authenticated governance event channel in a system allowing policy changes.

A stronger historical claim such as "the receipt sequence uniquely determines the full final authority state including its policy" is **false for the mixed-event model**. V7's receipt-chain theorems concern `runAdv` and a pinned policy; they do not assert this stronger claim.

## 3. Exact policy-switch regression: historical guarantees do not automatically carry forward

V7's own Lean source provides the relevant non-vacuous mathematical witness:

```lean
def malTarget : Policy := { pinned0 with target := gen0 }
theorem malTarget_admissible : StrongAdmissible malTarget.spec gen3 gen0 := by
  rw [← acceptStrong_iff]; decide
theorem pinned_rejects_regression : ¬ StrongAdmissible pinned0.spec gen3 gen0 :=
  gen3_gen0_not_admissible
```

These source-level theorems establish that the same network transition `gen3 → gen0` is valid after switching the target to `gen0`, but invalid under the original `pinned0` target `gen3`. Since `govern` checks only supported policy format and incumbent architectural validity, not conservative preservation of the old policy's obligations, the reference can model a **trusted** authorized policy switch and then admit the transition.

The independent Python reference constructed a **250-byte canonical PGSC6 certificate** (`governance_cross_policy_regression.pgsc6`) using the released V7 target, corpus and model artifacts. It reports:

| Metric | Before governed promotion | After governed promotion |
|---|---:|---:|
| Original policy corpus L1 loss (`pinned0`, target `gen3`) | **0** | **34** |
| Replacement policy corpus L1 loss (`malTarget`, target `gen0`) | **34** | **0** |

The reconstructed certificate passes the independent strong semantic acceptance test under `malTarget` and fails under `pinned0`. Its SHA-256 is `3a37eb421ee93ebd0d2c6f27b7b9ccbed1d1e6d50c34b8d708df3b4c7780095a`.

This example shows that **per-transition formal correctness plus trusted policy governance does not imply conservative cross-policy capability preservation**. The original policy's target has changed, and a capability ledger is not part of V7. The example is within the explicit scope limitation of V7, not a refutation of its existing fixed-policy theorem.

The Python-generated certificate itself has **not** been independently submitted to the native Lean V7 checker in this environment; the source includes a Lean theorem for the corresponding mathematical admissibility claim, but this does not amount to a kernel verification of the exact generated wire bytes. The artifact is intended as a follow-up differential vector.

## 3. Prototype event journal and conditional replay

The package includes an intentionally non-authoritative Python reference demonstration of a full event stream. Each canonical JSON event includes:

- Event sequence number and previous event hash;
- Exact before/after authority state, including policy bytes;
- **Full** raw request metadata and certificate bytes for a proposer request, or the complete new policy bytes for a governance event;
- The SHA-256 digest of the V7 proposal receipt on proposal events;
- A SHA-256 commitment to all event fields.

`semantic_event_replay` starts from a fixed genesis state and checks transitions by recomputing V7 reference authorization. Governance is admitted only when the candidate policy digest appears in a **caller-supplied externally authorized set**. A **caller-supplied trusted final hash** is required to verify that the full record has not been rewritten or truncated. These inputs are trust assumptions. Nothing in this Python prototype authenticates them.

The tests demonstrate:

1. The same V7 accepted receipt gives two different request-event hashes when requested policy, generation and incumbent differ.
2. A valid external governance event and a rejected proposal can be replayed to reconstruct the exact final policy and state, under a correct approval set.
3. Missing governance approval fails closed.
4. Dropped, reordered, or modified event records are detected **against an unchanged trusted anchor**.
5. If an attacker is free to replace both the event log *and the anchor*, a forged but internally consistent log can pass a self-supplied-anchor check. This is a deliberately retained negative control.

A SHA-256 event chain **alone** is not a signature, externally monotonic checkpoint, immutable ledger, or proof of operating-system security. The host must authenticate the event producer and protect the authority-owned root/epoch.

## 5. Design implications and next implementation milestone

Propose a new independent authority-level concept:

**`AuthorityCheckpointV8 = (policy_epoch, policy_bytes, model_generation, active_model_bytes_or_digest, event_root)`**

Every governance operation and every model-promotion decision produces an authenticated event envelope. The authority maintains a monotonically increasing **event sequence** for all events and a separately governed **policy epoch** for policy changes. Model generation advances only on accepted model promotion. Auditors replay both proposal and governance event classes from a pinned genesis/checkpoint, verify exact request bytes if forensic fidelity is required, and compare the resulting full authority state against a protected checkpoint.

Suggested *formal* obligations (not established by this Python audit):

- `full_event_replay_sound`: accepted full-history evidence reconstructs the policy as well as active model and generation.
- `full_event_replay_complete`: every event emitted by the full authority transition system has a corresponding auditable envelope.
- `policy_epoch_monotone`: governance cannot silently change policy at the same authority event sequence/epoch.
- `request_record_injective`: a canonical request envelope uniquely commits to the exact request bytes (regardless of whether the request is rejected).
- `conservative_governance_preserves_ledger`: any authorized policy change must preserve separately committed historical capability obligations; this is **not** a V7 property and belongs in a future evolving-policy formalization.
- `external_checkpoint_refinement`: the deployed operating-system service implements the abstract event+checkpoint contract, with all external trust assumptions stated and tested.

Keep this as a separate **audit and deployment track**. Aristotle's V8 mathematical capability research need not be interrupted. Later integration should use a dedicated draft branch and require actual Lean executable cross-runtime replay, since the reference Python oracle is independently written but not formally verified to implement Lean for all inputs.

## 6. Reproduction

```bash
python3 v7_boundary_falsification.py --fixtures fixtures_v7 --out boundary_results.json
```

All test results shown above were run locally from the exact V7 release fixtures. No actual Lean V7 executable was available in the working container. The code's use of V7 definitions is a read-only source-derived reference, and its agreement with the seven released byte fixtures does **not** establish full Python-to-Lean refinement, cryptographic authenticity, or production security.

**Classification:** A rigorous specification-gap finding and reproducible negative control for stronger auditing claims, **not** a new failure of V7 mathematical authorization soundness or an autonomous-learning breakthrough.
