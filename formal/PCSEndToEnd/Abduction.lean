import PCSAssumptionDiscovery

/-!
# End-to-end theorem for conditional assumption discovery

Pipeline: an accepted abduction request (a valid finite problem — ambient assumptions `A`,
target `T`, named catalog `H₀ … Hₖ₋₁`, positive costs, locks — together with resource limits) is
solved by the exact symbolic discovery procedure, a receipt is issued that carries the
*additional assumptions* explicitly, and the receipt is independently replayed (regeneration
plus the brute-force checker `feasibleB`).  An untrusted proposal policy may submit a candidate
explanation; it is only *audited* (feasibility and exact optimality gap), never trusted.

`end_to_end_abduction_sound` — a reported explanation is a satisfiable, sufficient, globally
minimum-cost assumption set; the count of distinct optimal catalog-index sets is exact; the
mandatory/possible lists are exact; the conditional conclusion `A ∧ (selected Hᵢ) → T` is
carried with the additional assumptions in both the conclusion and the receipt.
`abduction_policy_cannot_change_result` — the result does not depend on the proposal policy;
`abduction_audit_gap_sound` — an audited feasible proposal never beats the certified optimum.
-/

namespace PCSEndToEnd

open PCSOmega PCSDD PCSAssumptionDiscovery

variable {m k : Nat}

/-- A conditional theorem: the original target under the ambient assumptions *and the explicit
additional assumptions*, with a satisfiability witness for its premises. -/
structure ConditionalTheorem (p : Problem m k) where
  extra : List (BForm m)
  holds : ConditionalClaim p extra
  nonVacuous : NonVacuous p extra

/-- An untrusted abduction policy: proposes a selection (from arbitrary weights/memory). -/
structure AbductionPolicy (W : Type) where
  weights : W
  propose : W → List Bool

/-- Audit of a proposal: feasibility by the independent brute-force checker and its cost. -/
structure Audit where
  feasible : Bool
  cost : Nat
  gap : Option Nat
  deriving DecidableEq, Repr

inductive AbductionResult (m k : Nat) where
  | rejected
  | inconsistentAmbient
  | noExplanation
  | resourceLimit
  | explained (r : PCSAssumptionDiscovery.Receipt m k) (e : Explanation)
  deriving DecidableEq, Repr

/-- The pipeline result (policy-independent). -/
def abductionResult (p : Problem m k) (lim : Limits) : AbductionResult m k :=
  if p.validB then
    let r := issue p lim
    if r.verify then
      match r.outcome with
      | .optimal e => .explained r e
      | .inconsistentAmbient => .inconsistentAmbient
      | .noExplanation => .noExplanation
      | .resourceLimit _ => .resourceLimit
      | _ => .rejected
    else .rejected
  else .rejected

/-- The audit of a policy proposal against the certified result. -/
def audit {W : Type} (p : Problem m k) (lim : Limits) (pol : AbductionPolicy W) : Audit :=
  let y := pol.propose pol.weights
  let f := feasibleB p y
  ⟨f, selCost p y, match abductionResult p lim with
    | .explained _ e => if f then some (selCost p y - e.cost) else none
    | _ => none⟩

/-- The full pipeline: result plus audit of the untrusted proposal. -/
def abductionPipeline {W : Type} (p : Problem m k) (lim : Limits) (pol : AbductionPolicy W) :
    AbductionResult m k × Audit :=
  (abductionResult p lim, audit p lim pol)

/-- **End-to-end soundness of conditional assumption discovery.** -/
theorem end_to_end_abduction_sound {W : Type} (p : Problem m k) (lim : Limits)
    (pol : AbductionPolicy W) {r : PCSAssumptionDiscovery.Receipt m k} {e : Explanation}
    (h : (abductionPipeline p lim pol).1 = .explained r e) :
    r.problem = p ∧ r.limits = lim ∧ r.checker = CHECKER ∧ r.verify = true ∧
    r.outcome = .optimal e ∧
    -- the additional assumptions are explicit in the receipt …
    r.additionalAssumptions = e.indices.map p.hyp ∧
    -- … and in the conditional conclusion
    (∃ t : ConditionalTheorem p, t.extra = r.additionalAssumptions) ∧
    -- satisfiable, sufficient, lock-respecting and globally minimum-cost
    Feasible p e.selection ∧ Optimal p e.selection ∧
    (∀ z, Feasible p z → e.cost ≤ selCost p z) ∧ e.cost = selCost p e.selection ∧
    e.indices = idxSet k e.selection ∧
    -- exact number of distinct optimal catalog-index sets
    (∃ S : List (List Nat), S.Nodup ∧ e.count = S.length ∧
      ∀ I, I ∈ S ↔ ∃ y, Optimal p y ∧ idxSet k y = I) ∧
    -- exact mandatory / possible membership across all optimal explanations
    (∀ i, i ∈ e.mandatory ↔ i < k ∧ ∀ y, Optimal p y → i ∈ idxSet k y) ∧
    (∀ i, i ∈ e.possible ↔ i < k ∧ ∃ y, Optimal p y ∧ i ∈ idxSet k y) := by
  simp only [abductionPipeline, abductionResult] at h
  by_cases hv : p.validB = true
  · rw [if_pos hv] at h
    by_cases hver : (issue p lim).verify = true
    · rw [if_pos hver] at h
      split at h
      · rename_i e' ho
        cases h
        obtain ⟨_, hchk, hadd, hcl, hnv, hopt, hmin, hcost, hcnt, hmand, hposs⟩ :=
          abduction_result_replay_sound hver ho
        have hd : discover p lim = .optimal e := ho
        have hidx := (discover_optimal hd).2.2.2.2.2.2.2
        exact ⟨rfl, rfl, hchk, hver, ho, hadd, ⟨⟨_, hcl, hnv⟩, rfl⟩, hopt.1, hopt, hmin, hcost, hidx,
          hcnt, hmand, hposs⟩
      all_goals cases h
    · rw [if_neg hver] at h; cases h
  · rw [if_neg hv] at h; cases h

