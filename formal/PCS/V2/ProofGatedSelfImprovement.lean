import Lean

/-! Exact finite-domain reference policy. The trusted deployment root is external. -/
namespace PCS.V2.ProofGatedSelfImprovement

structure Neuron where
  useReLU : Bool
  weight : Int
  bias : Int
  deriving Repr, DecidableEq

def relu (z : Int) : Int := max 0 z

def predict (m : Neuron) (x : Int) : Int :=
  let z := m.weight * x + m.bias
  if m.useReLU then relu z else z

def corpus : List Int := [-3, -2, -1, 0, 1, 2, 3]
def target (x : Int) : Int := relu (2*x + 1)
def correct (m : Neuron) (x : Int) : Prop := predict m x = target x

instance instCorrectDecidable (m : Neuron) (x : Int) : Decidable (correct m x) :=
  inferInstanceAs (Decidable (predict m x = target x))

def loss (m : Neuron) : Nat :=
  (corpus.map (fun x => (predict m x - target x).natAbs)).sum

def preservesB : List Int → Neuron → Neuron → Bool
  | [], _, _ => true
  | x :: xs, a, b => decide (correct a x → correct b x) && preservesB xs a b

def expandsB : List Int → Neuron → Neuron → Bool
  | [], _, _ => false
  | x :: xs, a, b => decide (¬ correct a x ∧ correct b x) || expandsB xs a b

def admissible (a b : Neuron) : Prop :=
  (∀ x ∈ corpus, correct a x → correct b x) ∧
  (∃ x ∈ corpus, ¬ correct a x ∧ correct b x) ∧
  loss b < loss a

def accept (a b : Neuron) : Bool :=
  (preservesB corpus a b && expandsB corpus a b) && decide (loss b < loss a)

private theorem preservesB_sound (xs : List Int) (a b : Neuron)
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
      | inl eq =>
          cases eq
          exact hparts.1
      | inr mem =>
          exact ih hparts.2 x mem

private theorem expandsB_sound (xs : List Int) (a b : Neuron)
    (h : expandsB xs a b = true) :
    ∃ x ∈ xs, ¬ correct a x ∧ correct b x := by
  induction xs with
  | nil =>
      simp [expandsB] at h
  | cons y ys ih =>
      have hparts : (¬ correct a y ∧ correct b y) ∨ expandsB ys a b = true := by
        simpa only [expandsB, Bool.or_eq_true, decide_eq_true_eq] using h
      cases hparts with
      | inl hy =>
          exact ⟨y, by simp, hy⟩
      | inr htail =>
          obtain ⟨x, hx, hc⟩ := ih htail
          exact ⟨x, by simp [hx], hc⟩

theorem accept_sound {a b : Neuron} (h : accept a b = true) :
    admissible a b := by
  simp only [accept, Bool.and_eq_true] at h
  exact ⟨preservesB_sound corpus a b h.1.1,
    expandsB_sound corpus a b h.1.2, (decide_eq_true_eq).mp h.2⟩

theorem accepted_preserves {a b : Neuron} (h : accept a b = true)
    (x : Int) (hx : x ∈ corpus) (ha : correct a x) : correct b x :=
  (accept_sound h).1 x hx ha

theorem accepted_expands {a b : Neuron} (h : accept a b = true) :
    ∃ x ∈ corpus, ¬ correct a x ∧ correct b x :=
  (accept_sound h).2.1

theorem accepted_strict_loss {a b : Neuron} (h : accept a b = true) :
    loss b < loss a := (accept_sound h).2.2

theorem two_accepted_steps {a b c : Neuron}
    (hab : accept a b = true) (hbc : accept b c = true) :
    loss c < loss a :=
  Nat.lt_trans (accepted_strict_loss hbc) (accepted_strict_loss hab)

/-! For arbitrary accepted chains, the exact nonnegative loss is a
    decreasing natural-number potential, bounding how many accepted
    self-modifications may occur. -/
inductive CertifiedTrace : Nat → Neuron → Neuron → Prop where
  | zero (m : Neuron) : CertifiedTrace 0 m m
  | extend {n : Nat} {a b c : Neuron} :
      CertifiedTrace n a b → accept b c = true → CertifiedTrace (n+1) a c

theorem trace_preserves {n : Nat} {a b : Neuron}
    (h : CertifiedTrace n a b) (x : Int) (hx : x ∈ corpus)
    (ha : correct a x) : correct b x := by
  induction h with
  | zero m => exact ha
  | extend hp hc ih => exact accepted_preserves hc x hx (ih ha)

theorem trace_length_bound {n : Nat} {a b : Neuron}
    (h : CertifiedTrace n a b) : n + loss b ≤ loss a := by
  induction h with
  | zero m => simp
  | extend hp hc ih =>
      have hd := accepted_strict_loss hc
      omega

theorem trace_steps_bounded {n : Nat} {a b : Neuron}
    (h : CertifiedTrace n a b) : n ≤ loss a := by
  have hb := trace_length_bound h
  omega

