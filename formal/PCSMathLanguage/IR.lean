import Std

/-!
# The PCS Math IR (`pcs/experimental/prover/ir.py`): checker, typed IR and denotation

* `Expr` — the exact operator set of `ir.py` (`var`, `number`, `true`/`false`, `not`, `apply`,
  `forall`/`exists`, and the binary `OPS` table).
* `check` — a line-by-line transcription of `expression(e, variables, depth)`: depth limit 12,
  number range `0..1000` with type `Nat`/`Int`, binder names matching `NAME`, not `RESERVED`,
  **no shadowing**, operand typing exactly as in `OPS`, receiver-owned rendering.
* `TExpr Γ τ` — intrinsically typed, de Bruijn (capture-free) Math IR; `TExpr.den` — its
  compositional denotation into Lean (`Prop`, `Nat`, `Int`, `Nat → Nat`, `Nat → Prop`).
* `lower` — name-resolving lowering; `check_lowers` — every checker-accepted expression lowers,
  at the checker's type.
* `rawDen` — an independent compositional semantics of raw named expressions;
  `typed_lowering_preserves_denotation`.
-/

namespace PCSMathLanguage

inductive Ty where
  | prop | nat | int | natFn | natPred
  deriving DecidableEq, Repr

def Ty.lean : Ty → String
  | .prop => "Prop" | .nat => "Nat" | .int => "Int" | .natFn => "Nat → Nat" | .natPred => "Nat → Prop"

def Ty.key : Ty → String
  | .prop => "Prop" | .nat => "Nat" | .int => "Int" | .natFn => "NatFn" | .natPred => "NatPred"

inductive Op where
  | and | or | implies | iff | add | mul | eq | le
  deriving DecidableEq, Repr

inductive Q where
  | all | ex
  deriving DecidableEq, Repr

inductive Expr where
  | var (name : String)
  | num (value : Nat) (ty : Ty)
  | tt
  | ff
  | not (a : Expr)
  | apply (fn arg : Expr)
  | quant (q : Q) (name : String) (ty : Ty) (body : Expr)
  | bin (op : Op) (l r : Expr)
  deriving DecidableEq, Repr

/-! ## Names (`NAME`, `RESERVED`) -/

def isAsciiLetter (c : Char) : Bool := ('A' ≤ c && c ≤ 'Z') || ('a' ≤ c && c ≤ 'z')
def isAsciiAlnumU (c : Char) : Bool := isAsciiLetter c || ('0' ≤ c && c ≤ '9') || c == '_'

/-- `NAME = [A-Za-z][A-Za-z0-9_]{0,23}\Z` (ASCII only: Unicode letters are rejected). -/
def validName (s : String) : Bool :=
  match s.toList with
  | [] => false
  | c :: cs => isAsciiLetter c && cs.all isAsciiAlnumU && cs.length ≤ 23

def RESERVED : List String :=
  ["Prop", "Nat", "Int", "Type", "Sort", "True", "False", "theorem", "axiom", "def",
   "fun", "forall", "exists", "sorry", "admit", "by", "let", "in", "if", "then", "else",
   "match", "with", "where", "class", "instance", "unsafe", "namespace", "end", "import",
   "set_option"]

/-- `OPS[op] = (expected, result, symbol)`; `none` = arithmetic (`Nat`/`Int`). -/
def Op.spec : Op → Option Ty × Option Ty × String
  | .and => (some .prop, some .prop, "∧")
  | .or => (some .prop, some .prop, "∨")
  | .implies => (some .prop, some .prop, "→")
  | .iff => (some .prop, some .prop, "↔")
  | .add => (none, none, "+")
  | .mul => (none, none, "*")
  | .eq => (none, some .prop, "=")
  | .le => (none, some .prop, "≤")

def lookupTy (vars : List (String × Ty)) (n : String) : Option Ty :=
  (vars.find? (·.1 == n)).map (·.2)

/-! ## The checker: transcription of `expression` -/

