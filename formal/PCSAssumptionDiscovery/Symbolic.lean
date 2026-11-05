import PCSAssumptionDiscovery.Semantics

/-!
# Symbolic exact assumption discovery

1. **Quantifier elimination on typed formulas.**  `BForm.restrict` fixes one variable to a
   constant, `BForm.exElim` eliminates it existentially (`f[x:=0] ∨ f[x:=1]`) and
   `BForm.rename` re-indexes variables; each comes with its semantic theorem.
2. **Selector projection.**  For every world `w`, `ctxSel p w : BForm k` is the selector-level
   residual of `Context(w, ·)` obtained by eliminating all world variables at the point `w`.
   `selFormula p` is the exact selector predicate

   `(∨_w Context(w,y)) ∧ (∧_{w ⊭ T} ¬Context(w,y)) ∧ locks(y)`,

   and `selector_projection_exact` proves it denotes `Consistent ∧ Sufficient ∧ LocksOK`.
3. **Decision diagram + Bellman.**  `discover` compiles the selector predicate with the
   existing reduced-ordered decision-diagram compiler (`PCSDD.compile`), runs the existing
   positive-cost single Bellman pass with baseline *unselected* and the catalog costs, and
   reconstructs with the existing False-first walk.  The existing theorems
   (`compile_spec`, `bellman_correct`, `bellmanPass_spec`, `walkPy_spec`) transfer to the
   abduction denotation: global optimum, exact number of distinct optimal catalog-index sets,
   mandatory/possible hypotheses, lexicographically least (False-first) optimum.
4. Inconsistent ambient context, absence of any sufficient consistent explanation and work
   exhaustion are separate outcomes.
-/

namespace PCSAssumptionDiscovery

open PCSOmega PCSDD

variable {m k : Nat}

/-! ## Quantifier elimination and renaming on typed formulas -/

namespace BFormOps

/-- Substitute the constant `b` for variable `x`. -/
def restrict {n : Nat} (x : Nat) (b : Bool) : BForm n → BForm n
  | .atom i => if i.val = x then (if b then .tt else .ff) else .atom i
  | .tt => .tt
  | .ff => .ff
  | .not a => .not (restrict x b a)
  | .and a c => .and (restrict x b a) (restrict x b c)
  | .or a c => .or (restrict x b a) (restrict x b c)
  | .imp a c => .imp (restrict x b a) (restrict x b c)

/-- Point update of a valuation. -/
def upd (ρ : Nat → Bool) (x : Nat) (b : Bool) : Nat → Bool := fun i => if i = x then b else ρ i

theorem eval_restrict {n : Nat} (ρ : Nat → Bool) (x : Nat) (b : Bool) (f : BForm n) :
    (restrict x b f).eval ρ = f.eval (upd ρ x b) := by
  induction f with
  | atom i => by_cases h : i.val = x <;> cases b <;> simp [restrict, BForm.eval, upd, h]
  | tt => rfl
  | ff => rfl
  | not a ih => simp [restrict, BForm.eval, ih]
  | and a c iha ihc => simp [restrict, BForm.eval, iha, ihc]
  | or a c iha ihc => simp [restrict, BForm.eval, iha, ihc]
  | imp a c iha ihc => simp [restrict, BForm.eval, iha, ihc]

/-- Existential elimination of variable `x` (Shannon expansion). -/
def exElim {n : Nat} (x : Nat) (f : BForm n) : BForm n := .or (restrict x false f) (restrict x true f)

/-- **Quantification semantics.** -/
theorem eval_exElim {n : Nat} (ρ : Nat → Bool) (x : Nat) (f : BForm n) :
    (exElim x f).eval ρ = true ↔ ∃ b, f.eval (upd ρ x b) = true := by
  simp only [exElim, BForm.eval, Bool.or_eq_true, eval_restrict]
  constructor
  · rintro (h | h)
    · exact ⟨false, h⟩
    · exact ⟨true, h⟩
  · rintro ⟨b, h⟩; cases b
    · exact Or.inl h
    · exact Or.inr h

