import PCSIncremental.Semantics

/-!
# Central soundness theorems for incremental certificate revalidation

`incremental_implies_fresh` derives `FreshValid` on the updated graph from prior
soundness, complete change accounting, new-graph invalidation, and per-node
recheck/reuse premises — without assuming `FreshValid` as a field of
`IncrementalAccept`.
-/

namespace PCSIncremental

/-! ## A. Dependency correctness -/

theorem deps_accounted (g : Graph) (wf : WellFormedIds g) :
    g.depsExist :=
  wf.deps

theorem unique_ids (g : Graph) (wf : WellFormedIds g) :
    g.uniqueIds :=
  wf.unique

theorem acyclic_rejects_self_loops (g : Graph) (tr : TopoRank g)
    (n : Node) (hn : n ∈ g.nodes) : n.id ∉ n.deps :=
  acyclic_no_self_dep g tr n hn

/-! ## B–C. Invalidation -/

theorem invalidation_soundness
    (g : Graph) (changes : ChangeSet) (root leaf : NodeId)
    (hroot : root ∈ changes) (hpath : Downstream g root leaf) :
    Affected g changes leaf :=
  invalidation_sound g changes root leaf hroot hpath

theorem invalidation_completeness
    (g : Graph) (changes : ChangeSet) (leaf : NodeId)
    (h : Affected g changes leaf) :
    ∃ root ∈ changes, Downstream g root leaf :=
  invalidation_complete g changes leaf h

/-! ## D. Safe reuse -/

theorem safe_reuse_preserves_obligation
    (e : CacheEntry) (current : ObligationKey)
    (h : reusePermitted e current) :
    e.key = current ∧ e.priorAccepted = true := by
  refine ⟨h.1, ?_⟩
  simpa [hasAuthority] using h.2

/-! ## E. Central soundness -/

theorem obligation_keys_agree_ops
    (n n0 : Node) (deps deps0 : List Value)
    (h : obligationOf n deps = obligationOf n0 deps0) :
    n.op = n0.op ∧ n.version = n0.version ∧ n.policy = n0.policy ∧ deps = deps0 := by
  have hop := congrArg ObligationKey.op h
  have hver := congrArg ObligationKey.version h
  have hpol := congrArg ObligationKey.policy h
  have hdeps := congrArg ObligationKey.depOutputs h
  exact ⟨hop, hver, hpol, hdeps⟩

