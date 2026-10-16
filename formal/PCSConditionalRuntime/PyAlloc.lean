import PCSConditionalRuntime.PyCheckBase

/-!
# Allocation and read-back of JSON trees

* `alloc_prefix` — allocation only appends;
* `alloc_rb` — a freshly allocated tree reads back to itself (with any read-back budget that
  exceeds the number of allocated objects), on every heap extending the allocation;
* `rb_FRel` — a heap value reading back to a JSON tree that denotes a formula is a heap formula
  tree for it (`FRel`), when none of its addresses are mutable.
-/

namespace PCSCR.Py

open PCSCR PCSDD PCSOmega

mutual
theorem alloc_prefix : ∀ (h : Heap) (t : T), ∃ l, (allocT h t).2 = h ++ l
  | h, .null => ⟨[], by simp [allocT]⟩
  | h, .bool _ => ⟨[], by simp [allocT]⟩
  | h, .int _ => ⟨[], by simp [allocT]⟩
  | h, .str _ => ⟨[], by simp [allocT]⟩
  | h, .arr xs => by
      obtain ⟨l, hl⟩ := allocL_prefix h xs
      exact ⟨l ++ [.list (allocL h xs).1], by simp [allocT, hl]⟩
  | h, .obj kvs => by
      obtain ⟨l, hl⟩ := allocKV_prefix h kvs
      exact ⟨l ++ [.dict (allocKV h kvs).1], by simp [allocT, hl]⟩
theorem allocL_prefix : ∀ (h : Heap) (ts : List T), ∃ l, (allocL h ts).2 = h ++ l
  | h, [] => ⟨[], by simp [allocL]⟩
  | h, t :: ts => by
      obtain ⟨l1, h1⟩ := alloc_prefix h t
      obtain ⟨l2, h2⟩ := allocL_prefix (allocT h t).2 ts
      exact ⟨l1 ++ l2, by simp only [allocL]; rw [h2, h1]; simp⟩
theorem allocKV_prefix : ∀ (h : Heap) (kvs : List (String × T)), ∃ l, (allocKV h kvs).2 = h ++ l
  | h, [] => ⟨[], by simp [allocKV]⟩
  | h, (k, t) :: ts => by
      obtain ⟨l1, h1⟩ := alloc_prefix h t
      obtain ⟨l2, h2⟩ := allocKV_prefix (allocT h t).2 ts
      exact ⟨l1 ++ l2, by simp only [allocKV]; rw [h2, h1]; simp⟩
end

theorem HAgree.of_prefix {h h' : Heap} {l : List Obj} (e : h' = h ++ l) : HAgree h h' := by
  subst e; exact HAgree.append h l

theorem alloc_agree (h : Heap) (t : T) : HAgree h (allocT h t).2 := by
  obtain ⟨l, hl⟩ := alloc_prefix h t; exact HAgree.of_prefix hl
theorem allocL_agree (h : Heap) (ts : List T) : HAgree h (allocL h ts).2 := by
  obtain ⟨l, hl⟩ := allocL_prefix h ts; exact HAgree.of_prefix hl
theorem allocKV_agree (h : Heap) (kvs : List (String × T)) : HAgree h (allocKV h kvs).2 := by
  obtain ⟨l, hl⟩ := allocKV_prefix h kvs; exact HAgree.of_prefix hl