/-- The depth guard `if depth > 12: raise`. -/
def gd {α : Type} (depth : Nat) (x : Option α) : Option α := if depth > 12 then none else x

def check (vars : List (String × Ty)) (depth : Nat) : Expr → Option (Ty × String)
  | .var n => gd depth <| (lookupTy vars n).map fun t => (t, n)
  | .num n t => gd depth <|
      if n ≤ 1000 && (t == .nat || t == .int) then some (t, s!"({n} : {t.key})") else none
  | .tt => gd depth <| some (.prop, "True")
  | .ff => gd depth <| some (.prop, "False")
  | .not a => gd depth <| match check vars (depth + 1) a with
      | some (.prop, s) => some (.prop, s!"(¬ {s})")
      | _ => none
  | .apply f a => gd depth <| match check vars (depth + 1) f, check vars (depth + 1) a with
      | some (.natFn, sf), some (.nat, sa) => some (.nat, s!"({sf} {sa})")
      | some (.natPred, sf), some (.nat, sa) => some (.prop, s!"({sf} {sa})")
      | _, _ => none
  | .quant q n t b => gd depth <|
      if !validName n || RESERVED.contains n || (lookupTy vars n).isSome then none else
      match check ((n, t) :: vars) (depth + 1) b with
      | some (.prop, sb) =>
        some (.prop, s!"({if q == .all then "∀" else "∃"} ({n} : {t.lean}), {sb})")
      | _ => none
  | .bin op l r => gd depth <| match check vars (depth + 1) l, check vars (depth + 1) r with
      | some (lt, sl), some (rt, sr) =>
        if lt == rt && (match op.spec.1 with
          | some x => lt == x
          | none => lt == .nat || lt == .int)
        then some (op.spec.2.1.getD lt, s!"({sl} {op.spec.2.2} {sr})") else none
      | _, _ => none

/-! ## Intrinsically typed IR -/

abbrev Val : Ty → Type
  | .prop => Prop
  | .nat => Nat
  | .int => Int
  | .natFn => Nat → Nat
  | .natPred => Nat → Prop

inductive Var : List Ty → Ty → Type where
  | zero {Γ τ} : Var (τ :: Γ) τ
  | succ {Γ τ σ} : Var Γ τ → Var (σ :: Γ) τ
  deriving DecidableEq

def Env : List Ty → Type
  | [] => Unit
  | τ :: Γ => Val τ × Env Γ

def Var.get : {Γ : List Ty} → {τ : Ty} → Var Γ τ → Env Γ → Val τ
  | _ :: _, _, .zero, (v, _) => v
  | _ :: _, _, .succ x, (_, ρ) => x.get ρ

inductive TExpr : List Ty → Ty → Type where
  | var {Γ τ} : Var Γ τ → TExpr Γ τ
  | natLit {Γ} : Nat → TExpr Γ .nat
  | intLit {Γ} : Nat → TExpr Γ .int
  | tt {Γ} : TExpr Γ .prop
  | ff {Γ} : TExpr Γ .prop
  | not {Γ} : TExpr Γ .prop → TExpr Γ .prop
  | appF {Γ} : TExpr Γ .natFn → TExpr Γ .nat → TExpr Γ .nat
  | appP {Γ} : TExpr Γ .natPred → TExpr Γ .nat → TExpr Γ .prop
  | all {Γ} (τ : Ty) : TExpr (τ :: Γ) .prop → TExpr Γ .prop
  | ex {Γ} (τ : Ty) : TExpr (τ :: Γ) .prop → TExpr Γ .prop
  | and {Γ} : TExpr Γ .prop → TExpr Γ .prop → TExpr Γ .prop
  | or {Γ} : TExpr Γ .prop → TExpr Γ .prop → TExpr Γ .prop
  | imp {Γ} : TExpr Γ .prop → TExpr Γ .prop → TExpr Γ .prop
  | iff {Γ} : TExpr Γ .prop → TExpr Γ .prop → TExpr Γ .prop
  | addN {Γ} : TExpr Γ .nat → TExpr Γ .nat → TExpr Γ .nat
  | addI {Γ} : TExpr Γ .int → TExpr Γ .int → TExpr Γ .int
  | mulN {Γ} : TExpr Γ .nat → TExpr Γ .nat → TExpr Γ .nat
  | mulI {Γ} : TExpr Γ .int → TExpr Γ .int → TExpr Γ .int
  | eqN {Γ} : TExpr Γ .nat → TExpr Γ .nat → TExpr Γ .prop
  | eqI {Γ} : TExpr Γ .int → TExpr Γ .int → TExpr Γ .prop
  | leN {Γ} : TExpr Γ .nat → TExpr Γ .nat → TExpr Γ .prop
  | leI {Γ} : TExpr Γ .int → TExpr Γ .int → TExpr Γ .prop

