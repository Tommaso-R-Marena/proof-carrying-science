import PCSActionShield
set_option autoImplicit false

/-! Finite adversarial reachability. No fairness assumption, deployment bridge,
    source-extraction claim, or general AI safety claim is implicit here. -/
namespace PCSProgress
open PCSActionShield

structure Spec where
  base : Model
  goals : List Nat
  ranks : List (Nat × Nat)
  deriving DecidableEq, Repr

def region (d : Spec) : List Nat := d.ranks.map Prod.fst
def rank (d : Spec) (s : Nat) : Nat :=
  ((d.ranks.find? (fun p => p.1 == s)).map Prod.snd).getD 0

def Enabled (m : Model) (s a : Nat) : Prop :=
  ∃ e ∈ m.edges, e.source = s ∧ e.action = a

instance (m : Model) (s a : Nat) : Decidable (Enabled m s a) := by
  unfold Enabled
  infer_instance

def RankValid (d : Spec) (s : Nat) : Prop :=
  s ∈ d.base.safe ∧ (rank d s = 0 ↔ s ∈ d.goals) ∧
  (s ∉ d.goals → ∃ p ∈ d.base.allowed, p.1 = s)

def PairValid (d : Spec) (p : Nat × Nat) : Prop :=
  p.1 ∈ region d ∧ p.2 ∉ d.base.forbidden ∧ Enabled d.base p.1 p.2

def EdgeValid (d : Spec) (e : Edge) : Prop :=
  e.source ∈ region d → (e.source, e.action) ∈ d.base.allowed →
  e.target ∈ region d ∧ rank d e.target < rank d e.source

def LosingWitness (d : Spec) (s : Nat) : Prop :=
  s ∉ region d → ∀ a ∈ d.base.edges.map Edge.action,
    a ∉ d.base.forbidden → Enabled d.base s a →
    ∃ e ∈ d.base.edges, e.source = s ∧ e.action = a ∧ e.target ∉ region d

instance (d : Spec) (s : Nat) : Decidable (RankValid d s) := by unfold RankValid; infer_instance
instance (d : Spec) (p : Nat × Nat) : Decidable (PairValid d p) := by unfold PairValid; infer_instance
instance (d : Spec) (e : Edge) : Decidable (EdgeValid d e) := by unfold EdgeValid; infer_instance
instance (d : Spec) (s : Nat) : Decidable (LosingWitness d s) := by unfold LosingWitness; infer_instance

/-- Initial states need not be winning: a checked negative result must remain
    representable. Runtime admission below refuses every nonwinning state. -/
def Certified (d : Spec) : Prop :=
  (∀ s ∈ region d, RankValid d s) ∧
  (∀ p ∈ d.base.allowed, PairValid d p) ∧
  (∀ e ∈ d.base.edges, EdgeValid d e) ∧
  (∀ g ∈ d.goals, g ∈ region d) ∧
  (∀ s ∈ d.base.safe, LosingWitness d s)

def check (d : Spec) : Bool :=
  (region d).all (fun s => decide (RankValid d s)) &&
  d.base.allowed.all (fun p => decide (PairValid d p)) &&
  d.base.edges.all (fun e => decide (EdgeValid d e)) &&
  d.goals.all (fun g => decide (g ∈ region d)) &&
  d.base.safe.all (fun s => decide (LosingWitness d s))

theorem check_iff (d : Spec) : check d = true ↔ Certified d := by
  simp only [check, Certified, Bool.and_eq_true, List.all_eq_true, decide_eq_true_eq, and_assoc]

/-- Safe completion within at most n tool transitions, with a controller action
    followed by an adversarial choice of ANY declared outcome. -/
def CanForce (m : Model) (goals : List Nat) : Nat → Nat → Prop
  | 0, s => s ∈ goals ∧ s ∈ m.safe
  | n+1, s => (s ∈ goals ∧ s ∈ m.safe) ∨
      (s ∈ m.safe ∧ ∃ a, a ∉ m.forbidden ∧ Enabled m s a ∧
        ∀ e ∈ m.edges, e.source = s → e.action = a → CanForce m goals n e.target)

theorem force_succ {m : Model} {g : List Nat} :
    ∀ n s, CanForce m g n s → CanForce m g (n+1) s := by
  intro n
  induction n with
  | zero => intro s h; exact Or.inl h
  | succ n ih =>
    intro s h
    rcases h with h | ⟨hs, a, ha, he, ht⟩
    · exact Or.inl h
    · exact Or.inr ⟨hs, a, ha, he, fun e mem src act => ih _ (ht e mem src act)⟩

