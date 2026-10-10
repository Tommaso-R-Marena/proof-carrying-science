import PCSOmega.Formula

/-!
# Named Boolean formulas, declared-name validation and typed lowering

A bridge from *already parsed* named formulas (the JSON AST shape `atom/true/false/not/and/or/
implies` with string symbols) to the typed AST `BForm n`.  This does **not** model JSON bytes,
the text grammar, Unicode whitespace or `splitlines`; those remain outside the proofs.

* `nameOK` — `[A-Z][A-Z0-9_]{0,15}` and not a reserved keyword (`AND OR NOT IMPLIES TRUE FALSE`).
* `namesOK limit names` — at most `limit` names, each `nameOK`, strictly sorted (hence
  distinct; `strictSortedS_nodup`).
* `lower names` — replaces each symbol by its declared index; fails on an undeclared symbol
  (`lower_isSome_iff`).
* `lower_eval` — the lowered formula evaluated at a total assignment equals the named formula
  evaluated at the corresponding name→value environment.
* `NForm.boundedB` — the node/depth bounds (`63`/`8` for Omega, `128`/`12` for conditional
  formulas) agree with the typed bounds after lowering (`lower_size`, `lower_depth`).
-/

namespace PCSOmega

/-- Parsed named Boolean formula. -/
inductive NForm where
  | atom (s : String)
  | tt
  | ff
  | not (a : NForm)
  | and (a b : NForm)
  | or (a b : NForm)
  | imp (a b : NForm)
  deriving DecidableEq, Repr

namespace NForm

/-- Evaluation under a name environment. -/
def eval (σ : String → Bool) : NForm → Bool
  | atom s => σ s
  | tt => true
  | ff => false
  | not a => !(eval σ a)
  | and a b => eval σ a && eval σ b
  | or a b => eval σ a || eval σ b
  | imp a b => !(eval σ a) || eval σ b

/-- Symbols occurring in a formula. -/
def atoms : NForm → List String
  | atom s => [s]
  | tt => []
  | ff => []
  | not a => atoms a
  | and a b => atoms a ++ atoms b
  | or a b => atoms a ++ atoms b
  | imp a b => atoms a ++ atoms b

def size : NForm → Nat
  | atom _ => 1
  | tt => 1
  | ff => 1
  | not a => a.size + 1
  | and a b => a.size + b.size + 1
  | or a b => a.size + b.size + 1
  | imp a b => a.size + b.size + 1

def depth : NForm → Nat
  | atom _ => 0
  | tt => 0
  | ff => 0
  | not a => a.depth + 1
  | and a b => max a.depth b.depth + 1
  | or a b => max a.depth b.depth + 1
  | imp a b => max a.depth b.depth + 1

/-- Node/depth bound check. -/
def boundedB (maxNodes maxDepth : Nat) (f : NForm) : Bool :=
  decide (f.size ≤ maxNodes) && decide (f.depth ≤ maxDepth)

end NForm

/-- Reserved logical keywords. -/
def reserved : List String := ["AND", "OR", "NOT", "IMPLIES", "TRUE", "FALSE"]

/-- `[A-Z][A-Z0-9_]{0,15}` and not reserved. -/
def nameOK (s : String) : Bool :=
  match s.toList with
  | [] => false
  | c :: cs =>
      decide (cs.length ≤ 15) && ('A' ≤ c && c ≤ 'Z') &&
        cs.all (fun d => ('A' ≤ d && d ≤ 'Z') || ('0' ≤ d && d ≤ '9') || d == '_') &&
        !(reserved.contains s)

/-- Strictly increasing list of strings. -/
def strictSortedS : List String → Bool
  | a :: b :: r => decide (a < b) && strictSortedS (b :: r)
  | _ => true

/-- Declared-name validator. -/
def namesOK (limit : Nat) (names : List String) : Bool :=
  decide (names.length ≤ limit) && names.all nameOK && strictSortedS names