mutual
theorem alloc_rb : ∀ (h : Heap) (t : T) (h2 : Heap) (fu : Nat), HAgree (allocT h t).2 h2 →
    (allocT h t).2.length - h.length + 1 ≤ fu → readback fu h2 (allocT h t).1 = some t
  | h, .null, h2, fu + 1, _, _ => by simp [allocT, readback]
  | h, .bool _, h2, fu + 1, _, _ => by simp [allocT, readback]
  | h, .int _, h2, fu + 1, _, _ => by simp [allocT, readback]
  | h, .str _, h2, fu + 1, _, _ => by simp [allocT, readback]
  | h, .arr xs, h2, fu + 1, hag, hfu => by
      have ag1 : HAgree (allocL h xs).2 h2 :=
        (HAgree.append _ [.list (allocL h xs).1]).trans (by simpa [allocT] using hag)
      have hlen : (allocL h xs).2.length < h2.length := by
        have := hag.1; simp [allocT] at this; omega
      have hg : hget h2 (allocL h xs).2.length = some (.list (allocL h xs).1) := by
        rw [hag.2 _ (by simp [allocT])]; simp [allocT, hget]
      have l0 := (allocL_agree h xs).1
      have hm := allocL_rb h xs h2 fu ag1 (by simp [allocT] at hfu; omega)
      simp only [allocT, readback, hg, hm, Option.map_some]
  | h, .obj kvs, h2, fu + 1, hag, hfu => by
      have ag1 : HAgree (allocKV h kvs).2 h2 :=
        (HAgree.append _ [.dict (allocKV h kvs).1]).trans (by simpa [allocT] using hag)
      have hg : hget h2 (allocKV h kvs).2.length = some (.dict (allocKV h kvs).1) := by
        rw [hag.2 _ (by simp [allocT])]; simp [allocT, hget]
      have l0 := (allocKV_agree h kvs).1
      have hm := allocKV_rb h kvs h2 fu ag1 (by simp [allocT] at hfu; omega)
      simp only [allocT, readback, hg]
      exact (congrArg (Option.map T.obj) hm : _)
  | h, t, h2, 0, _, hfu => by omega
theorem allocL_rb : ∀ (h : Heap) (ts : List T) (h2 : Heap) (fu : Nat), HAgree (allocL h ts).2 h2 →
    (allocL h ts).2.length - h.length + 1 ≤ fu → (allocL h ts).1.mapM (readback fu h2) = some ts
  | h, [], h2, fu, _, _ => by simp [allocL]
  | h, t :: ts, h2, fu, hag, hfu => by
      have p1 := allocL_agree (allocT h t).2 ts
      have l0 := (alloc_agree h t).1
      have l1 := p1.1
      have e1 := alloc_rb h t h2 fu (p1.trans (by simpa [allocL] using hag))
        (by simp [allocL] at hfu; omega)
      have e2 := allocL_rb (allocT h t).2 ts h2 fu (by simpa [allocL] using hag)
        (by simp [allocL] at hfu; omega)
      simp only [allocL, List.mapM_cons, e1, e2]; rfl
theorem allocKV_rb : ∀ (h : Heap) (kvs : List (String × T)) (h2 : Heap) (fu : Nat),
    HAgree (allocKV h kvs).2 h2 → (allocKV h kvs).2.length - h.length + 1 ≤ fu →
    (allocKV h kvs).1.mapM (fun (p : V × V) => match p.1 with
      | .str k => (readback fu h2 p.2).map fun t => (k, t)
      | _ => none) = some kvs
  | h, [], h2, fu, _, _ => by simp [allocKV]
  | h, (k, t) :: ts, h2, fu, hag, hfu => by
      have p1 := allocKV_agree (allocT h t).2 ts
      have l0 := (alloc_agree h t).1
      have l1 := p1.1
      have e1 := alloc_rb h t h2 fu (p1.trans (by simpa [allocKV] using hag))
        (by simp [allocKV] at hfu; omega)
      have e2 := allocKV_rb (allocT h t).2 ts h2 fu (by simpa [allocKV] using hag)
        (by simp [allocKV] at hfu; omega)
      simp only [allocKV, List.mapM_cons, e1, e2]; rfl
end

/-! ## Reading fields of a read-back object -/

