import PCS.V2.ClaimGraph

/-!
# Obligation-graph checking: exact characterisation and a memoised evaluator

1. **Completeness of the specification checker.**  `checkGraph_complete` proves the converse
   of `accepted_graph_facts`: every graph with duplicate-free ids, root bound to the goal,
   every reachable node present and locally valid, and no cycle through a reachable node is
   accepted.  Hence `checkGraph_iff`: `checkGraph V g goal = true ↔ AcceptedGraph V g goal`
   — the simple checker is an exact decision procedure for the structural specification.

2. **Memoised evaluator.**  `checkGraphMemo` runs a depth-first search that records every
   fully verified node id in a `done` list and never re-expands it (`visit_done`), so a shared
   sub-graph is evaluated once (polynomially many steps instead of one per root-to-node path).
   The current DFS stack still detects cycles, duplicate ids and missing nodes are still
   rejected, and the leaf / rule checks are unchanged.
   `checkGraphMemo_eq : checkGraphMemo V g goal = checkGraph V g goal` — the optimisation does
   not change any verdict, so every soundness theorem of the simple checker
   (`root_assurance_sound`, `accepted_graph_facts`, `domain_adapter_sound`, …) applies
   verbatim (`root_assurance_sound_memo`).
-/

set_option autoImplicit false

namespace PCS.V2.ClaimGraph

variable {L C : Type}

/-! ## Counting lemma -/

theorem nodup_length_le {α : Type} [DecidableEq α] :
    ∀ {l m : List α}, l.Nodup → (∀ a ∈ l, a ∈ m) → l.length ≤ m.length
  | [], _, _, _ => Nat.zero_le _
  | a :: l, m, hnd, hsub => by
    have ha : a ∈ m := hsub a List.mem_cons_self
    have hnd' := List.nodup_cons.mp hnd
    have : l.length ≤ (m.erase a).length :=
      nodup_length_le hnd'.2 (fun b hb => by
        have hba : b ≠ a := fun e => hnd'.1 (e ▸ hb)
        exact (List.mem_erase_of_ne hba).mpr (hsub b (List.mem_cons_of_mem _ hb)))
    rw [List.length_erase_of_mem ha] at this
    have hpos : 0 < m.length := List.length_pos_of_mem ha
    simp only [List.length_cons]
    omega

/-! ## Completeness of the specification checker -/

theorem reach_trans_edge {g : Graph L C} {a b c : String} (h : Reach g a b) (he : Edge g b c) :
    Reach g a c := by
  induction h with
  | refl a => exact Reach.step he (Reach.refl c)
  | step e _ ih => exact Reach.step e (ih he)

/-- Strict reachability (at least one edge). -/
def ReachPlus (g : Graph L C) (a b : String) : Prop := ∃ z, Edge g a z ∧ Reach g z b

theorem find_some_mem_ids {g : Graph L C} {i : String} {nd : Node L C} (h : g.find i = some nd) :
    i ∈ g.nodes.map (·.id) :=
  List.mem_map.mpr ⟨nd, find_mem h, find_id h⟩

