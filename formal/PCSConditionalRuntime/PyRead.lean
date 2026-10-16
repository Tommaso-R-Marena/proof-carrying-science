import PCSConditionalRuntime.PyShrink

/-!
# Read-back of heap structures that avoid a set of mutable addresses

`rbM M` is `readback` that refuses to visit addresses in `M` (the objects `check` may still
overwrite).  Its results survive every heap evolution that only changes addresses in `M` and
appends (`ReadsM.frame`), and they are results of the plain `readback` (`ReadsM.readback`).
`ReadsM` hides the fuel (read-back is monotone in its fuel).
-/

namespace PCSCR.Py

open PCSCR PCSDD PCSOmega

open Classical in
noncomputable def rbM (M : Nat → Prop) : Nat → Heap → V → Option T
  | 0, _, _ => none
  | n + 1, h, v => match v with
    | .none => some .null
    | .bool b => some (.bool b)
    | .int i => some (.int i)
    | .str s => some (.str s)
    | .tup xs => (xs.mapM (rbM M n h)).map .arr
    | .ref a => if M a then none else match hget h a with
      | some (.list xs) => (xs.mapM (rbM M n h)).map .arr
      | some (.dict kvs) => (kvs.mapM fun (p : V × V) => match p.1 with
          | .str k => (rbM M n h p.2).map fun t => (k, t)
          | _ => none).map .obj
      | _ => none
    | _ => none

/-- Generic transport: unvisited addresses may change, visited ones must be preserved. -/
theorem rbM_transport {M M' : Nat → Prop} {h h' : Heap}
    (hyp : ∀ a o, ¬ M a → hget h a = some o → ¬ M' a ∧ hget h' a = some o) :
    ∀ (fu : Nat) (v : V) (t : T), rbM M fu h v = some t → rbM M' fu h' v = some t
  | 0, _, _, hr => by simp [rbM] at hr
  | fu + 1, v, t, hr => by
    cases v with
    | tup xs =>
      simp only [rbM] at hr ⊢
      rw [Option.map_eq_some_iff] at hr
      obtain ⟨ys, hm, rfl⟩ := hr
      rw [mapM_some_congr xs ys hm (fun x _ y hy => rbM_transport hyp fu x y hy)]; rfl
    | ref a =>
      simp only [rbM] at hr ⊢
      by_cases hM : M a
      · simp [hM] at hr
      simp only [hM, if_false] at hr
      cases hg : hget h a with
      | none => simp [hg] at hr
      | some o =>
        obtain ⟨hM', hg'⟩ := hyp a o hM hg
        simp only [hM', if_false, hg']
        rw [hg] at hr
        cases o with
        | list xs =>
          simp only at hr ⊢
          rw [Option.map_eq_some_iff] at hr
          obtain ⟨ys, hm, rfl⟩ := hr
          rw [mapM_some_congr xs ys hm (fun x _ y hy => rbM_transport hyp fu x y hy)]; rfl
        | dict kvs =>
          simp only at hr ⊢
          rw [Option.map_eq_some_iff] at hr
          obtain ⟨ys, hm, rfl⟩ := hr
          rw [mapM_some_congr kvs ys hm (fun p _ y hy => by
            obtain ⟨p1, p2⟩ := p
            cases p1 with
            | str k =>
              simp only at hy ⊢
              cases hq : rbM M fu h p2 with
              | none => simp [hq] at hy
              | some q => rw [rbM_transport hyp fu p2 q hq]; rw [hq] at hy; exact hy
            | _ => simp at hy)]
          rfl
        | inst _ _ => simp at hr
    | _ => simp [rbM] at hr ⊢; try exact hr

