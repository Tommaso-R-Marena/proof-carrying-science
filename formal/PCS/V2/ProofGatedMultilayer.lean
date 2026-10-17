import PCS.V2.ProofGatedSelfImprovement

/-!
# Two-hidden-neuron exact integer self-modification

An intentionally small *genuine two-hidden-unit* ReLU model.
Inputs, weights, activations and losses are mathematical integers, not
unverified floating-point/GPU operations.

The formal gate establishes improvement only on a fixed seven-input corpus.
Every parameter of the incumbent and candidate must be in [-32,32].
-/

namespace PCS.V2.ProofGatedMultilayer

open PCS.V2.ProofGatedSelfImprovement (relu)

structure TinyNet where
  h1w : Int
  h1b : Int
  h2w : Int
  h2b : Int
  out1 : Int
  out2 : Int
  outBias : Int
  deriving Repr, DecidableEq

def predict (m : TinyNet) (x : Int) : Int :=
  m.out1 * relu (m.h1w * x + m.h1b) +
  m.out2 * relu (m.h2w * x + m.h2b) + m.outBias

def corpus : List Int := [-3, -2, -1, 0, 1, 2, 3]

def target (x : Int) : Int := relu (2*x+1) + relu (-x+1)

def correct (m : TinyNet) (x : Int) : Prop := predict m x = target x

instance instCorrectDecidable (m : TinyNet) (x : Int) : Decidable (correct m x) :=
  inferInstanceAs (Decidable (predict m x = target x))

def params (m : TinyNet) : List Int :=
  [m.h1w, m.h1b, m.h2w, m.h2b, m.out1, m.out2, m.outBias]

def boundedParam (z : Int) : Bool := decide (-32 ≤ z ∧ z ≤ 32)
def bounded (m : TinyNet) : Bool := (params m).all boundedParam

def loss (m : TinyNet) : Nat :=
  (corpus.map fun x => (predict m x - target x).natAbs).sum

def preservesB : List Int → TinyNet → TinyNet → Bool
  | [], _, _ => true
  | x :: xs, a, b =>
      decide (correct a x → correct b x) && preservesB xs a b

def gainsB : List Int → TinyNet → TinyNet → Bool
  | [], _, _ => false
  | x :: xs, a, b =>
      decide (¬ correct a x ∧ correct b x) || gainsB xs a b

def admissible (a b : TinyNet) : Prop :=
  bounded a = true ∧ bounded b = true ∧
  (∀ x ∈ corpus, correct a x → correct b x) ∧
  (∃ x ∈ corpus, ¬ correct a x ∧ correct b x) ∧
  loss b < loss a

def accept (a b : TinyNet) : Bool :=
  (((bounded a && bounded b) && preservesB corpus a b) &&
    gainsB corpus a b) && decide (loss b < loss a)

private theorem preservesB_sound (xs : List Int) (a b : TinyNet)
    (h : preservesB xs a b = true) :
    ∀ x ∈ xs, correct a x → correct b x := by
  induction xs with
  | nil =>
      intro x hx
      cases hx
  | cons y ys ih =>
      have hparts : (correct a y → correct b y) ∧ preservesB ys a b = true := by
        simpa only [preservesB, Bool.and_eq_true, decide_eq_true_eq] using h
      intro x hx
      have hm : x = y ∨ x ∈ ys := by simpa only [List.mem_cons] using hx
      cases hm with
      | inl heq =>
          cases heq
          exact hparts.1
      | inr mem =>
          exact ih hparts.2 x mem

private theorem gainsB_sound (xs : List Int) (a b : TinyNet)
    (h : gainsB xs a b = true) :
    ∃ x ∈ xs, ¬ correct a x ∧ correct b x := by
  induction xs with
  | nil => simp [gainsB] at h
  | cons y ys ih =>
      have hparts : (¬ correct a y ∧ correct b y) ∨ gainsB ys a b = true := by
        simpa only [gainsB, Bool.or_eq_true, decide_eq_true_eq] using h
      cases hparts with
      | inl hy => exact ⟨y, by simp, hy⟩
      | inr ht =>
          obtain ⟨x, hx, hc⟩ := ih ht
          exact ⟨x, by simp [hx], hc⟩

theorem accept_sound {a b : TinyNet} (h : accept a b = true) :
    admissible a b := by
  simp only [accept, Bool.and_eq_true] at h
  exact ⟨h.1.1.1.1, h.1.1.1.2,
    preservesB_sound corpus a b h.1.1.2,
    gainsB_sound corpus a b h.1.2,
    (decide_eq_true_eq).mp h.2⟩

theorem accepted_preserves {a b : TinyNet} (h : accept a b = true)
    (x : Int) (hx : x ∈ corpus) (hc : correct a x) :
    correct b x := (accept_sound h).2.2.1 x hx hc

theorem accepted_expands {a b : TinyNet} (h : accept a b = true) :
    ∃ x ∈ corpus, ¬ correct a x ∧ correct b x :=
  (accept_sound h).2.2.2.1

