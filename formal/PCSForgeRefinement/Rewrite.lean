import PCSForgeRefinement.Typing

/-!
# Proof-carrying rewrite certificates for CertIR

* `Rule` — the sound rewrite schemas of `forgeopt-search::rewrite_expr`
  (`add_self_to_shl1`, `and_xor_add_to_or`, `add_commute`, `or_commute`, `or_idempotent`,
  `and_idempotent`, `and_zero`, `xor_self`).  The intentionally unsound proposals
  (`UNSOUND_*`) have no schema: a certificate can only cite admitted schemas, and the checker
  recomputes every rewritten expression.
* `rewriteAt` — context replacement along a path (congruence).
* `Cert` binds the exact original and candidate programs, the semantic version and the
  rewrite-library identifier; `checkCert` is the small independent checker.

Principal theorems:

* `rule_sound` — every admitted schema preserves typing and denotation in every well-typed
  store (universally, all widths);
* `rewriteAt_sound` — congruence/context replacement;
* `rewrite_certificate_universally_sound` — every accepted certificate yields universal
  denotational equivalence of the bodies;
* `optimization_sequence_preserves_program` — and identical Rust-interpreter results on every
  canonical input vector (the actual transcribed `eval`, all widths `u8 … u64`);
* `verified_static_cost_improvement` — cost never increases along a certificate, and strictly
  decreases when a reducing schema is used; `checkCertImproving` enforces strict improvement;
* `counterexample_certificate_sound` — an accepted counterexample certificate is a genuine
  distinguishing input of the actual interpreter.
-/

namespace PCSForgeRefinement

inductive Rule where
  | addSelfShl1 | andXorAddToOr | addComm | orComm | orIdem | andIdem | andZero | xorSelf
  deriving DecidableEq, Repr

/-- Root application of a schema (side conditions use the repaired checker). -/
def Rule.apply (env : Env) : Rule → Expr → Option Expr
  | .addSelfShl1, .binop .add x y =>
    if x = y then
      match typeOfG true env x with
      | .ok (.bv w) => some (.binop .shl x (.constBv w 1))
      | _ => none
    else none
  | .andXorAddToOr, .binop .add (.binop .and a1 b1) (.binop .xor a2 b2) =>
    if a1 = a2 ∧ b1 = b2 then some (.binop .or a1 b1) else none
  | .addComm, .binop .add x y => some (.binop .add y x)
  | .orComm, .binop .or x y => some (.binop .or y x)
  | .orIdem, .binop .or x y => if x = y then some x else none
  | .andIdem, .binop .and x y => if x = y then some x else none
  | .andZero, .binop .and _ (.constBv w 0) => some (.constBv w 0)
  | .xorSelf, .binop .xor x y =>
    if x = y then
      match typeOfG true env x with
      | .ok (.bv w) => some (.constBv w 0)
      | _ => none
    else none
  | _, _ => none

