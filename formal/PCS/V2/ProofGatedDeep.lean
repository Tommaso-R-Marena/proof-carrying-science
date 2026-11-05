import PCS.V2.ProofGatedWide

/-!
# Arbitrary-depth, arbitrary-width exact integer ReLU networks

`DeepNet` has any number of hidden ReLU layers of any widths, followed by an affine
read-out. The evaluator is total: dot products truncate to the shorter vector, and the
`valid` predicate additionally enforces consistent shapes, a depth bound, a width bound
and a parameter-magnitude bound (`DeepArch`). All arithmetic is exact on `Int`.

Results:
* `predict_ofWide`: every `WideNet` is a depth-1 `DeepNet` computing the same function
  on **all** integers (so the earlier width-`n` results are a special case);
* `predict_deepen`: inserting an identity ReLU layer after the last hidden layer
  preserves the function on all integers (a depth-increasing, semantics-preserving
  self-modification), using that post-ReLU activations are nonnegative;
* the generic gate applies (`deepSpec`), and a checked chain on a genuinely
  two-hidden-layer network for the target `relu (|x| - 2)` (`deep_two_generations`).
-/

namespace PCS.V2.ProofGatedDeep

open PCS.V2.ProofGatedSelfImprovement (relu)
open PCS.V2.ProofGatedGeneric
open PCS.V2.ProofGatedWide (WideNet HiddenUnit hiddenSum unitOut)

structure DNeuron where
  weights : List Int
  bias : Int
  deriving Repr, DecidableEq

structure DeepNet where
  layers : List (List DNeuron)
  readout : DNeuron
  deriving Repr, DecidableEq

def dot : List Int → List Int → Int
  | w :: ws, v :: vs => w * v + dot ws vs
  | _, _ => 0

def layerEval (L : List DNeuron) (v : List Int) : List Int :=
  L.map fun n => relu (dot n.weights v + n.bias)

def hiddenEval : List (List DNeuron) → List Int → List Int
  | [], v => v
  | L :: Ls, v => hiddenEval Ls (layerEval L v)

def predict (m : DeepNet) (x : Int) : Int :=
  dot m.readout.weights (hiddenEval m.layers [x]) + m.readout.bias

/-! ## Architecture bound and validity -/

structure DeepArch where
  maxDepth : Nat
  maxWidth : Nat
  bound : Nat
  deriving Repr, DecidableEq

def inRange (B : Nat) (z : Int) : Bool := decide (-(B : Int) ≤ z ∧ z ≤ (B : Int))

def neuronOK (B inW : Nat) (n : DNeuron) : Bool :=
  decide (n.weights.length = inW) && n.weights.all (inRange B) && inRange B n.bias

def layersOK (B W : Nat) : Nat → List (List DNeuron) → Bool × Nat
  | inW, [] => (true, inW)
  | inW, L :: Ls =>
      let r := layersOK B W L.length Ls
      (decide (L.length ≤ W) && L.all (neuronOK B inW) && r.1, r.2)

/-- Shapes are consistent (input width 1), each layer has at most `maxWidth` units, there
are at most `maxDepth` hidden layers, and every parameter is within `bound`. -/
def valid (A : DeepArch) (m : DeepNet) : Bool :=
  let r := layersOK A.bound A.maxWidth 1 m.layers
  decide (m.layers.length ≤ A.maxDepth) && r.1 && neuronOK A.bound r.2 m.readout

def deepSpec (A : DeepArch) (target : Int → Int) (corpus : List Int) : GateSpec DeepNet :=
  ⟨predict, target, corpus, valid A⟩

/-! ## Embedding of width-`n` networks -/

def ofWide (m : WideNet) : DeepNet :=
  ⟨[m.hidden.map fun u => ⟨[u.w], u.b⟩], ⟨m.hidden.map (·.out), m.outBias⟩⟩

