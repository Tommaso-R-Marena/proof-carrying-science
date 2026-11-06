import Std

/-!
A closed integer-polynomial counterexample to extrapolating equality from finitely
many samples. This file uses exact integers only. If a numerical experiment samples
r = i/100 and r = 1/2, the corresponding integer coordinate is x = 100*r.
There is no refinement theorem connecting this integer specification to Python
floating point evaluation, numerical tolerance, or learned-model execution.
-/
namespace ScientificSampling

def exactProduct : List Int → Int
  | [] => 1
  | x :: xs => x * exactProduct xs

/-- The twelve integer sample coordinates are explicit and closed. -/
def sampleCoordinates : List Int := [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

/-- An integer polynomial of degree twelve, the product of its twelve factors. -/
def ghost (x : Int) : Int := exactProduct (sampleCoordinates.map (fun i => x - i))

/-- Every chosen sample vanishes under exact kernel reduction. -/
theorem sampling_zeros :
    sampleCoordinates.map ghost = List.replicate 12 0 := by
  decide

/-- Agreement at the twelve samples does not imply agreement at coordinate fifty. -/
theorem ghost_fifty_nonzero : ghost 50 ≠ 0 := by
  decide

/-- A closed witness refutes the implication from sample agreement to global equality. -/
theorem sample_agreement_does_not_imply_global_equality :
    ∃ f g : Int → Int,
      sampleCoordinates.map f = sampleCoordinates.map g ∧
      ¬ (∀ x, f x = g x) := by
  refine ⟨ghost, (fun _ => 0), ?_, ?_⟩
  · decide
  · intro globallyEqual
    exact ghost_fifty_nonzero (globallyEqual 50)

#print axioms sampling_zeros
#print axioms ghost_fifty_nonzero
#print axioms sample_agreement_does_not_imply_global_equality

end ScientificSampling
