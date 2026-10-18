# PCS V7: Trusted Policy Binding, Monotonic Authority, and Proof-Carrying Execution

Lean 4.28.0, no Mathlib, no `sorry` / `admit` / `axiom` / `native_decide` / `unsafe` /
`implemented_by` / `extern`. Every public theorem in every `PCS/V2/ProofGated*` module
(818 theorems, 262 of them new in V7) is listed in the regenerated
`PCS/V2/ProofGatedFullAudit.lean`. The CI elaborates that file and checks that the only
axioms used are `propext`, `Classical.choice` and `Quot.sound`. Concrete fixtures are
checked by `decide +kernel`, so the kernel evaluates them and no
`Lean.ofReduceBool` / `native_decide` is involved.

The V5 and V6 theorem statements, sources and wire formats (PGSI1, PGSI2-WIDE, PGSC6) are
unchanged: `git diff` against the delivered V6 commit shows only *added* files plus three
edits. `ProofGatedFullAudit.lean` was regenerated, and `scripts/proof_gated_ci.sh` and
`scripts/gen_full_audit.sh` gained the new modules and test step. Production authority
modules were not modified.

## 1. New modules

| module | lines | public theorems | content |
|---|---|---|---|
| `ProofGatedSweepCert` | 1110 | 81 | Priority 4: sorted-breakpoint sweep certificates for universal no-forgetting |
| `ProofGatedCert7` | 323 | 29 | PGSC7 certificate (PGSC6 base + sweep witness), new tag `PGSC7` |
| `ProofGatedPolicy` | 656 | 41 | Priority 1: policy, canonical `PGPOL7` bytes, trusted checker table, safe/strict/naive designs, attacks |
| `ProofGatedBoundary` | 796 | 42 | Priority 2: trusted/untrusted state machine, receipts, safety, liveness, crash model |
| `ProofGatedReceipt` | 479 | 34 | Priority 3: `PGSR7` receipts, independent receipt and chain checkers, prefix/fork attacks, anchoring |
| `ProofGatedRuntimeContract` | 276 | 11 | Priority 5: refinement contract for an external runtime, with a counterexample for each dropped clause |
| `ProofGatedV7EndToEnd` | 171 | 7 | composition from policy through checking, promotion and receipts to inference |
| `ProofGatedV7Limits` | 201 | 17 | Priority 6: probe-certificate lower bound, objective relativity |

Test script: `scripts/proof_gated_v7_vectors.lean`. Fixtures: `fixtures/proof_gated/v7/`.

## 2. Priority 1: an independently fixed policy authority

`Policy` = (`version`, `checker`, `predicate`, `arch`, `target`, `corpus`, `lo`, `hi`).
Every semantically significant configuration field is a field, including the checker
implementation id and the predicate id. Canonical bytes are `PGPOL7|…`.

```lean
theorem decodePolicy_iff (bs : Bytes) (p : Policy) :
    decodePolicy bs = some p ↔ encodePolicy p = bs
theorem encodePolicy_binds {p q : Policy} (h : encodePolicy p = encodePolicy q) :
    p.version = q.version ∧ p.checker = q.checker ∧ p.predicate = q.predicate ∧
    p.arch = q.arch ∧ p.target = q.target ∧ p.corpus = q.corpus ∧ p.lo = q.lo ∧ p.hi = q.hi
theorem runChecker_sound {p : Policy} {g : Nat} {active cb cand : Bytes}
    (h : runChecker p g active cb = some cand) :
    ∃ o n, decodeBytes p.arch active = some o ∧ decodeBytes p.arch cand = some n ∧
      encodeBytes o = active ∧ encodeBytes n = cand ∧ StrongAdmissible p.spec o n
theorem safe_policy_independent (pinned : Policy) (g : Nat) (active : Bytes) (r r' : Request)
    (h : r.certificate = r'.certificate) :
    safeDecide pinned g active r = safeDecide pinned g active r'
theorem strict_rejects_other_policy (pinned q : Policy) (hq : q ≠ pinned) (g : Nat)
    (active : Bytes) (r : Request) (hr : r.requestedPolicy = encodePolicy q) :
    strictDecide pinned g active r = none
```

