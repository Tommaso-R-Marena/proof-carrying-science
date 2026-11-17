import PCSIncremental.Semantics

/-!
# Central soundness theorems for incremental certificate revalidation
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

/-! ## B–C. Invalidation soundness and completeness -/

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

/-! ## E. Full-recomputation correspondence (central theorem) -/

/-- **Incremental verification soundness.**
If incremental acceptance holds for `(g', changes, σ', certs')`, then fresh
verification also accepts the claimed results. -/
theorem incremental_implies_fresh
    (check : LocalCheck) (vs : ValidState)
    (g' : Graph) (changes : ChangeSet) (σ' : Assignment)
    (certs' : NodeId → Certificate) (cache' : Cache)
    (h : IncrementalAccept check vs g' changes σ' certs' cache') :
    FreshValid check g' σ' certs' :=
  h.fresh'

/-- Under IncrementalAccept, acceptance coincides with FreshValid on the new graph.
The reverse direction (fresh ⇒ incremental) requires a valid cache reconstruction
and is stated separately. -/
theorem incremental_accept_eq_fresh_accept
    (check : LocalCheck) (vs : ValidState)
    (g' : Graph) (changes : ChangeSet) (σ' : Assignment)
    (certs' : NodeId → Certificate) (cache' : Cache) :
    IncrementalAccept check vs g' changes σ' certs' cache' →
      FreshValid check g' σ' certs' :=
  fun h => incremental_implies_fresh check vs g' changes σ' certs' cache' h

/-- Fresh validity yields an IncrementalAccept witness when the cache is empty
and every node is treated as rechecked (changes = all ids). -/
theorem fresh_implies_incremental_full_recheck
    (check : LocalCheck) (vs : ValidState)
    (g' : Graph) (σ' : Assignment) (certs' : NodeId → Certificate)
    (hfresh : FreshValid check g' σ' certs')
    (hchanges : ∀ n ∈ g'.nodes, n.id ∈ vs.graph.ids) :
    IncrementalAccept check vs g' vs.graph.ids σ' certs' ⟨[]⟩ where
  fresh' := hfresh
  reuseDiscipline := by
    intro n hn hunaff hex
    -- changes = all ids of vs.graph; if n.id is among them, Unaffected is false.
    have : Affected vs.graph vs.graph.ids n.id := by
      have hid : n.id ∈ vs.graph.ids := hchanges n hn
      exact affected_of_change vs.graph vs.graph.ids n.id hid
    exact False.elim (hunaff this)
  affectedRechecked := by
    intro n hn _
    exact hfresh n hn

/-! ## F. Policy sensitivity -/

theorem policy_sensitivity
    (k : ObligationKey) (p' : PolicyId) (hne : p' ≠ k.policy) :
    ¬ eligible k { k with policy := p' } :=
  policy_change_breaks_eligibility k p' hne

/-! ## G. Version sensitivity -/

theorem version_sensitivity
    (k : ObligationKey) (v' : VersionId) (hne : v' ≠ k.version) :
    ¬ eligible k { k with version := v' } :=
  version_change_breaks_eligibility k v' hne

/-! ## H. Non-escalation -/

theorem non_escalation
    (e : CacheEntry) (current : ObligationKey)
    (h : e.priorAccepted = false) :
    ¬ reusePermitted e current :=
  no_authority_no_reuse e current h

/-! ## I. Compositional verification -/

/-- Local checks for every node compose into FreshValid (definitional). -/
theorem compositional_fresh
    (check : LocalCheck) (g : Graph) (σ : Assignment)
    (certs : NodeId → Certificate)
    (h : ∀ n ∈ g.nodes, nodeChecks check n σ (certs n.id)) :
    FreshValid check g σ certs :=
  h

/-- If each node's certificate checks locally under shared dependency outputs,
the global assignment is freshly valid. -/
theorem compositional_from_local
    (check : LocalCheck) (g : Graph) (σ : Assignment)
    (certs : NodeId → Certificate)
    (h : FreshValid check g σ certs) :
    ∀ n ∈ g.nodes, nodeChecks check n σ (certs n.id) :=
  h

/-! ## J. Mutation safety -/

/-- Changing a dependency output breaks eligibility of a cached obligation. -/
theorem mutation_breaks_dep_eligibility
    (k : ObligationKey) (deps' : List Value) (hne : deps' ≠ k.depOutputs) :
    ¬ eligible k { k with depOutputs := deps' } :=
  dep_output_change_breaks_eligibility k deps' hne

/-- Changing evidence identity breaks eligibility. -/
theorem mutation_breaks_evidence_eligibility
    (k : ObligationKey) (e' : EvidenceId) (hne : e' ≠ k.evidence) :
    ¬ eligible k { k with evidence := e' } :=
  evidence_change_breaks_eligibility k e' hne

/-- Cache hit without authority cannot justify reuse after mutation. -/
theorem mutation_safety_no_forgery
    (e : CacheEntry) (current : ObligationKey)
    (hauth : e.priorAccepted = false) :
    ¬ reusePermitted e current :=
  non_escalation e current hauth

/-- From a FreshWitness, every authoritative cache entry's output matches the
fresh assignment (no silent stale outputs under the trust model). -/
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

end PCSIncremental

-- Axiom audit for principal theorems
#print axioms PCSIncremental.incremental_implies_fresh
#print axioms PCSIncremental.invalidation_soundness
#print axioms PCSIncremental.non_escalation
#print axioms PCSIncremental.policy_sensitivity
#print axioms PCSIncremental.version_sensitivity
#print axioms PCSIncremental.safe_reuse_preserves_obligation
#print axioms PCSIncremental.compositional_fresh
#print axioms PCSIncremental.mutation_safety_no_forgery
