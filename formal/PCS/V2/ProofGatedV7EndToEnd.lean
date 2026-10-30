import PCS.V2.ProofGatedRuntimeContract

/-!
# V7 end-to-end composition

From an **independently fixed policy**, through **certificate checking** (PGSC6 or PGSC7,
selected by the pinned policy), **monotonic model promotion** and the **receipt log**, to
**exact inference** by the reference byte interpreter (and by a fixed-width evaluator under
`NoOverflow`).

* `runAdv_request_inert` — over a whole adversarial trace, every proposer-controlled field
  other than the certificate bytes (requested policy, generation, incumbent) is inert: two
  traces with the same certificate bytes produce identical states and identical logs;
* `v7_end_to_end` — the composed safety statement for an arbitrary adversarial trace;
* `v7_honest_complete` — completeness: every admissible chain under a supported pinned
  policy is realised by some request sequence;
* `v7_audit_end_to_end` — what an independent auditor concludes from an accepted anchored
  receipt chain. Its hypotheses are exactly the external trust assumptions: the auditor's
  pinned policy bytes are authentic, the genesis state is trusted, and the anchor is the
  authoritative state from protected monotonic storage (none of which is implemented here);
* `v7_runtime_audit` — an external runtime satisfying the refinement contract of
  `ProofGatedRuntimeContract` produces a state whose abstract log passes the independent
  chain checker, and whose served predictions are those of the committed network.
-/

namespace PCS.V2.ProofGatedV7EndToEnd

open PCS.V2.ProofGatedGeneric
open PCS.V2.ProofGatedWide
open PCS.V2.ProofGatedRobust
open PCS.V2.ProofGatedStrongGate
open PCS.V2.ProofGatedBytes
open PCS.V2.ProofGatedProtocol (AdmChain lastModel)
open PCS.V2.ProofGatedPolicy
open PCS.V2.ProofGatedBoundary
open PCS.V2.ProofGatedReceipt
open PCS.V2.ProofGatedInterpreter
open PCS.V2.ProofGatedRuntimeContract

