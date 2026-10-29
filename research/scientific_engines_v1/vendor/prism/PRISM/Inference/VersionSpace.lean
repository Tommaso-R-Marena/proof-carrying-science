module

public import PRISM.Models.Basic

/-!
# Version spaces, sharp query bounds, certification and countermodels

`K(D,A) = {m ∈ M₀ : A m ∧ m reproduces D}`.

All results here are *model-relative*: they say what follows from the declared
model class `M₀`, assumptions `A` and data `D`.  The theorem
`certified_transfers_to_truth` makes explicit the (empirical, unprovable)
adequacy hypothesis needed to transfer a certified conclusion to the physical
world.
-/

@[expose] public section

namespace PRISM

universe u v w

variable {M : Type u} {E : Type v} {O : Type w}

namespace Problem

variable [DecidableEq O] (P : Problem M E O)

/-- A model reproduces a dataset of (experiment, outcome) records. -/
def Reproduces (m : M) (D : List (E × O)) : Prop := ∀ d ∈ D, P.obs m d.1 = d.2

instance (m : M) (D : List (E × O)) : Decidable (P.Reproduces m D) := by
  unfold Reproduces; infer_instance

/-- The version space `K(D,A)` of admissible models consistent with the data. -/
def versionSpace (M₀ : Finset M) (A : M → Prop) [DecidablePred A] (D : List (E × O)) :
    Finset M :=
  M₀.filter (fun m => A m ∧ P.Reproduces m D)

variable {P}

/-- **Correctness of admissible-model filtering.** -/
theorem mem_versionSpace {M₀ : Finset M} {A : M → Prop} [DecidablePred A]
    {D : List (E × O)} {m : M} :
    m ∈ P.versionSpace M₀ A D ↔ m ∈ M₀ ∧ A m ∧ P.Reproduces m D := by
  simp [versionSpace]

/-- Adding observations can only shrink the version space. -/
theorem versionSpace_append_subset (M₀ : Finset M) (A : M → Prop) [DecidablePred A]
    (D D' : List (E × O)) : P.versionSpace M₀ A (D ++ D') ⊆ P.versionSpace M₀ A D := by
  intro m hm
  rw [mem_versionSpace] at *
  exact ⟨hm.1, hm.2.1, fun d hd => hm.2.2 d (List.mem_append_left _ hd)⟩

/-- Observing outcome `o` of experiment `e` is exactly restricting to the cell. -/
theorem versionSpace_snoc (M₀ : Finset M) (A : M → Prop) [DecidablePred A]
    (D : List (E × O)) (e : E) (o : O) :
    P.versionSpace M₀ A (D ++ [(e, o)]) = P.cell (P.versionSpace M₀ A D) e o := by
  ext m
  simp only [mem_versionSpace, mem_cell, Reproduces, List.mem_append, List.mem_singleton]
  constructor
  · rintro ⟨h1, h2, h3⟩
    exact ⟨⟨h1, h2, fun d hd => h3 d (Or.inl hd)⟩, h3 _ (Or.inr rfl)⟩
  · rintro ⟨⟨h1, h2, h3⟩, h4⟩
    refine ⟨h1, h2, fun d hd => ?_⟩
    rcases hd with hd | rfl
    · exact h3 d hd
    · exact h4

/-! ## Sharp bounds -/

omit [DecidableEq O] in
/-- **Soundness of query bounds**: every admissible model's query value lies in
`[L(K), U(K)]`. -/
theorem bounds_sound {K : Finset M} (h : K.Nonempty) {m : M} (hm : m ∈ K) :
    P.lower K h ≤ P.q m ∧ P.q m ≤ P.upper K h :=
  ⟨Finset.inf'_le _ hm, Finset.le_sup' _ hm⟩

omit [DecidableEq O] in
/-- **Sharpness of query bounds**: both bounds are attained by admissible models. -/
theorem bounds_sharp {K : Finset M} (h : K.Nonempty) :
    (∃ m ∈ K, P.q m = P.lower K h) ∧ (∃ m ∈ K, P.q m = P.upper K h) := by
  obtain ⟨a, ha, ha'⟩ := Finset.exists_mem_eq_inf' h P.q
  obtain ⟨b, hb, hb'⟩ := Finset.exists_mem_eq_sup' h P.q
  exact ⟨⟨a, ha, ha'.symm⟩, ⟨b, hb, hb'.symm⟩⟩

