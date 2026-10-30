import Data
set_option autoImplicit false

/-! Post-study analysis. This does not extend the deployed authority.

The tool model and host step discipline are explicit. We couple both executions
with the SAME deterministic, history-dependent outcome resolver. This proves
neither neural computation refinement nor equality of timing, logs or raw text.
-/
namespace PCSPublicStudy
open PCSProgress

/-- At most one allowed action at each modeled state. -/
def UniqueChoices (d : Spec) : Prop :=
  ∀ s a b, (s, a) ∈ d.base.allowed → (s, b) ∈ d.base.allowed → a = b

/-- With unique choices, the admitted action cannot depend on the proposal.
    This includes arbitrary invalid/absent proposals and all modeled states. -/
theorem choose_proposal_independent {d : Spec} (hu : UniqueChoices d)
    (s : Nat) (p q : Option Nat) : choose d s p = choose d s q := by
  by_cases h : check d = true ∧ s ∈ region d ∧ s ∉ d.goals
  · obtain ⟨a, ha⟩ := choose_available h.1 h.2.1 h.2.2 p
    obtain ⟨b, hb⟩ := choose_available h.1 h.2.1 h.2.2 q
    have hab := hu s a b (choose_sound ha).2.2.2 (choose_sound hb).2.2.2
    rw [ha, hb, hab]
  · simp [choose, h]

/-- A bounded host-driven trace. Proposers may adapt to the full state history.
    Outcome resolution is fixed and may also depend on that same history.
    No arbitrary effects outside this definition are included. -/
def toolTrace (d : Spec) (resolve : List Nat → Nat → Nat)
    (propose : List Nat → Option Nat) : Nat → Nat → List Nat → List Nat
  | 0, s, _ => [s]
  | n + 1, s, past =>
      match choose d s (propose (s :: past)) with
      | none => [s]
      | some a => s :: toolTrace d resolve propose n (resolve (s :: past) a) (s :: past)

/-- Equal coupled tool traces for ANY pair of adaptive proposers and any fuel.
    Hence successful completion of this unique-action workflow alone cannot
    distinguish a competent proposer from one that always proposes nonsense. -/
theorem adaptive_tool_trace_independent {d : Spec} (hu : UniqueChoices d)
    (resolve : List Nat → Nat → Nat) (p q : List Nat → Option Nat)
    (fuel s : Nat) (past : List Nat) :
    toolTrace d resolve p fuel s past = toolTrace d resolve q fuel s past := by
  induction fuel generalizing s past with
  | zero => rfl
  | succ n ih =>
    simp only [toolTrace]
    rw [choose_proposal_independent hu s (p (s :: past)) (q (s :: past))]
    cases choose d s (q (s :: past)) with
    | none => rfl
    | some a => exact congrArg (List.cons s) (ih _ _)

/-- Any projection of the coupled state trace is also independent. This does
    not include raw model replies or other unmodeled output channels. -/
theorem projected_tool_trace_independent {d : Spec} (hu : UniqueChoices d)
    (resolve : List Nat → Nat → Nat) (p q : List Nat → Option Nat)
    (fuel s : Nat) (past : List Nat) (view : Nat → Nat) :
    (toolTrace d resolve p fuel s past).map view =
    (toolTrace d resolve q fuel s past).map view := by
  rw [adaptive_tool_trace_independent hu resolve p q fuel s past]

/-- The ACTUAL fixed specification used by the study has unique allowed choices.
    No experimental measurements or Python analysis are premises of this fact. -/
theorem actual_spec_unique : UniqueChoices PCSProgressData.spec := by
  intro s a b ha hb
  simp [PCSProgressData.spec] at ha hb
  omega

theorem actual_adaptive_trace_independent
    (resolve : List Nat → Nat → Nat) (p q : List Nat → Option Nat)
    (fuel s : Nat) (past : List Nat) :
    toolTrace PCSProgressData.spec resolve p fuel s past =
    toolTrace PCSProgressData.spec resolve q fuel s past :=
  adaptive_tool_trace_independent actual_spec_unique resolve p q fuel s past

/-- A separate raw-reply channel can reveal a private bit while the complete
    modeled tool trace stays identical. This is a countermodel to inferring
    full-output noninterference from tool-trace independence alone. -/
theorem raw_reply_channel_countermodel
    (resolve : List Nat → Nat → Nat) (p q : List Nat → Option Nat)
    (fuel s : Nat) (past : List Nat) :
    let left := (toolTrace PCSProgressData.spec resolve p fuel s past, true)
    let right := (toolTrace PCSProgressData.spec resolve q fuel s past, false)
    left.1 = right.1 ∧ left ≠ right := by
  dsimp only
  constructor
  · exact actual_adaptive_trace_independent resolve p q fuel s past
  · intro h
    have := congrArg Prod.snd h
    contradiction

end PCSPublicStudy
#print axioms PCSPublicStudy.choose_proposal_independent
#print axioms PCSPublicStudy.adaptive_tool_trace_independent
#print axioms PCSPublicStudy.projected_tool_trace_independent
#print axioms PCSPublicStudy.actual_spec_unique
#print axioms PCSPublicStudy.actual_adaptive_trace_independent
#print axioms PCSPublicStudy.raw_reply_channel_countermodel
