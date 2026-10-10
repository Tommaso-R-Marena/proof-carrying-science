import Std

/-!
# Shared typed Boolean semantics (Omega repair and conditional/intervention layers)

* `BForm n` — typed Boolean AST over the variables `Fin n`: atom, TRUE, FALSE, NOT, AND,
  OR and implication (`!a || b`).
* `BForm.eval` — executable evaluator; `BForm.Holds` — independently defined
  propositional satisfaction. `eval_iff_holds` proves they agree.
* Total assignments are `List Bool` of length `n`; position `i` is variable `i`.
* `allAsg n` — complete False-before-True enumeration (variable `0` most significant, the
  same order as Python `itertools.product((False, True), repeat=n)`), proved complete,
  duplicate-free, of length `2^n` and strictly increasing in the lexicographic order
  `lexLt` (with `false < true`).  `allAsg 0 = [[]]`, so constants are checked on exactly one
  valuation.
-/

namespace PCSOmega

/-- Typed Boolean formulas over `n` declared variables. -/
inductive BForm (n : Nat) where
  | atom (i : Fin n)
  | tt
  | ff
  | not (a : BForm n)
  | and (a b : BForm n)
  | or (a b : BForm n)
  | imp (a b : BForm n)
  deriving DecidableEq, Repr

namespace BForm

variable {n : Nat}

/-- Executable Boolean evaluation under a valuation of variable indices. -/
def eval (ρ : Nat → Bool) : BForm n → Bool
  | atom i => ρ i.val
  | tt => true
  | ff => false
  | not a => !(eval ρ a)
  | and a b => eval ρ a && eval ρ b
  | or a b => eval ρ a || eval ρ b
  | imp a b => !(eval ρ a) || eval ρ b

/-- Independent propositional satisfaction (not defined through `eval`). -/
def Holds (ρ : Nat → Bool) : BForm n → Prop
  | atom i => ρ i.val = true
  | tt => True
  | ff => False
  | not a => ¬ Holds ρ a
  | and a b => Holds ρ a ∧ Holds ρ b
  | or a b => Holds ρ a ∨ Holds ρ b
  | imp a b => Holds ρ a → Holds ρ b

/-- **Evaluator correctness.** -/
theorem eval_iff_holds (ρ : Nat → Bool) (f : BForm n) : f.eval ρ = true ↔ f.Holds ρ := by
  induction f with
  | atom i => simp [eval, Holds]
  | tt => simp [eval, Holds]
  | ff => simp [eval, Holds]
  | not a ih => simp [eval, Holds, ← ih]
  | and a b iha ihb => simp [eval, Holds, ← iha, ← ihb]
  | or a b iha ihb => simp [eval, Holds, ← iha, ← ihb]
  | imp a b iha ihb =>
      simp only [eval, Holds, ← iha, ← ihb]
      cases eval ρ a <;> cases eval ρ b <;> simp

instance (ρ : Nat → Bool) (f : BForm n) : Decidable (f.Holds ρ) :=
  decidable_of_iff _ (eval_iff_holds ρ f)

/-- A formula only reads the declared variables `0 … n-1`. -/
theorem eval_congr {ρ σ : Nat → Bool} (h : ∀ i, i < n → ρ i = σ i) (f : BForm n) :
    f.eval ρ = f.eval σ := by
  induction f with
  | atom i => exact h i.val i.isLt
  | tt => rfl
  | ff => rfl
  | not a ih => simp [eval, ih]
  | and a b iha ihb => simp [eval, iha, ihb]
  | or a b iha ihb => simp [eval, iha, ihb]
  | imp a b iha ihb => simp [eval, iha, ihb]

/-- Number of AST nodes (the Python `count`). -/
def size : BForm n → Nat
  | atom _ => 1
  | tt => 1
  | ff => 1
  | not a => a.size + 1
  | and a b => a.size + b.size + 1
  | or a b => a.size + b.size + 1
  | imp a b => a.size + b.size + 1

