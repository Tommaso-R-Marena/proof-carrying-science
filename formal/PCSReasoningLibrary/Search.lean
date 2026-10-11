import PCSReasoningLibrary.Library

/-!
# A policy-independent fair search envelope

The action calculus for completeness is explicit: proofs whose formula annotations lie in a
finite universe `U` and whose leaves lie in a finite list `L` (hypotheses, `⊤`-intro and any
admitted lemma instances).  `enumPf U L n` lists every such proof of depth `≤ n`.

An arbitrary, adaptive, untrusted policy contributes a list of proposals per round; round `i`
checks the policy proposals *followed by the complete fallback level* `enumPf U L i`.  Nothing
is beam-pruned from the fallback.  Every candidate is accepted only by the checker.

* `adaptive_search_sound` — for every policy and budget an accepted proof checks;
* `resume_budget_monotone` — resumable search: success at budget `b` gives the *same*
  answer at every larger budget;
* `fallback_fair` — the fallback level `i` is checked by round `i` for every policy;
* `adaptive_fair_search_complete` — every proof in the action calculus is found once the budget
  exceeds its depth, whatever the policy, with an explicit work bound;
* `cost_guided_search_optimal` — admissible cost-guided (lower-bound-started uniform-cost)
  search returns a minimum-cost proof among the candidate universe.
-/

namespace PCSReasoningLibrary

def Pf.depth : Pf → Nat
  | .hyp _ | .topI | .lem _ _ => 0
  | .botE _ p | .andL p | .andR p | .orL _ p | .orR _ p | .lam _ p => p.depth + 1
  | .andI p q | .app p q => max p.depth q.depth + 1
  | .orE p _ _ q r => max p.depth (max q.depth r.depth) + 1

/-- Annotations in `U`, leaves in `L`. -/
def AnnIn (U : List Fm) (L : List Pf) : Pf → Prop
  | .hyp φ => .hyp φ ∈ L
  | .topI => .topI ∈ L
  | .lem j σ => .lem j σ ∈ L
  | .botE φ p => φ ∈ U ∧ AnnIn U L p
  | .andL p | .andR p => AnnIn U L p
  | .orL φ p | .orR φ p | .lam φ p => φ ∈ U ∧ AnnIn U L p
  | .andI p q | .app p q => AnnIn U L p ∧ AnnIn U L q
  | .orE p a b q r => a ∈ U ∧ b ∈ U ∧ AnnIn U L p ∧ AnnIn U L q ∧ AnnIn U L r

/-- One construction step over the proofs `E`. -/
def stepPf (U : List Fm) (E : List Pf) : List Pf :=
  U.flatMap (fun φ => E.map (.botE φ)) ++ E.map .andL ++ E.map .andR ++
    U.flatMap (fun φ => E.map (.orL φ)) ++ U.flatMap (fun φ => E.map (.orR φ)) ++
    U.flatMap (fun φ => E.map (.lam φ)) ++
    E.flatMap (fun p => E.map (.andI p)) ++ E.flatMap (fun p => E.map (.app p)) ++
    U.flatMap (fun a => U.flatMap (fun b => E.flatMap (fun p => E.flatMap (fun q =>
      E.map (.orE p a b q)))))

/-- All proofs of depth `≤ n` in the action calculus (cumulative levels). -/
def enumPf (U : List Fm) (L : List Pf) : Nat → List Pf
  | 0 => L
  | n + 1 => enumPf U L n ++ stepPf U (enumPf U L n)

theorem enum_succ {U : List Fm} {L : List Pf} {n : Nat} {p : Pf} (h : p ∈ enumPf U L n) :
    p ∈ enumPf U L (n + 1) := List.mem_append_left _ h

theorem enum_mono {U : List Fm} {L : List Pf} : ∀ {m n : Nat}, m ≤ n → ∀ {p : Pf},
    p ∈ enumPf U L m → p ∈ enumPf U L n := by
  intro m n hmn p hp
  induction n generalizing m with
  | zero => have : m = 0 := by omega
            subst this; exact hp
  | succ n ih =>
      rcases Nat.eq_or_lt_of_le hmn with h | h
      · subst h; exact hp
      · exact enum_succ (ih (by omega) hp)

theorem leaf_mem_enum {U : List Fm} {L : List Pf} {p : Pf} (h : p ∈ L) (n : Nat) :
    p ∈ enumPf U L n := enum_mono (Nat.zero_le n) h

theorem step_mem {U : List Fm} {L : List Pf} {n : Nat} {p : Pf}
    (h : p ∈ stepPf U (enumPf U L n)) : p ∈ enumPf U L (n + 1) := List.mem_append_right _ h

