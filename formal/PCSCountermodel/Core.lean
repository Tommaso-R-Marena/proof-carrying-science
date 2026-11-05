import Std

/-!
# PCS Countermodel Lab — typed finite first-order core

* `Formula k`: well-scoped first-order formulas with de Bruijn variables `Fin k`.
  Quantifier bodies live in `Formula (k+1)`; variable `0` of the body is the new binder.
* `World n`: interpretations of `P Q : Fin n → Bool` and `R : Fin n → Fin n → Bool`.
* `evalBool`: executable Boolean evaluator; quantifiers enumerate `List.finRange n`.
* `Holds`: independent propositional (Tarskian) satisfaction with real `∀`/`∃` over `Fin n`.
* `evalBool_iff_holds`: the two agree for every `n`, world, environment and formula.
* `checker`: Boolean disagreement of two closed formulas; `checker_iff` is its exact
  soundness/completeness statement for a fixed world.
-/

namespace PCSCountermodel

/-- The two unary predicate symbols of the game. -/
inductive UPred where
  | P
  | Q
  deriving DecidableEq, Repr

/-- Well-scoped first-order formulas over `k` free de Bruijn variables. -/
inductive Formula : Nat → Type where
  | pred {k : Nat} (p : UPred) (x : Fin k) : Formula k
  | rel  {k : Nat} (x y : Fin k) : Formula k
  | not  {k : Nat} (a : Formula k) : Formula k
  | and  {k : Nat} (a b : Formula k) : Formula k
  | or   {k : Nat} (a b : Formula k) : Formula k
  | imp  {k : Nat} (a b : Formula k) : Formula k
  | all  {k : Nat} (f : Formula (k + 1)) : Formula k
  | ex   {k : Nat} (f : Formula (k + 1)) : Formula k
  deriving Repr

/-- A finite world: domain `Fin n`, unary predicates `P`, `Q`, binary relation `R`. -/
structure World (n : Nat) where
  P : Fin n → Bool
  Q : Fin n → Bool
  R : Fin n → Fin n → Bool

/-- Read a unary predicate symbol in a world. -/
def World.unary {n : Nat} (w : World n) : UPred → Fin n → Bool
  | .P => w.P
  | .Q => w.Q

/-- Environments assign a domain element to each of the `k` de Bruijn variables. -/
abbrev Env (k n : Nat) := Fin k → Fin n

/-- The empty environment (for closed formulas). -/
def emptyEnv {n : Nat} : Env 0 n := fun i => Fin.elim0 i

/-- Binder extension: the new variable `0` is bound to `d`; outer variable `i` becomes `i+1`
and keeps its old value. -/
def extend {k n : Nat} (e : Env k n) (d : Fin n) : Env (k + 1) n :=
  fun i => Fin.cases d e i

@[simp] theorem extend_zero {k n : Nat} (e : Env k n) (d : Fin n) :
    extend e d 0 = d := rfl

@[simp] theorem extend_succ {k n : Nat} (e : Env k n) (d : Fin n) (i : Fin k) :
    extend e d i.succ = e i := rfl

/-- Executable Boolean evaluation. Quantifiers enumerate the whole domain. -/
def evalBool {n : Nat} (w : World n) : {k : Nat} → Env k n → Formula k → Bool
  | _, e, .pred p x => w.unary p (e x)
  | _, e, .rel x y  => w.R (e x) (e y)
  | _, e, .not a    => !(evalBool w e a)
  | _, e, .and a b  => evalBool w e a && evalBool w e b
  | _, e, .or a b   => evalBool w e a || evalBool w e b
  | _, e, .imp a b  => !(evalBool w e a) || evalBool w e b
  | _, e, .all f    => (List.finRange n).all (fun d => evalBool w (extend e d) f)
  | _, e, .ex f     => (List.finRange n).any (fun d => evalBool w (extend e d) f)

/-- Independent propositional satisfaction (not defined via `evalBool`). -/
def Holds {n : Nat} (w : World n) : {k : Nat} → Env k n → Formula k → Prop
  | _, e, .pred p x => w.unary p (e x) = true
  | _, e, .rel x y  => w.R (e x) (e y) = true
  | _, e, .not a    => ¬ Holds w e a
  | _, e, .and a b  => Holds w e a ∧ Holds w e b
  | _, e, .or a b   => Holds w e a ∨ Holds w e b
  | _, e, .imp a b  => Holds w e a → Holds w e b
  | _, e, .all f    => ∀ d : Fin n, Holds w (extend e d) f
  | _, e, .ex f     => ∃ d : Fin n, Holds w (extend e d) f

/-- **Evaluation correctness.** For every domain size, world, environment and formula,
the executable evaluator returns `true` exactly when the formula holds. -/
theorem evalBool_iff_holds {n : Nat} (w : World n) :
    ∀ {k : Nat} (e : Env k n) (f : Formula k), evalBool w e f = true ↔ Holds w e f := by
  intro k e f
  induction f with
  | pred p x => simp [evalBool, Holds]
  | rel x y => simp [evalBool, Holds]
  | not a ih => simp [evalBool, Holds, ← ih]
  | and a b iha ihb => simp [evalBool, Holds, ← iha, ← ihb]
  | or a b iha ihb => simp [evalBool, Holds, ← iha, ← ihb]
  | imp a b iha ihb =>
      simp only [evalBool, Holds, ← iha, ← ihb]
      cases evalBool w e a <;> cases evalBool w e b <;> simp
  | all f ih => simp [evalBool, Holds, List.all_eq_true, List.mem_finRange, ih]
  | ex f ih => simp [evalBool, Holds, List.any_eq_true, List.mem_finRange, ih]

/-- Satisfaction is decidable, via the (proved-correct) evaluator. -/
instance instDecidableHolds {n k : Nat} (w : World n) (e : Env k n) (f : Formula k) :
    Decidable (Holds w e f) :=
  decidable_of_iff _ (evalBool_iff_holds w e f)

/-- The countermodel checker for closed formulas: the two evaluations disagree. -/
def checker {n : Nat} (w : World n) (original proposal : Formula 0) : Bool :=
  evalBool w emptyEnv original != evalBool w emptyEnv proposal

/-- **Witness acceptance (soundness and completeness for a fixed world).** -/
theorem checker_iff {n : Nat} (w : World n) (original proposal : Formula 0) :
    checker w original proposal = true ↔
      ¬ (Holds w emptyEnv original ↔ Holds w emptyEnv proposal) := by
  rw [← evalBool_iff_holds w emptyEnv original, ← evalBool_iff_holds w emptyEnv proposal]
  unfold checker
  cases evalBool w emptyEnv original <;> cases evalBool w emptyEnv proposal <;> simp

end PCSCountermodel
