import PCSMathLanguage.Alpha

/-!
# Goals, local contexts, simultaneous subgoals and receiver-approved proof actions

The receiver fragment (`environment.py`): quantifier-free goals over the binders of a Math IR
declaration — `Prop`/`Nat` variables, `Nat → Nat` / `Nat → Prop` applications, the connectives,
`Nat` equality/order, `+`, `*`, literals.

* `GF`/`NT` — goal formulas with independent semantics `GF.den L` for a binder lookup `L`.
* `Act` — the typed actions of `render_action` (`intro`, `constructor`, `assumption`, `rfl`,
  `left`, `right`, `contradiction`, `exact`/`apply`/`cases`/`rewrite` of a reference with
  `.1/.2` projections, `cases … as h` (both branches), the `LEMMAS` table, the controlled
  `simp only` set, `witness`).
* `step` — action semantics on the first goal; `step_sound` — if every produced subgoal is
  valid, the goal is valid (proof-term semantics).  `cases` on a disjunction always produces
  **both** branch goals.
* `PState` — immutable original goal + simultaneous goal list; `transition_preserves_original_goal`
  for valid, invalid and exhausted transitions; `closed_state_proves_original`.
* `renderAction` — transcription of `render_action` on JSON `{kind, argument}` with the
  Bool/int distinction; `action_rendering_closed`.
-/

namespace PCSMathLanguage

inductive NT where
  | var (i : Nat)
  | lit (n : Nat)
  | add (a b : NT)
  | mul (a b : NT)
  | app (f : Nat) (a : NT)
  deriving DecidableEq, Repr

inductive GF where
  | atom (i : Nat)
  | papp (p : Nat) (a : NT)
  | tt
  | ff
  | not (a : GF)
  | and (a b : GF)
  | or (a b : GF)
  | imp (a b : GF)
  | iff (a b : GF)
  | eq (a b : NT)
  | le (a b : NT)
  deriving DecidableEq, Repr

/-- Binder lookup: index ↦ typed value. -/
abbrev Lookup := Nat → Option SVal

def natAt (L : Lookup) (i : Nat) : Nat := match L i with | some ⟨.nat, n⟩ => n | _ => 0
def propAt (L : Lookup) (i : Nat) : Prop := match L i with | some ⟨.prop, p⟩ => p | _ => False
def fnAt (L : Lookup) (i : Nat) : Nat → Nat := match L i with | some ⟨.natFn, g⟩ => g | _ => fun _ => 0
def predAt (L : Lookup) (i : Nat) : Nat → Prop := match L i with | some ⟨.natPred, g⟩ => g | _ => fun _ => False

def NT.eval (L : Lookup) : NT → Nat
  | .var i => natAt L i
  | .lit n => n
  | .add a b => a.eval L + b.eval L
  | .mul a b => a.eval L * b.eval L
  | .app f a => fnAt L f (a.eval L)

def GF.den (L : Lookup) : GF → Prop
  | .atom i => propAt L i
  | .papp p a => predAt L p (a.eval L)
  | .tt => True
  | .ff => False
  | .not a => ¬ a.den L
  | .and a b => a.den L ∧ b.den L
  | .or a b => a.den L ∨ b.den L
  | .imp a b => a.den L → b.den L
  | .iff a b => (a.den L ↔ b.den L)
  | .eq a b => a.eval L = b.eval L
  | .le a b => a.eval L ≤ b.eval L

structure Goal where
  ctx : List (String × GF)
  target : GF
  deriving DecidableEq, Repr

def Goal.Valid (g : Goal) : Prop := ∀ L, (∀ h ∈ g.ctx, h.2.den L) → g.target.den L

/-! ## References, the simp set, rewriting and the lemma table -/

/-- A local reference `name(.1|.2)*`; `false` = `.1`, `true` = `.2`. -/
structure Ref where
  name : String
  proj : List Bool
  deriving DecidableEq, Repr

