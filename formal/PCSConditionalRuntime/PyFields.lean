import PCSConditionalRuntime.PyCex

/-!
# Field-level read-back of the result dictionary

Generic facts used to track the `result` dictionary of `check` field by field:
`tset` (the JSON counterpart of `dictSet` on string keys), `ReadsKV.dictSet`, frames and
anti-monotonicity of `ReadsKV`, appending a fresh key, read-back of old objects, and
`witSteps … 0 = 0`.
-/

namespace PCSCR.Py

open PCSCR PCSDD PCSOmega

/-- Replace the value of key `k` (first occurrence) or append it. -/
def tset : List (String × T) → String → T → List (String × T)
  | [], k, t => [(k, t)]
  | (k', t') :: rest, k, t => if k' = k then (k', t) :: rest else (k', t') :: tset rest k t

theorem readback_rbM_false {h : Heap} :
    ∀ (fu : Nat) (v : V) (t : T), readback fu h v = some t → rbM (fun _ => False) fu h v = some t := by
  intro fu
  induction fu with
  | zero => intro v t hr; simp [readback] at hr
  | succ fu ih =>
    intro v t hr
    cases v with
    | tup xs =>
      simp only [rbM, readback] at hr ⊢
      rw [Option.map_eq_some_iff] at hr
      obtain ⟨ys, hm, rfl⟩ := hr
      rw [mapM_some_congr xs ys hm (fun x _ y hy => ih x y hy)]; rfl
    | ref a =>
      simp only [rbM, readback] at hr ⊢
      simp only [if_false]
      cases hg : hget h a with
      | none => simp [hg] at hr
      | some o =>
        rw [hg] at hr
        cases o with
        | list xs =>
          simp only at hr ⊢
          rw [Option.map_eq_some_iff] at hr
          obtain ⟨ys, hm, rfl⟩ := hr
          rw [mapM_some_congr xs ys hm (fun x _ y hy => ih x y hy)]; rfl
        | dict kvs =>
          simp only at hr ⊢
          rw [Option.map_eq_some_iff] at hr
          obtain ⟨ys, hm, rfl⟩ := hr
          rw [mapM_some_congr kvs ys hm (fun p _ y hy => by
            obtain ⟨p1, p2⟩ := p
            cases p1 with
            | str k =>
              simp only at hy ⊢
              cases hq : readback fu h p2 with
              | none => simp [hq] at hy
              | some q => rw [ih p2 q hq]; rw [hq] at hy; exact hy
            | _ => simp at hy)]
          rfl
        | inst _ _ => simp at hr
    | _ => simp [rbM, readback] at hr ⊢; try exact hr

/-- A read-back on a heap all of whose addresses lie outside `M` avoids `M`. -/
theorem ReadsM.of_readback {M : Nat → Prop} {h : Heap} {v : V} {t : T} {fu : Nat}
    (hr : PCSCR.readback fu h v = some t) (hM : ∀ a, M a → h.length ≤ a) : ReadsM M h v t :=
  ReadsM.transport (M := fun _ => False)
    (fun a _ _ hg => ⟨fun hm => by have := hM a hm; have := hget_lt hg; omega, hg⟩)
    ⟨fu, readback_rbM_false fu v t hr⟩

theorem kvStep_transport {M M' : Nat → Prop} {h h' : Heap}
    (hyp : ∀ a o, ¬ M a → hget h a = some o → ¬ M' a ∧ hget h' a = some o) (fu : Nat)
    (p : V × V) (y : String × T) (hy : kvStep M fu h p = some y) : kvStep M' fu h' p = some y := by
  obtain ⟨p1, p2⟩ := p
  cases p1 with
  | str k =>
    simp only [kvStep] at hy ⊢
    cases hq : rbM M fu h p2 with
    | none => simp [hq] at hy
    | some q => rw [rbM_transport hyp fu p2 q hq]; rw [hq] at hy; exact hy
  | _ => simp [kvStep] at hy

theorem ReadsKV.transport {M M' : Nat → Prop} {h h' : Heap}
    (hyp : ∀ a o, ¬ M a → hget h a = some o → ¬ M' a ∧ hget h' a = some o) {kvs : List (V × V)}
    {kts : List (String × T)} (r : ReadsKV M h kvs kts) : ReadsKV M' h' kvs kts := by
  obtain ⟨fu, e⟩ := r
  exact ⟨fu, mapM_some_congr _ _ e (fun x _ y hy => kvStep_transport hyp fu x y hy)⟩

theorem ReadsKV.frame {M : Nat → Prop} {h h' : Heap} (F : FrameS M h h') {kvs : List (V × V)}
    {kts : List (String × T)} (r : ReadsKV M h kvs kts) : ReadsKV M h' kvs kts :=
  r.transport (fun a o hm hg => ⟨hm, by rw [F.2 a (hget_lt hg) hm]; exact hg⟩)

theorem ReadsKV.anti {M M' : Nat → Prop} {h : Heap} (hs : ∀ a, M' a → M a) {kvs : List (V × V)}
    {kts : List (String × T)} (r : ReadsKV M h kvs kts) : ReadsKV M' h kvs kts :=
  r.transport (fun a _ hm hg => ⟨fun e => hm (hs a e), hg⟩)