omit [DecidableEq O] in
/-- The interval `[L, U]` is the *smallest* interval containing all admissible
query values: any interval containing them contains `[L,U]`. -/
theorem bounds_optimal {K : Finset M} (h : K.Nonempty) {l u : ℚ}
    (hlu : ∀ m ∈ K, l ≤ P.q m ∧ P.q m ≤ u) : l ≤ P.lower K h ∧ P.upper K h ≤ u := by
  obtain ⟨⟨a, ha, ha'⟩, ⟨b, hb, hb'⟩⟩ := bounds_sharp (P := P) h
  exact ⟨ha' ▸ (hlu a ha).1, hb' ▸ (hlu b hb).2⟩

omit [DecidableEq O] in
/-- A query value `x` is achievable by an admissible model only inside the bounds,
and the bounds themselves are achievable; with this, `W(K) = 0` iff the query is
identified. -/
theorem width_eq_zero_iff {K : Finset M} :
    P.width K = 0 ↔ ∀ a ∈ K, ∀ b ∈ K, P.q a = P.q b := by
  constructor
  · intro h a ha b hb
    have h1 := P.sub_le_width ha hb
    have h2 := P.sub_le_width hb ha
    linarith
  · intro h
    apply le_antisymm _ (P.width_nonneg K)
    exact (P.width_le_iff le_rfl).2 (fun a ha b hb => by rw [h a ha b hb]; simp)

/-! ## Certification, countermodels and inconsistency -/

/-- The three-way outcome for a Boolean scientific claim. -/
inductive ClaimStatus (M : Type u) where
  /-- No admissible model: the observations and assumptions are inconsistent. -/
  | inconsistent
  /-- The claim holds in every admissible model (and there is at least one). -/
  | certified
  /-- An explicit admissible countermodel. -/
  | falsified (m : M)

open Classical in
/-- The (specification-level) classifier of a claim relative to a version space. -/
noncomputable def classify (K : Finset M) (C : M → Prop) : ClaimStatus M :=
  if K = ∅ then .inconsistent
  else if h : ∃ m ∈ K, ¬ C m then .falsified h.choose else .certified

