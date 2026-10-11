import PCSAssumptionDiscovery.Receipt

/-!
# Executed controls for exact assumption discovery

All closed by ordinary kernel evaluation (`decide +kernel`); semantic statements are obtained
by instantiating the general theorems.
-/

namespace PCSAssumptionDiscovery.Controls

open PCSOmega PCSDD PCSAssumptionDiscovery Cegar

def a : BForm 2 := .atom ⟨0, by decide⟩
def b : BForm 2 := .atom ⟨1, by decide⟩

/-! ### Tied cheapest hypotheses and the exact optimal count -/

/-- Target `a ∧ b`; catalog `H₀ = a` (1), `H₁ = b` (1), `H₂ = a ∧ b` (2).
Two optimal explanations of cost 2: `{H₂}` and `{H₀, H₁}`. -/
def tie : Problem 2 3 := ⟨.tt, .and a b, [a, b, .and a b], [1, 1, 2], [], []⟩

example : discover tie DEFAULT_LIMITS = .optimal
    ⟨2, 2, [], [0, 1, 2], [false, false, true], [2]⟩ := by decide +kernel

theorem tie_count : ∃ S : List (List Nat), S.Nodup ∧ S.length = 2 ∧
    ∀ I, I ∈ S ↔ ∃ y, Optimal tie y ∧ idxSet 3 y = I := by
  obtain ⟨S, h1, h2, h3⟩ := abduction_optimal_count (p := tie) (lim := DEFAULT_LIMITS)
    (e := ⟨2, 2, [], [0, 1, 2], [false, false, true], [2]⟩) (by decide +kernel)
  exact ⟨S, h1, h2.symm, h3⟩

/-- CEGAR with the complete enumeration oracle agrees. -/
example : (match run (ofProblem tie) (boolOracle tie) (2 ^ 3 + 1) [] with
    | .optimal y _ _ => some y | _ => none) = some [false, false, true] := by decide +kernel

/-- Collecting all optima through the checker returns both explanations. -/
example : (match run (ofProblem tie) (boolOracle tie) 9 [] with
    | .optimal y _ cls => some (collect (ofProblem tie) (boolOracle tie) cls (cost (ofProblem tie) y))
    | _ => none) = some [[false, false, true], [true, true, false]] := by decide +kernel

/-! ### Consistent versus inconsistent explanations -/

/-- `H₀ = a ∧ ¬a` is cheaper and vacuously sufficient but inconsistent; it must not be reported. -/
def incons : Problem 2 2 := ⟨.tt, a, [.and a (.not a), a], [1, 5], [], []⟩

example : discover incons DEFAULT_LIMITS = .optimal ⟨5, 1, [1], [1], [false, true], [1]⟩ := by
  decide +kernel

example : (match run (ofProblem incons) (boolOracle incons) 5 [] with
    | .optimal y _ cls => some (y, cls) | _ => none) =
    some ([false, true], [⟨[], [0]⟩, ⟨[0, 1], []⟩]) := by decide +kernel

/-! ### Inconsistent ambient context -/

def badAmbient : Problem 2 1 := ⟨.and a (.not a), b, [b], [1], [], []⟩

example : discover badAmbient DEFAULT_LIMITS = .inconsistentAmbient := by decide +kernel

/-! ### Bad worlds -/

/-- An unavoidable bad world: `a = false, b = true` satisfies every hypothesis but not `a`. -/
def unavoidable : Problem 2 2 := ⟨.tt, a, [.tt, b], [1, 1], [], []⟩

example : discover unavoidable DEFAULT_LIMITS = .noExplanation := by decide +kernel
theorem unavoidable_none : ∀ y, ¬ Feasible unavoidable y :=
  (discover_noExplanation (lim := DEFAULT_LIMITS) (by decide +kernel)).2
example : (match run (ofProblem unavoidable) (boolOracle unavoidable) 5 [] with
    | .noExplanation cls => some cls | _ => none) = some [⟨[], []⟩, ⟨[1], []⟩] := by decide +kernel

/-- A bad world falsifying every catalog hypothesis yields the clause `{H₀}`. -/
def falsifyAll : Problem 2 1 := ⟨.tt, a, [a], [3], [], []⟩

example : discover falsifyAll DEFAULT_LIMITS = .optimal ⟨3, 1, [0], [0], [true], [0]⟩ := by
  decide +kernel

/-! ### Locks -/

/-- Locking `H₂` out leaves `{H₀, H₁}` as the unique optimum. -/
def tieLocked : Problem 2 3 := { tie with lockedOut := [2] }

example : discover tieLocked DEFAULT_LIMITS = .optimal
    ⟨2, 1, [0, 1], [0, 1], [true, true, false], [0, 1]⟩ := by decide +kernel

/-! ### A nontrivial discovery cycle: receipt, replay and conditional conclusion -/

def x0 : BForm 4 := .atom ⟨0, by decide⟩
def x1 : BForm 4 := .atom ⟨1, by decide⟩
def x2 : BForm 4 := .atom ⟨2, by decide⟩
def x3 : BForm 4 := .atom ⟨3, by decide⟩

/-- Ambient `x0 → x1`; target `x1 ∧ (x2 ∨ x3)`; five candidate hypotheses with costs. -/
def cycle : Problem 4 5 :=
  ⟨.imp x0 x1, .and x1 (.or x2 x3),
   [x0, x1, x2, .and x0 x3, .and x1 (.and x2 x3)], [2, 3, 2, 3, 6], [], []⟩

def cycleReceipt : Receipt 4 5 := issue cycle DEFAULT_LIMITS

theorem cycle_verifies : cycleReceipt.verify = true := issue_verify _ _
example : cycleReceipt.outcome = .optimal ⟨3, 1, [3], [3], [false, false, false, true, false], [3]⟩ := by
  decide +kernel

/-- The verified receipt yields the explicit conditional conclusion. -/
theorem cycle_conditional :
    ConditionalClaim cycle cycleReceipt.additionalAssumptions ∧
      NonVacuous cycle cycleReceipt.additionalAssumptions := by
  have h := abduction_result_replay_sound (r := cycleReceipt) cycle_verifies
    (e := ⟨3, 1, [3], [3], [false, false, false, true, false], [3]⟩) (by decide +kernel)
  exact ⟨h.2.2.2.1, h.2.2.2.2.1⟩

/-- Tampering with the additional assumptions is rejected. -/
example : ({ cycleReceipt with additionalAssumptions := [] } : Receipt 4 5).verify = false := by
  decide +kernel

/-- CEGAR on the same problem returns the same explanation. -/
example : (match run (ofProblem cycle) (boolOracle cycle) 33 [] with
    | .optimal y _ _ => some y | _ => none) = some [false, false, false, true, false] := by
  decide +kernel

end PCSAssumptionDiscovery.Controls