The safe design uses only the pinned policy and the authority's own generation and active
bytes. A `Request` (requested policy bytes, requested generation, requested incumbent and
certificate bytes) can influence the verdict only through its certificate bytes.

**Unsafe design: the proposer's requested policy is used.** Six kernel-checked attacks.
In each one the naive verifier commits a candidate that the pinned policy forbids, and the
safe verifier rejects the same request:

| theorem | substituted field | effect under the naive design |
|---|---|---|
| `naive_target_attack` | target | perfect `gen3` replaced by the zero network |
| `naive_interval_attack` | interval `[-4,4]` | robustness violated on the pinned `[-10^9,10^9]` |
| `naive_corpus_attack` | corpus `[8]` | step makes no progress on the pinned corpus |
| `naive_arch_attack` | architecture width 9 | committed bytes do not even decode under the pinned architecture |
| `naive_checker_attack` | checker id `0` (legacy corpus-only) | forgets input `-12` |
| `stale_generation_attack` | requested generation/incumbent | an old certificate is re-accepted |

**Digests.** `digest_sound` states the result *under the explicit hypothesis* that the
digest has no collision with the pinned bytes. `digest_collision_attack` shows that the
hypothesis is necessary: with a constant digest, the target-substitution attack succeeds.

## 3. Priority 2: the trusted/untrusted boundary

Trusted state `AState` = (policy, generation, active bytes). The checker is the fixed code
`runChecker`. The proposer's channel is `List Request`, and governance is a separate
`Event.govern`.

- **(1) Rejections change nothing.** `propose_reject_frame : (propose s r).2.accepted = false → (propose s r).1 = s`.
  `propose_policy_frame` and `runAdv_policy` say no proposal changes the policy.
  `policy_change_needs_governance` says any policy change in a mixed trace contains a
  governance event.
- **(2) Exactly one certificate per success.** `propose_accept_unique`: an accepted request
  corresponds to exactly one canonical PGSC6/PGSC7 certificate accepted under the pinned
  policy.
- **(3) Generations, no stale incumbents.** `propose_accept_generation`: a commit gives
  generation + 1, an unchanged policy, and a certificate naming the current generation and
  the exact current incumbent. `accepted_cert_at_most_once`: in any trace, no certificate
  is accepted twice.
- **(4) Invariants over adversarial traces.** `runAdv_invariant`: for every `rs`, there is
  an `m` with `decodeBytes p.arch active = some m`. That `m` keeps every integer that `m₀`
  gets right, satisfies every interval error bound `ErrBound` of `m₀`, and has
  `acceptedCount + loss m ≤ loss m₀`.
- **(5) Authorized predictions.** `authorized_predict`: `servePred` (the V6 reference byte
  interpreter on the committed bytes) equals `predict m` exactly.
- **(6) Audit log.** `runAdv_log_sound` (every receipt is `ReceiptOK`), `runAdv_log_chain`,
  `log_generation_explained` (every generation change is an accepted receipt with +1;
  rejections keep the state) and `replay_log` (replaying the log reconstructs the state).

**Safety vs liveness.**
- `adversary_can_stall`: an adversary who controls all proposals can block progress forever.
- `honest_progress`: if an admissible successor exists, an honest request is accepted.
- `race_one_winner`: two requests built from the same state cannot both commit. The
  linearisation point is the atomic `propose` step.
- `progress_bounded`: at most `loss m₀` acceptances in any trace, so unbounded progress is
  impossible.
- `dead_end_stuck`: there is a reachable state with positive loss from which nothing is
  ever accepted.

**Crash model.** `Disk` holds state, log and a staging slot. Each request runs as
verify → stage → commit (atomic pointer swap) → log → clear. `crash_recover_consistent`:
for a crash after any micro-step of any request, `recover` yields exactly the state after
`j` or `j+1` requests. `crash_recover_invariant` adds that the invariants survive.
`replay_after_commit`: re-submitting a committed certificate is rejected. This is a proof
about the *abstract* micro-step model. It does **not** prove that a filesystem provides
atomic rename, durability or read-after-write.

## 4. Priority 3: receipts

`Receipt` binds the version, canonical policy bytes, old generation and old active bytes,
expected generation, candidate, certificate, decision, and new generation and new active
bytes. The wire format is the new tag `PGSR7` (`decodeReceipt_iff`, `encodeReceipt_injective`).