/-- Depth with the root at depth `0` (the Python `depth`). -/
def depth : BForm n → Nat
  | atom _ => 0
  | tt => 0
  | ff => 0
  | not a => a.depth + 1
  | and a b => max a.depth b.depth + 1
  | or a b => max a.depth b.depth + 1
  | imp a b => max a.depth b.depth + 1

end BForm

/-- Semantic equivalence: agreement under every valuation. -/
def SemEquiv {n : Nat} (f g : BForm n) : Prop :=
  ∀ ρ : Nat → Bool, (f.Holds ρ ↔ g.Holds ρ)

/-! ## Total assignments and their enumeration -/

/-- The valuation read off a total assignment (variables beyond the list read `false`). -/
def envOf (a : List Bool) : Nat → Bool := fun i => a.getD i false

/-- The total assignment of length `k` read off a valuation. -/
def listOf (ρ : Nat → Bool) (k : Nat) : List Bool := (List.range k).map ρ

theorem listOf_length (ρ : Nat → Bool) (k : Nat) : (listOf ρ k).length = k := by
  simp [listOf]

theorem envOf_listOf {ρ : Nat → Bool} {k i : Nat} (h : i < k) : envOf (listOf ρ k) i = ρ i := by
  simp [envOf, listOf, List.getD_eq_getElem?_getD, h]

/-- Complete False-before-True enumeration of total assignments of length `k`. -/
def allAsg : Nat → List (List Bool)
  | 0 => [[]]
  | k + 1 => (allAsg k).map (false :: ·) ++ (allAsg k).map (true :: ·)

theorem allAsg_zero : allAsg 0 = [[]] := rfl

theorem mem_allAsg : ∀ {k : Nat} {a : List Bool}, a ∈ allAsg k ↔ a.length = k
  | 0, a => by cases a <;> simp [allAsg]
  | k + 1, a => by
      cases a with
      | nil => simp [allAsg]
      | cons x s =>
          cases x <;> simp [allAsg, mem_allAsg]

theorem length_allAsg : ∀ k, (allAsg k).length = 2 ^ k
  | 0 => rfl
  | k + 1 => by simp [allAsg, length_allAsg k, Nat.pow_succ]; omega

theorem nodup_allAsg : ∀ k, (allAsg k).Nodup
  | 0 => by simp [allAsg]
  | k + 1 => by
      simp only [allAsg, List.nodup_append]
      refine ⟨?_, ?_, ?_⟩
      · exact List.pairwise_map.2 ((nodup_allAsg k).imp (fun h e => h (List.cons.inj e).2))
      · exact List.pairwise_map.2 ((nodup_allAsg k).imp (fun h e => h (List.cons.inj e).2))
      · intro a ha b hb; simp at ha hb
        obtain ⟨_, _, rfl⟩ := ha; obtain ⟨_, _, rfl⟩ := hb; simp

/-! ## Lexicographic order (`false < true`, variable `0` most significant) -/

/-- Strict lexicographic order on Boolean lists. -/
def lexLt : List Bool → List Bool → Bool
  | [], _ => false
  | _ :: _, [] => false
  | x :: s, y :: t => (!x && y) || (x == y && lexLt s t)

theorem lexLt_irrefl : ∀ a : List Bool, lexLt a a = false
  | [] => rfl
  | x :: s => by cases x <;> simp [lexLt, lexLt_irrefl s]

theorem lexLt_trans : ∀ {a b c : List Bool}, lexLt a b = true → lexLt b c = true → lexLt a c = true
  | [], _, _, h, _ => by simp [lexLt] at h
  | _ :: _, [], _, h, _ => by simp [lexLt] at h
  | _ :: _, _ :: _, [], _, h => by simp [lexLt] at h
  | x :: s, y :: t, z :: u, h1, h2 => by
      cases x <;> cases y <;> cases z <;> simp_all [lexLt] <;> exact lexLt_trans h1 h2

/-- Trichotomy for assignments of equal length. -/
theorem lexLt_total : ∀ {a b : List Bool}, a.length = b.length →
    a = b ∨ lexLt a b = true ∨ lexLt b a = true
  | [], [], _ => Or.inl rfl
  | [], _ :: _, h => by simp at h
  | _ :: _, [], h => by simp at h
  | x :: s, y :: t, h => by
      have := lexLt_total (a := s) (b := t) (by simpa using h)
      cases x <;> cases y <;> simp [lexLt] <;> omega