/-- Typing- and meaning-preserving replacement (in every well-typed store). -/
def TEq (env : Env) (e e' : Expr) : Prop :=
  ∀ t, typeOfG true env e = .ok t →
    typeOfG true env e' = .ok t ∧ ∀ σ, WTStore env σ → denote σ e' = denote σ e

theorem denote_binop_bv {σ : DStore} {op : BinOp} {l r : Expr} {w : Width} {a b : BitVec w.bits}
    (hl : denote σ l = .ok (.bv w a)) (hr : denote σ r = .ok (.bv w b)) :
    denote σ (.binop op l r) = .ok (.bv w (denBin op a b)) := by
  simp [denote, hl, hr, bind, Except.bind]

theorem typed_bv {env : Env} {σ : DStore} (hσ : WTStore env σ) {e : Expr} {w : Width}
    (h : typeOfG true env e = .ok (.bv w)) : ∃ a, denote σ e = .ok (.bv w a) := by
  obtain ⟨v, hv, ht⟩ := type_safety hσ e _ h
  obtain ⟨a, rfl⟩ := DVal.ty_bv ht
  exact ⟨a, hv⟩

theorem typeOf_binop_bv {env : Env} {op : BinOp} {l r : Expr} {t : Ty}
    (h : typeOfG true env (.binop op l r) = .ok t) :
    ∃ w, t = .bv w ∧ typeOfG true env l = .ok (.bv w) ∧ typeOfG true env r = .ok (.bv w) := by
  simp only [typeOfG] at h
  cases hl : typeOfG true env l with
  | error e => rw [hl] at h; cases h
  | ok tl =>
    cases hr : typeOfG true env r with
    | error e => rw [hl, hr] at h; cases h
    | ok tr =>
      rw [hl, hr] at h
      cases tl with
      | bool => simp [bind, Except.bind] at h
      | bv w1 =>
        cases tr with
        | bool => simp [bind, Except.bind] at h
        | bv w2 =>
          by_cases hw : w1 = w2
          · subst hw; simp [bind, Except.bind] at h; exact ⟨w1, h.symm, rfl, rfl⟩
          · simp [bind, Except.bind, hw] at h

theorem typeOf_binop_of {env : Env} {op : BinOp} {l r : Expr} {w : Width}
    (hl : typeOfG true env l = .ok (.bv w)) (hr : typeOfG true env r = .ok (.bv w)) :
    typeOfG true env (.binop op l r) = .ok (.bv w) := by
  simp [typeOfG, hl, hr, bind, Except.bind]

theorem ofNat_one_toNat (w : Width) : (BitVec.ofNat w.bits 1).toNat = 1 := by
  cases w <;> decide

/-- **Every admitted schema is universally sound.** -/
theorem rule_sound (env : Env) (r : Rule) {e e' : Expr} (h : r.apply env e = some e') : TEq env e e' := by
  intro t ht
  cases r with
  | addSelfShl1 =>
      match e, h with
      | .binop .add x y, h =>
        simp only [Rule.apply] at h
        split at h
        · rename_i hxy; subst hxy
          split at h
          · rename_i w hx
            cases h
            obtain ⟨w', rfl, hx', _⟩ := typeOf_binop_bv ht
            rw [hx] at hx'; cases hx'
            refine ⟨typeOf_binop_of hx rfl, fun σ hσ => ?_⟩
            obtain ⟨a, ha⟩ := typed_bv hσ hx
            rw [denote_binop_bv ha ha, denote_binop_bv (b := BitVec.ofNat w.bits 1) ha rfl]
            congr 2
            apply BitVec.eq_of_toNat_eq
            simp only [denBin, BitVec.toNat_shiftLeft, BitVec.toNat_add, ofNat_one_toNat,
              Nat.shiftLeft_eq, Nat.pow_one, Nat.mul_two]
          · cases h
        · cases h
  | andXorAddToOr =>
      match e, h with
      | .binop .add (.binop .and a1 b1) (.binop .xor a2 b2), h =>
        simp only [Rule.apply] at h
        split at h
        · rename_i hab; obtain ⟨rfl, rfl⟩ := hab
          cases h
          obtain ⟨w, rfl, hand, _⟩ := typeOf_binop_bv ht
          obtain ⟨w', hw', ha, hb⟩ := typeOf_binop_bv hand
          cases hw'
          refine ⟨typeOf_binop_of ha hb, fun σ hσ => ?_⟩
          obtain ⟨x, hx⟩ := typed_bv hσ ha
          obtain ⟨y, hy⟩ := typed_bv hσ hb
          rw [denote_binop_bv hx hy, denote_binop_bv (denote_binop_bv (op := .and) hx hy)
            (denote_binop_bv (op := .xor) hx hy)]
          congr 2
          simp only [denBin]
          rw [BitVec.add_eq_or_of_and_eq_zero]
          · ext i; simp; cases x[i] <;> cases y[i] <;> simp
          · ext i; simp; cases x[i] <;> cases y[i] <;> simp
        · cases h
  | addComm =>
      match e, h with
      | .binop .add x y, h =>
        simp only [Rule.apply] at h; cases h
        obtain ⟨w, rfl, hx, hy⟩ := typeOf_binop_bv ht
        refine ⟨typeOf_binop_of hy hx, fun σ hσ => ?_⟩
        obtain ⟨a, ha⟩ := typed_bv hσ hx
        obtain ⟨b, hb⟩ := typed_bv hσ hy
        rw [denote_binop_bv hb ha, denote_binop_bv ha hb]
        simp only [denBin, BitVec.add_comm]
  | orComm =>
      match e, h with
      | .binop .or x y, h =>
        simp only [Rule.apply] at h; cases h
        obtain ⟨w, rfl, hx, hy⟩ := typeOf_binop_bv ht
        refine ⟨typeOf_binop_of hy hx, fun σ hσ => ?_⟩
        obtain ⟨a, ha⟩ := typed_bv hσ hx
        obtain ⟨b, hb⟩ := typed_bv hσ hy
        rw [denote_binop_bv hb ha, denote_binop_bv ha hb]
        simp only [denBin, BitVec.or_comm]
  | orIdem =>
      match e, h with
      | .binop .or x y, h =>
        simp only [Rule.apply] at h
        split at h
        · rename_i hxy; subst hxy; cases h
          obtain ⟨w, rfl, hx, _⟩ := typeOf_binop_bv ht
          refine ⟨hx, fun σ hσ => ?_⟩
          obtain ⟨a, ha⟩ := typed_bv hσ hx
          rw [denote_binop_bv ha ha, ha]; simp [denBin]
        · cases h
  | andIdem =>
      match e, h with
      | .binop .and x y, h =>
        simp only [Rule.apply] at h
        split at h
        · rename_i hxy; subst hxy; cases h
          obtain ⟨w, rfl, hx, _⟩ := typeOf_binop_bv ht
          refine ⟨hx, fun σ hσ => ?_⟩
          obtain ⟨a, ha⟩ := typed_bv hσ hx
          rw [denote_binop_bv ha ha, ha]; simp [denBin]
        · cases h
  | andZero =>
      match e, h with
      | .binop .and x (.constBv w 0), h =>
        simp only [Rule.apply] at h; cases h
        obtain ⟨w', rfl, hx, hz⟩ := typeOf_binop_bv ht
        simp only [typeOfG] at hz; cases hz
        refine ⟨rfl, fun σ hσ => ?_⟩
        obtain ⟨a, ha⟩ := typed_bv hσ hx
        rw [denote_binop_bv (b := BitVec.ofNat w.bits 0) ha rfl]
        simp [denote, denBin]
  | xorSelf =>
      match e, h with
      | .binop .xor x y, h =>
        simp only [Rule.apply] at h
        split at h
        · rename_i hxy; subst hxy
          split at h
          · rename_i w hx
            cases h
            obtain ⟨w', rfl, hx', _⟩ := typeOf_binop_bv ht
            rw [hx] at hx'; cases hx'
            refine ⟨rfl, fun σ hσ => ?_⟩
            obtain ⟨a, ha⟩ := typed_bv hσ hx
            rw [denote_binop_bv ha ha]
            simp [denote, denBin]
          · cases h
        · cases h

/-! ## Context replacement -/

inductive Dir where
  | arg | lhs | rhs | cond | thn | els
  deriving DecidableEq, Repr

def rewriteAt (env : Env) (r : Rule) : List Dir → Expr → Option Expr
  | [], e => r.apply env e
  | .arg :: p, .unop op e => (rewriteAt env r p e).map (.unop op ·)
  | .lhs :: p, .binop op l x => (rewriteAt env r p l).map (.binop op · x)
  | .rhs :: p, .binop op x l => (rewriteAt env r p l).map (.binop op x ·)
  | .lhs :: p, .cmp op l x => (rewriteAt env r p l).map (.cmp op · x)
  | .rhs :: p, .cmp op x l => (rewriteAt env r p l).map (.cmp op x ·)
  | .cond :: p, .select c a b => (rewriteAt env r p c).map (.select · a b)
  | .thn :: p, .select c a b => (rewriteAt env r p a).map (.select c · b)
  | .els :: p, .select c a b => (rewriteAt env r p b).map (.select c a ·)
  | _, _ => none

theorem TEq.unop {env : Env} {op : UnOp} {e e' : Expr} (h : TEq env e e') :
    TEq env (.unop op e) (.unop op e') := by
  intro t ht
  obtain ⟨te, hte⟩ := typeOf_unop_inv ht
  obtain ⟨h1, h2⟩ := h te hte
  refine ⟨by simp only [typeOfG, h1] at ht ⊢; simpa [hte] using ht, fun σ hσ => ?_⟩
  simp only [denote, h2 σ hσ]

theorem TEq.binopL {env : Env} {op : BinOp} {l l' x : Expr} (h : TEq env l l') :
    TEq env (.binop op l x) (.binop op l' x) := by
  intro t ht
  obtain ⟨⟨tl, htl⟩, _⟩ := typeOf_binop_inv ht
  obtain ⟨h1, h2⟩ := h tl htl
  refine ⟨by simp only [typeOfG, h1] at ht ⊢; simpa [htl] using ht, fun σ hσ => ?_⟩
  simp only [denote, h2 σ hσ]

theorem TEq.binopR {env : Env} {op : BinOp} {l l' x : Expr} (h : TEq env l l') :
    TEq env (.binop op x l) (.binop op x l') := by
  intro t ht
  obtain ⟨_, ⟨tl, htl⟩⟩ := typeOf_binop_inv ht
  obtain ⟨h1, h2⟩ := h tl htl
  refine ⟨by simp only [typeOfG, h1] at ht ⊢; simpa [htl] using ht, fun σ hσ => ?_⟩
  simp only [denote, h2 σ hσ]

theorem TEq.cmpL {env : Env} {op : CmpOp} {l l' x : Expr} (h : TEq env l l') :
    TEq env (.cmp op l x) (.cmp op l' x) := by
  intro t ht
  obtain ⟨⟨tl, htl⟩, _⟩ := typeOf_cmp_inv ht
  obtain ⟨h1, h2⟩ := h tl htl
  refine ⟨by simp only [typeOfG, h1] at ht ⊢; simpa [htl] using ht, fun σ hσ => ?_⟩
  simp only [denote, h2 σ hσ]

theorem TEq.cmpR {env : Env} {op : CmpOp} {l l' x : Expr} (h : TEq env l l') :
    TEq env (.cmp op x l) (.cmp op x l') := by
  intro t ht
  obtain ⟨_, ⟨tl, htl⟩⟩ := typeOf_cmp_inv ht
  obtain ⟨h1, h2⟩ := h tl htl
  refine ⟨by simp only [typeOfG, h1] at ht ⊢; simpa [htl] using ht, fun σ hσ => ?_⟩
  simp only [denote, h2 σ hσ]

theorem TEq.selC {env : Env} {c c' a b : Expr} (h : TEq env c c') :
    TEq env (.select c a b) (.select c' a b) := by
  intro t ht
  obtain ⟨⟨tc, htc⟩, _, _⟩ := typeOf_select_inv ht
  obtain ⟨h1, h2⟩ := h tc htc
  refine ⟨by simp only [typeOfG, h1] at ht ⊢; simpa [htc] using ht, fun σ hσ => ?_⟩
  simp only [denote, h2 σ hσ]

theorem TEq.selT {env : Env} {c a a' b : Expr} (h : TEq env a a') :
    TEq env (.select c a b) (.select c a' b) := by
  intro t ht
  obtain ⟨_, ⟨ta, hta⟩, _⟩ := typeOf_select_inv ht
  obtain ⟨h1, h2⟩ := h ta hta
  refine ⟨by simp only [typeOfG, h1] at ht ⊢; simpa [hta] using ht, fun σ hσ => ?_⟩
  simp only [denote, h2 σ hσ]

theorem TEq.selE {env : Env} {c a b b' : Expr} (h : TEq env b b') :
    TEq env (.select c a b) (.select c a b') := by
  intro t ht
  obtain ⟨_, _, ⟨tb, htb⟩⟩ := typeOf_select_inv ht
  obtain ⟨h1, h2⟩ := h tb htb
  refine ⟨by simp only [typeOfG, h1] at ht ⊢; simpa [htb] using ht, fun σ hσ => ?_⟩
  simp only [denote, h2 σ hσ]

/-- **Congruence / context replacement soundness.** -/
theorem rewriteAt_sound (env : Env) (r : Rule) :
    ∀ (p : List Dir) (e e' : Expr), rewriteAt env r p e = some e' → TEq env e e'
  | [], e, e', h => rule_sound env r h
  | .arg :: p, .unop op e, e', h => by
      simp only [rewriteAt, Option.map_eq_some_iff] at h
      obtain ⟨x, hx, rfl⟩ := h; exact (rewriteAt_sound env r p e x hx).unop
  | .lhs :: p, .binop op l y, e', h => by
      simp only [rewriteAt, Option.map_eq_some_iff] at h
      obtain ⟨x, hx, rfl⟩ := h; exact (rewriteAt_sound env r p l x hx).binopL
  | .rhs :: p, .binop op y l, e', h => by
      simp only [rewriteAt, Option.map_eq_some_iff] at h
      obtain ⟨x, hx, rfl⟩ := h; exact (rewriteAt_sound env r p l x hx).binopR
  | .lhs :: p, .cmp op l y, e', h => by
      simp only [rewriteAt, Option.map_eq_some_iff] at h
      obtain ⟨x, hx, rfl⟩ := h; exact (rewriteAt_sound env r p l x hx).cmpL
  | .rhs :: p, .cmp op y l, e', h => by
      simp only [rewriteAt, Option.map_eq_some_iff] at h
      obtain ⟨x, hx, rfl⟩ := h; exact (rewriteAt_sound env r p l x hx).cmpR
  | .cond :: p, .select c a b, e', h => by
      simp only [rewriteAt, Option.map_eq_some_iff] at h
      obtain ⟨x, hx, rfl⟩ := h; exact (rewriteAt_sound env r p c x hx).selC
  | .thn :: p, .select c a b, e', h => by
      simp only [rewriteAt, Option.map_eq_some_iff] at h
      obtain ⟨x, hx, rfl⟩ := h; exact (rewriteAt_sound env r p a x hx).selT
  | .els :: p, .select c a b, e', h => by
      simp only [rewriteAt, Option.map_eq_some_iff] at h
      obtain ⟨x, hx, rfl⟩ := h; exact (rewriteAt_sound env r p b x hx).selE
  | .arg :: _, .constBool _, _, h | .arg :: _, .constBv _ _, _, h | .arg :: _, .var _, _, h
  | .arg :: _, .binop .., _, h | .arg :: _, .cmp .., _, h | .arg :: _, .select .., _, h
  | .lhs :: _, .constBool _, _, h | .lhs :: _, .constBv _ _, _, h | .lhs :: _, .var _, _, h
  | .lhs :: _, .unop .., _, h | .lhs :: _, .select .., _, h
  | .rhs :: _, .constBool _, _, h | .rhs :: _, .constBv _ _, _, h | .rhs :: _, .var _, _, h
  | .rhs :: _, .unop .., _, h | .rhs :: _, .select .., _, h
  | .cond :: _, .constBool _, _, h | .cond :: _, .constBv _ _, _, h | .cond :: _, .var _, _, h
  | .cond :: _, .unop .., _, h | .cond :: _, .binop .., _, h | .cond :: _, .cmp .., _, h
  | .thn :: _, .constBool _, _, h | .thn :: _, .constBv _ _, _, h | .thn :: _, .var _, _, h
  | .thn :: _, .unop .., _, h | .thn :: _, .binop .., _, h | .thn :: _, .cmp .., _, h
  | .els :: _, .constBool _, _, h | .els :: _, .constBv _ _, _, h | .els :: _, .var _, _, h
  | .els :: _, .unop .., _, h | .els :: _, .binop .., _, h | .els :: _, .cmp .., _, h => by
      simp [rewriteAt] at h

theorem TEq.trans {env : Env} {a b c : Expr} (h1 : TEq env a b) (h2 : TEq env b c) : TEq env a c := by
  intro t ht
  obtain ⟨hb, eb⟩ := h1 t ht
  obtain ⟨hc, ec⟩ := h2 t hb
  exact ⟨hc, fun σ hσ => by rw [ec σ hσ, eb σ hσ]⟩

theorem TEq.refl (env : Env) (e : Expr) : TEq env e e := fun _ ht => ⟨ht, fun _ _ => rfl⟩

/-! ## Certificates -/

structure Step where
  rule : Rule
  path : List Dir
  deriving DecidableEq, Repr

def applySteps (env : Env) : List Step → Expr → Option Expr
  | [], e => some e
  | s :: ss, e => (rewriteAt env s.rule s.path e).bind (applySteps env ss)

/-- **Composition of multi-step optimisation.** -/
theorem applySteps_sound (env : Env) :
    ∀ (ss : List Step) (e e' : Expr), applySteps env ss e = some e' → TEq env e e'
  | [], e, e', h => by cases h; exact TEq.refl env e
  | s :: ss, e, e', h => by
      simp only [applySteps, Option.bind_eq_some_iff] at h
      obtain ⟨x, hx, hrest⟩ := h
      exact (rewriteAt_sound env s.rule s.path e x hx).trans (applySteps_sound env ss x e' hrest)

def SEMANTICS : String := "certir-rust-interpreter/1"
def LIBRARY : String := "forgeopt-sound-schemas/1"

/-- A proof-carrying optimisation certificate. -/
structure Cert where
  original : Program
  candidate : Program
  steps : List Step
  semantics : String
  library : String
  deriving DecidableEq, Repr

def okB {ε α : Type} : Except ε α → Bool
  | .ok _ => true
  | .error _ => false

/-- **The independent certificate checker.** -/
def checkCert (c : Cert) : Bool :=
  (c.semantics == SEMANTICS) && (c.library == LIBRARY) && okB (c.original.checkG true) &&
    (c.candidate.params == c.original.params) && (c.candidate.retTy == c.original.retTy) &&
    (applySteps c.original.env c.steps c.original.body == some c.candidate.body)

theorem checkCert_spec {c : Cert} (h : checkCert c = true) :
    c.semantics = SEMANTICS ∧ c.library = LIBRARY ∧
    (∃ t, typeOfG true c.original.env c.original.body = .ok t ∧ t = c.original.retTy) ∧
    c.candidate.params = c.original.params ∧ c.candidate.retTy = c.original.retTy ∧
    applySteps c.original.env c.steps c.original.body = some c.candidate.body := by
  simp only [checkCert, Bool.and_eq_true, beq_iff_eq] at h
  obtain ⟨⟨⟨⟨⟨hs, hl⟩, hc⟩, hp⟩, hr⟩, ha⟩ := h
  refine ⟨hs, hl, ?_, hp, hr, ha⟩
  unfold Program.checkG at hc
  split at hc
  · simp [okB] at hc
  · split at hc
    · simp [okB] at hc
    · rename_i t ht
      split at hc
      · simp [okB] at hc
      · rename_i hrt; exact ⟨t, ht, Classical.byContradiction hrt⟩

/-- **Universal soundness of accepted certificates** (denotational, all well-typed stores,
all widths). -/
theorem rewrite_certificate_universally_sound {c : Cert} (h : checkCert c = true) :
    typeOfG true c.original.env c.candidate.body = typeOfG true c.original.env c.original.body ∧
    ∀ σ, WTStore c.original.env σ → denote σ c.candidate.body = denote σ c.original.body := by
  obtain ⟨_, _, ⟨t, ht, _⟩, _, _, ha⟩ := checkCert_spec h
  obtain ⟨h1, h2⟩ := applySteps_sound _ _ _ _ ha t ht
  exact ⟨by rw [h1, ht], h2⟩

/-! ## Program-level correspondence for the actual interpreter -/

/-- Canonical interpreter values (what `Value::bitvec` constructs). -/
def Value.WF : Value → Prop
  | .bool _ => True
  | .bitvec w bits => bits < 2 ^ w.bits

instance (v : Value) : Decidable v.WF := by
  cases v <;> unfold Value.WF <;> exact inferInstance

def Value.decode : Value → DVal
  | .bool b => .bool b
  | .bitvec w bits => .bv w (BitVec.ofNat w.bits bits)

theorem Value.enc_decode {v : Value} (h : v.WF) : v.decode.enc = v := by
  cases v with
  | bool b => rfl
  | bitvec w bits =>
      simp only [Value.decode, DVal.enc, BitVec.toNat_ofNat]
      simp only [Value.WF] at h
      rw [Nat.mod_eq_of_lt h]

theorem Value.ty_decode (v : Value) : v.decode.ty = v.ty := by cases v <;> rfl

/-- Store agreement with a reversed typing environment. -/
def Agree (envRev : Env) (δ : DStore) : Prop :=
  ∀ x, (envRev.find? (·.1 == x)).map (·.2) = (δ.get x).map DVal.ty

theorem bindInputs_spec :
    ∀ (ps : List Param) (vs : List Value) (envRev : Env) (δ : DStore) (σ : Store),
      vs.length = ps.length → (∀ v ∈ vs, v.WF) → Agree envRev δ →
      bindInputs ps vs (encStore δ) = .ok σ →
      ∃ δ', σ = encStore δ' ∧ Agree ((ps.map (fun q => (q.name, q.ty))).reverse ++ envRev) δ'
  | [], [], envRev, δ, σ, _, _, hA, h => by
      simp only [bindInputs] at h; cases h; exact ⟨δ, rfl, by simpa using hA⟩
  | p :: ps, v :: vs, envRev, δ, σ, hlen, hwf, hA, h => by
      simp only [bindInputs] at h
      split at h
      · cases h
      · rename_i hty
        have hty' : p.ty = v.ty := Classical.byContradiction hty
        have hstore : ((p.name, v) :: encStore δ : Store) = encStore ((p.name, v.decode) :: δ) := by
          simp [encStore, Value.enc_decode (hwf v (by simp))]
        rw [hstore] at h
        have hA' : Agree ((p.name, p.ty) :: envRev) ((p.name, v.decode) :: δ) := by
          intro x
          simp only [List.find?_cons, DStore.get]
          by_cases hx : (p.name == x) = true
          · simp [hx, Value.ty_decode, hty']
          · simp only [hx]; exact hA x
        obtain ⟨δ', h1, h2⟩ := bindInputs_spec ps vs _ _ σ (by simpa using hlen)
          (fun u hu => hwf u (by simp [hu])) hA' h
        refine ⟨δ', h1, ?_⟩
        simpa using h2
  | [], _ :: _, _, _, _, hlen, _, _, _ => by simp at hlen
  | _ :: _, [], _, _, _, hlen, _, _, _ => by simp at hlen

theorem agree_wt {ps : List Param} {δ : DStore}
    (h : Agree ((ps.map (fun q => (q.name, q.ty))).reverse ++ []) δ) :
    WTStore (ps.map (fun q => (q.name, q.ty))) δ := by
  intro x t hx
  have := h x
  simp only [List.append_nil] at this
  unfold Env.lookup at hx
  rw [hx] at this
  cases hg : δ.get x with
  | none => rw [hg] at this; cases this
  | some v => rw [hg] at this; cases this; exact ⟨v, rfl, rfl⟩

/-- **Actual-interpreter equivalence** of an accepted certificate on every canonical input
vector (and identical errors on every arity/type-mismatched input). -/
theorem optimization_sequence_preserves_program {c : Cert} (h : checkCert c = true)
    (inputs : List Value) (hwf : ∀ v ∈ inputs, v.WF) :
    eval c.candidate inputs = eval c.original inputs := by
  obtain ⟨_, _, _, hp, hr, _⟩ := checkCert_spec h
  obtain ⟨_, hden⟩ := rewrite_certificate_universally_sound h
  unfold eval
  rw [hp, hr]
  split
  · rfl
  · rename_i hlen
    have hlen' : inputs.length = c.original.params.length := Classical.byContradiction hlen
    cases hb : bindInputs c.original.params inputs [] with
    | error e => rfl
    | ok σ =>
        have hA0 : Agree [] ([] : DStore) := fun x => rfl
        obtain ⟨δ, rfl, hA⟩ := bindInputs_spec c.original.params inputs [] [] σ hlen' hwf hA0
          (by simpa [encStore] using hb)
        have hwt : WTStore c.original.env δ := agree_wt hA
        simp only [certir_eval_correspondence, hden δ hwt]

/-- Static cost of a root schema application never increases; reducing schemas decrease it. -/
def Rule.reducing : Rule → Bool
  | .addComm | .orComm => false
  | _ => true

theorem rule_cost {env : Env} {r : Rule} {e e' : Expr} (h : r.apply env e = some e') :
    exprCost e' ≤ exprCost e ∧ (r.reducing = true → exprCost e' < exprCost e) := by
  cases r with
  | addSelfShl1 =>
      match e, h with
      | .binop .add x y, h =>
        simp only [Rule.apply] at h
        split at h
        · rename_i hxy; subst hxy
          split at h
          · cases h; simp [exprCost, opWeight, Rule.reducing]; omega
          · cases h
        · cases h
  | andXorAddToOr =>
      match e, h with
      | .binop .add (.binop .and a1 b1) (.binop .xor a2 b2), h =>
        simp only [Rule.apply] at h
        split at h
        · rename_i hab; obtain ⟨rfl, rfl⟩ := hab
          cases h; simp [exprCost, opWeight, Rule.reducing]; omega
        · cases h
  | addComm =>
      match e, h with
      | .binop .add x y, h =>
        simp only [Rule.apply] at h; cases h; simp [exprCost, Rule.reducing]; omega
  | orComm =>
      match e, h with
      | .binop .or x y, h =>
        simp only [Rule.apply] at h; cases h; simp [exprCost, Rule.reducing]; omega
  | orIdem =>
      match e, h with
      | .binop .or x y, h =>
        simp only [Rule.apply] at h
        split at h
        · rename_i hxy; subst hxy; cases h; simp [exprCost, opWeight, Rule.reducing]; omega
        · cases h
  | andIdem =>
      match e, h with
      | .binop .and x y, h =>
        simp only [Rule.apply] at h
        split at h
        · rename_i hxy; subst hxy; cases h; simp [exprCost, opWeight, Rule.reducing]; omega
        · cases h
  | andZero =>
      match e, h with
      | .binop .and x (.constBv w 0), h =>
        simp only [Rule.apply] at h; cases h; simp [exprCost, opWeight, Rule.reducing]; omega
  | xorSelf =>
      match e, h with
      | .binop .xor x y, h =>
        simp only [Rule.apply] at h
        split at h
        · rename_i hxy; subst hxy
          split at h
          · cases h; simp [exprCost, opWeight, Rule.reducing]; omega
          · cases h
        · cases h

theorem rewriteAt_cost (env : Env) (r : Rule) :
    ∀ (p : List Dir) (e e' : Expr), rewriteAt env r p e = some e' →
      exprCost e' ≤ exprCost e ∧ (r.reducing = true → exprCost e' < exprCost e)
  | [], e, e', h => rule_cost h
  | .arg :: p, .unop op e, e', h => by
      simp only [rewriteAt, Option.map_eq_some_iff] at h
      obtain ⟨x, hx, rfl⟩ := h
      obtain ⟨h1, h2⟩ := rewriteAt_cost env r p e x hx
      exact ⟨by simp only [exprCost]; omega, fun hr => by have := h2 hr; simp only [exprCost]; omega⟩
  | .lhs :: p, .binop op l y, e', h => by
      simp only [rewriteAt, Option.map_eq_some_iff] at h
      obtain ⟨x, hx, rfl⟩ := h
      obtain ⟨h1, h2⟩ := rewriteAt_cost env r p l x hx
      exact ⟨by simp only [exprCost]; omega, fun hr => by have := h2 hr; simp only [exprCost]; omega⟩
  | .rhs :: p, .binop op y l, e', h => by
      simp only [rewriteAt, Option.map_eq_some_iff] at h
      obtain ⟨x, hx, rfl⟩ := h
      obtain ⟨h1, h2⟩ := rewriteAt_cost env r p l x hx
      exact ⟨by simp only [exprCost]; omega, fun hr => by have := h2 hr; simp only [exprCost]; omega⟩
  | .lhs :: p, .cmp op l y, e', h => by
      simp only [rewriteAt, Option.map_eq_some_iff] at h
      obtain ⟨x, hx, rfl⟩ := h
      obtain ⟨h1, h2⟩ := rewriteAt_cost env r p l x hx
      exact ⟨by simp only [exprCost]; omega, fun hr => by have := h2 hr; simp only [exprCost]; omega⟩
  | .rhs :: p, .cmp op y l, e', h => by
      simp only [rewriteAt, Option.map_eq_some_iff] at h
      obtain ⟨x, hx, rfl⟩ := h
      obtain ⟨h1, h2⟩ := rewriteAt_cost env r p l x hx
      exact ⟨by simp only [exprCost]; omega, fun hr => by have := h2 hr; simp only [exprCost]; omega⟩
  | .cond :: p, .select c a b, e', h => by
      simp only [rewriteAt, Option.map_eq_some_iff] at h
      obtain ⟨x, hx, rfl⟩ := h
      obtain ⟨h1, h2⟩ := rewriteAt_cost env r p c x hx
      exact ⟨by simp only [exprCost]; omega, fun hr => by have := h2 hr; simp only [exprCost]; omega⟩
  | .thn :: p, .select c a b, e', h => by
      simp only [rewriteAt, Option.map_eq_some_iff] at h
      obtain ⟨x, hx, rfl⟩ := h
      obtain ⟨h1, h2⟩ := rewriteAt_cost env r p a x hx
      exact ⟨by simp only [exprCost]; omega, fun hr => by have := h2 hr; simp only [exprCost]; omega⟩
  | .els :: p, .select c a b, e', h => by
      simp only [rewriteAt, Option.map_eq_some_iff] at h
      obtain ⟨x, hx, rfl⟩ := h
      obtain ⟨h1, h2⟩ := rewriteAt_cost env r p b x hx
      exact ⟨by simp only [exprCost]; omega, fun hr => by have := h2 hr; simp only [exprCost]; omega⟩
  | .arg :: _, .constBool _, _, h | .arg :: _, .constBv _ _, _, h | .arg :: _, .var _, _, h
  | .arg :: _, .binop .., _, h | .arg :: _, .cmp .., _, h | .arg :: _, .select .., _, h
  | .lhs :: _, .constBool _, _, h | .lhs :: _, .constBv _ _, _, h | .lhs :: _, .var _, _, h
  | .lhs :: _, .unop .., _, h | .lhs :: _, .select .., _, h
  | .rhs :: _, .constBool _, _, h | .rhs :: _, .constBv _ _, _, h | .rhs :: _, .var _, _, h
  | .rhs :: _, .unop .., _, h | .rhs :: _, .select .., _, h
  | .cond :: _, .constBool _, _, h | .cond :: _, .constBv _ _, _, h | .cond :: _, .var _, _, h
  | .cond :: _, .unop .., _, h | .cond :: _, .binop .., _, h | .cond :: _, .cmp .., _, h
  | .thn :: _, .constBool _, _, h | .thn :: _, .constBv _ _, _, h | .thn :: _, .var _, _, h
  | .thn :: _, .unop .., _, h | .thn :: _, .binop .., _, h | .thn :: _, .cmp .., _, h
  | .els :: _, .constBool _, _, h | .els :: _, .constBv _ _, _, h | .els :: _, .var _, _, h
  | .els :: _, .unop .., _, h | .els :: _, .binop .., _, h | .els :: _, .cmp .., _, h => by
      simp [rewriteAt] at h

theorem applySteps_cost (env : Env) :
    ∀ (ss : List Step) (e e' : Expr), applySteps env ss e = some e' →
      exprCost e' ≤ exprCost e ∧ (ss.any (fun s => s.rule.reducing) = true → exprCost e' < exprCost e)
  | [], e, e', h => by cases h; simp
  | s :: ss, e, e', h => by
      simp only [applySteps, Option.bind_eq_some_iff] at h
      obtain ⟨x, hx, hrest⟩ := h
      have h1 := rewriteAt_cost env s.rule s.path e x hx
      have h2 := applySteps_cost env ss x e' hrest
      refine ⟨by omega, fun hany => ?_⟩
      simp only [List.any_cons, Bool.or_eq_true] at hany
      rcases hany with h | h
      · have := h1.2 h; omega
      · have := h2.2 h; omega

/-- Checker that additionally demands strict static improvement. -/
def checkCertImproving (c : Cert) : Bool :=
  checkCert c && decide (programCost c.candidate < programCost c.original)

/-- **Verified static cost improvement** against the declared `forgeopt-cost` function. -/
theorem verified_static_cost_improvement {c : Cert} (h : checkCert c = true) :
    programCost c.candidate ≤ programCost c.original ∧
    (c.steps.any (fun s => s.rule.reducing) = true → programCost c.candidate < programCost c.original) := by
  obtain ⟨_, _, _, _, _, ha⟩ := checkCert_spec h
  exact applySteps_cost _ _ _ _ ha

theorem checkCertImproving_sound {c : Cert} (h : checkCertImproving c = true) :
    checkCert c = true ∧ programCost c.candidate < programCost c.original := by
  simp only [checkCertImproving, Bool.and_eq_true, decide_eq_true_eq] at h
  exact h

/-! ## Counterexample certificates -/

structure CexCert where
  original : Program
  candidate : Program
  inputs : List Value
  deriving DecidableEq, Repr

/-- Structural equality of interpreter results. -/
def resultEq : Except EvalError Value → Except EvalError Value → Bool
  | .ok x, .ok y => x == y
  | .error e, .error f => e == f
  | _, _ => false

theorem resultEq_iff (a b : Except EvalError Value) : resultEq a b = true ↔ a = b := by
  cases a <;> cases b <;> simp [resultEq]

def checkCex (c : CexCert) : Bool := !resultEq (eval c.original c.inputs) (eval c.candidate c.inputs)

/-- **Counterexample certificates are actual distinguishing inputs** of the interpreter. -/
theorem counterexample_certificate_sound {c : CexCert} (h : checkCex c = true) :
    eval c.original c.inputs ≠ eval c.candidate c.inputs ∧
      ¬ ∀ inputs, eval c.original inputs = eval c.candidate inputs := by
  simp only [checkCex, Bool.not_eq_true'] at h
  have hne : eval c.original c.inputs ≠ eval c.candidate c.inputs := fun he => by
    rw [(resultEq_iff _ _).2 he] at h; cases h
  exact ⟨hne, fun hall => hne (hall c.inputs)⟩

end PCSForgeRefinement