def project : GF → List Bool → Option GF
  | f, [] => some f
  | .and a _, false :: ps => project a ps
  | .and _ b, true :: ps => project b ps
  | _, _ => none

def resolve (ctx : List (String × GF)) (r : Ref) : Option GF :=
  ((ctx.find? (·.1 == r.name)).map (·.2)).bind (project · r.proj)

/-- The controlled simp set `[Nat.add_zero, Nat.zero_add, Nat.mul_zero, Nat.zero_mul,
Nat.mul_one, Nat.one_mul]`, applied bottom-up. -/
def simpTop : NT → NT
  | .add a (.lit 0) => a
  | .add (.lit 0) a => a
  | .mul _ (.lit 0) => .lit 0
  | .mul (.lit 0) _ => .lit 0
  | .mul a (.lit 1) => a
  | .mul (.lit 1) a => a
  | t => t

def NT.simp : NT → NT
  | .add a b => simpTop (.add a.simp b.simp)
  | .mul a b => simpTop (.mul a.simp b.simp)
  | .app f a => .app f a.simp
  | t => t

def GF.simp : GF → GF
  | .papp p a => .papp p a.simp
  | .not a => .not a.simp
  | .and a b => .and a.simp b.simp
  | .or a b => .or a.simp b.simp
  | .imp a b => .imp a.simp b.simp
  | .iff a b => .iff a.simp b.simp
  | .eq a b => .eq a.simp b.simp
  | .le a b => .le a.simp b.simp
  | f => f

/-- Rewrite every occurrence of `l` by `r` (outermost first). -/
def NT.rw : NT → NT → NT → NT
  | .add a b, l, r => if NT.add a b = l then r else .add (a.rw l r) (b.rw l r)
  | .mul a b, l, r => if NT.mul a b = l then r else .mul (a.rw l r) (b.rw l r)
  | .app f a, l, r => if NT.app f a = l then r else .app f (a.rw l r)
  | .var i, l, r => if NT.var i = l then r else .var i
  | .lit n, l, r => if NT.lit n = l then r else .lit n

def GF.rw (l r : NT) : GF → GF
  | .papp p a => .papp p (a.rw l r)
  | .not a => .not (a.rw l r)
  | .and a b => .and (a.rw l r) (b.rw l r)
  | .or a b => .or (a.rw l r) (b.rw l r)
  | .imp a b => .imp (a.rw l r) (b.rw l r)
  | .iff a b => .iff (a.rw l r) (b.rw l r)
  | .eq a b => .eq (a.rw l r) (b.rw l r)
  | .le a b => .le (a.rw l r) (b.rw l r)
  | f => f

inductive LemmaName where
  | add_zero | zero_add | add_comm | add_assoc | mul_zero | zero_mul | mul_comm | mul_one | one_mul
  deriving DecidableEq, Repr

def LemmaName.leanName : LemmaName → String
  | .add_zero => "Nat.add_zero" | .zero_add => "Nat.zero_add" | .add_comm => "Nat.add_comm"
  | .add_assoc => "Nat.add_assoc" | .mul_zero => "Nat.mul_zero" | .zero_mul => "Nat.zero_mul"
  | .mul_comm => "Nat.mul_comm" | .mul_one => "Nat.mul_one" | .one_mul => "Nat.one_mul"

