import Std

/- Arbitrary-carrier set algebra, compiled to one-point membership circuits. -/
namespace PCS.SetAlgebra

abbrev Pred (α : Type u) := α → Prop

inductive Expr (n : Nat)
  | var (i : Fin n)
  | empty | univ
  | union (a b : Expr n) | inter (a b : Expr n)
  | diff (a b : Expr n) | compl (a : Expr n)
  | inf (a b : Expr n) | sup (a b : Expr n)
  deriving Repr

-- These order-theoretic specifications give infimum and supremum their meanings
-- without defining them as the intersection and union constructors.
def Below (a b : Pred α) : Prop := ∀ x, a x → b x
def meet (a b : Pred α) : Pred α := fun x => ∃ c, Below c a ∧ Below c b ∧ c x
def join (a b : Pred α) : Pred α := fun x => ∀ c, Below a c → Below b c → c x

theorem meet_iff (a b : Pred α) (x : α) : meet a b x ↔ a x ∧ b x := by
  constructor
  · rintro ⟨c, ha, hb, hx⟩
    exact ⟨ha x hx, hb x hx⟩
  · intro h
    exact ⟨fun y => a y ∧ b y, fun _ hy => hy.1, fun _ hy => hy.2, h⟩

theorem join_iff (a b : Pred α) (x : α) : join a b x ↔ a x ∨ b x := by
  constructor
  · intro h
    exact h (fun y => a y ∨ b y) (fun _ => Or.inl) (fun _ => Or.inr)
  · rintro (ha | hb) c ac bc
    · exact ac x ha
    · exact bc x hb

def Expr.denote (ρ : Fin n → Pred α) : Expr n → Pred α
  | .var i => ρ i
  | .empty => fun _ => False
  | .univ => fun _ => True
  | .union a b => fun x => a.denote ρ x ∨ b.denote ρ x
  | .inter a b => fun x => a.denote ρ x ∧ b.denote ρ x
  | .diff a b => fun x => a.denote ρ x ∧ ¬ b.denote ρ x
  | .compl a => fun x => ¬ a.denote ρ x
  | .inf a b => meet (a.denote ρ) (b.denote ρ)
  | .sup a b => join (a.denote ρ) (b.denote ρ)

inductive Circuit (n : Nat)
  | bit (i : Fin n) | constant (v : Bool)
  | and (a b : Circuit n) | or (a b : Circuit n) | neg (a : Circuit n)

def Circuit.eval (v : Fin n → Bool) : Circuit n → Bool
  | .bit i => v i
  | .constant c => c
  | .and a b => a.eval v && b.eval v
  | .or a b => a.eval v || b.eval v
  | .neg a => !(a.eval v)

def compile : Expr n → Circuit n
  | .var i => .bit i
  | .empty => .constant false
  | .univ => .constant true
  | .union a b | .sup a b => .or (compile a) (compile b)
  | .inter a b | .inf a b => .and (compile a) (compile b)
  | .diff a b => .and (compile a) (.neg (compile b))
  | .compl a => .neg (compile a)

theorem compile_preserves (e : Expr n) (ρ : Fin n → Pred α) (x : α)
    (v : Fin n → Bool) (hv : ∀ i, v i = true ↔ ρ i x) :
    (compile e).eval v = true ↔ e.denote ρ x := by
  induction e <;> simp_all [compile, Circuit.eval, Expr.denote, meet_iff, join_iff,
    Bool.eq_false_iff]

def allBits : {n : Nat} → ((Fin n → Bool) → Bool) → Bool
  | 0, p => p Fin.elim0
  | _+1, p => allBits (fun v => p (Fin.cases false v)) &&
               allBits (fun v => p (Fin.cases true v))

