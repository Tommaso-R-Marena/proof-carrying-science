import PCSReasoningLibrary.Calculus

/-!
# A conservative, growing library of checked lemmas, macros and strategies

* `Entry` — statement (schematic in its parameters), proof (may cite earlier entries),
  declared dependency DAG, declared resource cost and the foundation/checker revision under
  which it was admitted.
* `admitOne` / `admittedB` — independent admission: correct foundation revision, every cited
  lemma is a declared dependency, every dependency strictly precedes the entry (acyclic by
  construction), and the proof checks against the statements of the preceding entries.
  Model-proposed entries enter only through this checker.
* `expand` — macro/lemma expansion into primitive actions (structural, hence terminating);
  `closeLib` — the expanded primitive proof of every entry.

Principal theorems:

* `macro_expansion_preserves_proof` — expansion of a checked proof is a checked primitive proof
  of the same statement in the same context;
* `admitted_library_conservative` — every theorem established with any admitted generation
  already has a primitive proof over the original foundation, and is valid;
* `admitted_deps_acyclic`, `admittedB_deterministic` (replay), `foundation_change_invalidates`;
* `research_plan_composes_checked_results` — certified reuse of preceding results; failed or
  blocked dependencies never become available lemmas.
-/

namespace PCSReasoningLibrary

/-- Lemma references of a proof. -/
def Pf.lemRefs : Pf → List Nat
  | .hyp _ | .topI => []
  | .lem j _ => [j]
  | .botE _ p | .andL p | .andR p | .orL _ p | .orR _ p | .lam _ p => p.lemRefs
  | .andI p q | .app p q => p.lemRefs ++ q.lemRefs
  | .orE p _ _ q r => p.lemRefs ++ q.lemRefs ++ r.lemRefs

structure Entry where
  name : String
  stmt : Fm
  proof : Pf
  deps : List Nat
  cost : Nat
  foundation : String
  deriving DecidableEq, Repr

def stmts (lib : List Entry) : List Fm := lib.map (·.stmt)

/-- Independent admission of one entry on top of `lib`. -/
def admitOne (found : String) (lib : List Entry) (e : Entry) : Bool :=
  (e.foundation == found) && e.proof.lemRefs.all (· ∈ e.deps) && e.deps.all (· < lib.length) &&
    (infer (stmts lib) [] e.proof == some e.stmt)

/-- A library generation is admitted iff every entry is admitted on top of its prefix. -/
def admittedB (found : String) (lib : List Entry) : Bool :=
  (List.range lib.length).all (fun i => match lib[i]? with
    | some e => admitOne found (lib.take i) e
    | none => false)

theorem admittedB_entry {found : String} {lib : List Entry} (h : admittedB found lib = true)
    {i : Nat} (hi : i < lib.length) : admitOne found (lib.take i) lib[i] = true := by
  simp only [admittedB, List.all_eq_true, List.mem_range] at h
  have := h i hi
  simpa [List.getElem?_eq_getElem hi] using this

/-! ## Expansion -/

/-- Replace every library reference by the instantiated expanded proof. -/
def expand (cl : List Pf) : Pf → Pf
  | .hyp φ => .hyp φ
  | .topI => .topI
  | .botE φ p => .botE φ (expand cl p)
  | .andI p q => .andI (expand cl p) (expand cl q)
  | .andL p => .andL (expand cl p)
  | .andR p => .andR (expand cl p)
  | .orL b p => .orL b (expand cl p)
  | .orR a p => .orR a (expand cl p)
  | .orE p a b q r => .orE (expand cl p) a b (expand cl q) (expand cl r)
  | .lam φ p => .lam φ (expand cl p)
  | .app p q => .app (expand cl p) (expand cl q)
  | .lem j σ => (cl.getD j .topI).subst (inst σ)

theorem Pf.subst_primitive (s : Nat → Fm) : ∀ p : Pf, p.Primitive → (p.subst s).Primitive
  | .hyp _, _ | .topI, _ => trivial
  | .lem _ _, h => h.elim
  | .botE _ p, h | .andL p, h | .andR p, h | .orL _ p, h | .orR _ p, h | .lam _ p, h =>
      Pf.subst_primitive s p h
  | .andI p q, h | .app p q, h => ⟨Pf.subst_primitive s p h.1, Pf.subst_primitive s q h.2⟩
  | .orE p _ _ q r, h =>
      ⟨Pf.subst_primitive s p h.1, Pf.subst_primitive s q h.2.1, Pf.subst_primitive s r h.2.2⟩

