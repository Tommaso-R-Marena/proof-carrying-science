import PCSReasoningLibrary.Search

/-!
# A certified reuse separation on an infinite family

**Family.** `famCtx n = [p₀, p₀→p₀→p₁, …, pₙ₋₁→pₙ₋₁→pₙ]`, goal `pₙ` (atoms `pₖ = atom k`).
Each step uses its premise *twice* — repeated subproof structure.

**Baseline.** `bc` is plain backward-chaining tree search over two-premise rules
`a → b → g` (no memoisation, no library): it solves both premises independently.
`baseline_family_lower_bound`: whenever it succeeds on instance `n`, it has performed at least
`2ⁿ` goal expansions (exactly `2ⁿ⁺¹ − 1`), and its proof has size at least `2ⁿ`.

**Certified shared-strategy algorithm.** One reusable strategy is learned and admitted
*through the independent library checker*: `double_modus_ponens : (a→a→b)→a→b`.
`sharedProof n` uses it `n` times.  Its total cost `sharedTotal n` counts library construction
and admission checking, proof generation and full independent checking under the declared
checker cost model `chkWork` (including context scans and formula comparisons).
`shared_reasoning_family_upper_bound`: `sharedTotal n ≤ 40 (n+1)²`.

`certified_reuse_complexity_separation` is a **per-problem** statement (the library cost is
charged to every instance, not amortised): exponential lower bound for the baseline,
quadratic upper bound for certified reuse, strict advantage for all `n ≥ 13`, correctness of
both outputs and conservativity of the reuse proof over the primitive foundation.
-/

namespace PCSReasoningLibrary
namespace Separation

def ax (k : Nat) : Fm := .imp (.atom k) (.imp (.atom k) (.atom (k + 1)))

def famCtx : Nat → List Fm
  | 0 => [.atom 0]
  | n + 1 => ax n :: famCtx n

theorem famCtx_length : ∀ n, (famCtx n).length = n + 1
  | 0 => rfl
  | n + 1 => by simp [famCtx, famCtx_length n]

theorem atom_mem_famCtx : ∀ n k, Fm.atom k ∈ famCtx n ↔ k = 0
  | 0, k => by simp [famCtx, eq_comm]
  | n + 1, k => by simp [famCtx, ax, atom_mem_famCtx n k]

theorem ax_mem_famCtx : ∀ n k, k < n → ax k ∈ famCtx n
  | 0, k, h => absurd h (Nat.not_lt_zero _)
  | n + 1, k, h => by
      rcases Nat.lt_succ_iff_lt_or_eq.1 h with h | h
      · exact List.mem_cons_of_mem _ (ax_mem_famCtx n k h)
      · subst h; exact List.mem_cons_self

/-! ## Baseline: backward-chaining tree search -/

def ruleFor (g : Fm) : Fm → Option (Fm × Fm)
  | .imp a (.imp b c) => if c = g then some (a, b) else none
  | _ => none

def findRule (Γ : List Fm) (g : Fm) : Option (Fm × Fm) := Γ.findSome? (ruleFor g)

/-- Tree search: result and number of goal expansions. -/
def bc (Γ : List Fm) : Nat → Fm → Option Pf × Nat
  | 0, _ => (none, 1)
  | fuel + 1, g =>
    if g ∈ Γ then (some (.hyp g), 1) else
    match findRule Γ g with
    | none => (none, 1)
    | some (a, b) =>
      let r1 := bc Γ fuel a
      let r2 := bc Γ fuel b
      ((match r1.1, r2.1 with
        | some p, some q => some (.app (.app (.hyp (.imp a (.imp b g))) p) q)
        | _, _ => none), r1.2 + r2.2 + 1)

theorem findRule_mem {Γ : List Fm} {g a b : Fm} (h : findRule Γ g = some (a, b)) :
    Fm.imp a (.imp b g) ∈ Γ := by
  obtain ⟨ψ, hψ, hr⟩ := List.exists_of_findSome?_eq_some h
  match ψ, hr with
  | .imp a' (.imp b' c), hr =>
      simp only [ruleFor] at hr
      split at hr
      · rename_i hc; cases hr; subst hc; exact hψ
      · cases hr

