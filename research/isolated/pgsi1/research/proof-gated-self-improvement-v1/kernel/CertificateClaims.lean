import IntegerAffine

namespace PCS.Research.IntegerAffine

inductive Claim where
  | equal (a b : Net) (rows : List Row)
  | notEqual (a b : Net) (x : Int)
  | preserves (a b t : Net) (rows : List Row)
  | nonvacuous (a b t : Net) (rows : List Row) (witness : Int)
  | notPreserves (a b t : Net) (x : Int)
  | noCorrect (a t : Net) (rows : List Row)
  | hasCorrect (a t : Net) (witness : Int)
  | maximum (a b : Net) (rows : List Row) (low high : Int) (error : Nat) (peak : Int)
  deriving Repr

def checkClaim : Claim → Bool
  | .equal a b rows => acceptEqual a b rows
  | .notEqual a b x => refutesEqual a b x
  | .preserves a b t rows => acceptPreserves a b t rows
  | .nonvacuous a b t rows x => acceptNonvacuous a b t rows x
  | .notPreserves a b t x => refutesPreserves a b t x
  | .noCorrect a t rows => acceptNoCorrect a t rows
  | .hasCorrect a t x => decide (predict a x = predict t x)
  | .maximum a b rows l h m peak => acceptMaximum a b rows l h m peak

def Meaning : Claim → Prop
  | .equal a b _ => ∀ x : Int, predict a x = predict b x
  | .notEqual a b _ => ¬ (∀ x : Int, predict a x = predict b x)
  | .preserves a b t _ => ∀ x : Int, predict a x = predict t x → predict b x = predict t x
  | .nonvacuous a b t _ witness =>
    (∀ x : Int, predict a x = predict t x → predict b x = predict t x) ∧
    predict a witness = predict t witness
  | .notPreserves a b t _ => ¬ (∀ x : Int, predict a x = predict t x → predict b x = predict t x)
  | .noCorrect a t _ => ∀ x : Int, predict a x ≠ predict t x
  | .hasCorrect a t x => predict a x = predict t x
  | .maximum a b _ l h m peak =>
    (∀ x : Int, l ≤ x → x ≤ h → (predict a x - predict b x).natAbs ≤ m) ∧
    l ≤ peak ∧ peak ≤ h ∧ (predict a peak - predict b peak).natAbs = m

theorem checkClaim_sound (c : Claim) (h : checkClaim c = true) : Meaning c := by
  cases c with
  | equal a b rows => exact acceptEqual_sound a b rows h
  | notEqual a b x => exact refutesEqual_sound a b x h
  | preserves a b t rows => exact acceptPreserves_sound a b t rows h
  | nonvacuous a b t rows x => exact acceptNonvacuous_sound a b t rows x h
  | notPreserves a b t x => exact refutesPreserves_sound a b t x h
  | noCorrect a t rows => exact acceptNoCorrect_sound a t rows h
  | hasCorrect a t x =>
    change predict a x = predict t x
    exact of_decide_eq_true h
  | maximum a b rows l u m x => exact acceptMaximum_sound a b rows l u m x h

theorem checkBatch_sound (claims : List Claim) (h : claims.all checkClaim = true) :
    ∀ c ∈ claims, Meaning c := by
  intro c hc
  exact checkClaim_sound c (List.all_eq_true.mp h c hc)

end PCS.Research.IntegerAffine