/-- Closed primitive proofs for the library statements. -/
def ClosedFor (lib : List Fm) (cl : List Pf) : Prop :=
  cl.length = lib.length ∧ ∀ j (hj : j < lib.length) (hc : j < cl.length),
    infer [] [] cl[j] = some lib[j] ∧ cl[j].Primitive

/-- **Macro / lemma expansion preserves the proof** and yields primitive actions only. -/
theorem macro_expansion_preserves_proof {lib : List Fm} {cl : List Pf} (hcl : ClosedFor lib cl) :
    ∀ (p : Pf) (Γ : List Fm) (φ : Fm), infer lib Γ p = some φ →
      infer [] Γ (expand cl p) = some φ ∧ (expand cl p).Primitive := by
  intro p
  induction p with
  | hyp ψ => intro Γ φ h; exact ⟨h, trivial⟩
  | topI => intro Γ φ h; exact ⟨h, trivial⟩
  | botE ψ p ih =>
      intro Γ φ h; simp only [infer] at h
      split at h
      · rename_i hp; obtain ⟨h1, h2⟩ := ih Γ _ hp
        exact ⟨by simp only [expand, infer, h1]; exact h, h2⟩
      · cases h
  | andI p q ihp ihq =>
      intro Γ φ h; simp only [infer] at h
      split at h
      · rename_i a b hp hq
        obtain ⟨h1, h2⟩ := ihp Γ _ hp; obtain ⟨h3, h4⟩ := ihq Γ _ hq
        exact ⟨by simp only [expand, infer, h1, h3]; exact h, h2, h4⟩
      · cases h
  | andL p ih =>
      intro Γ φ h; simp only [infer] at h
      split at h
      · rename_i a b hp; obtain ⟨h1, h2⟩ := ih Γ _ hp
        exact ⟨by simp only [expand, infer, h1]; exact h, h2⟩
      · cases h
  | andR p ih =>
      intro Γ φ h; simp only [infer] at h
      split at h
      · rename_i a b hp; obtain ⟨h1, h2⟩ := ih Γ _ hp
        exact ⟨by simp only [expand, infer, h1]; exact h, h2⟩
      · cases h
  | orL b p ih =>
      intro Γ φ h; simp only [infer, Option.map_eq_some_iff] at h
      obtain ⟨a, hp, rfl⟩ := h; obtain ⟨h1, h2⟩ := ih Γ _ hp
      exact ⟨by simp only [expand, infer, h1]; rfl, h2⟩
  | orR a p ih =>
      intro Γ φ h; simp only [infer, Option.map_eq_some_iff] at h
      obtain ⟨b, hp, rfl⟩ := h; obtain ⟨h1, h2⟩ := ih Γ _ hp
      exact ⟨by simp only [expand, infer, h1]; rfl, h2⟩
  | orE p a b q r ihp ihq ihr =>
      intro Γ φ h; simp only [infer] at h
      split at h
      · rename_i hp
        split at h
        · rename_i c1 c2 hq hr
          obtain ⟨h1, h2⟩ := ihp Γ _ hp
          obtain ⟨h3, h4⟩ := ihq _ _ hq
          obtain ⟨h5, h6⟩ := ihr _ _ hr
          exact ⟨by simp only [expand, infer, h1, h3, h5, if_true]; exact h, h2, h4, h6⟩
        · cases h
      · cases h
  | lam ψ p ih =>
      intro Γ φ h; simp only [infer, Option.map_eq_some_iff] at h
      obtain ⟨b, hp, rfl⟩ := h; obtain ⟨h1, h2⟩ := ih _ _ hp
      exact ⟨by simp only [expand, infer, h1]; rfl, h2⟩
  | app p q ihp ihq =>
      intro Γ φ h; simp only [infer] at h
      split at h
      · rename_i a b a' hp hq
        obtain ⟨h1, h2⟩ := ihp Γ _ hp; obtain ⟨h3, h4⟩ := ihq Γ _ hq
        exact ⟨by simp only [expand, infer, h1, h3]; exact h, h2, h4⟩
      · cases h
  | lem j σ =>
      intro Γ φ h; simp only [infer, Option.map_eq_some_iff] at h
      obtain ⟨ψ, hψ, rfl⟩ := h
      obtain ⟨hj, rfl⟩ := List.getElem?_eq_some_iff.1 hψ
      have hc : j < cl.length := by rw [hcl.1]; exact hj
      obtain ⟨h1, h2⟩ := hcl.2 j hj hc
      have h3 := infer_subst (inst σ) _ _ _ h1
      simp only [List.map_nil] at h3
      refine ⟨?_, ?_⟩
      · simp only [expand, List.getD_eq_getElem?_getD, List.getElem?_eq_getElem hc, Option.getD_some]
        exact infer_weaken _ [] Γ _ (by simp) h3
      · simp only [expand, List.getD_eq_getElem?_getD, List.getElem?_eq_getElem hc, Option.getD_some]
        exact Pf.subst_primitive _ _ h2