theorem allBits_iff (p : (Fin n → Bool) → Bool) :
    allBits p = true ↔ ∀ v, p v = true := by
  induction n with
  | zero =>
    constructor
    · intro h v
      have : v = Fin.elim0 := funext fun i => Fin.elim0 i
      simpa [this] using h
    · exact fun h => h _
  | succ n ih =>
    simp only [allBits, Bool.and_eq_true, ih]
    constructor
    · rintro ⟨hf, ht⟩ v
      have h : Fin.cases (v 0) (fun i => v i.succ) = v :=
        funext fun i => Fin.cases rfl (fun _ => rfl) i
      rw [← h]
      cases v 0 <;> first | apply hf | apply ht
    · exact fun h => ⟨fun _ => h _, fun _ => h _⟩

inductive Kind | equal | subset deriving DecidableEq, Repr
structure Atom (n : Nat) where
  kind : Kind
  lhs : Expr n
  rhs : Expr n

def Atom.holds (a : Atom n) (ρ : Fin n → Pred α) : Prop :=
  match a.kind with
  | .equal => a.lhs.denote ρ = a.rhs.denote ρ
  | .subset => Below (a.lhs.denote ρ) (a.rhs.denote ρ)

def Atom.test (a : Atom n) (v : Fin n → Bool) : Bool :=
  match a.kind with
  | .equal => (compile a.lhs).eval v == (compile a.rhs).eval v
  | .subset => !((compile a.lhs).eval v) || (compile a.rhs).eval v

theorem holds_iff (a : Atom n) (ρ : Fin n → Pred α) (v : α → Fin n → Bool)
    (hv : ∀ x i, v x i = true ↔ ρ i x) :
    a.holds ρ ↔ ∀ x, a.test (v x) = true := by
  have point (x : α) (e : Expr n) := compile_preserves e ρ x (v x) (hv x)
  cases a with | mk k l r =>
    cases k
    · simp only [Atom.holds, Atom.test, beq_iff_eq]
      constructor
      · intro h x
        apply Bool.eq_iff_iff.mpr
        rw [point, point, h]
      · intro h
        exact funext fun x => propext (by rw [← point x, ← point x, h x])
    · simp [Atom.holds, Atom.test, Below, Bool.eq_false_iff, point]
      constructor
      · intro h x
        by_cases hl : l.denote ρ x
        · exact Or.inr (h x hl)
        · exact Or.inl hl
      · intro h x hx
        exact (h x).resolve_left (fun h => h hx)

structure Contract (n : Nat) where
  premises : List (Atom n)
  conclusion : Atom n

def Contract.Valid (c : Contract n) : Prop :=
  ∀ (α : Type) (ρ : Fin n → Pred α), (∀ a ∈ c.premises, a.holds ρ) → c.conclusion.holds ρ

def localTest (c : Contract n) (v : Fin n → Bool) : Bool :=
  !(c.premises.all (fun a => a.test v)) || c.conclusion.test v

theorem singleton_iff (a : Atom n) (v : Fin n → Bool) :
    a.holds (fun i (_ : Unit) => v i = true) ↔ a.test v = true := by
  simpa using holds_iff a (fun i (_ : Unit) => v i = true) (fun _ => v) (by simp)

theorem singleton_countermodel (c : Contract n) (v : Fin n → Bool)
    (h : localTest c v = false) :
    (∀ a ∈ c.premises, a.holds (fun i (_ : Unit) => v i = true)) ∧
    ¬c.conclusion.holds (fun i (_ : Unit) => v i = true) := by
  have hpre : c.premises.all (fun a => a.test v) = true := by
    cases he : c.premises.all (fun a => a.test v) <;> simp_all [localTest]
  constructor
  · exact fun a ha => (singleton_iff a v).2 (List.all_eq_true.mp hpre a ha)
  · intro hc
    simp [localTest, hpre, (singleton_iff _ _).1 hc] at h

