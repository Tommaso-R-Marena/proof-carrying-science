import PCSEndToEnd
import PCSMathLanguage.Controls
import PCSAssumptionDiscovery.Controls

/-!
# Executed end-to-end controls

* A full proof-learning cycle through `pipeline`: an untrusted policy first proposes a wrong
  attempt, then a library macro plus raw JSON actions, while forging rewards/flags/receipts;
  the pipeline succeeds only on the closing attempt and the training label is verifier-derived.
* Forged success: the same forged claims on the invalid `A ∨ B → A` never yield success, for
  every policy, budget and library generation (instantiation of the general theorem).
* Ambiguity: a request whose selected index is out of range is rejected.
* A nontrivial conditional assumption-discovery cycle through `abductionPipeline`, with an
  audited (worse) policy proposal.
-/

namespace PCSEndToEnd.Controls

open PCSMathLanguage PCSEndToEnd
open PCSMathLanguage.Controls (swapDecl orDecl cfg orGoal_invalid)

/-- A library generation with one learned macro: `intro h0; constructor`. -/
def lib0 : MacroLib := [⟨"intro-split", [("intro", .str "h0"), ("constructor", .none)], 2⟩]

example : admittedLib lib0 = true := by decide +kernel

/-- An adversarial policy: attempt 0 is wrong; attempt 1 uses the macro; claims are forged. -/
def forger : Policy Nat where
  weights := 7
  ranking := [1, 0]
  memory := ["unverified: swap is trivial", "unverified: or-elim closes A ∨ B → A"]
  propose := fun _ _ _ _ k => if k = 0 then [.json "exact" (.str "h0")]
    else [.useMacro 0, .json "exact" (.str "h0.2"), .json "exact" (.str "h0.1")]
  claimedReward := fun _ _ _ => 1000
  claimedVerified := fun _ _ _ => true
  claimedReceipt := fun _ d _ => some ⟨d, [], "forged-checker"⟩

def swapRequest : Request := ⟨[swapDecl], 0⟩

def swapActions : List Act :=
  [.intro "h0", .constructor, .exact ⟨"h0", [true]⟩, .exact ⟨"h0", [false]⟩]

/-- The full cycle succeeds on attempt 1 with the expanded primitive actions; the training
example carries the verifier's label/reward/revision, not the forged ones. -/
example : (match pipeline cfg swapRequest forger ⟨3, 24⟩ lib0 with
    | .success s => some (s.attempt, s.receipt.actions, s.training.label, s.training.reward,
        s.training.checker)
    | _ => none) = some (1, swapActions, true, 100, "pcs-receiver-v1") := by decide +kernel

/-- With a budget of one attempt the run is unresolved (no fabricated success). -/
example : (match pipeline cfg swapRequest forger ⟨1, 24⟩ lib0 with
    | .unresolved n => some n | _ => none) = some 1 := by decide +kernel

/-- An out-of-range selected interpretation is rejected. -/
example : (match pipeline cfg ⟨[swapDecl], 1⟩ forger ⟨3, 24⟩ lib0 with
    | .rejected => true | _ => false) = true := by decide +kernel

theorem orDecl_false : ¬ DeclHolds orDecl := by
  intro h
  have := h [("b", ⟨.prop, True⟩), ("a", ⟨.prop, False⟩)] (True, (False, ()))
    ⟨_, rfl, _, rfl, rfl⟩
  simp [orDecl, rawDen, binDen, asProp, NEnv.lookup] at this


/-- **Forged success / reward control**: for `A ∨ B → A`, no policy — including the forger with
its fabricated reward 1000, `verified = true` and forged receipt — any budget or any library
generation reaches success. -/
theorem forged_success_impossible {W : Type} (p : Policy W) (b : Budget) (lib : MacroLib) :
    ∀ s, pipeline cfg ⟨[orDecl], 0⟩ p b lib ≠ .success s :=
  policy_cannot_manufacture_acceptance cfg _ orDecl rfl orDecl_false p b lib

/-- Concretely, the forger on `A ∨ B → A` with a large budget is unresolved. -/
example : (match pipeline cfg ⟨[orDecl], 0⟩ forger ⟨16, 24⟩ lib0 with
    | .unresolved _ => true | _ => false) = true := by decide +kernel

/-! ### A nontrivial conditional assumption-discovery cycle -/

open PCSOmega PCSDD PCSAssumptionDiscovery
open PCSAssumptionDiscovery.Controls (cycle)

/-- An untrusted proposal: select `H₀` and `H₂` (cost 4, feasible but not optimal). -/
def guesser : AbductionPolicy Unit := ⟨(), fun _ => [true, false, true, false, false]⟩

example : (abductionPipeline cycle DEFAULT_LIMITS guesser).2 = ⟨true, 4, some 1⟩ := by
  decide +kernel

theorem cycle_explained : (abductionPipeline cycle DEFAULT_LIMITS guesser).1 =
    .explained (issue cycle DEFAULT_LIMITS) ⟨3, 1, [3], [3], [false, false, false, true, false], [3]⟩ := by
  decide +kernel

/-- The end-to-end abduction theorem instantiated on the cycle: the explanation `{H₃}` is the
unique cheapest satisfiable sufficient assumption set, carried explicitly. -/
theorem cycle_end_to_end :
    ConditionalClaim cycle [PCSAssumptionDiscovery.Problem.hyp cycle 3] ∧
    Optimal cycle [false, false, false, true, false] := by
  obtain ⟨-, -, -, -, -, hadd, ⟨t, ht⟩, -, hopt, -⟩ :=
    end_to_end_abduction_sound cycle DEFAULT_LIMITS guesser cycle_explained
  refine ⟨?_, hopt⟩
  have := t.holds
  rw [ht, hadd] at this
  exact this

end PCSEndToEnd.Controls