def TExpr.den : {Γ : List Ty} → {τ : Ty} → TExpr Γ τ → Env Γ → Val τ
  | _, _, .var x, ρ => x.get ρ
  | _, _, .natLit n, _ => (n : Nat)
  | _, _, .intLit n, _ => ((n : Nat) : Int)
  | _, _, .tt, _ => True
  | _, _, .ff, _ => False
  | _, _, .not a, ρ => ¬ (a.den ρ : Prop)
  | _, _, .appF f a, ρ => (f.den ρ : Nat → Nat) (a.den ρ)
  | _, _, .appP f a, ρ => (f.den ρ : Nat → Prop) (a.den ρ)
  | _, _, .all τ b, ρ => ∀ v : Val τ, (b.den (v, ρ) : Prop)
  | _, _, .ex τ b, ρ => ∃ v : Val τ, (b.den (v, ρ) : Prop)
  | _, _, .and a b, ρ => (a.den ρ : Prop) ∧ (b.den ρ : Prop)
  | _, _, .or a b, ρ => (a.den ρ : Prop) ∨ (b.den ρ : Prop)
  | _, _, .imp a b, ρ => (fun (p q : Prop) => p → q) (a.den ρ) (b.den ρ)
  | _, _, .iff a b, ρ => ((a.den ρ : Prop) ↔ (b.den ρ : Prop))
  | _, _, .addN a b, ρ => (a.den ρ : Nat) + (b.den ρ : Nat)
  | _, _, .addI a b, ρ => (a.den ρ : Int) + (b.den ρ : Int)
  | _, _, .mulN a b, ρ => (a.den ρ : Nat) * (b.den ρ : Nat)
  | _, _, .mulI a b, ρ => (a.den ρ : Int) * (b.den ρ : Int)
  | _, _, .eqN a b, ρ => (a.den ρ : Nat) = (b.den ρ : Nat)
  | _, _, .eqI a b, ρ => (a.den ρ : Int) = (b.den ρ : Int)
  | _, _, .leN a b, ρ => (a.den ρ : Nat) ≤ (b.den ρ : Nat)
  | _, _, .leI a b, ρ => (a.den ρ : Int) ≤ (b.den ρ : Int)

/-! ## Lowering (name resolution to de Bruijn variables) -/

def lookupVar : (vars : List (String × Ty)) → String → Option (Σ τ, Var (vars.map (·.2)) τ)
  | [], _ => none
  | (m, t) :: vs, n =>
    if m == n then some ⟨t, .zero⟩ else
    (lookupVar vs n).map fun ⟨τ, x⟩ => ⟨τ, .succ x⟩