theorem strictSortedS_head_lt : ∀ (l : List String) (a : String), strictSortedS (a :: l) = true →
    ∀ x ∈ l, a < x
  | [], _, _, x, hx => by simp at hx
  | b :: r, a, h, x, hx => by
      simp only [strictSortedS, Bool.and_eq_true, decide_eq_true_eq] at h
      rcases List.mem_cons.1 hx with rfl | hx
      · exact h.1
      · exact String.lt_trans h.1 (strictSortedS_head_lt r b h.2 x hx)

theorem strictSortedS_nodup : ∀ l : List String, strictSortedS l = true → l.Nodup
  | [], _ => List.nodup_nil
  | [a], _ => by simp
  | a :: b :: r, h => by
      have h' := h
      simp only [strictSortedS, Bool.and_eq_true] at h'
      refine List.nodup_cons.2 ⟨fun hm => ?_, strictSortedS_nodup (b :: r) h'.2⟩
      have := strictSortedS_head_lt (b :: r) a h a hm
      exact String.lt_irrefl a this

/-- Name environment of a total assignment over declared names. -/
def envNamed (names : List String) (a : List Bool) : String → Bool := fun s =>
  match names.idxOf? s with
  | some i => a.getD i false
  | none => false

/-- Typed lowering. -/
def lower {n : Nat} (names : List String) : NForm → Option (BForm n)
  | .atom s =>
      match names.idxOf? s with
      | some i => if h : i < n then some (.atom ⟨i, h⟩) else none
      | none => none
  | .tt => some .tt
  | .ff => some .ff
  | .not a => (lower names a).map .not
  | .and a b => do let x ← lower names a; let y ← lower names b; pure (.and x y)
  | .or a b => do let x ← lower names a; let y ← lower names b; pure (.or x y)
  | .imp a b => do let x ← lower names a; let y ← lower names b; pure (.imp x y)

variable {n : Nat}

/-- **Lowering preserves meaning.** -/
theorem lower_eval (names : List String) :
    ∀ (f : NForm) (g : BForm n), lower names f = some g → ∀ a, g.eval (envOf a) = f.eval (envNamed names a)
  | .atom s, g, h, a => by
      simp only [lower] at h
      split at h
      · rename_i i hi
        split at h
        · cases h; simp [BForm.eval, NForm.eval, envNamed, hi, envOf]
        · cases h
      · cases h
  | .tt, g, h, a => by cases h; rfl
  | .ff, g, h, a => by cases h; rfl
  | .not x, g, h, a => by
      simp only [lower] at h
      cases hx : lower names x with
      | none => rw [hx] at h; cases h
      | some x' => rw [hx] at h; cases h; simp [BForm.eval, NForm.eval, lower_eval names x x' hx a]
  | .and x y, g, h, a => by
      simp only [lower] at h
      cases hx : lower (n := n) names x <;> cases hy : lower (n := n) names y <;> rw [hx, hy] at h <;>
        try cases h
      simp [BForm.eval, NForm.eval, lower_eval names x _ hx a, lower_eval names y _ hy a]
  | .or x y, g, h, a => by
      simp only [lower] at h
      cases hx : lower (n := n) names x <;> cases hy : lower (n := n) names y <;> rw [hx, hy] at h <;>
        try cases h
      simp [BForm.eval, NForm.eval, lower_eval names x _ hx a, lower_eval names y _ hy a]
  | .imp x y, g, h, a => by
      simp only [lower] at h
      cases hx : lower (n := n) names x <;> cases hy : lower (n := n) names y <;> rw [hx, hy] at h <;>
        try cases h
      simp [BForm.eval, NForm.eval, lower_eval names x _ hx a, lower_eval names y _ hy a]

theorem idxOf?_isSome_iff {names : List String} {s : String} : (names.idxOf? s).isSome ↔ s ∈ names :=
  List.isSome_idxOf?

theorem idxOf?_lt {names : List String} {s : String} {i : Nat} (h : names.idxOf? s = some i) :
    i < names.length := by
  induction names generalizing i with
  | nil => simp at h
  | cons x xs ih =>
      by_cases hx : x = s
      · subst hx; simp [List.idxOf?_cons] at h; subst h; simp
      · have e : (List.idxOf? s (x :: xs)) = (xs.idxOf? s).map (· + 1) := by
          simp [List.idxOf?_cons, hx]
        rw [e] at h
        cases hi : xs.idxOf? s with
        | none => rw [hi] at h; cases h
        | some j => rw [hi] at h; cases h; have := ih hi; simp; omega

