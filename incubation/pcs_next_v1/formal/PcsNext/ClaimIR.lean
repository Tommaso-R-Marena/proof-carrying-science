/-
  Minimal Claim IR fragment: quantifier kind preservation and association≠causation tags.
-/
namespace PcsNext.ClaimIR

inductive Quantifier where
  | forallQ
  | existsQ
deriving DecidableEq, Repr

structure Binder where
  name : String
  sort : String
deriving Repr, DecidableEq

inductive EvidenceKind where
  | association
  | causal
  | simulation
  | unknown
deriving DecidableEq, Repr

inductive Expr where
  | var (name : String)
  | const (label : String)
  | not (φ : Expr)
  | and (a b : Expr)
  | or (a b : Expr)
  | implies (a b : Expr)
  | quant (q : Quantifier) (b : Binder) (body : Expr)
  | approx (a b bound : Expr)
  | claimTagged (kind : EvidenceKind) (φ : Expr)
deriving Repr, DecidableEq

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

/-- Wrapping with ∧ does not make an existential into a universal head. -/
theorem and_preserves_exists_left (b : Binder) (body ψ : Expr) :
    isExists (.and (.quant .existsQ b body) ψ) = false ∧
    isExists (.quant .existsQ b body) = true := by
  simp [isExists]

/-- Association-tagged claims are not causal-tagged. -/
theorem association_ne_causal (φ : Expr) :
    Expr.claimTagged .association φ ≠ Expr.claimTagged .causal φ := by
  intro h
  injection h with hkind
  cases hkind

/-- Causal language over association evidence is a distinct tag pair (detector hook). -/
def causalOverAssociation (φ : Expr) : Bool :=
  match φ with
  | Expr.claimTagged .causal (Expr.claimTagged .association _) => true
  | _ => false

theorem causal_over_association_detected (ψ : Expr) :
    causalOverAssociation (Expr.claimTagged .causal (Expr.claimTagged .association ψ)) = true := by
  simp [causalOverAssociation]

theorem association_alone_not_flagged (ψ : Expr) :
    causalOverAssociation (Expr.claimTagged .association ψ) = false := by
  simp [causalOverAssociation]

end PcsNext.ClaimIR