theorem ReadsL.anti {M M' : Nat → Prop} {h : Heap} (hs : ∀ a, M' a → M a) {vs : List V}
    {ts : List T} (r : ReadsL M h vs ts) : ReadsL M' h vs ts := by
  obtain ⟨fu, e⟩ := r
  exact ⟨fu, mapM_some_congr _ _ e (fun x _ y hy =>
    rbM_transport (fun a o hm hg => ⟨fun e => hm (hs a e), hg⟩) fu x y hy)⟩

theorem ReadsKV.uncons {M : Nat → Prop} {h : Heap} {p : V × V} {kvs : List (V × V)}
    {kts : List (String × T)} (r : ReadsKV M h (p :: kvs) kts) :
    ∃ k v t kts', p = (.str k, v) ∧ kts = (k, t) :: kts' ∧ ReadsM M h v t ∧ ReadsKV M h kvs kts' := by
  obtain ⟨fu, e⟩ := r
  obtain ⟨p1, p2⟩ := p
  simp only [List.mapM_cons, Option.bind_eq_bind] at e
  cases hs : kvStep M fu h (p1, p2) with
  | none => simp [hs] at e
  | some y =>
    rw [hs] at e
    simp only [Option.bind_some] at e
    cases hr : kvs.mapM (kvStep M fu h) with
    | none => simp [hr] at e
    | some ys =>
      rw [hr] at e
      simp only [Option.bind_some, Option.pure_def, Option.some.injEq] at e
      subst e
      cases p1 with
      | str k =>
        simp only [kvStep] at hs
        cases hq : rbM M fu h p2 with
        | none => simp [hq] at hs
        | some q =>
          rw [hq] at hs
          simp only [Option.map_some, Option.some.injEq] at hs
          subst hs
          exact ⟨k, p2, q, ys, rfl, rfl, ⟨fu, hq⟩, ⟨fu, hr⟩⟩
      | _ => simp [kvStep] at hs

theorem ReadsKV.dictSet {M : Nat → Prop} {h : Heap} {v : V} {t : T} (k : String) (hv : ReadsM M h v t) :
    ∀ (kvs : List (V × V)) (kts : List (String × T)), ReadsKV M h kvs kts →
      ReadsKV M h (PCSCR.dictSet .py kvs (.str k) v) (tset kts k t)
  | [], kts, r => by
    obtain ⟨fu, e⟩ := r
    simp at e; subst e
    exact ReadsKV.cons hv (ReadsKV.nil M h)
  | p :: kvs, kts, r => by
    obtain ⟨k', v', t', kts', rfl, rfl, h1, h2⟩ := r.uncons
    simp only [PCSCR.dictSet, tset, keyEq_str]
    by_cases hk : k' = k
    · subst hk; simp only [decide_true, if_true]; exact ReadsKV.cons hv h2
    · simp only [hk, decide_false, if_false, Bool.false_eq_true]
      exact ReadsKV.cons h1 (ReadsKV.dictSet k hv kvs kts' h2)

theorem ReadsKV.append {M : Nat → Prop} {h : Heap} {k : String} {v : V} {t : T} (hv : ReadsM M h v t) :
    ∀ (kvs : List (V × V)) (kts : List (String × T)), ReadsKV M h kvs kts →
      ReadsKV M h (kvs ++ [(.str k, v)]) (kts ++ [(k, t)])
  | [], kts, r => by
    obtain ⟨fu, e⟩ := r
    simp at e; subst e
    exact ReadsKV.cons hv (ReadsKV.nil M h)
  | p :: kvs, kts, r => by
    obtain ⟨k', v', t', kts', rfl, rfl, h1, h2⟩ := r.uncons
    exact ReadsKV.cons h1 (ReadsKV.append hv kvs kts' h2)

/-- Setting a key absent from the dictionary appends it. -/
theorem dictSet_absentKV {M : Nat → Prop} {h : Heap} (k : String) (v : V) :
    ∀ (kvs : List (V × V)) (kts : List (String × T)), ReadsKV M h kvs kts → k ∉ kts.map Prod.fst →
      PCSCR.dictSet .py kvs (.str k) v = kvs ++ [(.str k, v)]
  | [], _, _, _ => rfl
  | p :: kvs, kts, r, hk => by
    obtain ⟨k', v', t', kts', rfl, rfl, _, h2⟩ := r.uncons
    have hne : k' ≠ k := fun e => hk (by simp [e])
    simp only [PCSCR.dictSet, keyEq_str, hne, decide_false, Bool.false_eq_true, if_false, List.cons_append]
    rw [dictSet_absentKV k v kvs kts' h2 (fun hm => hk (by simp [hm]))]

theorem witStepsF_zero (ns : Nodes) : ∀ (d k : Nat), witStepsF ns d k 0 = 0
  | 0, _ => rfl
  | d + 1, k => by
    simp only [witStepsF]
    have : getNode ns 0 = none := by simp [getNode]
    rw [this]; exact witStepsF_zero ns d (k + 1)

theorem witSteps_zero (n : Nat) (ns : Nodes) : witSteps n ns 0 0 = 0 := witStepsF_zero ns _ _

end PCSCR.Py
