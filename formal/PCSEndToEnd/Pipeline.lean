import PCSMathLanguage
import PCSVerifiedLearning

/-!
# End-to-end acceptance theorem for the supported mathematical language

This module composes the already-proved layers into one pipeline and one theorem:

1. **Request.**  A request carries the *exact* list of parse candidates and a selected
   interpretation index.  It is accepted only if the selected candidate exists and the typed
   IR checker/lowering/translation (`declGoal`) accepts it.
2. **Untrusted proposal policy.**  A policy is an *arbitrary* function of its private weights,
   rankings and unverified research memory, the selected declaration and the attempt index.
   It emits raw JSON actions or references to macros of a library generation, plus arbitrary
   claimed rewards / `verified` flags / receipts.
3. **Decoder.**  Raw JSON actions are decoded by the receiver's `ofJson` (whose rendering is
   closed, `action_rendering_closed`); macros are expanded into decoded primitive actions.
   Unknown macros or undecodable actions reject the attempt.
4. **Search.**  Attempts `0, …, budget-1` are tried in order; each expanded action list is run by
   the receiver (`runActs`) on the immutable original goal.
5. **Final verifier.**  The first closing attempt is packaged into a `Receipt` bound to the full
   declaration, the candidate list, the selected index, the exact actions, the definitions,
   checker revision and axiom inventory, and is re-checked by the *independent*
   `verifyReceipt`.
6. **Replay and training intake.**  The training example is produced only by the verifier-side
   `intake`, which ignores every claimed field of the policy.

`end_to_end_acceptance_sound` — every successful result is bound to the immutable selected
statement, carries the actual receiver closure witness, verifies, replays, and supplies only
verifier-derived labels; `policy_cannot_manufacture_acceptance` — if the selected statement is
false, *no* policy, weights, ranking, memory, budget or library generation yields success;
`success_independent_of_claims` — claimed rewards/flags/receipts never affect the outcome.
-/

namespace PCSEndToEnd

open PCSMathLanguage
open PCSVerifiedLearning (Verifier Feedback TrainExample intake eligible_feedback_reverified)

/-! ## The receiver as a verifier for the learning interface -/

/-- Receiver closure of a declaration by an action list (the checked witness). -/
def receiverCloses (maxSteps : Nat) (d : Decl) (as : List Act) : Bool :=
  match declGoal d with
  | some g => (runActs maxSteps (PState.init g) as).goals.isEmpty
  | none => false

theorem receiverCloses_witness {m : Nat} {d : Decl} {as : List Act}
    (h : receiverCloses m d as = true) :
    ∃ g, declGoal d = some g ∧ (runActs m (PState.init g) as).goals = [] := by
  unfold receiverCloses at h
  split at h
  · rename_i g hg; exact ⟨g, hg, List.isEmpty_iff.1 h⟩
  · cases h

theorem receiverCloses_sound (m : Nat) (d : Decl) (as : List Act)
    (h : receiverCloses m d as = true) : DeclHolds d := by
  obtain ⟨g, hg, hc⟩ := receiverCloses_witness h
  exact decl_goal_sound d g hg (closed_state_proves_original m g as hc)

/-- The receiver, packaged as a verifier with proved soundness (no producer flag involved). -/
def declVerifier (c : Config) : Verifier Decl Act :=
  ⟨receiverCloses c.maxSteps, DeclHolds, receiverCloses_sound c.maxSteps, c.checker⟩

/-! ## Requests, policies, budgets and library generations -/

/-- A request: the exact parse candidates and the selected interpretation. -/
structure Request where
  candidates : List Decl
  selected : Nat
  deriving DecidableEq, Repr

/-- Request acceptance: the selected candidate exists and the typed IR pipeline accepts it. -/
def Request.accepted? (q : Request) : Option Decl :=
  match q.candidates[q.selected]? with
  | some d => if (declGoal d).isSome then some d else none
  | none => none

/-- A raw proposal step: a JSON action or a macro reference. -/
inductive Proposal where
  | json (kind : String) (arg : JArg)
  | useMacro (idx : Nat)
  deriving DecidableEq, Repr