theorem force_mono {m : Model} {g : List Nat} {n k s : Nat}
    (h : n ≤ k) (hf : CanForce m g n s) : CanForce m g k s := by
  induction h with
  | refl => exact hf
  | @step k le ih => exact force_succ k s ih

theorem winning_can_force {d : Spec} (hc : check d = true) :
    ∀ s ∈ region d, CanForce d.base d.goals (rank d s) s := by
  have cert := (check_iff d).mp hc
  have aux : ∀ n s, rank d s = n → s ∈ region d → CanForce d.base d.goals n s := by
    intro n
    induction n using Nat.strongRecOn with
    | ind n ih =>
      intro s hr hw
      have valid := cert.1 s hw
      cases n with
      | zero => exact ⟨valid.2.1.mp hr, valid.1⟩
      | succ n =>
        apply Or.inr
        have ng : s ∉ d.goals := by intro hg; have := valid.2.1.mpr hg; omega
        obtain ⟨p, hp, hps⟩ := valid.2.2 ng
        have pv := cert.2.1 p hp
        refine ⟨valid.1, p.2, pv.2.1, hps ▸ pv.2.2, ?_⟩
        intro e he hs ha
        have ep : (e.source, e.action) ∈ d.base.allowed := by simpa [hs, ha, ← hps] using hp
        have ev := cert.2.2.1 e he (by simpa [hs] using hw) ep
        have lt : rank d e.target < n+1 := by simpa [hs, hr] using ev.2
        exact force_mono (by omega) (ih _ lt _ rfl ev.1)
  intro s hw
  exact aux (rank d s) s rfl hw

/-- A complete losing-region witness rules out ANY finite worst-case completion
    bound, even for a different controller than this certificate's supervisor. -/
theorem force_implies_winning {d : Spec} (hc : check d = true) :
    ∀ n s, CanForce d.base d.goals n s → s ∈ region d := by
  have cert := (check_iff d).mp hc
  intro n
  induction n with
  | zero => intro s hf; exact cert.2.2.2.1 s hf.1
  | succ n ih =>
    intro s hf
    rcases hf with hg | ⟨hs, a, ha, he, ht⟩
    · exact cert.2.2.2.1 s hg.1
    · by_cases hw : s ∈ region d
      · exact hw
      · apply False.elim
        obtain ⟨e, hem, hes, hea⟩ := he
        have am : a ∈ d.base.edges.map Edge.action := List.mem_map.mpr ⟨e, hem, hea⟩
        obtain ⟨bad, hb, hbs, hba, hbw⟩ := cert.2.2.2.2 s hs hw a am ha ⟨e, hem, hes, hea⟩
        exact hbw (ih _ (ht bad hb hbs hba))

theorem losing_no_finite_bound {d : Spec} (hc : check d = true)
    {s : Nat} (hw : s ∉ region d) : ∀ n, ¬ CanForce d.base d.goals n s := by
  intro n h
  exact hw (force_implies_winning hc n s h)

def pick : List (Nat × Nat) → Nat → Option Nat
  | [], _ => none
  | (s,a)::xs, q => if s = q then some a else pick xs q

theorem pick_sound {xs : List (Nat × Nat)} {s a : Nat}
    (h : pick xs s = some a) : (s,a) ∈ xs := by
  induction xs with
  | nil => simp [pick] at h
  | cons p xs ih =>
    rcases p with ⟨u,b⟩
    by_cases eq : u = s
    · simp [pick, eq] at h; subst u; subst b; simp
    · simp [pick, eq] at h
      exact List.mem_cons_of_mem _ (ih h)

theorem pick_exists {xs : List (Nat × Nat)} {s : Nat}
    (h : ∃ p ∈ xs, p.1 = s) : ∃ a, pick xs s = some a := by
  induction xs with
  | nil => simpa using h
  | cons p xs ih =>
    rcases p with ⟨u,b⟩
    by_cases eq : u = s
    · exact ⟨b, by simp [pick, eq]⟩
    · simp only [pick, if_neg eq]
      apply ih
      obtain ⟨p, hp, hs⟩ := h
      rcases List.mem_cons.mp hp with rfl | hp
      · exact False.elim (eq hs)
      · exact ⟨p, hp, hs⟩

/-- The proposing model cannot create a safety violation or force an idle choice.
    A missing/denied proposal uses the fixed certificate's progressing fallback.
    Failure to call the supervisor or failure of the tool itself is not modeled. -/
def choose (d : Spec) (s : Nat) (proposal : Option Nat) : Option Nat :=
  if check d = true ∧ s ∈ region d ∧ s ∉ d.goals then
    match proposal with
    | some a => if (s,a) ∈ d.base.allowed then some a else pick d.base.allowed s
    | none => pick d.base.allowed s
  else none