/-- Authoritative eligible reuse preserves the local check bit. -/
theorem reuse_entry_checks
    (check : LocalCheck) (vs : ValidState) (w : FreshWitness check vs)
    (n : Node) (σ' : Assignment) (e : CacheEntry)
    (he : e ∈ vs.cache.entries)
    (hperm : reusePermitted e (obligationOf n (depValues n σ'))) :
    check n.op n.version n.policy (depValues n σ') e.cert.payload e.cert.output = true := by
  have hkey : e.key = obligationOf n (depValues n σ') := hperm.1
  have hauth : e.priorAccepted = true := by
    simpa [hasAuthority] using hperm.2
  rcases w.cacheSound e he hauth with ⟨n0, hn0, hkey0, _, hcheck0⟩
  have hagree :=
    obligation_keys_agree_ops n n0 (depValues n σ') (depValues n0 vs.outputs)
      (hkey.symm.trans hkey0)
  rcases hagree with ⟨hop, hver, hpol, hdeps⟩
  have hchk := hcheck0.1
  rw [hop, hver, hpol, hdeps]
  exact hchk

/-- **Substantive incremental soundness:** premises ⇒ `FreshValid` on `g'`. -/
theorem incremental_implies_fresh
    (check : LocalCheck) (vs : ValidState)
    (g' : Graph) (changes : ChangeSet) (σ' : Assignment)
    (certs' : NodeId → Certificate)
    (h : IncrementalAccept check vs g' changes σ' certs') :
    FreshValid check g' σ' certs' := by
  intro n hn
  by_cases ha : Affected g' changes n.id
  · exact h.affectedRechecked n hn ha
  · have hunaff : Unaffected g' changes n.id := ha
    rcases h.unaffectedReused n hn hunaff with ⟨e, he, hperm, hcert, hout⟩
    have hbit := reuse_entry_checks check vs h.prior n σ' e he hperm
    constructor
    · rw [hcert]; exact hbit
    · rw [hcert]; exact hout

theorem incremental_accept_eq_fresh_accept
    (check : LocalCheck) (vs : ValidState)
    (g' : Graph) (changes : ChangeSet) (σ' : Assignment)
    (certs' : NodeId → Certificate) :
    Nonempty (IncrementalAccept check vs g' changes σ' certs') →
      FreshValid check g' σ' certs' := by
  intro ⟨h⟩
  exact incremental_implies_fresh check vs g' changes σ' certs' h

/-- Full-recheck path: every node id is a change seed, so reuse is impossible. -/
def fresh_implies_incremental_full_recheck
    (check : LocalCheck) (vs : ValidState)
    (w : FreshWitness check vs)
    (g' : Graph) (σ' : Assignment) (certs' : NodeId → Certificate)
    (hfresh : FreshValid check g' σ' certs')
    (hids : ∀ n ∈ g'.nodes, ∃ m ∈ vs.graph.nodes, m.id = n.id)
    (hcomplete : ChangesComplete vs.graph g' vs.graph.ids) :
    IncrementalAccept check vs g' vs.graph.ids σ' certs' where
  prior := w
  changesComplete := hcomplete
  idsCovered := hids
  affectedRechecked := fun n hn _ => hfresh n hn
  unaffectedReused := by
    intro n hn hunaff
    have ⟨m, hm, hid⟩ := hids n hn
    have hin : n.id ∈ vs.graph.ids := by
      unfold Graph.ids
      exact List.mem_map.2 ⟨m, hm, hid⟩
    have ha : Affected g' vs.graph.ids n.id :=
      ⟨n.id, hin, Downstream.refl g' n.id⟩
    exact absurd ha hunaff

/-! ## F–J -/

theorem policy_sensitivity
    (k : ObligationKey) (p' : PolicyId) (hne : p' ≠ k.policy) :
    ¬ eligible k { k with policy := p' } :=
  policy_change_breaks_eligibility k p' hne

theorem version_sensitivity
    (k : ObligationKey) (v' : VersionId) (hne : v' ≠ k.version) :
    ¬ eligible k { k with version := v' } :=
  version_change_breaks_eligibility k v' hne

theorem non_escalation
    (e : CacheEntry) (current : ObligationKey)
    (h : e.priorAccepted = false) :
    ¬ reusePermitted e current :=
  no_authority_no_reuse e current h

theorem compositional_fresh
    (check : LocalCheck) (g : Graph) (σ : Assignment)
    (certs : NodeId → Certificate)
    (h : ∀ n ∈ g.nodes, nodeChecks check n σ (certs n.id)) :
    FreshValid check g σ certs :=
  h

theorem compositional_from_local
    (check : LocalCheck) (g : Graph) (σ : Assignment)
    (certs : NodeId → Certificate)
    (h : FreshValid check g σ certs) :
    ∀ n ∈ g.nodes, nodeChecks check n σ (certs n.id) :=
  h

theorem mutation_breaks_dep_eligibility
    (k : ObligationKey) (deps' : List Value) (hne : deps' ≠ k.depOutputs) :
    ¬ eligible k { k with depOutputs := deps' } :=
  dep_output_change_breaks_eligibility k deps' hne

theorem mutation_breaks_evidence_eligibility
    (k : ObligationKey) (e' : EvidenceId) (hne : e' ≠ k.evidence) :
    ¬ eligible k { k with evidence := e' } :=
  evidence_change_breaks_eligibility k e' hne

theorem mutation_safety_no_forgery
    (e : CacheEntry) (current : ObligationKey)
    (hauth : e.priorAccepted = false) :
    ¬ reusePermitted e current :=
  non_escalation e current hauth

theorem valid_state_outputs_agree
    (check : LocalCheck) (vs : ValidState)
    (w : FreshWitness check vs)
    (e : CacheEntry) (he : e ∈ vs.cache.entries)
    (ha : e.priorAccepted = true) :
    ∃ n ∈ vs.graph.nodes,
      e.cert.output = vs.outputs n.id ∧
      nodeChecks check n vs.outputs e.cert := by
  rcases w.cacheSound e he ha with ⟨n, hn, _, hout, hcheck⟩
  exact ⟨n, hn, hout, hcheck⟩

/-- New dependency edges require new-graph invalidation. -/
theorem new_edge_requires_new_graph_invalidation
    (g' : Graph) (changes : ChangeSet) (root leaf : NodeId)
    (hroot : root ∈ changes)
    (hnew : dependsOn g' leaf root) :
    Affected g' changes leaf :=
  ⟨root, hroot, Downstream.cons (Downstream.refl g' root) hnew⟩

/-- Alias: new-edge dependents are Affected on the updated graph. -/
theorem new_dependent_is_affected
    (g' : Graph) (changes : ChangeSet) (root leaf : NodeId)
    (hroot : root ∈ changes)
    (hnew : dependsOn g' leaf root) :
    Affected g' changes leaf :=
  new_edge_requires_new_graph_invalidation g' changes root leaf hroot hnew

end PCSIncremental

#print axioms PCSIncremental.incremental_implies_fresh
#print axioms PCSIncremental.reuse_entry_checks
#print axioms PCSIncremental.invalidation_soundness
#print axioms PCSIncremental.non_escalation
#print axioms PCSIncremental.policy_sensitivity
#print axioms PCSIncremental.version_sensitivity
#print axioms PCSIncremental.safe_reuse_preserves_obligation
#print axioms PCSIncremental.compositional_fresh
#print axioms PCSIncremental.mutation_safety_no_forgery
#print axioms PCSIncremental.affected_least
#print axioms PCSIncremental.new_edge_requires_new_graph_invalidation