/-- Combine two lowered operands of the same required type. -/
def lowerBin {Γ : List Ty} (op : Op) : (Σ τ, TExpr Γ τ) → (Σ τ, TExpr Γ τ) → Option (Σ τ, TExpr Γ τ)
  | ⟨.prop, a⟩, ⟨.prop, b⟩ => match op with
    | .and => some ⟨.prop, .and a b⟩
    | .or => some ⟨.prop, .or a b⟩
    | .implies => some ⟨.prop, .imp a b⟩
    | .iff => some ⟨.prop, .iff a b⟩
    | _ => none
  | ⟨.nat, a⟩, ⟨.nat, b⟩ => match op with
    | .add => some ⟨.nat, .addN a b⟩
    | .mul => some ⟨.nat, .mulN a b⟩
    | .eq => some ⟨.prop, .eqN a b⟩
    | .le => some ⟨.prop, .leN a b⟩
    | _ => none
  | ⟨.int, a⟩, ⟨.int, b⟩ => match op with
    | .add => some ⟨.int, .addI a b⟩
    | .mul => some ⟨.int, .mulI a b⟩
    | .eq => some ⟨.prop, .eqI a b⟩
    | .le => some ⟨.prop, .leI a b⟩
    | _ => none
  | _, _ => none

def lower : (vars : List (String × Ty)) → Expr → Option (Σ τ, TExpr (vars.map (·.2)) τ)
  | vars, .var n => (lookupVar vars n).map fun ⟨τ, x⟩ => ⟨τ, .var x⟩
  | _, .num n t => match t with
    | .nat => some ⟨.nat, .natLit n⟩
    | .int => some ⟨.int, .intLit n⟩
    | _ => none
  | _, .tt => some ⟨.prop, .tt⟩
  | _, .ff => some ⟨.prop, .ff⟩
  | vars, .not a => match lower vars a with
    | some ⟨.prop, a'⟩ => some ⟨.prop, .not a'⟩
    | _ => none
  | vars, .apply f a => match lower vars f, lower vars a with
    | some ⟨.natFn, f'⟩, some ⟨.nat, a'⟩ => some ⟨.nat, .appF f' a'⟩
    | some ⟨.natPred, f'⟩, some ⟨.nat, a'⟩ => some ⟨.prop, .appP f' a'⟩
    | _, _ => none
  | vars, .quant q n t b => match lower ((n, t) :: vars) b with
    | some ⟨.prop, b'⟩ => some ⟨.prop, match q with | .all => .all t b' | .ex => .ex t b'⟩
    | _ => none
  | vars, .bin op l r => match lower vars l, lower vars r with
    | some x, some y => lowerBin op x y
    | _, _ => none

theorem lookupVar_ty : ∀ (vars : List (String × Ty)) (n : String),
    (lookupVar vars n).map (·.1) = lookupTy vars n
  | [], _ => rfl
  | (m, t) :: vs, n => by
      simp only [lookupVar, lookupTy, List.find?_cons]
      by_cases h : (m == n) = true
      · simp [h]
      · simp only [h, if_false, Bool.false_eq_true]
        rw [Option.map_map]
        have := lookupVar_ty vs n
        simp only [lookupTy] at this
        rw [← this]; cases lookupVar vs n <;> rfl

theorem lowerBin_ty {Γ : List Ty} (op : Op) (x y : Σ τ, TExpr Γ τ) (hx : x.1 = y.1)
    (hok : (match op.spec.1 with | some t => x.1 == t | none => x.1 == .nat || x.1 == .int) = true) :
    (lowerBin op x y).map (·.1) = some (op.spec.2.1.getD x.1) := by
  obtain ⟨tx, a⟩ := x
  obtain ⟨ty, b⟩ := y
  simp only at hx; subst hx
  cases tx <;> cases op <;> simp_all [Op.spec, lowerBin]

theorem ite_some {α : Type} {c : Bool} {x y : α} (h : (if c = true then some x else none) = some y) :
    c = true ∧ x = y := by
  cases c <;> simp_all

