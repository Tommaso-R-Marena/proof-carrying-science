import PCSMathLanguage.Language

/-!
# The exact candidate set of the controlled language

`language_candidates_exact`: for every name list, domain, body and **every** untrusted ranker,
`formalizeCore` rejects iff some precedence table it must try rejects; otherwise its candidate
list contains exactly the successful parses under the tried tables (two tables exactly when the
body mixes `∧`/`∨` without parentheses), with no duplicates, each candidate's rendered Lean
statement determines its IR (deduplication by text never merges distinct meanings), and the
ranker only permutes the list.  Status `ambiguous` (more than one candidate) therefore means
two distinct IR meanings, and the receipt layer (`verifyReceipt`) requires an explicit selected
interpretation among the recorded candidates.
-/

namespace PCSMathLanguage
namespace Language

open RoundTrip

theorem nodup_of_map {α β : Type} (f : α → β) : ∀ (l : List α), (l.map f).Nodup → l.Nodup
  | [], _ => List.nodup_nil
  | a :: l, h => by
    simp only [List.map_cons, List.nodup_cons, List.mem_map, not_exists, not_and] at h
    refine List.nodup_cons.2 ⟨fun ha => h.1 a ha rfl, nodup_of_map f l h.2⟩

/-! ## The candidate loop -/

theorem collect_none_iff (names : List String) (domain : Ty) (body : String) :
    ∀ (Ps : List Prec) (acc : List Cand),
      collect names domain body Ps acc = none ↔ ∃ P ∈ Ps, tryTable names domain body P = none
  | [], acc => by simp [collect]
  | P :: Ps, acc => by
    simp only [collect, List.mem_cons, exists_eq_or_imp]
    cases h : tryTable names domain body P with
    | none => simp
    | some c => simp [collect_none_iff names domain body Ps]

theorem collect_some (names : List String) (domain : Ty) (body : String) :
    ∀ (Ps : List Prec) (acc cs : List Cand), collect names domain body Ps acc = some cs →
      (∀ c ∈ cs, c ∈ acc ∨ ∃ P ∈ Ps, tryTable names domain body P = some c) ∧
      (∀ c ∈ acc, c ∈ cs) ∧
      (∀ P ∈ Ps, ∃ c, tryTable names domain body P = some c ∧ ∃ c' ∈ cs, c'.lean = c.lean) ∧
      ((acc.map (·.lean)).Nodup → (cs.map (·.lean)).Nodup) ∧
      cs.length ≤ acc.length + Ps.length
  | [], acc, cs, h => by
    simp only [collect, Option.some.injEq] at h; subst h
    refine ⟨fun c hc => .inl hc, fun c hc => hc, by simp, id, by simp⟩
  | P :: Ps, acc, cs, h => by
    simp only [collect] at h
    cases hP : tryTable names domain body P with
    | none => simp [hP] at h
    | some c =>
      rw [hP] at h
      simp only at h
      have IH := collect_some names domain body Ps _ cs h
      obtain ⟨I1, I2, I3, I4, I5⟩ := IH
      by_cases hany : acc.any (·.lean == c.lean) = true
      · simp only [hany, if_true] at I1 I2 I4 I5
        obtain ⟨c', hc', hl⟩ : ∃ c' ∈ acc, c'.lean = c.lean := by
          simpa using hany
        refine ⟨fun x hx => ?_, I2, ?_, I4, by simp; omega⟩
        · rcases I1 x hx with h1 | ⟨Q, hQ, hQx⟩
          · exact .inl h1
          · exact .inr ⟨Q, List.mem_cons_of_mem _ hQ, hQx⟩
        · intro Q hQ
          simp only [List.mem_cons] at hQ
          rcases hQ with rfl | hQ
          · exact ⟨c, hP, c', I2 c' hc', hl⟩
          · exact I3 Q hQ
      · simp only [hany, Bool.false_eq_true, if_false] at I1 I2 I4 I5
        refine ⟨fun x hx => ?_, fun x hx => I2 x (List.mem_append_left _ hx), ?_, ?_, ?_⟩
        · rcases I1 x hx with h1 | ⟨Q, hQ, hQx⟩
          · simp only [List.mem_append, List.mem_singleton] at h1
            rcases h1 with h1 | rfl
            · exact .inl h1
            · exact .inr ⟨P, List.mem_cons_self, hP⟩
          · exact .inr ⟨Q, List.mem_cons_of_mem _ hQ, hQx⟩
        · intro Q hQ
          simp only [List.mem_cons] at hQ
          rcases hQ with rfl | hQ
          · exact ⟨c, hP, c, I2 c (by simp), rfl⟩
          · exact I3 Q hQ
        · intro hn
          apply I4
          simp only [List.map_append, List.map_cons, List.map_nil]
          refine List.nodup_append.2 ⟨hn, by simp, ?_⟩
          intro a ha b hb
          simp only [List.mem_singleton] at hb; subst hb
          simp only [List.mem_map] at ha
          obtain ⟨d, hd, rfl⟩ := ha
          intro heq
          apply hany
          simp only [List.any_eq_true, beq_iff_eq]
          exact ⟨d, hd, heq⟩
        · simp at I5 ⊢; omega

