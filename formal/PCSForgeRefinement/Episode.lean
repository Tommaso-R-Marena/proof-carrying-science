import PCSForgeRefinement.Counterexample

/-!
# Learned optimisation episodes: rankings cannot affect acceptance

An untrusted policy proposes candidate certificates in any order (`rank`).  The environment
accepts the first proposal that passes the independent checker `checkCertImproving`; the
reward is the verified static cost reduction, or a fixed penalty.

* `optimize_accept_sound` — whatever the ranking, an accepted result is a checked
  certificate: universal actual-interpreter equivalence and strict static improvement.
* `optimization_episode_reward_sound` — positive reward requires a checked, strictly
  improving, behaviour-preserving certificate; the reward equals the verified cost decrease.
* `optimize_replay` — replaying the accepted certificate re-establishes its theorem.
-/

namespace PCSForgeRefinement

/-- Verified reward: static cost decrease of an accepted certificate, else `-1`. -/
def optReward (c : Cert) : Int :=
  if checkCertImproving c then (programCost c.original : Int) - programCost c.candidate else -1

/-- **Optimisation reward soundness.** -/
theorem optimization_episode_reward_sound {c : Cert} (h : 0 < optReward c) :
    checkCert c = true ∧ programCost c.candidate < programCost c.original ∧
    optReward c = (programCost c.original : Int) - programCost c.candidate ∧
    ∀ inputs, (∀ v ∈ inputs, v.WF) → eval c.candidate inputs = eval c.original inputs := by
  unfold optReward at h ⊢
  split at h
  · rename_i hc
    obtain ⟨h1, h2⟩ := checkCertImproving_sound hc
    exact ⟨h1, h2, by simp [hc], fun i hi => optimization_sequence_preserves_program h1 i hi⟩
  · omega

/-- Proposal order chosen by an arbitrary policy (indices into the proposal list). -/
def optimize (rank : List Nat) (proposals : List Cert) : Option Cert :=
  (rank.filterMap (fun i => proposals[i]?)).find? checkCertImproving

theorem optimize_accept_sound {rank : List Nat} {proposals : List Cert} {c : Cert}
    (h : optimize rank proposals = some c) :
    c ∈ proposals ∧ checkCert c = true ∧ programCost c.candidate < programCost c.original ∧
    ∀ inputs, (∀ v ∈ inputs, v.WF) → eval c.candidate inputs = eval c.original inputs := by
  unfold optimize at h
  have hmem := List.mem_of_find?_eq_some h
  have hok := List.find?_some h
  obtain ⟨i, _, hi⟩ := List.mem_filterMap.1 hmem
  obtain ⟨h1, h2⟩ := checkCertImproving_sound hok
  exact ⟨List.mem_of_getElem? hi, h1, h2, fun inp hw => optimization_sequence_preserves_program h1 inp hw⟩

/-- **Replay**: re-running the checker on an accepted certificate re-establishes the theorem. -/
theorem optimize_replay {rank : List Nat} {proposals : List Cert} {c : Cert}
    (h : optimize rank proposals = some c) : checkCertImproving c = true := by
  unfold optimize at h; exact List.find?_some h

end PCSForgeRefinement
