import Progress
import ActionCodec
set_option autoImplicit false
namespace PCSTokenPolicyGate
open PCSProgress PCSActionShield

/-- Both independent mathematical tables must name the same action. -/
def pairDecode (tokens raw : List Nat) : Option PCSActionFormat.Action :=
  match PCSActionFormat.decodeTokens tokens, PCSActionFormat.decode raw with
  | some a, some b => if a = b then some a else none
  | _, _ => none

theorem pair_roundtrip (a : PCSActionFormat.Action) :
    pairDecode (PCSActionFormat.encodeTokens a) (PCSActionFormat.encode a) = some a := by
  simp [pairDecode, PCSActionFormat.roundtrip, PCSActionFormat.token_roundtrip]

theorem pair_sound {tokens raw : List Nat} {a : PCSActionFormat.Action}
    (h : pairDecode tokens raw = some a) :
    PCSActionFormat.encodeTokens a = tokens ∧ PCSActionFormat.encode a = raw := by
  unfold pairDecode at h
  cases ht : PCSActionFormat.decodeTokens tokens with
  | none => simp [ht] at h
  | some t =>
    cases hb : PCSActionFormat.decode raw with
    | none => simp [ht,hb] at h
    | some b =>
      simp only [ht,hb] at h
      split at h
      next eq =>
        simp only [Option.some.injEq] at h
        subst t; subst b
        exact ⟨PCSActionFormat.token_decode_sound ht,PCSActionFormat.decode_sound hb⟩
      next => simp at h

theorem pair_unique {tokens raw : List Nat} {a b : PCSActionFormat.Action}
    (ha : pairDecode tokens raw = some a) (hb : pairDecode tokens raw = some b) : a = b := by
  rw [ha] at hb
  exact Option.some.inj hb

inductive Reply where
  | invalid | refused | selected (action : Nat)
  deriving DecidableEq, Repr

/-- An invalid pair never grants an execution verdict, including at a goal. -/
def gate (d : Spec) (s : Nat) (tokens raw : List Nat) : Reply :=
  match pairDecode tokens raw with
  | none => .invalid
  | some a => match choose d s (some a.val) with
    | none => .refused
    | some selected => .selected selected

theorem invalid_never_selected (d : Spec) (s : Nat) {tokens raw : List Nat}
    (h : pairDecode tokens raw = none) : gate d s tokens raw = .invalid := by
  simp [gate,h]

theorem selected_from_choose {d : Spec} {s action : Nat} {tokens raw : List Nat}
    (h : gate d s tokens raw = .selected action) :
    ∃ a, pairDecode tokens raw = some a ∧ choose d s (some a.val) = some action := by
  unfold gate at h
  cases hp : pairDecode tokens raw with
  | none => simp [hp] at h
  | some a =>
    cases hc : choose d s (some a.val) with
    | none => simp [hp,hc] at h
    | some chosen =>
      simp [hp,hc] at h
      subst chosen
      exact ⟨a,rfl,hc⟩

theorem selected_pair_bound {d : Spec} {s action : Nat} {tokens raw : List Nat}
    (h : gate d s tokens raw = .selected action) :
    ∃ a, PCSActionFormat.encodeTokens a = tokens ∧ PCSActionFormat.encode a = raw := by
  obtain ⟨a,hp,_⟩ := selected_from_choose h
  exact ⟨a,pair_sound hp⟩

theorem selected_not_forbidden {d : Spec} {s action : Nat} {tokens raw : List Nat}
    (h : gate d s tokens raw = .selected action) : action ∉ d.base.forbidden := by
  obtain ⟨_,_,hc⟩ := selected_from_choose h
  obtain ⟨cert,_,_,allowed⟩ := choose_sound hc
  exact (((check_iff d).mp cert).2.1 _ allowed).2.1

theorem selected_all_outcomes {d : Spec} {s action : Nat} {tokens raw : List Nat}
    (h : gate d s tokens raw = .selected action) {e : Edge}
    (he : e ∈ d.base.edges) (hs : e.source = s) (ha : e.action = action) :
    e.target ∈ region d ∧ e.target ∈ d.base.safe ∧
      rank d e.target < rank d s ∧ action ∉ d.base.forbidden := by
  obtain ⟨_,_,hc⟩ := selected_from_choose h
  exact chosen_step_progresses hc he hs ha

theorem canonical_available {d : Spec} (hc : check d = true) {s : Nat}
    (hw : s ∈ region d) (hg : s ∉ d.goals) (a : PCSActionFormat.Action) :
    ∃ action, gate d s (PCSActionFormat.encodeTokens a) (PCSActionFormat.encode a) = .selected action := by
  obtain ⟨action,ha⟩ := choose_available hc hw hg (some a.val)
  exact ⟨action,by simp [gate,pair_roundtrip,ha]⟩

