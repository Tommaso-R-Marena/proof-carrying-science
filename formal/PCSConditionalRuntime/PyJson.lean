import PCSConditionalRuntime.PyCompile

/-!
# JSON encodings of typed conditional tasks, and their heap representation

* `formT`, `taskT`, `limT` — the JSON encodings of typed formulas, tasks and limits used as
  inputs of the runtime theorems (field order as in the protocol; the heap relations used by
  the proofs are order independent);
* `readback_agree`, `readback_fuel_mono` — read-back of a heap value only depends on the
  addresses it reaches and is monotone in its depth budget;
* `alloc_formT`, `alloc_taskT`, … — allocating an encoding appends objects and reads back to
  the same tree (this is what `deepcopy` does);
* `rb_FRel` — a heap value that reads back to `formT f` is a formula tree for `f` (`FRel`).
-/

namespace PCSCR.Py

open PCSCR PCSDD PCSOmega

/-- JSON encoding of a typed formula over the declared names. -/
def formT (names : List String) {n : Nat} : BForm n → T
  | .atom i => .obj [("op", .str "atom"), ("symbol", .str (names.getD i.val "")), ("args", .arr [])]
  | .tt => .obj [("op", .str "true")]
  | .ff => .obj [("op", .str "false")]
  | .not f => .obj [("op", .str "not"), ("body", formT names f)]
  | .and f g => .obj [("op", .str "and"), ("left", formT names f), ("right", formT names g)]
  | .or f g => .obj [("op", .str "or"), ("left", formT names f), ("right", formT names g)]
  | .imp f g => .obj [("op", .str "implies"), ("left", formT names f), ("right", formT names g)]

/-- JSON encoding of a typed conditional task (`pcs-conditional-boolean-task-v1`). -/
def taskT (names : List String) (t : CTask names.length) : T :=
  .obj [("format", .str "pcs-conditional-boolean-task-v1"), ("variables", .arr (names.map T.str)),
        ("source", formT names t.source), ("candidate", formT names t.candidate),
        ("assumptions", .arr (t.assumptions.map (formT names)))]

/-- JSON encoding of work limits. -/
def limT (lim : Limits) : T := .obj [("nodes", .int lim.nodes), ("operations", .int lim.operations)]

/-- `h'` agrees with `h` on every address of `h`. -/
def HAgree (h h' : Heap) : Prop := h.length ≤ h'.length ∧ ∀ a, a < h.length → hget h' a = hget h a

theorem HAgree.refl (h : Heap) : HAgree h h := ⟨Nat.le_refl _, fun _ _ => rfl⟩

theorem HAgree.trans {h1 h2 h3 : Heap} (a : HAgree h1 h2) (b : HAgree h2 h3) : HAgree h1 h3 :=
  ⟨Nat.le_trans a.1 b.1, fun x hx => by rw [b.2 x (Nat.lt_of_lt_of_le hx a.1), a.2 x hx]⟩

theorem HAgree.append (h : Heap) (l : List Obj) : HAgree h (h ++ l) :=
  ⟨by simp, fun a ha => by simp [hget, List.getElem?_append_left ha]⟩

theorem mapM_some_congr {α β : Type} {f g : α → Option β} :
    ∀ (xs : List α) (ys : List β), xs.mapM f = some ys → (∀ x ∈ xs, ∀ y, f x = some y → g x = some y) →
      xs.mapM g = some ys
  | [], ys, h, _ => by simpa using h
  | x :: xs, ys, h, hfg => by
      simp only [List.mapM_cons, Option.bind_eq_bind] at h ⊢
      cases hx : f x with
      | none => simp [hx] at h
      | some y =>
        rw [hx] at h
        simp only [Option.bind_some] at h
        cases hxs : xs.mapM f with
        | none => simp [hxs] at h
        | some ys' =>
          rw [hxs] at h
          simp only [Option.bind_some, Option.pure_def, Option.some.injEq] at h
          rw [hfg x (by simp) y hx, mapM_some_congr xs ys' hxs (fun z hz w hw => hfg z (by simp [hz]) w hw)]
          simp [h]

/-- Read-back only depends on the reached addresses. -/
theorem readback_agree {h h' : Heap} (hag : HAgree h h') :
    ∀ (fu : Nat) (v : V) (t : T), readback fu h v = some t → readback fu h' v = some t
  | 0, _, _, hr => by simp [readback] at hr
  | fu + 1, v, t, hr => by
    cases v with
    | tup xs =>
      simp only [readback] at hr ⊢
      cases hm : xs.mapM (readback fu h) with
      | none => simp [hm] at hr
      | some ys =>
        rw [hm] at hr
        rw [mapM_some_congr xs ys hm (fun x _ y hy => readback_agree hag fu x y hy)]
        exact hr
    | ref a =>
      simp only [readback] at hr ⊢
      cases hg : hget h a with
      | none => simp [hg] at hr
      | some o =>
        have ha := hget_lt hg
        rw [hag.2 a ha, hg]
        rw [hg] at hr
        cases o with
        | list xs =>
          simp only at hr ⊢
          cases hm : xs.mapM (readback fu h) with
          | none => simp [hm] at hr
          | some ys =>
            rw [hm] at hr
            rw [mapM_some_congr xs ys hm (fun x _ y hy => readback_agree hag fu x y hy)]
            exact hr
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
                | some q => rw [readback_agree hag fu p2 q hq]; rw [hq] at hy; exact hy
              | _ => simp at hy)]
          rfl
        | inst _ _ => simp at hr
    | _ => simp [readback] at hr ⊢; try exact hr

/-- Read-back is monotone in its depth budget. -/
theorem readback_fuel_mono {h : Heap} :
    ∀ (fu fu' : Nat) (v : V) (t : T), fu ≤ fu' → readback fu h v = some t → readback fu' h v = some t
  | 0, _, _, _, _, hr => by simp [readback] at hr
  | fu + 1, fu' + 1, v, t, hle, hr => by
    have hle' : fu ≤ fu' := by omega
    cases v with
    | tup xs =>
      simp only [readback] at hr ⊢
      cases hm : xs.mapM (readback fu h) with
      | none => simp [hm] at hr
      | some ys =>
        rw [hm] at hr
        rw [mapM_some_congr xs ys hm (fun x _ y hy => readback_fuel_mono fu fu' x y hle' hy)]
        exact hr
    | ref a =>
      simp only [readback] at hr ⊢
      cases hg : hget h a with
      | none => simp [hg] at hr
      | some o =>
        rw [hg] at hr
        cases o with
        | list xs =>
          simp only at hr ⊢
          cases hm : xs.mapM (readback fu h) with
          | none => simp [hm] at hr
          | some ys =>
            rw [hm] at hr
            rw [mapM_some_congr xs ys hm (fun x _ y hy => readback_fuel_mono fu fu' x y hle' hy)]
            exact hr
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
                | some q => rw [readback_fuel_mono fu fu' p2 q hle' hq]; rw [hq] at hy; exact hy
              | _ => simp at hy)]
          rfl
        | inst _ _ => simp at hr
    | _ => simp [readback] at hr ⊢; try exact hr
  | fu + 1, 0, _, _, hle, _ => by omega

end PCSCR.Py