/-! Arbitrarily varying untrusted proposal generators do not change
    the gate's integrity: rejected candidates leave the state unchanged.
    This is monotonic *non-regression*, not guaranteed strict progress. -/
def gatedStep (m proposed : Neuron) : Neuron :=
  if accept m proposed then proposed else m

theorem gatedStep_preserves (m proposed : Neuron) (x : Int)
    (hx : x ∈ corpus) (ha : correct m x) :
    correct (gatedStep m proposed) x := by
  cases h : accept m proposed with
  | false => simpa [gatedStep, h] using ha
  | true =>
      simpa [gatedStep, h] using (accepted_preserves h x hx ha)

theorem gatedStep_loss (m proposed : Neuron) :
    loss (gatedStep m proposed) ≤ loss m := by
  cases h : accept m proposed with
  | false => simp [gatedStep, h]
  | true =>
      simpa [gatedStep, h] using (Nat.le_of_lt (accepted_strict_loss h))

def runStrategies : Neuron → List (Neuron → Neuron) → Neuron
  | m, [] => m
  | m, strategy :: rest =>
      runStrategies (gatedStep m (strategy m)) rest

theorem arbitrary_strategies_preserve (strategies : List (Neuron → Neuron))
    (m : Neuron) (x : Int) (hx : x ∈ corpus) (ha : correct m x) :
    correct (runStrategies m strategies) x := by
  induction strategies generalizing m with
  | nil => simpa [runStrategies] using ha
  | cons strategy rest ih =>
      change correct (runStrategies (gatedStep m (strategy m)) rest) x
      exact ih (gatedStep m (strategy m))
        (gatedStep_preserves m (strategy m) x hx ha)

theorem arbitrary_strategies_nonincrease (strategies : List (Neuron → Neuron))
    (m : Neuron) : loss (runStrategies m strategies) ≤ loss m := by
  induction strategies generalizing m with
  | nil => simp [runStrategies]
  | cons strategy rest ih =>
      change loss (runStrategies (gatedStep m (strategy m)) rest) ≤ loss m
      exact Nat.le_trans (ih (gatedStep m (strategy m)))
        (gatedStep_loss m (strategy m))

theorem perfect_cannot_advance (m : Neuron)
    (hperfect : ∀ x ∈ corpus, correct m x) (candidate : Neuron) :
    accept m candidate = false := by
  cases hc : accept m candidate with
  | false => rfl
  | true =>
      obtain ⟨x, hx, hwrong, _⟩ := accepted_expands hc
      exact False.elim (hwrong (hperfect x hx))

def zero : Neuron := ⟨true, 0, 0⟩
def intermediate : Neuron := ⟨true, 1, 1⟩
def optimum : Neuron := ⟨true, 2, 1⟩
def regressive : Neuron := ⟨true, 1, 2⟩

example : accept zero intermediate = true := by decide
example : accept intermediate optimum = true := by decide
example : accept zero regressive = false := by decide
example : accept optimum zero = false := by decide
example : loss optimum = 0 := by decide

theorem optimum_perfect (x : Int) (_hx : x ∈ corpus) : correct optimum x := by
  rfl

/-! Certified improvement on the frozen finite corpus can still worsen
    the SAME target outside the corpus. This is a checked counterexample,
    not merely an empirical observation. -/
def oodOld : Neuron := ⟨true, 3, -3⟩
def oodCandidate : Neuron := ⟨true, 3, -1⟩

theorem same_target_ood_regression :
    accept oodOld oodCandidate = true ∧
    (predict oodOld 20 - target 20).natAbs <
    (predict oodCandidate 20 - target 20).natAbs := by
  decide

theorem optimum_terminal (candidate : Neuron) : accept optimum candidate = false :=
  perfect_cannot_advance optimum optimum_perfect candidate

end PCS.V2.ProofGatedSelfImprovement

private def parseActivation : String → Option Bool
  | "relu" => some true
  | "linear" => some false
  | _ => none

private def readNeuron (a w b : String) : Option PCS.V2.ProofGatedSelfImprovement.Neuron := do
  let activation ← parseActivation a
  let weight ← w.toInt?
  let bias ← b.toInt?
  if weight < -32 || weight > 32 || bias < -32 || bias > 32 then
    none
  else
    some ⟨activation, weight, bias⟩

def legacyParameterMain (args : List String) : IO UInt32 := do
  match args with
  | [oldA, oldW, oldB, newA, newW, newB] =>
    match readNeuron oldA oldW oldB, readNeuron newA newW newB with
    | some old, some candidate =>
      if PCS.V2.ProofGatedSelfImprovement.accept old candidate then
        IO.println "ACCEPT"
        return 0
      else
        IO.println "REJECT"
        return 1
    | _, _ =>
      IO.println "REJECT:bad_parameters"
      return 2
  | _ =>
    IO.println "REJECT:bad_arity"
    return 2