theorem rbM_mono {M : Nat → Prop} {h : Heap} :
    ∀ (fu fu' : Nat), fu ≤ fu' → ∀ (v : V) (t : T), rbM M fu h v = some t → rbM M fu' h v = some t
  | 0, _, _, _, _, hr => by simp [rbM] at hr
  | fu + 1, fu', hle, v, t, hr => by
    obtain ⟨n', rfl⟩ : ∃ n', fu' = n' + 1 := ⟨fu' - 1, by omega⟩
    have hn : fu ≤ n' := by omega
    cases v with
    | tup xs =>
      simp only [rbM] at hr ⊢
      rw [Option.map_eq_some_iff] at hr
      obtain ⟨ys, hm, rfl⟩ := hr
      rw [mapM_some_congr xs ys hm (fun x _ y hy => rbM_mono fu n' hn x y hy)]; rfl
    | ref a =>
      simp only [rbM] at hr ⊢
      by_cases hM : M a
      · simp [hM] at hr
      simp only [hM, if_false] at hr ⊢
      cases hg : hget h a with
      | none => simp [hg] at hr
      | some o =>
        rw [hg] at hr
        cases o with
        | list xs =>
          simp only at hr ⊢
          rw [Option.map_eq_some_iff] at hr
          obtain ⟨ys, hm, rfl⟩ := hr
          rw [mapM_some_congr xs ys hm (fun x _ y hy => rbM_mono fu n' hn x y hy)]; rfl
        | dict kvs =>
          simp only at hr ⊢
          rw [Option.map_eq_some_iff] at hr
          obtain ⟨ys, hm, rfl⟩ := hr
          rw [mapM_some_congr kvs ys hm (fun p _ y hy => by
            obtain ⟨p1, p2⟩ := p
            cases p1 with
            | str k =>
              simp only at hy ⊢
              cases hq : rbM M fu h p2 with
              | none => simp [hq] at hy
              | some q => rw [rbM_mono fu n' hn p2 q hq]; rw [hq] at hy; exact hy
            | _ => simp at hy)]
          rfl
        | inst _ _ => simp at hr
    | _ => simp [rbM] at hr ⊢; try exact hr

theorem rbM_fuel {M : Nat → Prop} {h : Heap} (fu : Nat) (v : V) (t : T) (hr : rbM M fu h v = some t) :
    rbM M (fu + 1) h v = some t := rbM_mono fu (fu + 1) (by omega) v t hr

theorem rbM_le {M : Nat → Prop} {h : Heap} {fu fu' : Nat} (hle : fu ≤ fu') {v : V} {t : T}
    (hr : rbM M fu h v = some t) : rbM M fu' h v = some t := rbM_mono fu fu' hle v t hr

theorem rbM_readback {M : Nat → Prop} {h : Heap} :
    ∀ (fu : Nat) (v : V) (t : T), rbM M fu h v = some t → readback fu h v = some t
  | 0, _, _, hr => by simp [rbM] at hr
  | fu + 1, v, t, hr => by
    cases v with
    | tup xs =>
      simp only [rbM, readback] at hr ⊢
      rw [Option.map_eq_some_iff] at hr
      obtain ⟨ys, hm, rfl⟩ := hr
      rw [mapM_some_congr xs ys hm (fun x _ y hy => rbM_readback fu x y hy)]; rfl
    | ref a =>
      simp only [rbM, readback] at hr ⊢
      by_cases hM : M a
      · simp [hM] at hr
      simp only [hM, if_false] at hr
      cases hg : hget h a with
      | none => simp [hg] at hr
      | some o =>
        rw [hg] at hr
        cases o with
        | list xs =>
          simp only at hr ⊢
          rw [Option.map_eq_some_iff] at hr
          obtain ⟨ys, hm, rfl⟩ := hr
          rw [mapM_some_congr xs ys hm (fun x _ y hy => rbM_readback fu x y hy)]; rfl
        | dict kvs =>
          simp only at hr ⊢
          rw [Option.map_eq_some_iff] at hr
          obtain ⟨ys, hm, rfl⟩ := hr
          rw [mapM_some_congr kvs ys hm (fun p _ y hy => by
            obtain ⟨p1, p2⟩ := p
            cases p1 with
            | str k =>
              simp only at hy ⊢
              cases hq : rbM M fu h p2 with
              | none => simp [hq] at hy
              | some q => rw [rbM_readback fu p2 q hq]; rw [hq] at hy; exact hy
            | _ => simp at hy)]
          rfl
        | inst _ _ => simp at hr
    | _ => simp [rbM, readback] at hr ⊢; try exact hr

/-! ## Fuel-free read-back facts -/

def ReadsM (M : Nat → Prop) (h : Heap) (v : V) (t : T) : Prop := ∃ fu, rbM M fu h v = some t

def ReadsL (M : Nat → Prop) (h : Heap) (vs : List V) (ts : List T) : Prop :=
  ∃ fu, vs.mapM (rbM M fu h) = some ts

noncomputable def kvStep (M : Nat → Prop) (fu : Nat) (h : Heap) (p : V × V) : Option (String × T) :=
  match p.1 with
  | .str k => (rbM M fu h p.2).map fun t => (k, t)
  | _ => none

def ReadsKV (M : Nat → Prop) (h : Heap) (kvs : List (V × V)) (kts : List (String × T)) : Prop :=
  ∃ fu, kvs.mapM (kvStep M fu h) = some kts

theorem mapM_fuel_le {α β : Type} {f : Nat → α → Option β} (hf : ∀ n x y, f n x = some y → f (n + 1) x = some y) :
    ∀ {n n' : Nat}, n ≤ n' → ∀ (xs : List α) (ys : List β), xs.mapM (f n) = some ys → xs.mapM (f n') = some ys := by
  intro n n' hle xs ys h
  induction hle with
  | refl => exact h
  | step _ ih => exact mapM_some_congr _ _ ih (fun x _ y hy => hf _ x y hy)

theorem ReadsM.int (M : Nat → Prop) (h : Heap) (i : Int) : ReadsM M h (.int i) (.int i) := ⟨1, rfl⟩
theorem ReadsM.bool (M : Nat → Prop) (h : Heap) (b : Bool) : ReadsM M h (.bool b) (.bool b) := ⟨1, rfl⟩
theorem ReadsM.str (M : Nat → Prop) (h : Heap) (s : String) : ReadsM M h (.str s) (.str s) := ⟨1, rfl⟩
theorem ReadsM.none (M : Nat → Prop) (h : Heap) : ReadsM M h .none .null := ⟨1, rfl⟩

theorem ReadsL.nil (M : Nat → Prop) (h : Heap) : ReadsL M h [] [] := ⟨0, rfl⟩

theorem ReadsL.cons {M : Nat → Prop} {h : Heap} {v : V} {t : T} {vs : List V} {ts : List T}
    (a : ReadsM M h v t) (b : ReadsL M h vs ts) : ReadsL M h (v :: vs) (t :: ts) := by
  obtain ⟨f1, h1⟩ := a
  obtain ⟨f2, h2⟩ := b
  refine ⟨max f1 f2, ?_⟩
  have e1 := rbM_le (Nat.le_max_left f1 f2) h1
  have e2 := mapM_fuel_le (f := fun n => rbM M n h) (fun n x y hy => rbM_fuel n x y hy)
    (Nat.le_max_right f1 f2) vs ts h2
  simp [List.mapM_cons, e1, e2]

theorem ReadsKV.nil (M : Nat → Prop) (h : Heap) : ReadsKV M h [] [] := ⟨0, rfl⟩

theorem kvStep_fuel {M : Nat → Prop} {h : Heap} (n : Nat) (p : V × V) (y : String × T)
    (hy : kvStep M n h p = some y) : kvStep M (n + 1) h p = some y := by
  obtain ⟨p1, p2⟩ := p
  cases p1 with
  | str k =>
    simp only [kvStep] at hy ⊢
    cases hq : rbM M n h p2 with
    | none => simp [hq] at hy
    | some q => rw [rbM_fuel n p2 q hq]; rw [hq] at hy; exact hy
  | _ => simp [kvStep] at hy

theorem ReadsKV.cons {M : Nat → Prop} {h : Heap} {k : String} {v : V} {t : T} {kvs : List (V × V)}
    {kts : List (String × T)} (a : ReadsM M h v t) (b : ReadsKV M h kvs kts) :
    ReadsKV M h ((.str k, v) :: kvs) ((k, t) :: kts) := by
  obtain ⟨f1, h1⟩ := a
  obtain ⟨f2, h2⟩ := b
  refine ⟨max f1 f2, ?_⟩
  have e1 := rbM_le (Nat.le_max_left f1 f2) h1
  have e2 := mapM_fuel_le (f := fun n => kvStep M n h) (fun n x y hy => kvStep_fuel n x y hy)
    (Nat.le_max_right f1 f2) kvs kts h2
  simp [List.mapM_cons, e2, kvStep, e1]

theorem ReadsM.list {M : Nat → Prop} {h : Heap} {a : Nat} {vs : List V} {ts : List T}
    (hg : hget h a = some (.list vs)) (hm : ¬ M a) (hl : ReadsL M h vs ts) :
    ReadsM M h (.ref a) (.arr ts) := by
  obtain ⟨fu, e⟩ := hl
  exact ⟨fu + 1, by simp [rbM, hm, hg, e]⟩

theorem ReadsM.tup {M : Nat → Prop} {h : Heap} {vs : List V} {ts : List T} (hl : ReadsL M h vs ts) :
    ReadsM M h (.tup vs) (.arr ts) := by
  obtain ⟨fu, e⟩ := hl
  exact ⟨fu + 1, by simp [rbM, e]⟩

theorem ReadsM.dict {M : Nat → Prop} {h : Heap} {a : Nat} {kvs : List (V × V)} {kts : List (String × T)}
    (hg : hget h a = some (.dict kvs)) (hm : ¬ M a) (hl : ReadsKV M h kvs kts) :
    ReadsM M h (.ref a) (.obj kts) := by
  obtain ⟨fu, e⟩ := hl
  refine ⟨fu + 1, ?_⟩
  simp only [rbM, hm, if_false, hg]
  have : (kvs.mapM fun (p : V × V) => match p.1 with
      | .str k => (rbM M fu h p.2).map fun t => (k, t)
      | _ => Option.none) = some kts := e
  rw [this]; rfl

theorem ReadsM.transport {M M' : Nat → Prop} {h h' : Heap}
    (hyp : ∀ a o, ¬ M a → hget h a = some o → ¬ M' a ∧ hget h' a = some o) {v : V} {t : T}
    (r : ReadsM M h v t) : ReadsM M' h' v t := by
  obtain ⟨fu, e⟩ := r
  exact ⟨fu, rbM_transport hyp fu v t e⟩

theorem ReadsM.frame {M : Nat → Prop} {h h' : Heap} (F : FrameS M h h') {v : V} {t : T}
    (r : ReadsM M h v t) : ReadsM M h' v t :=
  r.transport (fun a o hm hg => ⟨hm, by rw [F.2 a (hget_lt hg) hm]; exact hg⟩)

theorem ReadsM.anti {M M' : Nat → Prop} {h : Heap} (hs : ∀ a, M' a → M a) {v : V} {t : T}
    (r : ReadsM M h v t) : ReadsM M' h v t :=
  r.transport (fun a o hm hg => ⟨fun e => hm (hs a e), hg⟩)

theorem ReadsL.frame {M : Nat → Prop} {h h' : Heap} (F : FrameS M h h') {vs : List V} {ts : List T}
    (r : ReadsL M h vs ts) : ReadsL M h' vs ts := by
  obtain ⟨fu, e⟩ := r
  exact ⟨fu, mapM_some_congr _ _ e (fun x _ y hy =>
    rbM_transport (fun a o hm hg => ⟨hm, by rw [F.2 a (hget_lt hg) hm]; exact hg⟩) fu x y hy)⟩

theorem ReadsM.readback {M : Nat → Prop} {h : Heap} {v : V} {t : T} (r : ReadsM M h v t) :
    ∃ fu, readback fu h v = some t := by
  obtain ⟨fu, e⟩ := r
  exact ⟨fu, rbM_readback fu v t e⟩

/-- Read-back is deterministic across fuels. -/
theorem readback_det {h : Heap} {v : V} {t t' : T} {fu fu' : Nat} (a : readback fu h v = some t)
    (b : readback fu' h v = some t') : t = t' := by
  have a' : rbM (fun _ => False) fu h v = some t := by
    have : ∀ (fu : Nat) (v : V) (t : T), readback fu h v = some t → rbM (fun _ => False) fu h v = some t := by
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
    exact this fu v t a
  have b' : rbM (fun _ => False) fu' h v = some t' := by
    have : ∀ (fu : Nat) (v : V) (t : T), readback fu h v = some t → rbM (fun _ => False) fu h v = some t := by
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
    exact this fu' v t' b
  have e1 := rbM_le (Nat.le_max_left fu fu') a'
  have e2 := rbM_le (Nat.le_max_right fu fu') b'
  rw [e1] at e2; cases e2; rfl

end PCSCR.Py
