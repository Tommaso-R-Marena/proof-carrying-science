import Std

/-!
Research specification for integer SI exponent vectors and a conservative checker.
No claim connects this syntax to Python's parser, floating point, SBML declarations,
or physical truth. A symbol environment must be supplied explicitly. Literals,
including zero, have only the dimensionless type. Affine unit conversions are absent.
-/
namespace ScientificDimensions

structure Dim where
  length : Int
  mass : Int
  time : Int
  current : Int
  temperature : Int
  amount : Int
  luminosity : Int
  deriving DecidableEq, Repr

def dimensionless : Dim := ⟨0, 0, 0, 0, 0, 0, 0⟩
def timeDim : Dim := ⟨0, 0, 1, 0, 0, 0, 0⟩
def dimMul (a b : Dim) : Dim :=
  ⟨a.length + b.length, a.mass + b.mass, a.time + b.time,
    a.current + b.current, a.temperature + b.temperature,
    a.amount + b.amount, a.luminosity + b.luminosity⟩
def dimDiv (a b : Dim) : Dim :=
  ⟨a.length - b.length, a.mass - b.mass, a.time - b.time,
    a.current - b.current, a.temperature - b.temperature,
    a.amount - b.amount, a.luminosity - b.luminosity⟩
def dimPow (a : Dim) (n : Int) : Dim :=
  ⟨a.length * n, a.mass * n, a.time * n, a.current * n,
    a.temperature * n, a.amount * n, a.luminosity * n⟩

inductive Expr where
  | scalar : Expr
  | symbol : Nat → Expr
  | neg : Expr → Expr
  | add : Expr → Expr → Expr
  | mul : Expr → Expr → Expr
  | div : Expr → Expr → Expr
  | pow : Expr → Int → Expr
  | exp : Expr → Expr
  | derivative : Expr → Expr
  deriving Repr

abbrev Environment := Nat → Option Dim

noncomputable def check (env : Environment) : Expr → Option Dim :=
  Expr.rec
    (some dimensionless)
    (fun n => env n)
    (fun _ da => da)
    (fun _ _ da db => da.elim none (fun a => db.elim none
      (fun b => if a = b then some a else none)))
    (fun _ _ da db => da.elim none (fun a => db.elim none
      (fun b => some (dimMul a b))))
    (fun _ _ da db => da.elim none (fun a => db.elim none
      (fun b => some (dimDiv a b))))
    (fun _ n da => da.map (fun a => dimPow a n))
    (fun _ da => da.elim none
      (fun a => if a = dimensionless then some dimensionless else none))
    (fun _ da => da.map (fun a => dimDiv a timeDim))

/-- Declarative dimension typing, independently stated from the recursive checker. -/
inductive HasDim (env : Environment) : Expr → Dim → Prop where
  | scalar : HasDim env .scalar dimensionless
  | symbol : env n = some d → HasDim env (.symbol n) d
  | neg : HasDim env a d → HasDim env (.neg a) d
  | add : HasDim env a d → HasDim env b d → HasDim env (.add a b) d
  | mul : HasDim env a da → HasDim env b db → HasDim env (.mul a b) (dimMul da db)
  | div : HasDim env a da → HasDim env b db → HasDim env (.div a b) (dimDiv da db)
  | pow : HasDim env a da → HasDim env (.pow a n) (dimPow da n)
  | exp : HasDim env a dimensionless → HasDim env (.exp a) dimensionless
  | derivative : HasDim env a da → HasDim env (.derivative a) (dimDiv da timeDim)

