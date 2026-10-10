import PCSDecisionDiagram.Pass

/-!
# Positive-cost intervention planning (typed reference of `intervention.py`)

* `ITask` — a conditional problem with `candidate = FALSE`, a Boolean baseline, integer change
  costs `1 … 1,000,000`, and a strictly sorted list of locked variable indices.
  `ITask.validB` is the executable validator (also enforcing the conditional limits: at most 24
  variables, eight assumptions, 128 nodes and depth 12 per formula).
* `IFeasible t a` — `a` satisfies every premise and the target and keeps every locked variable
  at its baseline.  The baseline itself may violate the premises.
* `plan` — runs `check`; on `resource_limit` / `inconsistent_assumptions` the receipt carries
  no cost, assignment, count, masks or Bellman table; otherwise it runs the single
  Bellman pass over the returned diagram from the difference root (`context ∧ target`),
  reconstructs with the Python walk and re-checks the point against the AST (`guard`).
* Principal theorems: `plan_ok` (a valid task never reaches the internal-error guard),
  `plan_resource_limit`, `plan_inconsistent`, `plan_no_feasible` and `plan_optimal`
  (AST-level optimality, lexicographic leastness, count, mandatory/possible flips, bounds),
  `verify_iff` (replay rejects every receipt that differs from the regenerated one),
  `audit_*` (proposal audit and optimality gap).
-/

namespace PCSDD

open PCSOmega

variable {n : Nat}

/-- Typed intervention task (`pcs-intervention-task-v1`). -/
structure ITask (n : Nat) where
  problem : CTask n
  baseline : List Bool
  costs : List Nat
  locked : List Nat
  deriving DecidableEq, Repr

/-- Strictly increasing list (sorted and distinct). -/
def strictSorted : List Nat → Bool
  | a :: b :: r => decide (a < b) && strictSorted (b :: r)
  | _ => true

/-- Formula complexity bound of the conditional protocol. -/
def formulaOK (f : BForm n) : Bool := decide (f.size ≤ 128) && decide (f.depth ≤ 12)

/-- Executable conditional-task limits. -/
def CTask.validB (t : CTask n) : Bool :=
  decide (n ≤ 24) && decide (t.assumptions.length ≤ 8) &&
    (t.source :: t.candidate :: t.assumptions).all formulaOK

/-- Executable intervention-task validator (`validate_task`). -/
def ITask.validB (t : ITask n) : Bool :=
  t.problem.validB && (t.problem.candidate == .ff) && (t.baseline.length == n) &&
    (t.costs.length == n) && t.costs.all (fun c => decide (1 ≤ c) && decide (c ≤ 1000000)) &&
    strictSorted t.locked && t.locked.all (fun i => decide (i < n))

/-- Prices read off a task. -/
def ITask.prices (t : ITask n) : Prices :=
  ⟨fun i => t.baseline.getD i false, fun i => t.costs.getD i 0, fun i => t.locked.contains i⟩

/-- The intervention objective. -/
def ITask.cost (t : ITask n) (a : List Bool) : Nat := objective t.prices a

/-- Feasible total assignment at the AST level. -/
def IFeasible (t : ITask n) (a : List Bool) : Prop :=
  a.length = n ∧ allEval t.problem.assumptions (envOf a) = true ∧
    t.problem.source.eval (envOf a) = true ∧ ∀ i ∈ t.locked, a.getD i false = t.baseline.getD i false

/-- Optimal total assignment at the AST level. -/
def IOptimal (t : ITask n) (a : List Bool) : Prop :=
  IFeasible t a ∧ ∀ b, IFeasible t b → t.cost a ≤ t.cost b

inductive IDecision where
  | resourceLimit
  | inconsistentAssumptions
  | noFeasiblePlan
  | optimalPlan
  deriving DecidableEq, Repr

/-- Intervention receipt content (hash fields are outside the model). -/
structure IReceipt (n : Nat) where
  task : ITask n
  limits : Limits
  symbolic : CReceipt n
  decision : IDecision
  minimumCost : Option Nat
  optimalCount : Option Nat
  assignment : Option (List Bool)
  flips : Option (List Nat)
  mandatory : Option (List Nat)
  possible : Option (List Nat)
  cells : Option (Array (Option Cell))
  dpNodes : Nat
  pcsAuthority : Bool
  leanKernelChecked : Bool
  deriving DecidableEq, Repr