/-- **Every checker-accepted expression lowers to the typed IR at the checker's type.** -/
theorem check_lowers : ∀ (e : Expr) (vars : List (String × Ty)) (d : Nat) (τ : Ty) (s : String),
    check vars d e = some (τ, s) → (lower vars e).map (·.1) = some τ := by
  intro e
  induction e with
  | var n =>
      intro vars d τ s h
      simp only [check, gd] at h; split at h; · cases h
      simp only [Option.map_eq_some_iff] at h
      obtain ⟨t, ht, he⟩ := h; cases he
      simp only [lower, Option.map_map]
      rw [← ht, ← lookupVar_ty]; rfl
  | num n t =>
      intro vars d τ s h
      simp only [check, gd] at h; split at h; · cases h
      split at h
      · rename_i hc; cases h
        simp only [Bool.and_eq_true, Bool.or_eq_true, beq_iff_eq] at hc
        rcases hc.2 with rfl | rfl <;> rfl
      · cases h
  | tt => intro vars d τ s h; simp only [check, gd] at h; split at h; · cases h
          cases h; rfl
  | ff => intro vars d τ s h; simp only [check, gd] at h; split at h; · cases h
          cases h; rfl
  | not a ih =>
      intro vars d τ s h
      simp only [check, gd] at h; split at h; · cases h
      split at h
      · rename_i sa hsa; cases h
        have := ih vars (d + 1) .prop sa hsa
        simp only [lower]
        match hl : lower vars a, this with
        | some ⟨.prop, a'⟩, _ => rfl
      · cases h
  | apply f a ihf iha =>
      intro vars d τ s h
      simp only [check, gd] at h; split at h; · cases h
      split at h
      · rename_i sf sa hf ha; cases h
        have h1 := ihf vars (d + 1) _ _ hf; have h2 := iha vars (d + 1) _ _ ha
        simp only [lower]
        match lower vars f, lower vars a, h1, h2 with
        | some ⟨.natFn, _⟩, some ⟨.nat, _⟩, _, _ => rfl
      · rename_i sf sa hf ha; cases h
        have h1 := ihf vars (d + 1) _ _ hf; have h2 := iha vars (d + 1) _ _ ha
        simp only [lower]
        match lower vars f, lower vars a, h1, h2 with
        | some ⟨.natPred, _⟩, some ⟨.nat, _⟩, _, _ => rfl
      · cases h
  | quant q n t b ih =>
      intro vars d τ s h
      simp only [check, gd] at h; split at h; · cases h
      split at h; · cases h
      split at h
      · rename_i sb hb; cases h
        have := ih ((n, t) :: vars) (d + 1) .prop sb hb
        simp only [lower]
        match lower ((n, t) :: vars) b, this with
        | some ⟨.prop, _⟩, _ => rfl
      · cases h
  | bin op l r ihl ihr =>
      intro vars d τ s h
      simp only [check, gd] at h; split at h; · cases h
      split at h
      · rename_i lt sl rt sr hl hr
        have h1 := ihl vars (d + 1) _ _ hl; have h2 := ihr vars (d + 1) _ _ hr
        simp only [lower]
        obtain ⟨hall, hxy⟩ := ite_some h
        cases hxy
        match el : lower vars l, er : lower vars r, h1, h2 with
        | some x, some y, h1, h2 =>
          simp only [Option.map_some, Option.some.injEq] at h1 h2
          simp only [Bool.and_eq_true, beq_iff_eq] at hall
          simp only
          rw [lowerBin_ty op x y (by rw [h1, h2, hall.1]) (by rw [h1]; exact hall.2), h1]
      · cases h

/-! ## Independent raw semantics of named expressions -/

abbrev SVal := Σ τ : Ty, Val τ

