import PCS.V2.ExplanationIR
import PCS.V2.TranslationContract

/-!
# PCS v3 — a formal model of the generated Lean syntax and its name resolution

v2's `ElaborationBridge` ("the kernel-proved rendering of a claim means the claim in the intended
model") was a single trusted hypothesis, discharged inside Lean only for the fixture registry.
This file replaces most of it by a **general, proved** correspondence for every registry and every
claim satisfying an executable syntactic-safety gate, and isolates the remaining trust in a much
narrower statement about Lean's parser/elaborator.

1. `LTerm` / `LProp` / `LDecl` — the abstract syntax of the Lean text PCS generates.  Identifiers
   are raw strings, exactly as they appear in the text.
2. `readClaim R c` — the syntax tree of the rendering, and **`renderClaimLean_eq_print`**: the
   string produced by `renderClaimLean` (the text that is elaborated, receipted and kernel-checked)
   is *literally* the printing of `readClaim R c`.
3. `LeanEnvModel` — a semantic model of a (fingerprinted) Lean environment restricted to the
   fragment: carriers of named types, interpretations of named constants.
4. `LProp.denote` — the meaning of the syntax **with Lean's name-resolution discipline**: an
   identifier denotes a local variable if one of that name is in scope; an identifier whose first
   dotted component is a local variable is a *projection* (outside the fragment, no meaning);
   otherwise it denotes the global constant of that exact name.  A local binder can therefore
   capture a constant, a type name or `True`/`False`.
5. `leanSyntaxSafeB R c` — the executable anti-capture gate: every binder is a plain ASCII
   identifier that is not a Lean keyword and differs from every registry symbol id, every component
   of every registry Lean name / Lean type and from `True`/`False`; every registry Lean name and
   type is a dotted ASCII identifier; every symbol and sort used resolves uniquely.
6. **`lean_reading_correspondence`** — for *every* registry `R`, Lean environment model `E` and
   closed claim `c` passing the gate, the generated syntax means exactly what the claim means in
   the model induced by `E` and `R`.
7. `capture_breaks_correspondence` — the gate is necessary: a binder named like a grounded constant
   makes the rendered syntax mean something else.

**Remaining trusted condition** (`LeanFrontendFaithful`, used in `PCS.V2.AssuranceV3`): for texts
printed from gate-passing syntax trees, Lean's parser and elaborator, in the environment whose
fingerprint is bound into the receipts, produce the proposition `LProp.denote` describes.  This is
checked executably on the real environment by `tools/CheckElaborationV3.lean` (structural
comparison of the elaborated `Expr` with an `Expr` built from the syntax tree), not proved.
-/

set_option autoImplicit false

namespace PCS.V2.Semantic.LeanSyntax

open PCS.V2.Semantic

/-! ## Identifier safety -/

def leanKeywords : List String :=
  ["fun", "forall", "exists", "let", "have", "show", "from", "by", "do", "then", "else", "if",
   "match", "with", "at", "in", "Type", "Sort", "Prop", "theorem", "lemma", "def", "where",
   "structure", "open", "namespace", "end", "section", "variable", "universe", "import", "calc",
   "deriving", "instance", "class", "example", "axiom", "abbrev", "macro", "syntax", "notation",
   "infix", "infixl", "infixr", "prefix", "postfix", "mutual", "private", "protected",
   "noncomputable", "partial", "unsafe", "set_option", "attribute", "local", "scoped", "rec",
   "sorry", "admit", "True", "False", "Not", "And", "Or", "Iff", "Eq", "Ne", "Exists", "this"]

def identStart (c : Char) : Bool :=
  ('a' ≤ c && c ≤ 'z') || ('A' ≤ c && c ≤ 'Z') || c == '_'

def identRest (c : Char) : Bool :=
  identStart c || ('0' ≤ c && c ≤ '9') || c == '\''

/-- A plain ASCII Lean identifier that is not a keyword. -/
def isAtomicIdent (s : String) : Bool :=
  match s.toList with
  | [] => false
  | c :: cs => identStart c && cs.all identRest && !leanKeywords.contains s

/-- A dotted identifier `A.B.c` with atomic components. -/
def isDottedIdent (s : String) : Bool := (s.splitOn ".").all isAtomicIdent

/-- First dotted component. -/
def headComp (n : String) : String := (n.splitOn ".").headD n

/-- Every dotted component of every registry Lean name and type. -/
def registryComponents (R : Registry) : List String :=
  (R.symbols.map (·.leanName) ++ R.sorts.map (·.leanType)).flatMap (fun n => n.splitOn ".")

/-- Names a binder must avoid. -/
def reservedNames (R : Registry) : List String :=
  R.symbols.map (·.id) ++ R.symbols.map (·.leanName) ++ R.sorts.map (·.leanType) ++
    registryComponents R ++ ["True", "False"]

/-- Sorts used by quantifiers of a formula. -/
def Formula.quantSorts : Formula → List SortId
  | .tt | .ff | .unsupported _ | .pred _ _ | .eq _ _ | .ne _ _ => []
  | .not φ => Formula.quantSorts φ
  | .quant _ _ s φ => s :: Formula.quantSorts φ
  | .and φ ψ | .or φ ψ | .imp φ ψ => Formula.quantSorts φ ++ Formula.quantSorts ψ

/-- All binder names of a claim (parameters and quantified variables). -/
def claimBinders (c : SemanticClaim) : List String :=
  c.params.map (·.name) ++ (c.assumptions ++ [c.conclusion]).flatMap Formula.binders