theorem choose_sound {d : Spec} {s a : Nat} {proposal : Option Nat}
    (h : choose d s proposal = some a) :
    check d = true ∧ s ∈ region d ∧ s ∉ d.goals ∧ (s,a) ∈ d.base.allowed := by
  unfold choose at h
  split at h
  next cond =>
    refine ⟨cond.1, cond.2.1, cond.2.2, ?_⟩
    cases proposal with
    | none => exact pick_sound h
    | some b =>
      simp only at h
      split at h
      next hb => simp only [Option.some.injEq] at h; subst b; exact hb
      next => exact pick_sound h
  next => simp at h

theorem choose_available {d : Spec} (hc : check d = true) {s : Nat}
    (hw : s ∈ region d) (hg : s ∉ d.goals) (proposal : Option Nat) :
    ∃ a, choose d s proposal = some a := by
  have c := (check_iff d).mp hc
  obtain ⟨a, ha⟩ := pick_exists ((c.1 s hw).2.2 hg)
  cases proposal with
  | none => exact ⟨a, by simp [choose, hc, hw, hg, ha]⟩
  | some b =>
    by_cases hb : (s,b) ∈ d.base.allowed
    · exact ⟨b, by simp [choose, hc, hw, hg, hb]⟩
    · exact ⟨a, by simp [choose, hc, hw, hg, hb, ha]⟩

theorem chosen_step_progresses {d : Spec} {s a : Nat} {proposal : Option Nat}
    (h : choose d s proposal = some a) {e : Edge}
    (he : e ∈ d.base.edges) (hs : e.source = s) (ha : e.action = a) :
    e.target ∈ region d ∧ e.target ∈ d.base.safe ∧
      rank d e.target < rank d s ∧ a ∉ d.base.forbidden := by
  obtain ⟨hc, hw, _, hp⟩ := choose_sound h
  have c := (check_iff d).mp hc
  have ep : (e.source,e.action) ∈ d.base.allowed := by simpa [hs,ha] using hp
  have ev := c.2.2.1 e he (by simpa [hs] using hw) ep
  exact ⟨ev.1, (c.1 _ ev.1).1, by simpa [hs] using ev.2, (c.2.1 _ hp).2.1⟩

inductive Path (d : Spec) : Nat → Nat → Nat → Prop where
  | nil (s : Nat) : Path d 0 s s
  | cons {n s t : Nat} (e : Edge) (src : e.source = s)
      (edge : e ∈ d.base.edges) (allowed : (s,e.action) ∈ d.base.allowed)
      (tail : Path d n e.target t) : Path d (n+1) s t

theorem path_bound {d : Spec} (hc : check d = true) {n s t : Nat}
    (p : Path d n s t) (hw : s ∈ region d) :
    t ∈ region d ∧ rank d t + n ≤ rank d s := by
  have c := (check_iff d).mp hc
  induction p with
  | nil s => exact ⟨hw, by omega⟩
  | @cons n s t e src edge allowed tail ih =>
    have ep : (e.source,e.action) ∈ d.base.allowed := by simpa [src] using allowed
    have ev := c.2.2.1 e edge (by simpa [src] using hw) ep
    have rest := ih ev.1
    refine ⟨rest.1, ?_⟩
    have dec : rank d e.target < rank d s := by simpa [src] using ev.2
    omega

theorem completion_at_bound {d : Spec} (hc : check d = true) {s t : Nat}
    (hw : s ∈ region d) (p : Path d (rank d s) s t) : t ∈ d.goals := by
  have bound := path_bound hc p hw
  have zero : rank d t = 0 := by omega
  exact (((check_iff d).mp hc).1 t bound.1).2.1.mp zero

theorem preserves_existing_safety {d : Spec} (hc : check d = true)
    (hi : ∀ s ∈ d.base.initial, s ∈ region d) : PCSActionShield.check d.base = true := by
  have c := (check_iff d).mp hc
  apply (PCSActionShield.check_iff_certified d.base).mpr
  constructor
  · intro s hs; exact (c.1 s (hi s hs)).1
  · intro e he _ hp
    have source := (c.2.1 _ hp).1
    have target := (c.2.2.1 e he source hp).1
    exact ⟨(c.1 _ target).1, (c.2.1 _ hp).2.1⟩

theorem goals_halt (d : Spec) (s : Nat) (p : Option Nat) (hg : s ∈ d.goals) :
    choose d s p = none := by simp [choose, hg]

end PCSProgress
