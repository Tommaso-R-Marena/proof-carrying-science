import PCSReferenceCertificates.DeMorgan
import PCSReferenceCertificates.Choices
import PCSReferenceCertificates.DenseControl
import PCSDecisionDiagram.Intervention
import PCSDecisionDiagram.Validate

/-!
# Executed controls for the conditional checker and the intervention planner

Small examples are closed by ordinary kernel-checked `decide` or `decide +kernel` (no
`native_decide`, no `Lean.ofReduceBool`; `+kernel` skips the slow elaborator pre-evaluation and
leaves the check to the kernel), combined
with the general theorems where a semantic statement is required. The three larger controls use
ordinary-kernel computation certificates proved equivalent to the original computations.  The 24-variable controls are
evaluated through the bounded symbolic pipeline (diagram compilation and the Bellman pass), never
by enumerating `2^24` assignments.
-/

namespace PCSDD.Controls

open PCSOmega PCSDD

/-- Variable `i` of an `n`-variable formula. -/
def vr {n : Nat} [NeZero n] (i : Nat) : BForm n := .atom ⟨i % n, Nat.mod_lt _ (Nat.pos_of_neZero n)⟩

/-- Balanced tree over leaves `lo … lo+len-1` (keeps formula depth within the protocol bound). -/
def balR {n : Nat} (leaf : Nat → BForm n) (op : BForm n → BForm n → BForm n) : Nat → Nat → Nat → BForm n
  | 0, lo, _ => leaf lo
  | f + 1, lo, len =>
      if len ≤ 1 then leaf lo else op (balR leaf op f lo (len / 2)) (balR leaf op f (lo + len / 2) (len - len / 2))

/-! ## Conditional controls -/

def A2 : BForm 2 := vr 0
def B2 : BForm 2 := vr 1

/-- `TRUE` vs `B` under `A` and `A → B`: equivalent. -/
def tAB : CTask 2 := ⟨.tt, B2, [A2, .imp A2 B2]⟩
example : (check tAB DEFAULT_LIMITS).decision = .equivalentUnderAssumptions := by decide +kernel
example : (check tAB DEFAULT_LIMITS).contextExample = some [true, true] := by decide +kernel
theorem tAB_equivalent : ∀ ρ, allEval tAB.assumptions ρ = true → tAB.source.eval ρ = tAB.candidate.eval ρ :=
  (check_equivalent tAB DEFAULT_LIMITS (by decide +kernel)).2.2