/-- All sorts a claim's rendering mentions. -/
def claimSorts (c : SemanticClaim) : List SortId :=
  c.params.map (·.sort) ++ (c.assumptions ++ [c.conclusion]).flatMap Formula.quantSorts

/-- **The anti-capture / syntactic-safety gate.** -/
def leanSyntaxSafeB (R : Registry) (c : SemanticClaim) : Bool :=
  (claimBinders c).all (fun x => isAtomicIdent x && !(reservedNames R).contains x) &&
  R.symbols.all (fun e => isDottedIdent e.leanName) &&
  R.sorts.all (fun e => isDottedIdent e.leanType) &&
  c.symbols.all (fun f => (R.resolve f).isSome) &&
  (claimSorts c).all (fun s => (R.resolveSort s).isSome)

/-! ## Syntax of the generated Lean text -/

inductive LTerm where
  | ident (n : String)
  | app (head : String) (args : List LTerm)
  deriving Repr, Inhabited

inductive LProp where
  | tt
  | ff
  | atom (head : String) (args : List LTerm)
  | eq (a b : LTerm)
  | ne (a b : LTerm)
  | not (p : LProp)
  | and (p q : LProp)
  | or (p q : LProp)
  | imp (p q : LProp)
  | all (x ty : String) (p : LProp)
  | ex (x ty : String) (p : LProp)
  | unsupported (tag : String)
  deriving Repr, Inhabited

structure LDecl where
  binders : List (String × String)
  hyps : List LProp
  concl : LProp
  deriving Repr, Inhabited

mutual
def LTerm.print : LTerm → String
  | .ident n => n
  | .app h args => "(" ++ h ++ LTerm.printArgs args ++ ")"
def LTerm.printArgs : List LTerm → String
  | [] => ""
  | t :: ts => " " ++ LTerm.print t ++ LTerm.printArgs ts
end

def LProp.print : LProp → String
  | .tt => "True"
  | .ff => "False"
  | .atom h [] => h
  | .atom h (a :: as) => "(" ++ h ++ LTerm.printArgs (a :: as) ++ ")"
  | .eq a b => "(" ++ a.print ++ " = " ++ b.print ++ ")"
  | .ne a b => "(" ++ a.print ++ " ≠ " ++ b.print ++ ")"
  | .not p => "(¬ " ++ p.print ++ ")"
  | .and p q => "(" ++ p.print ++ " ∧ " ++ q.print ++ ")"
  | .or p q => "(" ++ p.print ++ " ∨ " ++ q.print ++ ")"
  | .imp p q => "(" ++ p.print ++ " → " ++ q.print ++ ")"
  | .all x T p => "(∀ (" ++ x ++ " : " ++ T ++ "), " ++ p.print ++ ")"
  | .ex x T p => "(∃ (" ++ x ++ " : " ++ T ++ "), " ++ p.print ++ ")"
  | .unsupported t => "(PCS_UNSUPPORTED_CONSTRUCT \"" ++ t ++ "\")"

def LDecl.print (d : LDecl) : String :=
  let body := d.hyps.foldr (fun a acc => a.print ++ " → " ++ acc) d.concl.print
  match d.binders with
  | [] => body
  | bs => "∀" ++ String.join (bs.map (fun b => " (" ++ b.1 ++ " : " ++ b.2 ++ ")")) ++ ", " ++ body

/-! ## Reading a claim as Lean syntax -/

mutual
def readTerm (R : Registry) : Term → LTerm
  | .var x => .ident x
  | .app f [] => .ident (leanNameOf R f)
  | .app f (a :: as) => .app (leanNameOf R f) (readTerms R (a :: as))
def readTerms (R : Registry) : List Term → List LTerm
  | [] => []
  | t :: ts => readTerm R t :: readTerms R ts
end

def readFormula (R : Registry) : Formula → LProp
  | .tt => .tt
  | .ff => .ff
  | .pred p args => .atom (leanNameOf R p) (readTerms R args)
  | .eq a b => .eq (readTerm R a) (readTerm R b)
  | .ne a b => .ne (readTerm R a) (readTerm R b)
  | .not φ => .not (readFormula R φ)
  | .and φ ψ => .and (readFormula R φ) (readFormula R ψ)
  | .or φ ψ => .or (readFormula R φ) (readFormula R ψ)
  | .imp φ ψ => .imp (readFormula R φ) (readFormula R ψ)
  | .quant .all x s φ => .all x (leanTypeOf R s) (readFormula R φ)
  | .quant .ex x s φ => .ex x (leanTypeOf R s) (readFormula R φ)
  | .unsupported t => .unsupported t

def readClaim (R : Registry) (c : SemanticClaim) : LDecl :=
  { binders := c.params.map (fun b => (b.name, leanTypeOf R b.sort)),
    hyps := c.assumptions.map (readFormula R),
    concl := readFormula R c.conclusion }

/-! ## The rendered string is the printing of the syntax tree -/

mutual
theorem print_readTerm (R : Registry) : ∀ t : Term, (readTerm R t).print = renderTermLean R t
  | .var x => by simp [readTerm, LTerm.print, renderTermLean]
  | .app f [] => by simp [readTerm, LTerm.print, renderTermLean]
  | .app f (a :: as) => by
    simp only [readTerm, LTerm.print, renderTermLean, printArgs_readTerms R (a :: as)]