theorem forbidden_corrected {d : Spec} (hc : check d = true) {s : Nat}
    (hw : s ∈ region d) (hg : s ∉ d.goals) (a : PCSActionFormat.Action)
    (bad : a.val ∈ d.base.forbidden) :
    ∃ action, gate d s (PCSActionFormat.encodeTokens a) (PCSActionFormat.encode a) = .selected action ∧ action ≠ a.val := by
  obtain ⟨action,ha⟩ := canonical_available hc hw hg a
  exact ⟨action,ha,fun eq => selected_not_forbidden ha (eq ▸ bad)⟩

theorem unsafe_corrected {d : Spec} (hc : check d = true) {s : Nat}
    (hw : s ∈ region d) (hg : s ∉ d.goals) (a : PCSActionFormat.Action)
    {e : Edge} (he : e ∈ d.base.edges) (hs : e.source = s) (ha : e.action = a.val)
    (badTarget : e.target ∉ d.base.safe) :
    ∃ action, gate d s (PCSActionFormat.encodeTokens a) (PCSActionFormat.encode a) = .selected action ∧ action ≠ a.val := by
  obtain ⟨action,h⟩ := canonical_available hc hw hg a
  refine ⟨action,h,?_⟩
  intro eq
  exact badTarget (selected_all_outcomes h he hs (by simpa [eq] using ha)).2.1

/-- The proposer may adapt arbitrarily to its entire prior history. Only actual
    selected calls and declared tool outcomes are admitted into this relation. -/
inductive Run (d : Spec) : List (List Nat × List Nat) → Nat → Nat → Prop where
  | nil (s : Nat) : Run d [] s s
  | cons {frames : List (List Nat × List Nat)} {s t : Nat}
      (tokens raw : List Nat) (e : Edge)
      (selected : gate d s tokens raw = .selected e.action)
      (src : e.source = s) (edge : e ∈ d.base.edges)
      (tail : Run d frames e.target t) : Run d ((tokens,raw)::frames) s t

theorem erases_to_checked_path {d : Spec} {frames : List (List Nat × List Nat)} {s t : Nat}
    (run : Run d frames s t) : Path d frames.length s t := by
  induction run with
  | nil s => exact .nil s
  | @cons frames s t tokens raw e selected src edge tail ih =>
    obtain ⟨_,_,hc⟩ := selected_from_choose selected
    exact .cons e src edge (choose_sound hc).2.2.2 ih

theorem adaptive_run_bound {d : Spec} (hc : check d = true)
    {frames : List (List Nat × List Nat)} {s t : Nat}
    (hw : s ∈ region d) (run : Run d frames s t) :
    t ∈ d.base.safe ∧ rank d t + frames.length ≤ rank d s := by
  have result := path_bound hc (erases_to_checked_path run) hw
  exact ⟨(((check_iff d).mp hc).1 _ result.1).1,result.2⟩

theorem adaptive_completion_at_rank {d : Spec} (hc : check d = true)
    {frames : List (List Nat × List Nat)} {s t : Nat}
    (hw : s ∈ region d) (run : Run d frames s t) (len : frames.length = rank d s) : t ∈ d.goals := by
  exact completion_at_bound hc hw (len ▸ erases_to_checked_path run)
theorem mismatched_actions_rejected (a b : PCSActionFormat.Action) (h : a ≠ b) :
    pairDecode (PCSActionFormat.encodeTokens a) (PCSActionFormat.encode b) = none := by
  simp [pairDecode,PCSActionFormat.roundtrip,PCSActionFormat.token_roundtrip,h]

theorem no_nonempty_run_at_goal {d : Spec} {frames : List (List Nat × List Nat)}
    {s t : Nat} (hg : s ∈ d.goals) (run : Run d frames s t) : frames = [] := by
  cases run with
  | nil => rfl
  | cons tokens raw e selected src edge tail =>
    obtain ⟨_,_,hc⟩ := selected_from_choose selected
    exact False.elim ((choose_sound hc).2.2.1 hg)
end PCSTokenPolicyGate

#print axioms PCSTokenPolicyGate.pair_roundtrip
#print axioms PCSTokenPolicyGate.pair_sound
#print axioms PCSTokenPolicyGate.pair_unique
#print axioms PCSTokenPolicyGate.invalid_never_selected
#print axioms PCSTokenPolicyGate.selected_from_choose
#print axioms PCSTokenPolicyGate.selected_pair_bound
#print axioms PCSTokenPolicyGate.selected_not_forbidden
#print axioms PCSTokenPolicyGate.selected_all_outcomes
#print axioms PCSTokenPolicyGate.canonical_available
#print axioms PCSTokenPolicyGate.forbidden_corrected
#print axioms PCSTokenPolicyGate.unsafe_corrected
#print axioms PCSTokenPolicyGate.erases_to_checked_path
#print axioms PCSTokenPolicyGate.adaptive_run_bound
#print axioms PCSTokenPolicyGate.adaptive_completion_at_rank
#print axioms PCSTokenPolicyGate.mismatched_actions_rejected
#print axioms PCSTokenPolicyGate.no_nonempty_run_at_goal
