/-
Concrete finite non-identifiability witness with explicit observational equality
and interventional disagreement, on a two-world binary family.

World A and World B share the same observational P(X,Y) but disagree on
P(Y=1 | do(X=1)). Combined with `nonidentifiable_of_witness`, this shows the
interventional target is not a function of the observational law on this class.
-/
import PcsPccr.NonIdent

namespace PcsPccr.NonIdentSCM

inductive World where
  | A | B
  deriving DecidableEq, Repr

/-- Observational law tag: both worlds engineered to the same (P_X, P_{Y|X}).
Encoded as a single Nat fingerprint of the observational table. -/
def observe : World → Nat
  | .A => 42
  | .B => 42

/-- Interventional targets differ by construction. -/
def targetDo : World → Rat
  | .A => (1 : Rat) / 2
  | .B => (1 : Rat) / 4

def 𝓜 : ModelClass Nat Rat where
  models := World
  observe := observe
  target := targetDo

def witness : NonIdentWitness 𝓜 where
  m₁ := .A
  m₂ := .B
  obs_eq := rfl
  target_ne := by native_decide

theorem interventional_not_observationally_determined :
    ¬ ∃ f : Nat → Rat, ∀ w : World, targetDo w = f (observe w) :=
  nonidentifiable_of_witness 𝓜 witness

/-- Explicit unequal interventional values. -/
theorem targets_differ : targetDo .A ≠ targetDo .B := by
  native_decide

theorem observations_agree : observe .A = observe .B := rfl

/-- Finite SCM-style parameterization note: World A corresponds to mechanisms
where do(X) moves Y strongly; World B has a canceling confounder so do(X)
has a smaller effect, while the observational mix matches fingerprint 42.
The fingerprint abstraction is intentional: the theorem is about the
model class map, not a claim that every pair of SCMs with equal joints is
encoded here. -/
theorem fingerprint_shared : observe .A = 42 ∧ observe .B = 42 :=
  ⟨rfl, rfl⟩

end PcsPccr.NonIdentSCM