theorem propose_inert (s : AState) (r r' : Request) (h : r.certificate = r'.certificate) :
    propose s r = propose s r' := by
  unfold propose
  rw [safe_policy_independent s.policy s.generation s.active r r' h, h]

/-- **Requested fields are inert over whole traces.** -/
theorem runAdv_request_inert : ∀ (rs rs' : List Request) (s : AState),
    rs.map (·.certificate) = rs'.map (·.certificate) → runAdv s rs = runAdv s rs'
  | [], [], _, _ => rfl
  | [], _ :: _, _, h => by simp at h
  | _ :: _, [], _, h => by simp at h
  | r :: rs, r' :: rs', s, h => by
    simp only [List.map_cons, List.cons.injEq] at h
    simp only [runAdv, propose_inert s r r' h.1, runAdv_request_inert rs rs' _ h.2]

/-- **V7 end-to-end safety.** For any pinned policy `P`, generation `g`, initial active
bytes `a₀` decoding to `m₀`, and **any** adversarial request sequence `rs`: the policy is
unchanged; the outcome depends on the requests only through their certificate bytes; the
active bytes are the canonical bytes of a valid network `m` that the reference interpreter
serves exactly, that keeps every correct integer of `m₀`, stays within every interval
error bound of `m₀`, and whose loss accounts for every acceptance; the generation counts the
acceptances; the emitted receipt log passes the independent chain checker; and any
fixed-width evaluator satisfying `NoOverflow` computes `m` exactly on its range. -/
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
      (∀ X h, NoOverflow P.arch X h → ∀ x : Int, x.natAbs ≤ X → predictK h m x = predict m x) := by
  intro out
  obtain ⟨m, ⟨-, hd, hnf, hrob⟩, hg, hl⟩ := runAdv_invariant ⟨P, g, a₀⟩ rs m₀ h₀
  have hv := decodeBytes_valid hd
  refine ⟨runAdv_policy _ rs, fun rs' h => runAdv_request_inert rs' rs _ h, m,
    decodeBytes_canonical hd, hv, fun x => ?_, hnf, hrob, hl, hg,
    checkChain_complete ⟨P, g, a₀⟩ rs, fun X h hno x hx => predictK_eq_predict P.arch X h hno m hv x hx⟩
  have hp : out.1.policy = P := runAdv_policy _ rs
  have hd' : decodeBytes P.arch out.1.active = some m := hd
  simp only [servePred, hp, interpBytes_eq_inferBytes, inferBytes, hd', Option.map_some]

/-- **V7 completeness.** Under a supported pinned policy, every admissible chain
`a ↦ m₁ ↦ … ↦ mₖ` is realised by an honest request sequence: the authority ends at
generation `g + k` with the canonical bytes of `mₖ`, and accepted every request. -/
theorem v7_honest_complete (P : Policy) (hP : P.supported) :
    ∀ (ms : List WideNet) (g : Nat) (a : WideNet), AdmChain P.spec a ms →
      ∃ rs : List Request, (runAdv ⟨P, g, encodeBytes a⟩ rs).1 =
          ⟨P, g + ms.length, encodeBytes (lastModel a ms)⟩ ∧
        acceptedCount (runAdv ⟨P, g, encodeBytes a⟩ rs).2 = ms.length
  | [], g, a, _ => ⟨[], rfl, rfl⟩
  | n :: ms, g, a, ⟨hadm, hc⟩ => by
    obtain ⟨r, hacc, hact, hgen⟩ := honest_progress ⟨P, g, encodeBytes a⟩ hP a n rfl hadm
    have hst : (propose ⟨P, g, encodeBytes a⟩ r).1 = ⟨P, g + 1, encodeBytes n⟩ := by
      have hpol := propose_policy_frame ⟨P, g, encodeBytes a⟩ r
      cases hq : (propose ⟨P, g, encodeBytes a⟩ r).1
      rw [hq] at hpol hact hgen
      simp_all
    obtain ⟨rs, h1, h2⟩ := v7_honest_complete P hP ms (g + 1) n hc
    refine ⟨r :: rs, ?_, ?_⟩
    · simp only [runAdv, hst, h1, List.length_cons, lastModel]
      congr 1; omega
    · simp only [runAdv, hst, acceptedCount, List.filter_cons, hacc, if_true,
        List.length_cons] at h2 ⊢
      rw [h2]

/-- **What an independent auditor learns** from an accepted anchored receipt chain.

External trust assumptions, each an explicit hypothesis:
* `hp` — the auditor's pinned policy bytes `pinnedBytes` are the authority's (authentic
  configuration; e.g. protected by signatures or read-only storage, not modelled);
* `h₀` — the genesis state `(g₀, a₀)` is trusted and decodes to `m₀`;
* `anchor` — is the authoritative current state, read from protected monotonic storage
  (not modelled; `ProofGatedReceipt.rollback_without_monotonic_anchor` shows the
  conclusion fails for a stale prefix without it).

Conclusion: the anchored state is reached by an actual authority run from genesis under the
pinned policy, its bytes are the canonical bytes of a valid network `m` that the reference
interpreter serves exactly, and `m` keeps every correct integer and every interval error
bound of `m₀`. -/
theorem v7_audit_end_to_end (pinnedBytes : Bytes) (P : Policy) (g₀ : Nat) (a₀ : Bytes)
    (m₀ : WideNet) (rcs : List Receipt) (anchor : Anchor)
    (hp : decodePolicy pinnedBytes = some P) (h₀ : decodeBytes P.arch a₀ = some m₀)
    (h : checkAnchored pinnedBytes (g₀, a₀) rcs anchor = true) :
    (∃ rs : List Request, runAdv ⟨P, g₀, a₀⟩ rs = (⟨P, anchor.1, anchor.2⟩, rcs)) ∧
    ∃ m, encodeBytes m = anchor.2 ∧ valid P.arch m = true ∧
      (∀ x, interpBytes P.arch anchor.2 x = some (predict m x)) ∧
      (∀ x, predict m₀ x = predict P.target x → predict m x = predict P.target x) ∧
      (∀ B, ErrBound m₀ P.target P.lo P.hi B → ErrBound m P.target P.lo P.hi B) ∧
      anchor.1 = g₀ + acceptedCount rcs := by
  refine ⟨chain_realised hp h, ?_⟩
  obtain ⟨m, hd, hnf, hrob, hg⟩ := anchored_sound hp h h₀
  refine ⟨m, decodeBytes_canonical hd, decodeBytes_valid hd, fun x => ?_, hnf, hrob, hg⟩
  simp only [interpBytes_eq_inferBytes, inferBytes, hd, Option.map_some]

/-- **Runtime plus audit.** Under the refinement contract and the initial-state
assumptions, after any request sequence the external runtime's state equals the authority's
abstract state, the abstract receipt log passes the independent chain checker from the
initial state to the runtime's state, and every served prediction on `|x| ≤ X` is that of
the committed network. -/
theorem v7_runtime_audit (P : Policy) (X : Nat) (R : Runtime) (hC : Contract P X R)
    (st : RState) (m₀ : WideNet) (hI : Initial P st m₀) (rs : List Request) :
    checkChain (encodePolicy P) (st.generation, st.active) (runAdv (abs P st) rs).2
      ((rtRun R st rs).generation, (rtRun R st rs).active) = true ∧
    ∃ m, encodeBytes m = (rtRun R st rs).active ∧
      ∀ x, x.natAbs ≤ X → rtPredict R (rtRun R st rs) x = some (predict m x) := by
  obtain ⟨habs, m, he, -, hp, -⟩ := runtime_end_to_end P X R hC st m₀ hI rs
  refine ⟨?_, m, he, hp⟩
  have hc := checkChain_complete (abs P st) rs
  have hg : (rtRun R st rs).generation = (runAdv (abs P st) rs).1.generation := by
    rw [← habs]; rfl
  have ha : (rtRun R st rs).active = (runAdv (abs P st) rs).1.active := by
    rw [← habs]; rfl
  rw [hg, ha]
  exact hc

/-- **Malicious policy substitution, end to end**: the substituted-target request that a
naive verifier accepts (`ProofGatedPolicy.naive_target_attack`) leaves the pinned authority
unchanged, and its rejection is recorded by a receipt that the independent checker accepts. -/
theorem v7_policy_substitution_rejected :
    (propose ⟨pinned0, 0, encodeBytes gen3⟩ attackTarget).1 = ⟨pinned0, 0, encodeBytes gen3⟩ ∧
    (propose ⟨pinned0, 0, encodeBytes gen3⟩ attackTarget).2.accepted = false ∧
    checkReceipt (encodePolicy pinned0) (propose ⟨pinned0, 0, encodeBytes gen3⟩ attackTarget).2 = true ∧
    naiveDecide 0 (encodeBytes gen3) attackTarget = some (encodeBytes gen0) := by
  refine ⟨?_, ?_, ?_, (naive_target_attack).1⟩ <;> decide +kernel

end PCS.V2.ProofGatedV7EndToEnd
