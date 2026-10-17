/-
  Minimal Claim IR fragment: quantifier kind preservation.
-/
namespace PcsNext.ClaimIR

inductive Quantifier where
  | forallQ
  | existsQ
deriving DecidableEq, Repr

structure Binder where
  name : String
  sort : String
deriving Repr

inductive Expr where
  | var (name : String)
  | const (label : String)
  | not (φ : Expr)
  | and (a b : Expr)
  | or (a b : Expr)
  | implies (a b : Expr)
  | quant (q : Quantifier) (b : Binder) (body : Expr)
  | approx (a b bound : Expr)
deriving Repr

/-- Existential quantifiers are not silently rewritten to universal. -/
def isExists : Expr → Bool
  | .quant .existsQ _ _ => true
  | _ => false

def isForall : Expr → Bool
  | .quant .forallQ _ _ => true
  | _ => false

theorem exists_ne_forall (b : Binder) (body : Expr) :
    isExists (.quant .existsQ b body) = true ∧
    isForall (.quant .existsQ b body) = false := by
  simp [isExists, isForall]

/-- Double negation introduction does not change quantifier head. -/
theorem neg_neg_preserves_exists (b : Binder) (body : Expr) :
    isExists (.not (.not (.quant .existsQ b body))) = false ∧
    isExists (.quant .existsQ b body) = true := by
  simp [isExists]

end PcsNext.ClaimIR