```lean
theorem checkReceipt_sound {pinnedBytes : Bytes} {rc : Receipt}
    (h : checkReceipt pinnedBytes rc = true) :
    ∃ p, decodePolicy pinnedBytes = some p ∧ ∃ r : Request,
      propose ⟨p, rc.oldGen, rc.oldActive⟩ r = (⟨p, rc.newGen, rc.newActive⟩, rc)
theorem checkReceipt_complete (s : AState) (r : Request) :
    checkReceipt (encodePolicy s.policy) (propose s r).2 = true
```

Chains: `chain_realised` and `checkChain_sound` say an accepted chain is the log of an
actual authority run from genesis. `checkChain_complete` is the converse.
`checkChain_invariant` carries no-forgetting, error bounds and loss accounting from the
genesis model to the final model.

**What chain continuity does not give**, with kernel-checked counterexamples:
- `prefix_valid` and `prefix_attack`: every prefix of a valid chain is valid. The one-step
  prefix ends at `r1`, which is wrong at `x = 0`, where the current `gen3` is right.
- `fork_attack`: two valid chains reach generation 1 with different models.
- `rollback_without_monotonic_anchor`: a stale prefix passes anchored checking if the
  "anchor" is itself stale.

With an anchor taken from protected monotonic storage (an explicit hypothesis, not
implemented), the following hold:
- `anchored_sound`
- `anchored_rejects_prefix`: every prefix with fewer accepted steps is rejected.
- `anchored_unique_state`

## 5. Priority 4: cheaper no-forgetting certificates

The sweep certificate (`NFCert`) is the list of tagged hidden units of incumbent,
candidate and target, sorted by integer split point. The checker `checkNF` does three
things, and it evaluates no network:
1. checks that the list is a permutation of the actual units;
2. checks sortedness;
3. sweeps the affine coefficients of the two error functions, deciding each affine piece
   in O(1) by exact integer arithmetic.

```lean
theorem checkNF_sound {a m t : WideNet} {c : NFCert} (h : checkNF a m t c = true) :
    ∀ x, predict a x = predict t x → predict m x = predict t x
theorem checkNF_complete (a m t : WideNet)
    (h : ∀ x, predict a x = predict t x → predict m x = predict t x) :
    checkNF a m t (genNF a m t) = true
theorem checkNF_iff_noForgetting (a m t : WideNet) :
    (∃ c, checkNF a m t c = true) ↔ noForgetting a m t = true
theorem checkNF_not_perm (a m t : WideNet) (c : NFCert)
    (h : ¬ c.order.Perm (sweepUnits a m t)) : checkNF a m t c = false
theorem checkNF_unsorted (a m t : WideNet) (c : NFCert) (h : ¬ SortedSplit c.order) :
    checkNF a m t c = false
theorem checkNF_forgetting_rejected (a m t : WideNet) (x : Int)
    (hx : predict a x = predict t x) (hm : predict m x ≠ predict t x) (c : NFCert) :
    checkNF a m t c = false
theorem checkBoth_iff (a m t : WideNet) (L U : Int) (B : Nat) :
    (∃ c, checkBoth a m t L U B c = true) ↔
      (∀ x, predict a x = predict t x → predict m x = predict t x) ∧
      (∀ x, L ≤ x → x ≤ U → (predict m x - predict t x).natAbs ≤ B)
```

Soundness holds against arbitrary witnesses. Fixtures `nf_*` and `both_*` show incomplete,
reordered, duplicated, forged and foreign-unit witnesses being rejected. Completeness is
proved for the whole supported one-dimensional integer ReLU class (`WideNet`, any width,
any integer parameters).

**Costs (proved).** `sweep_steps`: the sweep makes N unit updates and N + 1 O(1) piece
decisions, and `genNF_length` says the certificate has exactly N entries.
`v6_candidates_length_ge`: the V6 procedure evaluates the three networks on at least
9N + 3 integers, each evaluation costing Θ(N). Overall the checker is O(N) arithmetic
operations plus the permutation check (`List.isPerm`, O(N²) comparisons in the current
list implementation), versus V6's Θ(N²) network-unit evaluations. Ordering is the only
work shifted to the untrusted generator (`genNF`), and the checker re-validates it.

