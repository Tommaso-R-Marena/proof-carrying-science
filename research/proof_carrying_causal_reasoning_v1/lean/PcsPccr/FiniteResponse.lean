import Std
import Init.Data.Rat.Lemmas

/-! Finite recursive SCMs with exact frequencies. A schema is a list of domain
cardinalities, newest variable first. Each equation can read only its
predecessors and a shared exogenous state. A finite list of nonnegative integer
weights describes any finitely supported rational law by clearing denominators.
Repeated exogenous states represent additional mass. -/
namespace PcsPccr.FiniteResponse

def Values : List Nat → Type
  | [] => Unit
  | n :: ns => Fin n × Values ns

def Intervention : List Nat → Type
  | [] => Unit
  | n :: ns => Option (Fin n) × Intervention ns

/-- Newest variable heads the list. Equations introduce no cycles. -/
inductive Equations (U : Type) : List Nat → Type
  | empty : Equations U []
  | extend : Equations U ns → (U → Values ns → Fin n) → Equations U (n :: ns)

def natural : (ns : List Nat) → Intervention ns
  | [] => ()
  | _ :: ns => (none, natural ns)

def evaluate : Equations U ns → Intervention ns → U → Values ns
  | .empty, _, _ => ()
  | .extend prev f, (action, rest), u =>
      let prior := evaluate prev rest u
      (action.getD (f u prior), prior)

/-- Relational specification: each component is its assigned value or the
value of its original equation on this very assignment's predecessors. -/
def Solves : Equations U ns → Intervention ns → U → Values ns → Prop
  | .empty, _, _, _ => True
  | .extend prev f, (action, rest), u, (value, prior) =>
      Solves prev rest u prior ∧
      match action with
      | some x => value = x
      | none => value = f u prior

/-- Existence and uniqueness of the structural solution for any surgical
intervention and shared noise realization. -/
theorem solves_iff (s : Equations U ns) (a : Intervention ns) (u : U) (v : Values ns) :
    Solves s a u v ↔ v = evaluate s a u := by
  induction s with
  | empty => cases v; simp [Solves, evaluate]
  | extend prev f ih =>
    rcases a with ⟨action, rest⟩
    rcases v with ⟨x, prior⟩
    cases action <;> simp only [Solves, evaluate, ih, Option.getD]
    all_goals constructor
    all_goals rintro ⟨h, k⟩
    all_goals simp_all

def compatible : (ns : List Nat) → Intervention ns → Values ns → Prop
  | [], _, _ => True
  | _ :: ns, (action, rest), (x, prior) =>
      compatible ns rest prior ∧ (∀ y, action = some y → y = x)

/-- Unit-level consistency, including simultaneous interventions on any subset
of variables. The factual and intervened assignments use the same noise. -/
theorem consistency (s : Equations U ns) (a : Intervention ns) (u : U)
    (h : compatible ns a (evaluate s (natural ns) u)) :
    evaluate s a u = evaluate s (natural ns) u := by
  induction s with
  | empty => rfl
  | extend prev f ih =>
    rcases a with ⟨action, rest⟩
    obtain ⟨hp, hx⟩ := h
    simp only [evaluate, natural, ih rest hp, Option.getD_none]
    cases action with
    | none => rfl
    | some y => exact Prod.ext (hx y rfl) rfl

/-- Sum the multiplicities of the event in an exogenous population. -/
def count (event : U → Bool) : List (U × Nat) → Nat
  | [] => 0
  | (u,w) :: rows => (if event u then w else 0) + count event rows

theorem count_congr (rows : List (U × Nat)) {p q : U → Bool}
    (h : ∀ u, p u = q u) : count p rows = count q rows := by rw [funext h]

theorem count_partition (rows : List (U × Nat)) (p : U → Bool) :
    count p rows + count (fun u => !(p u)) rows = count (fun _ => true) rows := by
  induction rows with
  | nil => rfl
  | cons r rows ih => cases r with
    | mk u w => cases h : p u <;> simp [count, h] <;> omega

/-- Positive total mass excludes the empty empirical law. -/
structure Population (U : Type) where
  rows : List (U × Nat)
  positive : 0 < count (fun _ => true) rows

def probability (pop : Population U) (p : U → Bool) : Rat :=
  mkRat (count p pop.rows) (count (fun _ => true) pop.rows)

theorem normalized (pop : Population U) : probability pop (fun _ => true) = 1 := by
  unfold probability
  rw [← Rat.divInt_ofNat, Rat.divInt_self']
  exact Int.natCast_ne_zero.mpr (Nat.ne_zero_of_lt pop.positive)

/-- Evidence is interpreted in the factual world. The outcome is interpreted
in the intervened world with the very same exogenous state. A zero-mass event
has no conditional probability. -/
def conditional (pop : Population U) (s : Equations U ns) (a : Intervention ns)
    (evidence outcome : Values ns → Bool) : Option Rat :=
  let obs := evaluate s (natural ns)
  let den := count (fun u => evidence (obs u)) pop.rows
  let num := count (fun u => evidence (obs u) && outcome (evaluate s a u)) pop.rows
  if den = 0 then none else some (mkRat num den)

/-- Conditioning preserves consistency when the factual evidence determines
all the intervention values. This includes zero-probability evidence. -/
theorem conditional_consistency (pop : Population U) (s : Equations U ns)
    (a : Intervention ns) (evidence outcome : Values ns → Bool)
    (h : ∀ u, evidence (evaluate s (natural ns) u) = true →
      compatible ns a (evaluate s (natural ns) u)) :
    conditional pop s a evidence outcome = conditional pop s (natural ns) evidence outcome := by
  have same : ∀ u, (evidence (evaluate s (natural ns) u) && outcome (evaluate s a u)) =
      (evidence (evaluate s (natural ns) u) && outcome (evaluate s (natural ns) u)) := by
    intro u
    cases he : evidence (evaluate s (natural ns) u) with
    | false => rfl
    | true => rw [consistency s a u (h u he)]
  simp only [conditional, count_congr pop.rows same]

end PcsPccr.FiniteResponse
