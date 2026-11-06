import Std

/-!
Finite exact integer stoichiometry only. Rates are arbitrary integers; these theorems
say nothing about a continuous trajectory, species units, or biochemical meaning.
Core integer algebra uses Lean's standard propext, reported below. There are no new
logical assumptions. Mismatched shapes are excluded by every matrix theorem.
-/
namespace ScientificConservation

def dot : List Int → List Int → Int
  | x :: xs, y :: ys => x * y + dot xs ys
  | _, _ => 0

def addVector : List Int → List Int → List Int
  | x :: xs, y :: ys => (x + y) :: addVector xs ys
  | _, _ => []

def scaleVector (rate : Int) (column : List Int) : List Int := column.map (rate * ·)

theorem dot_zero_vector (weights : List Int) :
    dot weights (List.replicate weights.length 0) = 0 := by
  induction weights with
  | nil => rfl
  | cons w ws ih =>
      change dot (w :: ws) (List.replicate (ws.length + 1) 0) = 0
      rw [List.replicate_succ]
      change w * 0 + dot ws (List.replicate ws.length 0) = 0
      rw [ih, Int.mul_zero]
      rfl

theorem add_vector_length (a b : List Int) (shape : a.length = b.length) :
    (addVector a b).length = a.length := by
  induction a generalizing b with
  | nil =>
      cases b with
      | nil => rfl
      | cons b bs => cases shape
  | cons a as ih =>
      cases b with
      | nil => cases shape
      | cons b bs =>
          change (addVector as bs).length + 1 = as.length + 1
          exact congrArg (fun n => n + 1) (ih bs (Nat.succ.inj shape))

theorem dot_add (weights a b : List Int)
    (ha : a.length = weights.length) (hb : b.length = weights.length) :
    dot weights (addVector a b) = dot weights a + dot weights b := by
  induction weights generalizing a b with
  | nil =>
      have anil : a = [] := List.length_eq_zero_iff.mp ha
      have bnil : b = [] := List.length_eq_zero_iff.mp hb
      subst a
      subst b
      rfl
  | cons w ws ih =>
      cases a with
      | nil => cases ha
      | cons a as =>
          cases b with
          | nil => cases hb
          | cons b bs =>
              have ha' : as.length = ws.length := Nat.succ.inj ha
              have hb' : bs.length = ws.length := Nat.succ.inj hb
              change w * (a + b) + dot ws (addVector as bs) =
                (w * a + dot ws as) + (w * b + dot ws bs)
              rw [ih as bs ha' hb', Int.mul_add]
              simp only [Int.add_assoc, Int.add_left_comm]