**Cost (measured only, not verified).** On 40 random width-24 updates (parameters in
[-1000, 1000]), interpreted `#eval`: V6 `noForgetting` took ≈1.1 s, `genNF` ≈30 ms, and
`checkNF` ≈38 ms. The results agree on all 800 small-suite cases and all 40 large ones.

PGSC7 (`ProofGatedCert7`) = PGSC6 base certificate + the sweep witness:
`checkCert7_sound`, `checkCert7_complete`, `checkCert7_iff_gate`,
`checker_substitution_equiv` (PGSC7 accepts exactly what PGSC6 accepts), `decodeCert7_iff`,
`pgsc6_not_pgsc7` (the two wire formats are disjoint).

## 6. Priority 5: runtime refinement contract

`Runtime` abstracts an external implementation as six functions: policy loader, checker,
parser, evaluator, served-bytes-after-commit and generation update. `Contract P X R` has
one field per obligation:

| field | obligation |
|---|---|
| `policyId` | loading the pinned policy bytes yields exactly `P` |
| `checkerId` | the checker equals the verified table `runChecker` |
| `parseExact` | byte-exact canonical parsing (`decodeBytes`), exact parameters and bounds |
| `arith` | evaluation equals `predict` on valid nets for `|x| ≤ X` |
| `execId` | after a commit the runtime serves exactly the committed bytes |
| `genNext` | generation + 1 per commit |

`Initial` (configuration = pinned bytes, served = active, active decodes) and the
monotonic-state assumption (the state evolves only by `rtStep`) are further hypotheses.

```lean
theorem runtime_end_to_end (P : Policy) (X : Nat) (R : Runtime) (hC : Contract P X R)
    (st : RState) (m₀ : WideNet) (hI : Initial P st m₀) (rs : List Request) :
    abs P (rtRun R st rs) = (runAdv (abs P st) rs).1 ∧
    ∃ m, encodeBytes m = (rtRun R st rs).active ∧ valid P.arch m = true ∧
      (∀ x, x.natAbs ≤ X → rtPredict R (rtRun R st rs) x = some (predict m x)) ∧
      (∀ x, predict m₀ x = predict P.target x → predict m x = predict P.target x) ∧
      (∀ B, ErrBound m₀ P.target P.lo P.hi B → ErrBound m P.target P.lo P.hi B) ∧
      acceptedCount (runAdv (abs P st) rs).2 + loss P.spec.corpusSpec m ≤ loss P.spec.corpusSpec m₀
```

`int64_runtime_end_to_end` discharges `arith` for the wrapping fixed-width evaluator
`predictK` using V6's `NoOverflow`. `pinned0_contract` gives the full contract for the
fixture policy on `|x| ≤ 32768`.

**Necessity of each assumption** (kernel-checked counterexamples):
- no policy authority: the six Priority 1 attacks;
- no execution identity: `stale_cache_runtime` (after a commit the runtime serves the old
  model, which differs at `x = -1`);
- no monotonic state: `rollback_breaks_no_forgetting` (restoring a snapshot serves `r1`,
  which is wrong at 0) and `rollback_enables_replay` (an already used certificate is
  accepted again);
- no overflow contract: `overflow_runtime` (an exact certified network, but `int64`
  returns `0` instead of `2^64` at `x = 2^62`);
- no exact parsing: `truncating_parser_runtime`.

## 7. End-to-end composition (`ProofGatedV7EndToEnd`)