/-! ## Rendered text determines the candidate -/

theorem reserved_true : RESERVED.contains "True" = true := by decide
theorem reserved_false : RESERVED.contains "False" = true := by decide

theorem binderVars_good : ∀ (bs : List (String × Ty)) (v v' : Vars), GoodVars v →
    binderVars bs v = some v' → GoodVars v'
  | [], v, v', hg, h => by simp only [binderVars, Option.some.injEq] at h; subst h; exact hg
  | (n, t) :: bs, v, v', hg, h => by
    simp only [binderVars] at h
    split at h
    · rename_i hc
      simp only [Bool.and_eq_true, Bool.not_eq_true', Option.isSome_eq_false_iff,
        Option.isNone_iff_eq_none] at hc
      refine binderVars_good bs _ v' ?_ h
      intro p hp
      simp only [List.mem_cons] at hp
      rcases hp with rfl | hp
      · refine ⟨hc.1.1, ?_, ?_⟩
        · rintro rfl; have := hc.1.2; rw [reserved_true] at this; cases this
        · rintro rfl; have := hc.1.2; rw [reserved_false] at this; cases this
      · exact hg p hp
    · cases h

/-- `theorem(obj)`'s rendering determines the body among declarations with the same binders. -/
theorem declCheck_injective (bs : List (String × Ty)) (e e' : Expr) (s : String)
    (h : declCheck ⟨bs, e⟩ = some s) (h' : declCheck ⟨bs, e'⟩ = some s) : e = e' := by
  unfold declCheck at h h'
  simp only at h h'
  split at h
  · cases h
  · split at h'
    · cases h'
    · cases hv : binderVars bs [] with
      | none => simp [hv] at h
      | some v =>
        rw [hv] at h h'
        simp only at h h'
        have hg : GoodVars v := binderVars_good bs [] v (by intro p hp; cases hp) hv
        split at h
        · rename_i b hb
          split at h'
          · rename_i b' hb'
            simp only [Option.some.injEq] at h h'
            have hbb : b = b' := by
              rw [← h'] at h
              split at h
              · exact h
              · have := congrArg String.toList h
                simp only [String.toList_append] at this
                exact String.toList_inj.mp (List.append_cancel_left this)
            subst hbb
            exact render_injective_on_checked v 0 0 e e' .prop .prop b hg hb hb'
          · cases h'
        · cases h

theorem tryTable_shape (names : List String) (domain : Ty) (body : String) (P : Prec) (c : Cand)
    (h : tryTable names domain body P = some c) :
    c.ir.binders = names.map (·, domain) ∧ declCheck c.ir = some c.lean := by
  unfold tryTable at h
  split at h
  · cases h
  · split at h
    · cases h
    · simp only at h
      split at h
      · split at h
        · cases h
        · split at h
          · cases h
          · simp only [Option.map_eq_some_iff] at h
            obtain ⟨l, hl, rfl⟩ := h
            exact ⟨rfl, hl⟩
      · cases h

/-- **Deduplication by rendered text never merges distinct meanings.** -/
theorem tryTable_lean_injective (names : List String) (domain : Ty) (body : String) (P Q : Prec)
    (c d : Cand) (hc : tryTable names domain body P = some c) (hd : tryTable names domain body Q = some d)
    (hl : c.lean = d.lean) : c = d := by
  obtain ⟨hcb, hcl⟩ := tryTable_shape names domain body P c hc
  obtain ⟨hdb, hdl⟩ := tryTable_shape names domain body Q d hd
  obtain ⟨⟨cb, ce⟩, cl⟩ := c
  obtain ⟨⟨db, de⟩, dl⟩ := d
  simp only at hcb hdb hl hcl hdl
  subst hcb hdb hl
  have := declCheck_injective _ ce de cl hcl hdl
  subst this; rfl

/-! ## The principal theorem -/

theorem tables_ne_nil (body : String) : tables body ≠ [] := by
  unfold tables; split <;> simp

/-- **`language_candidates_exact`.** -/
theorem language_candidates_exact (names : List String) (domain : Ty) (body : String)
    (ranker : Option (Decl → Int)) :
    (formalizeCore names domain body ranker = none ↔
      ∃ P ∈ tables body, tryTable names domain body P = none) ∧
    ∀ cs, formalizeCore names domain body ranker = some cs →
      (∀ c, c ∈ cs ↔ ∃ P ∈ tables body, tryTable names domain body P = some c) ∧
      (∀ c ∈ cs, c.ir.binders = names.map (·, domain) ∧ declCheck c.ir = some c.lean) ∧
      (cs.map (·.lean)).Nodup ∧ cs.Nodup ∧
      (∀ c ∈ cs, ∀ d ∈ cs, c.lean = d.lean → c = d) ∧
      1 ≤ cs.length ∧ cs.length ≤ (tables body).length ∧
      (status cs = "ambiguous" → ambiguous body = true) ∧
      (∀ ranker' : Option (Decl → Int), ∃ cs', formalizeCore names domain body ranker' = some cs' ∧
        cs'.Perm cs) := by
  have hrank : ∀ (r : Option (Decl → Int)) (l : List Cand), (rank r l).Perm l := by
    intro r l; cases r with
    | none => exact List.Perm.refl _
    | some f => exact List.mergeSort_perm _ _
  refine ⟨?_, fun cs h => ?_⟩
  · unfold formalizeCore
    rw [Option.map_eq_none_iff]
    exact collect_none_iff names domain body _ []
  · unfold formalizeCore at h
    simp only [Option.map_eq_some_iff] at h
    obtain ⟨cs0, h0, rfl⟩ := h
    have hp := hrank ranker cs0
    obtain ⟨I1, -, I3, I4, I5⟩ := collect_some names domain body _ [] cs0 h0
    have hmem : ∀ c, c ∈ cs0 ↔ ∃ P ∈ tables body, tryTable names domain body P = some c := by
      intro c
      constructor
      · intro hc
        rcases I1 c hc with h | h
        · cases h
        · exact h
      · rintro ⟨P, hP, hPc⟩
        obtain ⟨c1, hc1, c', hc', hl⟩ := I3 P hP
        rw [hPc] at hc1; cases hc1
        rcases I1 c' hc' with h | ⟨Q, -, hQ⟩
        · cases h
        · rw [← tryTable_lean_injective names domain body Q P c' c hQ hPc hl]; exact hc'
    have hnd : (cs0.map (·.lean)).Nodup := I4 List.nodup_nil
    refine ⟨fun c => (hp.mem_iff).trans (hmem c), ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_⟩
    · intro c hc
      obtain ⟨P, -, hPc⟩ := (hmem c).1 (hp.mem_iff.1 hc)
      exact tryTable_shape names domain body P c hPc
    · exact (hp.map _).nodup_iff.2 hnd
    · exact hp.nodup_iff.2 (nodup_of_map _ _ hnd)
    · intro c hc d hd hl
      obtain ⟨P, -, hPc⟩ := (hmem c).1 (hp.mem_iff.1 hc)
      obtain ⟨Q, -, hQd⟩ := (hmem d).1 (hp.mem_iff.1 hd)
      exact tryTable_lean_injective names domain body P Q c d hPc hQd hl
    · rw [hp.length_eq]
      obtain ⟨P, Ps, hPs⟩ : ∃ P Ps, tables body = P :: Ps := by
        cases ht : tables body with
        | nil => exact absurd ht (tables_ne_nil body)
        | cons P Ps => exact ⟨P, Ps, rfl⟩
      obtain ⟨c, hc, c', hc', -⟩ := I3 P (by rw [hPs]; exact List.mem_cons_self)
      exact List.length_pos_of_mem hc'
    · rw [hp.length_eq]; simpa using I5
    · intro hs
      unfold status at hs
      split at hs
      · rename_i hlen
        rw [hp.length_eq] at hlen
        have : cs0.length ≤ (tables body).length := by simpa using I5
        unfold tables at this
        split at this
        · assumption
        · simp at this; omega
      · exact absurd hs (by decide)
    · intro r'
      exact ⟨rank r' cs0, by simp [formalizeCore, h0], (hrank r' cs0).trans hp.symm⟩

end Language
end PCSMathLanguage