theorem dot_ofWide (hs : List HiddenUnit) (x : Int) :
    dot (hs.map (·.out)) (layerEval (hs.map fun u => ⟨[u.w], u.b⟩) [x]) = hiddenSum hs x := by
  induction hs with
  | nil => rfl
  | cons u us ih =>
      simp only [List.map_cons, layerEval] at ih ⊢
      simp only [dot, hiddenSum, unitOut, Int.add_zero, ih]

theorem predict_ofWide (m : WideNet) (x : Int) :
    predict (ofWide m) x = PCS.V2.ProofGatedWide.predict m x := by
  simp only [predict, ofWide, hiddenEval, PCS.V2.ProofGatedWide.predict, dot_ofWide]

/-! ## Depth increase by an identity ReLU layer -/

/-- Neuron `i` of the identity layer reads coordinate `i` (dot products truncate, so
trailing zeros are unnecessary). -/
def idLayer (n : Nat) : List DNeuron :=
  (List.range n).map fun i => ⟨List.replicate i 0 ++ [1], 0⟩

theorem dot_unit (i : Nat) (v : List Int) :
    dot (List.replicate i 0 ++ [1]) v = v.getD i 0 := by
  induction i generalizing v with
  | zero =>
      cases v with
      | nil => rfl
      | cons a as => simp [dot]
  | succ i ih =>
      cases v with
      | nil =>
          simp only [List.replicate_succ, List.cons_append]
          rfl
      | cons a as =>
          simp only [List.replicate_succ, List.cons_append, dot, Int.zero_mul, Int.zero_add]
          rw [ih]
          rfl

theorem range_map_getD (v : List Int) :
    (List.range v.length).map (fun i => v.getD i 0) = v := by
  induction v with
  | nil => rfl
  | cons a as ih =>
      rw [List.length_cons, List.range_succ_eq_map]
      simp only [List.map_cons, List.map_map]
      congr 1

theorem layerEval_idLayer (v : List Int) (h : ∀ a ∈ v, 0 ≤ a) :
    layerEval (idLayer v.length) v = v := by
  unfold layerEval idLayer
  rw [List.map_map]
  conv => rhs; rw [← range_map_getD v]
  apply List.map_congr_left
  intro i hi
  simp only [Function.comp, dot_unit, Int.add_zero, relu]
  have hlt : i < v.length := List.mem_range.mp hi
  have hmem : v.getD i 0 ∈ v := by
    rw [← List.getElem_eq_getD 0 (h := hlt)]; exact List.getElem_mem hlt
  exact Int.max_eq_right (h _ hmem)

theorem layerEval_nonneg (L : List DNeuron) (v : List Int) : ∀ a ∈ layerEval L v, 0 ≤ a := by
  intro a ha
  simp only [layerEval, List.mem_map] at ha
  obtain ⟨n, _, rfl⟩ := ha
  exact Int.le_max_left _ _

theorem layerEval_length (L : List DNeuron) (v : List Int) :
    (layerEval L v).length = L.length := by simp [layerEval]

theorem hiddenEval_append (Ls Ms : List (List DNeuron)) (v : List Int) :
    hiddenEval (Ls ++ Ms) v = hiddenEval Ms (hiddenEval Ls v) := by
  induction Ls generalizing v with
  | nil => rfl
  | cons L Ls ih => exact ih _

/-- **Depth-increasing, semantics-preserving transform**: appending an identity layer of
the right width after a nonempty stack of hidden layers changes nothing, on every input. -/
theorem predict_deepen (Ls : List (List DNeuron)) (L : List DNeuron) (r : DNeuron) (x : Int) :
    predict ⟨Ls ++ [L, idLayer L.length], r⟩ x = predict ⟨Ls ++ [L], r⟩ x := by
  simp only [predict]
  congr 1
  rw [show Ls ++ [L, idLayer L.length] = (Ls ++ [L]) ++ [idLayer L.length] by simp,
    hiddenEval_append (Ls ++ [L]) [idLayer L.length]]
  simp only [hiddenEval]
  have hlen : (hiddenEval (Ls ++ [L]) [x]).length = L.length := by
    rw [hiddenEval_append]; simp [hiddenEval, layerEval_length]
  have hnn : ∀ a ∈ hiddenEval (Ls ++ [L]) [x], 0 ≤ a := by
    rw [hiddenEval_append]; simp only [hiddenEval]; exact layerEval_nonneg _ _
  rw [← hlen, layerEval_idLayer _ hnn]