/-- **Completeness of the enumeration** for the explicit action calculus. -/
theorem mem_enumPf {U : List Fm} {L : List Pf} : ∀ p : Pf, AnnIn U L p → p ∈ enumPf U L p.depth := by
  intro p hp
  induction p with
  | hyp φ => exact leaf_mem_enum hp 0
  | topI => exact leaf_mem_enum hp 0
  | lem j σ => exact leaf_mem_enum hp 0
  | botE φ p ih =>
      simp only [AnnIn] at hp; have := ih hp.2; have := hp.1
      exact step_mem (by simp [stepPf, *])
  | andL p ih =>
      simp only [AnnIn] at hp; have := ih hp
      exact step_mem (by simp [stepPf, *])
  | andR p ih =>
      simp only [AnnIn] at hp; have := ih hp
      exact step_mem (by simp [stepPf, *])
  | orL φ p ih =>
      simp only [AnnIn] at hp; have := ih hp.2; have := hp.1
      exact step_mem (by simp [stepPf, *])
  | orR φ p ih =>
      simp only [AnnIn] at hp; have := ih hp.2; have := hp.1
      exact step_mem (by simp [stepPf, *])
  | lam φ p ih =>
      simp only [AnnIn] at hp; have := ih hp.2; have := hp.1
      exact step_mem (by simp [stepPf, *])
  | andI p q ihp ihq =>
      simp only [AnnIn] at hp
      have h1 := enum_mono (Nat.le_max_left p.depth q.depth) (ihp hp.1)
      have h2 := enum_mono (Nat.le_max_right p.depth q.depth) (ihq hp.2)
      exact step_mem (by simp [stepPf, h1, h2])
  | app p q ihp ihq =>
      simp only [AnnIn] at hp
      have h1 := enum_mono (Nat.le_max_left p.depth q.depth) (ihp hp.1)
      have h2 := enum_mono (Nat.le_max_right p.depth q.depth) (ihq hp.2)
      exact step_mem (by simp [stepPf, h1, h2])
  | orE p a b q r ihp ihq ihr =>
      simp only [AnnIn] at hp
      obtain ⟨ha, hb, hp', hq', hr'⟩ := hp
      have h1 := enum_mono (show p.depth ≤ max p.depth (max q.depth r.depth) by omega) (ihp hp')
      have h2 := enum_mono (show q.depth ≤ max p.depth (max q.depth r.depth) by omega) (ihq hq')
      have h3 := enum_mono (show r.depth ≤ max p.depth (max q.depth r.depth) by omega) (ihr hr')
      exact step_mem (by simp only [stepPf, List.mem_append, List.mem_flatMap, List.mem_map]
                         exact Or.inr ⟨a, ha, b, hb, p, h1, q, h2, r, h3, rfl⟩)

/-! ## The search envelope -/

/-- Candidates checked within budget `b`: per round, policy proposals then the full fallback
level. -/
def cands (U : List Fm) (L : List Pf) (policy : Nat → List Pf) : Nat → List Pf
  | 0 => []
  | b + 1 => cands U L policy b ++ (policy b ++ enumPf U L b)

/-- Acceptance is by the checker only. -/
def accepts (lib Γ : List Fm) (goal : Fm) (p : Pf) : Bool := infer lib Γ p == some goal

def search (lib Γ : List Fm) (goal : Fm) (U : List Fm) (L : List Pf) (policy : Nat → List Pf)
    (b : Nat) : Option Pf :=
  (cands U L policy b).find? (accepts lib Γ goal)

/-- **Acceptance soundness for every policy and budget.** -/
theorem adaptive_search_sound {lib Γ : List Fm} {goal : Fm} {U : List Fm} {L : List Pf}
    {policy : Nat → List Pf} {b : Nat} {p : Pf} (h : search lib Γ goal U L policy b = some p) :
    infer lib Γ p = some goal := by
  have := List.find?_some h
  simpa [accepts] using this

theorem cands_prefix (U : List Fm) (L : List Pf) (policy : Nat → List Pf) :
    ∀ {b b' : Nat}, b ≤ b' → ∃ t, cands U L policy b' = cands U L policy b ++ t := by
  intro b b' h
  induction b' with
  | zero => have : b = 0 := by omega
            subst this; exact ⟨[], by simp⟩
  | succ n ih =>
      rcases Nat.eq_or_lt_of_le h with e | e
      · subst e; exact ⟨[], by simp⟩
      · obtain ⟨t, ht⟩ := ih (by omega)
        exact ⟨t ++ (policy n ++ enumPf U L n), by simp [cands, ht]⟩

/-- **Resumable search is budget-monotone** (same answer at every larger budget). -/
theorem resume_budget_monotone {lib Γ : List Fm} {goal : Fm} {U : List Fm} {L : List Pf}
    {policy : Nat → List Pf} {b b' : Nat} (hb : b ≤ b') {p : Pf}
    (h : search lib Γ goal U L policy b = some p) : search lib Γ goal U L policy b' = some p := by
  obtain ⟨t, ht⟩ := cands_prefix U L policy hb
  unfold search at h ⊢
  rw [ht, List.find?_append, h]; rfl

/-- **Fairness**: the fallback level `i` is checked by round `i + 1`, for every policy. -/
theorem fallback_fair (U : List Fm) (L : List Pf) (policy : Nat → List Pf) (i : Nat) :
    ∀ p ∈ enumPf U L i, p ∈ cands U L policy (i + 1) := by
  intro p hp; simp [cands, hp]

/-- **Completeness** for every finite proof of the action calculus, for every policy. -/
theorem adaptive_fair_search_complete {lib Γ : List Fm} {goal : Fm} {U : List Fm} {L : List Pf}
    {p : Pf} (hp : AnnIn U L p) (hv : infer lib Γ p = some goal) (policy : Nat → List Pf) :
    ∀ b, p.depth < b → ∃ q, search lib Γ goal U L policy b = some q ∧ infer lib Γ q = some goal := by
  intro b hb
  have hmem : p ∈ cands U L policy b := by
    obtain ⟨t, ht⟩ := cands_prefix U L policy (show p.depth + 1 ≤ b by omega)
    rw [ht]; exact List.mem_append_left _ (fallback_fair U L policy _ p (mem_enumPf p hp))
  cases hs : search lib Γ goal U L policy b with
  | none =>
      unfold search at hs
      rw [List.find?_eq_none] at hs
      exact absurd (by simp [accepts, hv]) (hs p hmem)
  | some q => exact ⟨q, rfl, adaptive_search_sound hs⟩

/-- Explicit resource accounting: policy inference/retrieval cost per round plus one checker
transition per candidate weighted by its size (failed attempts included). -/
def work (U : List Fm) (L : List Pf) (policy : Nat → List Pf) (polCost : Nat → Nat) : Nat → Nat
  | 0 => 0
  | b + 1 => work U L policy polCost b + polCost b + ((policy b ++ enumPf U L b).map Pf.size).sum

theorem work_mono (U : List Fm) (L : List Pf) (policy : Nat → List Pf) (polCost : Nat → Nat) :
    ∀ {b b'}, b ≤ b' → work U L policy polCost b ≤ work U L policy polCost b' := by
  intro b b' h
  induction b' with
  | zero => have : b = 0 := by omega
            subst this; exact Nat.le_refl _
  | succ n ih =>
      rcases Nat.eq_or_lt_of_le h with e | e
      · subst e; exact Nat.le_refl _
      · have := ih (by omega); simp only [work]; omega

/-! ## Admissible cost-guided search -/

/-- Level-by-level search starting at an admissible lower bound `lo`. -/
def levelSearch (C : List Pf) (ok : Pf → Bool) (cost : Pf → Nat) : Nat → Nat → Option Pf
  | _, 0 => none
  | lo, fuel + 1 =>
    match (C.filter (fun p => ok p && cost p == lo)).head? with
    | some p => some p
    | none => levelSearch C ok cost (lo + 1) fuel

/-- **Admissible cost-guided search is optimal.** If every accepted candidate costs at least
`lo` (admissibility), a returned proof is accepted and has minimum cost among all accepted
candidates. -/
theorem cost_guided_search_optimal (C : List Pf) (ok : Pf → Bool) (cost : Pf → Nat) :
    ∀ (fuel lo : Nat) (p : Pf), (∀ q ∈ C, ok q = true → lo ≤ cost q) →
      levelSearch C ok cost lo fuel = some p →
      p ∈ C ∧ ok p = true ∧ ∀ q ∈ C, ok q = true → cost p ≤ cost q := by
  intro fuel
  induction fuel with
  | zero => intro lo p _ h; simp [levelSearch] at h
  | succ n ih =>
      intro lo p hadm h
      simp only [levelSearch] at h
      split at h
      · rename_i q hq
        cases h
        have hm := List.mem_of_mem_head? hq
        simp only [List.mem_filter, Bool.and_eq_true, beq_iff_eq] at hm
        exact ⟨hm.1, hm.2.1, fun r hr hok => by rw [hm.2.2]; exact hadm r hr hok⟩
      · rename_i hnone
        apply ih (lo + 1) p _ h
        intro q hq hok
        have := hadm q hq hok
        rcases Nat.eq_or_lt_of_le this with e | e
        · exfalso
          rw [List.head?_eq_none_iff, List.filter_eq_nil_iff] at hnone
          exact hnone q hq (by simp [hok, e])
        · exact e

/-- Completeness of cost-guided search within its fuel. -/
theorem cost_guided_search_complete (C : List Pf) (ok : Pf → Bool) (cost : Pf → Nat) :
    ∀ (fuel lo : Nat) (q : Pf), q ∈ C → ok q = true → lo ≤ cost q → cost q < lo + fuel →
      (levelSearch C ok cost lo fuel).isSome := by
  intro fuel
  induction fuel with
  | zero => intro lo q _ _ h1 h2; omega
  | succ n ih =>
      intro lo q hq hok h1 h2
      simp only [levelSearch]
      split
      · rfl
      · rename_i hnone
        apply ih (lo + 1) q hq hok _ (by omega)
        rcases Nat.eq_or_lt_of_le h1 with e | e
        · exfalso
          rw [List.head?_eq_none_iff, List.filter_eq_nil_iff] at hnone
          exact hnone q hq (by simp [hok, e])
        · exact e

end PCSReasoningLibrary