```lean
theorem runAdv_request_inert : ∀ (rs rs' : List Request) (s : AState),
    rs.map (·.certificate) = rs'.map (·.certificate) → runAdv s rs = runAdv s rs'

theorem v7_end_to_end (P : Policy) (g : Nat) (a₀ : Bytes) (m₀ : WideNet)
    (h₀ : decodeBytes P.arch a₀ = some m₀) (rs : List Request) :
    let out := runAdv ⟨P, g, a₀⟩ rs
    out.1.policy = P ∧
    (∀ rs' : List Request, rs'.map (·.certificate) = rs.map (·.certificate) →
      runAdv ⟨P, g, a₀⟩ rs' = out) ∧
    ∃ m, encodeBytes m = out.1.active ∧ valid P.arch m = true ∧
      (∀ x, servePred out.1 x = some (predict m x)) ∧
      (∀ x, predict m₀ x = predict P.target x → predict m x = predict P.target x) ∧
      (∀ B, ErrBound m₀ P.target P.lo P.hi B → ErrBound m P.target P.lo P.hi B) ∧
      acceptedCount out.2 + loss P.spec.corpusSpec m ≤ loss P.spec.corpusSpec m₀ ∧
      out.1.generation = g + acceptedCount out.2 ∧
      checkChain (encodePolicy P) (g, a₀) out.2 (out.1.generation, out.1.active) = true ∧
      (∀ X h, NoOverflow P.arch X h → ∀ x : Int, x.natAbs ≤ X → predictK h m x = predict m x)

theorem v7_honest_complete (P : Policy) (hP : P.supported) :
    ∀ (ms : List WideNet) (g : Nat) (a : WideNet), AdmChain P.spec a ms →
      ∃ rs : List Request, (runAdv ⟨P, g, encodeBytes a⟩ rs).1 =
          ⟨P, g + ms.length, encodeBytes (lastModel a ms)⟩ ∧
        acceptedCount (runAdv ⟨P, g, encodeBytes a⟩ rs).2 = ms.length

theorem v7_audit_end_to_end (pinnedBytes : Bytes) (P : Policy) (g₀ : Nat) (a₀ : Bytes)
    (m₀ : WideNet) (rcs : List Receipt) (anchor : Anchor)
    (hp : decodePolicy pinnedBytes = some P) (h₀ : decodeBytes P.arch a₀ = some m₀)
    (h : checkAnchored pinnedBytes (g₀, a₀) rcs anchor = true) :
    (∃ rs : List Request, runAdv ⟨P, g₀, a₀⟩ rs = (⟨P, anchor.1, anchor.2⟩, rcs)) ∧
    ∃ m, encodeBytes m = anchor.2 ∧ valid P.arch m = true ∧
      (∀ x, interpBytes P.arch anchor.2 x = some (predict m x)) ∧
      (∀ x, predict m₀ x = predict P.target x → predict m x = predict P.target x) ∧
      (∀ B, ErrBound m₀ P.target P.lo P.hi B → ErrBound m P.target P.lo P.hi B) ∧
      anchor.1 = g₀ + acceptedCount rcs
```

There is also `v7_runtime_audit` (a contract-satisfying runtime yields a log accepted by
the independent chain checker) and `v7_policy_substitution_rejected` (the malicious target
substitution, accepted by the naive design, leaves the pinned authority unchanged, and its
rejection receipt passes the independent checker).

**External trust assumptions, all explicit.** These are the only routes by which the
real world enters:
- authenticity of the pinned policy bytes (`hp`);
- trusted genesis (`h₀`);
- the anchor coming from protected monotonic storage (`anchor`);
- the runtime contract fields (`Contract`), the initial-state facts (`Initial`) and the
  monotonic-state assumption;
- for fixed-width runtimes, `NoOverflow`.

Nothing here verifies an operating system, signatures, disk durability, atomic rename or
Python execution.

## 8. Priority 6: limits

```lean
theorem probe_checker_needs_all_points (B : Nat) (hB : 2 ≤ B) (Q : List Int) (D : ProbeChecker)
    (hs : ProbeSound ⟨3, B⟩ Q D) (hc : ProbeComplete ⟨3, B⟩ Q D) :
    ∀ p : Int, p.natAbs + 1 ≤ B → p ∈ Q
theorem probe_checker_length (B : Nat) (hB : 2 ≤ B) (Q : List Int) (D : ProbeChecker)
    (hs : ProbeSound ⟨3, B⟩ Q D) (hc : ProbeComplete ⟨3, B⟩ Q D) : 2 * B - 1 ≤ Q.length
theorem no_finite_probe_checker (Q : List Int) (D : ProbeChecker)
    (h0 : D (vals Q zeroNet) (vals Q zeroNet) (vals Q zeroNet) = true) :
    ∃ n, D (vals Q zeroNet) (vals Q n) (vals Q zeroNet) = true ∧ ¬ NoForget zeroNet n zeroNet
theorem objective_relative :
    StrongAdmissible pinned0.spec gen0 r1 ∧
    predict gen0 (-1) = predict zeroNet (-1) ∧ predict r1 (-1) ≠ predict zeroNet (-1)
```

