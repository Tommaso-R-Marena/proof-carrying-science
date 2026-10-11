import PCSMathLanguage.IR

/-!
# Alpha equivalence and the structural-fingerprint firewall (`data.py`)

`structural_fingerprint` renames top-level binders to `v0, v1, …` in order and each nested
binder to `v{len(scope)}`: a de Bruijn **level** naming, then hashes the JSON.  `canonDecl` is
that canonical object (levels as numbers, binder names dropped — they are determined by the
depth), so the Python digest is `H (canonDecl d)` for a deterministic `H`.

* `Alpha` — an independent inductive definition of alpha equivalence (binder correspondence
  lists, first-match variable relation, free variables equal).
* `alpha_firewall_exact` — canonical-object equality iff alpha equivalence.
* `firewall_rejects_alpha_duplicates` — the digest firewall rejects every alpha duplicate of a
  held-out theorem, for every hash function; `firewall_admit_not_alpha` — an admitted goal is
  not alpha-equivalent to any held-out goal (collisions only cause extra rejection);
  `exact_firewall_iff` — the identity theorem uses full canonical objects.
-/

namespace PCSMathLanguage

/-- Canonical (level) objects. -/
inductive CE where
  | lvl (i : Nat)
  | free (n : String)
  | num (value : Nat) (ty : Ty)
  | tt
  | ff
  | not (a : CE)
  | apply (f a : CE)
  | quant (q : Q) (ty : Ty) (body : CE)
  | bin (op : Op) (l r : CE)
  deriving DecidableEq, Repr

def idx? : List String → String → Option Nat
  | [], _ => none
  | a :: L, x => if a = x then some 0 else (idx? L x).map (· + 1)

theorem idx?_lt : ∀ (L : List String) (x : String) (i : Nat), idx? L x = some i → i < L.length
  | [], _, _, h => by simp [idx?] at h
  | a :: L, x, i, h => by
      simp only [idx?] at h
      split at h
      · cases h; simp
      · simp only [Option.map_eq_some_iff] at h
        obtain ⟨j, hj, rfl⟩ := h
        have := idx?_lt L x j hj; simp; omega

/-- Python's `scope[name]` with the level naming `v{len(scope)}` (scope newest-first). -/
def dv (L : List String) (x : String) : CE :=
  match idx? L x with
  | some i => .lvl (L.length - 1 - i)
  | none => .free x

def canonE : List String → Expr → CE
  | L, .var n => dv L n
  | _, .num n t => .num n t
  | _, .tt => .tt
  | _, .ff => .ff
  | L, .not a => .not (canonE L a)
  | L, .apply f a => .apply (canonE L f) (canonE L a)
  | L, .quant q n t b => .quant q t (canonE (n :: L) b)
  | L, .bin op l r => .bin op (canonE L l) (canonE L r)

/-! ## Independent alpha equivalence -/

inductive VarRel : List (String × String) → String → String → Prop where
  | free {x} : VarRel [] x x
  | here {R x y} : VarRel ((x, y) :: R) x y
  | there {R x y a b} : x ≠ a → y ≠ b → VarRel R x y → VarRel ((a, b) :: R) x y