theorem evalNode_complete [DecidableEq C] {V : Checker L C} {g : Graph L C} {goal : C}
    (hA : AcceptedGraph V g goal) :
    ∀ k (path : List String) (x : String), path.length + k = g.nodes.length → path.Nodup →
      (∀ y ∈ path, Reach g g.root y) → (∀ y ∈ path, ReachPlus g y x) → Reach g g.root x →
      evalNode V g k path x = true := by
  intro k
  induction k with
  | zero =>
    intro path x hlen hnd hreach hplus hx
    exfalso
    have hxp : x ∉ path := fun hm => by
      obtain ⟨z, hz, hzx⟩ := hplus x hm
      exact hA.acyclic x hx ⟨z, hz, hzx⟩
    have hsub : ∀ a ∈ x :: path, a ∈ g.nodes.map (·.id) := by
      intro a ha
      have hr : Reach g g.root a := by
        rcases List.mem_cons.mp ha with rfl | ha
        · exact hx
        · exact hreach a ha
      obtain ⟨nd, hnd', _⟩ := hA.reachableOK a hr
      exact find_some_mem_ids hnd'
    have := nodup_length_le (List.nodup_cons.mpr ⟨hxp, hnd⟩) hsub
    simp only [List.length_cons, List.length_map] at this
    omega
  | succ k ih =>
    intro path x hlen hnd hreach hplus hx
    have hxp : x ∉ path := fun hm => by
      obtain ⟨z, hz, hzx⟩ := hplus x hm
      exact hA.acyclic x hx ⟨z, hz, hzx⟩
    obtain ⟨nd, hfind, hloc⟩ := hA.reachableOK x hx
    simp only [evalNode]
    have hc : path.contains x = false := by simpa using hxp
    rw [hc, hfind]
    simp only [Bool.false_eq_true, if_false]
    unfold LocalOK at hloc
    split
    · rename_i ob hk
      rw [hk] at hloc; exact hloc
    · rename_i r chs hk
      rw [hk] at hloc
      obtain ⟨cs, hcs, hrule⟩ := hloc
      rw [hcs]
      simp only [hrule, Bool.true_and, List.all_eq_true]
      intro ch hch
      have hedge : Edge g x ch := ⟨nd, r, chs, hfind, hk, hch⟩
      refine ih (x :: path) ch (by simp only [List.length_cons]; omega)
        (List.nodup_cons.mpr ⟨hxp, hnd⟩) ?_ ?_ (reach_trans_edge hx hedge)
      · intro y hy
        rcases List.mem_cons.mp hy with rfl | hy
        · exact hx
        · exact hreach y hy
      · intro y hy
        rcases List.mem_cons.mp hy with rfl | hy
        · exact ⟨ch, hedge, Reach.refl ch⟩
        · obtain ⟨z, hz, hzx⟩ := hplus y hy
          exact ⟨z, hz, reach_trans_edge hzx hedge⟩
    · rename_i tag hk
      rw [hk] at hloc; exact hloc.elim

/-- **Completeness**: every structurally well-formed graph is accepted. -/
theorem checkGraph_complete [DecidableEq C] {V : Checker L C} {g : Graph L C} {goal : C}
    (hA : AcceptedGraph V g goal) : checkGraph V g goal = true := by
  simp only [checkGraph, Bool.and_eq_true, decide_eq_true_eq]
  refine ⟨⟨hA.nodup, ?_⟩, ?_⟩
  · obtain ⟨nd, hnd, hc⟩ := hA.rootBound
    simp [rootBoundB, hnd, hc]
  · exact evalNode_complete hA g.nodes.length [] g.root (by simp) List.nodup_nil
      (fun _ h => by cases h) (fun _ h => by cases h) (Reach.refl _)

/-- **Exact characterisation of the graph checker.** -/
theorem checkGraph_iff [DecidableEq C] (V : Checker L C) (g : Graph L C) (goal : C) :
    checkGraph V g goal = true ↔ AcceptedGraph V g goal :=
  ⟨accepted_graph_facts, checkGraph_complete⟩

/-! ## The memoised evaluator -/

/-- Visit the children in order, threading the `done` list. -/
def visitChildren (f : List String → String → Option (List String)) :
    List String → List String → Option (List String)
  | done, [] => some done
  | done, ch :: rest =>
    match f done ch with
    | none => none
    | some d => visitChildren f d rest

/-- Memoised depth-first evaluation of node `i`: `stack` is the current DFS path (cycle
    detection), `done` the list of fully verified node ids (never re-expanded). -/
def visit (V : Checker L C) (g : Graph L C) :
    Nat → List String → List String → String → Option (List String)
  | 0, _, _, _ => none
  | n + 1, stack, done, i =>
    if done.contains i then some done
    else if stack.contains i then none
    else
      match g.find i with
      | none => none
      | some nd =>
        match nd.kind with
        | .leaf ob => if V.leaf ob nd.claim then some (i :: done) else none
        | .derive r chs =>
          match g.findAll chs with
          | none => none
          | some cs =>
            if V.rule r nd.claim cs then
              (visitChildren (visit V g n (i :: stack)) done chs).map (i :: ·)
            else none
        | .unsupported _ => none

