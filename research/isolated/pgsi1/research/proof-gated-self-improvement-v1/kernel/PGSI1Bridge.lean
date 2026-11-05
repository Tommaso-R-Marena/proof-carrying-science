import IntegerAffine
import PCS.V2.ProofGatedSelfImprovement

/-! Research-only mathematical composition; never imported by PCS authority.
This relates the new exact network semantics to the unchanged PGSI1 neuron
specification. Serialization/native/OS implementation refinement is not proved.
-/
namespace PCS.Research.PGSI1Bridge
open IntegerAffine
open PCS.V2

def embed (n : ProofGatedSelfImprovement.Neuron) : Net :=
  if n.useReLU then ⟨[⟨1, n.weight, n.bias⟩], 0⟩
  else ⟨[⟨1, n.weight, n.bias⟩, ⟨-1, -n.weight, -n.bias⟩], 0⟩

theorem embed_predict (n : ProofGatedSelfImprovement.Neuron) (x : Int) : predict (embed n) x = ProofGatedSelfImprovement.predict n x := by
  cases n with
  | mk r w b =>
    cases r <;> by_cases hz : 0 ≤ w*x+b <;>
      simp [embed, predict, termsValue, termValue, relu, ProofGatedSelfImprovement.predict, ProofGatedSelfImprovement.relu,
        Int.neg_mul, Int.max_def] <;> omega

def targetNet : Net := ⟨[⟨1, 2, 1⟩], 0⟩

theorem target_predict (x : Int) : predict targetNet x = ProofGatedSelfImprovement.target x := by
  by_cases hz : 0 ≤ 2*x+1 <;>
    simp [targetNet, predict, termsValue, termValue, relu, ProofGatedSelfImprovement.target, ProofGatedSelfImprovement.relu,
      Int.max_def] <;> omega

def guardAccept (a b : ProofGatedSelfImprovement.Neuron) (preservation oldRows newRows : List Row)
    (l h : Int) (oldMax newMax : Nat) (oldPeak newPeak witness : Int) : Bool :=
  ProofGatedSelfImprovement.accept a b && acceptNonvacuous (embed a) (embed b) targetNet preservation witness &&
  acceptMaximum (embed a) targetNet oldRows l h oldMax oldPeak &&
  acceptMaximum (embed b) targetNet newRows l h newMax newPeak &&
  decide (newMax ≤ oldMax)

theorem guardAccept_sound (a b : ProofGatedSelfImprovement.Neuron) (preservation oldRows newRows : List Row)
    (l h : Int) (oldMax newMax : Nat) (oldPeak newPeak witness : Int)
    (ha : guardAccept a b preservation oldRows newRows l h oldMax newMax oldPeak newPeak witness = true) :
    ProofGatedSelfImprovement.admissible a b ∧
    (∀ x : Int, ProofGatedSelfImprovement.correct a x → ProofGatedSelfImprovement.correct b x) ∧
    ProofGatedSelfImprovement.correct a witness ∧
    (∀ x : Int, l ≤ x → x ≤ h → (ProofGatedSelfImprovement.predict a x - ProofGatedSelfImprovement.target x).natAbs ≤ oldMax) ∧
    (ProofGatedSelfImprovement.predict a oldPeak - ProofGatedSelfImprovement.target oldPeak).natAbs = oldMax ∧
    (∀ x : Int, l ≤ x → x ≤ h → (ProofGatedSelfImprovement.predict b x - ProofGatedSelfImprovement.target x).natAbs ≤ newMax) ∧
    (ProofGatedSelfImprovement.predict b newPeak - ProofGatedSelfImprovement.target newPeak).natAbs = newMax ∧
    newMax ≤ oldMax ∧ l ≤ oldPeak ∧ oldPeak ≤ h ∧ l ≤ newPeak ∧ newPeak ≤ h := by
  have hp : (((ProofGatedSelfImprovement.accept a b = true ∧
      acceptNonvacuous (embed a) (embed b) targetNet preservation witness = true) ∧
      acceptMaximum (embed a) targetNet oldRows l h oldMax oldPeak = true) ∧
      acceptMaximum (embed b) targetNet newRows l h newMax newPeak = true) ∧
      newMax ≤ oldMax := by
    simpa only [guardAccept, Bool.and_eq_true, decide_eq_true_eq] using ha
  have hn := acceptNonvacuous_sound _ _ _ _ _ hp.1.1.1.2
  have ho := acceptMaximum_sound _ _ _ _ _ _ _ hp.1.1.2
  have hb := acceptMaximum_sound _ _ _ _ _ _ _ hp.1.2
  simp only [embed_predict, target_predict] at hn ho hb
  exact ⟨ProofGatedSelfImprovement.accept_sound hp.1.1.1.1, hn.1, hn.2, ho.1, ho.2.2.2,
    hb.1, hb.2.2.2, hp.2, ho.2.1, ho.2.2.1, hb.2.1, hb.2.2.1⟩

structure GuardCase where
  old : ProofGatedSelfImprovement.Neuron
  new : ProofGatedSelfImprovement.Neuron
  preservation : List Row
  oldRows : List Row
  newRows : List Row
  low : Int
  high : Int
  oldMax : Nat
  newMax : Nat
  oldPeak : Int
  newPeak : Int
  witness : Int

def checkGuardCase (c : GuardCase) : Bool :=
  guardAccept c.old c.new c.preservation c.oldRows c.newRows
    c.low c.high c.oldMax c.newMax c.oldPeak c.newPeak c.witness

def GuardMeaning (c : GuardCase) : Prop :=
  ProofGatedSelfImprovement.admissible c.old c.new ∧
  (∀ x : Int, ProofGatedSelfImprovement.correct c.old x → ProofGatedSelfImprovement.correct c.new x) ∧
  ProofGatedSelfImprovement.correct c.old c.witness ∧
  c.low ≤ c.oldPeak ∧ c.oldPeak ≤ c.high ∧
  (∀ x : Int, c.low ≤ x → x ≤ c.high →
    (ProofGatedSelfImprovement.predict c.old x - ProofGatedSelfImprovement.target x).natAbs ≤
    (ProofGatedSelfImprovement.predict c.old c.oldPeak - ProofGatedSelfImprovement.target c.oldPeak).natAbs) ∧
  (∀ x : Int, c.low ≤ x → x ≤ c.high →
    (ProofGatedSelfImprovement.predict c.new x - ProofGatedSelfImprovement.target x).natAbs ≤
    (ProofGatedSelfImprovement.predict c.old c.oldPeak - ProofGatedSelfImprovement.target c.oldPeak).natAbs)

theorem checkGuardCase_sound (c : GuardCase) (h : checkGuardCase c = true) : GuardMeaning c := by
  have hp := guardAccept_sound c.old c.new c.preservation c.oldRows c.newRows
    c.low c.high c.oldMax c.newMax c.oldPeak c.newPeak c.witness h
  rcases hp with ⟨hadm, hpres, hw, hold, hpeak, hnew, _, hm, hlo, hhi, _, _⟩
  refine ⟨hadm, hpres, hw, hlo, hhi, ?_, ?_⟩
  · intro x hl hh
    rw [hpeak]
    exact hold x hl hh
  · intro x hl hh
    rw [hpeak]
    exact Nat.le_trans (hnew x hl hh) hm

theorem checkGuardBatch_sound (cases : List GuardCase) (h : cases.all checkGuardCase = true) :
    ∀ c ∈ cases, GuardMeaning c := by
  intro c hc
  exact checkGuardCase_sound c (List.all_eq_true.mp h c hc)

end PCS.Research.PGSI1Bridge