/-- **Lowering succeeds iff every symbol is declared** (with `n` declared names). -/
theorem lower_isSome_iff {names : List String} (hn : names.length = n) :
    ∀ f : NForm, (lower (n := n) names f).isSome ↔ ∀ s ∈ f.atoms, s ∈ names
  | .atom s => by
      simp only [lower, NForm.atoms, List.mem_singleton, forall_eq]
      rw [← idxOf?_isSome_iff]
      cases h : names.idxOf? s with
      | none => simp
      | some i =>
          have := idxOf?_lt h
          simp [show i < n by omega]
  | .tt => by simp [lower, NForm.atoms]
  | .ff => by simp [lower, NForm.atoms]
  | .not x => by simp [lower, NForm.atoms, lower_isSome_iff hn x]
  | .and x y => by
      have hx := lower_isSome_iff hn x; have hy := lower_isSome_iff hn y
      simp only [lower, NForm.atoms, List.mem_append]
      cases h1 : lower (n := n) names x <;> cases h2 : lower (n := n) names y <;>
        simp_all <;> grind
  | .or x y => by
      have hx := lower_isSome_iff hn x; have hy := lower_isSome_iff hn y
      simp only [lower, NForm.atoms, List.mem_append]
      cases h1 : lower (n := n) names x <;> cases h2 : lower (n := n) names y <;>
        simp_all <;> grind
  | .imp x y => by
      have hx := lower_isSome_iff hn x; have hy := lower_isSome_iff hn y
      simp only [lower, NForm.atoms, List.mem_append]
      cases h1 : lower (n := n) names x <;> cases h2 : lower (n := n) names y <;>
        simp_all <;> grind

/-- Lowering preserves node count and depth (so bounds are checked once, before lowering). -/
theorem lower_size_depth (names : List String) :
    ∀ (f : NForm) (g : BForm n), lower names f = some g → g.size = f.size ∧ g.depth = f.depth
  | .atom s, g, h => by
      simp only [lower] at h
      split at h
      · split at h
        · cases h; exact ⟨rfl, rfl⟩
        · cases h
      · cases h
  | .tt, g, h => by cases h; exact ⟨rfl, rfl⟩
  | .ff, g, h => by cases h; exact ⟨rfl, rfl⟩
  | .not x, g, h => by
      simp only [lower] at h
      cases hx : lower names x with
      | none => rw [hx] at h; cases h
      | some x' =>
          rw [hx] at h; cases h
          have := lower_size_depth names x x' hx
          simp [BForm.size, BForm.depth, NForm.size, NForm.depth, this.1, this.2]
  | .and x y, g, h => by
      simp only [lower] at h
      cases hx : lower (n := n) names x <;> cases hy : lower (n := n) names y <;> rw [hx, hy] at h <;>
        try cases h
      have h1 := lower_size_depth names x _ hx; have h2 := lower_size_depth names y _ hy
      simp [BForm.size, BForm.depth, NForm.size, NForm.depth, h1.1, h1.2, h2.1, h2.2]
  | .or x y, g, h => by
      simp only [lower] at h
      cases hx : lower (n := n) names x <;> cases hy : lower (n := n) names y <;> rw [hx, hy] at h <;>
        try cases h
      have h1 := lower_size_depth names x _ hx; have h2 := lower_size_depth names y _ hy
      simp [BForm.size, BForm.depth, NForm.size, NForm.depth, h1.1, h1.2, h2.1, h2.2]
  | .imp x y, g, h => by
      simp only [lower] at h
      cases hx : lower (n := n) names x <;> cases hy : lower (n := n) names y <;> rw [hx, hy] at h <;>
        try cases h
      have h1 := lower_size_depth names x _ hx; have h2 := lower_size_depth names y _ hy
      simp [BForm.size, BForm.depth, NForm.size, NForm.depth, h1.1, h1.2, h2.1, h2.2]

end PCSOmega