/-- **The memoised graph checker.** -/
def checkGraphMemo [DecidableEq C] (V : Checker L C) (g : Graph L C) (goal : C) : Bool :=
  decide ((g.nodes.map (·.id)).Nodup) && rootBoundB g goal &&
    (visit V g g.nodes.length [] [] g.root).isSome

/-- Shared sub-graphs are evaluated once: a verified node is never re-expanded. -/
theorem visit_done (V : Checker L C) (g : Graph L C) (n : Nat) (stack done : List String)
    {i : String} (h : i ∈ done) : visit V g (n + 1) stack done i = some done := by
  simp [visit, h]

/-! ### Specification ⟹ memo -/

theorem visitChildren_isSome {f : List String → String → Option (List String)} :
    ∀ {chs : List String}, (∀ ch ∈ chs, ∀ d, (f d ch).isSome) →
      ∀ d, (visitChildren f d chs).isSome
  | [], _, d => rfl
  | ch :: rest, h, d => by
    simp only [visitChildren]
    obtain ⟨d', hd'⟩ := Option.isSome_iff_exists.mp (h ch List.mem_cons_self d)
    rw [hd']
    exact visitChildren_isSome (fun c hc => h c (List.mem_cons_of_mem _ hc)) d'

theorem visit_of_evalNode {V : Checker L C} {g : Graph L C} :
    ∀ n path i, evalNode V g n path i = true → ∀ done, (visit V g n path done i).isSome := by
  intro n
  induction n with
  | zero => intro path i h; simp [evalNode] at h
  | succ n ih =>
    intro path i h done
    simp only [visit]
    by_cases hd : done.contains i = true
    · rw [if_pos hd]; rfl
    · rw [if_neg hd]
      simp only [evalNode] at h
      split at h
      · cases h
      · rename_i hp
        rw [if_neg hp]
        split at h
        · cases h
        · rename_i nd hnd
          rw [hnd]
          simp only
          split at h
          · rename_i ob hk
            rw [hk]; simp [h]
          · rename_i r chs hk
            rw [hk]
            simp only
            split at h
            · cases h
            · rename_i cs hcs
              rw [hcs]
              simp only [Bool.and_eq_true, List.all_eq_true] at h
              simp only [h.1, if_true, Option.isSome_map]
              exact visitChildren_isSome (fun ch hch d => ih _ ch (h.2 ch hch) d) done
          · cases h

/-! ### Memo ⟹ specification -/

/-- A topologically ordered, closed list of verified nodes (children after parents). -/
inductive TopoList (V : Checker L C) (g : Graph L C) : List String → Prop
  | nil : TopoList V g []
  | cons {i : String} {d : List String} {nd : Node L C} : TopoList V g d → i ∉ d →
      g.find i = some nd → LocalOK V g nd →
      (∀ r chs, nd.kind = .derive r chs → ∀ ch ∈ chs, ch ∈ d) → TopoList V g (i :: d)

theorem topo_mem {V : Checker L C} {g : Graph L C} :
    ∀ {d : List String}, TopoList V g d → ∀ {x}, x ∈ d →
      ∃ nd, g.find x = some nd ∧ LocalOK V g nd ∧
        ∀ r chs, nd.kind = .derive r chs → ∀ ch ∈ chs, ch ∈ d
  | _, .nil, _, hx => by cases hx
  | _, .cons (nd := nd) ht hi hf hl hc, x, hx => by
    rcases List.mem_cons.mp hx with rfl | hx
    · exact ⟨nd, hf, hl, fun r chs hk ch hch => List.mem_cons_of_mem _ (hc r chs hk ch hch)⟩
    · obtain ⟨nd', hf', hl', hc'⟩ := topo_mem ht hx
      exact ⟨nd', hf', hl', fun r chs hk ch hch => List.mem_cons_of_mem _ (hc' r chs hk ch hch)⟩