/-- Every accepted result has a declarative typing derivation. -/
theorem check_sound (env : Environment) (e : Expr) :
    ∀ d, check env e = some d → HasDim env e d := by
  induction e with
  | scalar =>
      intro d h
      exact (Option.some.inj h) ▸ HasDim.scalar
  | symbol n =>
      intro d h
      exact HasDim.symbol h
  | neg a ih =>
      intro d h
      exact HasDim.neg (ih d h)
  | add a b iha ihb =>
      intro d h
      change (check env a).elim none (fun da => (check env b).elim none
        (fun db => if da = db then some da else none)) = some d at h
      cases ha : check env a with
      | none => rw [ha] at h; cases h
      | some da =>
          rw [ha] at h
          cases hb : check env b with
          | none => rw [hb] at h; cases h
          | some db =>
              rw [hb] at h
              by_cases hd : da = db
              · subst db
                have hh := Eq.trans (if_pos (rfl : da = da)).symm h
                exact (Option.some.inj hh) ▸ HasDim.add (iha da ha) (ihb da hb)
              · have hh := Eq.trans (if_neg hd).symm h
                cases hh
  | mul a b iha ihb =>
      intro d h
      change (check env a).elim none (fun da => (check env b).elim none
        (fun db => some (dimMul da db))) = some d at h
      cases ha : check env a with
      | none => rw [ha] at h; cases h
      | some da =>
          rw [ha] at h
          cases hb : check env b with
          | none => rw [hb] at h; cases h
          | some db =>
              rw [hb] at h
              exact (Option.some.inj h) ▸ HasDim.mul (iha da ha) (ihb db hb)
  | div a b iha ihb =>
      intro d h
      change (check env a).elim none (fun da => (check env b).elim none
        (fun db => some (dimDiv da db))) = some d at h
      cases ha : check env a with
      | none => rw [ha] at h; cases h
      | some da =>
          rw [ha] at h
          cases hb : check env b with
          | none => rw [hb] at h; cases h
          | some db =>
              rw [hb] at h
              exact (Option.some.inj h) ▸ HasDim.div (iha da ha) (ihb db hb)
  | pow a n ih =>
      intro d h
      change (check env a).map (fun da => dimPow da n) = some d at h
      cases ha : check env a with
      | none => rw [ha] at h; cases h
      | some da =>
          rw [ha] at h
          exact (Option.some.inj h) ▸ HasDim.pow (ih da ha)
  | exp a ih =>
      intro d h
      change (check env a).elim none
        (fun da => if da = dimensionless then some dimensionless else none) = some d at h
      cases ha : check env a with
      | none => rw [ha] at h; cases h
      | some da =>
          rw [ha] at h
          by_cases hd : da = dimensionless
          · subst da
            change (if dimensionless = dimensionless then some dimensionless else (none : Option Dim)) = some d at h
            have hh := Eq.trans (if_pos (rfl : dimensionless = dimensionless)).symm h
            exact (Option.some.inj hh) ▸ HasDim.exp (ih dimensionless ha)
          · have hh := Eq.trans (if_neg hd).symm h
            cases hh
  | derivative a ih =>
      intro d h
      change (check env a).map (fun da => dimDiv da timeDim) = some d at h
      cases ha : check env a with
      | none => rw [ha] at h; cases h
      | some da =>
          rw [ha] at h
          exact (Option.some.inj h) ▸ HasDim.derivative (ih da ha)

/-- Every derivable typing is found by the recursive checker. -/
theorem check_complete {env : Environment} {e : Expr} {d : Dim}
    (typed : HasDim env e d) : check env e = some d := by
  induction typed with
  | scalar => rfl
  | symbol h => exact h
  | neg _ ih => exact ih
  | add _ _ iha ihb =>
      change (check _ _).elim none (fun da => (check _ _).elim none
        (fun db => if da = db then some da else none)) = _
      rw [iha, ihb]
      exact if_pos rfl
  | mul _ _ iha ihb =>
      change (check _ _).elim none (fun da => (check _ _).elim none
        (fun db => some (dimMul da db))) = _
      rw [iha, ihb]
      rfl
  | div _ _ iha ihb =>
      change (check _ _).elim none (fun da => (check _ _).elim none
        (fun db => some (dimDiv da db))) = _
      rw [iha, ihb]
      rfl
  | pow _ ih =>
      change Option.map _ (check _ _) = _
      rw [ih]
      rfl
  | exp _ ih =>
      change (check _ _).elim none
        (fun da => if da = dimensionless then some dimensionless else none) = _
      rw [ih]
      change (if dimensionless = dimensionless then some dimensionless else (none : Option Dim)) = some dimensionless
      exact if_pos rfl
  | derivative _ ih =>
      change Option.map _ (check _ _) = _
      rw [ih]
      rfl

/-- Missing environment declarations cannot receive a typing derivation. -/
theorem undeclared_symbol_untypable (env : Environment) (n : Nat)
    (missing : env n = none) (d : Dim) : ¬ HasDim env (.symbol n) d := by
  intro typed
  have accepted := check_complete typed
  change env n = some d at accepted
  rw [missing] at accepted
  cases accepted