open Classical in
omit [DecidableEq O] in
/-- Soundness of `classify`: `certified` really means universal truth over a
nonempty version space; `falsified m` really gives an admissible countermodel;
`inconsistent` really means the version space is empty. -/
theorem classify_sound (K : Finset M) (C : M → Prop) :
    (classify K C = .inconsistent ↔ K = ∅) ∧
    (classify K C = .certified ↔ K.Nonempty ∧ ∀ m ∈ K, C m) ∧
    (∀ m, classify K C = .falsified m → m ∈ K ∧ ¬ C m) := by
  unfold classify
  by_cases hK : K = ∅
  · simp [hK]
  · have hne : K.Nonempty := Finset.nonempty_iff_ne_empty.2 hK
    by_cases h : ∃ m ∈ K, ¬ C m
    · have e1 : (if K = ∅ then ClaimStatus.inconsistent else
          if h : ∃ m ∈ K, ¬ C m then ClaimStatus.falsified h.choose else .certified)
          = ClaimStatus.falsified h.choose := by rw [if_neg hK, dif_pos h]
      rw [e1]
      refine ⟨by simp [hK], ?_, ?_⟩
      · simp only [reduceCtorEq, false_iff, not_and]
        intro _ h'
        obtain ⟨m, hm, hc⟩ := h
        exact hc (h' m hm)
      · rintro m ⟨⟩
        exact h.choose_spec
    · have e1 : (if K = ∅ then ClaimStatus.inconsistent else
          if h : ∃ m ∈ K, ¬ C m then ClaimStatus.falsified h.choose else .certified)
          = ClaimStatus.certified := by rw [if_neg hK, dif_neg h]
      rw [e1]
      push_neg at h
      refine ⟨by simp [hK], by simp only [true_iff]; exact ⟨hne, h⟩, ?_⟩
      rintro m ⟨⟩

omit [DecidableEq O] in
/-- Why inconsistency must be reported: over an empty version space *every* claim,
and its negation, is vacuously "certified". -/
theorem empty_certifies_everything (C : M → Prop) :
    (∀ m ∈ (∅ : Finset M), C m) ∧ (∀ m ∈ (∅ : Finset M), ¬ C m) := by simp

/-- An independently checkable **inconsistency certificate**: for every candidate
model, either a violated assumption or an index of a datum it fails to reproduce. -/
def InconsistencyCert (M₀ : Finset M) (A : M → Prop) (D : List (E × O))
    (r : M → Option (Fin D.length)) : Prop :=
  ∀ m ∈ M₀, match r m with
    | none => ¬ A m
    | some i => P.obs m (D.get i).1 ≠ (D.get i).2

theorem inconsistencyCert_sound {M₀ : Finset M} {A : M → Prop} [DecidablePred A]
    {D : List (E × O)} {r : M → Option (Fin D.length)}
    (hc : P.InconsistencyCert M₀ A D r) : P.versionSpace M₀ A D = ∅ := by
  ext m
  simp only [mem_versionSpace, Finset.notMem_empty, iff_false, not_and]
  intro hm hA hR
  have := hc m hm
  cases h : r m with
  | none => rw [h] at this; exact this hA
  | some i => rw [h] at this; exact this (hR _ (List.get_mem D i))

/-- Inconsistency certificates are complete: whenever the version space is empty a
certificate exists. -/
theorem inconsistencyCert_complete {M₀ : Finset M} {A : M → Prop} [DecidablePred A]
    {D : List (E × O)} (h : P.versionSpace M₀ A D = ∅) :
    ∃ r, P.InconsistencyCert M₀ A D r := by
  classical
  refine ⟨fun m => if hA : A m then
    (if hD : ∃ i : Fin D.length, P.obs m (D.get i).1 ≠ (D.get i).2 then some hD.choose
      else none) else none, ?_⟩
  intro m hm
  by_cases hA : A m
  · have hnR : ¬ P.Reproduces m D := by
      intro hR
      have : m ∈ P.versionSpace M₀ A D := mem_versionSpace.2 ⟨hm, hA, hR⟩
      rw [h] at this; simp at this
    have hD : ∃ i : Fin D.length, P.obs m (D.get i).1 ≠ (D.get i).2 := by
      by_contra hcon
      push_neg at hcon
      apply hnR
      intro d hd
      obtain ⟨i, rfl⟩ := List.get_of_mem hd
      exact hcon i
    simp only [hA, dite_true, hD]
    exact hD.choose_spec
  · simp [hA]

/-- **Model-relative versus empirical truth.**  A certified conclusion transfers to
the true physical mechanism `m⋆` *only under the adequacy hypothesis* that `m⋆` is in
the declared model class, satisfies the declared assumptions and reproduces the data.
No theorem of PRISM discharges this hypothesis; it is an empirical assumption. -/
theorem certified_transfers_to_truth {M₀ : Finset M} {A : M → Prop} [DecidablePred A]
    {D : List (E × O)} {C : M → Prop}
    (hcert : ∀ m ∈ P.versionSpace M₀ A D, C m)
    {mstar : M} (h₁ : mstar ∈ M₀) (h₂ : A mstar) (h₃ : P.Reproduces mstar D) : C mstar :=
  hcert mstar (mem_versionSpace.2 ⟨h₁, h₂, h₃⟩)

/-- The adequacy hypothesis cannot be dropped: a claim certified over the model class
can fail for a mechanism outside it. -/
theorem certified_does_not_imply_truth :
    ∃ (P : Problem Bool Unit Unit) (M₀ : Finset Bool),
      (∀ m ∈ P.versionSpace M₀ (fun _ => True) [], P.q m = 0) ∧ P.q true ≠ 0 := by
  refine ⟨⟨fun _ _ => (), fun b => if b then 1 else 0, fun _ => 0⟩, {false}, ?_, ?_⟩
  · intro m hm
    rw [mem_versionSpace] at hm
    simp only [Finset.mem_singleton] at hm
    simp [hm.1]
  · simp

end Problem

end PRISM