/-- Named environments (newest binding first, as Python's `{**variables, n: t}`). -/
abbrev NEnv := List (String × SVal)

def NEnv.lookup (ρ : NEnv) (n : String) : Option SVal := (ρ.find? (·.1 == n)).map (·.2)

def asProp : Option SVal → Prop
  | some ⟨.prop, p⟩ => p
  | _ => False

def binDen (op : Op) : SVal → SVal → Option SVal
  | ⟨.prop, a⟩, ⟨.prop, b⟩ => match op with
    | .and => some ⟨.prop, (a : Prop) ∧ (b : Prop)⟩
    | .or => some ⟨.prop, (a : Prop) ∨ (b : Prop)⟩
    | .implies => some ⟨.prop, (fun (p q : Prop) => p → q) a b⟩
    | .iff => some ⟨.prop, ((a : Prop) ↔ (b : Prop))⟩
    | _ => none
  | ⟨.nat, a⟩, ⟨.nat, b⟩ => match op with
    | .add => some ⟨.nat, (a : Nat) + (b : Nat)⟩
    | .mul => some ⟨.nat, (a : Nat) * (b : Nat)⟩
    | .eq => some ⟨.prop, (a : Nat) = (b : Nat)⟩
    | .le => some ⟨.prop, (a : Nat) ≤ (b : Nat)⟩
    | _ => none
  | ⟨.int, a⟩, ⟨.int, b⟩ => match op with
    | .add => some ⟨.int, (a : Int) + (b : Int)⟩
    | .mul => some ⟨.int, (a : Int) * (b : Int)⟩
    | .eq => some ⟨.prop, (a : Int) = (b : Int)⟩
    | .le => some ⟨.prop, (a : Int) ≤ (b : Int)⟩
    | _ => none
  | _, _ => none

def rawDen : NEnv → Expr → Option SVal
  | ρ, .var n => ρ.lookup n
  | _, .num n t => match t with
    | .nat => some ⟨.nat, (n : Nat)⟩
    | .int => some ⟨.int, ((n : Nat) : Int)⟩
    | _ => none
  | _, .tt => some ⟨.prop, True⟩
  | _, .ff => some ⟨.prop, False⟩
  | ρ, .not a => match rawDen ρ a with
    | some ⟨.prop, p⟩ => some ⟨.prop, ¬ (p : Prop)⟩
    | _ => none
  | ρ, .apply f a => match rawDen ρ f, rawDen ρ a with
    | some ⟨.natFn, g⟩, some ⟨.nat, x⟩ => some ⟨.nat, (g : Nat → Nat) x⟩
    | some ⟨.natPred, g⟩, some ⟨.nat, x⟩ => some ⟨.prop, (g : Nat → Prop) x⟩
    | _, _ => none
  | ρ, .quant q n t b => match q with
    | .all => some ⟨.prop, ∀ v : Val t, asProp (rawDen ((n, ⟨t, v⟩) :: ρ) b)⟩
    | .ex => some ⟨.prop, ∃ v : Val t, asProp (rawDen ((n, ⟨t, v⟩) :: ρ) b)⟩
  | ρ, .bin op l r => match rawDen ρ l, rawDen ρ r with
    | some x, some y => binDen op x y
    | _, _ => none

/-- A named environment realises a typed environment. -/
def Realises : (vars : List (String × Ty)) → NEnv → Env (vars.map (·.2)) → Prop
  | [], ρ, () => ρ = []
  | (n, t) :: vs, ρ, (v, η) => ∃ ρ', ρ = (n, ⟨t, v⟩) :: ρ' ∧ Realises vs ρ' η

theorem lookup_realises : ∀ (vars : List (String × Ty)) (ρ : NEnv) (η : Env (vars.map (·.2)))
    (n : String) (τ : Ty) (x : Var (vars.map (·.2)) τ),
    Realises vars ρ η → lookupVar vars n = some ⟨τ, x⟩ → ρ.lookup n = some ⟨τ, x.get η⟩
  | [], _, _, _, _, _, _, h => by simp [lookupVar] at h
  | (m, t) :: vs, ρ, (v, η), n, τ, x, hR, h => by
      obtain ⟨ρ', rfl, hR'⟩ := hR
      simp only [lookupVar] at h
      by_cases hm : (m == n) = true
      · simp only [hm, if_true, Option.some.injEq] at h
        cases h
        simp [NEnv.lookup, List.find?_cons, hm, Var.get]
      · simp only [hm, Bool.false_eq_true, if_false, Option.map_eq_some_iff] at h
        obtain ⟨⟨τ', y⟩, hy, he⟩ := h
        cases he
        have := lookup_realises vs ρ' η n _ y hR' hy
        simp only [NEnv.lookup, List.find?_cons, hm, Bool.false_eq_true] at this ⊢
        simpa [Var.get] using this

theorem lowerBin_den {vars : List (String × Ty)} (op : Op) (η : Env (vars.map (·.2)))
    (x y : Σ τ, TExpr (vars.map (·.2)) τ) (z : Σ τ, TExpr (vars.map (·.2)) τ)
    (h : lowerBin op x y = some z) :
    binDen op ⟨x.1, x.2.den η⟩ ⟨y.1, y.2.den η⟩ = some ⟨z.1, z.2.den η⟩ := by
  obtain ⟨tx, a⟩ := x
  obtain ⟨ty, b⟩ := y
  cases tx <;> cases ty <;> cases op <;> simp [lowerBin] at h <;> subst h <;> rfl

/-- **Typed lowering preserves denotation.** -/
theorem typed_lowering_preserves_denotation : ∀ (e : Expr) (vars : List (String × Ty)) (ρ : NEnv)
    (η : Env (vars.map (·.2))) (τ : Ty) (t : TExpr (vars.map (·.2)) τ),
    Realises vars ρ η → lower vars e = some ⟨τ, t⟩ → rawDen ρ e = some ⟨τ, t.den η⟩ := by
  intro e
  induction e with
  | var n =>
      intro vars ρ η τ t hR h
      simp only [lower, Option.map_eq_some_iff] at h
      obtain ⟨⟨τ', x⟩, hx, he⟩ := h
      cases he
      exact lookup_realises vars ρ η n _ x hR hx
  | num n ty =>
      intro vars ρ η τ t hR h
      cases ty <;> simp [lower] at h <;> obtain ⟨rfl, h⟩ := h <;> cases h <;> rfl
  | tt => intro vars ρ η τ t hR h; simp [lower] at h; obtain ⟨rfl, h⟩ := h; cases h; rfl
  | ff => intro vars ρ η τ t hR h; simp [lower] at h; obtain ⟨rfl, h⟩ := h; cases h; rfl
  | not a ih =>
      intro vars ρ η τ t hR h
      simp only [lower] at h
      split at h
      · rename_i a' ha; cases h
        simp [rawDen, ih vars ρ η .prop a' hR ha, TExpr.den]
      · cases h
  | apply f a ihf iha =>
      intro vars ρ η τ t hR h
      simp only [lower] at h
      split at h
      · rename_i f' a' hf ha; cases h
        simp [rawDen, ihf vars ρ η _ f' hR hf, iha vars ρ η _ a' hR ha, TExpr.den]
      · rename_i f' a' hf ha; cases h
        simp [rawDen, ihf vars ρ η _ f' hR hf, iha vars ρ η _ a' hR ha, TExpr.den]
      · cases h
  | quant q n ty b ih =>
      intro vars ρ η τ t hR h
      simp only [lower] at h
      split at h
      · rename_i b' hb
        cases h
        have key : ∀ v : Val ty, asProp (rawDen ((n, ⟨ty, v⟩) :: ρ) b) = (b'.den (v, η) : Prop) := by
          intro v
          rw [ih ((n, ty) :: vars) ((n, ⟨ty, v⟩) :: ρ) (v, η) .prop b' ⟨ρ, rfl, hR⟩ hb]
          rfl
        cases q <;> simp only [rawDen, TExpr.den, key]
      · cases h
  | bin op l r ihl ihr =>
      intro vars ρ η τ t hR h
      simp only [lower] at h
      split at h
      · rename_i x y hl hr
        obtain ⟨tl, l'⟩ := x
        obtain ⟨tr, r'⟩ := y
        simp only [rawDen, ihl vars ρ η tl l' hR hl, ihr vars ρ η tr r' hR hr]
        exact lowerBin_den op η ⟨tl, l'⟩ ⟨tr, r'⟩ ⟨τ, t⟩ h
      · cases h

end PCSMathLanguage