theorem printArgs_readTerms (R : Registry) :
    ∀ ts : List Term, LTerm.printArgs (readTerms R ts) = renderTermsLean R ts
  | [] => by simp [readTerms, LTerm.printArgs, renderTermsLean]
  | t :: ts => by
    simp only [readTerms, LTerm.printArgs, renderTermsLean, print_readTerm R t,
      printArgs_readTerms R ts]
end

theorem print_readFormula (R : Registry) : ∀ φ : Formula, (readFormula R φ).print = renderLean R φ
  | .tt | .ff => rfl
  | .pred p [] => by simp [readFormula, readTerms, LProp.print, renderLean]
  | .pred p (a :: as) => by
    simp only [readFormula, LProp.print, renderLean, readTerms]
    rw [← printArgs_readTerms R (a :: as)]
    rfl
  | .eq a b => by simp [readFormula, LProp.print, renderLean, print_readTerm]
  | .ne a b => by simp [readFormula, LProp.print, renderLean, print_readTerm]
  | .not φ => by simp [readFormula, LProp.print, renderLean, print_readFormula R φ]
  | .and φ ψ => by
    simp [readFormula, LProp.print, renderLean, print_readFormula R φ, print_readFormula R ψ]
  | .or φ ψ => by
    simp [readFormula, LProp.print, renderLean, print_readFormula R φ, print_readFormula R ψ]
  | .imp φ ψ => by
    simp [readFormula, LProp.print, renderLean, print_readFormula R φ, print_readFormula R ψ]
  | .quant .all x s φ => by simp [readFormula, LProp.print, renderLean, print_readFormula R φ]
  | .quant .ex x s φ => by simp [readFormula, LProp.print, renderLean, print_readFormula R φ]
  | .unsupported t => rfl

/-- **`renderClaimLean_eq_print`**: the generated Lean text is literally the printing of the
    syntax tree `readClaim R c`. -/
theorem renderClaimLean_eq_print (R : Registry) (c : SemanticClaim) :
    renderClaimLean R c = (readClaim R c).print := by
  obtain ⟨ps, as, cl⟩ := c
  have hbody : (as.map (readFormula R)).foldr (fun a acc => a.print ++ " → " ++ acc)
      (readFormula R cl).print =
      as.foldr (fun a acc => renderLean R a ++ " → " ++ acc) (renderLean R cl) := by
    rw [List.foldr_map]
    simp only [print_readFormula]
  unfold renderClaimLean LDecl.print readClaim
  simp only
  rw [hbody]
  cases ps with
  | nil => rfl
  | cons p ps => simp [List.map_map, Function.comp_def]

/-! ## Semantics of the syntax with Lean's name resolution -/

/-- A semantic model of a Lean environment restricted to the fragment. -/
structure LeanEnvModel where
  Val : Type
  /-- the values of the Lean type with this exact name -/
  typeHas : String → Val → Prop
  /-- the global function constant with this exact name -/
  const : String → List Val → Val
  /-- the global predicate constant with this exact name -/
  constPred : String → List Val → Prop

/-- A name resolves to a global constant in local scope `b` (neither the name nor its first
    dotted component is a local variable). -/
def globalIn (b : List String) (n : String) : Bool := !b.contains n && !b.contains (headComp n)

mutual
/-- Lean-style resolution of term syntax: locals shadow globals; `x.f` with local `x` is a
    projection (outside the fragment). -/
def LTerm.res (E : LeanEnvModel) (b : List String) (ν : String → E.Val) : LTerm → Option E.Val
  | .ident n => if b.contains n then some (ν n) else if b.contains (headComp n) then none
      else some (E.const n [])
  | .app h args => if globalIn b h then (LTerm.resList E b ν args).map (E.const h) else none
def LTerm.resList (E : LeanEnvModel) (b : List String) (ν : String → E.Val) :
    List LTerm → Option (List E.Val)
  | [] => some []
  | t :: ts =>
    match LTerm.res E b ν t, LTerm.resList E b ν ts with
    | some v, some vs => some (v :: vs)
    | _, _ => none
end

/-- Meaning of proposition syntax under Lean's name resolution. -/
def LProp.denote (E : LeanEnvModel) : List String → (String → E.Val) → LProp → Prop
  | _, _, .tt => True
  | _, _, .ff => False
  | b, ν, .atom h args =>
    globalIn b h = true ∧ ∃ vs, LTerm.resList E b ν args = some vs ∧ E.constPred h vs
  | b, ν, .eq x y => ∃ u w, LTerm.res E b ν x = some u ∧ LTerm.res E b ν y = some w ∧ u = w
  | b, ν, .ne x y => ∃ u w, LTerm.res E b ν x = some u ∧ LTerm.res E b ν y = some w ∧ u ≠ w
  | b, ν, .not p => ¬ LProp.denote E b ν p
  | b, ν, .and p q => LProp.denote E b ν p ∧ LProp.denote E b ν q
  | b, ν, .or p q => LProp.denote E b ν p ∨ LProp.denote E b ν q
  | b, ν, .imp p q => LProp.denote E b ν p → LProp.denote E b ν q
  | b, ν, .all x T p => globalIn b T = true ∧
      ∀ v, E.typeHas T v → LProp.denote E (x :: b) (update ν x v) p
  | b, ν, .ex x T p => globalIn b T = true ∧
      ∃ v, E.typeHas T v ∧ LProp.denote E (x :: b) (update ν x v) p
  | _, _, .unsupported _ => False