/-- A library macro: a named, costed sequence of raw JSON actions. -/
structure Macro where
  name : String
  body : List (String × JArg)
  cost : Nat
  deriving DecidableEq, Repr

/-- A library generation. -/
abbrev MacroLib := List Macro

/-- Decode raw JSON actions with the receiver's decoder (all-or-nothing). -/
def decodeAll : List (String × JArg) → Option (List Act)
  | [] => some []
  | (k, a) :: rest => match ofJson k a, decodeAll rest with
    | some x, some xs => some (x :: xs)
    | _, _ => none

/-- Independent macro admission: every body action decodes. -/
def admitMacro (m : Macro) : Bool := (decodeAll m.body).isSome

def admittedLib (lib : MacroLib) : Bool := lib.all admitMacro

/-- Macro expansion into decoded primitive receiver actions. -/
def expand (lib : MacroLib) : List Proposal → Option (List Act)
  | [] => some []
  | .json k a :: rest => match ofJson k a, expand lib rest with
    | some x, some xs => some (x :: xs)
    | _, _ => none
  | .useMacro i :: rest => match lib[i]?, expand lib rest with
    | some m, some xs => (decodeAll m.body).map (· ++ xs)
    | _, _ => none

/-- An untrusted proposal policy with private weights `W`, a ranking and unverified research
memory.  `propose` and the claimed fields are arbitrary functions. -/
structure Policy (W : Type) where
  weights : W
  ranking : List Nat
  memory : List String
  propose : W → List Nat → List String → Decl → Nat → List Proposal
  claimedReward : W → Decl → Nat → Int
  claimedVerified : W → Decl → Nat → Bool
  claimedReceipt : W → Decl → Nat → Option (PCSVerifiedLearning.Receipt Decl Act)

/-- The proposals of attempt `k`. -/
def Policy.attempt {W : Type} (p : Policy W) (d : Decl) (k : Nat) : List Proposal :=
  p.propose p.weights p.ranking p.memory d k

/-- A resource budget: number of attempts and receiver step limit. -/
structure Budget where
  attempts : Nat
  maxSteps : Nat
  deriving DecidableEq, Repr

/-- A valid budget never exceeds the final verifier's step limit. -/
def Budget.Valid (c : Config) (b : Budget) : Prop := b.maxSteps ≤ c.maxSteps

/-! ## Search, final verification, replay and intake -/

/-- Expanded actions of attempt `k`, if they close the goal under the search step limit. -/
def tryAttempt {W : Type} (lib : MacroLib) (p : Policy W) (m : Nat) (d : Decl) (k : Nat) :
    Option (List Act) :=
  match expand lib (p.attempt d k) with
  | some as => if receiverCloses m d as then some as else none
  | none => none

/-- First closing attempt among `0, …, n-1`. -/
def search {W : Type} (lib : MacroLib) (p : Policy W) (m : Nat) (d : Decl) : Nat → Option (Nat × List Act)
  | 0 => none
  | n + 1 => match search lib p m d n with
    | some r => some r
    | none => (tryAttempt lib p m d n).map (n, ·)

/-- The receipt of a successful attempt. -/
def mkReceipt (c : Config) (q : Request) (d : Decl) (as : List Act) : Receipt :=
  ⟨d, q.candidates, q.selected, as, c.definitions, c.checker, [], ""⟩

/-- Replay of a stored receipt from its content alone. -/
def replayReceipt (c : Config) (r : Receipt) : Bool := verifyReceipt c r

structure Success where
  receipt : Receipt
  attempt : Nat
  training : TrainExample Decl Act
  deriving Repr

inductive Outcome where
  | rejected
  | unresolved (attemptsUsed : Nat)
  | success (s : Success)
  deriving Repr

/-- Untrusted feedback of attempt `k` (claims are arbitrary policy outputs). -/
def feedbackOf {W : Type} (p : Policy W) (d : Decl) (k : Nat) (as : List Act) :
    Feedback Decl Act :=
  ⟨d, as, p.claimedReward p.weights d k, p.claimedVerified p.weights d k,
    p.claimedReceipt p.weights d k⟩

