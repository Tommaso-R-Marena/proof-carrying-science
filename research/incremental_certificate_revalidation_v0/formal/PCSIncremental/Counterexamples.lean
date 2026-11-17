import PCSIncremental.Soundness

/-!
# Counterexamples: naive cache acceptance is unsound

These examples show why lookup ≠ eligibility ≠ authority.
-/
namespace PCSIncremental

/-- A forged cache entry with matching key but `priorAccepted = false`. -/
def forgedEntry (k : ObligationKey) (c : Certificate) : CacheEntry :=
  { key := k, cert := c, priorAccepted := false }

theorem forged_cannot_reuse (k : ObligationKey) (c : Certificate) :
    ¬ reusePermitted (forgedEntry k c) k :=
  no_authority_no_reuse (forgedEntry k c) k rfl

/-- Stale policy: same payload/output but different policy breaks eligibility. -/
def stalePolicyKey (k : ObligationKey) (p' : PolicyId) : ObligationKey :=
  { k with policy := p' }

theorem stale_policy_not_eligible
    (k : ObligationKey) (p' : PolicyId) (hne : p' ≠ k.policy) :
    ¬ eligible k (stalePolicyKey k p') :=
  policy_change_breaks_eligibility k p' hne

/-- Stale version reuse attempt. -/
theorem stale_version_not_eligible
    (k : ObligationKey) (v' : VersionId) (hne : v' ≠ k.version) :
    ¬ eligible k { k with version := v' } :=
  version_change_breaks_eligibility k v' hne

/-- Dependency surgery: changing dep outputs breaks eligibility even if payload matches. -/
theorem dependency_surgery_breaks
    (k : ObligationKey) (deps' : List Value) (hne : deps' ≠ k.depOutputs) :
    ¬ eligible k { k with depOutputs := deps' } :=
  dep_output_change_breaks_eligibility k deps' hne

/-- Concrete numeric illustration. -/
def demoKey : ObligationKey :=
  { id := 1, op := 10, policy := 1, version := 1, evidence := 0, depOutputs := [2, 3] }

def demoCert : Certificate := { payload := 99, output := 5 }

theorem demo_forged_rejected :
    ¬ reusePermitted (forgedEntry demoKey demoCert) demoKey :=
  forged_cannot_reuse demoKey demoCert

theorem demo_policy_swap_rejected :
    ¬ eligible demoKey (stalePolicyKey demoKey 2) :=
  stale_policy_not_eligible demoKey 2 (by decide)

theorem demo_dep_swap_rejected :
    ¬ eligible demoKey { demoKey with depOutputs := [2, 4] } :=
  dependency_surgery_breaks demoKey [2, 4] (by decide)

/-- Lookup alone is not validity: existence of an entry is not `reusePermitted`
without authority. -/
theorem lookup_not_validity (k : ObligationKey) (c : Certificate) :
    (forgedEntry k c).key = k ∧ ¬ reusePermitted (forgedEntry k c) k :=
  ⟨rfl, forged_cannot_reuse k c⟩

end PCSIncremental

#print axioms PCSIncremental.demo_forged_rejected
#print axioms PCSIncremental.demo_policy_swap_rejected
#print axioms PCSIncremental.lookup_not_validity
