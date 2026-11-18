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

end AssuranceMirage

#print axioms AssuranceMirage.admit_unique
#print axioms AssuranceMirage.step_proposal_independent
#print axioms AssuranceMirage.tool_trace_independent
#print axioms AssuranceMirage.channel1_score_independent
#print axioms AssuranceMirage.constructive_mirage
#print axioms AssuranceMirage.single_channel_blind
#print axioms AssuranceMirage.joint_detects_constructive_mirage
#print axioms AssuranceMirage.completion_not_competence

#print axioms AssuranceMirage.admit_unique
#print axioms AssuranceMirage.step_proposal_independent
#print axioms AssuranceMirage.tool_trace_independent
#print axioms AssuranceMirage.channel1_score_independent
#print axioms AssuranceMirage.constructive_mirage
#print axioms AssuranceMirage.single_channel_blind
#print axioms AssuranceMirage.joint_detects_constructive_mirage
#print axioms AssuranceMirage.completion_not_competence
