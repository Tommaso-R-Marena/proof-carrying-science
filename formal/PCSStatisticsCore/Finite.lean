/-!
# Finite exact probability foundation for promotion gates (Std only)

The general measure-theoretic statements live in the separate Mathlib library
`statistics/PCSStatistics/Gates.lean`.  This module provides the Std-only finite foundation:

* exact counting probability over a finite list of equally likely outcomes, and the
  finite **union bound** used to allocate the global error budget over candidates and generations;
* a geometric allocation `δ / 2^(k+1)` in exact natural-number arithmetic (`∑ ≤ δ`);
* the **data exposure ledger** and `exposure_ledger_enforces_test_protocol`;
* mathematical negative controls: repeated tuning on exposed test answers (a memoriser)
  and counting the same task as several independent observations.
-/

namespace PCSStatisticsCore

/-! ## Counting probability and the union bound -/

/-- Number of outcomes in `Ω` satisfying `p`. The probability is `count p Ω / Ω.length`. -/
def count {α : Type} (p : α → Bool) (Ω : List α) : Nat := Ω.countP p

theorem count_or_le {α : Type} (p q : α → Bool) (Ω : List α) :
    count (fun x => p x || q x) Ω ≤ count p Ω + count q Ω := by
  induction Ω with
  | nil => simp [count]
  | cons x xs ih =>
    simp only [count, List.countP_cons] at *
    cases hp : p x <;> cases hq : q x <;> simp <;> omega

/-- **Finite union bound**: the number of outcomes where *some* candidate in `cs` is bad is at
most the sum of the per-candidate counts. -/
theorem union_bound {α γ : Type} (bad : γ → α → Bool) (Ω : List α) (cs : List γ) :
    count (fun x => cs.any (fun c => bad c x)) Ω ≤ (cs.map (fun c => count (bad c) Ω)).sum := by
  induction cs with
  | nil => simp [count]
  | cons c cs ih =>
    simp only [List.any_cons, List.map_cons, List.sum_cons]
    exact Nat.le_trans (count_or_le _ _ Ω) (Nat.add_le_add_left ih _)

/-- Union bound across generations and candidates: a two-level budget. -/
theorem union_bound_generations {α γ : Type} (bad : Nat → γ → α → Bool) (Ω : List α)
    (cands : Nat → List γ) (K : Nat) :
    count (fun x => (List.range K).any (fun k => (cands k).any (fun c => bad k c x))) Ω ≤
      ((List.range K).map (fun k => ((cands k).map (fun c => count (bad k c) Ω)).sum)).sum := by
  refine Nat.le_trans (union_bound (fun k x => (cands k).any (fun c => bad k c x)) Ω _) ?_
  induction (List.range K) with
  | nil => simp
  | cons k ks ih =>
    simp only [List.map_cons, List.sum_cons]
    exact Nat.add_le_add (union_bound _ _ _) ih

/-! ## Geometric error allocation -/

/-- Allocation for generation `k` out of a budget `δ` expressed in units of `2^K`:
generation `k < K` receives `2^(K-k-1)` units. -/
def alloc (K k : Nat) : Nat := 2 ^ (K - k - 1)

theorem alloc_sum (K : Nat) : ((List.range K).map (alloc K)).sum + 1 = 2 ^ K := by
  induction K with
  | zero => simp
  | succ K ih =>
    rw [List.range_succ, List.map_append, List.sum_append_nat]
    simp only [List.map_cons, List.map_nil, List.sum_cons, List.sum_nil, alloc]
    have hmap : (List.range K).map (alloc (K + 1)) = (List.range K).map (fun k => 2 * alloc K k) := by
      apply List.map_congr_left
      intro k hk
      have := List.mem_range.mp hk
      simp only [alloc]
      rw [show K + 1 - k - 1 = (K - k - 1) + 1 by omega, Nat.pow_succ]; omega
    rw [hmap]
    have hs : ((List.range K).map (fun k => 2 * alloc K k)).sum = 2 * ((List.range K).map (alloc K)).sum := by
      induction (List.range K) with
      | nil => simp
      | cons a l ih => simp [List.sum_cons]; omega
    rw [hs, Nat.pow_succ]; simp; omega

/-- **Geometric allocation**: the per-generation allocations never exceed the global budget. -/
theorem geometric_allocation_le (K : Nat) : ((List.range K).map (alloc K)).sum < 2 ^ K := by
  have := alloc_sum K; omega

/-! ## The data exposure ledger -/

/-- What the experiment state machine records: tasks ever exposed to training, tuning, research
memory or previous evaluation feedback. -/
structure Ledger where
  exposed : List Nat
  deriving DecidableEq, Repr

/-- A proposed evaluation batch: task identifiers (each task counted once; seeds/models of the
same task are aggregated into one paired observation before reaching the gate). -/
structure EvalBatch where
  tasks : List Nat
  required : Nat
  deriving DecidableEq, Repr

def ledgerAdmits (L : Ledger) (B : EvalBatch) : Bool :=
  B.tasks.Nodup && B.tasks.all (fun t => !(L.exposed.contains t)) && B.tasks.length == B.required

/-- After evaluation the batch is exposed: it can never be reused as a fresh test. -/
def Ledger.record (L : Ledger) (B : EvalBatch) : Ledger := ⟨B.tasks ++ L.exposed⟩