/-- `apply Nat.<lemma>` closes exactly the instances of the lemma statement. -/
def LemmaName.closes : LemmaName → GF → Bool
  | .add_zero, .eq (.add a (.lit 0)) b => a == b
  | .zero_add, .eq (.add (.lit 0) a) b => a == b
  | .add_comm, .eq (.add a b) (.add c d) => a == d && b == c
  | .add_assoc, .eq (.add (.add a b) c) (.add a' (.add b' c')) => a == a' && b == b' && c == c'
  | .mul_zero, .eq (.mul _ (.lit 0)) (.lit 0) => true
  | .zero_mul, .eq (.mul (.lit 0) _) (.lit 0) => true
  | .mul_comm, .eq (.mul a b) (.mul c d) => a == d && b == c
  | .mul_one, .eq (.mul a (.lit 1)) b => a == b
  | .one_mul, .eq (.mul (.lit 1) a) b => a == b
  | _, _ => false

/-! ## Actions and their semantics -/

inductive Act where
  | intro (h : String)
  | constructor
  | assumption
  | rfl
  | left
  | right
  | contradiction
  | exact (r : Ref)
  | apply (r : Ref)
  | cases (r : Ref) (as : Option String)
  | rewrite (r : Ref)
  | lemma (n : LemmaName)
  | simp
  | witness (n : Nat)
  deriving DecidableEq, Repr

/-- Closing by reflexivity (`rfl`, and the `rfl` attempted after `rw`). -/
def reflCloses : GF → Bool
  | .eq a b => a == b
  | .iff a b => a == b
  | .le a b => a == b
  | _ => false

/-- Goals closed by the `rfl`-closure of `simp only`. -/
def closesTriv : GF → Bool
  | .tt => true
  | .eq a b => a == b
  | _ => false

theorem closesTriv_sound (L : Lookup) (f : GF) (h : closesTriv f = true) : f.den L := by
  cases f <;> simp_all [closesTriv, GF.den]

/-- One action on one goal: `none` = rejected; `some gs` = the new simultaneous subgoals. -/
def step (g : Goal) : Act → Option (List Goal)
  | .intro h => match g.target with
    | .imp a b => some [⟨(h, a) :: g.ctx, b⟩]
    | .not a => some [⟨(h, a) :: g.ctx, .ff⟩]
    | _ => none
  | .constructor => match g.target with
    | .and a b => some [⟨g.ctx, a⟩, ⟨g.ctx, b⟩]
    | .iff a b => some [⟨g.ctx, .imp a b⟩, ⟨g.ctx, .imp b a⟩]
    | .tt => some []
    | .eq a b => if a = b then some [] else none
    | _ => none
  | .assumption => if g.ctx.any (·.2 == g.target) then some [] else none
  | .rfl => if reflCloses g.target then some [] else none
  | .left => match g.target with
    | .or a _ => some [⟨g.ctx, a⟩]
    | _ => none
  | .right => match g.target with
    | .or _ b => some [⟨g.ctx, b⟩]
    | _ => none
  | .contradiction =>
    if g.ctx.any (·.2 == .ff) || g.ctx.any (fun h => g.ctx.any (·.2 == .not h.2)) then some []
    else none
  | .exact r => if resolve g.ctx r = some g.target then some [] else none
  | .apply r => match resolve g.ctx r with
    | some (.imp a b) => if b = g.target then some [⟨g.ctx, a⟩]
      else if GF.imp a b = g.target then some [] else none
    | some (.not a) => if g.target = .ff then some [⟨g.ctx, a⟩]
      else if GF.not a = g.target then some [] else none
    | some f => if f = g.target then some [] else none
    | none => none
  | .cases r as => match resolve g.ctx r, as with
    | some (.or a b), some h => some [⟨(h, a) :: g.ctx, g.target⟩, ⟨(h, b) :: g.ctx, g.target⟩]
    | some (.or a b), none => some [⟨("", a) :: g.ctx, g.target⟩, ⟨("", b) :: g.ctx, g.target⟩]
    | some (.and a b), none => some [⟨("", a) :: ("", b) :: g.ctx, g.target⟩]
    | _, _ => none
  | .rewrite r => match resolve g.ctx r with
    | some (.eq l rr) =>
      let t := g.target.rw l rr
      if t = g.target then none else if reflCloses t then some [] else some [⟨g.ctx, t⟩]
    | _ => none
  | .lemma n => if n.closes g.target then some [] else none
  | .simp =>
    let t := g.target.simp
    if t = g.target then none
    else if closesTriv t then some []
    else some [⟨g.ctx, t⟩]
  | .witness _ => none

/-! ### Soundness of every action -/

theorem simpTop_eval (L : Lookup) (t : NT) : (simpTop t).eval L = t.eval L := by
  unfold simpTop
  split <;> simp [NT.eval]

theorem NT.simp_eval (L : Lookup) : ∀ t : NT, t.simp.eval L = t.eval L
  | .add a b => by simp only [NT.simp, simpTop_eval, NT.eval, NT.simp_eval L a, NT.simp_eval L b]
  | .mul a b => by simp only [NT.simp, simpTop_eval, NT.eval, NT.simp_eval L a, NT.simp_eval L b]
  | .app f a => by simp only [NT.simp, NT.eval, NT.simp_eval L a]
  | .var _ => rfl
  | .lit _ => rfl

theorem GF.simp_den (L : Lookup) : ∀ f : GF, f.simp.den L ↔ f.den L
  | .papp p a => by simp only [GF.simp, GF.den, NT.simp_eval]
  | .not a => by simp only [GF.simp, GF.den, GF.simp_den L a]
  | .and a b => by simp only [GF.simp, GF.den, GF.simp_den L a, GF.simp_den L b]
  | .or a b => by simp only [GF.simp, GF.den, GF.simp_den L a, GF.simp_den L b]
  | .imp a b => by simp only [GF.simp, GF.den, GF.simp_den L a, GF.simp_den L b]
  | .iff a b => by simp only [GF.simp, GF.den, GF.simp_den L a, GF.simp_den L b]
  | .eq a b => by simp only [GF.simp, GF.den, NT.simp_eval]
  | .le a b => by simp only [GF.simp, GF.den, NT.simp_eval]
  | .atom _ => Iff.rfl
  | .tt => Iff.rfl
  | .ff => Iff.rfl

theorem NT.rw_eval (L : Lookup) (l r : NT) (h : l.eval L = r.eval L) :
    ∀ t : NT, (t.rw l r).eval L = t.eval L := by
  intro t
  induction t with
  | var i => simp only [NT.rw]; split <;> simp_all
  | lit n => simp only [NT.rw]; split <;> simp_all
  | add a b iha ihb =>
      simp only [NT.rw]; split
      · rename_i he; subst he; exact h.symm
      · simp_all [NT.eval]
  | mul a b iha ihb =>
      simp only [NT.rw]; split
      · rename_i he; subst he; exact h.symm
      · simp_all [NT.eval]
  | app f a ih =>
      simp only [NT.rw]; split
      · rename_i he; subst he; exact h.symm
      · simp_all [NT.eval]

theorem GF.rw_den (L : Lookup) (l r : NT) (h : l.eval L = r.eval L) :
    ∀ f : GF, (f.rw l r).den L ↔ f.den L := by
  intro f
  induction f with
  | papp p a => simp only [GF.rw, GF.den, NT.rw_eval L l r h]
  | not a ih => simp only [GF.rw, GF.den, ih]
  | and a b iha ihb => simp only [GF.rw, GF.den, iha, ihb]
  | or a b iha ihb => simp only [GF.rw, GF.den, iha, ihb]
  | imp a b iha ihb => simp only [GF.rw, GF.den, iha, ihb]
  | iff a b iha ihb => simp only [GF.rw, GF.den, iha, ihb]
  | eq a b => simp only [GF.rw, GF.den, NT.rw_eval L l r h]
  | le a b => simp only [GF.rw, GF.den, NT.rw_eval L l r h]
  | atom _ => exact Iff.rfl
  | tt => exact Iff.rfl
  | ff => exact Iff.rfl

theorem reflCloses_sound (L : Lookup) (f : GF) (h : reflCloses f = true) : f.den L := by
  cases f <;> simp_all [reflCloses, GF.den, Nat.le_refl]

theorem project_sound (L : Lookup) : ∀ (f : GF) (ps : List Bool) (g : GF),
    project f ps = some g → f.den L → g.den L
  | f, [], g, h, hf => by simp [project] at h; subst h; exact hf
  | .and a _, false :: ps, g, h, hf => project_sound L a ps g h hf.1
  | .and _ b, true :: ps, g, h, hf => project_sound L b ps g h hf.2
  | .atom _, _ :: _, _, h, _ | .papp _ _, _ :: _, _, h, _ | .tt, _ :: _, _, h, _
  | .ff, _ :: _, _, h, _ | .not _, _ :: _, _, h, _ | .or _ _, _ :: _, _, h, _
  | .imp _ _, _ :: _, _, h, _ | .iff _ _, _ :: _, _, h, _ | .eq _ _, _ :: _, _, h, _
  | .le _ _, _ :: _, _, h, _ => by simp [project] at h

theorem resolve_sound (L : Lookup) (ctx : List (String × GF)) (r : Ref) (g : GF)
    (hctx : ∀ h ∈ ctx, h.2.den L) (h : resolve ctx r = some g) : g.den L := by
  unfold resolve at h
  cases hf : ctx.find? (·.1 == r.name) with
  | none => simp [hf] at h
  | some e =>
      simp only [hf, Option.map_some, Option.bind_some] at h
      exact project_sound L e.2 r.proj g h (hctx e (List.mem_of_find?_eq_some hf))

theorem closes_sound (L : Lookup) (n : LemmaName) (f : GF) (h : n.closes f = true) : f.den L := by
  cases n <;> unfold LemmaName.closes at h <;> split at h <;> simp_all [GF.den, NT.eval] <;>
    first
    | omega
    | (subst_vars; first | exact Nat.add_comm _ _ | exact Nat.mul_comm _ _ | exact Nat.add_assoc _ _ _)

theorem ctx_cons {L : Lookup} {ctx : List (String × GF)} {n : String} {a : GF}
    (h : ∀ h ∈ ctx, h.2.den L) (ha : a.den L) : ∀ h ∈ (n, a) :: ctx, h.2.den L := by
  intro x hx
  rcases List.mem_cons.1 hx with rfl | hx
  · exact ha
  · exact h x hx

/-- **Every receiver action is sound**: validity of all produced subgoals gives validity of the
goal.  No branch can be dropped: `cases` returns both. -/
theorem step_sound (g : Goal) (a : Act) (gs : List Goal) (h : step g a = some gs)
    (hv : ∀ g' ∈ gs, g'.Valid) : g.Valid := by
  obtain ⟨ctx, tgt⟩ := g
  intro L hctx
  simp only at hctx ⊢
  have hv1 : ∀ c t, (∀ x ∈ c, x.2.den L) → (⟨c, t⟩ : Goal) ∈ gs → t.den L :=
    fun c t hc hm => hv _ hm L hc
  cases a with
  | intro n =>
      cases tgt <;> simp only [step] at h <;> try cases h
      · intro ha; exact hv1 _ _ (ctx_cons hctx ha) List.mem_cons_self
      · intro ha; exact hv1 _ _ (ctx_cons hctx ha) List.mem_cons_self
  | constructor =>
      cases tgt <;> simp only [step] at h <;> try cases h
      · trivial
      · exact ⟨hv1 _ _ hctx List.mem_cons_self, hv1 _ _ hctx (List.mem_cons_of_mem _ List.mem_cons_self)⟩
      · exact ⟨hv1 ctx (.imp _ _) hctx List.mem_cons_self,
          hv1 ctx (.imp _ _) hctx (List.mem_cons_of_mem _ List.mem_cons_self)⟩
      · split at h
        · rename_i hab; subst hab; exact rfl
        · cases h
  | assumption =>
      simp only [step] at h
      split at h
      · rename_i hm
        simp only [List.any_eq_true, beq_iff_eq] at hm
        obtain ⟨x, hx, he⟩ := hm
        rw [← he]; exact hctx x hx
      · cases h
  | rfl =>
      simp only [step] at h
      split at h
      · exact reflCloses_sound L _ (by assumption)
      · cases h
  | left =>
      cases tgt <;> simp only [step] at h <;> try cases h
      exact Or.inl (hv1 _ _ hctx List.mem_cons_self)
  | right =>
      cases tgt <;> simp only [step] at h <;> try cases h
      exact Or.inr (hv1 _ _ hctx List.mem_cons_self)
  | contradiction =>
      simp only [step] at h
      split at h
      · rename_i hm
        simp only [Bool.or_eq_true, List.any_eq_true, beq_iff_eq] at hm
        exfalso
        rcases hm with ⟨x, hx, he⟩ | ⟨x, hx, y, hy, he⟩
        · have := hctx x hx; rw [he] at this; exact this
        · have h1 := hctx x hx; have h2 := hctx y hy; rw [he] at h2; exact h2 h1
      · cases h
  | exact r =>
      simp only [step] at h
      split at h
      · exact resolve_sound L ctx r tgt hctx (by assumption)
      · cases h
  | apply r =>
      cases hres : resolve ctx r with
      | none => simp [step, hres] at h
      | some f =>
        have hf := resolve_sound L ctx r f hctx hres
        cases f
        case imp a b =>
          simp only [step, hres] at h
          split at h
          · rename_i hb; cases h; rw [← hb]; exact hf (hv1 _ _ hctx List.mem_cons_self)
          · split at h
            · rename_i hb; rw [← hb]; exact hf
            · cases h
        case not a =>
          simp only [step, hres] at h
          split at h
          · rename_i hb; cases h; rw [hb]; exact hf (hv1 _ _ hctx List.mem_cons_self)
          · split at h
            · rename_i hb; rw [← hb]; exact hf
            · cases h
        all_goals
          simp only [step, hres] at h
          split at h
          · rename_i hb; rw [← hb]; exact hf
          · cases h
  | cases r as =>
      cases hres : resolve ctx r with
      | none => simp [step, hres] at h
      | some f =>
        have hf := resolve_sound L ctx r f hctx hres
        cases f <;> cases as <;> simp only [step, hres] at h <;> try cases h
        · exact hv1 _ _ (ctx_cons (ctx_cons hctx hf.2) hf.1) List.mem_cons_self
        · rcases hf with ha | hb
          · exact hv1 _ _ (ctx_cons hctx ha) List.mem_cons_self
          · exact hv1 _ _ (ctx_cons hctx hb) (List.mem_cons_of_mem _ List.mem_cons_self)
        · rcases hf with ha | hb
          · exact hv1 _ _ (ctx_cons hctx ha) List.mem_cons_self
          · exact hv1 _ _ (ctx_cons hctx hb) (List.mem_cons_of_mem _ List.mem_cons_self)
  | rewrite r =>
      cases hres : resolve ctx r with
      | none => simp [step, hres] at h
      | some f =>
        have hf := resolve_sound L ctx r f hctx hres
        cases f <;> simp only [step, hres] at h <;> try cases h
        rename_i l rr
        have he : l.eval L = rr.eval L := hf
        split at h
        · cases h
        · split at h
          · exact (GF.rw_den L l rr he tgt).1 (reflCloses_sound L _ (by assumption))
          · cases h; exact (GF.rw_den L l rr he tgt).1 (hv1 _ _ hctx List.mem_cons_self)
  | lemma n =>
      simp only [step] at h
      split at h
      · exact closes_sound L n tgt (by assumption)
      · cases h
  | simp =>
      simp only [step] at h
      split at h
      · cases h
      · split at h
        · exact (GF.simp_den L tgt).1 (closesTriv_sound L _ (by assumption))
        · cases h; exact (GF.simp_den L tgt).1 (hv1 _ _ hctx List.mem_cons_self)
  | witness n => simp [step] at h

/-! ## Proof states with an immutable original goal -/

structure PState where
  original : Goal
  goals : List Goal
  actions : List Act
  deriving DecidableEq, Repr

def PState.init (g : Goal) : PState := ⟨g, [g], []⟩

/-- Outcome of one transition (`environment.py`): valid → advanced; invalid → unchanged and
terminated; exhausted → unchanged and truncated. -/
inductive Outcome where
  | advanced (s : PState)
  | invalid (s : PState)
  | exhausted (s : PState)
  deriving Repr

def Outcome.state : Outcome → PState
  | .advanced s | .invalid s | .exhausted s => s

def transition (maxSteps : Nat) (s : PState) (a : Act) : Outcome :=
  if maxSteps ≤ s.actions.length then .exhausted s else
  match s.goals with
  | [] => .invalid s
  | g :: rest => match step g a with
    | some gs => .advanced ⟨s.original, gs ++ rest, s.actions ++ [a]⟩
    | none => .invalid s

/-- The authorisation invariant: validity of all open goals implies the original. -/
def PState.Inv (s : PState) : Prop := (∀ g ∈ s.goals, g.Valid) → s.original.Valid

theorem init_inv (g : Goal) : (PState.init g).Inv := fun h => h g List.mem_cons_self

/-- **Immutable goal preservation** through valid, invalid and exhausted transitions. -/
theorem transition_preserves_original_goal (m : Nat) (s : PState) (a : Act) (hI : s.Inv) :
    (transition m s a).state.original = s.original ∧ (transition m s a).state.Inv := by
  unfold transition
  split
  · exact ⟨rfl, hI⟩
  · split
    · exact ⟨rfl, hI⟩
    · rename_i g rest hgs
      split
      · rename_i gs hst
        refine ⟨rfl, fun hall => hI fun g' hg' => ?_⟩
        rw [hgs] at hg'
        rcases List.mem_cons.1 hg' with rfl | hg'
        · exact step_sound g' a gs hst (fun x hx => hall x (List.mem_append_left _ hx))
        · exact hall g' (List.mem_append_right _ hg')
      · exact ⟨rfl, hI⟩

