import PCSAssumptionDiscovery.Cegar

/-!
# Abduction receipts, independent replay and conditional conclusions

* `feasibleB` — an independent brute-force checker of a reported explanation (enumerates
  every world; shares no code with the decision-diagram route).  `feasibleB_iff`.
* `Receipt` binds the full problem content (ambient assumptions, target, catalog, costs,
  locks), the limits, the checker revision, the outcome and — explicitly — the
  *additional assumptions* (the selected catalog formulas).
* `Receipt.verify` regenerates the receipt and independently rechecks the explanation.
* `ConditionalClaim` is the conditional conclusion `A ∧ (selected Hᵢ) → T`; the discovered
  hypotheses are never silently imported into an unconditional theorem.
* `abduction_result_replay_sound` — a verified receipt entails the conditional claim with a
  satisfiability witness, global optimality, exact count and mandatory/possible membership.
-/

namespace PCSAssumptionDiscovery

open PCSOmega PCSDD

variable {m k : Nat}

/-- Executable context test. -/
def ctxB (p : Problem m k) (w y : List Bool) : Bool :=
  p.ambient.eval (envOf w) && (List.range k).all (fun i => !sel y i || (p.hyp i).eval (envOf w))

theorem ctxB_iff (p : Problem m k) (w y : List Bool) : ctxB p w y = true ↔ Context p w y := by
  unfold ctxB Context
  simp only [Bool.and_eq_true, List.all_eq_true, List.mem_range, Bool.or_eq_true, Bool.not_eq_true']
  apply and_congr Iff.rfl
  constructor
  · intro h i hi hs; rcases h i hi with h | h
    · rw [hs] at h; cases h
    · exact h
  · intro h i hi
    cases hs : sel y i
    · exact Or.inl rfl
    · exact Or.inr (h i hi hs)

/-- Executable lock test. -/
def locksB (p : Problem m k) (y : List Bool) : Bool :=
  p.lockedIn.all (sel y) && p.lockedOut.all (fun i => !sel y i)

/-- **Independent brute-force feasibility checker.** -/
def feasibleB (p : Problem m k) (y : List Bool) : Bool :=
  (y.length == k) && (allAsg m).any (fun w => ctxB p w y) &&
    (allAsg m).all (fun w => !ctxB p w y || p.target.eval (envOf w)) && locksB p y

theorem feasibleB_iff (p : Problem m k) (y : List Bool) : feasibleB p y = true ↔ Feasible p y := by
  unfold feasibleB Feasible Consistent Sufficient LocksOK locksB
  simp only [Bool.and_eq_true, beq_iff_eq, List.any_eq_true, List.all_eq_true, mem_allAsg,
    Bool.or_eq_true, Bool.not_eq_true', ctxB_iff]
  constructor
  · rintro ⟨⟨⟨hl, w, hw, hc⟩, hs⟩, hin, hout⟩
    refine ⟨hl, ⟨w, hw, hc⟩, fun v hv hcv => ?_, hin, fun i hi => by simpa using hout i hi⟩
    rcases hs v hv with h | h
    · rw [(ctxB_iff p v y).2 hcv] at h; cases h
    · exact h
  · rintro ⟨hl, ⟨w, hw, hc⟩, hs, hin, hout⟩
    refine ⟨⟨⟨hl, w, hw, hc⟩, fun v hv => ?_⟩, hin, fun i hi => by simp [hout i hi]⟩
    cases h : ctxB p v y
    · exact Or.inl rfl
    · exact Or.inr (hs v hv ((ctxB_iff p v y).1 h))

/-- Checker revision bound into every receipt. -/
def CHECKER : String := "pcs-abduction-dd-bellman/1"

/-- Additional assumptions reported by an outcome (the selected catalog formulas). -/
def additional (p : Problem m k) : Outcome → List (BForm m)
  | .optimal e => e.indices.map p.hyp
  | _ => []

/-- Abduction receipt. -/
structure Receipt (m k : Nat) where
  problem : Problem m k
  limits : Limits
  checker : String
  outcome : Outcome
  additionalAssumptions : List (BForm m)
  deriving DecidableEq, Repr

/-- Issue a receipt. -/
def issue (p : Problem m k) (lim : Limits) : Receipt m k :=
  ⟨p, lim, CHECKER, discover p lim, additional p (discover p lim)⟩

/-- Independent re-check of an optimal outcome by the brute-force checker. -/
def recheck (p : Problem m k) : Outcome → Bool
  | .optimal e => feasibleB p e.selection && (e.cost == selCost p e.selection) &&
      (e.indices == idxSet k e.selection)
  | _ => true

/-- **Replay**: regenerate and independently recheck. -/
def Receipt.verify (r : Receipt m k) : Bool :=
  (r == issue r.problem r.limits) && recheck r.problem r.outcome

/-- The conditional conclusion: ambient assumptions plus the *explicit* additional
assumptions entail the target on every world. -/
def ConditionalClaim (p : Problem m k) (extra : List (BForm m)) : Prop :=
  ∀ w, w.length = m → p.ambient.eval (envOf w) = true → (∀ h ∈ extra, h.eval (envOf w) = true) →
    p.target.eval (envOf w) = true

/-- The conditional claim is not vacuous: its premises are jointly satisfiable. -/
def NonVacuous (p : Problem m k) (extra : List (BForm m)) : Prop :=
  ∃ w, w.length = m ∧ p.ambient.eval (envOf w) = true ∧ ∀ h ∈ extra, h.eval (envOf w) = true

theorem context_iff_extra (p : Problem m k) (w y : List Bool) :
    Context p w y ↔ p.ambient.eval (envOf w) = true ∧
      ∀ h ∈ (idxSet k y).map p.hyp, h.eval (envOf w) = true := by
  unfold Context
  apply and_congr Iff.rfl
  simp only [List.mem_map, mem_idxSet]
  constructor
  · rintro h f ⟨i, ⟨hi, hs⟩, rfl⟩; exact h i hi hs
  · intro h i hi hs; exact h _ ⟨i, ⟨hi, hs⟩, rfl⟩

/-- **Replay soundness of abduction receipts.** -/
theorem abduction_result_replay_sound {r : Receipt m k} (hv : r.verify = true) {e : Explanation}
    (ho : r.outcome = .optimal e) :
    r.problem.validB = true ∧ r.checker = CHECKER ∧
    r.additionalAssumptions = e.indices.map r.problem.hyp ∧
    ConditionalClaim r.problem r.additionalAssumptions ∧
    NonVacuous r.problem r.additionalAssumptions ∧
    Optimal r.problem e.selection ∧ (∀ z, Feasible r.problem z → e.cost ≤ selCost r.problem z) ∧
    e.cost = selCost r.problem e.selection ∧
    (∃ S : List (List Nat), S.Nodup ∧ e.count = S.length ∧
      ∀ I, I ∈ S ↔ ∃ y, Optimal r.problem y ∧ idxSet k y = I) ∧
    (∀ i, i ∈ e.mandatory ↔ i < k ∧ ∀ y, Optimal r.problem y → i ∈ idxSet k y) ∧
    (∀ i, i ∈ e.possible ↔ i < k ∧ ∃ y, Optimal r.problem y ∧ i ∈ idxSet k y) := by
  unfold Receipt.verify at hv
  simp only [Bool.and_eq_true, beq_iff_eq] at hv
  obtain ⟨hr, hre⟩ := hv
  have hd : discover r.problem r.limits = .optimal e := by
    have := congrArg Receipt.outcome hr; simp only [issue] at this; rw [← this, ho]
  have hadd : r.additionalAssumptions = e.indices.map r.problem.hyp := by
    have := congrArg Receipt.additionalAssumptions hr; simp only [issue] at this; rw [this, hd]; rfl
  have hchk : r.checker = CHECKER := by have := congrArg Receipt.checker hr; simpa [issue] using this
  obtain ⟨hvalid, _⟩ := discover_unfold hd
  obtain ⟨hopt, _, hcost, hmin, _, _, _, hidx⟩ := discover_optimal hd
  rw [ho] at hre
  simp only [recheck, Bool.and_eq_true, beq_iff_eq] at hre
  have hfeas : Feasible r.problem e.selection := (feasibleB_iff _ _).1 hre.1.1
  refine ⟨hvalid, hchk, hadd, ?_, ?_, hopt, hmin, hcost, abduction_optimal_count hd,
    (abduction_mandatory_possible_exact hd).1, (abduction_mandatory_possible_exact hd).2⟩
  · intro w hw ha hx
    rw [hadd, hidx] at hx
    exact hfeas.2.2.1 w hw ((context_iff_extra _ w _).2 ⟨ha, hx⟩)
  · obtain ⟨w, hw, hc⟩ := hfeas.2.1
    refine ⟨w, hw, hc.1, ?_⟩
    rw [hadd, hidx]; exact ((context_iff_extra _ w _).1 hc).2

/-- Every issued receipt verifies (completeness of replay). -/
theorem issue_verify (p : Problem m k) (lim : Limits) : (issue p lim).verify = true := by
  unfold Receipt.verify
  simp only [Bool.and_eq_true, beq_iff_eq]
  refine ⟨rfl, ?_⟩
  show recheck p (discover p lim) = true
  cases hd : discover p lim with
  | optimal e =>
      obtain ⟨hopt, _, hcost, _, _, _, _, hidx⟩ := discover_optimal hd
      simp only [recheck, Bool.and_eq_true, beq_iff_eq]
      exact ⟨⟨(feasibleB_iff _ _).2 hopt.1, hcost⟩, hidx⟩
  | _ => rfl

/-- A receipt with any altered field (outcome, additional assumptions, problem, limits or
checker) is rejected unless it equals the regenerated one. -/
theorem verify_rejects_altered {r : Receipt m k} (h : r ≠ issue r.problem r.limits) :
    r.verify = false := by
  unfold Receipt.verify
  simp [h]

end PCSAssumptionDiscovery