/-- With `A` removed: disagreement at the least assignment satisfying `A → B` with `B` false. -/
def tAB' : CTask 2 := ⟨.tt, B2, [.imp A2 B2]⟩
example : (check tAB' DEFAULT_LIMITS).decision = .counterexample := by decide +kernel
example : (check tAB' DEFAULT_LIMITS).counterexample.map (·.assignment) = some [false, false] := by decide +kernel

/-- Opposite premises with a dense, never-compiled query. -/
def dense4 : BForm 4 :=
  .or (.and (vr 0) (vr 2)) (.or (.and (vr 1) (vr 3)) (.imp (.not (vr 0)) (.and (vr 3) (.not (vr 1)))))
def tOpp : CTask 4 := ⟨dense4, .not dense4, [vr 0, .not (vr 0)]⟩
example : (check tOpp DEFAULT_LIMITS).decision = .inconsistentAssumptions := by decide +kernel
example : (check tOpp DEFAULT_LIMITS).unsatCore = some [0, 1] := by decide +kernel
example : (check tOpp DEFAULT_LIMITS).diagram.map (·.source) = some none := by decide +kernel
example : (check tOpp DEFAULT_LIMITS).coreWitnesses = some [(0, [false, false, false, false]),
    (1, [true, false, false, false])] := by decide +kernel
theorem tOpp_inconsistent : ∀ ρ, allEval tOpp.assumptions ρ = false :=
  (check_inconsistent tOpp DEFAULT_LIMITS (by decide +kernel)).1

/-- 24-variable De Morgan (balanced, depth 6), decided symbolically. -/
def dm24 : CTask 24 := ⟨.not (balR vr .and 6 0 24), balR (fun i => .not (vr i)) .or 6 0 24, []⟩
set_option maxRecDepth 100000 in
set_option maxHeartbeats 0 in
theorem dm24_decision : (check dm24 DEFAULT_LIMITS).decision = .equivalentUnderAssumptions := by
  exact equivalent_from_certificates (t := dm24) (by rfl) StagedControl.c0 StagedControl.c48 StagedControl.hx StagedControl.ha (by decide)
theorem dm24_equivalent : ∀ ρ, dm24.source.eval ρ = dm24.candidate.eval ρ := fun ρ =>
  (check_equivalent dm24 DEFAULT_LIMITS dm24_decision).2.2 ρ (by simp [allEval, dm24])

/-- A dense ordering (`x_i ∧ x_{i+6}`) exhausts a small node budget: unresolved. -/
def dense12 : BForm 12 := balR (fun i => .and (vr i) (vr (i + 6))) .or 4 0 6
def tDense : CTask 12 := ⟨dense12, .ff, []⟩
def smallLim : Limits := ⟨40, 100000⟩
example : (check tDense smallLim).decision = .resourceLimit := by decide +kernel
example : (check tDense smallLim).limitReached = some .nodes := by decide +kernel
set_option maxRecDepth 100000 in
set_option maxHeartbeats 0 in
example : (check tDense DEFAULT_LIMITS).decision = .counterexample := by
  exact StagedDense.result
theorem tDense_nothing_claimed :
    (check tDense smallLim).counterexample = none ∧ (check tDense smallLim).diagram = none :=
  have h := check_resource_limit tDense smallLim (by decide +kernel)
  ⟨h.2.1, h.2.2.2.2.1⟩

/-- `n = 0` constants. -/
example : (check (⟨.tt, .tt, []⟩ : CTask 0) DEFAULT_LIMITS).decision = .equivalentUnderAssumptions := by decide +kernel
example : (check (⟨.tt, .ff, []⟩ : CTask 0) DEFAULT_LIMITS).counterexample.map (·.assignment) = some [] := by
  decide +kernel

/-! ## Intervention controls -/

/-- Summary of a planner run used by the controls. -/
structure ISum where
  decision : IDecision
  minimumCost : Option Nat
  optimalCount : Option Nat
  assignment : Option (List Bool)
  mandatory : Option (List Nat)
  possible : Option (List Nat)
  deriving DecidableEq, Repr

def isum {n : Nat} (t : ITask n) (lim : Limits := DEFAULT_LIMITS) : Option ISum :=
  match plan t lim with
  | .ok r => some ⟨r.decision, r.minimumCost, r.optimalCount, r.assignment, r.mandatory, r.possible⟩
  | .error _ => none

def orAB : CTask 2 := ⟨.or A2 B2, .ff, []⟩

/-- Weighted `A ∨ B`, baseline false/false, costs 3/1: minimum 1, flip `B` is mandatory. -/
def wAB : ITask 2 := ⟨orAB, [false, false], [3, 1], []⟩
example : isum wAB = some ⟨.optimalPlan, some 1, some 1, some [false, true], some [1], some [1]⟩ := by decide +kernel

/-- Tied costs 1/1: count 2, no mandatory flip, both flips possible, False-first tie break. -/
def tieAB : ITask 2 := ⟨orAB, [false, false], [1, 1], []⟩
example : isum tieAB = some ⟨.optimalPlan, some 1, some 2, some [false, true], some [], some [0, 1]⟩ := by decide +kernel

/-- Lock `B`: flipping `A` becomes mandatory. -/
def lockB : ITask 2 := ⟨orAB, [false, false], [3, 1], [1]⟩
example : isum lockB = some ⟨.optimalPlan, some 3, some 1, some [true, false], some [0], some [0]⟩ := by decide +kernel

/-- Lock both: no feasible plan (premises are consistent). -/
def lockBoth : ITask 2 := ⟨orAB, [false, false], [3, 1], [0, 1]⟩
example : isum lockBoth = some ⟨.noFeasiblePlan, none, none, none, none, none⟩ := by decide +kernel
theorem lockBoth_infeasible : ∀ a, ¬ IFeasible lockBoth a := by
  obtain ⟨r, hr⟩ := plan_ok (t := lockBoth) (lim := DEFAULT_LIMITS) (by decide +kernel) (by decide +kernel)
  have hd : r.decision = .noFeasiblePlan := by
    have : isum lockBoth = some ⟨r.decision, r.minimumCost, r.optimalCount, r.assignment, r.mandatory,
        r.possible⟩ := by simp [isum, hr]
    have h2 : isum lockBoth = some ⟨.noFeasiblePlan, none, none, none, none, none⟩ := by decide +kernel
    have e := congrArg (Option.map ISum.decision) (this.symm.trans h2)
    simpa using e
  exact (plan_no_feasible (by decide +kernel) hr hd).2.1

/-- `A ∨ (B ∧ ¬B)` with a true `B` baseline: `B` is skipped and keeps its baseline. -/
def skipB : ITask 2 := ⟨⟨.or A2 (.and B2 (.not B2)), .ff, []⟩, [false, true], [5, 7], []⟩
example : isum skipB = some ⟨.optimalPlan, some 5, some 1, some [true, true], some [0], some [0]⟩ := by decide +kernel

theorem isum_of_plan {t : ITask n} {lim : Limits} {r : IReceipt n} {s : ISum}
    (h : plan t lim = .ok r)
    (hs : (⟨r.decision, r.minimumCost, r.optimalCount, r.assignment, r.mandatory, r.possible⟩ : ISum) = s) :
    isum t lim = some s := by
  unfold isum
  rw [h]
  dsimp only
  rw [hs]

/-- Twelve disjoint two-variable choices over 24 variables: minimum 12, count 4096. -/
def pairs12 : BForm 24 := balR (fun k => .or (vr (2 * k)) (vr (2 * k + 1))) .and 5 0 12
def choices12 : ITask 24 :=
  ⟨⟨pairs12, .ff, []⟩, List.replicate 24 false, List.replicate 24 1, []⟩
set_option maxRecDepth 100000 in
set_option maxHeartbeats 0 in
theorem choices12_summary : isum choices12 = some ⟨.optimalPlan, some 12, some 4096,
    some ((List.replicate 12 [false, true]).flatten), some [],
    some (List.range 24)⟩ := by
  exact isum_of_plan (t := choices12) StagedChoices.result (by rfl)

/-- `n = 0`: target `TRUE` has the empty optimal plan; target `FALSE` is infeasible. -/
def zeroT : ITask 0 := ⟨⟨.tt, .ff, []⟩, [], [], []⟩
def zeroF : ITask 0 := ⟨⟨.ff, .ff, []⟩, [], [], []⟩
example : isum zeroT = some ⟨.optimalPlan, some 0, some 1, some [], some [], some []⟩ := by decide +kernel
example : isum zeroF = some ⟨.noFeasiblePlan, none, none, none, none, none⟩ := by decide +kernel

/-- Inconsistent context (premises `A`, `¬A`) is reported separately from an infeasible goal
(premise `A`, target `¬A`). -/
def inconsistentCtx : ITask 2 := ⟨⟨B2, .ff, [A2, .not A2]⟩, [false, false], [1, 1], []⟩
def infeasibleGoal : ITask 2 := ⟨⟨.not A2, .ff, [A2]⟩, [false, false], [1, 1], []⟩
example : isum inconsistentCtx = some ⟨.inconsistentAssumptions, none, none, none, none, none⟩ := by decide +kernel
example : isum infeasibleGoal = some ⟨.noFeasiblePlan, none, none, none, none, none⟩ := by decide +kernel

/-! ## Runtime rejection controls -/

/-- Invalid ordering, forward child identifier, redundant node, duplicate triple. -/
example : validB 2 #[⟨0, 0, 1⟩] = true := by decide +kernel
example : validB 2 #[⟨1, 0, 1⟩, ⟨1, 0, 2⟩] = false := by decide +kernel
example : validB 2 #[⟨0, 0, 3⟩] = false := by decide +kernel
example : validB 2 #[⟨0, 1, 1⟩] = false := by decide +kernel
example : validB 2 #[⟨0, 0, 1⟩, ⟨0, 0, 1⟩] = false := by decide +kernel
example : validB 1 #[⟨1, 0, 1⟩] = false := by decide +kernel

/-- The guarded Bellman entry rejects a zero cost and an out-of-range root. -/
def pricesZero : Prices := ⟨fun _ => false, fun i => if i = 0 then 0 else 1, fun _ => false⟩
example : (bellmanChecked 1 #[⟨0, 0, 1⟩] pricesZero 2).toOption.isNone = true := by decide +kernel
def pricesOne : Prices := ⟨fun _ => false, fun _ => 1, fun _ => false⟩
example : (bellmanChecked 1 #[⟨0, 0, 1⟩] pricesOne 3).toOption.isNone = true := by decide +kernel
example : (bellmanChecked 1 #[⟨0, 0, 1⟩] pricesOne 2).toOption.map (·.1) = some (some ⟨1, 1, 1, 1⟩) := by
  decide +kernel

/-- Zero costs, a non-`FALSE` candidate and unsorted locks are rejected by task validation. -/
example : isum (⟨orAB, [false, false], [0, 1], []⟩ : ITask 2) = none := by decide +kernel
example : isum (⟨⟨.or A2 B2, .tt, []⟩, [false, false], [1, 1], []⟩ : ITask 2) = none := by decide +kernel
example : isum (⟨orAB, [false, false], [1, 1], [1, 0]⟩ : ITask 2) = none := by decide +kernel
example : isum (⟨orAB, [false, false], [1, 1000001], []⟩ : ITask 2) = none := by decide +kernel
example : isum wAB ⟨0, 1⟩ = none := by decide +kernel

/-- Forged counts, masks and costs are rejected by replay. -/
def wABr : IReceipt 2 := match plan wAB DEFAULT_LIMITS with
  | .ok r => r
  | .error _ => IReceipt.bare wAB DEFAULT_LIMITS (check wAB.problem DEFAULT_LIMITS) .resourceLimit
example : wABr.verify = true := by decide +kernel
example : ({ wABr with optimalCount := some 2 } : IReceipt 2).verify = false := by decide +kernel
example : ({ wABr with mandatory := some [] } : IReceipt 2).verify = false := by decide +kernel
example : ({ wABr with possible := some [0, 1] } : IReceipt 2).verify = false := by decide +kernel
example : ({ wABr with minimumCost := some 0 } : IReceipt 2).verify = false := by decide +kernel
example : ({ wABr with assignment := some [true, false] } : IReceipt 2).verify = false := by decide +kernel
example : ({ wABr with pcsAuthority := true } : IReceipt 2).verify = false := by decide +kernel
example : ({ wABr with limits := ⟨4096, 99999⟩ } : IReceipt 2).verify = false := by decide +kernel

/-- Exhausted work: a resource-limit receipt carries no plan, and a forged optimal receipt for the
same task and limits is rejected. -/
def denseTask : ITask 12 := ⟨tDense, List.replicate 12 false, List.replicate 12 1, []⟩
example : isum denseTask smallLim = some ⟨.resourceLimit, none, none, none, none, none⟩ := by decide +kernel
def denseR : IReceipt 12 := match plan denseTask smallLim with
  | .ok r => r
  | .error _ => IReceipt.bare denseTask smallLim (check tDense smallLim) .optimalPlan
example : ({ denseR with decision := .optimalPlan, minimumCost := some 2 } : IReceipt 12).verify = false := by
  decide +kernel

/-- Audit: an infeasible cheap proposal gets no gap; the optimal proposal has gap `0`; a feasible
non-optimal proposal has a positive gap. -/
def gapOf {n : Nat} (t : ITask n) (a : List Bool) : Option (Bool × Option Int) :=
  match auditProposal t a DEFAULT_LIMITS with
  | .ok au => some (au.feasible, au.gap)
  | .error _ => none
example : gapOf wAB [false, false] = some (false, none) := by decide +kernel
example : gapOf wAB [false, true] = some (true, some 0) := by decide +kernel
example : gapOf wAB [true, false] = some (true, some 2) := by decide +kernel
example : gapOf lockBoth [true, true] = some (false, none) := by decide +kernel

end PCSDD.Controls
