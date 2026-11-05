import PCS.V2.Common

/-!
# Separator splitting, declaratively and executably

`splitAt sep s` is Python's `s.split(sep)` for a one-symbol separator: it returns the
maximal separator-free segments between occurrences of `sep` (so `"".split(",")` is
`[""]` and `"a,".split(",")` is `["a", ""]`).

The declarative meaning is `SplitBy sep s parts`: `parts` is a non-empty list of
separator-free segments whose `sep`-join is exactly `s`.  The two are proved to coincide
(`splitAt_sound`, `splitAt_complete`), so a segmentation is unique (`splitBy_unique`).

`Pointwise R xs ys` is the declarative counterpart of `mapOpt`.
-/

namespace PCS.V2.TextSplit

open PCS.V2.Common

variable {α : Type} [DecidableEq α]

/-- Python `str.split(sep)` for a single-symbol separator. -/
def splitAt (sep : α) : List α → List (List α)
  | [] => [[]]
  | c :: cs =>
    if c = sep then [] :: splitAt sep cs
    else
      match splitAt sep cs with
      | p :: ps => (c :: p) :: ps
      | [] => [[c]]

/-- Join segments with a separator (inverse of `splitAt`). -/
def joinWith (sep : α) : List (List α) → List α
  | [] => []
  | [p] => p
  | p :: q :: ps => p ++ sep :: joinWith sep (q :: ps)

/-- Declarative segmentation: `parts` are separator-free and join to `s`. -/
def SplitBy (sep : α) (s : List α) (parts : List (List α)) : Prop :=
  parts ≠ [] ∧ joinWith sep parts = s ∧ ∀ p ∈ parts, sep ∉ p

theorem splitAt_ne_nil (sep : α) : ∀ s : List α, splitAt sep s ≠ []
  | [] => by simp [splitAt]
  | c :: cs => by
    unfold splitAt
    split
    · simp
    · split <;> simp

omit [DecidableEq α] in
theorem joinWith_cons_head (sep : α) (c : α) :
    ∀ (p : List α) (ps : List (List α)), joinWith sep ((c :: p) :: ps) = c :: joinWith sep (p :: ps)
  | _, [] => rfl
  | _, _ :: _ => rfl

omit [DecidableEq α] in
theorem joinWith_nil_cons (sep : α) :
    ∀ (ps : List (List α)), ps ≠ [] → joinWith sep ([] :: ps) = sep :: joinWith sep ps
  | [], h => absurd rfl h
  | _ :: _, _ => rfl

theorem splitAt_join (sep : α) : ∀ s : List α, joinWith sep (splitAt sep s) = s
  | [] => rfl
  | c :: cs => by
    unfold splitAt
    split
    · rename_i hc
      rw [joinWith_nil_cons sep _ (splitAt_ne_nil sep cs), splitAt_join sep cs, hc]
    · have ih := splitAt_join sep cs
      split
      · rename_i p ps hps
        rw [hps] at ih
        rw [joinWith_cons_head, ih]
      · rename_i hps
        exact absurd hps (splitAt_ne_nil sep cs)

theorem splitAt_no_sep (sep : α) : ∀ (s : List α), ∀ p ∈ splitAt sep s, sep ∉ p
  | [], p, hp => by simp [splitAt] at hp; subst hp; simp
  | c :: cs, p, hp => by
    unfold splitAt at hp
    split at hp
    · simp only [List.mem_cons] at hp
      rcases hp with rfl | hp
      · simp
      · exact splitAt_no_sep sep cs p hp
    · rename_i hc
      have ih := splitAt_no_sep sep cs
      split at hp
      · rename_i q qs hqs
        rw [hqs] at ih
        simp only [List.mem_cons] at hp
        rcases hp with rfl | hp
        · intro h
          simp only [List.mem_cons] at h
          rcases h with h | h
          · exact hc h.symm
          · exact ih q (by simp) h
        · exact ih p (by simp [hp])
      · simp only [List.mem_cons, List.not_mem_nil, or_false] at hp
        subst hp
        intro h
        simp only [List.mem_cons, List.not_mem_nil, or_false] at h
        exact hc h.symm

/-- `splitAt` produces a declarative segmentation. -/
theorem splitAt_sound (sep : α) (s : List α) : SplitBy sep s (splitAt sep s) :=
  ⟨splitAt_ne_nil sep s, splitAt_join sep s, splitAt_no_sep sep s⟩

theorem splitAt_of_no_sep (sep : α) : ∀ (p : List α), sep ∉ p → splitAt sep p = [p]
  | [], _ => rfl
  | c :: cs, h => by
    have hc : c ≠ sep := fun e => h (by simp [e])
    have ih := splitAt_of_no_sep sep cs (fun e => h (List.mem_cons_of_mem _ e))
    simp [splitAt, hc, ih]