/-- Universal closure over the declaration binders, continuation style. -/
def denoteBinders (E : LeanEnvModel) : List (String × String) → List String → (String → E.Val) →
    (List String → (String → E.Val) → Prop) → Prop
  | [], b, ν, k => k b ν
  | (x, T) :: bs, b, ν, k => globalIn b T = true ∧
      ∀ v, E.typeHas T v → denoteBinders E bs (x :: b) (update ν x v) k

/-- Meaning of a generated declaration type `∀ (x : T) …, H₁ → … → C`. -/
def LDecl.denote (E : LeanEnvModel) (d : LDecl) (ν : String → E.Val) : Prop :=
  denoteBinders E d.binders [] ν (fun b ν' =>
    d.hyps.foldr (fun h acc => LProp.denote E b ν' h → acc) (LProp.denote E b ν' d.concl))

/-- The PCS model induced by a Lean environment model through the registry's groundings. -/
def modelOf (E : LeanEnvModel) (R : Registry) : Model :=
  { Dom := E.Val, HasSort := fun s => E.typeHas (leanTypeOf R s),
    fn := fun f => E.const (leanNameOf R f), pred := fun p => E.constPred (leanNameOf R p) }

/-! ## The correspondence -/

/-- `N`-protected names: a name and its first component are in `N`. -/
def Protected (N : List String) (n : String) : Prop := n ∈ N ∧ headComp n ∈ N

theorem notMem_of_protected {N b : List String} {n : String} (hb : ∀ y ∈ b, y ∉ N)
    (h : Protected N n) : n ∉ b ∧ headComp n ∉ b :=
  ⟨fun hm => hb n hm h.1, fun hm => hb _ hm h.2⟩

theorem globalIn_of_protected {N b : List String} {n : String} (hb : ∀ y ∈ b, y ∉ N)
    (h : Protected N n) : globalIn b n = true := by
  obtain ⟨h1, h2⟩ := notMem_of_protected hb h
  unfold globalIn
  simp [h1, h2]

theorem contains_of_freeVars_nil {b : List String} {x : String}
    (h : Term.freeVars b (.var x) = []) : b.contains x = true := by
  unfold Term.freeVars at h
  cases hc : b.contains x
  · rw [hc] at h; cases h
  · rfl

mutual
theorem res_readTerm (E : LeanEnvModel) (R : Registry) (N : List String) (b : List String)
    (ν : String → E.Val) (hb : ∀ y ∈ b, y ∉ N) :
    ∀ t : Term, Term.freeVars b t = [] → (∀ f ∈ t.symbols, Protected N (leanNameOf R f)) →
      LTerm.res E b ν (readTerm R t) = some (Term.denote (modelOf E R) ν t)
  | .var x, hf, _ => by
    have hx : x ∈ b := List.contains_iff_mem.mp (contains_of_freeVars_nil hf)
    simp [readTerm, LTerm.res, hx, Term.denote]
  | .app f [], _, hs => by
    have hp := hs f (by simp [Term.symbols])
    obtain ⟨h1, h2⟩ := notMem_of_protected hb hp
    simp [readTerm, LTerm.res, h1, h2, Term.denote, Term.denoteList, modelOf]
  | .app f (a :: as), hf, hs => by
    have hp := hs f (by simp [Term.symbols])
    have hg := globalIn_of_protected hb hp
    have hl := resList_readTerms E R N b ν hb (a :: as)
      (by simpa [Term.freeVars] using hf)
      (fun g hg' => hs g (by simp only [Term.symbols]; exact List.mem_cons_of_mem _ hg'))
    simp only [readTerm, LTerm.res, hg, if_true, hl, Option.map_some, Term.denote, modelOf]
theorem resList_readTerms (E : LeanEnvModel) (R : Registry) (N : List String) (b : List String)
    (ν : String → E.Val) (hb : ∀ y ∈ b, y ∉ N) :
    ∀ ts : List Term, Term.freeVarsList b ts = [] →
      (∀ f ∈ Term.symbolsList ts, Protected N (leanNameOf R f)) →
      LTerm.resList E b ν (readTerms R ts) = some (Term.denoteList (modelOf E R) ν ts)
  | [], _, _ => by simp [readTerms, LTerm.resList, Term.denoteList]
  | t :: ts, hf, hs => by
    simp only [Term.freeVarsList, List.append_eq_nil_iff] at hf
    have h1 := res_readTerm E R N b ν hb t hf.1
      (fun f hf' => hs f (by simp only [Term.symbolsList]; exact List.mem_append_left _ hf'))
    have h2 := resList_readTerms E R N b ν hb ts hf.2
      (fun f hf' => hs f (by simp only [Term.symbolsList]; exact List.mem_append_right _ hf'))
    simp only [readTerms, LTerm.resList, h1, h2, Term.denoteList]
end

theorem update_ne {α : Type} (ρ : String → α) {x y : String} (d : α) (h : y ≠ x) :
    update ρ x d y = ρ y := by
  simp [update, h]