theorem topo_closed {V : Checker L C} {g : Graph L C} {d : List String} (ht : TopoList V g d)
    {x y : String} (hr : Reach g x y) (hx : x ∈ d) : y ∈ d := by
  induction hr with
  | refl => exact hx
  | step he _ ih =>
    obtain ⟨nd, r, chs, hf, hk, hb⟩ := he
    obtain ⟨nd', hf', _, hc⟩ := topo_mem ht hx
    rw [hf] at hf'; cases hf'
    exact ih (hc r chs hk _ hb)

theorem topo_acyclic {V : Checker L C} {g : Graph L C} :
    ∀ {d : List String}, TopoList V g d → ∀ x ∈ d, ¬ ∃ y, Edge g x y ∧ Reach g y x
  | _, .nil, _, hx, _ => by cases hx
  | _, .cons (i := i) (nd := nd) ht hi hf _ hc, x, hx, ⟨y, hxy, hyx⟩ => by
    rcases List.mem_cons.mp hx with rfl | hx
    · obtain ⟨nd', r, chs, hf', hk, hb⟩ := hxy
      rw [hf] at hf'; cases hf'
      exact hi (topo_closed ht hyx (hc r chs hk y hb))
    · exact topo_acyclic ht x hx ⟨y, hxy, hyx⟩