/-- Final verification, replay and intake of a closing attempt. -/
def conclude (c : Config) (q : Request) (d : Decl) (k : Nat) (as : List Act) (n : Nat)
    (fb : Feedback Decl Act) : Outcome :=
  if verifyReceipt c (mkReceipt c q d as) && replayReceipt c (mkReceipt c q d as) then
    match intake (declVerifier c) fb with
    | some e => .success ⟨mkReceipt c q d as, k, e⟩
    | none => .unresolved n
  else .unresolved n

/-- **The integrated pipeline.** -/
def pipeline {W : Type} (c : Config) (q : Request) (p : Policy W) (b : Budget) (lib : MacroLib) :
    Outcome :=
  match q.accepted? with
  | none => .rejected
  | some d =>
    match search lib p b.maxSteps d b.attempts with
    | none => .unresolved b.attempts
    | some (k, as) => conclude c q d k as b.attempts (feedbackOf p d k as)

theorem conclude_spec {c : Config} {q : Request} {d : Decl} {k : Nat} {as : List Act} {n : Nat}
    {fb : Feedback Decl Act} {s : Success} (h : conclude c q d k as n fb = .success s) :
    verifyReceipt c (mkReceipt c q d as) = true ∧ replayReceipt c (mkReceipt c q d as) = true ∧
      s.receipt = mkReceipt c q d as ∧ s.attempt = k ∧ intake (declVerifier c) fb = some s.training := by
  unfold conclude at h
  by_cases hv : (verifyReceipt c (mkReceipt c q d as) && replayReceipt c (mkReceipt c q d as)) = true
  · rw [if_pos hv] at h
    simp only [Bool.and_eq_true] at hv
    split at h
    · rename_i e he; cases h; exact ⟨hv.1, hv.2, rfl, rfl, he⟩
    · cases h
  · rw [if_neg hv] at h; cases h

/-! ## Lemmas -/

