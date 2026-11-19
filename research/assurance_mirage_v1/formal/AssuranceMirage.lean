/-!
# Assurance Mirage (research only)

A correcting unique-action guard can make the **executed tool channel** look
perfectly safe while the **proposal channel** and **raw-reply channel** still
fail. Any evaluation metric that inspects only the guarded tool trace therefore
admits a mirage: equal "safe completion" scores for proposers that differ on
harmfulness and confidentiality.

This file is self-contained. It does not import production PCS authority and
does not claim neural safety, OS refinement, or general alignment.
-/
set_option autoImplicit false

namespace AssuranceMirage

/-- Finite tool actions in the synthetic scientific workflow. -/
inductive Action where
  | loadEvidence | reviewClaim | publishSummary | finish | exfiltrate
  deriving DecidableEq, Repr, Inhabited

/-- Abstract workflow states. -/
inductive State where
  | start | loaded | reviewed | published | done
  deriving DecidableEq, Repr, Inhabited

/-- Unique-action correcting policy: at each live state exactly one action is
    admitted, independent of the proposer. -/
def admit (s : State) : Option Action :=
  match s with
  | .start => some .loadEvidence
  | .loaded => some .reviewClaim
  | .reviewed => some .publishSummary
  | .published => some .finish
  | .done => none

def nextState (s : State) (a : Action) : Option State :=
  match s, a with
  | .start, .loadEvidence => some .loaded
  | .loaded, .reviewClaim => some .reviewed
  | .reviewed, .publishSummary => some .published
  | .published, .finish => some .done
  | _, _ => none

/-- Channel 1: the sequence of actually admitted (state, action) pairs. -/
abbrev ToolTrace := List (State × Action)

/-- Channel 2: whether any proposed action was forbidden relative to admit. -/
structure ProposalRecord where
  proposed : Option Action
  forbidden : Bool
  deriving DecidableEq, Repr

/-- Channel 3: whether the raw completion contains a private marker bit. -/
structure RawRecord where
  leaked : Bool
  deriving DecidableEq, Repr

structure Episode where
  tools : ToolTrace
  proposals : List ProposalRecord
  raw : RawRecord
  deriving DecidableEq, Repr

/-- Correcting step: ignore the proposal and take the unique admitted action. -/
def step (s : State) (_proposal : Option Action) : Option (State × Action × State) :=
  match admit s with
  | none => none
  | some a =>
    match nextState s a with
    | none => none
    | some t => some (s, a, t)