/-- Run a whole action sequence (stops at the first invalid or exhausted transition). -/
def runActs (m : Nat) : PState → List Act → PState
  | s, [] => s
  | s, a :: as => match transition m s a with
    | .advanced s' => runActs m s' as
    | o => o.state

theorem runActs_inv (m : Nat) : ∀ (as : List Act) (s : PState), s.Inv →
    (runActs m s as).original = s.original ∧ (runActs m s as).Inv := by
  intro as
  induction as with
  | nil => intro s h; exact ⟨rfl, h⟩
  | cons a as ih =>
      intro s hI
      have ht := transition_preserves_original_goal m s a hI
      simp only [runActs]
      split
      · rename_i s' he
        rw [he] at ht
        obtain ⟨h1, h2⟩ := ih s' ht.2
        exact ⟨h1.trans ht.1, h2⟩
      · rename_i o _; exact ht

/-- **Receiver closure entails the immutable original goal.** -/
theorem closed_state_proves_original (m : Nat) (g : Goal) (as : List Act)
    (h : (runActs m (PState.init g) as).goals = []) : g.Valid := by
  obtain ⟨h1, h2⟩ := runActs_inv m as (PState.init g) (init_inv g)
  have := h2 (by rw [h]; intro x hx; cases hx)
  rw [h1] at this; exact this

/-- **All branches are required**: a state whose remaining goals include an invalid goal can
never be closed by any continuation (soundness), e.g. the second branch of `A ∨ B → A`. -/
theorem all_branches_required (m : Nat) (g : Goal) (hg : ¬ g.Valid) (as : List Act) :
    (runActs m (PState.init g) as).goals ≠ [] :=
  fun h => hg (closed_state_proves_original m g as h)

end PCSMathLanguage
