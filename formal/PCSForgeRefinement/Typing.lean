import PCSForgeRefinement.Denote

/-!
# Type safety of the repaired CertIR type checker

`WTStore env σ` — every variable typed by `env` (last binding wins, as `Env.lookup`) has a
value of that type in the denotational store.

`type_safety` — for the *patched* checker (`typeOfG true`), a well-typed expression evaluated
in a well-typed store always succeeds with a value of its type.  (The original checker
admits always-failing programs; see `PCSForgeRefinement.Counterexample`.)
-/

namespace PCSForgeRefinement

def WTStore (env : Env) (σ : DStore) : Prop :=
  ∀ x t, env.lookup x = some t → ∃ v, σ.get x = some v ∧ v.ty = t

theorem DVal.ty_bv {v : DVal} {w : Width} (h : v.ty = .bv w) : ∃ x, v = .bv w x := by
  cases v with
  | bool b => cases h
  | bv w' x => cases h; exact ⟨x, rfl⟩

theorem DVal.ty_bool {v : DVal} (h : v.ty = .bool) : ∃ b, v = .bool b := by
  cases v with
  | bool b => exact ⟨b, rfl⟩
  | bv w' x => cases h

/-- **Type safety** of the repaired checker. -/
theorem type_safety {env : Env} {σ : DStore} (hσ : WTStore env σ) :
    ∀ (e : Expr) (t : Ty), typeOfG true env e = .ok t → ∃ v, denote σ e = .ok v ∧ v.ty = t := by
  intro e
  induction e with
  | constBool b => intro t h; cases h; exact ⟨_, rfl, rfl⟩
  | constBv w v => intro t h; cases h; exact ⟨_, rfl, rfl⟩
  | var x =>
      intro t h
      simp only [typeOfG] at h
      split at h
      · rename_i t' ht; cases h
        obtain ⟨v, hv, hty⟩ := hσ x t ht
        exact ⟨v, by simp [denote, hv], hty⟩
      · cases h
  | unop op e ih =>
      intro t h
      simp only [typeOfG] at h
      cases he : typeOfG true env e with
      | error err => rw [he] at h; cases h
      | ok te =>
          rw [he] at h
          obtain ⟨v, hv, hvt⟩ := ih te he
          cases op <;> cases te <;> simp [bind, Except.bind] at h <;> subst h
          · obtain ⟨b, rfl⟩ := DVal.ty_bool hvt
            exact ⟨.bool (!b), by simp [denote, hv, bind, Except.bind], rfl⟩
          · obtain ⟨x, rfl⟩ := DVal.ty_bv hvt
            exact ⟨.bv _ (~~~x), by simp [denote, hv, bind, Except.bind], rfl⟩
          · obtain ⟨x, rfl⟩ := DVal.ty_bv hvt
            exact ⟨.bv _ (-x), by simp [denote, hv, bind, Except.bind], rfl⟩
  | binop op l r ihl ihr =>
      intro t h
      simp only [typeOfG] at h
      cases hl : typeOfG true env l with
      | error err => rw [hl] at h; cases h
      | ok tl =>
        cases hr : typeOfG true env r with
        | error err => rw [hl, hr] at h; cases h
        | ok tr =>
          rw [hl, hr] at h
          obtain ⟨vl, hvl, hvlt⟩ := ihl tl hl
          obtain ⟨vr, hvr, hvrt⟩ := ihr tr hr
          cases tl with
          | bool => simp [bind, Except.bind] at h
          | bv w1 =>
            cases tr with
            | bool => simp [bind, Except.bind] at h
            | bv w2 =>
              by_cases hw : w1 = w2
              · subst hw
                simp [bind, Except.bind] at h; subst h
                obtain ⟨a, rfl⟩ := DVal.ty_bv hvlt
                obtain ⟨b, rfl⟩ := DVal.ty_bv hvrt
                exact ⟨.bv _ (denBin op a b), by simp [denote, hvl, hvr, bind, Except.bind], rfl⟩
              · simp [bind, Except.bind, hw] at h
  | cmp op l r ihl ihr =>
      intro t h
      simp only [typeOfG] at h
      cases hl : typeOfG true env l with
      | error err => rw [hl] at h; cases h
      | ok tl =>
        cases hr : typeOfG true env r with
        | error err => rw [hl, hr] at h; cases h
        | ok tr =>
          rw [hl, hr] at h
          obtain ⟨vl, hvl, hvlt⟩ := ihl tl hl
          obtain ⟨vr, hvr, hvrt⟩ := ihr tr hr
          cases tl with
          | bool =>
            cases tr with
            | bv w => simp [bind, Except.bind] at h
            | bool =>
              obtain ⟨a, rfl⟩ := DVal.ty_bool hvlt
              obtain ⟨b, rfl⟩ := DVal.ty_bool hvrt
              cases op <;> simp [bind, Except.bind] at h <;> subst h
              · exact ⟨.bool (a == b), by simp [denote, hvl, hvr, bind, Except.bind], rfl⟩
              · exact ⟨.bool (a != b), by simp [denote, hvl, hvr, bind, Except.bind], rfl⟩
          | bv w1 =>
            cases tr with
            | bool => simp [bind, Except.bind] at h
            | bv w2 =>
              by_cases hw : w1 = w2
              · subst hw
                simp [bind, Except.bind] at h; subst h
                obtain ⟨a, rfl⟩ := DVal.ty_bv hvlt
                obtain ⟨b, rfl⟩ := DVal.ty_bv hvrt
                exact ⟨.bool (denCmp op a b), by simp [denote, hvl, hvr, bind, Except.bind], rfl⟩
              · simp [bind, Except.bind, hw] at h
  | select c a b ihc iha ihb =>
      intro t h
      simp only [typeOfG] at h
      cases hc : typeOfG true env c with
      | error err => rw [hc] at h; cases h
      | ok tc =>
        rw [hc] at h
        by_cases htc : tc = .bool
        · subst htc
          cases ha : typeOfG true env a with
          | error err => simp [ha, bind, Except.bind] at h
          | ok ta =>
            cases hb : typeOfG true env b with
            | error err => simp [ha, hb, bind, Except.bind] at h
            | ok tb =>
              by_cases hab : ta = tb
              · subst hab
                simp [ha, hb, bind, Except.bind] at h; subst h
                obtain ⟨vc, hvc, hvct⟩ := ihc .bool hc
                obtain ⟨cb, rfl⟩ := DVal.ty_bool hvct
                obtain ⟨va, hva, hvat⟩ := iha ta ha
                obtain ⟨vb, hvb, hvbt⟩ := ihb ta hb
                cases cb
                · exact ⟨vb, by simp [denote, hvc, hvb, bind, Except.bind], hvbt⟩
                · exact ⟨va, by simp [denote, hvc, hva, bind, Except.bind], hvat⟩
              · simp [ha, hb, hab, bind, Except.bind] at h
        · simp [htc, bind, Except.bind] at h

