import PCSAssumptionDiscovery.Symbolic

/-!
# Counterexample-guided exact assumption discovery (certified, theorem-level)

The world type `W` is arbitrary (finite or infinite) and the ambient assumptions `A` and the
target `T` are arbitrary propositions.  Hypotheses `H i : W → Bool` are decidable so that a
counterexample world yields a concrete selector clause.

The *checker interface* is a proof-carrying `Oracle`: for a candidate selector `y` it must
return one of

* `counter w hctx hT`   — a genuine bad world (`Context(w,y)` and `¬T(w)`),
* `inconsistent h`      — a proof that `Context(·,y)` is unsatisfiable,
* `valid w hctx hsuff`  — a satisfying context witness and a proof of sufficiency.

Because every verdict carries its proof, an untrusted oracle implementation cannot cause a
wrong acceptance.  The search over selectors is exact and finite (`2^k` candidates).

Principal theorems:

* `counterexample_clause_necessary` — each counterexample (and each inconsistency blocking)
  clause is satisfied by every sufficient consistent explanation;
* `cegar_optimum_preserved` — the clause invariant is preserved, so no feasible (in particular
  no optimal) explanation is ever excluded;
* `cegar_progress` — each refinement removes the current candidate;
* `cegar_accept_optimal` — completed acceptance is a globally optimal and
  lexicographically least (False-first) explanation;
* `cegar_finite_termination` — with fuel `2^k + 1` the run never stops on fuel;
* `cegar_partial_lower_bound` — a fuel-limited run reports a certified lower bound and its
  unresolved clause set, never a fabricated optimum;
* `collect_exact` — collecting all optima yields exactly the optimal explanations with exact
  count and mandatory/possible membership;
* `finiteOracle` — a complete enumeration oracle for finite domains, and
  `cegar_agrees_with_symbolic` — on Boolean problems CEGAR and the decision-diagram route
  agree on the minimum cost.
-/

namespace PCSAssumptionDiscovery.Cegar

open PCSOmega PCSAssumptionDiscovery

/-- A theorem-level abduction specification over worlds `W` with `k` catalog hypotheses. -/
structure Spec (W : Type) (k : Nat) where
  A : W → Prop
  T : W → Prop
  H : Nat → W → Bool
  cost : Nat → Nat
  lockedIn : List Nat
  lockedOut : List Nat

variable {W : Type} {k : Nat}

def Ctx (s : Spec W k) (w : W) (y : List Bool) : Prop :=
  s.A w ∧ ∀ i < k, sel y i = true → s.H i w = true

def LocksOK (s : Spec W k) (y : List Bool) : Bool :=
  s.lockedIn.all (sel y) && s.lockedOut.all (fun i => !sel y i)

def Feas (s : Spec W k) (y : List Bool) : Prop :=
  y.length = k ∧ (∃ w, Ctx s w y) ∧ (∀ w, Ctx s w y → s.T w) ∧ LocksOK s y = true

def cost (s : Spec W k) (y : List Bool) : Nat :=
  ((List.range k).map (fun i => if sel y i then s.cost i else 0)).sum

def Opt (s : Spec W k) (y : List Bool) : Prop :=
  Feas s y ∧ ∀ z, Feas s z → cost s y ≤ cost s z

/-- A selector clause: some `pos` index selected or some `neg` index unselected. -/
structure Clause where
  pos : List Nat
  neg : List Nat
  deriving DecidableEq, Repr

def Clause.sat (c : Clause) (y : List Bool) : Bool :=
  c.pos.any (sel y) || c.neg.any (fun i => !sel y i)

/-- Proof-carrying checker verdicts. -/
inductive Verdict (s : Spec W k) (y : List Bool) : Type where
  | counter (w : W) (hc : Ctx s w y) (ht : ¬ s.T w)
  | inconsistent (h : ∀ w, ¬ Ctx s w y)
  | valid (w : W) (hc : Ctx s w y) (hs : ∀ v, Ctx s v y → s.T v)

/-- The checker interface (possibly untrusted code; its outputs carry proofs). -/
abbrev Oracle (s : Spec W k) := (y : List Bool) → Verdict s y