theorem validity_iff (c : Contract n) : allBits (localTest c) = true ↔ c.Valid := by
  rw [allBits_iff]
  constructor
  · intro h α ρ hp
    classical
    let v (x : α) (i : Fin n) := decide (ρ i x)
    have hv : ∀ x i, v x i = true ↔ ρ i x := by simp [v]
    apply (holds_iff _ _ v hv).mpr
    intro x
    have hpre : c.premises.all (fun a => a.test (v x)) = true :=
      List.all_eq_true.mpr fun a ha => (holds_iff a ρ v hv).mp (hp a ha) x
    simpa [localTest, hpre] using h (v x)
  · intro h v
    cases he : localTest c v with
    | true => rfl
    | false =>
      have bad := singleton_countermodel c v he
      exact False.elim (bad.2 (h Unit _ bad.1))

-- Agreement of individual operands avoids accepting two unrelated valid theorems.
def exprTest (a b : Expr n) : Bool :=
  allBits fun v => (compile a).eval v == (compile b).eval v

theorem expression_iff (a b : Expr n) : exprTest a b = true ↔
    ∀ (α : Type) (ρ : Fin n → Pred α), a.denote ρ = b.denote ρ := by
  simp only [exprTest, allBits_iff, beq_iff_eq]
  constructor
  · intro h α ρ
    classical
    apply funext
    intro x
    let v (i : Fin n) := decide (ρ i x)
    have hv : ∀ i, v i = true ↔ ρ i x := by simp [v]
    apply propext
    rw [← compile_preserves a ρ x v hv, ← compile_preserves b ρ x v hv, h]
  · intro h v
    let ρ (i : Fin n) (_ : Unit) := v i = true
    have hv : ∀ i, v i = true ↔ ρ i () := fun _ => Iff.rfl
    apply Bool.eq_iff_iff.mpr
    rw [compile_preserves a ρ () v hv, compile_preserves b ρ () v hv, h]

def atomTest (a b : Atom n) : Bool :=
  decide (a.kind = b.kind) && exprTest a.lhs b.lhs && exprTest a.rhs b.rhs

def Atom.Same (a b : Atom n) : Prop :=
  a.kind = b.kind ∧
  (∀ (α : Type) (ρ : Fin n → Pred α), a.lhs.denote ρ = b.lhs.denote ρ) ∧
  (∀ (α : Type) (ρ : Fin n → Pred α), a.rhs.denote ρ = b.rhs.denote ρ)

theorem atomTest_iff (a b : Atom n) : atomTest a b = true ↔ a.Same b := by
  simp [atomTest, Atom.Same, expression_iff, and_assoc]

def premiseTest : List (Atom n) → List (Atom n) → Bool
  | [], [] => true
  | a::as, b::bs => atomTest a b && premiseTest as bs
  | _, _ => false

def PremisesSame : List (Atom n) → List (Atom n) → Prop
  | [], [] => True
  | a::as, b::bs => a.Same b ∧ PremisesSame as bs
  | _, _ => False

theorem premiseTest_iff (as bs : List (Atom n)) :
    premiseTest as bs = true ↔ PremisesSame as bs := by
  induction as generalizing bs with
  | nil => cases bs <;> simp [premiseTest, PremisesSame]
  | cons a as ih => cases bs <;> simp [premiseTest, PremisesSame, atomTest_iff, ih]

def compareContracts (a b : Contract n) : Bool :=
  premiseTest a.premises b.premises && atomTest a.conclusion b.conclusion

def Contract.Same (a b : Contract n) : Prop :=
  PremisesSame a.premises b.premises ∧ a.conclusion.Same b.conclusion

theorem correspondence_iff (a b : Contract n) :
    compareContracts a b = true ↔ a.Same b := by
  simp [compareContracts, Contract.Same, premiseTest_iff, atomTest_iff]

#print axioms compile_preserves
#print axioms expression_iff
#print axioms singleton_countermodel
#print axioms validity_iff
#print axioms correspondence_iff
end PCS.SetAlgebra
