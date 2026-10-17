import Lean

/-!
# PCS Proof-Gated Self-Improvement (finite-domain prototype)

A bounded neuron, frozen examples and exact loss. The acceptance theorem
concerns only this formal policy; it does not prove out-of-domain improvement
or the reliability of any external deployment wrapper.
-/

namespace PCS.V2.ProofGatedSelfImprovement

structure Neuron where
  useReLU : Bool
  weight : Int
  bias : Int
  deriving Repr, DecidableEq

def relu (z : Int) : Int := max 0 z

def predict (m : Neuron) (x : Int) : Int :=
  let z := m.weight * x + m.bias
  if m.useReLU then relu z else z

def point (i : Fin 7) : Int := (Int.ofNat i.val) - 3

def target (i : Fin 7) : Int := relu (2 * point i + 1)

def correct (m : Neuron) (i : Fin 7) : Prop := predict m (point i) = target i

def loss (m : Neuron) : Nat :=
  ((List.range 7).map fun j =>
    (predict m ((Int.ofNat j) - 3) - relu (2 * ((Int.ofNat j) - 3) + 1)).natAbs).sum

def admissible (old candidate : Neuron) : Prop :=
  (∀ i : Fin 7, correct old i → correct candidate i) ∧
  (∃ i : Fin 7, ¬ correct old i ∧ correct candidate i) ∧
  loss candidate < loss old

-- Quantifiers are finite (Fin 7), so the whole policy is executable.
def accept (old candidate : Neuron) : Bool := decide (admissible old candidate)

theorem accept_sound {old candidate : Neuron} (h : accept old candidate = true) :
    admissible old candidate := by
  exact of_decide_true h

theorem accepted_preserves {old candidate : Neuron}
    (h : accept old candidate = true) (i : Fin 7)
    (hi : correct old i) : correct candidate i :=
  (accept_sound h).1 i hi

theorem accepted_expands {old candidate : Neuron}
    (h : accept old candidate = true) :
    ∃ i : Fin 7, ¬ correct old i ∧ correct candidate i :=
  (accept_sound h).2.1

theorem accepted_strict_loss {old candidate : Neuron}
    (h : accept old candidate = true) : loss candidate < loss old :=
  (accept_sound h).2.2

theorem two_accepted_steps {a b c : Neuron}
    (hab : accept a b = true) (hbc : accept b c = true) :
    loss c < loss a :=
  Nat.lt_trans (accepted_strict_loss hbc) (accepted_strict_loss hab)

theorem perfect_cannot_advance (m : Neuron)
    (hperfect : ∀ i : Fin 7, correct m i) (candidate : Neuron) :
    accept m candidate = false := by
  cases hc : accept m candidate with
  | false => rfl
  | true =>
    obtain ⟨i, hi, _⟩ := accepted_expands hc
    exact False.elim (hi (hperfect i))

def zero : Neuron := ⟨true, 0, 0⟩
def intermediate : Neuron := ⟨true, 1, 1⟩
def optimum : Neuron := ⟨true, 2, 1⟩
def regressive : Neuron := ⟨true, 1, 2⟩

example : accept zero intermediate = true := by decide
example : accept intermediate optimum = true := by decide
example : accept zero regressive = false := by decide
example : accept optimum zero = false := by decide
example : loss optimum = 0 := by decide

theorem optimum_perfect (i : Fin 7) : correct optimum i := by
  rfl

theorem optimum_terminal (candidate : Neuron) : accept optimum candidate = false :=
  perfect_cannot_advance optimum optimum_perfect candidate

end PCS.V2.ProofGatedSelfImprovement

/-! Experimental Lean authority CLI. DO NOT expose as privileged production service.
    Only constant, vetted source is evaluated; input is parsed as integers. -/
private def parseActivation : String → Option Bool
  | "relu" => some true
  | "linear" => some false
  | _ => none

private def readNeuron (a w b : String) : Option PCS.V2.ProofGatedSelfImprovement.Neuron := do
  let activation ← parseActivation a
  let weight ← w.toInt?
  let bias ← b.toInt?
  if weight < -32 || weight > 32 || bias < -32 || bias > 32 then
    none
  else
    some ⟨activation, weight, bias⟩

def main : IO UInt32 := do
  let args ← IO.getArgs
  match args.toList with
  | [oldA, oldW, oldB, newA, newW, newB] =>
    match readNeuron oldA oldW oldB, readNeuron newA newW newB with
    | some old, some candidate =>
      if PCS.V2.ProofGatedSelfImprovement.accept old candidate then
        IO.println "ACCEPT"
        return 0
      else
        IO.println "REJECT"
        return 1
    | _, _ =>
      IO.println "REJECT:bad_parameters"
      return 2
  | _ =>
    IO.println "REJECT:bad_arity"
    return 2