/-- Clause contributed by a bad world: `∨{yᵢ | Hᵢ(w) = false}`. -/
def cexClause (s : Spec W k) (w : W) : Clause := ⟨(List.range k).filter (fun i => !s.H i w), []⟩

/-- Clause contributed by an inconsistent selection: do not contain all of `y`. -/
def blockClause (k : Nat) (y : List Bool) : Clause := ⟨[], idxSet k y⟩

/-! ## Clause necessity and progress -/

/-- **Each counterexample clause is necessary** for every sufficient consistent explanation. -/
theorem counterexample_clause_necessary (s : Spec W k) {y : List Bool} {w : W}
    (hc : Ctx s w y) (ht : ¬ s.T w) : ∀ z, Feas s z → (cexClause s w).sat z = true := by
  intro z ⟨_, _, hsuff, _⟩
  cases hsat : (cexClause s w).sat z
  · exfalso
    apply ht
    apply hsuff
    refine ⟨hc.1, fun i hi hz => ?_⟩
    cases hH : s.H i w
    · have : (cexClause s w).sat z = true := by
        simp only [Clause.sat, cexClause, List.any_nil, Bool.or_false]
        exact List.any_eq_true.2 ⟨i, List.mem_filter.2 ⟨List.mem_range.2 hi, by simp [hH]⟩, hz⟩
      rw [hsat] at this; cases this
    · rfl
  · rfl

/-- Inconsistency blocking clauses are necessary too (supersets of an inconsistent selection
are inconsistent). -/
theorem block_clause_necessary (s : Spec W k) {y : List Bool} (h : ∀ w, ¬ Ctx s w y) :
    ∀ z, Feas s z → (blockClause k y).sat z = true := by
  intro z ⟨_, ⟨w, hw⟩, _, _⟩
  cases hsat : (blockClause k y).sat z
  · exfalso
    apply h w
    refine ⟨hw.1, fun i hi hy => hw.2 i hi ?_⟩
    cases hz : sel z i
    · have : (blockClause k y).sat z = true := by
        simp only [Clause.sat, blockClause, List.any_nil, Bool.false_or]
        exact List.any_eq_true.2 ⟨i, mem_idxSet.2 ⟨hi, hy⟩, by simp [hz]⟩
      rw [hsat] at this; cases this
    · rfl
  · rfl