/-- The eliminated variable no longer occurs. -/
theorem exElim_indep {n : Nat} (ρ : Nat → Bool) (x : Nat) (b : Bool) (f : BForm n) :
    (exElim x f).eval (upd ρ x b) = (exElim x f).eval ρ := by
  have h : ∀ c, upd (upd ρ x b) x c = upd ρ x c := fun c => by
    funext i; by_cases hi : i = x <;> simp [upd, hi]
  simp [exElim, BForm.eval, eval_restrict, h]

/-- Variable renaming along `r : Fin n → Fin n'`. -/
def rename {n n' : Nat} (r : Fin n → Fin n') : BForm n → BForm n'
  | .atom i => .atom (r i)
  | .tt => .tt
  | .ff => .ff
  | .not a => .not (rename r a)
  | .and a c => .and (rename r a) (rename r c)
  | .or a c => .or (rename r a) (rename r c)
  | .imp a c => .imp (rename r a) (rename r c)

/-- **Renaming semantics.** -/
theorem eval_rename {n n' : Nat} (r : Fin n → Fin n') (ρ : Nat → Bool) (f : BForm n) :
    (rename r f).eval ρ = f.eval (fun i => if h : i < n then ρ (r ⟨i, h⟩).val else false) := by
  induction f with
  | atom i => simp [rename, BForm.eval, i.isLt]
  | tt => rfl
  | ff => rfl
  | not a ih => simp [rename, BForm.eval, ih]
  | and a c iha ihc => simp [rename, BForm.eval, iha, ihc]
  | or a c iha ihc => simp [rename, BForm.eval, iha, ihc]
  | imp a c iha ihc => simp [rename, BForm.eval, iha, ihc]

/-- Conjunction of a list. -/
def conjL {n : Nat} : List (BForm n) → BForm n
  | [] => .tt
  | f :: fs => .and f (conjL fs)

/-- Disjunction of a list. -/
def disjL {n : Nat} : List (BForm n) → BForm n
  | [] => .ff
  | f :: fs => .or f (disjL fs)

theorem eval_conjL {n : Nat} (ρ : Nat → Bool) :
    ∀ fs : List (BForm n), (conjL fs).eval ρ = true ↔ ∀ f ∈ fs, f.eval ρ = true
  | [] => by simp [conjL, BForm.eval]
  | f :: fs => by simp [conjL, BForm.eval, eval_conjL ρ fs]

theorem eval_disjL {n : Nat} (ρ : Nat → Bool) :
    ∀ fs : List (BForm n), (disjL fs).eval ρ = true ↔ ∃ f ∈ fs, f.eval ρ = true
  | [] => by simp [disjL, BForm.eval]
  | f :: fs => by simp [disjL, BForm.eval, eval_disjL ρ fs]

/-- Atom by natural index (out of range reads `TRUE`). -/
def atomN {n : Nat} (i : Nat) : BForm n := if h : i < n then .atom ⟨i, h⟩ else .tt

theorem eval_atomN {n : Nat} (ρ : Nat → Bool) {i : Nat} (h : i < n) :
    (atomN i : BForm n).eval ρ = ρ i := by simp [atomN, h, BForm.eval]

end BFormOps

open BFormOps

/-! ## The exact selector predicate -/

/-- Residual of `Context(w, ·)` after eliminating the world variables at the point `w`. -/
def ctxSel (p : Problem m k) (w : List Bool) : BForm k :=
  if p.ambient.eval (envOf w) then
    conjL (((List.range k).filter (fun i => !(p.hyp i).eval (envOf w))).map (fun i => .not (atomN i)))
  else .ff

/-- Lock constraints as a selector formula. -/
def lockF (p : Problem m k) : BForm k :=
  conjL (p.lockedIn.map atomN ++ p.lockedOut.map (fun i => .not (atomN i)))

/-- The exact selector predicate. -/
def selFormula (p : Problem m k) : BForm k :=
  .and (disjL ((allAsg m).map (ctxSel p)))
    (.and (conjL (((allAsg m).filter (fun w => !p.target.eval (envOf w))).map
        (fun w => .not (ctxSel p w)))) (lockF p))

theorem envOf_eq_sel (y : List Bool) (i : Nat) : envOf y i = sel y i := rfl