/-- Receipt without a plan. -/
def IReceipt.bare (t : ITask n) (lim : Limits) (sym : CReceipt n) (d : IDecision) : IReceipt n :=
  ⟨t, lim, sym, d, none, none, none, none, none, none, none, 0, false, false⟩

/-- The AST re-check of the reconstructed point (the guard kept under `python -O`). -/
def guard (t : ITask n) (a : List Bool) (cost : Nat) : Bool :=
  t.problem.source.eval (envOf a) && allEval t.problem.assumptions (envOf a) &&
    t.locked.all (fun i => a.getD i false == t.baseline.getD i false) && (t.cost a == cost)

/-- Indices `< n` whose bit is set. -/
def bitsOf (n m : Nat) : List Nat := (List.range n).filter (fun i => m.testBit i)

/-- `plan(task, limits)`. -/
def plan (t : ITask n) (lim : Limits) : Except String (IReceipt n) :=
  if t.validB = false then .error "invalid intervention task" else
  if lim.valid = false then .error "invalid limits" else
  let sym := check t.problem lim
  match sym.decision with
  | .resourceLimit => .ok (IReceipt.bare t lim sym .resourceLimit)
  | .inconsistentAssumptions => .ok (IReceipt.bare t lim sym .inconsistentAssumptions)
  | _ =>
    match sym.diagram with
    | none => .error "internal: missing diagram"
    | some dr =>
      match dr.difference with
      | none => .error "internal: missing difference root"
      | some root =>
        let P := t.prices
        let st := bellmanPass dr.nodes P
        match st.cells.getD root none with
        | none => .ok { IReceipt.bare t lim sym .noFeasiblePlan with
                        cells := some st.cells, dpNodes := dr.nodes.size }
        | some c =>
          match walkPy dr.nodes st.choices (dr.nodes.size + 1) root (baseList P n) with
          | none => .error "internal: reconstruction did not reach TRUE"
          | some a =>
            if guard t a c.cost then
              .ok { task := t, limits := lim, symbolic := sym, decision := .optimalPlan,
                    minimumCost := some c.cost, optimalCount := some c.count, assignment := some a,
                    flips := some ((List.range n).filter (fun i => flips P a i)),
                    mandatory := some (bitsOf n c.mand), possible := some (bitsOf n c.poss),
                    cells := some st.cells, dpNodes := dr.nodes.size, pcsAuthority := false,
                    leanKernelChecked := false }
            else .error "internal: plan witness does not match the declared task or cost"

/-- Receipt replay: regenerate the deterministic result and compare all content. -/
def IReceipt.verify (r : IReceipt n) : Bool :=
  match plan r.task r.limits with
  | .ok r' => r == r'
  | .error _ => false

theorem IReceipt.verify_iff (r : IReceipt n) : r.verify = true ↔ plan r.task r.limits = .ok r := by
  unfold IReceipt.verify
  split
  · rename_i r' h; rw [h]; simp only [beq_iff_eq, Except.ok.injEq]; exact ⟨fun e => e ▸ rfl, fun e => e ▸ rfl⟩
  · rename_i e h; rw [h]; simp

/-- **Replay rejects every changed receipt**: any receipt (with any task, limits, cells,
witnesses, masks, costs, work or flags) that differs from the deterministic reference output for
its own task and limits is rejected. -/
theorem IReceipt.verify_rejects {r : IReceipt n} (h : plan r.task r.limits ≠ .ok r) :
    r.verify = false := by
  cases hv : r.verify
  · rfl
  · exact absurd ((IReceipt.verify_iff r).1 hv) h