/-- **Genuine progress**: the candidate violates the clause it produced. -/
theorem cegar_progress (s : Spec W k) (y : List Bool) :
    (∀ (w : W), Ctx s w y → (cexClause s w).sat y = false) ∧ (blockClause k y).sat y = false := by
  refine ⟨fun w hc => ?_, ?_⟩
  · simp only [Clause.sat, cexClause, List.any_nil, Bool.or_false]
    rw [List.any_eq_false]
    intro i hi hyi
    have hi' := List.mem_filter.1 hi
    have := hc.2 i (List.mem_range.1 hi'.1) hyi
    simp [this] at hi'
  · simp only [Clause.sat, blockClause, List.any_nil, Bool.false_or]
    rw [List.any_eq_false]
    intro i hi h
    simp [(mem_idxSet.1 hi).2] at h

/-! ## Exact cheapest candidate -/

/-- First element of minimum value. -/
def argminFirst {α : Type} (f : α → Nat) : List α → Option α
  | [] => none
  | a :: l =>
    match argminFirst f l with
    | none => some a
    | some b => if f b < f a then some b else some a

theorem argminFirst_none {α : Type} {f : α → Nat} : ∀ {l : List α}, argminFirst f l = none ↔ l = []
  | [] => by simp [argminFirst]
  | a :: l => by
      simp only [argminFirst]
      split
      · simp
      · split <;> simp

theorem argminFirst_spec {α : Type} {f : α → Nat} {R : α → α → Prop} :
    ∀ {l : List α} {r : α}, l.Pairwise R → argminFirst f l = some r →
      r ∈ l ∧ (∀ x ∈ l, f r ≤ f x) ∧ (∀ x ∈ l, f x = f r → x = r ∨ R r x)
  | [], _, _, h => by simp [argminFirst] at h
  | a :: l, r, hp, h => by
      rw [List.pairwise_cons] at hp
      simp only [argminFirst] at h
      split at h
      · rename_i hn
        cases h
        rw [argminFirst_none] at hn; subst hn
        simp
      · rename_i b hb
        obtain ⟨hbm, hbmin, hbfirst⟩ := argminFirst_spec hp.2 hb
        split at h
        · rename_i hlt
          cases h
          refine ⟨List.mem_cons_of_mem _ hbm, ?_, ?_⟩
          · intro x hx
            rcases List.mem_cons.1 hx with rfl | hx
            · omega
            · exact hbmin x hx
          · intro x hx he
            rcases List.mem_cons.1 hx with rfl | hx
            · omega
            · exact hbfirst x hx he
        · rename_i hge
          cases h
          refine ⟨List.mem_cons_self, ?_, ?_⟩
          · intro x hx
            rcases List.mem_cons.1 hx with rfl | hx
            · omega
            · have := hbmin x hx; omega
          · intro x hx _
            rcases List.mem_cons.1 hx with rfl | hx
            · exact Or.inl rfl
            · exact Or.inr (hp.1 x hx)

/-- Selectors of length `k` satisfying all clauses and the locks. -/
def cands (s : Spec W k) (cls : List Clause) : List (List Bool) :=
  (allAsg k).filter (fun y => cls.all (fun c => c.sat y) && LocksOK s y)

/-- The exact cheapest candidate (False-first among ties). -/
def best (s : Spec W k) (cls : List Clause) : Option (List Bool) := argminFirst (cost s) (cands s cls)

/-- Clause invariant: every feasible selector satisfies every clause. -/
def ClauseInv (s : Spec W k) (cls : List Clause) : Prop := ∀ c ∈ cls, ∀ z, Feas s z → c.sat z = true

theorem feas_mem_cands {s : Spec W k} {cls : List Clause} (hI : ClauseInv s cls) {z : List Bool}
    (hz : Feas s z) : z ∈ cands s cls := by
  simp only [cands, List.mem_filter, mem_allAsg, Bool.and_eq_true, List.all_eq_true]
  exact ⟨hz.1, fun c hc => hI c hc z hz, hz.2.2.2⟩

theorem best_spec {s : Spec W k} {cls : List Clause} {y : List Bool} (h : best s cls = some y) :
    y ∈ cands s cls ∧ (∀ z ∈ cands s cls, cost s y ≤ cost s z) ∧
      (∀ z ∈ cands s cls, cost s z = cost s y → z = y ∨ lexLt y z = true) :=
  argminFirst_spec ((pairwise_lexLt_allAsg k).sublist List.filter_sublist) h

/-! ## The refinement loop -/

inductive Result (W : Type) where
  | optimal (y : List Bool) (w : W) (cls : List Clause)
  | noExplanation (cls : List Clause)
  | unresolved (lowerBound : Option Nat) (cls : List Clause)

/-- Certified lower bound from the current clause set. -/
def lowerBound (s : Spec W k) (cls : List Clause) : Option Nat := (best s cls).map (cost s)

/-- Counterexample-guided refinement with explicit fuel. -/
def run (s : Spec W k) (o : Oracle s) : Nat → List Clause → Result W
  | 0, cls => .unresolved (lowerBound s cls) cls
  | fuel + 1, cls =>
    match best s cls with
    | none => .noExplanation cls
    | some y =>
      match o y with
      | .counter w _ _ => run s o fuel (cexClause s w :: cls)
      | .inconsistent _ => run s o fuel (blockClause k y :: cls)
      | .valid w _ _ => .optimal y w cls

/-- **Valid optimums are never excluded**: refinement preserves the clause invariant. -/
theorem cegar_optimum_preserved (s : Spec W k) {cls : List Clause} (hI : ClauseInv s cls) :
    (∀ (y : List Bool) (w : W), Ctx s w y → ¬ s.T w → ClauseInv s (cexClause s w :: cls)) ∧
    (∀ y : List Bool, (∀ w, ¬ Ctx s w y) → ClauseInv s (blockClause k y :: cls)) := by
  refine ⟨fun y w hc ht => ?_, fun y h => ?_⟩
  · intro c hc'
    rcases List.mem_cons.1 hc' with rfl | hc'
    · exact counterexample_clause_necessary s hc ht
    · exact hI c hc'
  · intro c hc'
    rcases List.mem_cons.1 hc' with rfl | hc'
    · exact block_clause_necessary s h
    · exact hI c hc'

theorem ClauseInv.nil (s : Spec W k) : ClauseInv s [] := by simp [ClauseInv]

/-- The loop invariant along a run, and the meaning of each terminal outcome. -/
theorem run_spec (s : Spec W k) (o : Oracle s) :
    ∀ (fuel : Nat) (cls : List Clause), ClauseInv s cls →
      (∀ y w cls', run s o fuel cls = .optimal y w cls' →
        ClauseInv s cls' ∧ best s cls' = some y ∧ Feas s y ∧ Ctx s w y) ∧
      (∀ cls', run s o fuel cls = .noExplanation cls' → ClauseInv s cls' ∧ best s cls' = none) ∧
      (∀ lb cls', run s o fuel cls = .unresolved lb cls' → ClauseInv s cls' ∧ lb = lowerBound s cls')
  | 0, cls, hI => by
      refine ⟨fun y w cls' h => ?_, fun cls' h => ?_, fun lb cls' h => ?_⟩ <;> simp only [run] at h
      · cases h
      · cases h
      · cases h; exact ⟨hI, rfl⟩
  | fuel + 1, cls, hI => by
      cases hb : best s cls with
      | none =>
          refine ⟨fun y w cls' h => ?_, fun cls' h => ?_, fun lb cls' h => ?_⟩ <;>
            simp only [run, hb] at h
          · cases h
          · cases h; exact ⟨hI, hb⟩
          · cases h
      | some y =>
          have hy := (best_spec hb).1
          simp only [cands, List.mem_filter, mem_allAsg, Bool.and_eq_true] at hy
          cases hv : o y with
          | counter w hc ht =>
              have e : run s o (fuel + 1) cls = run s o fuel (cexClause s w :: cls) := by
                simp only [run, hb, hv]
              rw [e]; exact run_spec s o fuel _ ((cegar_optimum_preserved s hI).1 y w hc ht)
          | inconsistent h =>
              have e : run s o (fuel + 1) cls = run s o fuel (blockClause k y :: cls) := by
                simp only [run, hb, hv]
              rw [e]; exact run_spec s o fuel _ ((cegar_optimum_preserved s hI).2 y h)
          | valid w hc hs =>
              have e : run s o (fuel + 1) cls = .optimal y w cls := by simp only [run, hb, hv]
              rw [e]
              refine ⟨fun y' w' cls' h => ?_, fun cls' h => ?_, fun lb cls' h => ?_⟩
              · cases h; exact ⟨hI, hb, ⟨hy.1, ⟨w, hc⟩, hs, hy.2.2⟩, hc⟩
              · cases h
              · cases h

/-- **Completed acceptance is globally optimal and False-first**, with the checker's
context witness. -/
theorem cegar_accept_optimal (s : Spec W k) (o : Oracle s) {fuel : Nat} {y : List Bool} {w : W}
    {cls : List Clause} (h : run s o fuel [] = .optimal y w cls) :
    Opt s y ∧ IsLexLeast (Opt s) y ∧ Ctx s w y := by
  obtain ⟨hI, hb, hf, hw⟩ := (run_spec s o fuel [] (ClauseInv.nil s)).1 _ _ _ h
  obtain ⟨_, hmin, hfirst⟩ := best_spec hb
  have hopt : Opt s y := ⟨hf, fun z hz => hmin z (feas_mem_cands hI hz)⟩
  refine ⟨hopt, ⟨hopt, fun z hz => ?_⟩, hw⟩
  have hc := feas_mem_cands hI hz.1
  have hle := hmin z hc
  have hge := hz.2 y hf
  exact hfirst z hc (by omega)

/-- **No explanation** is reported only when none exists. -/
theorem cegar_noExplanation (s : Spec W k) (o : Oracle s) {fuel : Nat} {cls : List Clause}
    (h : run s o fuel [] = .noExplanation cls) : ∀ z, ¬ Feas s z := by
  obtain ⟨hI, hb⟩ := (run_spec s o fuel [] (ClauseInv.nil s)).2.1 _ h
  intro z hz
  have := feas_mem_cands hI hz
  unfold best at hb
  rw [argminFirst_none] at hb
  rw [hb] at this; simp at this

/-- **Partial runs**: a certified lower bound on every feasible cost and the unresolved
clause set; `none` certifies that no explanation exists.  No optimum is fabricated. -/
theorem cegar_partial_lower_bound (s : Spec W k) (o : Oracle s) {fuel : Nat} {lb : Option Nat}
    {cls : List Clause} (h : run s o fuel [] = .unresolved lb cls) :
    ClauseInv s cls ∧ ∀ z, Feas s z → ∃ b, lb = some b ∧ b ≤ cost s z := by
  obtain ⟨hI, rfl⟩ := (run_spec s o fuel [] (ClauseInv.nil s)).2.2 _ _ h
  refine ⟨hI, fun z hz => ?_⟩
  have hc := feas_mem_cands hI hz
  unfold lowerBound
  cases hb : best s cls with
  | none =>
      unfold best at hb; rw [argminFirst_none] at hb; rw [hb] at hc; simp at hc
  | some y => exact ⟨cost s y, rfl, (best_spec hb).2.1 z hc⟩

/-! ## Termination -/

theorem length_filter_lt {α : Type} (p : α → Bool) :
    ∀ {l : List α} {x : α}, x ∈ l → p x = false → (l.filter p).length < l.length
  | [], _, hx, _ => by simp at hx
  | a :: l, x, hx, hp => by
      rcases List.mem_cons.1 hx with rfl | hx
      · have := List.length_filter_le p l
        simp only [List.filter_cons, hp, List.length_cons]
        simp only [Bool.false_eq_true, ite_false]; omega
      · have := length_filter_lt p hx hp
        have := List.length_filter_le p l
        cases hpa : p a
        · simp only [List.filter_cons, hpa, Bool.false_eq_true, ite_false, List.length_cons]; omega
        · simp only [List.filter_cons, hpa, ite_true, List.length_cons]; omega

theorem cands_cons (s : Spec W k) (c : Clause) (cls : List Clause) :
    cands s (c :: cls) = (cands s cls).filter c.sat := by
  unfold cands
  rw [List.filter_filter]
  congr 1
  funext y
  simp only [List.all_cons]
  cases c.sat y <;> simp

theorem cands_shrink (s : Spec W k) {cls : List Clause} {y : List Bool} {c : Clause}
    (hy : y ∈ cands s cls) (hc : c.sat y = false) :
    (cands s (c :: cls)).length < (cands s cls).length := by
  rw [cands_cons]; exact length_filter_lt _ hy hc

theorem run_not_partial (s : Spec W k) (o : Oracle s) :
    ∀ (fuel : Nat) (cls : List Clause), (cands s cls).length < fuel →
      ∀ lb cls', run s o fuel cls ≠ .unresolved lb cls'
  | 0, _, h, _, _ => by omega
  | fuel + 1, cls, h, lb, cls' => by
      simp only [run]
      split
      · simp
      · rename_i y hb
        have hy := (best_spec hb).1
        split
        · rename_i w hc _ _
          apply run_not_partial s o fuel
          have := cands_shrink s hy ((cegar_progress s y).1 w hc); omega
        · apply run_not_partial s o fuel
          have := cands_shrink s hy (cegar_progress s y).2; omega
        · simp

/-- **Finite termination**: with fuel `2^k + 1` (from any clause set) the refinement loop
reaches acceptance or proves that no explanation exists. -/
theorem cegar_finite_termination (s : Spec W k) (o : Oracle s) (cls : List Clause) :
    ∀ lb cls', run s o (2 ^ k + 1) cls ≠ .unresolved lb cls' := by
  apply run_not_partial
  have : (cands s cls).length ≤ (allAsg k).length := List.length_filter_le _ _
  rw [length_allAsg] at this; omega

/-! ## Collecting every optimum -/

def Verdict.isValid {s : Spec W k} {y : List Bool} : Verdict s y → Bool
  | .valid .. => true
  | _ => false

/-- All optimal explanations, re-checked one by one through the proof-carrying checker. -/
def collect (s : Spec W k) (o : Oracle s) (cls : List Clause) (c : Nat) : List (List Bool) :=
  (cands s cls).filter (fun y => cost s y == c && (o y).isValid)

/-- Mandatory hypotheses (selected by every optimum). -/
def mandatory (L : List (List Bool)) : List Nat := (List.range k).filter (fun i => L.all (sel · i))

/-- Possible hypotheses (selected by some optimum). -/
def possible (L : List (List Bool)) : List Nat := (List.range k).filter (fun i => L.any (sel · i))

theorem verdict_valid_feas {s : Spec W k} {y : List Bool} (v : Verdict s y) (hv : v.isValid = true) :
    (∃ w, Ctx s w y) ∧ (∀ w, Ctx s w y → s.T w) := by
  cases v with
  | counter => simp [Verdict.isValid] at hv
  | inconsistent => simp [Verdict.isValid] at hv
  | valid w hc hs => exact ⟨⟨w, hc⟩, hs⟩

theorem verdict_feas_valid {s : Spec W k} {y : List Bool} (v : Verdict s y) (hf : Feas s y) :
    v.isValid = true := by
  cases v with
  | counter w hc ht => exact absurd (hf.2.2.1 w hc) ht
  | inconsistent h => obtain ⟨w, hw⟩ := hf.2.1; exact absurd hw (h w)
  | valid => rfl

/-- **Exact collection of all optima**: duplicate-free, exactly the optimal explanations,
with exact mandatory/possible membership. -/
theorem collect_exact (s : Spec W k) (o : Oracle s) {fuel : Nat} {y : List Bool} {w : W}
    {cls : List Clause} (h : run s o fuel [] = .optimal y w cls) :
    let L := collect s o cls (cost s y)
    L.Nodup ∧ (∀ z, z ∈ L ↔ Opt s z) ∧
      (∀ i, i ∈ mandatory (k := k) L ↔ i < k ∧ ∀ z, Opt s z → sel z i = true) ∧
      (∀ i, i ∈ possible (k := k) L ↔ i < k ∧ ∃ z, Opt s z ∧ sel z i = true) := by
  obtain ⟨hI, _, _, _⟩ := (run_spec s o fuel [] (ClauseInv.nil s)).1 _ _ _ h
  obtain ⟨hopt, _, _⟩ := cegar_accept_optimal s o h
  have hmem : ∀ z, z ∈ collect s o cls (cost s y) ↔ Opt s z := by
    intro z
    simp only [collect, List.mem_filter, Bool.and_eq_true, beq_iff_eq]
    constructor
    · rintro ⟨hc, he, hv⟩
      have hc' := hc
      simp only [cands, List.mem_filter, mem_allAsg, Bool.and_eq_true] at hc'
      have hfz : Feas s z := ⟨hc'.1, (verdict_valid_feas _ hv).1, (verdict_valid_feas _ hv).2, hc'.2.2⟩
      exact ⟨hfz, fun x hx => by rw [he]; exact hopt.2 x hx⟩
    · intro hz
      refine ⟨feas_mem_cands hI hz.1, ?_, verdict_feas_valid _ hz.1⟩
      have := hz.2 y hopt.1; have := hopt.2 z hz.1; omega
  refine ⟨((nodup_allAsg k).filter _).filter _, hmem, fun i => ?_, fun i => ?_⟩
  · simp only [mandatory, List.mem_filter, List.mem_range, List.all_eq_true, hmem]
  · simp only [possible, List.mem_filter, List.mem_range, List.any_eq_true, hmem]

/-! ## A complete proof-producing oracle for finite domains -/

section Finite

variable (s : Spec W k) [DecidablePred s.A] [DecidablePred s.T]

instance ctxDec (w : W) (y : List Bool) : Decidable (Ctx s w y) := by
  unfold Ctx; exact inferInstance

/-- Enumeration oracle over a list containing every world satisfying `A`. -/
def finiteOracle (worlds : List W) (hcomp : ∀ w, s.A w → w ∈ worlds) : Oracle s := fun y =>
  match hb : worlds.find? (fun w => decide (Ctx s w y) && !decide (s.T w)) with
  | some w =>
      have hp := List.find?_some hb
      .counter w (by simp at hp; exact hp.1) (by simp at hp; exact hp.2)
  | none =>
    match hc : worlds.find? (fun w => decide (Ctx s w y)) with
    | some w =>
        have hp := List.find?_some hc
        .valid w (by simpa using hp) (fun v hv => by
          have hm := hcomp v hv.1
          rw [List.find?_eq_none] at hb
          have := hb v hm
          simp only [Bool.and_eq_true, decide_eq_true_eq, Bool.not_eq_true', decide_eq_false_iff_not,
            not_and, Classical.not_not] at this
          exact this hv)
    | none =>
        .inconsistent (fun v hv => by
          rw [List.find?_eq_none] at hc
          have := hc v (hcomp v hv.1)
          simp only [decide_eq_true_eq] at this
          exact this hv)

end Finite

/-! ## Boolean problems: agreement with the symbolic route -/

/-- The theorem-level specification of a Boolean abduction problem. -/
def ofProblem {m : Nat} (p : Problem m k) : Spec (List Bool) k where
  A w := w.length = m ∧ p.ambient.eval (envOf w) = true
  T w := p.target.eval (envOf w) = true
  H i w := (p.hyp i).eval (envOf w)
  cost := p.cost
  lockedIn := p.lockedIn
  lockedOut := p.lockedOut

theorem feas_ofProblem_iff {m : Nat} (p : Problem m k) (y : List Bool) :
    Feas (ofProblem p) y ↔ Feasible p y := by
  unfold Feas Feasible Consistent Sufficient PCSAssumptionDiscovery.LocksOK LocksOK
  simp only [ofProblem, Ctx, PCSAssumptionDiscovery.Context, Bool.and_eq_true, List.all_eq_true,
    Bool.not_eq_true']
  constructor
  · rintro ⟨hl, ⟨w, ⟨hw, ha⟩, hh⟩, hs, hin, hout⟩
    exact ⟨hl, ⟨w, hw, ha, hh⟩, fun v hv hc => hs v ⟨⟨hv, hc.1⟩, hc.2⟩, hin, hout⟩
  · rintro ⟨hl, ⟨w, hw, ha, hh⟩, hs, hin, hout⟩
    exact ⟨hl, ⟨w, ⟨hw, ha⟩, hh⟩, fun v ⟨⟨hv, hc⟩, hh⟩ => hs v hv ⟨hc, hh⟩, hin, hout⟩

theorem cost_ofProblem {m : Nat} (p : Problem m k) (y : List Bool) :
    cost (ofProblem p) y = selCost p y := rfl

theorem opt_ofProblem_iff {m : Nat} (p : Problem m k) (y : List Bool) :
    Opt (ofProblem p) y ↔ Optimal p y := by
  unfold Opt Optimal
  simp only [feas_ofProblem_iff, cost_ofProblem]

instance {m : Nat} (p : Problem m k) : DecidablePred (ofProblem p).A := fun w => by
  unfold ofProblem; exact inferInstance

instance {m : Nat} (p : Problem m k) : DecidablePred (ofProblem p).T := fun w => by
  unfold ofProblem; exact inferInstance

/-- The complete enumeration oracle for a Boolean problem. -/
def boolOracle {m : Nat} (p : Problem m k) : Oracle (ofProblem p) :=
  finiteOracle (ofProblem p) (allAsg m) (fun _ hw => mem_allAsg.2 hw.1)

/-- **CEGAR and the decision-diagram route return the same explanation and cost.** -/
theorem cegar_agrees_with_symbolic {m : Nat} {p : Problem m k} {lim : PCSDD.Limits}
    {e : Explanation} (hd : discover p lim = .optimal e) (o : Oracle (ofProblem p)) {fuel : Nat}
    {y : List Bool} {w : List Bool} {cls : List Clause}
    (hc : run (ofProblem p) o fuel [] = .optimal y w cls) :
    y = e.selection ∧ cost (ofProblem p) y = e.cost := by
  obtain ⟨_, hlexD, hcostD, _⟩ := discover_optimal hd
  obtain ⟨_, hlexC, _⟩ := cegar_accept_optimal _ o hc
  have hlexC' : IsLexLeast (Optimal p) y :=
    ⟨(opt_ofProblem_iff p y).1 hlexC.1, fun b hb => hlexC.2 b ((opt_ofProblem_iff p b).2 hb)⟩
  have he : y = e.selection := hlexC'.unique hlexD
  exact ⟨he, by rw [he, cost_ofProblem, hcostD]⟩

end PCSAssumptionDiscovery.Cegar