A probe checker sees the three networks only through their values on a fixed finite set
`Q`, and may be *any* function of those values. If it is sound and complete for universal
no-forgetting on width-3 networks with parameters in `[-B, B]`, it needs at least 2B − 1
probes. That is exponential in the bit length of `B`. The witness is a width-3 "bump"
network, equal to 1 at one integer and 0 everywhere else. With no parameter bound, no
finite probe set works at all. The sweep certificate reads parameters, and its size N is
independent of `B`.

For depth, `saw6_cert_contains_all` and `sawNet_cert_length` (V5/V6) already show that
breakpoint certificates for deep networks can be exponentially long in the depth.
Two-dimensional inputs were **not** formalized beyond this. Region counting in 2D remains
an open item.

**Objective vs intelligence.** `objective_relative` shows that an accepted improvement
under the pinned objective is a strict regression under another objective. Combined with
`progress_bounded`, every result here concerns preservation and bounded improvement of a
*fixed, pinned mathematical objective*. Nothing measures or implies improvement in
scientific truth, general reasoning, autonomous research ability or open-ended
intelligence.

## 9. Tests (`bash scripts/proof_gated_ci.sh`, all passing)

| step | result |
|---|---|
| build | 38 modules (30 V5/V6 + 8 V7); the only warnings are 3 pre-existing unused-variable warnings in `ProofGatedPromotion` |
| forbidden tokens | all `PCS/V2/ProofGated*.lean` + 4 vector scripts clean |
| axiom audits | 125 + 19 + 101 + 818 `#print axioms` entries; axioms used: `propext`, `Classical.choice`, `Quot.sound` only |
| V5 codec vectors | 8502 checks |
| V5 checker vectors | 754 checks |
| V6 vectors | 19199 checks |
| **V7 vectors** | **12776 checks**: 18 fixture files byte-compared; 6 attacks (naive accepts, safe rejects, state unchanged); stored PGSC7 chain replays under `pinned7`; PGSC6 and PGSC7 are not cross-accepted; 7 stored receipts checked independently; anchored chain accepted and stale prefix rejected; receipts rejected under a substituted policy; 556 policy byte mutations (162 decode, none to the pinned policy, all canonical); 1737 PGSC7 mutations (0 accepted); 7997 receipt mutations (0 accepted); 840 sweep-vs-V6 cross-checks; reversed and truncated witnesses rejected; runtime refinement on the adversarial trace |
| file-based authority | 14 CLI cases |

These runtime checks are tests, not proofs. The universal statements are the theorems cited
above.

## 10. Failures, limitations and open items

- `List.mergeSort` does not reduce in the kernel for the fixtures, so `genNF` uses
  insertion sort (O(N²), untrusted generator only).
- The permutation check inside `checkNF` uses `List.isPerm` (O(N²) comparisons). A
  canonical-order design could make it O(N log N), but that was not done.
- `ProofGatedSweepCert.lean` is 1110 lines (one coherent development).
- Crash consistency is proved for an abstract micro-step model only.
- Concurrency is modelled as atomic `propose` steps (linearisation at the commit). No
  interleaving semantics of a real implementation is verified.
- No 2D region-counting theorem. Depth limits come from V5/V6.
- Digest security is only conditional (`digest_sound` with an explicit collision-freedom
  hypothesis).

## 11. Release

`scripts/proof_gated_package.sh` builds `dist/pcs_proof_gated_v7.tar.gz` from the exact
committed tree, with `PROOF_GATED_MANIFEST.json` and `PROOF_GATED_SHA256SUMS`.
`scripts/proof_gated_verify_archive.sh` re-extracts it into a clean directory, checks the
file set and every hash, and reruns the complete CI there from scratch. It writes
`dist/ARCHIVE_VERIFICATION.json`. The archive's SHA-256 is in
`dist/pcs_proof_gated_v7.tar.gz.sha256`, since it cannot be recorded inside the archive
itself.