/-- The baseline is sound: its proofs check (for any library). -/
theorem bc_sound (lib Γ : List Fm) : ∀ fuel g p, (bc Γ fuel g).1 = some p → infer lib Γ p = some g := by
  intro fuel
  induction fuel with
  | zero => intro g p h; simp [bc] at h
  | succ f ih =>
      intro g p h
      simp only [bc] at h
      split at h
      · rename_i hg; cases h; simp [infer, hg]
      · split at h
        · cases h
        · rename_i a b hr
          simp only at h
          split at h
          · rename_i p1 q1 h1 h2
            cases h
            simp [infer, findRule_mem hr, ih a p1 h1, ih b q1 h2]
          · cases h

theorem findRule_fam : ∀ n k, k < n → findRule (famCtx n) (.atom (k + 1)) = some (.atom k, .atom k)
  | 0, k, h => absurd h (Nat.not_lt_zero _)
  | n + 1, k, h => by
      simp only [findRule, famCtx, List.findSome?_cons]
      rcases Nat.lt_succ_iff_lt_or_eq.1 h with h | h
      · have hne : ¬ n + 1 = k + 1 := by omega
        have hne' : n ≠ k := by omega
        have := findRule_fam n k h
        simp only [findRule] at this
        simp [ruleFor, ax, hne', this]
      · subst h; simp [ruleFor, ax]

/-- The baseline's proof tree. -/
def tree : Nat → Pf
  | 0 => .hyp (.atom 0)
  | k + 1 => .app (.app (.hyp (ax k)) (tree k)) (tree k)

theorem tree_size : ∀ k, 2 ^ k ≤ (tree k).size
  | 0 => by simp [tree, Pf.size]
  | k + 1 => by
      have := tree_size k
      simp only [tree, Pf.size, Nat.pow_succ]; omega

theorem bc_fam_result (n : Nat) : ∀ k fuel, k ≤ n →
    (bc (famCtx n) fuel (.atom k)).1 = if k < fuel then some (tree k) else none := by
  intro k
  induction k with
  | zero =>
      intro fuel _
      cases fuel with
      | zero => simp [bc]
      | succ f => simp [bc, (atom_mem_famCtx n 0).2 rfl, tree]
  | succ j ih =>
      intro fuel hj
      cases fuel with
      | zero => simp [bc]
      | succ f =>
          have hnm : Fm.atom (j + 1) ∉ famCtx n := by
            rw [atom_mem_famCtx]; omega
          simp only [bc, hnm, if_false, findRule_fam n j (by omega), ih f (by omega)]
          by_cases hf : j < f
          · simp [hf, tree, ax, show j + 1 < f + 1 by omega]
          · simp [hf, show ¬ j + 1 < f + 1 by omega]

theorem bc_fam_work (n : Nat) : ∀ k fuel, k ≤ n → k < fuel →
    (bc (famCtx n) fuel (.atom k)).2 + 1 = 2 ^ (k + 1) := by
  intro k
  induction k with
  | zero =>
      intro fuel _ hf
      cases fuel with
      | zero => omega
      | succ f => simp [bc, (atom_mem_famCtx n 0).2 rfl]
  | succ j ih =>
      intro fuel hj hf
      cases fuel with
      | zero => omega
      | succ f =>
          have hnm : Fm.atom (j + 1) ∉ famCtx n := by
            rw [atom_mem_famCtx]; omega
          have := ih f (by omega) (by omega)
          simp only [bc, hnm, if_false, findRule_fam n j (by omega)]
          rw [Nat.pow_succ]; omega

/-- **Baseline lower bound.** Whenever tree search succeeds on instance `n`, it performed at
least `2ⁿ` expansions and returned a proof of size at least `2ⁿ`. -/
theorem baseline_family_lower_bound (n fuel : Nat) {p : Pf}
    (h : (bc (famCtx n) fuel (.atom n)).1 = some p) :
    2 ^ n ≤ (bc (famCtx n) fuel (.atom n)).2 ∧ 2 ^ n ≤ p.size ∧
      (bc (famCtx n) fuel (.atom n)).2 + 1 = 2 ^ (n + 1) := by
  rw [bc_fam_result n n fuel (Nat.le_refl _)] at h
  split at h
  · rename_i hf
    cases h
    have hw := bc_fam_work n n fuel (Nat.le_refl _) hf
    rw [Nat.pow_succ] at hw
    have := Nat.one_le_two_pow (n := n)
    exact ⟨by omega, tree_size n, hw⟩
  · cases h

/-! ## Declared checker cost model -/

/-- Unit-cost model of the checker `infer`: one unit per node, context scans cost
`|Γ|·size`, formula comparisons cost the size of the compared formula, lemma lookup costs its
index plus the size of the instantiated statement. -/
def chkWork (lib : List Fm) : List Fm → Pf → Nat
  | Γ, .hyp φ => Γ.length * φ.size + 1
  | _, .topI => 1
  | Γ, .botE _ p => chkWork lib Γ p + 2
  | Γ, .andI p q => chkWork lib Γ p + chkWork lib Γ q + 1
  | Γ, .andL p => chkWork lib Γ p + 1
  | Γ, .andR p => chkWork lib Γ p + 1
  | Γ, .orL _ p => chkWork lib Γ p + 1
  | Γ, .orR _ p => chkWork lib Γ p + 1
  | Γ, .orE p a b q r => chkWork lib Γ p + chkWork lib (a :: Γ) q + chkWork lib (b :: Γ) r +
      a.size + b.size + 2 + (match infer lib (a :: Γ) q with | some c => c.size | none => 0)
  | Γ, .lam φ p => chkWork lib (φ :: Γ) p + 1
  | Γ, .app p q => chkWork lib Γ p + chkWork lib Γ q + 1 +
      (match infer lib Γ q with | some a => a.size | none => 0)
  | _, .lem j σ => j + 1 + (match lib[j]? with | some ψ => (ψ.subst (inst σ)).size | none => 0)

/-! ## The learned reusable strategy and the shared algorithm -/

def dmp : Fm := .imp (.imp (.atom 0) (.imp (.atom 0) (.atom 1))) (.imp (.atom 0) (.atom 1))

def dmpProof : Pf :=
  .lam (.imp (.atom 0) (.imp (.atom 0) (.atom 1)))
    (.lam (.atom 0) (.app (.app (.hyp (.imp (.atom 0) (.imp (.atom 0) (.atom 1))))
      (.hyp (.atom 0))) (.hyp (.atom 0))))

def dmpEntry (found : String) : Entry :=
  { name := "double_modus_ponens", stmt := dmp, proof := dmpProof, deps := [],
    cost := dmpProof.size, foundation := found }

def sharedLib (found : String) : List Entry := [dmpEntry found]

/-- The learned strategy passes independent admission. -/
theorem sharedLib_admitted (found : String) : admittedB found (sharedLib found) = true := by
  simp [admittedB, sharedLib, admitOne, dmpEntry, Pf.lemRefs, dmpProof, stmts, infer, dmp]

theorem stmts_sharedLib (found : String) : stmts (sharedLib found) = [dmp] := rfl

def sharedProof : Nat → Pf
  | 0 => .hyp (.atom 0)
  | k + 1 => .app (.app (.lem 0 [.atom k, .atom (k + 1)]) (.hyp (ax k))) (sharedProof k)

theorem sharedProof_checks (n : Nat) : ∀ k, k ≤ n →
    infer [dmp] (famCtx n) (sharedProof k) = some (.atom k) := by
  intro k
  induction k with
  | zero => intro _; simp [sharedProof, infer, (atom_mem_famCtx n 0).2 rfl]
  | succ j ih =>
      intro hj
      have h1 := ih (by omega)
      have hm := ax_mem_famCtx n j (by omega)
      simp only [sharedProof, infer, h1, hm, if_true]
      simp [dmp, ax, Fm.subst, inst]

theorem sharedProof_size : ∀ k, (sharedProof k).size = 4 * k + 1
  | 0 => rfl
  | k + 1 => by simp only [sharedProof, Pf.size, sharedProof_size k]; omega

theorem sharedProof_work (n : Nat) : ∀ k, k ≤ n →
    chkWork [dmp] (famCtx n) (sharedProof k) = n + 2 + k * (5 * n + 24) := by
  intro k
  induction k with
  | zero => intro _; simp [sharedProof, chkWork, famCtx_length, Fm.size]
  | succ j ih =>
      intro hj
      have h1 := ih (by omega)
      have h2 := sharedProof_checks n j (by omega)
      have hm := ax_mem_famCtx n j (by omega)
      simp only [sharedProof, chkWork, h1, h2, famCtx_length, infer, hm, if_true]
      simp only [dmp, ax, Fm.subst, inst, Fm.size, List.getElem?_cons_zero, Option.map_some,
        List.getD_cons_zero, List.getD_cons_succ, List.getD_nil]
      rw [show (j + 1) * (5 * n + 24) = j * (5 * n + 24) + (5 * n + 24) by
        rw [Nat.add_mul, Nat.one_mul]]
      simp only [Nat.reduceAdd, Nat.zero_add]
      generalize j * (5 * n + 24) = X
      omega

/-- Library construction + admission checking cost (charged to every instance). -/
def libCost : Nat := dmpProof.size + chkWork [] [] dmpProof

theorem libCost_eq : libCost = 30 := by decide

/-- Total cost of the certified shared-strategy algorithm on instance `n`. -/
def sharedTotal (n : Nat) : Nat :=
  libCost + (sharedProof n).size + chkWork [dmp] (famCtx n) (sharedProof n)

/-- Total cost of the baseline on instance `n` (expansions only — a lower estimate). -/
def baselineWork (n : Nat) : Nat := (bc (famCtx n) (n + 1) (.atom n)).2

theorem sharedTotal_eq (n : Nat) : sharedTotal n = 33 + 5 * n + n * (5 * n + 24) := by
  simp only [sharedTotal, libCost_eq, sharedProof_size, sharedProof_work n n (Nat.le_refl _)]
  omega

/-- **Upper bound** (construction, admission, generation and checking all counted). -/
theorem shared_reasoning_family_upper_bound (n : Nat) :
    sharedTotal n ≤ 40 * (n + 1) * (n + 1) ∧
      infer (stmts (sharedLib "PCS")) (famCtx n) (sharedProof n) = some (.atom n) := by
  refine ⟨?_, sharedProof_checks n n (Nat.le_refl _)⟩
  rw [sharedTotal_eq]
  have : n * (5 * n + 24) = 5 * (n * n) + 24 * n := by
    rw [Nat.mul_add, Nat.mul_left_comm]
    rw [Nat.mul_comm n 24]
  have h2 : 40 * (n + 1) * (n + 1) = 40 * (n * n) + 80 * n + 40 := by
    simp only [Nat.mul_add, Nat.add_mul, Nat.mul_one, Nat.one_mul, Nat.mul_assoc]; omega
  omega

theorem baselineWork_eq (n : Nat) : baselineWork n + 1 = 2 ^ (n + 1) :=
  bc_fam_work n n (n + 1) (Nat.le_refl _) (Nat.lt_succ_self _)

theorem pow_dominates : ∀ n, 13 ≤ n → 40 * (n + 1) * (n + 1) < 2 ^ n := by
  intro n hn
  induction n with
  | zero => omega
  | succ m ih =>
      rcases Nat.eq_or_lt_of_le hn with h | h
      · rw [← h]; decide
      · have := ih (by omega)
        rw [Nat.pow_succ]
        have e1 : 40 * (m + 1 + 1) * (m + 1 + 1) = 40 * (m * m) + 160 * m + 160 := by
          simp only [Nat.mul_add, Nat.add_mul, Nat.mul_one, Nat.one_mul, Nat.mul_assoc]; omega
        have e2 : 40 * (m + 1) * (m + 1) = 40 * (m * m) + 80 * m + 40 := by
          simp only [Nat.mul_add, Nat.add_mul, Nat.mul_one, Nat.one_mul, Nat.mul_assoc]; omega
        have hm : 12 * m ≤ m * m := Nat.mul_le_mul_right m (by omega)
        omega

/-- **Certified reuse complexity separation** (per problem, library cost included). -/
theorem certified_reuse_complexity_separation :
    admittedB "PCS" (sharedLib "PCS") = true ∧
    (∀ n, infer (stmts (sharedLib "PCS")) (famCtx n) (sharedProof n) = some (.atom n)) ∧
    (∀ n, infer [] (famCtx n) (expand (closeLib (sharedLib "PCS")) (sharedProof n)) = some (.atom n) ∧
      (expand (closeLib (sharedLib "PCS")) (sharedProof n)).Primitive) ∧
    (∀ n, sharedTotal n ≤ 40 * (n + 1) * (n + 1)) ∧
    (∀ n, 2 ^ n ≤ baselineWork n ∧ baselineWork n + 1 = 2 ^ (n + 1)) ∧
    (∀ n p, (bc (famCtx n) (n + 1) (.atom n)).1 = some p → infer [] (famCtx n) p = some (.atom n)) ∧
    (∀ n, 13 ≤ n → sharedTotal n < baselineWork n) := by
  have hadm := sharedLib_admitted "PCS"
  refine ⟨hadm, fun n => sharedProof_checks n n (Nat.le_refl _), fun n => ?_,
    fun n => (shared_reasoning_family_upper_bound n).1, fun n => ?_,
    fun n p h => bc_sound [] _ _ _ _ h, fun n hn => ?_⟩
  · have := admitted_library_conservative hadm (sharedProof_checks n n (Nat.le_refl _))
    exact ⟨this.1, this.2.1⟩
  · have := baselineWork_eq n
    rw [Nat.pow_succ] at this
    have := Nat.one_le_two_pow (n := n)
    exact ⟨by omega, baselineWork_eq n⟩
  · have h1 := (shared_reasoning_family_upper_bound n).1
    have h2 := pow_dominates n hn
    have h3 := baselineWork_eq n
    rw [Nat.pow_succ] at h3
    omega

/-! ## Instantiations with actual Lean theorems -/

/-- Any predicate family with a doubly-used step: the certified reuse proof yields the Lean
theorem through checker soundness. -/
theorem family_instance (P : Nat → Prop) (h0 : P 0) (hs : ∀ k, P k → P k → P (k + 1)) (n : Nat) :
    P n := by
  have hv : ∀ ψ ∈ famCtx n, ψ.den P := by
    intro ψ hψ
    induction n with
    | zero => simp [famCtx] at hψ; subst hψ; exact h0
    | succ m ih =>
        simp only [famCtx, List.mem_cons] at hψ
        rcases hψ with rfl | hψ
        · exact hs m
        · exact ih hψ
  have hlib : ∀ φ ∈ stmts (sharedLib "PCS"), Valid φ := admitted_valid (sharedLib_admitted "PCS")
  exact infer_sound hlib P (sharedProof n) (famCtx n) (.atom n) hv (sharedProof_checks n n (Nat.le_refl _))

/-- Arithmetic instance. -/
theorem arith_instance (n : Nat) : 2 ^ n + 2 ^ n = 2 ^ (n + 1) :=
  family_instance (fun k => 2 ^ k + 2 ^ k = 2 ^ (k + 1)) (by decide)
    (fun k _ _ => by show 2 ^ (k + 1) + 2 ^ (k + 1) = 2 ^ (k + 1 + 1); rw [Nat.pow_succ 2 (k + 1)]; omega) n

/-- `n`-fold iteration (function composition power). -/
def iterN {α : Type} (f : α → α) : Nat → α → α
  | 0, x => x
  | k + 1, x => f (iterN f k x)

theorem iterN_add {α : Type} (f : α → α) (m : Nat) : ∀ k x, iterN f (m + k) x = iterN f m (iterN f k x)
  | 0, _ => rfl
  | k + 1, x => by
      show f (iterN f (m + k) x) = iterN f m (f (iterN f k x))
      rw [iterN_add f m k x]
      clear iterN_add
      induction m generalizing x with
      | zero => rfl
      | succ m ih => show f (f (iterN f m _)) = f (iterN f m (f _)); rw [← ih]

/-- Function-composition instance: `f^(2^(k+1)) = f^(2^k) ∘ f^(2^k)`. -/
theorem composition_instance {α : Type} (f : α → α) (n : Nat) :
    ∀ x, iterN f (2 ^ (n + 1)) x = iterN f (2 ^ n) (iterN f (2 ^ n) x) :=
  family_instance (fun k => ∀ x, iterN f (2 ^ (k + 1)) x = iterN f (2 ^ k) (iterN f (2 ^ k) x))
    (fun x => iterN_add f 1 1 x)
    (fun k _ _ x => by
      show iterN f (2 ^ (k + 1 + 1)) x = iterN f (2 ^ (k + 1)) (iterN f (2 ^ (k + 1)) x)
      rw [← iterN_add, Nat.pow_succ 2 (k + 1), Nat.mul_two]) n

/-- Logical instance: implication chains over arbitrary propositions. -/
theorem logic_instance (Q : Nat → Prop) (h0 : Q 0) (hs : ∀ k, Q k → Q (k + 1)) (n : Nat) : Q n :=
  family_instance Q h0 (fun k h _ => hs k h) n

end Separation
end PCSReasoningLibrary