theorem rb_obj {fu : Nat} {h : Heap} {v : V} {kvs' : List (String × T)}
    (hr : readback fu h v = some (.obj kvs')) :
    ∃ fu' a kvs, fu = fu' + 1 ∧ v = .ref a ∧ hget h a = some (.dict kvs) ∧
      kvs.mapM (fun (p : V × V) => match p.1 with
        | .str k => (readback fu' h p.2).map fun t => (k, t)
        | _ => none) = some kvs' := by
  match fu, v, hr with
  | fu' + 1, .ref a, hr =>
    simp only [readback] at hr
    cases hg : hget h a with
    | none => simp [hg] at hr
    | some o =>
      rw [hg] at hr
      cases o with
      | list xs => simp at hr
      | inst _ _ => simp at hr
      | dict kvs =>
        simp only at hr
        rw [Option.map_eq_some_iff] at hr
        obtain ⟨ys, hm, e⟩ := hr
        cases e
        exact ⟨fu', a, kvs, rfl, rfl, hg, hm⟩
  | fu' + 1, .tup xs, hr => simp [readback] at hr
  | fu' + 1, .none, hr => simp [readback] at hr
  | fu' + 1, .bool _, hr => simp [readback] at hr
  | fu' + 1, .int _, hr => simp [readback] at hr
  | fu' + 1, .str _, hr => simp [readback] at hr
  | fu' + 1, .undef, hr => simp [readback] at hr
  | fu' + 1, .fset _, hr => simp [readback] at hr
  | 0, _, hr => simp [readback] at hr

theorem tlook_dictFind {fu : Nat} {h : Heap} :
    ∀ (kvs : List (V × V)) (kvs' : List (String × T)),
    kvs.mapM (fun (p : V × V) => match p.1 with
        | .str k => (readback fu h p.2).map fun t => (k, t)
        | _ => none) = some kvs' →
    ∀ (x : String) (t : T), tlook kvs' x = some t →
      ∃ v, dictFind .py kvs (.str x) = some v ∧ readback fu h v = some t
  | [], kvs', hm, x, t, ht => by
      simp at hm; subst hm; simp [tlook] at ht
  | (k, w) :: rest, kvs', hm, x, t, ht => by
      simp only [List.mapM_cons, Option.bind_eq_bind] at hm
      cases k with
      | str k =>
        simp only at hm
        cases hw : readback fu h w with
        | none => simp [hw] at hm
        | some tw =>
          rw [hw] at hm
          simp only [Option.map_some, Option.bind_some] at hm
          cases hr : rest.mapM (fun (p : V × V) => match p.1 with
              | .str k => (readback fu h p.2).map fun t => (k, t)
              | _ => none) with
          | none => simp [hr] at hm
          | some ys =>
            rw [hr] at hm
            simp only [Option.bind_some, Option.pure_def, Option.some.injEq] at hm
            subst hm
            simp only [tlook] at ht
            by_cases e : k = x
            · subst e
              simp at ht; subst ht
              exact ⟨w, by simp [dictFind, keyEq_str], hw⟩
            · simp only [e, if_false] at ht
              obtain ⟨v, h1, h2⟩ := tlook_dictFind rest ys hr x t ht
              exact ⟨v, by simp [dictFind, keyEq_str, e, h1], h2⟩
      | _ => simp at hm

theorem rb_str {fu : Nat} {h : Heap} {v : V} {s : String} (hr : readback fu h v = some (.str s)) :
    v = .str s := by
  match fu, v, hr with
  | fu' + 1, .str s', hr => simp [readback] at hr; rw [hr]
  | fu' + 1, .ref a, hr =>
    simp only [readback] at hr
    split at hr <;> simp at hr
  | fu' + 1, .tup xs, hr => simp [readback] at hr
  | fu' + 1, .none, hr => simp [readback] at hr
  | fu' + 1, .bool _, hr => simp [readback] at hr
  | fu' + 1, .int _, hr => simp [readback] at hr
  | fu' + 1, .undef, hr => simp [readback] at hr
  | fu' + 1, .fset _, hr => simp [readback] at hr
  | 0, _, hr => simp [readback] at hr

/-- A field of a read-back object. -/
theorem rb_field {fu : Nat} {h : Heap} {v : V} {kvs' : List (String × T)}
    (hr : readback fu h v = some (.obj kvs')) {x : String} {t : T} (ht : tlook kvs' x = some t) :
    ∃ fu' a kvs w, fu = fu' + 1 ∧ v = .ref a ∧ hget h a = some (.dict kvs) ∧
      dictFind .py kvs (.str x) = some w ∧ readback fu' h w = some t := by
  obtain ⟨fu', a, kvs, e1, e2, hg, hm⟩ := rb_obj hr
  obtain ⟨w, h1, h2⟩ := tlook_dictFind kvs kvs' hm x t ht
  exact ⟨fu', a, kvs, w, e1, e2, hg, h1, h2⟩

/-- **Read-back denotation gives a heap formula tree.** -/
theorem rb_FRel {D : Addrs} {h : Heap} {names : List String} {n : Nat}
    (hnm : ∀ a, a < h.length → ¬ D.mut a) :
    ∀ (f : BForm n) (fu : Nat) (v : V) (tj : T), readback fu h v = some tj → FDen names tj f →
      FRel D h names v f := by
  intro f
  induction f with
  | atom i =>
    intro fu v tj hr hd
    match tj, hd with
    | .obj kvs', ⟨hop, hsym⟩ =>
      obtain ⟨_, a, kvs, w1, -, rfl, hg, f1, r1⟩ := rb_field hr hop
      obtain ⟨_, _, _, w2, -, e2, hg2, f2, r2⟩ := rb_field hr hsym
      cases e2; rw [hg] at hg2; cases hg2
      exact ⟨hnm a (hget_lt hg), kvs, hg, by rw [f1, rb_str r1], by rw [f2, rb_str r2]⟩
  | tt =>
    intro fu v tj hr hd
    match tj, hd with
    | .obj kvs', hop =>
      obtain ⟨_, a, kvs, w1, -, rfl, hg, f1, r1⟩ := rb_field hr hop
      exact ⟨hnm a (hget_lt hg), kvs, hg, by rw [f1, rb_str r1]⟩
  | ff =>
    intro fu v tj hr hd
    match tj, hd with
    | .obj kvs', hop =>
      obtain ⟨_, a, kvs, w1, -, rfl, hg, f1, r1⟩ := rb_field hr hop
      exact ⟨hnm a (hget_lt hg), kvs, hg, by rw [f1, rb_str r1]⟩
  | not f ih =>
    intro fu v tj hr hd
    match tj, hd with
    | .obj kvs', ⟨hop, b, hb, hdb⟩ =>
      obtain ⟨_, a, kvs, w1, -, rfl, hg, f1, r1⟩ := rb_field hr hop
      obtain ⟨_, _, _, w2, -, e2, hg2, f2, r2⟩ := rb_field hr hb
      cases e2; rw [hg] at hg2; cases hg2
      exact ⟨hnm a (hget_lt hg), kvs, w2, hg, by rw [f1, rb_str r1], f2, ih _ w2 b r2 hdb⟩
  | and f g ih1 ih2 =>
    intro fu v tj hr hd
    match tj, hd with
    | .obj kvs', ⟨hop, l, r, hl, hrr, hdl, hdr⟩ =>
      obtain ⟨_, a, kvs, w1, -, rfl, hg, f1, r1⟩ := rb_field hr hop
      obtain ⟨_, _, _, w2, -, e2, hg2, f2, r2⟩ := rb_field hr hl
      obtain ⟨_, _, _, w3, -, e3, hg3, f3, r3⟩ := rb_field hr hrr
      cases e2; cases e3; rw [hg] at hg2 hg3; cases hg2; cases hg3
      exact ⟨hnm a (hget_lt hg), kvs, w2, w3, hg, by rw [f1, rb_str r1], f2, f3,
        ih1 _ w2 l r2 hdl, ih2 _ w3 r r3 hdr⟩
  | or f g ih1 ih2 =>
    intro fu v tj hr hd
    match tj, hd with
    | .obj kvs', ⟨hop, l, r, hl, hrr, hdl, hdr⟩ =>
      obtain ⟨_, a, kvs, w1, -, rfl, hg, f1, r1⟩ := rb_field hr hop
      obtain ⟨_, _, _, w2, -, e2, hg2, f2, r2⟩ := rb_field hr hl
      obtain ⟨_, _, _, w3, -, e3, hg3, f3, r3⟩ := rb_field hr hrr
      cases e2; cases e3; rw [hg] at hg2 hg3; cases hg2; cases hg3
      exact ⟨hnm a (hget_lt hg), kvs, w2, w3, hg, by rw [f1, rb_str r1], f2, f3,
        ih1 _ w2 l r2 hdl, ih2 _ w3 r r3 hdr⟩
  | imp f g ih1 ih2 =>
    intro fu v tj hr hd
    match tj, hd with
    | .obj kvs', ⟨hop, l, r, hl, hrr, hdl, hdr⟩ =>
      obtain ⟨_, a, kvs, w1, -, rfl, hg, f1, r1⟩ := rb_field hr hop
      obtain ⟨_, _, _, w2, -, e2, hg2, f2, r2⟩ := rb_field hr hl
      obtain ⟨_, _, _, w3, -, e3, hg3, f3, r3⟩ := rb_field hr hrr
      cases e2; cases e3; rw [hg] at hg2 hg3; cases hg2; cases hg3
      exact ⟨hnm a (hget_lt hg), kvs, w2, w3, hg, by rw [f1, rb_str r1], f2, f3,
        ih1 _ w2 l r2 hdl, ih2 _ w3 r r3 hdr⟩

end PCSCR.Py

namespace PCSCR.Py

open PCSCR PCSDD PCSOmega

/-! ## Read-back avoiding one address

`readbackEx R` is `readback` that refuses to visit address `R` (the result dictionary, which is
overwritten at the end of `check`); its results survive changes at `R` and appends. -/

def readbackEx (R : Nat) : Nat → Heap → V → Option T
  | 0, _, _ => none
  | n + 1, h, v => match v with
    | .none => some .null
    | .bool b => some (.bool b)
    | .int i => some (.int i)
    | .str s => some (.str s)
    | .tup xs => (xs.mapM (readbackEx R n h)).map .arr
    | .ref a => if a = R then none else match hget h a with
      | some (.list xs) => (xs.mapM (readbackEx R n h)).map .arr
      | some (.dict kvs) => (kvs.mapM fun (p : V × V) => match p.1 with
          | .str k => (readbackEx R n h p.2).map fun t => (k, t)
          | _ => none).map .obj
      | _ => none
    | _ => none

/-- `h'` agrees with `h` except possibly at `R`. -/
def StableEx (R : Nat) (h h' : Heap) : Prop :=
  h.length ≤ h'.length ∧ ∀ a, a < h.length → a ≠ R → hget h' a = hget h a

theorem StableEx.refl (R : Nat) (h : Heap) : StableEx R h h := ⟨Nat.le_refl _, fun _ _ _ => rfl⟩

theorem StableEx.trans {R : Nat} {h1 h2 h3 : Heap} (a : StableEx R h1 h2) (b : StableEx R h2 h3) :
    StableEx R h1 h3 :=
  ⟨Nat.le_trans a.1 b.1, fun x hx hr => by rw [b.2 x (Nat.lt_of_lt_of_le hx a.1) hr, a.2 x hx hr]⟩

theorem StableEx.append (R : Nat) (h : Heap) (o : Obj) : StableEx R h (h ++ [o]) :=
  ⟨by simp, fun _ ha _ => hget_append_lt o ha⟩

theorem StableEx.hset (R : Nat) (h : Heap) (o : Obj) : StableEx R h (hset h R o) :=
  ⟨by simp, fun _ _ hr => hget_hset_ne o (Ne.symm hr)⟩

/-- Generic congruence for the three read-back shapes. -/
theorem readbackEx_stable {R : Nat} {h h' : Heap} (hs : StableEx R h h') :
    ∀ (fu : Nat) (v : V) (t : T), readbackEx R fu h v = some t → readbackEx R fu h' v = some t
  | 0, _, _, hr => by simp [readbackEx] at hr
  | fu + 1, v, t, hr => by
    cases v with
    | tup xs =>
      simp only [readbackEx] at hr ⊢
      rw [Option.map_eq_some_iff] at hr
      obtain ⟨ys, hm, rfl⟩ := hr
      rw [mapM_some_congr xs ys hm (fun x _ y hy => readbackEx_stable hs fu x y hy)]; rfl
    | ref a =>
      simp only [readbackEx] at hr ⊢
      by_cases hR : a = R
      · simp [hR] at hr
      simp only [hR, if_false] at hr ⊢
      cases hg : hget h a with
      | none => simp [hg] at hr
      | some o =>
        rw [hs.2 a (hget_lt hg) hR, hg]
        rw [hg] at hr
        cases o with
        | list xs =>
          simp only at hr ⊢
          rw [Option.map_eq_some_iff] at hr
          obtain ⟨ys, hm, rfl⟩ := hr
          rw [mapM_some_congr xs ys hm (fun x _ y hy => readbackEx_stable hs fu x y hy)]; rfl
        | dict kvs =>
          simp only at hr ⊢
          rw [Option.map_eq_some_iff] at hr
          obtain ⟨ys, hm, rfl⟩ := hr
          rw [mapM_some_congr kvs ys hm (fun p _ y hy => by
            obtain ⟨p1, p2⟩ := p
            cases p1 with
            | str k =>
              simp only at hy ⊢
              cases hq : readbackEx R fu h p2 with
              | none => simp [hq] at hy
              | some q => rw [readbackEx_stable hs fu p2 q hq]; rw [hq] at hy; exact hy
            | _ => simp at hy)]
          rfl
        | inst _ _ => simp at hr
    | _ => simp [readbackEx] at hr ⊢; try exact hr

theorem readbackEx_readback {R : Nat} {h : Heap} :
    ∀ (fu : Nat) (v : V) (t : T), readbackEx R fu h v = some t → readback fu h v = some t
  | 0, _, _, hr => by simp [readbackEx] at hr
  | fu + 1, v, t, hr => by
    cases v with
    | tup xs =>
      simp only [readbackEx, readback] at hr ⊢
      rw [Option.map_eq_some_iff] at hr
      obtain ⟨ys, hm, rfl⟩ := hr
      rw [mapM_some_congr xs ys hm (fun x _ y hy => readbackEx_readback fu x y hy)]; rfl
    | ref a =>
      simp only [readbackEx, readback] at hr ⊢
      by_cases hR : a = R
      · simp [hR] at hr
      simp only [hR, if_false] at hr
      cases hg : hget h a with
      | none => simp [hg] at hr
      | some o =>
        rw [hg] at hr
        cases o with
        | list xs =>
          simp only at hr ⊢
          rw [Option.map_eq_some_iff] at hr
          obtain ⟨ys, hm, rfl⟩ := hr
          rw [mapM_some_congr xs ys hm (fun x _ y hy => readbackEx_readback fu x y hy)]; rfl
        | dict kvs =>
          simp only at hr ⊢
          rw [Option.map_eq_some_iff] at hr
          obtain ⟨ys, hm, rfl⟩ := hr
          rw [mapM_some_congr kvs ys hm (fun p _ y hy => by
            obtain ⟨p1, p2⟩ := p
            cases p1 with
            | str k =>
              simp only at hy ⊢
              cases hq : readbackEx R fu h p2 with
              | none => simp [hq] at hy
              | some q => rw [readbackEx_readback fu p2 q hq]; rw [hq] at hy; exact hy
            | _ => simp at hy)]
          rfl
        | inst _ _ => simp at hr
    | _ => simp [readbackEx, readback] at hr ⊢; try exact hr

/-- A read-back on a heap shorter than `R` never visits `R`. -/
theorem readback_readbackEx {R : Nat} {h : Heap} (hR : h.length ≤ R) :
    ∀ (fu : Nat) (v : V) (t : T), readback fu h v = some t → readbackEx R fu h v = some t
  | 0, _, _, hr => by simp [readback] at hr
  | fu + 1, v, t, hr => by
    cases v with
    | tup xs =>
      simp only [readbackEx, readback] at hr ⊢
      rw [Option.map_eq_some_iff] at hr
      obtain ⟨ys, hm, rfl⟩ := hr
      rw [mapM_some_congr xs ys hm (fun x _ y hy => readback_readbackEx hR fu x y hy)]; rfl
    | ref a =>
      simp only [readbackEx, readback] at hr ⊢
      cases hg : hget h a with
      | none => simp [hg] at hr
      | some o =>
        have ha : a ≠ R := by have := hget_lt hg; omega
        simp only [ha, if_false, hg]
        rw [hg] at hr
        cases o with
        | list xs =>
          simp only at hr ⊢
          rw [Option.map_eq_some_iff] at hr
          obtain ⟨ys, hm, rfl⟩ := hr
          rw [mapM_some_congr xs ys hm (fun x _ y hy => readback_readbackEx hR fu x y hy)]; rfl
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
              | some q => rw [readback_readbackEx hR fu p2 q hq]; rw [hq] at hy; exact hy
            | _ => simp at hy)]
          rfl
        | inst _ _ => simp at hr
    | _ => simp [readbackEx, readback] at hr ⊢; try exact hr

end PCSCR.Py