theorem ctxSel_iff (p : Problem m k) (w y : List Bool) :
    (ctxSel p w).eval (envOf y) = true ↔ Context p w y := by
  unfold ctxSel Context
  by_cases ha : p.ambient.eval (envOf w) = true
  · simp only [ha, if_true, true_and, eval_conjL, List.mem_map, List.mem_filter, List.mem_range]
    constructor
    · intro h i hi hy
      cases hh : (p.hyp i).eval (envOf w)
      · have := h _ ⟨i, ⟨hi, by simp [hh]⟩, rfl⟩
        simp [BForm.eval, eval_atomN _ hi, envOf_eq_sel, hy] at this
      · rfl
    · rintro h f ⟨i, ⟨hi, hh⟩, rfl⟩
      simp only [BForm.eval, eval_atomN _ hi, envOf_eq_sel, Bool.not_eq_true']
      cases hs : sel y i
      · rfl
      · have := h i hi hs; simp [this] at hh
  · simp [ha, BForm.eval]

/-- Locks in range (part of `validB`). -/
def LocksInRange (p : Problem m k) : Prop :=
  (∀ i ∈ p.lockedIn, i < k) ∧ (∀ i ∈ p.lockedOut, i < k)

theorem locksInRange_of_valid {p : Problem m k} (h : p.validB = true) : LocksInRange p := by
  simp only [Problem.validB, Bool.and_eq_true, List.all_eq_true, decide_eq_true_eq] at h
  exact ⟨h.1.2, h.2⟩

theorem lockF_iff {p : Problem m k} (hr : LocksInRange p) (y : List Bool) :
    (lockF p).eval (envOf y) = true ↔ LocksOK p y := by
  unfold lockF LocksOK
  simp only [eval_conjL, List.mem_append, List.mem_map]
  constructor
  · intro h
    refine ⟨fun i hi => ?_, fun i hi => ?_⟩
    · have := h _ (Or.inl ⟨i, hi, rfl⟩); rwa [eval_atomN _ (hr.1 i hi)] at this
    · have := h _ (Or.inr ⟨i, hi, rfl⟩)
      simp only [BForm.eval, eval_atomN _ (hr.2 i hi)] at this; simpa using this
  · rintro ⟨h1, h2⟩ f (⟨i, hi, rfl⟩ | ⟨i, hi, rfl⟩)
    · rw [eval_atomN _ (hr.1 i hi)]; exact h1 i hi
    · simp only [BForm.eval, eval_atomN _ (hr.2 i hi)]; simp [envOf_eq_sel, h2 i hi]

/-- **Selector projection is exact**: the symbolic selector predicate denotes
consistency ∧ sufficiency ∧ locks, with all world variables eliminated. -/
theorem selector_projection_exact {p : Problem m k} (hr : LocksInRange p) (y : List Bool) :
    (selFormula p).eval (envOf y) = true ↔ Consistent p y ∧ Sufficient p y ∧ LocksOK p y := by
  unfold selFormula
  simp only [BForm.eval, Bool.and_eq_true, eval_disjL, eval_conjL, List.mem_map, List.mem_filter,
    lockF_iff hr]
  apply and_congr
  · constructor
    · rintro ⟨f, ⟨w, hw, rfl⟩, h⟩
      exact ⟨w, mem_allAsg.1 hw, (ctxSel_iff p w y).1 h⟩
    · rintro ⟨w, hw, h⟩
      exact ⟨_, ⟨w, mem_allAsg.2 hw, rfl⟩, (ctxSel_iff p w y).2 h⟩
  · apply and_congr _ Iff.rfl
    constructor
    · intro h w hw hc
      cases ht : p.target.eval (envOf w)
      · have := h _ ⟨w, ⟨mem_allAsg.2 hw, by simp [ht]⟩, rfl⟩
        simp only [BForm.eval, Bool.not_eq_true'] at this
        rw [(ctxSel_iff p w y).2 hc] at this; contradiction
      · rfl
    · rintro h f ⟨w, ⟨hw, ht⟩, rfl⟩
      simp only [BForm.eval, Bool.not_eq_true']
      cases hc : (ctxSel p w).eval (envOf y)
      · rfl
      · have := h w (mem_allAsg.1 hw) ((ctxSel_iff p w y).1 hc); simp [this] at ht

/-- **Abduction feasibility**: on length-`k` selectors the selector predicate is exactly
`Feasible`. -/
theorem abduction_feasible_iff {p : Problem m k} (hv : p.validB = true) (y : List Bool)
    (hy : y.length = k) : (selFormula p).eval (envOf y) = true ↔ Feasible p y := by
  rw [selector_projection_exact (locksInRange_of_valid hv)]
  exact ⟨fun h => ⟨hy, h⟩, fun h => h.2⟩

/-! ## Compilation into the positive-cost Bellman machinery -/

/-- Prices: baseline *unselected*, catalog costs, no Bellman-level locks (locks are part of the
selector predicate). -/
def prices (p : Problem m k) : Prices := ⟨fun _ => false, p.cost, fun _ => false⟩

theorem objective_prices (p : Problem m k) {y : List Bool} (hy : y.length = k) :
    objective (prices p) y = selCost p y := by
  unfold objective selCost
  rw [hy]
  congr 1
  apply List.map_congr_left
  intro i _
  cases h : y.getD i false <;> simp only [sel, prices, h] <;> simp

theorem flips_prices (p : Problem m k) {y : List Bool} (hy : y.length = k) {i : Nat} (hi : i < k) :
    flips (prices p) y i = sel y i := by
  simp [flips, prices, hy, hi, sel]

theorem flips_prices_ge (p : Problem m k) {y : List Bool} (hy : y.length = k) {i : Nat} (hi : k ≤ i) :
    flips (prices p) y i = false := by
  simp [flips, hy]; omega

/-- Result of exact discovery. -/
structure Explanation where
  cost : Nat
  count : Nat
  mandatory : List Nat
  possible : List Nat
  selection : List Bool
  indices : List Nat
  deriving DecidableEq, Repr

inductive Outcome where
  | invalid
  | inconsistentAmbient
  | resourceLimit (r : LimitReached)
  | noExplanation
  | internalError
  | optimal (e : Explanation)
  deriving DecidableEq, Repr

/-- Executable ambient-consistency test. -/
def ambientB (p : Problem m k) : Bool := (allAsg m).any (fun w => p.ambient.eval (envOf w))

theorem ambientB_iff (p : Problem m k) : ambientB p = true ↔ AmbientConsistent p := by
  simp [ambientB, AmbientConsistent, mem_allAsg]

/-- **Exact symbolic discovery of all cheapest sufficient consistent explanations.** -/
def discover (p : Problem m k) (lim : Limits) : Outcome :=
  if p.validB = false then .invalid else
  if ambientB p = false then .inconsistentAmbient else
  match compile k lim (selFormula p) Mgr.empty with
  | .error (r, _) => .resourceLimit r
  | .ok (root, mg) =>
    let P := prices p
    let st := bellmanPass mg.nodes P
    match st.cells.getD root none with
    | none => .noExplanation
    | some c =>
      match walkPy mg.nodes st.choices (mg.nodes.size + 1) root (baseList P k) with
      | none => .internalError
      | some a => .optimal ⟨c.cost, c.count, bitsOf k c.mand, bitsOf k c.poss, a, idxSet k a⟩

/-! ## Transfer lemmas -/

section Transfer

variable {p : Problem m k} {ns : Nodes} {root : Nat}

theorem dd_feasible_iff (hv : p.validB = true)
    (hden : ∀ ρ, evalD ns ρ root = (selFormula p).eval ρ) (y : List Bool) :
    PCSDD.Feasible k ns (prices p) root y ↔ Feasible p y := by
  unfold PCSDD.Feasible
  constructor
  · rintro ⟨hl, he, _⟩
    exact (abduction_feasible_iff hv y hl).1 (by rw [← hden]; exact he)
  · intro h
    exact ⟨h.1, by rw [hden]; exact (abduction_feasible_iff hv y h.1).2 h, fun _ _ h => by
      simp [prices] at h⟩

theorem dd_optimal_iff (hv : p.validB = true)
    (hden : ∀ ρ, evalD ns ρ root = (selFormula p).eval ρ) (y : List Bool) :
    PCSDD.Optimal k ns (prices p) root y ↔ Optimal p y := by
  unfold PCSDD.Optimal Optimal
  rw [dd_feasible_iff hv hden]
  constructor
  · rintro ⟨hf, hle⟩
    refine ⟨hf, fun z hz => ?_⟩
    have := hle z ((dd_feasible_iff hv hden z).2 hz)
    rwa [objective_prices p hf.1, objective_prices p hz.1] at this
  · rintro ⟨hf, hle⟩
    refine ⟨hf, fun z hz => ?_⟩
    have hz' := (dd_feasible_iff hv hden z).1 hz
    rw [objective_prices p hf.1, objective_prices p hz'.1]; exact hle z hz'

end Transfer

theorem mem_bitsOf {k mask i : Nat} : i ∈ bitsOf k mask ↔ i < k ∧ mask.testBit i = true := by
  simp [bitsOf]

/-- Decomposition of a successful run. -/
theorem discover_unfold {p : Problem m k} {lim : Limits} {e : Explanation}
    (h : discover p lim = .optimal e) :
    p.validB = true ∧ ∃ root mg c, compile k lim (selFormula p) Mgr.empty = .ok (root, mg) ∧
      (bellmanPass mg.nodes (prices p)).cells.getD root none = some c ∧
      walkPy mg.nodes (bellmanPass mg.nodes (prices p)).choices (mg.nodes.size + 1) root
        (baseList (prices p) k) = some e.selection ∧
      e = ⟨c.cost, c.count, bitsOf k c.mand, bitsOf k c.poss, e.selection, idxSet k e.selection⟩ := by
  unfold discover at h
  split at h
  · cases h
  rename_i hv
  split at h
  · cases h
  split at h
  · cases h
  rename_i root mg hc
  dsimp only at h
  split at h
  · cases h
  rename_i c hcell
  split at h
  · cases h
  rename_i a hw
  cases h
  exact ⟨by simpa using hv, root, mg, c, hc, hcell, hw, rfl⟩

/-- **Global optimum, exact count, mandatory/possible hypotheses, False-first optimum.**
This bundles the principal discovery theorems; the named projections follow. -/
theorem discover_optimal {p : Problem m k} {lim : Limits} {e : Explanation}
    (h : discover p lim = .optimal e) :
    Optimal p e.selection ∧ IsLexLeast (Optimal p) e.selection ∧
    e.cost = selCost p e.selection ∧ (∀ z, Feasible p z → e.cost ≤ selCost p z) ∧
    (∃ L : List (List Bool), L.Nodup ∧ (∀ y, y ∈ L ↔ Optimal p y) ∧ e.count = L.length ∧
        (L.map (idxSet k)).Nodup) ∧
    (∀ i, i ∈ e.mandatory ↔ i < k ∧ ∀ y, Optimal p y → sel y i = true) ∧
    (∀ i, i ∈ e.possible ↔ i < k ∧ ∃ y, Optimal p y ∧ sel y i = true) ∧
    e.indices = idxSet k e.selection := by
  obtain ⟨hv, root, mg, c, hc, hcell, hw, he⟩ := discover_unfold h
  have hpos := Problem.validB_pos hv
  obtain ⟨hinv, _, _, hr, hden⟩ := compile_spec (selFormula p) Mgr.empty root mg (Inv.empty k lim) hc
  have hval := hinv.valid
  have I := bellmanPass_spec (P := prices p) hval
  have hcr : cellRec mg.nodes (prices p) root = some c := by
    rw [Array.getD_eq_getD_getElem?, I.cells root hr] at hcell; simpa using hcell
  have hpos' : ∀ i < k, 0 < (prices p).cost i := hpos
  obtain ⟨_, hB⟩ := bellman_correct hval hpos' hr
  obtain ⟨⟨a0, ha0, ha0c⟩, hmin, hopt, ⟨hnd, hmemL, hcount⟩, hmand, hposs⟩ := hB c hcr
  obtain ⟨a, hwa, _, hlex, hobj⟩ := walkPy_spec hval hpos' hr hcr
  rw [hw] at hwa; cases hwa
  have hO := fun y => dd_optimal_iff (p := p) hv hden y
  have hF := fun y => dd_feasible_iff (p := p) hv hden y
  have hselOpt : Optimal p e.selection := (hO _).1 hlex.1
  have hlen : e.selection.length = k := hselOpt.1.1
  rw [he]
  refine ⟨hselOpt, ⟨hselOpt, fun b hb => hlex.2 b ((hO b).2 hb)⟩, ?_, ?_, ?_, ?_, ?_, rfl⟩
  · dsimp only; rw [← objective_prices p hlen, hobj]
  · intro z hz
    have := hmin z ((hF z).2 hz); rwa [objective_prices p hz.1] at this
  · refine ⟨optList k mg.nodes (prices p) root c.cost, hnd, fun y => by rw [hmemL, hO], hcount, ?_⟩
    refine nodup_map_of_injOn hnd ?_
    intro y hy z hz hyz
    have hy' := ((hO y).1 ((hmemL y).1 hy)).1.1
    have hz' := ((hO z).1 ((hmemL z).1 hz)).1.1
    exact idxSet_inj hy' hz' hyz
  · intro i
    dsimp only
    rw [mem_bitsOf]
    constructor
    · rintro ⟨hi, hb⟩
      refine ⟨hi, fun y hy => ?_⟩
      have := (hmand i).1 hb y ((hO y).2 hy)
      rwa [flips_prices p hy.1.1 hi] at this
    · rintro ⟨hi, hall⟩
      refine ⟨hi, (hmand i).2 fun y hy => ?_⟩
      have hy' := (hO y).1 hy
      rw [flips_prices p hy'.1.1 hi]; exact hall y hy'
  · intro i
    dsimp only
    rw [mem_bitsOf]
    constructor
    · rintro ⟨hi, hb⟩
      obtain ⟨y, hy, hf⟩ := (hposs i).1 hb
      have hy' := (hO y).1 hy
      rw [flips_prices p hy'.1.1 hi] at hf
      exact ⟨hi, y, hy', hf⟩
    · rintro ⟨hi, y, hy, hs⟩
      refine ⟨hi, (hposs i).2 ⟨y, (hO y).2 hy, ?_⟩⟩
      rw [flips_prices p hy.1.1 hi]; exact hs

/-- **Global optimum** (named projection). -/
theorem abduction_global_optimum {p : Problem m k} {lim : Limits} {e : Explanation}
    (h : discover p lim = .optimal e) :
    Feasible p e.selection ∧ e.cost = selCost p e.selection ∧
      ∀ z, Feasible p z → e.cost ≤ selCost p z :=
  let H := discover_optimal h
  ⟨H.1.1, H.2.2.1, H.2.2.2.1⟩

/-- **Exact number of distinct optimal catalog-index sets.** -/
theorem abduction_optimal_count {p : Problem m k} {lim : Limits} {e : Explanation}
    (h : discover p lim = .optimal e) :
    ∃ S : List (List Nat), S.Nodup ∧ e.count = S.length ∧
      ∀ I, I ∈ S ↔ ∃ y, Optimal p y ∧ idxSet k y = I := by
  obtain ⟨L, hnd, hmem, hc, hmap⟩ := (discover_optimal h).2.2.2.2.1
  refine ⟨L.map (idxSet k), hmap, by simp [hc], fun I => ?_⟩
  simp only [List.mem_map]
  constructor
  · rintro ⟨y, hy, rfl⟩; exact ⟨y, (hmem y).1 hy, rfl⟩
  · rintro ⟨y, hy, rfl⟩; exact ⟨y, (hmem y).2 hy, rfl⟩

/-- **Mandatory / possible hypotheses across all optimal explanations.** -/
theorem abduction_mandatory_possible_exact {p : Problem m k} {lim : Limits} {e : Explanation}
    (h : discover p lim = .optimal e) :
    (∀ i, i ∈ e.mandatory ↔ i < k ∧ ∀ y, Optimal p y → i ∈ idxSet k y) ∧
    (∀ i, i ∈ e.possible ↔ i < k ∧ ∃ y, Optimal p y ∧ i ∈ idxSet k y) := by
  obtain ⟨_, _, _, _, _, hm, hp, _⟩ := discover_optimal h
  refine ⟨fun i => ?_, fun i => ?_⟩
  · rw [hm]
    constructor
    · rintro ⟨hi, H⟩; exact ⟨hi, fun y hy => mem_idxSet.2 ⟨hi, H y hy⟩⟩
    · rintro ⟨hi, H⟩; exact ⟨hi, fun y hy => (mem_idxSet.1 (H y hy)).2⟩
  · rw [hp]
    constructor
    · rintro ⟨hi, y, hy, hs⟩; exact ⟨hi, y, hy, mem_idxSet.2 ⟨hi, hs⟩⟩
    · rintro ⟨hi, y, hy, hs⟩; exact ⟨hi, y, hy, (mem_idxSet.1 hs).2⟩

/-- A successful run never reports an internal error. -/
theorem discover_ne_internal (p : Problem m k) (lim : Limits) : discover p lim ≠ .internalError := by
  intro h
  unfold discover at h
  split at h
  · cases h
  rename_i hv
  split at h
  · cases h
  split at h
  · cases h
  rename_i root mg hc
  dsimp only at h
  split at h
  · cases h
  rename_i c hcell
  split at h
  · rename_i hw
    have hv' : p.validB = true := by simpa using hv
    obtain ⟨hinv, _, _, hr, _⟩ := compile_spec (selFormula p) Mgr.empty root mg (Inv.empty k lim) hc
    have I := bellmanPass_spec (P := prices p) hinv.valid
    have hcr : cellRec mg.nodes (prices p) root = some c := by
      rw [Array.getD_eq_getD_getElem?, I.cells root hr] at hcell; simpa using hcell
    obtain ⟨a, hwa, _⟩ := walkPy_spec (P := prices p) hinv.valid (Problem.validB_pos hv') hr hcr
    rw [hw] at hwa; cases hwa
  · cases h

/-- **No sufficient consistent explanation.** -/
theorem discover_noExplanation {p : Problem m k} {lim : Limits}
    (h : discover p lim = .noExplanation) : AmbientConsistent p ∧ ∀ y, ¬ Feasible p y := by
  unfold discover at h
  split at h
  · cases h
  rename_i hv
  split at h
  · cases h
  rename_i ha
  split at h
  · cases h
  rename_i root mg hc
  dsimp only at h
  split at h
  · rename_i hcell
    have hv' : p.validB = true := by simpa using hv
    refine ⟨(ambientB_iff p).1 (by simpa using ha), fun y hy => ?_⟩
    obtain ⟨hinv, _, _, hr, hden⟩ := compile_spec (selFormula p) Mgr.empty root mg (Inv.empty k lim) hc
    have I := bellmanPass_spec (P := prices p) hinv.valid
    have hcr : cellRec mg.nodes (prices p) root = none := by
      rw [Array.getD_eq_getD_getElem?, I.cells root hr] at hcell; simpa using hcell
    obtain ⟨hnone, _⟩ := bellman_correct (P := prices p) hinv.valid (Problem.validB_pos hv') hr
    exact (hnone.1 hcr) y ((dd_feasible_iff hv' hden y).2 hy)
  · split at h <;> cases h

/-- **Inconsistent ambient context** (reported separately; no explanation can exist). -/
theorem discover_inconsistent {p : Problem m k} {lim : Limits}
    (h : discover p lim = .inconsistentAmbient) : ¬ AmbientConsistent p ∧ ∀ y, ¬ Feasible p y := by
  unfold discover at h
  split at h
  · cases h
  split at h
  · rename_i ha
    have hn : ¬ AmbientConsistent p := fun hc => by rw [(ambientB_iff p).2 hc] at ha; simp at ha
    exact ⟨hn, fun y hy => hn hy.consistent_ambient⟩
  · split at h
    · cases h
    · dsimp only at h; split at h
      · cases h
      · split at h <;> cases h

/-- **Budget exhaustion** is an explicit unresolved outcome carrying no semantic claim; it
arises only from the compiler's work limits. -/
theorem discover_resourceLimit {p : Problem m k} {lim : Limits} {r : LimitReached}
    (h : discover p lim = .resourceLimit r) :
    p.validB = true ∧ AmbientConsistent p ∧ ∃ mg, compile k lim (selFormula p) Mgr.empty = .error (r, mg) := by
  unfold discover at h
  split at h
  · cases h
  rename_i hv
  split at h
  · cases h
  rename_i ha
  split at h
  · rename_i r' mg hc
    cases h
    exact ⟨by simpa using hv, (ambientB_iff p).1 (by simpa using ha), mg, hc⟩
  · dsimp only at h; split at h
    · cases h
    · split at h <;> cases h

end PCSAssumptionDiscovery
