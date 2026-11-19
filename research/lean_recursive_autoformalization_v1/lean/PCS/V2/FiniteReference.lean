import PCS.V2.ProofGatedFormalization

/-!
Executable reference checking for open quantified Boolean contracts. Free variables
are interpreted pointwise under a common ordered signature. De Bruijn index zero
denotes the newest bound variable. References must be supplied independently.
-/
namespace PCS.V2.FiniteReference

open PCS.V2.ProofGatedFormalization

/-- An assignment in a context with exactly `n` Boolean variables. -/
def Assignment : Nat → Type
  | 0 => Unit
  | n+1 => Bool × Assignment n

def lookup : {n : Nat} → Assignment n → Fin n → Bool
  | 0, _, i => i.elim0
  | _+1, (head, tail), i => Fin.cases head (lookup tail) i

inductive Formula : Nat → Type
  | var : Fin n → Formula n
  | truth : Bool → Formula n
  | conj : Formula n → Formula n → Formula n
  | implies : Formula n → Formula n → Formula n
  | neg : Formula n → Formula n
  | every : Formula (n+1) → Formula n
  | someVal : Formula (n+1) → Formula n
  deriving Repr

def eval : Formula n → Assignment n → Bool
  | .var i, ρ => lookup ρ i
  | .truth b, _ => b
  | .conj p q, ρ => eval p ρ && eval q ρ
  | .implies p q, ρ => !(eval p ρ) || eval q ρ
  | .neg p, ρ => !(eval p ρ)
  | .every p, ρ => eval p (false, ρ) && eval p (true, ρ)
  | .someVal p, ρ => eval p (false, ρ) || eval p (true, ρ)

/-- Independent interpretation with genuine Lean quantifiers over Bool. -/
def denote : Formula n → Assignment n → Prop
  | .var i, ρ => lookup ρ i = true
  | .truth b, _ => b = true
  | .conj p q, ρ => denote p ρ ∧ denote q ρ
  | .implies p q, ρ => denote p ρ → denote q ρ
  | .neg p, ρ => ¬ denote p ρ
  | .every p, ρ => ∀ b : Bool, denote p (b, ρ)
  | .someVal p, ρ => ∃ b : Bool, denote p (b, ρ)

theorem eval_iff_denote (p : Formula n) (ρ : Assignment n) :
    eval p ρ = true ↔ denote p ρ := by
  induction p with
  | var | truth => rfl
  | conj p q ih jh => simp [eval, denote, ih, jh]
  | implies p q ih jh =>
    simp only [eval, denote, ← ih, ← jh]
    cases eval p ρ <;> cases eval q ρ <;> decide
  | neg p ih => simp [eval, denote, ← ih]
  | every p ih => simp [eval, denote, ih, Bool.forall_bool]
  | someVal p ih => simp [eval, denote, ih, Bool.exists_bool]

def assignments : (n : Nat) → List (Assignment n)
  | 0 => [()]
  | n+1 => (assignments n).map (false, ·) ++ (assignments n).map (true, ·)

theorem assignments_complete (n : Nat) (ρ : Assignment n) : ρ ∈ assignments n := by
  induction n with
  | zero => cases ρ; simp [assignments]
  | succ n ih => obtain ⟨b, rest⟩ := ρ; cases b <;> simp [assignments, ih]

structure Contract (n : Nat) where
  premise : Formula n
  conclusion : Formula n
  deriving Repr

/-- Both the admissible inputs and the conclusion under any input must agree.
Comparing conclusions even off the premise is intentional in this relation. -/
def Corresponds (a b : Contract n) : Prop :=
  ∀ ρ, (denote a.premise ρ ↔ denote b.premise ρ) ∧
       (denote a.conclusion ρ ↔ denote b.conclusion ρ)

def disagrees (a b : Contract n) (ρ : Assignment n) : Bool :=
  (eval a.premise ρ != eval b.premise ρ) || (eval a.conclusion ρ != eval b.conclusion ρ)

def counterexample (a b : Contract n) : Option (Assignment n) :=
  (assignments n).find? (disagrees a b)

private theorem agrees_iff (a b : Contract n) (ρ : Assignment n) :
    disagrees a b ρ = false ↔ ((denote a.premise ρ ↔ denote b.premise ρ) ∧
                              (denote a.conclusion ρ ↔ denote b.conclusion ρ)) := by
  simp only [disagrees, ← eval_iff_denote]
  cases eval a.premise ρ <;> cases eval b.premise ρ <;>
    cases eval a.conclusion ρ <;> cases eval b.conclusion ρ <;> decide