theorem visitChildren_spec {V : Checker L C} {g : Graph L C}
    {f : List String → String → Option (List String)}
    (hf : ∀ d ch d', f d ch = some d' → TopoList V g d →
      TopoList V g d' ∧ ch ∈ d' ∧ ∀ y ∈ d, y ∈ d') :
    ∀ {chs d d'}, visitChildren f d chs = some d' → TopoList V g d →
      TopoList V g d' ∧ (∀ ch ∈ chs, ch ∈ d') ∧ ∀ y ∈ d, y ∈ d'
  | [], d, d', h, ht => by
    simp only [visitChildren, Option.some.injEq] at h; subst h
    refine ⟨ht, ?_, fun _ h => h⟩
    intro _ h; cases h
  | ch :: rest, d, d', h, ht => by
    simp only [visitChildren] at h
    split at h
    · cases h
    · rename_i d₁ h₁
      obtain ⟨ht₁, hch, hsub₁⟩ := hf d ch d₁ h₁ ht
      obtain ⟨ht₂, hall, hsub₂⟩ := visitChildren_spec hf h ht₁
      refine ⟨ht₂, ?_, fun y hy => hsub₂ y (hsub₁ y hy)⟩
      intro c hc
      rcases List.mem_cons.mp hc with rfl | hc
      · exact hsub₂ _ hch
      · exact hall c hc

theorem visitChildren_disjoint {f : List String → String → Option (List String)} {y : String}
    (hf : ∀ d ch d', f d ch = some d' → y ∉ d → y ∉ d') :
    ∀ {chs d d'}, visitChildren f d chs = some d' → y ∉ d → y ∉ d'
  | [], d, d', h, hd => by
    simp only [visitChildren, Option.some.injEq] at h; subst h; exact hd
  | ch :: rest, d, d', h, hd => by
    simp only [visitChildren] at h
    split at h
    · cases h
    · rename_i d₁ h₁
      exact visitChildren_disjoint hf h (hf d ch d₁ h₁ hd)

/-- A node on the DFS stack that is not yet done is never marked done below it. -/
theorem visit_disjoint {V : Checker L C} {g : Graph L C} :
    ∀ n stack d x d' y, visit V g n stack d x = some d' → y ∈ stack → y ∉ d → y ∉ d' := by
  intro n
  induction n with
  | zero => intro stack d x d' y h; simp [visit] at h
  | succ n ih =>
    intro stack d x d' y h hy hd
    simp only [visit] at h
    split at h
    · cases h; exact hd
    · split at h
      · cases h
      · rename_i hxs
        have hxs' : x ∉ stack := by simpa using hxs
        have hyx : y ≠ x := fun e => hxs' (e ▸ hy)
        split at h
        · cases h
        · split at h
          · split at h
            · cases h
              intro hm
              rcases List.mem_cons.mp hm with e | hm
              · exact hyx e
              · exact hd hm
            · cases h
          · split at h
            · cases h
            · split at h
              · obtain ⟨d₀, h₀, rfl⟩ := Option.map_eq_some_iff.mp h
                have hdis := visitChildren_disjoint (y := y)
                  (fun d ch d' h hd => ih (x :: stack) d ch d' y h (List.mem_cons_of_mem _ hy) hd)
                  h₀ hd
                intro hm
                rcases List.mem_cons.mp hm with e | hm
                · exact hyx e
                · exact hdis hm
              · cases h
          · cases h

/-- Successful memoised evaluation yields a topologically ordered closed list of verified
    nodes containing the visited node. -/
theorem visit_topo {V : Checker L C} {g : Graph L C} :
    ∀ n stack d x d', visit V g n stack d x = some d' → TopoList V g d →
      TopoList V g d' ∧ x ∈ d' ∧ ∀ y ∈ d, y ∈ d' := by
  intro n
  induction n with
  | zero => intro stack d x d' h; simp [visit] at h
  | succ n ih =>
    intro stack d x d' h ht
    simp only [visit] at h
    split at h
    · rename_i hxd
      cases h
      exact ⟨ht, by simpa using hxd, fun _ h => h⟩
    · rename_i hxd
      have hxd' : x ∉ d := by simpa using hxd
      split at h
      · cases h
      · rename_i hxs
        split at h
        · cases h
        · rename_i nd hnd
          split at h
          · rename_i ob hk
            split at h
            · rename_i hl
              cases h
              refine ⟨TopoList.cons ht hxd' hnd ?_ ?_, List.mem_cons_self,
                fun y hy => List.mem_cons_of_mem _ hy⟩
              · unfold LocalOK; rw [hk]; exact hl
              · intro r chs hk'; rw [hk] at hk'; cases hk'
            · cases h
          · rename_i r chs hk
            split at h
            · cases h
            · rename_i cs hcs
              split at h
              · rename_i hrule
                obtain ⟨d₀, h₀, rfl⟩ := Option.map_eq_some_iff.mp h
                obtain ⟨ht₀, hall, hsub⟩ :=
                  visitChildren_spec (fun d ch d' h ht => ih (x :: stack) d ch d' h ht) h₀ ht
                have hxd₀ : x ∉ d₀ :=
                  visitChildren_disjoint (y := x)
                    (fun d ch d' h hd => visit_disjoint n (x :: stack) d ch d' x h
                      List.mem_cons_self hd) h₀ hxd'
                refine ⟨TopoList.cons ht₀ hxd₀ hnd ?_ ?_, List.mem_cons_self,
                  fun y hy => List.mem_cons_of_mem _ (hsub y hy)⟩
                · unfold LocalOK; rw [hk]; exact ⟨cs, hcs, hrule⟩
                · intro r' chs' hk'
                  rw [hk] at hk'; cases hk'
                  exact hall
              · cases h
          · cases h

/-- Memoised acceptance implies the structural specification. -/
theorem checkGraphMemo_facts [DecidableEq C] {V : Checker L C} {g : Graph L C} {goal : C}
    (h : checkGraphMemo V g goal = true) : AcceptedGraph V g goal := by
  simp only [checkGraphMemo, Bool.and_eq_true, decide_eq_true_eq] at h
  obtain ⟨⟨hnd, hroot⟩, hv⟩ := h
  obtain ⟨d', hd'⟩ := Option.isSome_iff_exists.mp hv
  obtain ⟨ht, hr, _⟩ := visit_topo _ _ _ _ _ hd' TopoList.nil
  refine ⟨hnd, ?_, ?_, ?_⟩
  · unfold rootBoundB at hroot
    split at hroot
    · rename_i nd hn; exact ⟨nd, hn, by simpa using hroot⟩
    · cases hroot
  · intro x hx
    obtain ⟨nd, hf, hl, _⟩ := topo_mem ht (topo_closed ht hx hr)
    exact ⟨nd, hf, hl⟩
  · intro x hx
    exact topo_acyclic ht x (topo_closed ht hx hr)

/-- **The memoised checker computes exactly the specification checker's verdict.** -/
theorem checkGraphMemo_eq [DecidableEq C] (V : Checker L C) (g : Graph L C) (goal : C) :
    checkGraphMemo V g goal = checkGraph V g goal := by
  apply Bool.eq_iff_iff.mpr
  constructor
  · intro h; exact checkGraph_complete (checkGraphMemo_facts h)
  · intro h
    have h' := h
    simp only [checkGraph, Bool.and_eq_true, decide_eq_true_eq] at h'
    obtain ⟨⟨hnd, hroot⟩, hev⟩ := h'
    simp only [checkGraphMemo, Bool.and_eq_true, decide_eq_true_eq]
    exact ⟨⟨hnd, hroot⟩, visit_of_evalNode _ _ _ hev []⟩

/-- Root-assurance soundness inherited by the memoised checker. -/
theorem root_assurance_sound_memo [DecidableEq C] {V : Checker L C} {Sem : C → Prop}
    (hV : CheckerSound V Sem) {g : Graph L C} {goal : C}
    (h : checkGraphMemo V g goal = true) : Sem goal :=
  root_assurance_sound hV (by rw [← checkGraphMemo_eq]; exact h)

/-! ## Performance witness and cache-key falsification -/

/-- A chain of `k` diamonds: `2 ^ k` root-to-sink paths, `3k + 1` nodes.  The simple checker
    re-evaluates the shared sink once per path; the memoised checker once. -/
def diamondChain (k : Nat) : Graph Unit Nat :=
  ⟨(List.range k).flatMap (fun i =>
      [⟨s!"n{i}", 0, .derive "and" [s!"l{i}", s!"r{i}"]⟩,
       ⟨s!"l{i}", 0, .derive "and" [s!"n{i + 1}"]⟩,
       ⟨s!"r{i}", 0, .derive "and" [s!"n{i + 1}"]⟩]) ++
    [⟨s!"n{k}", 0, .leaf ()⟩], "n0"⟩

def trivialChecker : Checker Unit Nat := { leaf := fun _ _ => true, rule := fun _ _ _ => true }

-- 2^40 paths: infeasible for the path-enumerating checker, immediate for the memoised one
-- (compiled evaluation; by `checkGraphMemo_eq` this is also the simple checker's verdict).
#guard checkGraphMemo trivialChecker (diamondChain 40) 0

/-- Cache-key collision / wrong-node reuse: two different nodes under the same id are
    rejected (ids must be unique), so the memo key `id` always names one node. -/
theorem memo_rejects_id_collision :
    checkGraphMemo trivialChecker
      ⟨[⟨"r", 0, .derive "and" ["x"]⟩, ⟨"x", 0, .leaf ()⟩, ⟨"x", 1, .unsupported "evil"⟩], "r"⟩ 0 =
      false := by decide

/-- Cycles are still rejected by the memoised checker. -/
theorem memo_rejects_cycle :
    checkGraphMemo trivialChecker
      ⟨[⟨"r", 0, .derive "and" ["x"]⟩, ⟨"x", 0, .derive "and" ["r"]⟩], "r"⟩ 0 = false := by decide

/-- Missing nodes are still rejected by the memoised checker. -/
theorem memo_rejects_missing :
    checkGraphMemo trivialChecker ⟨[⟨"r", 0, .derive "and" ["x"]⟩], "r"⟩ 0 = false := by decide

end PCS.V2.ClaimGraph
