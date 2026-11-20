import EvolvingSafetyGate

/-! Finite, executable empirical promotions with a pointwise hard-case invariant. -/
set_option autoImplicit false
namespace HardReview

abbrev Case (X : Type) := X × Bool

def hit {D X : Type} (predict : D → X → Bool) (d : D) (c : Case X) : Bool :=
  decide (predict d c.1 = c.2)

def score {D X : Type} (predict : D → X → Bool) (d : D) (rows : List (Case X)) : Nat :=
  rows.countP (hit predict d)

/-- A behavioral witness for the single admitted class of the bounded artifact
language. The two anchor packets agree on execution and later effect. -/
def admitted {D X : Type} (predict : D → X → Bool) (safe flagged : X) (d : D) : Bool :=
  EvolvingSafetyGate.admissible .jointChannel && !predict d safe && predict d flagged

def gate {D X : Type} (predict : D → X → Bool) (safe flagged : X)
    (hard measured : List (Case X)) (old proposed : D) : Bool :=
  admitted predict safe flagged old && admitted predict safe flagged proposed &&
    hard.all (fun c => !hit predict old c || hit predict proposed c) &&
    decide (score predict old measured < score predict proposed measured)

theorem gate_exact {D X : Type} (predict : D → X → Bool) (safe flagged : X)
    (hard measured : List (Case X)) (old proposed : D) :
    gate predict safe flagged hard measured old proposed = true ↔
    (admitted predict safe flagged old = true ∧ admitted predict safe flagged proposed = true) ∧
    (∀ c ∈ hard, hit predict old c = true → hit predict proposed c = true) ∧
    score predict old measured < score predict proposed measured := by
  simp only [gate, Bool.and_eq_true, List.all_eq_true, decide_eq_true_eq]
  have localRule (x y : Bool) : ((!x || y) = true) ↔ (x = true → y = true) := by
    cases x <;> cases y <;> decide
  simp only [localRule, and_assoc]

/-- Measured cases can rotate at each step. The hard case contract and the
meaning of a prediction stay fixed across an accepted lineage. -/
inductive Path {D X : Type} (p : D → X → Bool) (s f : X) (hard : List (Case X)) :
    D → D → Prop where
  | initial (d) : Path p s f hard d d
  | promote {a b c suite} : Path p s f hard a b →
      gate p s f hard suite b c = true → Path p s f hard a c

theorem path_preserves {D X : Type} {p : D → X → Bool} {s f : X} {hard : List (Case X)}
    {a b : D} (history : Path p s f hard a b) (seed : admitted p s f a = true) :
    admitted p s f b = true ∧
    ∀ c ∈ hard, hit p a c = true → hit p b c = true := by
  induction history with
  | initial => exact ⟨seed, fun _ _ yes => yes⟩
  | promote _ edge ih =>
    have step := (gate_exact ..).1 edge
    exact ⟨step.1.2, fun c mem was => step.2.1 c mem (ih.2 c mem was)⟩

/-- A controlled family whose score increases at each accepted step on a fixed
benchmark, while losing exactly one held-out answer. -/
inductive SweepInput where
  | measured (i : Nat)
  | heldOut (i : Nat)
  | anchor (b : Bool)

def sweepPredict (g : Nat) : SweepInput → Bool
  | .measured i => decide (i < g)
  | .heldOut i => decide (g ≤ i)
  | .anchor b => b

def suite (view : Nat → SweepInput) (n : Nat) : List (Case SweepInput) :=
  (List.range n).map (fun i => (view i, true))

def anchors : List (Case SweepInput) := [(.anchor false, false), (.anchor true, true)]

theorem sweep_scores (n g : Nat) :
    score sweepPredict g (suite .measured n) = min n g ∧
    score sweepPredict g (suite .heldOut n) = n - min n g := by
  induction n with
  | zero => simp [score, suite]
  | succ n ih =>
    obtain ⟨measured, held⟩ := ih
    simp only [score, suite, List.range_succ, List.map_append, List.countP_append,
      List.map_cons, List.map_nil, List.countP_cons, List.countP_nil] at *
    simp only [hit, sweepPredict, decide_eq_true_eq] at *
    by_cases before : n < g
    · have after : ¬g ≤ n := by omega
      have cur : n ≤ g := Nat.le_of_lt before
      have next : n + 1 ≤ g := before
      simp [measured, held, before, after, Nat.min_eq_left cur, Nat.min_eq_left next]
    · have after : g ≤ n := by omega
      have next : g ≤ n + 1 := Nat.le_succ_of_le after
      simp [measured, held, before, after, Nat.min_eq_right after, Nat.min_eq_right next]
      omega

theorem repeated_heldout_loss (n g : Nat) (remaining : g < n) :
    gate sweepPredict (.anchor false) (.anchor true) anchors (suite .measured n) g (g+1) = true ∧
    score sweepPredict (g+1) (suite .heldOut n) + 1 = score sweepPredict g (suite .heldOut n) := by
  obtain ⟨oldDev, oldOut⟩ := sweep_scores n g
  obtain ⟨newDev, newOut⟩ := sweep_scores n (g+1)
  have cur : min n g = g := Nat.min_eq_right (Nat.le_of_lt remaining)
  have next : min n (g + 1) = g + 1 := Nat.min_eq_right remaining
  rw [cur] at oldDev oldOut
  rw [next] at newDev newOut
  constructor
  · simp [gate, admitted, EvolvingSafetyGate.joint_channel_admissible, anchors, hit,
      sweepPredict, oldDev, newDev]
  · omega

#print axioms gate_exact
#print axioms path_preserves
#print axioms sweep_scores
#print axioms repeated_heldout_loss
end HardReview
