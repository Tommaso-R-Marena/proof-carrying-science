import PCSIncremental.Soundness

/-!
# Executable incremental algorithms (kernel-checked)

`computeChanges` derives a complete change seed set from two graphs (proved).
`affectedClosure` is a fuel-bounded reverse-dependency expansion.
`runIncremental` computes changes internally (does not trust a caller change list).

`incremental_run_sound`: LogicalAccept ⇒ FreshValid (does not store FreshValid
in RunResult). Bridging a concrete ok-run to LogicalAccept remains operational.
-/

namespace PCSIncremental

/-! ## Change detection -/

def hasDefnDiff (g : Graph) (n' : Node) : Bool :=
  (g.nodes.filter (fun n => decide (n.id = n'.id))).any (fun n => !(sameDefnB n n'))

/-- Seed ids that are new or definitionally changed relative to `g`. -/
def computeChanges (g g' : Graph) : ChangeSet :=
  g'.nodes.filterMap fun n' =>
    match g.nodes.filter (fun n => decide (n.id = n'.id)) with
    | [] => some n'.id
    | _ => if hasDefnDiff g n' then some n'.id else none

theorem computeChanges_complete (g g' : Graph) :
    ChangesComplete g g' (computeChanges g g') := by
  intro n' hn' n hn hid hdiff
  unfold computeChanges
  refine List.mem_filterMap.2 ⟨n', hn', ?_⟩
  have hpriors_mem :
      n ∈ g.nodes.filter (fun x => decide (x.id = n'.id)) :=
    List.mem_filter.2 ⟨hn, by simp [hid]⟩
  have hdiffB : sameDefnB n n' = false := by
    cases hsb : sameDefnB n n' with
    | false => rfl
    | true => exact absurd ((sameDefnB_iff n n').1 hsb) hdiff
  have hany : hasDefnDiff g n' = true :=
    List.any_eq_true.2 ⟨n, hpriors_mem, by simp [hdiffB]⟩
  match hpriors : g.nodes.filter (fun x => decide (x.id = n'.id)) with
  | [] =>
      have : n ∈ ([] : List Node) := by simpa [hpriors] using hpriors_mem
      cases this
  | p :: ps =>
      simp [hpriors, hany]

theorem computeChanges_seeds_new
    (g g' : Graph) (n' : Node) (hn' : n' ∈ g'.nodes)
    (hnew : ∀ n ∈ g.nodes, n.id ≠ n'.id) :
    n'.id ∈ computeChanges g g' := by
  unfold computeChanges
  refine List.mem_filterMap.2 ⟨n', hn', ?_⟩
  have hempty : g.nodes.filter (fun n => decide (n.id = n'.id)) = [] := by
    apply List.eq_nil_iff_forall_not_mem.2
    intro x hx
    rcases List.mem_filter.1 hx with ⟨hxg, hdec⟩
    exact (hnew x hxg) (of_decide_eq_true hdec)
  simp [hempty]

/-! ## Affected closure -/

def expandAffected (g : Graph) (frontier : List NodeId) : List NodeId :=
  frontier.flatMap (collectDependents g)

def affectedClosureFuel (g : Graph) (seeds : List NodeId) : Nat → List NodeId
  | 0 => seeds
  | fuel + 1 =>
      let cur := affectedClosureFuel g seeds fuel
      cur ++ expandAffected g cur

def affectedClosure (g : Graph) (seeds : ChangeSet) : List NodeId :=
  affectedClosureFuel g seeds (g.nodes.length + 1)

theorem mem_seeds_mem_affectedClosureFuel
    (g : Graph) (seeds : List NodeId) (fuel : Nat) (id : NodeId)
    (h : id ∈ seeds) :
    id ∈ affectedClosureFuel g seeds fuel := by
  induction fuel with
  | zero => simpa [affectedClosureFuel] using h
  | succ fuel ih =>
      simp [affectedClosureFuel, List.mem_append]
      exact Or.inl ih

theorem mem_affectedClosure_of_change
    (g : Graph) (changes : ChangeSet) (id : NodeId) (h : id ∈ changes) :
    id ∈ affectedClosure g changes :=
  mem_seeds_mem_affectedClosureFuel g changes (g.nodes.length + 1) id h

theorem affectedClosure_sound_seeds
    (g : Graph) (changes : ChangeSet) (id : NodeId)
    (h : id ∈ changes) :
    Affected g changes id :=
  affected_of_change g changes id h

theorem collectDependents_implies_dependsOn
    (g : Graph) (prior next : NodeId)
    (hdep : next ∈ collectDependents g prior) :
    dependsOn g next prior := by
  unfold collectDependents at hdep
  rcases List.mem_filterMap.1 hdep with ⟨n, hn, hopt⟩
  by_cases hp : prior ∈ n.deps
  · simp [hp] at hopt
    exact ⟨n, hn, hopt, hp⟩
  · simp [hp] at hopt

theorem affectedClosure_step_sound
    (g : Graph) (changes : ChangeSet) (prior next : NodeId)
    (hp : Affected g changes prior)
    (hdep : next ∈ collectDependents g prior) :
    Affected g changes next :=
  affected_step g changes prior next hp
    (collectDependents_implies_dependsOn g prior next hdep)

/-! ## Incremental run -/

structure RunResult where
  accepted : Bool
  changes : ChangeSet
  affected : List NodeId
  reused : List NodeId
  rechecked : List NodeId
  outputs : List (NodeId × Value)
  certificates : List (NodeId × Certificate)
  error : Option String
  deriving Repr

def assignOf (outs : List (NodeId × Value)) : Assignment :=
  fun id => match outs.find? (fun p => decide (p.1 = id)) with
            | some (_, v) => v
            | none => 0

def tryReuse (cache : Cache) (key : ObligationKey) : Option Certificate :=
  match cache.lookup key with
  | none => none
  | some e => if e.priorAccepted then some e.cert else none

def stepNode
    (check : LocalCheck)
    (cache : Cache)
    (affected : List NodeId)
    (mkCert : Node → List Value → Option Certificate)
    (n : Node)
    (depVals : List Value) : Option (Value × Certificate × Bool) :=
  let key := obligationOf n depVals
  if decide (n.id ∈ affected) then
    match mkCert n depVals with
    | none => none
    | some c =>
        if check n.op n.version n.policy n.evidence depVals c.payload c.output then
          some (c.output, c, false)
        else none
  else
    match tryReuse cache key with
    | some c =>
        if check n.op n.version n.policy n.evidence depVals c.payload c.output then
          some (c.output, c, true)
        else
          match mkCert n depVals with
          | none => none
          | some c2 =>
              if check n.op n.version n.policy n.evidence depVals c2.payload c2.output then
                some (c2.output, c2, false)
              else none
    | none =>
        match mkCert n depVals with
        | none => none
        | some c =>
            if check n.op n.version n.policy n.evidence depVals c.payload c.output then
              some (c.output, c, false)
            else none

def runNodes
    (check : LocalCheck)
    (cache : Cache)
    (affected : List NodeId)
    (mkCert : Node → List Value → Option Certificate) :
    List Node → List (NodeId × Value) → List (NodeId × Certificate) →
      List NodeId → List NodeId →
      Option (List (NodeId × Value) × List (NodeId × Certificate) × List NodeId × List NodeId)
  | [], outs, certs, reused, rechecked =>
      some (outs, certs, reused, rechecked)
  | n :: rest, outs, certs, reused, rechecked =>
      let deps := depValues n (assignOf outs)
      match stepNode check cache affected mkCert n deps with
      | none => none
      | some (v, c, didReuse) =>
          runNodes check cache affected mkCert rest
            (outs ++ [(n.id, v)])
            (certs ++ [(n.id, c)])
            (if didReuse then reused ++ [n.id] else reused)
            (if didReuse then rechecked else rechecked ++ [n.id])

/-- Core body given precomputed changes/affected. -/
def runIncrementalBody
    (check : LocalCheck)
    (vs : ValidState)
    (topo : List Node)
    (mkCert : Node → List Value → Option Certificate)
    (changes : ChangeSet)
    (affected : List NodeId)
    (topoOk : Bool) : RunResult :=
  if topoOk then
    match runNodes check vs.cache affected mkCert topo [] [] [] [] with
    | none =>
        { accepted := false, changes, affected, reused := [], rechecked := [],
          outputs := [], certificates := [], error := some "node check failed" }
    | some (outs, certs, reused, rechecked) =>
        { accepted := true, changes, affected, reused, rechecked,
          outputs := outs, certificates := certs, error := none }
  else
    { accepted := false, changes, affected, reused := [], rechecked := [],
      outputs := [], certificates := [], error := some "topo length mismatch" }

/-- Concrete incremental algorithm: changes are computed, not caller-trusted. -/
def runIncremental
    (check : LocalCheck)
    (vs : ValidState)
    (g' : Graph)
    (topo : List Node)
    (mkCert : Node → List Value → Option Certificate) : RunResult :=
  let changes := computeChanges vs.graph g'
  let affected := affectedClosure g' changes
  let topoOk := decide (topo.length = g'.nodes.length)
  runIncrementalBody check vs topo mkCert changes affected topoOk

theorem runIncrementalBody_changes
    (check : LocalCheck) (vs : ValidState) (topo : List Node)
    (mkCert : Node → List Value → Option Certificate)
    (changes : ChangeSet) (affected : List NodeId) (topoOk : Bool) :
    (runIncrementalBody check vs topo mkCert changes affected topoOk).changes = changes := by
  unfold runIncrementalBody
  split <;> (try split) <;> rfl

theorem runIncremental_changes_eq
    (check : LocalCheck) (vs : ValidState) (g' : Graph)
    (topo : List Node) (mkCert : Node → List Value → Option Certificate) :
    (runIncremental check vs g' topo mkCert).changes = computeChanges vs.graph g' := by
  simp [runIncremental, runIncrementalBody_changes]

theorem runIncremental_changes_complete
    (check : LocalCheck) (vs : ValidState) (g' : Graph)
    (topo : List Node) (mkCert : Node → List Value → Option Certificate) :
    ChangesComplete vs.graph g' (runIncremental check vs g' topo mkCert).changes := by
  rw [runIncremental_changes_eq]
  exact computeChanges_complete vs.graph g'

theorem incremental_run_sound
    (check : LocalCheck) (vs : ValidState)
    (g' : Graph) (changes : ChangeSet) (σ' : Assignment)
    (certs' : NodeId → Certificate)
    (h : LogicalAccept check vs g' changes σ' certs') :
    FreshValid check g' σ' certs' :=
  logical_implies_fresh check vs g' changes σ' certs' h

end PCSIncremental

#print axioms PCSIncremental.computeChanges_complete
#print axioms PCSIncremental.computeChanges_seeds_new
#print axioms PCSIncremental.incremental_run_sound
#print axioms PCSIncremental.runIncremental_changes_complete
#print axioms PCSIncremental.affectedClosure_step_sound
#print axioms PCSIncremental.collectDependents_implies_dependsOn