theorem dot_scale (weights column : List Int) (rate : Int)
    (shape : column.length = weights.length) :
    dot weights (scaleVector rate column) = rate * dot weights column := by
  induction weights generalizing column with
  | nil =>
      have cnil : column = [] := List.length_eq_zero_iff.mp shape
      subst column
      exact (Int.mul_zero rate).symm
  | cons w ws ih =>
      cases column with
      | nil => cases shape
      | cons c cs =>
          have shape' : cs.length = ws.length := Nat.succ.inj shape
          change w * (rate * c) + dot ws (scaleVector rate cs) =
            rate * (w * c + dot ws cs)
          rw [ih cs shape', Int.mul_add]
          rw [← Int.mul_assoc w rate c, Int.mul_comm w rate, Int.mul_assoc rate w c]

inductive ColumnsShape (size : Nat) : List (List Int) → Prop where
  | nil : ColumnsShape size []
  | cons : column.length = size → ColumnsShape size columns →
      ColumnsShape size (column :: columns)

inductive NullColumns (weights : List Int) : List (List Int) → Prop where
  | nil : NullColumns weights []
  | cons : column.length = weights.length → dot weights column = 0 →
      NullColumns weights columns → NullColumns weights (column :: columns)

def linearCombination (size : Nat) : List (List Int) → List Int → List Int
  | column :: columns, rate :: rates =>
      addVector (scaleVector rate column) (linearCombination size columns rates)
  | _, _ => List.replicate size 0

def weightedFlux (weights : List Int) : List (List Int) → List Int → Int
  | column :: columns, rate :: rates =>
      rate * dot weights column + weightedFlux weights columns rates
  | _, _ => 0

theorem null_columns_have_shape {weights : List Int} {columns : List (List Int)}
    (nulls : NullColumns weights columns) : ColumnsShape weights.length columns := by
  induction nulls with
  | nil => exact ColumnsShape.nil
  | cons shape _ _ ih => exact ColumnsShape.cons shape ih

theorem linear_combination_length {size : Nat} {columns : List (List Int)}
    (shapes : ColumnsShape size columns) (rates : List Int)
    (matching : rates.length = columns.length) :
    (linearCombination size columns rates).length = size := by
  induction shapes generalizing rates with
  | nil =>
      have rnil : rates = [] := List.length_eq_zero_iff.mp matching
      subst rates
      exact List.length_replicate
  | @cons columns column shape _ ih =>
      cases rates with
      | nil => cases matching
      | cons rate rest =>
          have matching' : rest.length = columns.length := Nat.succ.inj matching
          change (addVector (scaleVector rate column)
            (linearCombination size columns rest)).length = size
          have scale_length : (scaleVector rate column).length = size := by
            simpa only [scaleVector, List.length_map] using shape
          have tail_length := ih rest matching'
          rw [add_vector_length _ _ (scale_length.trans tail_length.symm)]
          exact scale_length

/-- Dotting a finite integer linear combination equals the weighted flux sum. -/
theorem dot_linear_combination (weights : List Int) {columns : List (List Int)}
    (shapes : ColumnsShape weights.length columns) (rates : List Int)
    (matching : rates.length = columns.length) :
    dot weights (linearCombination weights.length columns rates) =
      weightedFlux weights columns rates := by
  induction shapes generalizing rates with
  | nil =>
      have rnil : rates = [] := List.length_eq_zero_iff.mp matching
      subst rates
      exact dot_zero_vector weights
  | @cons columns column shape rest_shapes ih =>
      cases rates with
      | nil => cases matching
      | cons rate rest =>
          have matching' : rest.length = columns.length := Nat.succ.inj matching
          change dot weights (addVector (scaleVector rate column)
            (linearCombination weights.length columns rest)) =
            rate * dot weights column + weightedFlux weights columns rest
          have scale_length : (scaleVector rate column).length = weights.length := by
            simpa only [scaleVector, List.length_map] using shape
          rw [dot_add weights _ _ scale_length
            (linear_combination_length rest_shapes rest matching')]
          rw [dot_scale weights column rate shape, ih rest matching']

/-- A checked left-nullspace certificate cancels every matched integer rate vector. -/
theorem conserved_weighted_flux (weights : List Int) {columns : List (List Int)}
    (nulls : NullColumns weights columns) (rates : List Int)
    (matching : rates.length = columns.length) :
    weightedFlux weights columns rates = 0 := by
  induction nulls generalizing rates with
  | nil =>
      have rnil : rates = [] := List.length_eq_zero_iff.mp matching
      subst rates
      rfl
  | @cons column columns shape zero _ ih =>
      cases rates with
      | nil => cases matching
      | cons rate rest =>
          have matching' : rest.length = columns.length := Nat.succ.inj matching
          change rate * dot weights column + weightedFlux weights columns rest = 0
          rw [zero, ih rest matching', Int.mul_zero]
          exact Int.add_zero 0

/-- Exact finite stoichiometric conservation for arbitrary integer fluxes. -/
theorem conserved_linear_combination (weights : List Int) {columns : List (List Int)}
    (nulls : NullColumns weights columns) (rates : List Int)
    (matching : rates.length = columns.length) :
    dot weights (linearCombination weights.length columns rates) = 0 := by
  rw [dot_linear_combination weights (null_columns_have_shape nulls) rates matching]
  exact conserved_weighted_flux weights nulls rates matching

#print axioms dot_zero_vector
#print axioms add_vector_length
#print axioms dot_add
#print axioms dot_scale
#print axioms null_columns_have_shape
#print axioms linear_combination_length
#print axioms dot_linear_combination
#print axioms conserved_weighted_flux
#print axioms conserved_linear_combination

end ScientificConservation
