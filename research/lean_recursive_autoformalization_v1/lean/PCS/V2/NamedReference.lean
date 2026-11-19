import PCS.V2.FiniteReference
import Lean.Data.Json

/-! A closed input vocabulary for reference review. Resolving a name always
selects the nearest binder. Successful translation preserves the independent
named, proposition-valued interpretation, including variable shadowing. -/
namespace PCS.V2.FiniteReference

inductive Named where
  | var (name : String)
  | truth (value : Bool)
  | conj (left right : Named)
  | implies (left right : Named)
  | neg (body : Named)
  | every (name : String) (body : Named)
  | someVal (name : String) (body : Named)
  deriving Repr, Lean.FromJson, Lean.ToJson

def override (ρ : String → Bool) (x : String) (b : Bool) : String → Bool :=
  fun y => if y = x then b else ρ y

def meaning : Named → (String → Bool) → Prop
  | .var x, ρ => ρ x = true
  | .truth b, _ => b = true
  | .conj p q, ρ => meaning p ρ ∧ meaning q ρ
  | .implies p q, ρ => meaning p ρ → meaning q ρ
  | .neg p, ρ => ¬ meaning p ρ
  | .every x p, ρ => ∀ b, meaning p (override ρ x b)
  | .someVal x p, ρ => ∃ b, meaning p (override ρ x b)

def valuation : (names : List String) → Assignment names.length → String → Bool
  | [], _ => fun _ => false
  | x :: xs, (b, tail) => override (valuation xs tail) x b

def indexOf? : (names : List String) → String → Option (Fin names.length)
  | [], _ => none
  | x :: xs, y => if y = x then some ⟨0, Nat.succ_pos _⟩ else (indexOf? xs y).map Fin.succ

theorem indexOf_sound (names : List String) (x : String) (ρ : Assignment names.length)
    (i : Fin names.length) (h : indexOf? names x = some i) :
    lookup ρ i = valuation names ρ x := by
  induction names with
  | nil => simp [indexOf?] at h
  | cons y ys ih =>
    obtain ⟨b, tail⟩ := ρ
    by_cases eq : x = y
    · simp [indexOf?, eq] at h
      subst i
      simp [lookup, valuation, override, eq]
    · cases old : indexOf? ys x with
      | none => simp [indexOf?, eq, old] at h
      | some j =>
        simp [indexOf?, eq, old] at h
        subst i
        simpa [lookup, valuation, override, eq] using ih tail j old

/-- Unsupported and unbound names cannot produce an intrinsically scoped term. -/
def resolve (names : List String) : Named → Option (Formula names.length)
  | .var x => (indexOf? names x).map Formula.var
  | .truth b => some (.truth b)
  | .neg p => (resolve names p).map Formula.neg
  | .conj p q => return .conj (← resolve names p) (← resolve names q)
  | .implies p q => return .implies (← resolve names p) (← resolve names q)
  | .every x p => (resolve (x :: names) p).map Formula.every
  | .someVal x p => (resolve (x :: names) p).map Formula.someVal

/-- A source name is legal precisely when it is in the active binding context. -/
def Scoped (names : List String) : Named → Prop
  | .var x => x ∈ names
  | .truth _ => True
  | .neg p => Scoped names p
  | .conj p q | .implies p q => Scoped names p ∧ Scoped names q
  | .every x p | .someVal x p => Scoped (x :: names) p

private theorem indexOf_defined (names : List String) (x : String) :
    (indexOf? names x).isSome = true ↔ x ∈ names := by
  induction names with
  | nil => simp [indexOf?]
  | cons y ys ih =>
    by_cases he : x = y
    · simp [indexOf?, he]
    · simp [indexOf?, he, ih]

theorem resolve_defined_iff (p : Named) (names : List String) :
    (resolve names p).isSome = true ↔ Scoped names p := by
  induction p generalizing names with
  | var x => simp [resolve, Scoped, indexOf_defined]
  | truth => simp [resolve, Scoped]
  | neg p ih => simp [resolve, Scoped, ih]
  | conj p q ih jh | implies p q ih jh =>
    simp only [Scoped, ← ih, ← jh, resolve]
    cases resolve names p <;> cases resolve names q <;> simp
  | every x p ih | someVal x p ih => simp [resolve, Scoped, ih]

theorem resolve_sound (p : Named) (names : List String) (ρ : Assignment names.length)
    (f : Formula names.length) (h : resolve names p = some f) :
    denote f ρ ↔ meaning p (valuation names ρ) := by
  induction p generalizing names with
  | var x =>
    cases hx : indexOf? names x with
    | none => simp [resolve, hx] at h
    | some i =>
      simp [resolve, hx] at h
      subst f
      simp [meaning, denote, indexOf_sound names x ρ i hx]
  | truth b => simp [resolve] at h; subst f; rfl
  | neg p ih =>
    cases hp : resolve names p <;> simp [resolve, hp] at h
    subst f
    simp [meaning, denote, ih names ρ _ hp]
  | conj p q ih jh | implies p q ih jh =>
    cases hp : resolve names p <;> cases hq : resolve names q <;> simp [resolve, hp, hq] at h
    subst f
    simp [meaning, denote, ih names ρ _ hp, jh names ρ _ hq]
  | every x p ih | someVal x p ih =>
    cases hp : resolve (x :: names) p <;> simp [resolve, hp] at h
    subst f
    simp only [denote, meaning]
    first
    | exact forall_congr' (fun b => ih (x :: names) (b, ρ) _ hp)
    | exact exists_congr (fun b => ih (x :: names) (b, ρ) _ hp)

structure NamedContract where
  premise : Named
  conclusion : Named
  deriving Lean.ToJson, Lean.FromJson

def NamedContract.resolve? (a : NamedContract) (names : List String) :
    Option (Contract names.length) := return ⟨← resolve names a.premise, ← resolve names a.conclusion⟩

def NamedCorresponds (names : List String) (r c : NamedContract) : Prop :=
  ∀ ρ : Assignment names.length,
    (meaning r.premise (valuation names ρ) ↔ meaning c.premise (valuation names ρ)) ∧
    (meaning r.conclusion (valuation names ρ) ↔ meaning c.conclusion (valuation names ρ))

/-- The exhaustive decision applies to each component in the source vocabulary,
including the declared free-variable order and the scoping of quantified names. -/
theorem named_counterexample_none_iff (names : List String) (r c : NamedContract)
    {a b : Contract names.length} (hr : r.resolve? names = some a)
    (hc : c.resolve? names = some b) :
    counterexample a b = none ↔ NamedCorresponds names r c := by
  cases hrp : resolve names r.premise <;> cases hrq : resolve names r.conclusion <;>
    simp [NamedContract.resolve?, hrp, hrq] at hr
  cases hcp : resolve names c.premise <;> cases hcq : resolve names c.conclusion <;>
    simp [NamedContract.resolve?, hcp, hcq] at hc
  subst a; subst b
  simp only [counterexample_none_iff, Corresponds, NamedCorresponds,
    resolve_sound _ _ _ _ hrp, resolve_sound _ _ _ _ hrq,
    resolve_sound _ _ _ _ hcp, resolve_sound _ _ _ _ hcq]

/-- Conservative upper bound on recursive formula visits per assignment;
quantifier costs account for both possible bound values. -/
def Named.cost : Named → Nat
  | .var _ | .truth _ => 1
  | .conj p q | .implies p q => 1 + p.cost + q.cost
  | .neg p => 1 + p.cost
  | .every _ p | .someVal _ p => 1 + 2 * p.cost

end PCS.V2.FiniteReference