/-- Type uniqueness follows from the checker, including arbitrary nested expressions. -/
theorem dimension_unique {env : Environment} {e : Expr} {d₁ d₂ : Dim}
    (h₁ : HasDim env e d₁) (h₂ : HasDim env e d₂) : d₁ = d₂ := by
  have eq₁ := check_complete h₁
  have eq₂ := check_complete h₂
  have both : some d₁ = some d₂ := Eq.trans eq₁.symm eq₂
  exact Option.some.inj both

/-- Research evidence never grants production authority. -/
inductive Evidence where
  | verified
  | refuted
  | unknown
  deriving DecidableEq, Repr

def authority (_ : Evidence) : Bool := false

theorem research_has_no_authority (e : Evidence) : authority e = false := by
  cases e <;> rfl

/-- An explicit nonnegative rational-pair model. A meaningful value has den ≠ 0.
No normalization, floating point semantics, or affine temperature conversion is modeled. -/
structure RationalPair where
  num : Nat
  den : Nat
  deriving DecidableEq, Repr

def RationalPair.wellFormed (q : RationalPair) : Prop := q.den ≠ 0

def rationalMul (a b : RationalPair) : RationalPair :=
  ⟨a.num * b.num, a.den * b.den⟩

def scaleRational (factor value : RationalPair) : RationalPair := rationalMul factor value

/-- A constructive associativity proof avoids the classical axioms of Std Rat algebra. -/
theorem nat_mul_assoc_constructive (a b c : Nat) : (a * b) * c = a * (b * c) := by
  induction c with
  | zero => rfl
  | succ c ih =>
      calc
        (a * b) * (c + 1) = (a * b) * c + a * b := Nat.mul_succ (a * b) c
        _ = a * (b * c) + a * b := congrArg (fun x => x + a * b) ih
        _ = a * (b * c + b) := (Nat.mul_add a (b * c) b).symm
        _ = a * (b * (c + 1)) := congrArg (fun x => a * x) (Nat.mul_succ b c).symm

theorem nat_product_reorder (a b c d : Nat) : (a * b) * (c * d) = (a * c) * (b * d) := by
  calc
    (a * b) * (c * d) = a * (b * (c * d)) := nat_mul_assoc_constructive a b (c * d)
    _ = a * ((b * c) * d) := congrArg (fun x => a * x) (nat_mul_assoc_constructive b c d).symm
    _ = a * ((c * b) * d) := congrArg (fun x => a * (x * d)) (Nat.mul_comm b c)
    _ = a * (c * (b * d)) := congrArg (fun x => a * x) (nat_mul_assoc_constructive c b d)
    _ = (a * c) * (b * d) := (nat_mul_assoc_constructive a c (b * d)).symm

/-- Exact rational-pair multiplication respects multiplying conversion factors.
This is an arithmetic model theorem; it does not assert physical unit compatibility. -/
theorem scale_multiplicative_compatibility (f g x y : RationalPair)
    (_hf : f.wellFormed) (_hg : g.wellFormed)
    (_hx : x.wellFormed) (_hy : y.wellFormed) :
    scaleRational (rationalMul f g) (rationalMul x y) =
      rationalMul (scaleRational f x) (scaleRational g y) := by
  cases f with
  | mk fn fd =>
    cases g with
    | mk gn gd =>
      cases x with
      | mk xn xd =>
        cases y with
        | mk yn yd =>
          unfold scaleRational rationalMul
          exact congr
            (congrArg RationalPair.mk (nat_product_reorder fn gn xn yn))
            (nat_product_reorder fd gd xd yd)

/-- Exact min→s scaling for a nonnegative rational quantity: numerator ×60. -/
def minutesToSeconds (q : RationalPair) : RationalPair := scaleRational ⟨60, 1⟩ q

theorem minutes_to_seconds_exact (n d : Nat) :
    minutesToSeconds ⟨n, d⟩ = ⟨60 * n, d⟩ := by
  unfold minutesToSeconds scaleRational rationalMul
  exact congrArg (RationalPair.mk (60 * n)) (Nat.one_mul d)

#print axioms check_sound
#print axioms check_complete
#print axioms undeclared_symbol_untypable
#print axioms dimension_unique
#print axioms research_has_no_authority
#print axioms nat_mul_assoc_constructive
#print axioms nat_product_reorder
#print axioms scale_multiplicative_compatibility
#print axioms minutes_to_seconds_exact

end ScientificDimensions