theorem accepted_spec {q : Request} {d : Decl} (h : q.accepted? = some d) :
    q.candidates[q.selected]? = some d ∧ (declGoal d).isSome = true := by
  unfold Request.accepted? at h
  split at h
  · rename_i d' hd
    by_cases hg : (declGoal d').isSome = true
    · rw [if_pos hg] at h; cases h; exact ⟨hd, hg⟩
    · rw [if_neg hg] at h; cases h
  · cases h

theorem search_spec {W : Type} {lib : MacroLib} {p : Policy W} {m : Nat} {d : Decl} :
    ∀ {n k : Nat} {as : List Act}, search lib p m d n = some (k, as) →
      k < n ∧ expand lib (p.attempt d k) = some as ∧ receiverCloses m d as = true := by
  intro n
  induction n with
  | zero => intro k as h; cases h
  | succ n ih =>
      intro k as h
      simp only [search] at h
      split at h
      · rename_i r hr
        cases h
        obtain ⟨h1, h2, h3⟩ := ih hr
        exact ⟨by omega, h2, h3⟩
      · simp only [Option.map_eq_some_iff] at h
        obtain ⟨as', ht, he⟩ := h
        cases he
        unfold tryAttempt at ht
        split at ht
        · rename_i as'' hx
          by_cases hc : receiverCloses m d as'' = true
          · rw [if_pos hc] at ht; cases ht; exact ⟨by omega, hx, hc⟩
          · rw [if_neg hc] at ht; cases ht
        · cases ht

/-- Search completeness for the fair attempt order: if some attempt below the budget closes,
search succeeds. -/
theorem search_complete {W : Type} {lib : MacroLib} {p : Policy W} {m : Nat} {d : Decl}
    {k : Nat} {as : List Act} (hk : tryAttempt lib p m d k = some as) :
    ∀ n, k < n → (search lib p m d n).isSome = true := by
  intro n
  induction n with
  | zero => intro h; omega
  | succ n ih =>
      intro h
      simp only [search]
      split
      · rfl
      · rename_i hn
        rcases Nat.lt_succ_iff_lt_or_eq.1 h with h | h
        · have := ih h; rw [hn] at this; cases this
        · subst h; simp [hk]

/-- Expansion output consists only of receiver-decoded primitive actions: every action is the
decoding of some raw JSON action (from the proposal or from an admitted macro body). -/
theorem expand_decoded {lib : MacroLib} :
    ∀ {ps : List Proposal} {as : List Act}, expand lib ps = some as →
      ∀ a ∈ as, ∃ k j, ofJson k j = some a := by
  have hdec : ∀ {xs : List (String × JArg)} {as : List Act}, decodeAll xs = some as →
      ∀ a ∈ as, ∃ k j, ofJson k j = some a := by
    intro xs
    induction xs with
    | nil => intro as h a ha; simp [decodeAll] at h; subst h; cases ha
    | cons x xs ih =>
        intro as h a ha
        obtain ⟨k, j⟩ := x
        simp only [decodeAll] at h
        split at h
        · rename_i y ys hy hys
          cases h
          rcases List.mem_cons.1 ha with rfl | ha
          · exact ⟨k, j, hy⟩
          · exact ih hys a ha
        · cases h
  intro ps
  induction ps with
  | nil => intro as h a ha; simp [expand] at h; subst h; cases ha
  | cons p ps ih =>
      intro as h a ha
      cases p with
      | json k j =>
          simp only [expand] at h
          split at h
          · rename_i y ys hy hys
            cases h
            rcases List.mem_cons.1 ha with rfl | ha
            · exact ⟨k, j, hy⟩
            · exact ih hys a ha
          · cases h
      | useMacro i =>
          simp only [expand] at h
          split at h
          · rename_i mc ys _ hys
            simp only [Option.map_eq_some_iff] at h
            obtain ⟨bs, hbs, rfl⟩ := h
            rcases List.mem_append.1 ha with ha | ha
            · exact hdec hbs a ha
            · exact ih hys a ha
          · cases h

/-! ## The end-to-end theorems -/

/-- **End-to-end acceptance soundness.**  For every request, every untrusted policy (weights,
rankings, memory and claims arbitrary), every budget and every library generation: a successful
result is bound to the immutable selected statement among the exact parse candidates, carries
the actual receiver-closure witness for the declaration's goal, passes the independent final
verifier under the pinned checker/definitions/axiom inventory, survives replay, establishes the
Lean statement of the declaration, and its training example is the verifier's own intake
output (label and reward verifier-derived, independent of every claimed field). -/
theorem end_to_end_acceptance_sound {W : Type} (c : Config) (q : Request) (p : Policy W)
    (b : Budget) (lib : MacroLib) (s : Success) (h : pipeline c q p b lib = .success s) :
    ∃ d g, q.candidates[q.selected]? = some d ∧ declGoal d = some g ∧
      s.receipt.decl = d ∧ s.receipt.candidates = q.candidates ∧
      s.receipt.interpretation = q.selected ∧
      s.receipt.checker = c.checker ∧ s.receipt.definitions = c.definitions ∧
      (∀ a ∈ s.receipt.axioms, a ∈ c.allowedAxioms) ∧
      (runActs c.maxSteps (PState.init g) s.receipt.actions).goals = [] ∧
      expand lib (p.attempt d s.attempt) = some s.receipt.actions ∧ s.attempt < b.attempts ∧
      verifyReceipt c s.receipt = true ∧ replayReceipt c s.receipt = true ∧
      DeclHolds d ∧
      (∀ r', r' = s.receipt → DeclHolds r'.decl) ∧
      (∀ (rw : Int) (vf : Bool) (rc : Option (PCSVerifiedLearning.Receipt Decl Act)),
        intake (declVerifier c) ⟨d, s.receipt.actions, rw, vf, rc⟩ = some s.training) ∧
      s.training.goal = d ∧ s.training.actions = s.receipt.actions ∧
      s.training.label = true ∧ s.training.reward = 100 ∧ s.training.checker = c.checker := by
  unfold pipeline at h
  split at h
  · cases h
  · rename_i d hq
    obtain ⟨hsel, hgs⟩ := accepted_spec hq
    split at h
    · cases h
    · rename_i k as hs
      obtain ⟨hk, hexp, _⟩ := search_spec hs
      obtain ⟨hv1, hv2, hr, ha, he⟩ := conclude_spec h
      rcases s with ⟨r, k', tr⟩
      simp only at hr ha he ⊢
      subst hr ha
      have hfin := final_receipt_sound c _ hv1
      obtain ⟨hchk, -, hgoal, hacts, hlab, hrew, hrev⟩ :=
        eligible_feedback_reverified (declVerifier c) _ _ he
      have hcl : receiverCloses c.maxSteps d as = true := by
        have := hchk; simp only [declVerifier] at this; rw [hgoal, hacts] at this; exact this
      obtain ⟨g, hg, hclosed⟩ := receiverCloses_witness hcl
      refine ⟨d, g, hsel, hg, rfl, rfl, rfl, rfl, rfl, hfin.2.2.2.2, hclosed, hexp,
        hk, hv1, hv2, hfin.1, ?_, ?_, hgoal, hacts, hlab, hrew, hrev⟩
      · intro r' hr; subst hr; exact hfin.1
      · intro rw vf rc
        rw [← he]; exact PCSVerifiedLearning.intake_noninterference _ _ _ rfl rfl

/-- **The policy cannot manufacture acceptance.**  If the selected statement is false, then for
every policy (any weights, rankings, unverified research memory, claimed rewards, flags and
receipts), every budget and every library generation, the pipeline does not succeed. -/
theorem policy_cannot_manufacture_acceptance {W : Type} (c : Config) (q : Request) (d : Decl)
    (hsel : q.candidates[q.selected]? = some d) (hfalse : ¬ DeclHolds d) (p : Policy W)
    (b : Budget) (lib : MacroLib) : ∀ s, pipeline c q p b lib ≠ .success s := by
  intro s h
  obtain ⟨d', _, hsel', _, _, _, _, _, _, _, _, _, _, _, _, hd, _⟩ :=
    end_to_end_acceptance_sound c q p b lib s h
  rw [hsel] at hsel'; cases hsel'
  exact hfalse hd

/-- Two policies proposing the same raw actions on the selected declaration yield the same
outcome: claimed rewards, `verified` flags, receipts, weights, rankings and memory are inert. -/
theorem success_independent_of_claims {W W' : Type} (c : Config) (q : Request) (p : Policy W)
    (p' : Policy W') (b : Budget) (lib : MacroLib)
    (hsame : ∀ d k, p.attempt d k = p'.attempt d k) :
    pipeline c q p b lib = pipeline c q p' b lib := by
  have hs : ∀ m d n, search lib p m d n = search lib p' m d n := by
    intro m d n
    induction n with
    | zero => rfl
    | succ n ih => simp only [search, tryAttempt, ih, hsame]
  unfold pipeline
  split
  · rfl
  · rename_i d _
    rw [hs]
    split
    · rfl
    · rename_i k as _
      unfold conclude
      rw [PCSVerifiedLearning.intake_noninterference (declVerifier c) (feedbackOf p d k as)
        (feedbackOf p' d k as) rfl rfl]

/-- Budget monotonicity of acceptance: a larger attempt budget never loses an available closing
attempt. -/
theorem search_budget_monotone {W : Type} {lib : MacroLib} {p : Policy W} {m : Nat} {d : Decl}
    {n n' : Nat} (hn : n ≤ n') (h : (search lib p m d n).isSome = true) :
    (search lib p m d n').isSome = true := by
  obtain ⟨⟨k, as⟩, hs⟩ := Option.isSome_iff_exists.1 h
  obtain ⟨hk, hexp, hcl⟩ := search_spec hs
  have ht : tryAttempt lib p m d k = some as := by simp [tryAttempt, hexp, hcl]
  exact search_complete ht n' (by omega)

end PCSEndToEnd