theorem accepted_strict_loss {a b : TinyNet} (h : accept a b = true) :
    loss b < loss a := (accept_sound h).2.2.2.2

theorem accepted_candidate_bounded {a b : TinyNet}
    (h : accept a b = true) : bounded b = true :=
  (accept_sound h).2.1

inductive CertifiedTrace : Nat → TinyNet → TinyNet → Prop where
  | zero (m : TinyNet) : CertifiedTrace 0 m m
  | extend {n : Nat} {a b c : TinyNet} :
      CertifiedTrace n a b → accept b c = true → CertifiedTrace (n+1) a c

theorem trace_preserves {n : Nat} {a b : TinyNet}
    (h : CertifiedTrace n a b) (x : Int) (hx : x ∈ corpus)
    (ha : correct a x) : correct b x := by
  induction h with
  | zero m => exact ha
  | extend hp hc ih => exact accepted_preserves hc x hx (ih ha)

theorem trace_length_bound {n : Nat} {a b : TinyNet}
    (h : CertifiedTrace n a b) : n + loss b ≤ loss a := by
  induction h with
  | zero m => simp
  | extend hp hc ih =>
      have hd := accepted_strict_loss hc
      omega

def gatedStep (m proposed : TinyNet) : TinyNet :=
  if accept m proposed then proposed else m

theorem gatedStep_preserves (m proposed : TinyNet)
    (x : Int) (hx : x ∈ corpus) (hc : correct m x) :
    correct (gatedStep m proposed) x := by
  cases h : accept m proposed with
  | false => simpa [gatedStep, h] using hc
  | true => simpa [gatedStep, h] using accepted_preserves h x hx hc

theorem gatedStep_loss (m proposed : TinyNet) :
    loss (gatedStep m proposed) ≤ loss m := by
  cases h : accept m proposed with
  | false => simp [gatedStep, h]
  | true => simpa [gatedStep, h] using Nat.le_of_lt (accepted_strict_loss h)

def runProposers : TinyNet → List (TinyNet → TinyNet) → TinyNet
  | m, [] => m
  | m, proposer :: rest => runProposers (gatedStep m (proposer m)) rest

theorem arbitrary_proposers_preserve (proposers : List (TinyNet → TinyNet))
    (m : TinyNet) (x : Int) (hx : x ∈ corpus) (hc : correct m x) :
    correct (runProposers m proposers) x := by
  induction proposers generalizing m with
  | nil => simpa [runProposers] using hc
  | cons proposer rest ih =>
      change correct (runProposers (gatedStep m (proposer m)) rest) x
      exact ih (gatedStep m (proposer m))
        (gatedStep_preserves m (proposer m) x hx hc)

theorem arbitrary_proposers_nonincrease (proposers : List (TinyNet → TinyNet))
    (m : TinyNet) : loss (runProposers m proposers) ≤ loss m := by
  induction proposers generalizing m with
  | nil => simp [runProposers]
  | cons proposer rest ih =>
      change loss (runProposers (gatedStep m (proposer m)) rest) ≤ loss m
      exact Nat.le_trans (ih (gatedStep m (proposer m)))
        (gatedStep_loss m (proposer m))

def swapHidden (m : TinyNet) : TinyNet :=
  ⟨m.h2w, m.h2b, m.h1w, m.h1b, m.out2, m.out1, m.outBias⟩

theorem swapHidden_semantics (m : TinyNet) (x : Int) :
    predict (swapHidden m) x = predict m x := by
  simp [predict, swapHidden]
  omega

def zero : TinyNet := ⟨0, 0, 0, 0, 0, 0, 0⟩
def first : TinyNet := ⟨2, 1, -1, 1, 1, 0, 0⟩
def complete : TinyNet := ⟨2, 1, -1, 1, 1, 1, 0⟩

theorem two_neuron_improvement_first : accept zero first = true := by decide
theorem two_neuron_improvement_second : accept first complete = true := by decide
theorem completed_model_loss_zero : loss complete = 0 := by decide
theorem original_model_loss : loss zero = 26 := by decide
theorem intermediate_model_loss : loss first = 10 := by decide

theorem two_generations_certified : CertifiedTrace 2 zero complete := by
  exact CertifiedTrace.extend
    (CertifiedTrace.extend (CertifiedTrace.zero zero) two_neuron_improvement_first)
    two_neuron_improvement_second

theorem complete_perfect (x : Int) (hx : x ∈ corpus) : correct complete x := by
  rfl

theorem perfect_cannot_advance (m : TinyNet)
    (h : ∀ x ∈ corpus, correct m x) (candidate : TinyNet) :
    accept m candidate = false := by
  cases hc : accept m candidate with
  | false => rfl
  | true =>
      obtain ⟨x, hx, hwrong, _⟩ := accepted_expands hc
      exact False.elim (hwrong (h x hx))

theorem complete_terminal (candidate : TinyNet) : accept complete candidate = false :=
  perfect_cannot_advance complete complete_perfect candidate

end PCS.V2.ProofGatedMultilayer