/-- The formula-level correspondence, for any local scope `b` avoiding the protected names. -/
theorem denote_readFormula (E : LeanEnvModel) (R : Registry) (N : List String) :
    ∀ (φ : Formula) (b : List String) (ν : String → E.Val), Formula.freeVars b φ = [] →
      (∀ y ∈ b, y ∉ N) → (∀ y ∈ Formula.binders φ, y ∉ N) →
      (∀ f ∈ Formula.symbols φ, Protected N (leanNameOf R f)) →
      (∀ s ∈ Formula.quantSorts φ, Protected N (leanTypeOf R s)) →
      (LProp.denote E b ν (readFormula R φ) ↔ Formula.denote (modelOf E R) ν φ)
  | .tt, _, _, _, _, _, _, _ => Iff.rfl
  | .ff, _, _, _, _, _, _, _ => Iff.rfl
  | .unsupported _, _, _, _, _, _, _, _ => Iff.rfl
  | .pred p args, b, ν, hf, hb, _, hs, _ => by
    have hp := hs p (by simp [Formula.symbols])
    have hl := resList_readTerms E R N b ν hb args (by simpa [Formula.freeVars] using hf)
      (fun g hg => hs g (by simp only [Formula.symbols]; exact List.mem_cons_of_mem _ hg))
    simp only [readFormula, LProp.denote, globalIn_of_protected hb hp, hl, Option.some.injEq,
      true_and, exists_eq_left', Formula.denote, modelOf]
  | .eq x y, b, ν, hf, hb, _, hs, _ => by
    simp only [Formula.freeVars, List.append_eq_nil_iff] at hf
    have h1 := res_readTerm E R N b ν hb x hf.1
      (fun f h => hs f (by simp only [Formula.symbols]; exact List.mem_append_left _ h))
    have h2 := res_readTerm E R N b ν hb y hf.2
      (fun f h => hs f (by simp only [Formula.symbols]; exact List.mem_append_right _ h))
    simp only [readFormula, LProp.denote, h1, h2, Option.some.injEq, exists_and_left,
      exists_eq_left', Formula.denote]
  | .ne x y, b, ν, hf, hb, _, hs, _ => by
    simp only [Formula.freeVars, List.append_eq_nil_iff] at hf
    have h1 := res_readTerm E R N b ν hb x hf.1
      (fun f h => hs f (by simp only [Formula.symbols]; exact List.mem_append_left _ h))
    have h2 := res_readTerm E R N b ν hb y hf.2
      (fun f h => hs f (by simp only [Formula.symbols]; exact List.mem_append_right _ h))
    simp only [readFormula, LProp.denote, h1, h2, Option.some.injEq, exists_and_left,
      exists_eq_left', Formula.denote]
  | .not φ, b, ν, hf, hb, hbd, hs, hq => by
    have := denote_readFormula E R N φ b ν hf hb hbd hs hq
    simp only [readFormula, LProp.denote, Formula.denote, this]
  | .and φ ψ, b, ν, hf, hb, hbd, hs, hq => by
    simp only [Formula.freeVars, List.append_eq_nil_iff] at hf
    have h1 := denote_readFormula E R N φ b ν hf.1 hb
      (fun y h => hbd y (List.mem_append_left _ h)) (fun f h => hs f (List.mem_append_left _ h))
      (fun s h => hq s (List.mem_append_left _ h))
    have h2 := denote_readFormula E R N ψ b ν hf.2 hb
      (fun y h => hbd y (List.mem_append_right _ h)) (fun f h => hs f (List.mem_append_right _ h))
      (fun s h => hq s (List.mem_append_right _ h))
    simp only [readFormula, LProp.denote, Formula.denote, h1, h2]
  | .or φ ψ, b, ν, hf, hb, hbd, hs, hq => by
    simp only [Formula.freeVars, List.append_eq_nil_iff] at hf
    have h1 := denote_readFormula E R N φ b ν hf.1 hb
      (fun y h => hbd y (List.mem_append_left _ h)) (fun f h => hs f (List.mem_append_left _ h))
      (fun s h => hq s (List.mem_append_left _ h))
    have h2 := denote_readFormula E R N ψ b ν hf.2 hb
      (fun y h => hbd y (List.mem_append_right _ h)) (fun f h => hs f (List.mem_append_right _ h))
      (fun s h => hq s (List.mem_append_right _ h))
    simp only [readFormula, LProp.denote, Formula.denote, h1, h2]
  | .imp φ ψ, b, ν, hf, hb, hbd, hs, hq => by
    simp only [Formula.freeVars, List.append_eq_nil_iff] at hf
    have h1 := denote_readFormula E R N φ b ν hf.1 hb
      (fun y h => hbd y (List.mem_append_left _ h)) (fun f h => hs f (List.mem_append_left _ h))
      (fun s h => hq s (List.mem_append_left _ h))
    have h2 := denote_readFormula E R N ψ b ν hf.2 hb
      (fun y h => hbd y (List.mem_append_right _ h)) (fun f h => hs f (List.mem_append_right _ h))
      (fun s h => hq s (List.mem_append_right _ h))
    simp only [readFormula, LProp.denote, Formula.denote, h1, h2]
  | .quant q x s φ, b, ν, hf, hb, hbd, hs, hq => by
    have hx : x ∉ N := hbd x (by simp [Formula.binders])
    have hb' : ∀ y ∈ x :: b, y ∉ N := by
      intro y hy
      rcases List.mem_cons.mp hy with rfl | hy
      · exact hx
      · exact hb y hy
    have hT := globalIn_of_protected hb (hq s (by simp [Formula.quantSorts]))
    have ih : ∀ v, LProp.denote E (x :: b) (update ν x v) (readFormula R φ) ↔
        Formula.denote (modelOf E R) (update ν x v) φ := fun v =>
      denote_readFormula E R N φ (x :: b) (update ν x v) (by simpa [Formula.freeVars] using hf) hb'
        (fun y h => hbd y (by simp only [Formula.binders]; exact List.mem_cons_of_mem _ h))
        (fun f h => hs f (by simpa [Formula.symbols] using h))
        (fun s' h => hq s' (by simp only [Formula.quantSorts]; exact List.mem_cons_of_mem _ h))
    cases q
    · simp only [readFormula, LProp.denote, hT, true_and, Formula.denote, modelOf]
      exact forall_congr' fun v => imp_congr_right fun _ => ih v
    · simp only [readFormula, LProp.denote, hT, true_and, Formula.denote, modelOf]
      exact exists_congr fun v => and_congr_right fun _ => ih v

theorem foldr_imp_iff {α : Type} (P : α → Prop) (C : Prop) :
    ∀ l : List α, l.foldr (fun h acc => P h → acc) C ↔ ((∀ a ∈ l, P a) → C)
  | [] => by simp
  | a :: l => by
    simp only [List.foldr_cons, List.mem_cons, forall_eq_or_imp]
    rw [foldr_imp_iff P C l]
    constructor
    · intro h ⟨ha, hl⟩; exact h ha hl
    · intro h ha hl; exact h ⟨ha, hl⟩

mutual
theorem Term.freeVars_mono {b b' : List String} (h : ∀ y ∈ b, y ∈ b') :
    ∀ t : Term, Term.freeVars b t = [] → Term.freeVars b' t = []
  | .var x, hf => by
    have hx := List.contains_iff_mem.mp (contains_of_freeVars_nil hf)
    simp [Term.freeVars, h x hx]
  | .app _ args, hf => by
    simp only [Term.freeVars] at hf ⊢
    exact Term.freeVarsList_mono h args hf
theorem Term.freeVarsList_mono {b b' : List String} (h : ∀ y ∈ b, y ∈ b') :
    ∀ ts : List Term, Term.freeVarsList b ts = [] → Term.freeVarsList b' ts = []
  | [], _ => rfl
  | t :: ts, hf => by
    simp only [Term.freeVarsList, List.append_eq_nil_iff] at hf ⊢
    exact ⟨Term.freeVars_mono h t hf.1, Term.freeVarsList_mono h ts hf.2⟩
end

theorem Formula.freeVars_mono :
    ∀ (φ : Formula) (b b' : List String), (∀ y ∈ b, y ∈ b') →
      Formula.freeVars b φ = [] → Formula.freeVars b' φ = []
  | .tt, _, _, _, _ | .ff, _, _, _, _ | .unsupported _, _, _, _, _ => rfl
  | .pred _ args, _, _, h, hf => by
    simp only [Formula.freeVars] at hf ⊢; exact Term.freeVarsList_mono h args hf
  | .eq x y, _, _, h, hf | .ne x y, _, _, h, hf => by
    simp only [Formula.freeVars, List.append_eq_nil_iff] at hf ⊢
    exact ⟨Term.freeVars_mono h x hf.1, Term.freeVars_mono h y hf.2⟩
  | .not φ, b, b', h, hf => by
    simp only [Formula.freeVars] at hf ⊢; exact Formula.freeVars_mono φ b b' h hf
  | .and φ ψ, b, b', h, hf | .or φ ψ, b, b', h, hf | .imp φ ψ, b, b', h, hf => by
    simp only [Formula.freeVars, List.append_eq_nil_iff] at hf ⊢
    exact ⟨Formula.freeVars_mono φ b b' h hf.1, Formula.freeVars_mono ψ b b' h hf.2⟩
  | .quant _ x _ φ, b, b', h, hf => by
    simp only [Formula.freeVars] at hf ⊢
    refine Formula.freeVars_mono φ (x :: b) (x :: b') ?_ hf
    intro y hy
    rcases List.mem_cons.mp hy with rfl | hy
    · exact List.mem_cons_self
    · exact List.mem_cons_of_mem _ (h y hy)

/-- Binder-level correspondence. -/
theorem denoteBinders_readClaim (E : LeanEnvModel) (R : Registry) (N : List String)
    (names : List String) (K : List String → (String → E.Val) → Prop) (K' : (String → E.Val) → Prop)
    (hK : ∀ b ν, (∀ y ∈ b, y ∉ N) → (∀ y ∈ names, y ∈ b) → (K b ν ↔ K' ν)) :
    ∀ (ps : List Binder) (b : List String) (ν : String → E.Val), (∀ y ∈ b, y ∉ N) →
      (∀ y ∈ names, y ∈ b ∨ y ∈ ps.map (·.name)) →
      (∀ p ∈ ps, p.name ∉ N ∧ Protected N (leanTypeOf R p.sort)) →
      (denoteBinders E (ps.map (fun p => (p.name, leanTypeOf R p.sort))) b ν K ↔
        denoteParams (modelOf E R) ps ν K')
  | [], b, ν, hb, hn, _ => by
    simp only [List.map_nil, denoteBinders, denoteParams]
    exact hK b ν hb (fun y hy => by simpa using hn y hy)
  | p :: ps, b, ν, hb, hn, hp => by
    have hp0 := hp p List.mem_cons_self
    have hb' : ∀ y ∈ p.name :: b, y ∉ N := by
      intro y hy
      rcases List.mem_cons.mp hy with rfl | hy
      · exact hp0.1
      · exact hb y hy
    have hn' : ∀ y ∈ names, y ∈ p.name :: b ∨ y ∈ ps.map (·.name) := by
      intro y hy
      rcases hn y hy with h | h
      · exact Or.inl (List.mem_cons_of_mem _ h)
      · simp only [List.map_cons, List.mem_cons] at h
        rcases h with h | h
        · exact Or.inl (h ▸ List.mem_cons_self)
        · exact Or.inr h
    simp only [List.map_cons, denoteBinders, denoteParams, globalIn_of_protected hb hp0.2,
      true_and, modelOf]
    exact forall_congr' fun v => imp_congr_right fun _ =>
      denoteBinders_readClaim E R N names K K' hK ps (p.name :: b) (update ν p.name v) hb' hn'
        (fun q hq => hp q (List.mem_cons_of_mem _ hq))

/-- **General correspondence with an explicit protected-name set.** -/
theorem lean_reading_correspondence_N (E : LeanEnvModel) (R : Registry) (N : List String)
    (c : SemanticClaim) (hclosed : c.freeVars = [])
    (hbind : ∀ y ∈ claimBinders c, y ∉ N)
    (hsym : ∀ f ∈ c.symbols, Protected N (leanNameOf R f))
    (hsort : ∀ s ∈ claimSorts c, Protected N (leanTypeOf R s)) (ν : String → E.Val) :
    (readClaim R c).denote E ν ↔ c.denote (modelOf E R) ν := by
  obtain ⟨ps, as, cl⟩ := c
  unfold SemanticClaim.freeVars at hclosed
  simp only [List.append_eq_nil_iff, List.flatMap_eq_nil_iff] at hclosed
  have hfb : ∀ φ ∈ as ++ [cl], ∀ y ∈ Formula.binders φ, y ∉ N := by
    intro φ hφ y hy
    apply hbind y
    unfold claimBinders
    exact List.mem_append_right _ (List.mem_flatMap.mpr ⟨φ, hφ, hy⟩)
  have hfs : ∀ φ ∈ as ++ [cl], ∀ f ∈ Formula.symbols φ, Protected N (leanNameOf R f) := by
    intro φ hφ f hf
    apply hsym f
    unfold SemanticClaim.symbols
    rcases List.mem_append.mp hφ with h | h
    · exact List.mem_append_left _ (List.mem_flatMap.mpr ⟨φ, h, hf⟩)
    · simp only [List.mem_singleton] at h
      subst h
      exact List.mem_append_right _ hf
  have hfq : ∀ φ ∈ as ++ [cl], ∀ s ∈ Formula.quantSorts φ, Protected N (leanTypeOf R s) := by
    intro φ hφ s hs
    apply hsort s
    unfold claimSorts
    exact List.mem_append_right _ (List.mem_flatMap.mpr ⟨φ, hφ, hs⟩)
  have hclosed' : ∀ φ ∈ as ++ [cl], Formula.freeVars (ps.map (·.name)) φ = [] := by
    intro φ hφ
    rcases List.mem_append.mp hφ with h | h
    · exact hclosed.1 φ h
    · simp only [List.mem_singleton] at h; subst h; exact hclosed.2
  have hform : ∀ φ ∈ as ++ [cl], ∀ (b : List String) (ν' : String → E.Val), (∀ y ∈ b, y ∉ N) →
      (∀ y ∈ ps.map (·.name), y ∈ b) →
      (LProp.denote E b ν' (readFormula R φ) ↔ Formula.denote (modelOf E R) ν' φ) := by
    intro φ hφ b ν' hb hn
    exact denote_readFormula E R N φ b ν' (Formula.freeVars_mono φ _ b hn (hclosed' φ hφ)) hb
      (hfb φ hφ) (hfs φ hφ) (hfq φ hφ)
  unfold LDecl.denote readClaim SemanticClaim.denote
  simp only
  refine denoteBinders_readClaim E R N (ps.map (·.name)) _ _ ?_ ps [] ν (by simp)
    (fun y hy => Or.inr hy)
    (fun p hp => ⟨hbind p.name (List.mem_append_left _ (List.mem_map_of_mem hp)),
      hsort p.sort (List.mem_append_left _ (List.mem_map_of_mem hp))⟩)
  intro b ν' hb hn
  rw [List.foldr_map, foldr_imp_iff]
  have hcl := hform cl (by simp) b ν' hb hn
  constructor
  · intro h ha
    exact hcl.mp (h (fun a hma => (hform a (List.mem_append_left _ hma) b ν' hb hn).mpr (ha a hma)))
  · intro h ha
    exact hcl.mpr (h (fun a hma => (hform a (List.mem_append_left _ hma) b ν' hb hn).mp (ha a hma)))

/-! ## The executable gate discharges the side conditions -/

theorem Registry.resolve_mem {R : Registry} {f : String} {e : SymbolEntry}
    (h : R.resolve f = some e) : e ∈ R.symbols := by
  unfold Registry.resolve Registry.entries at h
  split at h
  · rename_i e' he
    cases h
    have : e ∈ R.symbols.filter (fun x => x.id == f) := by rw [he]; exact List.mem_cons_self
    exact (List.mem_filter.mp this).1
  · cases h

theorem Registry.resolveSort_mem {R : Registry} {s : SortId} {e : SortEntry}
    (h : R.resolveSort s = some e) : e ∈ R.sorts := by
  unfold Registry.resolveSort at h
  split at h
  · rename_i e' he
    cases h
    have : e ∈ R.sorts.filter (fun x => x.id == s) := by rw [he]; exact List.mem_cons_self
    exact (List.mem_filter.mp this).1
  · cases h

theorem protected_of_registry_name {R : Registry} {n : String}
    (hn : n ∈ R.symbols.map (·.leanName) ++ R.sorts.map (·.leanType)) :
    Protected (reservedNames R) n := by
  have hmem : n ∈ reservedNames R := by
    unfold reservedNames
    rcases List.mem_append.mp hn with h | h
    · exact List.mem_append_left _ (List.mem_append_left _ (List.mem_append_left _
        (List.mem_append_right _ h)))
    · exact List.mem_append_left _ (List.mem_append_left _ (List.mem_append_right _ h))
  refine ⟨hmem, ?_⟩
  unfold headComp
  cases hs : n.splitOn "." with
  | nil => exact hmem
  | cons h t =>
    simp only [List.headD_cons]
    unfold reservedNames registryComponents
    refine List.mem_append_left _ (List.mem_append_right _ (List.mem_flatMap.mpr ⟨n, hn, ?_⟩))
    rw [hs]; exact List.mem_cons_self

/-- **`lean_reading_correspondence`** — for every registry, every Lean environment model and
    every closed claim accepted by the executable gate `leanSyntaxSafeB`, the generated Lean
    syntax, read with Lean's name-resolution discipline, means exactly what the claim means in
    the induced model. -/
theorem lean_reading_correspondence (E : LeanEnvModel) (R : Registry) (c : SemanticClaim)
    (hsafe : leanSyntaxSafeB R c = true) (hclosed : c.freeVars = []) (ν : String → E.Val) :
    (readClaim R c).denote E ν ↔ c.denote (modelOf E R) ν := by
  unfold leanSyntaxSafeB at hsafe
  simp only [Bool.and_eq_true, List.all_eq_true, Bool.not_eq_true', Option.isSome_iff_exists] at hsafe
  obtain ⟨⟨⟨⟨hb, -⟩, -⟩, hsy⟩, hso⟩ := hsafe
  refine lean_reading_correspondence_N E R (reservedNames R) c hclosed ?_ ?_ ?_ ν
  · intro y hy hN
    have := (hb y hy).2
    rw [List.contains_iff_mem.mpr hN] at this
    cases this
  · intro f hf
    obtain ⟨e, he⟩ := hsy f hf
    have : leanNameOf R f = e.leanName := by unfold leanNameOf; rw [he]
    rw [this]
    exact protected_of_registry_name (List.mem_append_left _
      (List.mem_map_of_mem (Registry.resolve_mem he)))
  · intro s hs
    obtain ⟨e, he⟩ := hso s hs
    have : leanTypeOf R s = e.leanType := by unfold leanTypeOf; rw [he]
    rw [this]
    exact protected_of_registry_name (List.mem_append_right _
      (List.mem_map_of_mem (Registry.resolveSort_mem he)))

/-- The gate rejects any claim with a binder named like a registry name. -/
theorem gate_rejects_reserved_binder {R : Registry} {c : SemanticClaim} {x : String}
    (hx : x ∈ claimBinders c) (hr : x ∈ reservedNames R) : leanSyntaxSafeB R c = false := by
  cases h : leanSyntaxSafeB R c
  · rfl
  · unfold leanSyntaxSafeB at h
    simp only [Bool.and_eq_true, List.all_eq_true, Bool.not_eq_true'] at h
    have := (h.1.1.1.1 x hx).2
    rw [List.contains_iff_mem.mpr hr] at this
    cases this

/-! ## The gate is necessary: binder capture changes the meaning -/

/-- A registry with one sort `S` (Lean type `T`) and one predicate `p` (Lean constant `P`). -/
def captureRegistry : Registry :=
  { sorts := [⟨"S", "T", "example"⟩], symbols := [⟨"p", "P", .pred ["S"], "example"⟩] }

/-- `∀ x : S, ∀ P : S, p x` — the inner binder is named like the Lean constant of `p`. -/
def captureClaim : SemanticClaim :=
  { params := [⟨"x", "S"⟩], assumptions := [],
    conclusion := .quant .all "P" "S" (.pred "p" [.var "x"]) }

/-- The everything-true environment on a one-point carrier. -/
def unitEnv : LeanEnvModel :=
  { Val := Unit, typeHas := fun _ _ => True, const := fun _ _ => (), constPred := fun _ _ => True }

/-- **`capture_breaks_correspondence`** — without the gate the correspondence fails: the PCS
    meaning of `captureClaim` is true in the induced model, but its rendering
    `∀ (x : T), (∀ (P : T), (P x))` resolves `P` to the bound variable, so the Lean reading is
    false.  The gate rejects this claim. -/
theorem capture_breaks_correspondence :
    captureClaim.denote (modelOf unitEnv captureRegistry) (fun _ => ()) ∧
    ¬ (readClaim captureRegistry captureClaim).denote unitEnv (fun _ => ()) ∧
    leanSyntaxSafeB captureRegistry captureClaim = false := by
  refine ⟨?_, ?_, ?_⟩
  · intro _ _ _ _ _
    trivial
  · intro h
    have h1 := (h.2 () trivial)
    simp only [readClaim, captureClaim, List.map_cons, List.map_nil, List.foldr_nil] at h1
    unfold readFormula at h1
    have h2 := (h1.2 () trivial).1
    simp [globalIn, leanNameOf, Registry.resolve, Registry.entries, captureRegistry] at h2
  · apply gate_rejects_reserved_binder (x := "P")
    · simp [claimBinders, captureClaim, Formula.binders]
    · simp [reservedNames, captureRegistry]

end PCS.V2.Semantic.LeanSyntax