/-- Expanded primitive proofs of the first `n` entries. -/
def closeAux (lib : List Entry) : Nat → List Pf
  | 0 => []
  | n + 1 =>
    let cl := closeAux lib n
    cl ++ [expand cl ((lib[n]?).map (·.proof) |>.getD .topI)]

theorem closeAux_spec {found : String} {lib : List Entry} (h : admittedB found lib = true) :
    ∀ n, n ≤ lib.length → ClosedFor (stmts (lib.take n)) (closeAux lib n) := by
  intro n
  induction n with
  | zero => intro _; exact ⟨by simp [closeAux, stmts], fun j hj => by simp [stmts] at hj⟩
  | succ n ih =>
      intro hn
      have hn' : n < lib.length := by omega
      obtain ⟨hlen, hcl⟩ := ih (by omega)
      have hlen' : (closeAux lib n).length = n := by
        rw [hlen]; simp [stmts]; omega
      have ha := admittedB_entry h hn'
      simp only [admitOne, Bool.and_eq_true, beq_iff_eq] at ha
      obtain ⟨_, hinf⟩ := ha
      obtain ⟨hnew, hprim⟩ := macro_expansion_preserves_proof ⟨hlen, hcl⟩ _ _ _ hinf
      refine ⟨by simp [closeAux, stmts, hlen']; omega, fun j hj hc => ?_⟩
      simp only [stmts, List.length_map, List.length_take] at hj
      simp only [closeAux, List.getElem_append]
      split
      · rename_i hjn
        have hj' : j < (stmts (lib.take n)).length := by simp [stmts]; omega
        obtain ⟨h1, h2⟩ := hcl j hj' hjn
        refine ⟨?_, h2⟩
        rw [h1]; simp [stmts, List.getElem_take]
      · rename_i hjn
        have hjeq : j = n := by simp [closeAux] at hc; omega
        subst hjeq
        simp only [List.getElem?_eq_getElem hn', Option.map_some, Option.getD_some]
        refine ⟨?_, by simpa using hprim⟩
        simp only [List.getElem_singleton]
        rw [hnew]; simp [stmts, List.getElem_take]

/-- Expanded primitive proofs of every entry. -/
def closeLib (lib : List Entry) : List Pf := closeAux lib lib.length

theorem closeLib_spec {found : String} {lib : List Entry} (h : admittedB found lib = true) :
    ClosedFor (stmts lib) (closeLib lib) := by
  have := closeAux_spec h lib.length (Nat.le_refl _)
  rwa [List.take_length] at this

/-- **Library-extension conservativity.** -/
theorem admitted_library_conservative {found : String} {lib : List Entry}
    (h : admittedB found lib = true) {Γ : List Fm} {p : Pf} {φ : Fm}
    (hp : infer (stmts lib) Γ p = some φ) :
    infer [] Γ (expand (closeLib lib) p) = some φ ∧ (expand (closeLib lib) p).Primitive ∧
      ∀ v, (∀ ψ ∈ Γ, ψ.den v) → φ.den v := by
  obtain ⟨h1, h2⟩ := macro_expansion_preserves_proof (closeLib_spec h) p Γ φ hp
  exact ⟨h1, h2, fun v hΓ => infer_sound (lib := []) (by simp) v _ Γ φ hΓ h1⟩

/-- Every admitted statement is schematically valid. -/
theorem admitted_valid {found : String} {lib : List Entry} (h : admittedB found lib = true) :
    ∀ φ ∈ stmts lib, Valid φ := by
  intro φ hφ v
  obtain ⟨j, hj, rfl⟩ := List.getElem_of_mem hφ
  have hc := closeLib_spec h
  have hjc : j < (closeLib lib).length := by rw [hc.1]; exact hj
  exact infer_sound (lib := []) (by simp) v _ [] _ (by simp) (hc.2 j hj hjc).1

/-- **Acyclicity**: every declared dependency and every cited lemma strictly precedes. -/
theorem admitted_deps_acyclic {found : String} {lib : List Entry} (h : admittedB found lib = true)
    {i : Nat} (hi : i < lib.length) :
    (∀ d ∈ lib[i].deps, d < i) ∧ (∀ d ∈ lib[i].proof.lemRefs, d ∈ lib[i].deps) := by
  have ha := admittedB_entry h hi
  simp only [admitOne, Bool.and_eq_true, List.all_eq_true, decide_eq_true_eq, List.length_take] at ha
  obtain ⟨⟨⟨_, hrefs⟩, hdeps⟩, _⟩ := ha
  exact ⟨fun d hd => by have := hdeps d hd; omega, hrefs⟩

/-- **Deterministic replay**: admission is a pure function of the stored library. -/
theorem admittedB_deterministic (found : String) (lib : List Entry) (b₁ b₂ : Bool)
    (h₁ : admittedB found lib = b₁) (h₂ : admittedB found lib = b₂) : b₁ = b₂ := h₁ ▸ h₂

/-- **Provenance invalidation**: an entry admitted under another foundation/checker revision is
not admitted under the current one; it must be re-checked. -/
theorem foundation_change_invalidates {found found' : String} {lib : List Entry}
    (hne : found ≠ found') (h : admittedB found lib = true) (hpos : 0 < lib.length) :
    admittedB found' lib = false := by
  cases h' : admittedB found' lib
  · rfl
  · have a1 := admittedB_entry h hpos
    have a2 := admittedB_entry h' hpos
    simp only [admitOne, Bool.and_eq_true, beq_iff_eq] at a1 a2
    exact absurd (a1.1.1.1.symm.trans a2.1.1.1) hne

/-! ## Research plans with certified reuse -/

structure Node where
  goal : Fm
  deps : List Nat
  proof : Pf
  deriving DecidableEq, Repr

inductive Status where
  | verified (base : Pf)
  | failed
  | blocked
  deriving DecidableEq, Repr

def Status.base? : Status → Option Pf
  | .verified b => some b
  | _ => none

/-- Base proofs of the dependencies, if all are verified earlier nodes. -/
def depBases (done : List Status) : List Nat → Option (List Pf)
  | [] => some []
  | d :: ds =>
    match (done[d]?).bind Status.base?, depBases done ds with
    | some b, some bs => some (b :: bs)
    | _, _ => none

theorem depBases_mem {done : List Status} :
    ∀ {deps : List Nat} {bs : List Pf}, depBases done deps = some bs →
      ∀ d ∈ deps, ∃ b, (done[d]?).bind Status.base? = some b
  | [], _, _, d, hd => by simp at hd
  | x :: xs, bs, h, d, hd => by
      simp only [depBases] at h
      split at h
      · rename_i b rest hb hrest
        rcases List.mem_cons.1 hd with rfl | hd
        · exact ⟨b, hb⟩
        · exact depBases_mem hrest d hd
      · cases h

/-- One plan node: `lem k` in its proof refers to its `k`-th dependency. -/
def stepNode (plan : List Node) (done : List Status) (nd : Node) : Status :=
  match depBases done nd.deps with
  | none => .blocked
  | some bs =>
    if infer (nd.deps.map (fun d => (plan[d]?.map (·.goal)).getD .top)) [] nd.proof = some nd.goal
    then .verified (expand bs nd.proof) else .failed

def execAux (plan : List Node) : Nat → List Status
  | 0 => []
  | n + 1 => let done := execAux plan n
    done ++ [match plan[n]? with
      | some nd => stepNode plan done nd
      | none => .blocked]

/-- Execute a research plan in index order. -/
def execPlan (plan : List Node) : List Status := execAux plan plan.length

/-- Invariant: every verified node carries a primitive proof of its goal. -/
def PlanInv (plan : List Node) (done : List Status) : Prop :=
  ∀ i (hi : i < done.length) b, done[i] = .verified b →
    ∃ nd, plan[i]? = some nd ∧ infer [] [] b = some nd.goal ∧ b.Primitive

theorem depBases_spec {plan : List Node} {done : List Status} (hI : PlanInv plan done) :
    ∀ (deps : List Nat) (bs : List Pf), depBases done deps = some bs →
      ClosedFor (deps.map (fun d => (plan[d]?.map (·.goal)).getD .top)) bs := by
  intro deps
  induction deps with
  | nil => intro bs h; simp [depBases] at h; subst h; exact ⟨rfl, fun j hj => by simp at hj⟩
  | cons d ds ih =>
      intro bs h
      simp only [depBases] at h
      split at h
      rotate_left
      · cases h
      rename_i b rest hb hrest
      simp only [Option.some.injEq] at h; subst h
      obtain ⟨hlen, hcl⟩ := ih rest hrest
      obtain ⟨st, hst, hsb⟩ := Option.bind_eq_some_iff.1 hb
      cases st with
      | verified b' =>
          simp only [Status.base?, Option.some.injEq] at hsb; subst hsb
          obtain ⟨hd, hdeq⟩ := List.getElem?_eq_some_iff.1 hst
          obtain ⟨nd, hnd, hinf, hprim⟩ := hI d hd _ hdeq
          refine ⟨by simp [hlen], fun j hj hc => ?_⟩
          cases j with
          | zero => simp [hnd, hinf, hprim]
          | succ j =>
              simp only [List.length_cons, List.length_map] at hj hc
              have := hcl j (by simp; omega) (by omega)
              simpa using this
      | failed => simp [Status.base?] at hsb
      | blocked => simp [Status.base?] at hsb

theorem execAux_inv (plan : List Node) : ∀ n, n ≤ plan.length →
    (execAux plan n).length = n ∧ PlanInv plan (execAux plan n) := by
  intro n
  induction n with
  | zero => intro _; exact ⟨rfl, fun i hi => by simp [execAux] at hi⟩
  | succ n ih =>
      intro hn
      obtain ⟨hlen, hI⟩ := ih (by omega)
      refine ⟨by simp [execAux, hlen], ?_⟩
      intro i hi b hb
      simp only [execAux] at hi hb
      rw [List.getElem_append] at hb
      split at hb
      · exact hI i _ b hb
      · rename_i hin
        have hieq : i = n := by simp at hi; omega
        subst hieq
        have hn' : i < plan.length := by omega
        simp only [List.getElem?_eq_getElem hn', List.getElem_singleton] at hb
        refine ⟨plan[i], List.getElem?_eq_getElem hn', ?_⟩
        unfold stepNode at hb
        split at hb
        · cases hb
        · rename_i bs hbs
          split at hb
          · rename_i hinf
            simp only [Status.verified.injEq] at hb; subst hb
            exact macro_expansion_preserves_proof (depBases_spec hI _ bs hbs) _ _ _ hinf
          · cases hb

/-- **Research plans compose checked intermediate results** into a primitive proof of every
verified goal (and hence of the requested final theorem). -/
theorem research_plan_composes_checked_results (plan : List Node) {i : Nat} {b : Pf}
    (h : (execPlan plan)[i]? = some (.verified b)) :
    ∃ nd, plan[i]? = some nd ∧ infer [] [] b = some nd.goal ∧ b.Primitive ∧ Valid nd.goal := by
  obtain ⟨hlen, hI⟩ := execAux_inv plan plan.length (Nat.le_refl _)
  obtain ⟨hi, hb⟩ := List.getElem?_eq_some_iff.1 h
  obtain ⟨nd, hnd, hinf, hprim⟩ := hI i hi b hb
  exact ⟨nd, hnd, hinf, hprim, fun v => infer_sound (lib := []) (by simp) v b [] _ (by simp) hinf⟩

/-- **Failed or blocked dependencies are never available**: a node with such a dependency is
blocked. -/
theorem failed_dependency_blocks (plan : List Node) (done : List Status) (nd : Node) {d : Nat}
    (hd : d ∈ nd.deps) (hst : ∀ b, done[d]? ≠ some (.verified b)) :
    stepNode plan done nd = .blocked := by
  unfold stepNode
  cases hdb : depBases done nd.deps with
  | none => rfl
  | some bs =>
      exfalso
      obtain ⟨b, hb⟩ := depBases_mem hdb d hd
      obtain ⟨st, hst', hsb⟩ := Option.bind_eq_some_iff.1 hb
      cases st with
      | verified b' => exact hst b' hst'
      | failed => simp [Status.base?] at hsb
      | blocked => simp [Status.base?] at hsb

end PCSReasoningLibrary