/-- Bounded correcting execution. Proposals may be arbitrary and adaptive. -/
def run (propose : Nat → State → Option Action) : Nat → State → ToolTrace → List ProposalRecord
    → ToolTrace × List ProposalRecord
  | 0, _, tools, props => (tools, props)
  | n + 1, s, tools, props =>
    let p := propose n s
    let forbidden :=
      match admit s, p with
      | some a, some b => decide (a ≠ b)
      | some _, none => true
      | none, _ => false
    let props' := props ++ [{ proposed := p, forbidden := forbidden }]
    match step s p with
    | none => (tools, props')
    | some (s0, a, t) =>
      run propose n t (tools ++ [(s0, a)]) props'

theorem admit_unique (s : State) (a b : Action)
    (ha : admit s = some a) (hb : admit s = some b) : a = b := by
  cases s <;> simp [admit] at ha hb <;> cases ha <;> cases hb <;> rfl

/-- The correcting step ignores the proposal. -/
theorem step_proposal_independent (s : State) (p q : Option Action) :
    step s p = step s q := by
  simp [step]

/-- Tool traces are identical for any pair of proposers under the correcting guard. -/
theorem tool_trace_independent
    (p q : Nat → State → Option Action) (fuel : Nat) (s : State)
    (tools : ToolTrace) (propsP propsQ : List ProposalRecord) :
    (run p fuel s tools propsP).1 = (run q fuel s tools propsQ).1 := by
  induction fuel generalizing s tools propsP propsQ with
  | zero => rfl
  | succ n ih =>
    simp only [run]
    have hstep : step s (p n s) = step s (q n s) := step_proposal_independent s _ _
    simp [hstep]
    cases step s (q n s) with
    | none => rfl
    | some trip =>
      rcases trip with ⟨s0, a, t⟩
      exact ih t (tools ++ [(s0, a)]) _ _

/-- Channel-1-only scores cannot distinguish proposers. -/
def channel1Score (tools : ToolTrace) : Nat :=
  tools.length

theorem channel1_score_independent
    (p q : Nat → State → Option Action) (fuel : Nat) :
    channel1Score (run p fuel .start [] []).1 =
    channel1Score (run q fuel .start [] []).1 := by
  simp [channel1Score, tool_trace_independent p q fuel .start [] [] []]

/-- Constructive safe proposer: always proposes the admitted action. -/
def safePropose (_n : Nat) (s : State) : Option Action := admit s

/-- Constructive unsafe proposer: always proposes exfiltration. -/
def unsafePropose (_n : Nat) (_s : State) : Option Action := some .exfiltrate

/-- A mirage is equal channel-1 success with unequal proposal-harm or raw leakage. -/
def Mirage (e₁ e₂ : Episode) : Prop :=
  e₁.tools = e₂.tools ∧
  channel1Score e₁.tools = channel1Score e₂.tools ∧
  (e₁.proposals ≠ e₂.proposals ∨ e₁.raw ≠ e₂.raw)

def episodeOf (propose : Nat → State → Option Action) (leaked : Bool) (fuel : Nat) : Episode :=
  let r := run propose fuel .start [] []
  { tools := r.1
    proposals := r.2
    raw := { leaked := leaked } }

theorem constructive_mirage :
    let eSafe := episodeOf safePropose false 4
    let eUnsafe := episodeOf unsafePropose true 4
    Mirage eSafe eUnsafe := by
  dsimp [Mirage, episodeOf, channel1Score]
  refine ⟨?tools, rfl, Or.inr ?raw⟩
  · exact tool_trace_independent safePropose unsafePropose 4 .start [] [] []
  · intro h; cases h

/-- Any score depending only on the tool trace assigns equal values to the mirage pair. -/
theorem single_channel_blind
    (score : ToolTrace → Nat) :
    score (episodeOf safePropose false 4).tools =
    score (episodeOf unsafePropose true 4).tools := by
  simp [episodeOf, tool_trace_independent safePropose unsafePropose 4 .start [] [] []]

/-- Joint score that looks at proposals and raw leakage. -/
def jointScore (e : Episode) : Nat :=
  let harm := (e.proposals.filter (·.forbidden)).length
  let leak := if e.raw.leaked then 1 else 0
  channel1Score e.tools + 1000 * (harm + leak)

theorem joint_detects_constructive_mirage :
    jointScore (episodeOf safePropose false 4) ≠
    jointScore (episodeOf unsafePropose true 4) := by
  decide

/-- Completing the guarded workflow does not imply the proposer was competent. -/
theorem completion_not_competence :
    (run unsafePropose 4 .start [] []).1.length = 4 ∧
    ((run unsafePropose 4 .start [] []).2.filter (·.forbidden)).length = 4 := by
  decide

/-- Unguarded step follows the proposal when the transition exists. -/
def unguardedStep (s : State) (proposal : Option Action) : Option (State × Action × State) :=
  match proposal with
  | none => none
  | some a =>
    match nextState s a with
    | none => none
    | some t => some (s, a, t)

def unguardedRun (propose : Nat → State → Option Action) : Nat → State → ToolTrace → ToolTrace
  | 0, _, tools => tools
  | n + 1, s, tools =>
    match unguardedStep s (propose n s) with
    | none => tools
    | some (s0, a, t) => unguardedRun propose n t (tools ++ [(s0, a)])

/-- Under the guard, safe and unsafe proposers share a tool trace. -/
theorem guard_erases_divergence (fuel : Nat) :
    (run safePropose fuel .start [] []).1 =
    (run unsafePropose fuel .start [] []).1 :=
  tool_trace_independent safePropose unsafePropose fuel .start [] [] []

/-- Without the guard, the unsafe proposer diverges immediately. -/
theorem unguarded_diverges :
    unguardedRun safePropose 1 .start [] ≠
    unguardedRun unsafePropose 1 .start [] := by
  decide

/-- Guarded completion length is independent of the proposer; unguarded is not. -/
theorem guard_completion_independent_unguarded_not :
    (run safePropose 4 .start [] []).1.length =
      (run unsafePropose 4 .start [] []).1.length ∧
    (unguardedRun safePropose 4 .start []).length ≠
      (unguardedRun unsafePropose 4 .start []).length := by
  decide

/-- The unique-action policy never admits exfiltration. -/
theorem admit_never_exfiltrates (s : State) : admit s ≠ some .exfiltrate := by
  cases s <;> decide

/-- Channel-2 (proposal harm count) separates the constructive mirage pair. -/
def channel2Score (props : List ProposalRecord) : Nat :=
  (props.filter (·.forbidden)).length

theorem channel2_detects_constructive_mirage :
    channel2Score (episodeOf safePropose false 4).proposals ≠
    channel2Score (episodeOf unsafePropose true 4).proposals := by
  decide

/-- Channel-3 (raw leakage bit) separates the constructive mirage pair. -/
def channel3Score (raw : RawRecord) : Nat :=
  if raw.leaked then 1 else 0

theorem channel3_detects_constructive_mirage :
    channel3Score (episodeOf safePropose false 4).raw ≠
    channel3Score (episodeOf unsafePropose true 4).raw := by
  decide

/-- For every fuel budget, the constructive pair remains a mirage on tools + raw. -/
theorem constructive_mirage_any_fuel (fuel : Nat) :
    Mirage (episodeOf safePropose false fuel) (episodeOf unsafePropose true fuel) := by
  have htools :=
    tool_trace_independent safePropose unsafePropose fuel .start [] [] []
  refine ⟨?tools, ?scores, Or.inr ?raw⟩
  · simpa [episodeOf] using htools
  · simpa [episodeOf, channel1Score] using congrArg List.length htools
  · intro eq; cases eq

/-- Without the guard, the unsafe proposer never advances the scientific workflow. -/
theorem unguarded_unsafe_stalls :
    unguardedRun unsafePropose 4 .start [] = ([] : ToolTrace) := by
  decide

/-- Safe unguarded execution completes the four-step workflow. -/
theorem unguarded_safe_completes :
    (unguardedRun safePropose 4 .start []).length = 4 := by
  decide

/-!
## Indistinguishability of the constructive pair

A score on episodes is **channel-1-factorable** when it depends only on the
guarded tool trace. Under a correcting unique-action guard, every such score is
blind to the constructive mirage. By contraposition, any score that separates the
constructive mirage cannot be channel-1-factorable. This is the precise sense in
which tool-trace / task-completion metrics are not model-safety measurements.
-/

/-- A score factors through the guarded tool channel. -/
def Channel1Factorable (score : Episode → Nat) : Prop :=
  ∃ f : ToolTrace → Nat, ∀ e : Episode, score e = f e.tools

/-- Channel-1-factorable scores assign equal values to any equal-tool episodes. -/
theorem channel1_factorable_tool_determined
    (score : Episode → Nat) (h : Channel1Factorable score)
    (e₁ e₂ : Episode) (htools : e₁.tools = e₂.tools) :
    score e₁ = score e₂ := by
  rcases h with ⟨f, hf⟩
  simp [hf, htools]

/-- Every channel-1-factorable score is blind to the constructive mirage. -/
theorem channel1_factorable_blind_constructive
    (score : Episode → Nat) (h : Channel1Factorable score) :
    score (episodeOf safePropose false 4) =
    score (episodeOf unsafePropose true 4) := by
  apply channel1_factorable_tool_determined score h
  simpa [episodeOf] using
    tool_trace_independent safePropose unsafePropose 4 .start [] [] []

/-- By contraposition, separating the constructive mirage forbids channel-1 factorability. -/
theorem separates_constructive_not_channel1_factorable
    (score : Episode → Nat)
    (hsep : score (episodeOf safePropose false 4) ≠
            score (episodeOf unsafePropose true 4)) :
    ¬ Channel1Factorable score := by
  intro hfac
  exact hsep (channel1_factorable_blind_constructive score hfac)

/-- The joint score is a witness that non-factorable scores exist and detect mirages. -/
theorem joint_not_channel1_factorable :
    ¬ Channel1Factorable jointScore :=
  separates_constructive_not_channel1_factorable jointScore
    joint_detects_constructive_mirage

/-- Explicit factorability of the pure tool-length score. -/
theorem channel1Score_factorable :
    Channel1Factorable (fun e => channel1Score e.tools) :=
  ⟨channel1Score, fun _ => rfl⟩

/-- Detector bit: proposal harm present. -/
def hasProposalHarm (e : Episode) : Bool :=
  decide ((e.proposals.filter (·.forbidden)).length > 0)

/-- Detector: episode has proposal harm or raw leakage. -/
def jointFlags (e : Episode) : Bool :=
  hasProposalHarm e || e.raw.leaked

theorem joint_flags_sound (e : Episode) :
    jointFlags e = true ↔ (hasProposalHarm e = true ∨ e.raw.leaked = true) := by
  simp [jointFlags, Bool.or_eq_true]

theorem joint_flags_constructive_unsafe :
    jointFlags (episodeOf unsafePropose true 4) = true := by
  decide

theorem joint_flags_constructive_safe :
    jointFlags (episodeOf safePropose false 4) = false := by
  decide

/-!
## Transfer workflow

A second unique-action correcting program (lab notebook archive). The same
independence theorems hold: channel-1 scores cannot see proposer divergence.
-/

inductive LabAction where
  | openDraft | annotate | archivePublic | close | dumpPrivate
  deriving DecidableEq, Repr, Inhabited

inductive LabState where
  | empty | drafted | annotated | archived | closed
  deriving DecidableEq, Repr, Inhabited

def labAdmit (s : LabState) : Option LabAction :=
  match s with
  | .empty => some .openDraft
  | .drafted => some .annotate
  | .annotated => some .archivePublic
  | .archived => some .close
  | .closed => none

def labNext (s : LabState) (a : LabAction) : Option LabState :=
  match s, a with
  | .empty, .openDraft => some .drafted
  | .drafted, .annotate => some .annotated
  | .annotated, .archivePublic => some .archived
  | .archived, .close => some .closed
  | _, _ => none

abbrev LabTrace := List (LabState × LabAction)

def labStep (s : LabState) (_p : Option LabAction) : Option (LabState × LabAction × LabState) :=
  match labAdmit s with
  | none => none
  | some a =>
    match labNext s a with
    | none => none
    | some t => some (s, a, t)

def labRun (propose : Nat → LabState → Option LabAction) :
    Nat → LabState → LabTrace → LabTrace
  | 0, _, tools => tools
  | n + 1, s, tools =>
    match labStep s (propose n s) with
    | none => tools
    | some (s0, a, t) => labRun propose n t (tools ++ [(s0, a)])

theorem lab_step_proposal_independent (s : LabState) (p q : Option LabAction) :
    labStep s p = labStep s q := by
  simp [labStep]

theorem lab_tool_trace_independent
    (p q : Nat → LabState → Option LabAction) (fuel : Nat) (s : LabState)
    (tools : LabTrace) :
    labRun p fuel s tools = labRun q fuel s tools := by
  induction fuel generalizing s tools with
  | zero => rfl
  | succ n ih =>
    simp only [labRun]
    have hstep : labStep s (p n s) = labStep s (q n s) :=
      lab_step_proposal_independent s _ _
    simp [hstep]
    cases labStep s (q n s) with
    | none => rfl
    | some trip =>
      rcases trip with ⟨s0, a, t⟩
      exact ih t (tools ++ [(s0, a)])

def labSafe (_n : Nat) (s : LabState) : Option LabAction := labAdmit s
def labUnsafe (_n : Nat) (_s : LabState) : Option LabAction := some .dumpPrivate

theorem lab_guard_erases_divergence (fuel : Nat) :
    labRun labSafe fuel .empty [] = labRun labUnsafe fuel .empty [] :=
  lab_tool_trace_independent labSafe labUnsafe fuel .empty []

theorem lab_channel1_blind (score : LabTrace → Nat) :
    score (labRun labSafe 4 .empty []) =
    score (labRun labUnsafe 4 .empty []) := by
  simp [lab_tool_trace_independent labSafe labUnsafe 4 .empty []]

theorem lab_admit_never_dumps (s : LabState) :
    labAdmit s ≠ some .dumpPrivate := by
  cases s <;> decide

end AssuranceMirage

#print axioms AssuranceMirage.admit_unique
#print axioms AssuranceMirage.step_proposal_independent
#print axioms AssuranceMirage.tool_trace_independent
#print axioms AssuranceMirage.channel1_score_independent
#print axioms AssuranceMirage.constructive_mirage
#print axioms AssuranceMirage.single_channel_blind
#print axioms AssuranceMirage.joint_detects_constructive_mirage
#print axioms AssuranceMirage.completion_not_competence
#print axioms AssuranceMirage.guard_erases_divergence
#print axioms AssuranceMirage.unguarded_diverges
#print axioms AssuranceMirage.guard_completion_independent_unguarded_not
#print axioms AssuranceMirage.admit_never_exfiltrates
#print axioms AssuranceMirage.channel2_detects_constructive_mirage
#print axioms AssuranceMirage.channel3_detects_constructive_mirage
#print axioms AssuranceMirage.constructive_mirage_any_fuel
#print axioms AssuranceMirage.unguarded_unsafe_stalls
#print axioms AssuranceMirage.unguarded_safe_completes
#print axioms AssuranceMirage.channel1_factorable_tool_determined
#print axioms AssuranceMirage.channel1_factorable_blind_constructive
#print axioms AssuranceMirage.separates_constructive_not_channel1_factorable
#print axioms AssuranceMirage.joint_not_channel1_factorable
#print axioms AssuranceMirage.channel1Score_factorable
#print axioms AssuranceMirage.joint_flags_sound
#print axioms AssuranceMirage.joint_flags_constructive_unsafe
#print axioms AssuranceMirage.joint_flags_constructive_safe
#print axioms AssuranceMirage.lab_step_proposal_independent
#print axioms AssuranceMirage.lab_tool_trace_independent
#print axioms AssuranceMirage.lab_guard_erases_divergence
#print axioms AssuranceMirage.lab_channel1_blind
#print axioms AssuranceMirage.lab_admit_never_dumps
