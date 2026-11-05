/-!
# Heterogeneous proof-obligation graphs (Claim IR) and root-assurance soundness

A PCS claim is discharged by a *proof-obligation graph*: every node carries a typed claim
(an element of an arbitrary claim-IR type `C`) and is either

* a **leaf** carrying an obligation `ob : L` (formal proof, computational replay, empirical
  validation, external receipt, … — `L` is arbitrary, and `Checker.sumLeaf` combines
  validators for heterogeneous leaf kinds), or
* a **derivation** node naming a decomposition rule and the ids of its children, or
* an explicitly **unsupported** node (always rejected).

The graph is *untrusted data*: it may be produced by the package author, by the domain
adapter, or by an external proposer (see `PCS.V2.Proposer`).  Only the `Checker` is
trusted, and only through the two local soundness obligations of `CheckerSound`:

* `leaf`  — a leaf obligation that the validator accepts for a claim denotes that claim;
* `rule`  — a decomposition rule accepted by the rule checker is semantics-preserving
  (all child claims true ⇒ parent claim true).

`checkGraph V g goal` is the deterministic graph checker.  It **rejects**

* duplicate node ids (`Nodup` check),
* a missing root, or a root whose claim is not the expected `goal` (wrong claim binding),
* a reference to a missing child (unresolved obligation),
* an `unsupported` node,
* a leaf whose validator does not accept the leaf's *own* claim
  (so an accepted leaf can never stand for a different proposition than the one its
  parent's rule check consumed),
* any cycle reachable from the root (a node met again on the current path),
* any graph deeper than its number of nodes (fuel).

Main results:

* `root_assurance_sound` — acceptance + `CheckerSound` ⇒ the root claim's semantics.
* `accepted_graph_facts` — acceptance alone ⇒ duplicate-free ids, root bound to `goal`,
  every reachable node present and supported, every reachable derivation's children
  present and its rule check passing, every reachable leaf discharged, and **no cycle
  through any reachable node**.

The file depends only on Lean core.
-/

set_option autoImplicit false

namespace PCS.V2.ClaimGraph

/-- What a node is. -/
inductive NodeKind (L : Type) where
  /-- a leaf discharged by an obligation validator -/
  | leaf (ob : L)
  /-- an internal decomposition / derivation step -/
  | derive (rule : String) (children : List String)
  /-- an explicitly unsupported node (never accepted) -/
  | unsupported (tag : String)

/-- A node of the obligation graph. -/
structure Node (L C : Type) where
  id : String
  claim : C
  kind : NodeKind L

/-- An (untrusted) obligation graph with a designated root. -/
structure Graph (L C : Type) where
  nodes : List (Node L C)
  root : String

variable {L C : Type}

/-- Node lookup by id (first match; duplicates are rejected by `checkGraph` anyway). -/
def Graph.find (g : Graph L C) (i : String) : Option (Node L C) :=
  g.nodes.find? (fun n => n.id == i)

/-- Claims of the listed children; `none` if any child is missing. -/
def Graph.findAll (g : Graph L C) : List String → Option (List C)
  | [] => some []
  | i :: is =>
    match g.find i, g.findAll is with
    | some n, some cs => some (n.claim :: cs)
    | _, _ => none

/-- The trusted part: an obligation validator and a decomposition-rule checker. -/
structure Checker (L C : Type) where
  /-- does obligation `ob` discharge claim `c`? -/
  leaf : L → C → Bool
  /-- is rule `r` a valid derivation of parent claim `p` from child claims `cs`? -/
  rule : String → C → List C → Bool

/-- **The local soundness obligations** of a checker w.r.t. a claim semantics. -/
structure CheckerSound (V : Checker L C) (Sem : C → Prop) : Prop where
  leaf : ∀ ob c, V.leaf ob c = true → Sem c
  rule : ∀ r p cs, V.rule r p cs = true → (∀ c ∈ cs, Sem c) → Sem p

/-- Recursive, fuel-bounded, cycle-detecting evaluation of node `i` with current
    ancestor path `path`. -/
def evalNode (V : Checker L C) (g : Graph L C) : Nat → List String → String → Bool
  | 0, _, _ => false
  | n + 1, path, i =>
    if path.contains i then false else
    match g.find i with
    | none => false
    | some nd =>
      match nd.kind with
      | .leaf ob => V.leaf ob nd.claim
      | .derive r chs =>
        match g.findAll chs with
        | none => false
        | some cs => V.rule r nd.claim cs && chs.all (fun ch => evalNode V g n (i :: path) ch)
      | .unsupported _ => false

/-- Is the root present and bound to the expected claim? -/
def rootBoundB [DecidableEq C] (g : Graph L C) (goal : C) : Bool :=
  match g.find g.root with
  | some nd => decide (nd.claim = goal)
  | none => false

/-- **The graph checker**: unique ids, root bound to `goal`, recursive evaluation. -/
def checkGraph [DecidableEq C] (V : Checker L C) (g : Graph L C) (goal : C) : Bool :=
  decide ((g.nodes.map (·.id)).Nodup) && rootBoundB g goal &&
    evalNode V g g.nodes.length [] g.root

/-! ## Basic lemmas -/

theorem find_id {g : Graph L C} {i : String} {nd : Node L C} (h : g.find i = some nd) :
    nd.id = i := by
  have := List.find?_some h
  simpa using this

theorem find_mem {g : Graph L C} {i : String} {nd : Node L C} (h : g.find i = some nd) :
    nd ∈ g.nodes :=
  List.mem_of_find?_eq_some h

theorem findAll_spec {g : Graph L C} :
    ∀ {chs : List String} {cs : List C}, g.findAll chs = some cs →
      ∀ c ∈ cs, ∃ i ∈ chs, ∃ nd, g.find i = some nd ∧ nd.claim = c
  | [], cs, h, c, hc => by
    simp only [Graph.findAll, Option.some.injEq] at h
    subst h; cases hc
  | i :: is, cs, h, c, hc => by
    simp only [Graph.findAll] at h
    split at h
    · rename_i n cs' hn hcs
      cases h
      simp only [List.mem_cons] at hc
      rcases hc with rfl | hc
      · exact ⟨i, List.mem_cons_self, n, hn, rfl⟩
      · obtain ⟨j, hj, nd, hnd, hc'⟩ := findAll_spec hcs c hc
        exact ⟨j, List.mem_cons_of_mem _ hj, nd, hnd, hc'⟩
    · cases h

/-- What a successful evaluation says about the node itself. -/
def LocalOK (V : Checker L C) (g : Graph L C) (nd : Node L C) : Prop :=
  match nd.kind with
  | .leaf ob => V.leaf ob nd.claim = true
  | .derive r chs => ∃ cs, g.findAll chs = some cs ∧ V.rule r nd.claim cs = true
  | .unsupported _ => False

theorem evalNode_local {V : Checker L C} {g : Graph L C} {n : Nat} {path : List String}
    {i : String} (h : evalNode V g n path i = true) :
    i ∉ path ∧ ∃ nd, g.find i = some nd ∧ LocalOK V g nd := by
  cases n with
  | zero => simp [evalNode] at h
  | succ n =>
    simp only [evalNode] at h
    split at h
    · cases h
    · rename_i hp
      refine ⟨fun hm => hp (by simpa using hm), ?_⟩
      split at h
      · cases h
      · rename_i nd hnd
        refine ⟨nd, hnd, ?_⟩
        unfold LocalOK
        split at h
        · exact h
        · split at h
          · cases h
          · rename_i cs hcs
            simp only [Bool.and_eq_true] at h
            exact ⟨cs, hcs, h.1⟩
        · cases h

/-- Successful evaluation of a derivation node evaluates every child, one level deeper,
    with the node pushed on the path. -/
theorem evalNode_child {V : Checker L C} {g : Graph L C} {n : Nat} {path : List String}
    {i : String} (h : evalNode V g n path i = true) {nd : Node L C} (hnd : g.find i = some nd)
    {r : String} {chs : List String} (hk : nd.kind = .derive r chs) {ch : String}
    (hch : ch ∈ chs) : ∃ m, n = m + 1 ∧ evalNode V g m (i :: path) ch = true := by
  cases n with
  | zero => simp [evalNode] at h
  | succ m =>
    refine ⟨m, rfl, ?_⟩
    simp only [evalNode] at h
    split at h
    · cases h
    · rw [hnd] at h
      simp only at h
      rw [hk] at h
      simp only at h
      split at h
      · cases h
      · simp only [Bool.and_eq_true, List.all_eq_true] at h
        exact h.2 ch hch

/-! ## Root-assurance soundness -/

/-- Every successfully evaluated node's claim holds. -/
theorem evalNode_sound {V : Checker L C} {Sem : C → Prop} (hV : CheckerSound V Sem)
    (g : Graph L C) :
    ∀ n path i, evalNode V g n path i = true → ∃ nd, g.find i = some nd ∧ Sem nd.claim := by
  intro n
  induction n with
  | zero => intro path i h; simp [evalNode] at h
  | succ n ih =>
    intro path i h
    simp only [evalNode] at h
    split at h
    · cases h
    · split at h
      · cases h
      · rename_i nd hnd
        refine ⟨nd, hnd, ?_⟩
        split at h
        · rename_i ob _
          exact hV.leaf ob nd.claim h
        · rename_i r chs _
          split at h
          · cases h
          · rename_i cs hcs
            simp only [Bool.and_eq_true, List.all_eq_true] at h
            apply hV.rule r nd.claim cs h.1
            intro c hc
            obtain ⟨j, hj, nj, hnj, rfl⟩ := findAll_spec hcs c hc
            obtain ⟨nj', hnj', hsem⟩ := ih (i :: path) j (h.2 j hj)
            rw [hnj] at hnj'
            cases hnj'
            exact hsem
        · cases h

/-- **Root-assurance soundness.**  If the graph checker accepts `g` for the expected root
    claim `goal`, and the trusted checker satisfies its local leaf/rule soundness
    obligations, then the semantic proposition of `goal` holds.  Nothing is assumed about
    who produced `g`. -/
theorem root_assurance_sound [DecidableEq C] {V : Checker L C} {Sem : C → Prop}
    (hV : CheckerSound V Sem) {g : Graph L C} {goal : C}
    (h : checkGraph V g goal = true) : Sem goal := by
  simp only [checkGraph, Bool.and_eq_true] at h
  obtain ⟨⟨_, hroot⟩, heval⟩ := h
  obtain ⟨nd, hnd, hsem⟩ := evalNode_sound hV g _ _ _ heval
  unfold rootBoundB at hroot
  rw [hnd] at hroot
  simp only [decide_eq_true_eq] at hroot
  rw [← hroot]; exact hsem

/-! ## Structural guarantees of acceptance (no soundness assumption) -/

/-- A derivation edge `a → b` of the graph. -/
def Edge (g : Graph L C) (a b : String) : Prop :=
  ∃ nd r chs, g.find a = some nd ∧ nd.kind = .derive r chs ∧ b ∈ chs

/-- Reflexive-transitive reachability along derivation edges. -/
inductive Reach (g : Graph L C) : String → String → Prop
  | refl (a : String) : Reach g a a
  | step {a b c : String} : Edge g a b → Reach g b c → Reach g a c

theorem evalNode_reach {V : Checker L C} {g : Graph L C} {a x : String} (hr : Reach g a x) :
    ∀ {n path}, evalNode V g n path a = true →
      ∃ m p, evalNode V g m p x = true ∧ ∀ y ∈ path, y ∈ p := by
  induction hr with
  | refl a => intro n path h; exact ⟨n, path, h, fun _ hy => hy⟩
  | step he _ ih =>
    intro n path h
    obtain ⟨nd, r, chs, hnd, hk, hb⟩ := he
    obtain ⟨m, _, hm⟩ := evalNode_child h hnd hk hb
    obtain ⟨m', p', h', hsub⟩ := ih hm
    exact ⟨m', p', h', fun y hy => hsub y (List.mem_cons_of_mem _ hy)⟩

/-- The structural content of graph acceptance. -/
structure AcceptedGraph [DecidableEq C] (V : Checker L C) (g : Graph L C) (goal : C) : Prop where
  /-- duplicate node ids are rejected -/
  nodup : (g.nodes.map (·.id)).Nodup
  /-- the root exists and carries exactly the expected claim -/
  rootBound : ∃ nd, g.find g.root = some nd ∧ nd.claim = goal
  /-- every reachable node exists, and passes its local check (so it is not
      `unsupported`, its children all exist, its rule check passes, and if it is a leaf
      its validator accepts the leaf's own claim) -/
  reachableOK : ∀ x, Reach g g.root x → ∃ nd, g.find x = some nd ∧ LocalOK V g nd
  /-- no cycle passes through any reachable node -/
  acyclic : ∀ x, Reach g g.root x → ¬ ∃ y, Edge g x y ∧ Reach g y x

theorem accepted_graph_facts [DecidableEq C] {V : Checker L C} {g : Graph L C} {goal : C}
    (h : checkGraph V g goal = true) : AcceptedGraph V g goal := by
  simp only [checkGraph, Bool.and_eq_true, decide_eq_true_eq] at h
  obtain ⟨⟨hnd, hroot⟩, heval⟩ := h
  refine ⟨hnd, ?_, ?_, ?_⟩
  · unfold rootBoundB at hroot
    split at hroot
    · rename_i nd hn; exact ⟨nd, hn, by simpa using hroot⟩
    · cases hroot
  · intro x hx
    obtain ⟨m, p, hm, _⟩ := evalNode_reach hx heval
    exact (evalNode_local hm).2
  · intro x hx ⟨y, hxy, hyx⟩
    obtain ⟨m, p, hm, _⟩ := evalNode_reach hx heval
    obtain ⟨nd, r, chs, hnd', hk, hy⟩ := hxy
    obtain ⟨m', _, hm'⟩ := evalNode_child hm hnd' hk hy
    obtain ⟨m'', p'', hm'', hsub⟩ := evalNode_reach hyx hm'
    exact (evalNode_local hm'').1 (hsub x List.mem_cons_self)

/-- A reachable `unsupported` node makes acceptance impossible. -/
theorem unsupported_rejected [DecidableEq C] {V : Checker L C} {g : Graph L C} {goal : C}
    {x : String} (hx : Reach g g.root x) {nd : Node L C} (hnd : g.find x = some nd)
    {tag : String} (hk : nd.kind = .unsupported tag) : checkGraph V g goal = false := by
  cases h : checkGraph V g goal with
  | false => rfl
  | true =>
    obtain ⟨nd', hnd', hl⟩ := (accepted_graph_facts h).reachableOK x hx
    rw [hnd] at hnd'; cases hnd'
    unfold LocalOK at hl; rw [hk] at hl; exact hl.elim

/-- A reachable reference to a missing child makes acceptance impossible. -/
theorem missing_child_rejected [DecidableEq C] {V : Checker L C} {g : Graph L C} {goal : C}
    {x : String} (hx : Reach g g.root x) {nd : Node L C} (hnd : g.find x = some nd)
    {r : String} {chs : List String} (hk : nd.kind = .derive r chs) {ch : String}
    (hch : ch ∈ chs) (hmiss : g.find ch = none) : checkGraph V g goal = false := by
  cases h : checkGraph V g goal with
  | false => rfl
  | true =>
    have hr : Reach g g.root ch := by
      have hxy : Edge g x ch := ⟨nd, r, chs, hnd, hk, hch⟩
      -- append the edge to the path root ⇝ x
      have key : ∀ {a b}, Reach g a b → Edge g b ch → Reach g a ch := by
        intro a b hab
        induction hab with
        | refl a => intro he; exact .step he (.refl _)
        | step he' _ ih => intro he; exact .step he' (ih he)
      exact key hx hxy
    obtain ⟨nd', hnd', _⟩ := (accepted_graph_facts h).reachableOK ch hr
    rw [hmiss] at hnd'; cases hnd'

/-- Duplicate ids make acceptance impossible. -/
theorem duplicate_ids_rejected [DecidableEq C] {V : Checker L C} {g : Graph L C} {goal : C}
    (hdup : ¬ (g.nodes.map (·.id)).Nodup) : checkGraph V g goal = false := by
  cases h : checkGraph V g goal with
  | false => rfl
  | true => exact absurd (accepted_graph_facts h).nodup hdup

/-- A cycle through a reachable node makes acceptance impossible. -/
theorem cycle_rejected [DecidableEq C] {V : Checker L C} {g : Graph L C} {goal : C}
    {x y : String} (hx : Reach g g.root x) (hxy : Edge g x y) (hyx : Reach g y x) :
    checkGraph V g goal = false := by
  cases h : checkGraph V g goal with
  | false => rfl
  | true => exact absurd ⟨y, hxy, hyx⟩ ((accepted_graph_facts h).acyclic x hx)

/-! ## Heterogeneous leaves

Leaf obligations of different evidence classes (formal proof, computational replay,
empirical validation, external receipt, …) are combined as a sum type; the combined
validator is sound as soon as each component validator is. -/

/-- Combine two leaf validators into one over the sum of their obligation types. -/
def Checker.sumLeaf {L₁ L₂ : Type} (V₁ : Checker L₁ C) (V₂ : Checker L₂ C) : Checker (L₁ ⊕ L₂) C :=
  { leaf := fun ob c => match ob with
      | .inl o => V₁.leaf o c
      | .inr o => V₂.leaf o c,
    rule := fun r p cs => V₁.rule r p cs }

theorem Checker.sumLeaf_sound {L₁ L₂ : Type} {V₁ : Checker L₁ C} {V₂ : Checker L₂ C}
    {Sem : C → Prop} (h₁ : CheckerSound V₁ Sem)
    (h₂ : ∀ ob c, V₂.leaf ob c = true → Sem c) : CheckerSound (V₁.sumLeaf V₂) Sem :=
  { leaf := fun ob c h => by
      cases ob with
      | inl o => exact h₁.leaf o c h
      | inr o => exact h₂ o c h,
    rule := h₁.rule }

end PCS.V2.ClaimGraph