/-- Every width-`n` network has an exactly equivalent depth-2 network. -/
theorem predict_deepen_ofWide (m : WideNet) (x : Int) :
    predict ⟨[m.hidden.map fun u => ⟨[u.w], u.b⟩, idLayer m.hidden.length],
      ⟨m.hidden.map (·.out), m.outBias⟩⟩ x = PCS.V2.ProofGatedWide.predict m x := by
  have := predict_deepen [] (m.hidden.map fun u => ⟨[u.w], u.b⟩)
    ⟨m.hidden.map (·.out), m.outBias⟩ x
  simp only [List.nil_append, List.length_map] at this
  rw [this]
  exact predict_ofWide m x

/-! ## A checked chain on a genuinely two-hidden-layer network -/

def deepArch : DeepArch := ⟨3, 4, 8⟩
def corpusD : List Int := [-4, -3, -2, -1, 0, 1, 2, 3, 4]
/-- `relu (|x| - 2)`, with `|x| = relu x + relu (-x)`. -/
def targetD (x : Int) : Int := relu (relu x + relu (-x) - 2)
def specD : GateSpec DeepNet := deepSpec deepArch targetD corpusD

/-- First layer `[relu x, relu (-x)]`. -/
def layer1 : List DNeuron := [⟨[1], 0⟩, ⟨[-1], 0⟩]

def dZero : DeepNet := ⟨[layer1, [⟨[0, 0], 0⟩]], ⟨[0], 0⟩⟩
def dHalf : DeepNet := ⟨[layer1, [⟨[1, 0], -2⟩]], ⟨[1], 0⟩⟩
def dFull : DeepNet := ⟨[layer1, [⟨[1, 1], -2⟩]], ⟨[1], 0⟩⟩

theorem deep_step1 : accept specD dZero dHalf = true := by decide
theorem deep_step2 : accept specD dHalf dFull = true := by decide
theorem deep_losses : loss specD dZero = 6 ∧ loss specD dHalf = 3 ∧ loss specD dFull = 0 := by
  decide

theorem deep_two_generations : CertifiedTrace specD 2 dZero dFull :=
  .extend (.extend (.zero dZero) deep_step1) deep_step2

theorem dFull_exact (x : Int) : predict dFull x = targetD x := by
  simp only [predict, dFull, layer1, hiddenEval, layerEval, List.map, dot, targetD, relu]
  omega

/-- Ill-shaped candidate (second-layer neuron reads three inputs from a width-2 layer):
rejected even though it computes the target exactly. -/
def dIllShaped : DeepNet := ⟨[layer1, [⟨[1, 1, 5], -2⟩]], ⟨[1], 0⟩⟩
theorem dIllShaped_semantics (x : Int) : predict dIllShaped x = targetD x := by
  rw [← dFull_exact]; rfl
theorem dIllShaped_blocked : accept specD dHalf dIllShaped = false := by decide

/-- Too deep: four hidden layers exceed `maxDepth = 3`. -/
def dTooDeep : DeepNet :=
  ⟨[layer1, [⟨[1, 1], -2⟩], idLayer 1, idLayer 1], ⟨[1], 0⟩⟩
theorem dTooDeep_blocked : accept specD dHalf dTooDeep = false := by decide

/-- A depth-3 version of `dFull` obtained by `predict_deepen` is accepted exactly like
`dFull` (validity holds and predictions agree on all inputs). -/
theorem deepened_full_accepted :
    accept specD dHalf ⟨[layer1, [⟨[1, 1], -2⟩], idLayer 1], ⟨[1], 0⟩⟩ = true := by
  decide

end PCS.V2.ProofGatedDeep