/-- Typing results of subexpressions (inversion). -/
theorem typeOf_binop_inv {p : Bool} {env : Env} {op : BinOp} {l r : Expr} {t : Ty}
    (h : typeOfG p env (.binop op l r) = .ok t) :
    (∃ tl, typeOfG p env l = .ok tl) ∧ (∃ tr, typeOfG p env r = .ok tr) := by
  simp only [typeOfG] at h
  cases hl : typeOfG p env l with
  | error e => rw [hl] at h; cases h
  | ok tl =>
    cases hr : typeOfG p env r with
    | error e => rw [hl, hr] at h; cases h
    | ok tr => exact ⟨⟨tl, rfl⟩, ⟨tr, rfl⟩⟩

theorem typeOf_cmp_inv {p : Bool} {env : Env} {op : CmpOp} {l r : Expr} {t : Ty}
    (h : typeOfG p env (.cmp op l r) = .ok t) :
    (∃ tl, typeOfG p env l = .ok tl) ∧ (∃ tr, typeOfG p env r = .ok tr) := by
  simp only [typeOfG] at h
  cases hl : typeOfG p env l with
  | error e => rw [hl] at h; cases h
  | ok tl =>
    cases hr : typeOfG p env r with
    | error e => rw [hl, hr] at h; cases h
    | ok tr => exact ⟨⟨tl, rfl⟩, ⟨tr, rfl⟩⟩

theorem typeOf_unop_inv {p : Bool} {env : Env} {op : UnOp} {e : Expr} {t : Ty}
    (h : typeOfG p env (.unop op e) = .ok t) : ∃ te, typeOfG p env e = .ok te := by
  simp only [typeOfG] at h
  cases he : typeOfG p env e with
  | error err => rw [he] at h; cases h
  | ok te => exact ⟨te, rfl⟩

theorem typeOf_select_inv {p : Bool} {env : Env} {c a b : Expr} {t : Ty}
    (h : typeOfG p env (.select c a b) = .ok t) :
    (∃ tc, typeOfG p env c = .ok tc) ∧ (∃ ta, typeOfG p env a = .ok ta) ∧
      (∃ tb, typeOfG p env b = .ok tb) := by
  simp only [typeOfG] at h
  cases hc : typeOfG p env c with
  | error err => rw [hc] at h; cases h
  | ok tc =>
    rw [hc] at h
    by_cases htc : tc = .bool
    · subst htc
      cases ha : typeOfG p env a with
      | error err => simp [ha, bind, Except.bind] at h
      | ok ta =>
        cases hb : typeOfG p env b with
        | error err => simp [ha, hb, bind, Except.bind] at h
        | ok tb => exact ⟨⟨_, rfl⟩, ⟨_, rfl⟩, ⟨_, rfl⟩⟩
    · simp [htc, bind, Except.bind] at h

end PCSForgeRefinement