theorem IReceipt.verify_rejects_changed {t : ITask n} {lim : Limits} {r r' : IReceipt n}
    (hp : plan t lim = .ok r) (ht : r'.task = t) (hl : r'.limits = lim) (hne : r' ≠ r) :
    r'.verify = false :=
  IReceipt.verify_rejects (by rw [ht, hl, hp]; intro e; exact hne (Except.ok.inj e).symm)

/-! ## Facts about valid tasks -/

theorem strictSorted_nodup : ∀ l : List Nat, strictSorted l = true → l.Nodup
  | [], _ => List.nodup_nil
  | [a], _ => by simp
  | a :: b :: r, h => by
      simp only [strictSorted, Bool.and_eq_true, decide_eq_true_eq] at h
      have ih := strictSorted_nodup (b :: r) h.2
      have hlt : ∀ x ∈ b :: r, a < x := by
        suffices ∀ (l : List Nat) (a : Nat), strictSorted l = true → ∀ x ∈ l, l.head? = some a → a ≤ x by
          intro x hx; have := this (b :: r) b h.2 x hx rfl; omega
        intro l
        induction l with
        | nil => simp
        | cons y ys ih2 =>
            intro a hs x hx hh
            simp at hh; subst hh
            rcases List.mem_cons.1 hx with rfl | hx
            · exact Nat.le_refl _
            · cases ys with
              | nil => simp at hx
              | cons z zs =>
                  simp only [strictSorted, Bool.and_eq_true, decide_eq_true_eq] at hs
                  have := ih2 z hs.2 x hx rfl; omega
      exact List.nodup_cons.2 ⟨fun hm => by have := hlt a hm; omega, ih⟩

structure ValidFacts (t : ITask n) : Prop where
  nle : n ≤ 24
  cand : t.problem.candidate = .ff
  pos : ∀ k < n, 0 < t.prices.cost k
  le : ∀ k, t.prices.cost k ≤ 1000000
  locked_lt : ∀ i ∈ t.locked, i < n
  locked_nodup : t.locked.Nodup
  base_len : t.baseline.length = n

theorem validFacts {t : ITask n} (h : t.validB = true) : ValidFacts t := by
  simp only [ITask.validB, CTask.validB, Bool.and_eq_true, decide_eq_true_eq, beq_iff_eq,
    List.all_eq_true] at h
  obtain ⟨⟨⟨⟨⟨⟨⟨⟨hn, _⟩, _⟩, hc⟩, hb⟩, hcl⟩, hcs⟩, hs⟩, hl⟩ := h
  refine ⟨hn, hc, fun k hk => ?_, fun k => ?_, fun i hi => hl i hi, strictSorted_nodup _ hs, hb⟩
  · have hk' : k < t.costs.length := by omega
    have := hcs (t.costs[k]'hk') (List.getElem_mem hk')
    simp [ITask.prices, List.getD_eq_getElem?_getD, List.getElem?_eq_getElem hk']; omega
  · simp only [ITask.prices, List.getD_eq_getElem?_getD]
    cases h : t.costs[k]? with
    | none => simp
    | some c =>
        have := hcs c (List.mem_of_getElem? h)
        simp; omega

/-- Diagram facts of a decided conditional receipt. -/
theorem check_decided {t : CTask n} {lim : Limits}
    (h1 : (check t lim).decision ≠ .resourceLimit) (h2 : (check t lim).decision ≠ .inconsistentAssumptions) :
    ∃ dr d, (check t lim).diagram = some dr ∧ dr.difference = some d ∧ Valid n dr.nodes ∧
      d < dr.nodes.size + 2 ∧ dr.nodes.size ≤ lim.nodes ∧
      (∀ ρ, evalD dr.nodes ρ d = (allEval t.assumptions ρ && (t.source.eval ρ != t.candidate.eval ρ))) ∧
      ∃ ρ, allEval t.assumptions ρ = true := by
  unfold check at h1 h2 ⊢
  match hp : pipeline t lim with
  | .error _ => simp [hp] at h1
  | .ok (.inconsistent .., _) => simp [hp] at h2
  | .ok (.decided ctx s c d, m) =>
    simp only
    obtain ⟨hinv, hnz, dctx, dd⟩ := pipeline_decided hp
    refine ⟨_, d, rfl, rfl, hinv.valid, dd.1, hinv.size_le, dd.2, ?_⟩
    obtain ⟨ρ, hρ⟩ : ∃ ρ, evalD m.nodes ρ ctx = true := by
      refine Classical.byContradiction fun hno => hnz ?_
      exact (eq_zero_iff_unsat hinv.valid dctx.1).2 (fun ρ => by
        cases h : evalD m.nodes ρ ctx
        · rfl
        · exact absurd ⟨ρ, h⟩ hno)
    exact ⟨ρ, by rw [← dctx.2]; exact hρ⟩

/-- Bridge: diagram-level feasibility of the difference root is AST-level feasibility. -/
theorem feasible_iff {t : ITask n} (hf : ValidFacts t) {ns : Nodes} {d : Nat}
    (hd : ∀ ρ, evalD ns ρ d = (allEval t.problem.assumptions ρ &&
      (t.problem.source.eval ρ != t.problem.candidate.eval ρ))) (a : List Bool) :
    Feasible n ns t.prices d a ↔ IFeasible t a := by
  simp only [Feasible, IFeasible, hd, hf.cand, BForm.eval, Bool.and_eq_true, Bool.bne_false]
  constructor
  · rintro ⟨hl, ⟨h1, h2⟩, hk⟩
    exact ⟨hl, h1, h2, fun i hi => hk i (hf.locked_lt i hi) (by simp [ITask.prices, hi])⟩
  · rintro ⟨hl, h1, h2, hk⟩
    exact ⟨hl, ⟨h1, h2⟩, fun i _ hli => hk i (by simpa [ITask.prices] using hli)⟩

theorem optimal_iff {t : ITask n} (hf : ValidFacts t) {ns : Nodes} {d : Nat}
    (hd : ∀ ρ, evalD ns ρ d = (allEval t.problem.assumptions ρ &&
      (t.problem.source.eval ρ != t.problem.candidate.eval ρ))) (a : List Bool) :
    Optimal n ns t.prices d a ↔ IOptimal t a := by
  simp only [Optimal, IOptimal, feasible_iff hf hd, ITask.cost]

theorem guard_iff {t : ITask n} (a : List Bool) (hl : a.length = n) (c : Nat) :
    guard t a c = true ↔ IFeasible t a ∧ t.cost a = c := by
  simp only [guard, IFeasible, Bool.and_eq_true, List.all_eq_true, beq_iff_eq]
  constructor
  · rintro ⟨⟨⟨h1, h2⟩, h3⟩, h4⟩; exact ⟨⟨hl, h2, h1, h3⟩, h4⟩
  · rintro ⟨⟨_, h2, h1, h3⟩, h4⟩; exact ⟨⟨⟨h1, h2⟩, h3⟩, h4⟩

/-! ## The planner contracts -/

/-- A successful run certifies that the task and the limits passed validation. -/
theorem plan_valid {t : ITask n} {lim : Limits} {r : IReceipt n} (hp : plan t lim = .ok r) :
    t.validB = true ∧ lim.valid = true := by
  unfold plan at hp
  split at hp
  · cases hp
  rename_i h1
  split at hp
  · cases hp
  rename_i h2
  exact ⟨by simpa using h1, by simpa using h2⟩

/-- Unfolded successful planner run. -/
theorem plan_cases {t : ITask n} {lim : Limits} {r : IReceipt n} (hv : t.validB = true)
    (hp : plan t lim = .ok r) :
    ((check t.problem lim).decision = .resourceLimit ∧ r = IReceipt.bare t lim (check t.problem lim) .resourceLimit) ∨
    ((check t.problem lim).decision = .inconsistentAssumptions ∧
      r = IReceipt.bare t lim (check t.problem lim) .inconsistentAssumptions) ∨
    ∃ dr d, (check t.problem lim).diagram = some dr ∧ dr.difference = some d ∧ Valid n dr.nodes ∧
      d < dr.nodes.size + 2 ∧ dr.nodes.size ≤ lim.nodes ∧
      (∀ ρ, evalD dr.nodes ρ d = (allEval t.problem.assumptions ρ &&
        (t.problem.source.eval ρ != t.problem.candidate.eval ρ))) ∧
      (∃ ρ, allEval t.problem.assumptions ρ = true) ∧
      ((cellRec dr.nodes t.prices d = none ∧
        r = { IReceipt.bare t lim (check t.problem lim) .noFeasiblePlan with
              cells := some (bellmanPass dr.nodes t.prices).cells, dpNodes := dr.nodes.size }) ∨
       ∃ c a, cellRec dr.nodes t.prices d = some c ∧
        walkPy dr.nodes (bellmanPass dr.nodes t.prices).choices (dr.nodes.size + 1) d
          (baseList t.prices n) = some a ∧ guard t a c.cost = true ∧
        r = { task := t, limits := lim, symbolic := check t.problem lim, decision := .optimalPlan,
              minimumCost := some c.cost, optimalCount := some c.count, assignment := some a,
              flips := some ((List.range n).filter (fun i => flips t.prices a i)),
              mandatory := some (bitsOf n c.mand), possible := some (bitsOf n c.poss),
              cells := some (bellmanPass dr.nodes t.prices).cells, dpNodes := dr.nodes.size,
              pcsAuthority := false, leanKernelChecked := false }) := by
  unfold plan at hp
  rw [if_neg (by simp [hv])] at hp
  split at hp
  · cases hp
  simp only at hp
  split at hp
  · rename_i hd; cases hp; exact Or.inl ⟨hd, rfl⟩
  · rename_i hd; cases hp; exact Or.inr (Or.inl ⟨hd, rfl⟩)
  · rename_i hd1 hd2
    right; right
    obtain ⟨dr, d, hdr, hdd, hval, hdlt, hsz, hden, hcons⟩ := check_decided hd1 hd2
    refine ⟨dr, d, hdr, hdd, hval, hdlt, hsz, hden, hcons, ?_⟩
    rw [hdr] at hp; simp only at hp
    rw [hdd] at hp; simp only at hp
    have I := bellmanPass_spec (P := t.prices) hval
    have hget : (bellmanPass dr.nodes t.prices).cells.getD d none = cellRec dr.nodes t.prices d := by
      rw [Array.getD_eq_getD_getElem?, I.cells d hdlt]; rfl
    rw [hget] at hp
    split at hp
    · rename_i hc; cases hp; exact Or.inl ⟨hc, rfl⟩
    · rename_i c hc
      split at hp
      · cases hp
      · rename_i a ha
        split at hp
        · rename_i hg; cases hp; exact Or.inr ⟨c, a, hc, ha, hg, rfl⟩
        · cases hp

/-- **A valid task never reaches an internal-error branch** (the guard always passes). -/
theorem plan_ok {t : ITask n} (hv : t.validB = true) {lim : Limits} (hl : lim.valid = true) :
    ∃ r, plan t lim = .ok r := by
  have hf := validFacts hv
  unfold plan
  rw [if_neg (by simp [hv]), if_neg (by simp [hl])]
  simp only
  split
  · exact ⟨_, rfl⟩
  · exact ⟨_, rfl⟩
  · rename_i hd1 hd2
    obtain ⟨dr, d, hdr, hdd, hval, hdlt, _, hden, _⟩ := check_decided hd1 hd2
    rw [hdr]; simp only
    rw [hdd]; simp only
    have I := bellmanPass_spec (P := t.prices) hval
    have hget : (bellmanPass dr.nodes t.prices).cells.getD d none = cellRec dr.nodes t.prices d := by
      rw [Array.getD_eq_getD_getElem?, I.cells d hdlt]; rfl
    rw [hget]
    split
    · exact ⟨_, rfl⟩
    · rename_i c hc
      obtain ⟨a, hw, ha, _, hobj⟩ := walkPy_spec hval hf.pos hdlt hc
      rw [hw]; simp only
      have hfe := (recon_spec hval hf.pos hdlt hc).2.2
      rw [← ha] at hfe
      have hg : guard t a c.cost = true :=
        (guard_iff a hfe.1 c.cost).2 ⟨(feasible_iff hf hden a).1 hfe, hobj⟩
      rw [if_pos hg]
      exact ⟨_, rfl⟩

/-- **Resource-limit receipts contain no costs, assignment, count, masks or Bellman table.** -/
theorem plan_resource_limit {t : ITask n} {lim : Limits} {r : IReceipt n} (hv : t.validB = true)
    (hp : plan t lim = .ok r) (hd : r.decision = .resourceLimit) :
    r.minimumCost = none ∧ r.optimalCount = none ∧ r.assignment = none ∧ r.flips = none ∧
      r.mandatory = none ∧ r.possible = none ∧ r.cells = none ∧ r.dpNodes = 0 ∧
      r.symbolic.decision = .resourceLimit := by
  rcases plan_cases hv hp with ⟨h1, rfl⟩ | ⟨_, rfl⟩ | ⟨_, _, _, _, _, _, _, _, _, ⟨_, rfl⟩ | ⟨_, _, _, _, _, rfl⟩⟩ <;>
    first | exact ⟨rfl, rfl, rfl, rfl, rfl, rfl, rfl, rfl, h1⟩ | cases hd

/-- **Inconsistent premises** (reported separately from an infeasible goal). -/
theorem plan_inconsistent {t : ITask n} {lim : Limits} {r : IReceipt n} (hv : t.validB = true)
    (hp : plan t lim = .ok r) (hd : r.decision = .inconsistentAssumptions) :
    (∀ ρ, allEval t.problem.assumptions ρ = false) ∧ r.minimumCost = none ∧ r.assignment = none ∧
      r.optimalCount = none ∧ r.cells = none := by
  rcases plan_cases hv hp with ⟨_, rfl⟩ | ⟨h1, rfl⟩ | ⟨_, _, _, _, _, _, _, _, _, ⟨_, rfl⟩ | ⟨_, _, _, _, _, rfl⟩⟩
  · cases hd
  · exact ⟨(check_inconsistent _ _ h1).1, rfl, rfl, rfl, rfl⟩
  · cases hd
  · cases hd

/-- **No feasible plan**: the premises are consistent, but no total assignment satisfies the
premises, the target and the locks. -/
theorem plan_no_feasible {t : ITask n} {lim : Limits} {r : IReceipt n} (hv : t.validB = true)
    (hp : plan t lim = .ok r) (hd : r.decision = .noFeasiblePlan) :
    (∃ ρ, allEval t.problem.assumptions ρ = true) ∧ (∀ a, ¬ IFeasible t a) ∧
      r.minimumCost = none ∧ r.assignment = none ∧ r.optimalCount = none := by
  have hf := validFacts hv
  rcases plan_cases hv hp with ⟨_, rfl⟩ | ⟨_, rfl⟩ |
    ⟨dr, d, _, _, hval, hdlt, _, hden, hcons, ⟨hc, rfl⟩ | ⟨_, _, _, _, _, rfl⟩⟩
  · cases hd
  · cases hd
  · refine ⟨hcons, fun a ha => ?_, rfl, rfl, rfl⟩
    have := ((bellman_correct (P := t.prices) hval hf.pos hdlt).1.1 hc) a
    exact this ((feasible_iff hf hden a).2 ha)
  · cases hd

/-- **Optimal plan: AST-level optimality, lexicographic leastness, count and explanations.** -/
theorem plan_optimal {t : ITask n} {lim : Limits} {r : IReceipt n} (hv : t.validB = true)
    (hp : plan t lim = .ok r) (hd : r.decision = .optimalPlan) :
    ∃ a mc cnt mand poss fl, r.assignment = some a ∧ r.minimumCost = some mc ∧
      r.optimalCount = some cnt ∧ r.mandatory = some mand ∧ r.possible = some poss ∧
      r.flips = some fl ∧
      IsLexLeast (IOptimal t) a ∧ t.cost a = mc ∧ (∀ b, IFeasible t b → mc ≤ t.cost b) ∧
      (∃ L : List (List Bool), L.Nodup ∧ (∀ b, b ∈ L ↔ IOptimal t b) ∧ cnt = L.length) ∧
      (∀ i, i ∈ mand ↔ i < n ∧ ∀ b, IOptimal t b → flips t.prices b i = true) ∧
      (∀ i, i ∈ poss ↔ i < n ∧ ∃ b, IOptimal t b ∧ flips t.prices b i = true) ∧
      (∀ i, i ∈ fl ↔ i < n ∧ flips t.prices a i = true) ∧
      (∀ i ∈ t.locked, i ∉ poss ∧ i ∉ mand) ∧
      cnt ≤ 2 ^ n ∧ mc ≤ 24000000 ∧ r.dpNodes ≤ lim.nodes := by
  have hf := validFacts hv
  rcases plan_cases hv hp with ⟨_, rfl⟩ | ⟨_, rfl⟩ |
    ⟨dr, d, _, _, hval, hdlt, hsz, hden, _, ⟨_, rfl⟩ | ⟨c, a, hc, hw, _, rfl⟩⟩
  · cases hd
  · cases hd
  · cases hd
  · obtain ⟨_, hB⟩ := bellman_correct (P := t.prices) hval hf.pos hdlt
    obtain ⟨_, hmin, hopt, ⟨hnd, hmem, hcnt⟩, hmand, hposs⟩ := hB c hc
    obtain ⟨a', hw', ha', hlex, hobj⟩ := walkPy_spec hval hf.pos hdlt hc
    rw [hw] at hw'; cases hw'
    obtain ⟨hcount, _, _, _, hlock, hcost⟩ := bellman_bounds (P := t.prices) hval hf.pos hdlt hc
    have oi := optimal_iff hf hden
    have fi := feasible_iff hf hden
    refine ⟨a, c.cost, c.count, _, _, _, rfl, rfl, rfl, rfl, rfl, rfl,
      ⟨(oi a).1 hlex.1, fun b hb => hlex.2 b ((oi b).2 hb)⟩, hobj,
      fun b hb => hmin b ((fi b).2 hb),
      ⟨_, hnd, fun b => (hmem b).trans (oi b), hcnt⟩, ?_, ?_, ?_, ?_, hcount, ?_, hsz⟩
    · intro i
      simp only [bitsOf, List.mem_filter, List.mem_range, hmand i]
      constructor
      · rintro ⟨hi, h⟩; exact ⟨hi, fun b hb => h b ((oi b).2 hb)⟩
      · rintro ⟨hi, h⟩; exact ⟨hi, fun b hb => h b ((oi b).1 hb)⟩
    · intro i
      simp only [bitsOf, List.mem_filter, List.mem_range, hposs i]
      constructor
      · rintro ⟨hi, b, hb, h⟩; exact ⟨hi, b, (oi b).1 hb, h⟩
      · rintro ⟨hi, b, hb, h⟩; exact ⟨hi, b, (oi b).2 hb, h⟩
    · intro i; simp
    · intro i hi
      have hl : t.prices.lock i = true := by simp [ITask.prices, hi]
      obtain ⟨h1, h2⟩ := hlock i hl
      simp [bitsOf, h1, h2]
    · have := hcost 1000000 hf.le
      have : n * 1000000 ≤ 24 * 1000000 := Nat.mul_le_mul_right _ hf.nle
      omega

theorem plan_flags {t : ITask n} {lim : Limits} {r : IReceipt n} (hv : t.validB = true)
    (hp : plan t lim = .ok r) : r.pcsAuthority = false ∧ r.leanKernelChecked = false := by
  rcases plan_cases hv hp with ⟨_, rfl⟩ | ⟨_, rfl⟩ | ⟨_, _, _, _, _, _, _, _, _, ⟨_, rfl⟩ | ⟨_, _, _, _, _, rfl⟩⟩ <;>
    exact ⟨rfl, rfl⟩

/-- Exact JavaScript integer representation: `2^24 ≤ 2^53` and `24,000,000 < 2^53`. -/
theorem js_safe_bounds : 2 ^ 24 < 2 ^ 53 ∧ 24000000 < 2 ^ 53 := by decide

/-! ## Proposal audit (`audit_proposal`) -/

structure Audit (n : Nat) where
  assignment : List Bool
  assumptionsTrue : List Bool
  targetTrue : Bool
  lockViolations : List Nat
  feasible : Bool
  cost : Nat
  gap : Option Int
  planner : IReceipt n
  pcsAuthority : Bool
  deriving DecidableEq, Repr

/-- Audit a proposed total assignment and attach an exact optimality gap when known. -/
def auditProposal (t : ITask n) (a : List Bool) (lim : Limits) : Except String (Audit n) :=
  if a.length ≠ n then .error "proposal must assign every declared variable" else
  match plan t lim with
  | .error e => .error e
  | .ok r =>
    let prem := t.problem.assumptions.map (fun f => f.eval (envOf a))
    let target := t.problem.source.eval (envOf a)
    let viol := t.locked.filter (fun i => a.getD i false != t.baseline.getD i false)
    let cost := t.cost a
    let feasible := prem.all id && target && viol.isEmpty
    .ok { assignment := a, assumptionsTrue := prem, targetTrue := target, lockViolations := viol,
          feasible := feasible, cost := cost,
          gap := if feasible && r.decision == .optimalPlan then
                   r.minimumCost.map (fun m => (cost : Int) - m) else none,
          planner := r, pcsAuthority := false }

theorem audit_unfold {t : ITask n} {a : List Bool} {lim : Limits} {au : Audit n}
    (h : auditProposal t a lim = .ok au) :
    a.length = n ∧ plan t lim = .ok au.planner ∧
    au.feasible = ((t.problem.assumptions.map (fun f => f.eval (envOf a))).all id &&
      t.problem.source.eval (envOf a) &&
      (t.locked.filter (fun i => a.getD i false != t.baseline.getD i false)).isEmpty) ∧
    au.cost = t.cost a ∧
    au.gap = (if au.feasible && au.planner.decision == .optimalPlan then
      au.planner.minimumCost.map (fun m => (t.cost a : Int) - m) else none) ∧
    au.pcsAuthority = false := by
  unfold auditProposal at h
  split at h
  · cases h
  · rename_i hl
    split at h
    · cases h
    · rename_i r hr
      cases h
      exact ⟨Classical.byContradiction hl, hr, rfl, rfl, rfl, rfl⟩

/-- **Audit feasibility is exactly premises ∧ target ∧ locks.** -/
theorem audit_feasible_iff {t : ITask n} {a : List Bool} {lim : Limits} {au : Audit n}
    (h : auditProposal t a lim = .ok au) : au.feasible = true ↔ IFeasible t a := by
  obtain ⟨hl, _, hfe, _⟩ := audit_unfold h
  rw [hfe]
  simp only [IFeasible, Bool.and_eq_true, List.all_eq_true, List.mem_map, id, List.isEmpty_iff,
    List.filter_eq_nil_iff, bne_iff_ne, ne_eq, Decidable.not_not, allEval]
  constructor
  · rintro ⟨⟨h1, h2⟩, h3⟩
    exact ⟨hl, fun f hf => h1 _ ⟨f, hf, rfl⟩, h2, h3⟩
  · rintro ⟨_, h1, h2, h3⟩
    exact ⟨⟨fun b ⟨f, hf, e⟩ => e ▸ h1 f hf, h2⟩, h3⟩

/-- **Optimality gap**: present only for a feasible proposal against a resolved optimum; it is
nonnegative and zero iff the proposal is optimal. -/
theorem audit_gap {t : ITask n} {a : List Bool} {lim : Limits} {au : Audit n} (hv : t.validB = true)
    (h : auditProposal t a lim = .ok au) {g : Int} (hg : au.gap = some g) :
    IFeasible t a ∧ au.planner.decision = .optimalPlan ∧ 0 ≤ g ∧ (g = 0 ↔ IOptimal t a) := by
  obtain ⟨_, hp, _, _, hgap, _⟩ := audit_unfold h
  rw [hgap] at hg
  split at hg
  · rename_i hc
    simp only [Bool.and_eq_true, beq_iff_eq] at hc
    have hfa := (audit_feasible_iff h).1 hc.1
    obtain ⟨a', mc, _, _, _, _, _, hmc, _, _, _, _, hopt, hcost, hmin, _⟩ := plan_optimal hv hp hc.2
    rw [hmc] at hg
    have hg' : (t.cost a : Int) - mc = g := by simpa using hg
    subst hg'
    have hle := hmin a hfa
    refine ⟨hfa, hc.2, by omega, ?_⟩
    constructor
    · intro h0
      exact ⟨hfa, fun b hb => by have := hmin b hb; omega⟩
    · intro ho
      have := ho.2 a' hopt.1.1
      rw [hcost] at this
      omega
  · cases hg

/-- An unresolved (or non-optimal-plan) planner never supplies a gap. -/
theorem audit_no_gap_unresolved {t : ITask n} {a : List Bool} {lim : Limits} {au : Audit n}
    (h : auditProposal t a lim = .ok au) (hd : au.planner.decision ≠ .optimalPlan) : au.gap = none := by
  obtain ⟨_, _, _, _, hgap, _⟩ := audit_unfold h
  rw [hgap, if_neg (by intro hc; simp only [Bool.and_eq_true, beq_iff_eq] at hc; exact hd hc.2)]

/-- An infeasible proposal never receives a gap, however low its objective. -/
theorem audit_no_gap_infeasible {t : ITask n} {a : List Bool} {lim : Limits} {au : Audit n}
    (h : auditProposal t a lim = .ok au) (hi : ¬ IFeasible t a) : au.gap = none := by
  obtain ⟨_, _, _, _, hgap, _⟩ := audit_unfold h
  have : au.feasible = false := by
    cases hf : au.feasible
    · rfl
    · exact absurd ((audit_feasible_iff h).1 hf) hi
  rw [hgap, this]; rfl

/-- A feasible proposal against a resolved optimum always receives a gap. -/
theorem audit_gap_present {t : ITask n} {a : List Bool} {lim : Limits} {au : Audit n}
    (hv : t.validB = true) (h : auditProposal t a lim = .ok au) (hfa : IFeasible t a)
    (hd : au.planner.decision = .optimalPlan) : au.gap.isSome := by
  obtain ⟨_, hp, _, _, hgap, _⟩ := audit_unfold h
  obtain ⟨_, mc, _, _, _, _, _, hmc, _⟩ := plan_optimal hv hp hd
  rw [hgap, if_pos (by simp [(audit_feasible_iff h).2 hfa, hd]), hmc]
  rfl

end PCSDD