/-- The result is a function of the request alone: no proposal policy, weights or memory can
change it. -/
theorem abduction_policy_cannot_change_result {W W' : Type} (p : Problem m k) (lim : Limits)
    (pol : AbductionPolicy W) (pol' : AbductionPolicy W') :
    (abductionPipeline p lim pol).1 = (abductionPipeline p lim pol').1 := rfl

/-- **Audit soundness**: a proposal is reported feasible only if it is a satisfiable,
sufficient, lock-respecting selection, and its reported gap is its exact excess over the
certified optimum (never negative: no proposal beats the optimum). -/
theorem abduction_audit_gap_sound {W : Type} (p : Problem m k) (lim : Limits)
    (pol : AbductionPolicy W) {r : PCSAssumptionDiscovery.Receipt m k} {e : Explanation}
    (h : (abductionPipeline p lim pol).1 = .explained r e)
    (hf : (abductionPipeline p lim pol).2.feasible = true) :
    Feasible p (pol.propose pol.weights) ∧ e.cost ≤ selCost p (pol.propose pol.weights) ∧
      (abductionPipeline p lim pol).2.gap = some (selCost p (pol.propose pol.weights) - e.cost) := by
  have hfe : Feasible p (pol.propose pol.weights) := (feasibleB_iff _ _).1 hf
  obtain ⟨-, -, -, -, -, -, -, -, -, hmin, -⟩ := end_to_end_abduction_sound p lim pol h
  refine ⟨hfe, hmin _ hfe, ?_⟩
  have h1 : abductionResult p lim = .explained r e := h
  simp only [abductionPipeline, audit] at hf ⊢
  rw [h1]; simp [hf]

theorem abductionResult_inconsistent {p : Problem m k} {lim : Limits}
    (h : abductionResult p lim = .inconsistentAmbient) : discover p lim = .inconsistentAmbient := by
  simp only [abductionResult] at h
  by_cases hv : p.validB = true
  · rw [if_pos hv] at h
    by_cases hver : (issue p lim).verify = true
    · rw [if_pos hver] at h
      split at h <;> first | (rename_i ho; exact ho) | (rename_i r ho; exact ⟨r, ho⟩) | cases h
    · rw [if_neg hver] at h; cases h
  · rw [if_neg hv] at h; cases h

theorem abductionResult_none {p : Problem m k} {lim : Limits}
    (h : abductionResult p lim = .noExplanation) : discover p lim = .noExplanation := by
  simp only [abductionResult] at h
  by_cases hv : p.validB = true
  · rw [if_pos hv] at h
    by_cases hver : (issue p lim).verify = true
    · rw [if_pos hver] at h
      split at h <;> first | (rename_i ho; exact ho) | (rename_i r ho; exact ⟨r, ho⟩) | cases h
    · rw [if_neg hver] at h; cases h
  · rw [if_neg hv] at h; cases h

theorem abductionResult_limit {p : Problem m k} {lim : Limits}
    (h : abductionResult p lim = .resourceLimit) : ∃ r, discover p lim = .resourceLimit r := by
  simp only [abductionResult] at h
  by_cases hv : p.validB = true
  · rw [if_pos hv] at h
    by_cases hver : (issue p lim).verify = true
    · rw [if_pos hver] at h
      split at h <;> first | (rename_i ho; exact ho) | (rename_i r ho; exact ⟨r, ho⟩) | cases h
    · rw [if_neg hver] at h; cases h
  · rw [if_neg hv] at h; cases h

/-- **Separate unresolved/negative outcomes.**  An inconsistent ambient context, the absence of
any sufficient consistent explanation and budget exhaustion are reported as such and never as
an explanation: the first two are semantically certified, the third carries no claim. -/
theorem abduction_negative_outcomes_sound (p : Problem m k) (lim : Limits) :
    (abductionResult p lim = .inconsistentAmbient → ¬ AmbientConsistent p ∧ ∀ y, ¬ Feasible p y) ∧
    (abductionResult p lim = .noExplanation → AmbientConsistent p ∧ ∀ y, ¬ Feasible p y) ∧
    (abductionResult p lim = .resourceLimit → ∃ r, discover p lim = .resourceLimit r) :=
  ⟨fun h => discover_inconsistent (abductionResult_inconsistent h),
   fun h => discover_noExplanation (abductionResult_none h), abductionResult_limit⟩

end PCSEndToEnd