theorem splitAt_append_sep (sep : α) (t : List α) :
    ∀ (p : List α), sep ∉ p → splitAt sep (p ++ sep :: t) = p :: splitAt sep t
  | [], _ => by simp [splitAt]
  | c :: cs, h => by
    have hc : c ≠ sep := fun e => h (by simp [e])
    have ih := splitAt_append_sep sep t cs (fun e => h (List.mem_cons_of_mem _ e))
    simp [splitAt, hc, ih]

/-- Every declarative segmentation is the one computed by `splitAt`. -/
theorem splitAt_complete (sep : α) :
    ∀ (s : List α) (parts : List (List α)), SplitBy sep s parts → splitAt sep s = parts
  | _, [], ⟨hne, _, _⟩ => absurd rfl hne
  | s, [p], ⟨_, hj, hp⟩ => by
    simp only [joinWith] at hj; subst hj
    exact splitAt_of_no_sep sep _ (hp _ (by simp))
  | s, p :: q :: ps, ⟨_, hj, hp⟩ => by
    simp only [joinWith] at hj; subst hj
    rw [splitAt_append_sep sep _ p (hp p (by simp))]
    congr 1
    exact splitAt_complete sep _ (q :: ps)
      ⟨by simp, rfl, fun x hx => hp x (List.mem_cons_of_mem _ hx)⟩

theorem splitBy_unique {sep : α} {s : List α} {ps qs : List (List α)}
    (h₁ : SplitBy sep s ps) (h₂ : SplitBy sep s qs) : ps = qs :=
  (splitAt_complete sep s ps h₁).symm.trans (splitAt_complete sep s qs h₂)

theorem splitBy_iff (sep : α) (s : List α) (parts : List (List α)) :
    SplitBy sep s parts ↔ splitAt sep s = parts :=
  ⟨splitAt_complete sep s parts, fun h => h ▸ splitAt_sound sep s⟩

/-! ## Pointwise relations and `mapOpt` -/

/-- Declarative pointwise relation between two lists. -/
inductive Pointwise {β γ : Type} (R : β → γ → Prop) : List β → List γ → Prop
  | nil : Pointwise R [] []
  | cons {x y xs ys} : R x y → Pointwise R xs ys → Pointwise R (x :: xs) (y :: ys)

theorem mapOpt_pointwise {β γ : Type} {f : β → Option γ} :
    ∀ {xs : List β} {ys : List γ}, mapOpt f xs = some ys ↔ Pointwise (fun x y => f x = some y) xs ys
  | [], ys => by
    constructor
    · intro h; cases h; exact Pointwise.nil
    · intro h; cases h; rfl
  | x :: xs, ys => by
    constructor
    · intro h
      simp only [mapOpt] at h
      split at h
      · rename_i y ys' hy hys
        cases h
        exact Pointwise.cons hy (mapOpt_pointwise.1 hys)
      · cases h
    · intro h
      cases h with
      | cons hy hys =>
        simp only [mapOpt, hy, mapOpt_pointwise.2 hys]

theorem Pointwise.imp {β γ : Type} {R S : β → γ → Prop} (hRS : ∀ x y, R x y → S x y) :
    ∀ {xs : List β} {ys : List γ}, Pointwise R xs ys → Pointwise S xs ys
  | _, _, .nil => .nil
  | _, _, .cons h t => .cons (hRS _ _ h) (Pointwise.imp hRS t)

theorem Pointwise.functional {β γ : Type} {R : β → γ → Prop}
    (hR : ∀ x y₁ y₂, R x y₁ → R x y₂ → y₁ = y₂) :
    ∀ {xs : List β} {ys zs : List γ}, Pointwise R xs ys → Pointwise R xs zs → ys = zs
  | _, _, _, .nil, .nil => rfl
  | _, _, _, .cons h₁ t₁, .cons h₂ t₂ => by
    rw [hR _ _ _ h₁ h₂, Pointwise.functional hR t₁ t₂]

theorem Pointwise.forall_mem {β γ : Type} {R : β → γ → Prop} :
    ∀ {xs : List β} {ys : List γ}, Pointwise R xs ys → ∀ y ∈ ys, ∃ x ∈ xs, R x y
  | _, _, .nil, _, hy => by cases hy
  | _, _, .cons h t, y, hy => by
    simp only [List.mem_cons] at hy
    rcases hy with rfl | hy
    · exact ⟨_, List.mem_cons_self, h⟩
    · obtain ⟨x, hx, hr⟩ := Pointwise.forall_mem t y hy
      exact ⟨x, List.mem_cons_of_mem _ hx, hr⟩

theorem Pointwise.length_eq {β γ : Type} {R : β → γ → Prop} :
    ∀ {xs : List β} {ys : List γ}, Pointwise R xs ys → xs.length = ys.length
  | _, _, .nil => rfl
  | _, _, .cons _ t => by simp [Pointwise.length_eq t]

end PCS.V2.TextSplit