inductive Alpha : List (String × String) → Expr → Expr → Prop where
  | var {R x y} : VarRel R x y → Alpha R (.var x) (.var y)
  | num {R n t} : Alpha R (.num n t) (.num n t)
  | tt {R} : Alpha R .tt .tt
  | ff {R} : Alpha R .ff .ff
  | not {R a a'} : Alpha R a a' → Alpha R (.not a) (.not a')
  | apply {R f f' a a'} : Alpha R f f' → Alpha R a a' → Alpha R (.apply f a) (.apply f' a')
  | quant {R q x y t b b'} : Alpha ((x, y) :: R) b b' → Alpha R (.quant q x t b) (.quant q y t b')
  | bin {R op l l' r r'} : Alpha R l l' → Alpha R r r' → Alpha R (.bin op l r) (.bin op l' r')

theorem varRel_iff : ∀ (R : List (String × String)) (x y : String),
    VarRel R x y ↔ (idx? (R.map (·.1)) x = idx? (R.map (·.2)) y ∧
      (idx? (R.map (·.1)) x = none → x = y))
  | [], x, y => by
      constructor
      · intro h; cases h; simp [idx?]
      · intro h; simp [idx?] at h; subst h; exact .free
  | (a, b) :: R, x, y => by
      have ih := varRel_iff R x y
      constructor
      · intro h
        cases h with
        | here => simp [idx?]
        | there hx hy hr =>
            have hx' : ¬ a = x := fun e => hx e.symm
            have hy' : ¬ b = y := fun e => hy e.symm
            simp only [List.map_cons, idx?, hx', hy', if_false]
            obtain ⟨h1, h2⟩ := ih.1 hr
            rw [h1]
            refine ⟨rfl, fun h => h2 ?_⟩
            rw [h1]; cases hh : idx? (R.map (·.2)) y <;> simp_all
      · intro ⟨h1, h2⟩
        simp only [List.map_cons, idx?] at h1 h2
        by_cases hx : a = x <;> by_cases hy : b = y
        · subst hx; subst hy; exact .here
        · simp [hx, hy] at h1
          try (cases hh : idx? (R.map (·.2)) y <;> simp_all)
        · simp [hx, hy] at h1
          try (cases hh : idx? (R.map (·.1)) x <;> simp_all)
        · simp only [hx, hy, if_false] at h1 h2
          refine .there (fun e => hx e.symm) (fun e => hy e.symm) (ih.2 ⟨?_, ?_⟩)
          · cases h3 : idx? (R.map (·.1)) x <;> cases h4 : idx? (R.map (·.2)) y <;> simp_all
          · intro h; apply h2; rw [h]; rfl

theorem dv_eq_iff (R : List (String × String)) (x y : String) :
    dv (R.map (·.1)) x = dv (R.map (·.2)) y ↔ VarRel R x y := by
  rw [varRel_iff]
  unfold dv
  have hl : (R.map (·.1)).length = (R.map (·.2)).length := by simp
  cases h1 : idx? (R.map (·.1)) x <;> cases h2 : idx? (R.map (·.2)) y
  · simp
  · simp
  · simp
  · rename_i i j
    have := idx?_lt _ _ _ h1; have := idx?_lt _ _ _ h2
    simp only [CE.lvl.injEq, Option.some.injEq, reduceCtorEq]
    simp only [List.length_map] at *
    constructor
    · intro h; exact ⟨by omega, fun h' => by cases h'⟩
    · intro h; have := h.1; omega

/-- **Canonical objects coincide exactly for alpha-equivalent expressions.** -/
theorem canon_eq_iff_alpha : ∀ (e e' : Expr) (R : List (String × String)),
    canonE (R.map (·.1)) e = canonE (R.map (·.2)) e' ↔ Alpha R e e' := by
  intro e
  induction e with
  | var x =>
      intro e' R
      constructor
      · intro h
        cases e' with
        | var y => exact .var ((dv_eq_iff R x y).1 h)
        | _ => simp only [canonE, dv] at h; split at h <;> cases h
      · intro h; cases h with | var hr => exact (dv_eq_iff R _ _).2 hr
  | num n t =>
      intro e' R; constructor
      · intro h; cases e' <;> simp only [reduceCtorEq, canonE, dv, CE.num.injEq] at h
        · split at h <;> cases h
        · obtain ⟨rfl, rfl⟩ := h; exact .num
      · intro h; cases h; rfl
  | tt =>
      intro e' R; constructor
      · intro h; cases e' <;> simp only [reduceCtorEq, canonE, dv] at h
        · split at h <;> cases h
        all_goals first | exact .tt | cases h
      · intro h; cases h; rfl
  | ff =>
      intro e' R; constructor
      · intro h; cases e' <;> simp only [reduceCtorEq, canonE, dv] at h
        · split at h <;> cases h
        all_goals first | exact .ff | cases h
      · intro h; cases h; rfl
  | not a ih =>
      intro e' R; constructor
      · intro h; cases e' <;> simp only [reduceCtorEq, canonE, dv, CE.not.injEq] at h
        · split at h <;> cases h
        all_goals first | exact .not ((ih _ R).1 h) | cases h
      · intro h; cases h with | not ha => simp only [canonE, (ih _ R).2 ha]
  | apply f a ihf iha =>
      intro e' R; constructor
      · intro h; cases e' <;> simp only [reduceCtorEq, canonE, dv, CE.apply.injEq] at h
        · split at h <;> cases h
        all_goals first | exact .apply ((ihf _ R).1 h.1) ((iha _ R).1 h.2) | cases h
      · intro h; cases h with
        | apply hf ha => simp only [canonE, (ihf _ R).2 hf, (iha _ R).2 ha]
  | quant q x t b ih =>
      intro e' R; constructor
      · intro h; cases e' <;> simp only [reduceCtorEq, canonE, dv, CE.quant.injEq] at h
        · split at h <;> cases h
        all_goals first
          | (obtain ⟨rfl, rfl, hb⟩ := h
             exact .quant ((ih _ ((x, _) :: R)).1 hb))
          | cases h
      · intro h; cases h with
        | @quant _ _ _ y _ _ b' hb =>
            simp only [canonE]
            have := (ih b' ((x, y) :: R)).2 hb
            simp only [List.map_cons] at this
            rw [this]
  | bin op l r ihl ihr =>
      intro e' R; constructor
      · intro h; cases e' <;> simp only [reduceCtorEq, canonE, dv, CE.bin.injEq] at h
        · split at h <;> cases h
        all_goals first
          | (obtain ⟨rfl, hl, hr⟩ := h
             exact .bin ((ihl _ R).1 hl) ((ihr _ R).1 hr))
          | cases h
      · intro h; cases h with
        | bin hl hr => simp only [canonE, (ihl _ R).2 hl, (ihr _ R).2 hr]

/-! ## Declarations and the firewall -/

/-- A `pcs-math-ir-v1` declaration: binders and body. -/
structure Decl where
  binders : List (String × Ty)
  body : Expr
  deriving DecidableEq, Repr

/-- The canonical object hashed by `structural_fingerprint`. -/
def canonDecl (d : Decl) : List Ty × CE :=
  (d.binders.map (·.2), canonE (d.binders.map (·.1)).reverse d.body)

/-- Alpha equivalence of declarations: same binder types; bodies related under the binder
correspondence. -/
def AlphaDecl (d d' : Decl) : Prop :=
  d.binders.map (·.2) = d'.binders.map (·.2) ∧
    Alpha ((d.binders.map (·.1)).zip (d'.binders.map (·.1))).reverse d.body d'.body

theorem map_fst_zip_reverse (A B : List String) (h : A.length = B.length) :
    ((A.zip B).reverse.map (·.1)) = A.reverse ∧ ((A.zip B).reverse.map (·.2)) = B.reverse := by
  rw [List.map_reverse, List.map_reverse]
  exact ⟨by rw [List.map_fst_zip (by omega)], by rw [List.map_snd_zip (by omega)]⟩

/-- **Alpha firewall exactness**: canonical-object equality iff alpha equivalence. -/
theorem alpha_firewall_exact (d d' : Decl) : canonDecl d = canonDecl d' ↔ AlphaDecl d d' := by
  unfold canonDecl AlphaDecl
  constructor
  · intro h
    simp only [Prod.mk.injEq] at h
    have hl : (d.binders.map (·.1)).length = (d'.binders.map (·.1)).length := by
      have := congrArg List.length h.1; simpa using this
    obtain ⟨h1, h2⟩ := map_fst_zip_reverse _ _ hl
    refine ⟨h.1, (canon_eq_iff_alpha _ _ _).1 ?_⟩
    rw [h1, h2]; exact h.2
  · intro ⟨ht, ha⟩
    have hl : (d.binders.map (·.1)).length = (d'.binders.map (·.1)).length := by
      have := congrArg List.length ht; simpa using this
    obtain ⟨h1, h2⟩ := map_fst_zip_reverse _ _ hl
    have := (canon_eq_iff_alpha _ _ _).2 ha
    rw [h1, h2] at this
    simp only [Prod.mk.injEq]; exact ⟨ht, this⟩

/-- The digest firewall of `intake_feedback`, for an arbitrary deterministic digest `H`. -/
def firewallAdmit {D : Type} [BEq D] (H : List Ty × CE → D) (heldout : List Decl) (g : Decl) : Bool :=
  !(heldout.any fun t => H (canonDecl t) == H (canonDecl g))

/-- **Every alpha duplicate of a held-out theorem is rejected**, for every hash function. -/
theorem firewall_rejects_alpha_duplicates {D : Type} [BEq D] [LawfulBEq D] (H : List Ty × CE → D)
    (heldout : List Decl) (t g : Decl) (ht : t ∈ heldout) (ha : AlphaDecl t g) :
    firewallAdmit H heldout g = false := by
  have := (alpha_firewall_exact t g).2 ha
  simp only [firewallAdmit, Bool.not_eq_false', List.any_eq_true, beq_iff_eq]
  exact ⟨t, ht, by rw [this]⟩

/-- An admitted goal is not alpha-equivalent to any held-out goal (conservative). -/
theorem firewall_admit_not_alpha {D : Type} [BEq D] [LawfulBEq D] (H : List Ty × CE → D)
    (heldout : List Decl) (g : Decl) (h : firewallAdmit H heldout g = true) :
    ∀ t ∈ heldout, ¬ AlphaDecl t g := by
  intro t ht ha
  rw [firewall_rejects_alpha_duplicates H heldout t g ht ha] at h; cases h

/-- Exact firewall over full canonical objects: the identity theorem. -/
def exactAdmit (heldout : List Decl) (g : Decl) : Bool :=
  !(heldout.any fun t => canonDecl t == canonDecl g)

theorem exact_firewall_iff (heldout : List Decl) (g : Decl) :
    exactAdmit heldout g = true ↔ ∀ t ∈ heldout, ¬ AlphaDecl t g := by
  simp only [exactAdmit, Bool.not_eq_true', List.any_eq_false, beq_iff_eq]
  constructor
  · intro h t ht ha; exact h t ht ((alpha_firewall_exact t g).2 ha)
  · intro h t ht he; exact h t ht ((alpha_firewall_exact t g).1 he)

/-- The digest firewall admits only what the exact firewall admits. -/
theorem firewall_admit_implies_exact {D : Type} [BEq D] [LawfulBEq D] (H : List Ty × CE → D)
    (heldout : List Decl) (g : Decl) (h : firewallAdmit H heldout g = true) :
    exactAdmit heldout g = true :=
  (exact_firewall_iff heldout g).2 (firewall_admit_not_alpha H heldout g h)

end PCSMathLanguage