theorem counterexample_none_iff (a b : Contract n) :
    counterexample a b = none ↔ Corresponds a b := by
  simp only [counterexample, List.find?_eq_none, Bool.not_eq_true]
  exact ⟨fun h ρ => (agrees_iff a b ρ).mp (h ρ (assignments_complete n ρ)),
         fun h ρ _ => (agrees_iff a b ρ).mpr (h ρ)⟩

theorem counterexample_some_sound {a b : Contract n} {ρ : Assignment n}
    (h : counterexample a b = some ρ) :
    ¬ ((denote a.premise ρ ↔ denote b.premise ρ) ∧
       (denote a.conclusion ρ ↔ denote b.conclusion ρ)) := by
  have bad : disagrees a b ρ = true := List.find?_some h
  intro same
  rw [(agrees_iff a b ρ).mpr same] at bad
  contradiction

/-- A separate decision question asks whether the conditional holds everywhere. -/
def falsifier (c : Contract n) : Option (Assignment n) :=
  (assignments n).find? (fun ρ => eval c.premise ρ && !(eval c.conclusion ρ))

theorem falsifier_none_iff (c : Contract n) :
    falsifier c = none ↔ ∀ ρ, denote c.premise ρ → denote c.conclusion ρ := by
  simp only [falsifier, List.find?_eq_none, Bool.and_eq_true, Bool.not_eq_true',
    not_and, Bool.not_eq_false, ← eval_iff_denote]
  exact ⟨fun h ρ => h ρ (assignments_complete n ρ), fun h ρ _ => h ρ⟩

theorem falsifier_some_sound {c : Contract n} {ρ : Assignment n} (h : falsifier c = some ρ) :
    denote c.premise ρ ∧ ¬ denote c.conclusion ρ := by
  have witness : (eval c.premise ρ && !(eval c.conclusion ρ)) = true := List.find?_some (p := fun v => eval c.premise v && !(eval c.conclusion v)) h
  simpa [← eval_iff_denote] using witness

/-- A missing candidate and an inequivalent candidate both remain unresolved. -/
def status (reference : Contract n) (candidate : Option (Contract n)) : CaseStatus :=
  match candidate with
  | none => .fail
  | some c => if (counterexample reference c).isNone then .supported else .fail

theorem supported_iff (r c : Contract n) :
    status r (some c) = .supported ↔ Corresponds r c := by
  cases h : counterexample r c <;> simp [status, h, ← counterexample_none_iff]

abbrev Proposals (k n : Nat) := Fin k → Option (Contract n)

def capability (ref : Fin k → Contract n) (p : Proposals k n) : Capability :=
  List.ofFn (fun i => status (ref i) (p i))

inductive Trace (ref : Fin k → Contract n) : Nat → Proposals k n → Proposals k n → Prop
  | zero (a) : Trace ref 0 a a
  | step {t a b c} : Trace ref t a b →
      accept (capability ref b) (capability ref c) = true → Trace ref (t+1) a c

theorem status_trace {ref : Fin k → Contract n} {t a b} (h : Trace ref t a b) :
    CertifiedTrace t (capability ref a) (capability ref b) := by
  induction h with
  | zero => exact .zero _
  | step _ accepted ih => exact .extend ih accepted

/-- Receipts are recomputed for every proposed state. Across arbitrarily many
accepted repairs, a previously corresponding candidate still has a
corresponding replacement in the same reference slot. -/
theorem trace_preserves_correspondence {ref : Fin k → Contract n} {t a b}
    (h : Trace ref t a b) (i : Fin k) {old : Contract n}
    (ho : a i = some old) (hc : Corresponds (ref i) old) :
    ∃ new, b i = some new ∧ Corresponds (ref i) new := by
  have initial : (capability ref a)[i.val]? = some CaseStatus.supported := by
    simp [capability, i.isLt, ho, (supported_iff _ _).mpr hc]
  have final := trace_preserves (status_trace h) i.val initial (by decide)
  have locked : status (ref i) (b i) = .supported := by simpa [capability, i.isLt] using final
  cases hbi : b i with
  | none => simp [hbi, status] at locked
  | some c => exact ⟨c, rfl, (supported_iff _ _).mp (hbi ▸ locked)⟩

end PCS.V2.FiniteReference