theorem pairwise_lexLt_allAsg : ∀ k, (allAsg k).Pairwise (fun a b => lexLt a b = true)
  | 0 => by simp [allAsg]
  | k + 1 => by
      simp only [allAsg, List.pairwise_append, List.pairwise_map]
      refine ⟨?_, ?_, ?_⟩
      · exact (pairwise_lexLt_allAsg k).imp (fun h => by simpa [lexLt] using h)
      · exact (pairwise_lexLt_allAsg k).imp (fun h => by simpa [lexLt] using h)
      · intro a ha b hb; simp at ha hb
        obtain ⟨_, _, rfl⟩ := ha; obtain ⟨_, _, rfl⟩ := hb; simp [lexLt]

/-- `a` is the lexicographically least list satisfying `P`. -/
def IsLexLeast (P : List Bool → Prop) (a : List Bool) : Prop :=
  P a ∧ ∀ b, P b → b = a ∨ lexLt a b = true

theorem IsLexLeast.unique {P : List Bool → Prop} {a b : List Bool}
    (ha : IsLexLeast P a) (hb : IsLexLeast P b) : a = b := by
  rcases ha.2 b hb.1 with h | h
  · exact h.symm
  · rcases hb.2 a ha.1 with h' | h'
    · exact h'
    · have := lexLt_trans h h'; rw [lexLt_irrefl] at this; contradiction

/-- `find?` on a strictly sorted list returns the least satisfying element. -/
theorem find?_pairwise_least {R : α → α → Prop} {p : α → Bool} :
    ∀ {l : List α} {a : α}, l.Pairwise R → l.find? p = some a →
      ∀ b ∈ l, p b = true → b = a ∨ R a b
  | [], _, _, h, _, hb, _ => by simp at hb
  | x :: xs, a, hl, h, b, hb, hpb => by
      rw [List.pairwise_cons] at hl
      by_cases hx : p x = true
      · simp [hx] at h
        subst h
        rcases List.mem_cons.1 hb with rfl | hb
        · exact Or.inl rfl
        · exact Or.inr (hl.1 b hb)
      · simp [hx] at h
        rcases List.mem_cons.1 hb with rfl | hb
        · exact absurd hpb hx
        · exact find?_pairwise_least hl.2 h b hb hpb

/-- Lifting a lexicographic-least argument through a list cons: the shape used by
false-first witness extraction and by tie-breaking reconstruction. -/
theorem isLexLeast_cons_false {P : List Bool → Prop} {Q0 : List Bool → Prop} {s : List Bool}
    (hP : ∀ t, P (false :: t) ↔ Q0 t) (hQ : IsLexLeast Q0 s)
    (hnil : ¬ P []) :
    IsLexLeast P (false :: s) := by
  refine ⟨(hP s).2 hQ.1, ?_⟩
  intro b hb
  cases b with
  | nil => exact absurd hb hnil
  | cons y t =>
      cases y with
      | true => right; simp [lexLt]
      | false =>
          rcases hQ.2 t ((hP t).1 hb) with h | h
          · left; rw [h]
          · right; simp [lexLt, h]

theorem isLexLeast_cons_true {P : List Bool → Prop} {Q1 : List Bool → Prop} {s : List Bool}
    (hP : ∀ t, P (true :: t) ↔ Q1 t) (hno : ∀ t, ¬ P (false :: t)) (hQ : IsLexLeast Q1 s)
    (hnil : ¬ P []) :
    IsLexLeast P (true :: s) := by
  refine ⟨(hP s).2 hQ.1, ?_⟩
  intro b hb
  cases b with
  | nil => exact absurd hb hnil
  | cons y t =>
      cases y with
      | false => exact absurd hb (hno t)
      | true =>
          rcases hQ.2 t ((hP t).1 hb) with h | h
          · left; rw [h]
          · right; simp [lexLt, h]

end PCSOmega