/-- **Exposure ledger enforces the test protocol**: a batch is admitted iff its tasks are
distinct, fresh (never exposed) and of the declared sample size. -/
theorem exposure_ledger_enforces_test_protocol (L : Ledger) (B : EvalBatch) :
    ledgerAdmits L B = true ↔
      B.tasks.Nodup ∧ (∀ t ∈ B.tasks, t ∉ L.exposed) ∧ B.tasks.length = B.required := by
  simp [ledgerAdmits, List.all_eq_true, and_assoc]

/-- Once recorded, any batch sharing a task with an earlier evaluation is rejected. -/
theorem reuse_rejected (L : Ledger) (B B' : EvalBatch) (t : Nat) (h : t ∈ B.tasks)
    (h' : t ∈ B'.tasks) : ledgerAdmits (L.record B) B' = false := by
  cases hb : ledgerAdmits (L.record B) B' with
  | false => rfl
  | true =>
    have := ((exposure_ledger_enforces_test_protocol _ _).1 hb).2.1 t h'
    simp [Ledger.record, h] at this

/-! ## Negative control 1: repeated tuning on exposed answers -/

/-- A "memoriser" that has seen the exposed answers: it outputs the stored answer on exposed
tasks and a constant guess elsewhere. -/
def memorizer (answers : Nat → Bool) (exposed : List Nat) (t : Nat) : Bool :=
  if exposed.contains t then answers t else false

def score (pred answers : Nat → Bool) (ts : List Nat) : Nat :=
  count (fun t => pred t == answers t) ts

/-- On the exposed tasks the memoriser is perfect, whatever the true answers are. -/
theorem memorizer_control (answers : Nat → Bool) (exposed : List Nat) :
    score (memorizer answers exposed) answers exposed = exposed.length := by
  unfold score count memorizer
  rw [List.countP_eq_length]
  intro t ht; simp [ht]

/-- …but on fresh tasks whose answers are all `true` it scores zero: the exposed score carries no
information about genuine ability. -/
theorem memorizer_fresh_zero (answers : Nat → Bool) (exposed fresh : List Nat)
    (hfresh : ∀ t ∈ fresh, t ∉ exposed) (htrue : ∀ t ∈ fresh, answers t = true) :
    score (memorizer answers exposed) answers fresh = 0 := by
  unfold score count memorizer
  rw [List.countP_eq_zero]
  intro t ht
  have h1 := hfresh t ht
  simp [h1, htrue t ht]

/-- The ledger rejects re-evaluating the memoriser on its exposed tasks. -/
theorem memorizer_rejected (exposed : List Nat) (t : Nat) (ht : t ∈ exposed) (B : EvalBatch)
    (hB : t ∈ B.tasks) : ledgerAdmits ⟨exposed⟩ B = false := by
  cases hb : ledgerAdmits ⟨exposed⟩ B with
  | false => rfl
  | true =>
    have := ((exposure_ledger_enforces_test_protocol _ _).1 hb).2.1 t hB
    exact absurd ht this

/-- An honest fresh batch is admitted. -/
theorem honest_admitted : ledgerAdmits ⟨[0, 1, 2]⟩ ⟨[3, 4, 5, 6], 4⟩ = true := by decide

/-! ## Negative control 2: one task counted as many observations -/

/-- All Boolean vectors of length `n` (equally likely fair outcomes). -/
def cube : Nat → List (List Bool)
  | 0 => [[]]
  | n + 1 => (cube n).map (true :: ·) ++ (cube n).map (false :: ·)

theorem cube_length (n : Nat) : (cube n).length = 2 ^ n := by
  induction n with
  | zero => rfl
  | succ n ih => simp [cube, ih, Nat.pow_succ]; omega

/-- With `n` genuinely independent fair observations, "all successes" has exactly one outcome
out of `2^n`. -/
theorem independent_all_success (n : Nat) :
    count (fun v => v.all id) (cube n) = 1 := by
  induction n with
  | zero => decide
  | succ n ih =>
    simp only [count, cube, List.countP_append, List.countP_map] at *
    have h2 : (cube n).countP ((fun v => v.all id) ∘ (false :: ·)) = 0 := by
      rw [List.countP_eq_zero]; intro a _; simp
    have h1 : (cube n).countP ((fun v => v.all id) ∘ (true :: ·)) =
        (cube n).countP (fun v => v.all id) := by
      apply List.countP_congr; intro a _; simp
    rw [h1, h2, ih]

/-- Counting one task `n` times: the duplicated "sample" is `replicate n b` for a single fair bit
`b`, and all successes occur with probability `1/2` for every `n ≥ 1` — so the `2^{-n}`
concentration claimed for independent observations is false for duplicated tasks. -/
theorem duplicated_all_success (n : Nat) (hn : 0 < n) :
    count (fun v => v.all id) ([true, false].map (List.replicate n)) = 1 := by
  obtain ⟨m, rfl⟩ : ∃ m, n = m + 1 := ⟨n - 1, by omega⟩
  simp [count, List.replicate_succ]

theorem duplication_breaks_independence (n : Nat) (hn : 2 ≤ n) :
    count (fun v => v.all id) (cube n) * 2 < (cube n).length *
      count (fun v => v.all id) ([true, false].map (List.replicate n)) := by
  rw [independent_all_success, duplicated_all_success n (by omega), cube_length]
  have : 4 ≤ 2 ^ n := by
    calc 4 = 2 ^ 2 := rfl
      _ ≤ 2 ^ n := Nat.pow_le_pow_right (by decide) hn
  omega

end PCSStatisticsCore
