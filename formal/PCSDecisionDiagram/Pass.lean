import PCSDecisionDiagram.Recon

/-!
# The executable single pass and the Python-shaped reconstruction walk

* `inspect` / `stepCell` — a literal transcription of one loop iteration of `bellman`:
  inspect the false then the true branch (skipping locked flips and `null` children), take the
  minimum cost, keep the winners in order, sum counts / intersect mandatory masks / unite
  possible masks over the winners, and record the first winner's value as the choice (so
  False wins a tie).  `stepCell_eq` proves it equals `nodeCell` / `choiceOf`.
* `bellmanPass` — one fold over the append-ordered node table, starting from
  `cells = [null, [0,1,0,0]]`, `choices = [null, null]`.
* `bellmanPass_spec` — for every valid diagram: the pass terminates (it is a structural fold),
  produces exactly `ns.size + 2` cells and choices, performs exactly one cell computation and
  two branch inspections per node, and every cell / choice equals the recursive specification
  (`cellRec`, `choiceRec`), whose meaning is fixed by `bellman_correct` and `recon_spec`.
* `walkPy` — the Python reconstruction loop: start from the baseline, follow recorded choices
  from the root setting each visited variable.  `walkPy_spec`: it reaches the true terminal and
  returns `recon n ns P 0 u` (the lexicographically least optimal total assignment).
-/

namespace PCSDD

open PCSOmega

variable {n : Nat} {ns : Nodes} {P : Prices}

/-- One branch inspection (`bellman`'s inner loop body). -/
def inspect (P : Prices) (cells : Array (Option Cell)) (v : Nat) (x : Bool) (child : Nat) :
    Option (Bool × Cell) :=
  if P.lock v = true ∧ x ≠ P.base v then none else
  match cells.getD child none with
  | none => none
  | some c => some (x, shiftCell (P.flipC v x) (P.flipM v x) c)

/-- Tie merge of a winner into the accumulator. -/
def mergeCell (acc o : Cell) : Cell := ⟨acc.cost, acc.count + o.count, acc.mand &&& o.mand, acc.poss ||| o.poss⟩

/-- The `min` / winners loop over the present branches: `(cell, choice)`. -/
def winnersCell (br : List (Bool × Cell)) : Option Cell × Option Bool :=
  match br with
  | [] => (none, none)
  | p0 :: _ =>
    let best := br.foldl (fun m p => Nat.min m p.2.cost) p0.2.cost
    match br.filter (fun p => p.2.cost == best) with
    | [] => (none, none)
    | w :: others => (some (others.foldl (fun acc p => mergeCell acc p.2) w.2), some w.1)

/-- One node of the pass: `(cell, choice)`. -/
def stepCell (P : Prices) (cells : Array (Option Cell)) (nd : Node) : Option Cell × Option Bool :=
  winnersCell ([inspect P cells nd.var false nd.low, inspect P cells nd.var true nd.high].filterMap id)

/-- With at most two branches the winners loop is `comb`, and False wins a tie. -/
theorem winnersCell_two (bF bT : Option Cell) :
    winnersCell ([bF.map (false, ·), bT.map (true, ·)].filterMap id) =
      (comb bF bT, (comb bF bT).map (fun _ => choiceOf bF bT)) := by
  cases bF with
  | none =>
      cases bT with
      | none => rfl
      | some b => simp [winnersCell, comb, choiceOf]
  | some a =>
      cases bT with
      | none => simp [winnersCell, comb, choiceOf]
      | some b =>
          simp only [winnersCell, Option.map_some, List.filterMap_cons, id, List.filterMap_nil,
            List.foldl_cons, List.foldl_nil, Nat.min_self]
          by_cases h1 : a.cost < b.cost
          · have hm : Nat.min a.cost b.cost = a.cost := by simp only [Nat.min_def]; split <;> omega
            have hb : (b.cost == a.cost) = false := by simp; omega
            simp [hm, List.filter, hb, comb, h1, choiceOf]; omega
          · by_cases h2 : b.cost < a.cost
            · have hm : Nat.min a.cost b.cost = b.cost := by simp only [Nat.min_def]; split <;> omega
              have ha : (a.cost == b.cost) = false := by simp; omega
              simp [hm, List.filter, ha, comb, h1, h2, choiceOf]
            · have e : a.cost = b.cost := by omega
              have hm : Nat.min a.cost b.cost = a.cost := by simp only [Nat.min_def]; split <;> omega
              simp [List.filter, e, comb, choiceOf, mergeCell]

theorem inspect_eq (cells : Array (Option Cell)) (v : Nat) (x : Bool) (child : Nat) :
    inspect P cells v x child = (bcell P v x (cells.getD child none)).map (x, ·) := by
  unfold inspect bcell Prices.lockOK
  by_cases h : P.lock v = true ∧ x ≠ P.base v
  · rw [if_pos h]
    have : (!P.lock v || x == P.base v) = false := by
      obtain ⟨h1, h2⟩ := h; simp [h1, h2]
    rw [this]; rfl
  · rw [if_neg h]
    have : (!P.lock v || x == P.base v) = true := by
      cases hl : P.lock v
      · rfl
      · have : x = P.base v := by
          refine Classical.byContradiction fun hx => h ⟨hl, hx⟩
        simp [this]
    rw [if_pos this]
    cases cells.getD child none <;> rfl

/-- **The literal winners loop equals `comb` / `choiceOf`.** -/
theorem stepCell_eq (cells : Array (Option Cell)) (nd : Node) :
    stepCell P cells nd =
      (nodeCell P nd (cells.getD nd.low none) (cells.getD nd.high none),
       (nodeCell P nd (cells.getD nd.low none) (cells.getD nd.high none)).map
         (fun _ => choiceOf (bcell P nd.var false (cells.getD nd.low none))
           (bcell P nd.var true (cells.getD nd.high none)))) := by
  unfold stepCell nodeCell
  rw [inspect_eq, inspect_eq, winnersCell_two]

/-- Pass state: cells, choices and the work counters. -/
structure PassSt where
  cells : Array (Option Cell)
  choices : Array (Option Bool)
  computations : Nat
  inspections : Nat

/-- `cells = [null, [0,1,0,0]]`, `choices = [null, null]`. -/
def PassSt.init : PassSt := ⟨#[none, some Cell.one], #[none, none], 0, 0⟩

/-- One node: one cell computation, two branch inspections. -/
def passStep (P : Prices) (st : PassSt) (nd : Node) : PassSt :=
  let r := stepCell P st.cells nd
  ⟨st.cells.push r.1, st.choices.push r.2, st.computations + 1, st.inspections + 2⟩

/-- The single Bellman pass over the append-ordered node table. -/
def bellmanPass (ns : Nodes) (P : Prices) : PassSt := ns.foldl (passStep P) PassSt.init

/-- Recursive specification of the recorded choices. -/
def choiceRec (ns : Nodes) (P : Prices) (u : Nat) : Option Bool :=
  match getNode ns u with
  | none => none
  | some nd => (nodeCell P nd (cellRec ns P nd.low) (cellRec ns P nd.high)).map (fun _ => nodeChoice ns P nd)

/-- The pass after the first `j` nodes. -/
def passUpTo (ns : Nodes) (P : Prices) (j : Nat) : PassSt :=
  (ns.toList.take j).foldl (passStep P) PassSt.init

/-- Invariant after `j` nodes. -/
structure PassInv (ns : Nodes) (P : Prices) (j : Nat) (st : PassSt) : Prop where
  cells_size : st.cells.size = j + 2
  choices_size : st.choices.size = j + 2
  computations : st.computations = j
  inspections : st.inspections = 2 * j
  cells : ∀ u < j + 2, st.cells[u]? = some (cellRec ns P u)
  choices : ∀ u < j + 2, st.choices[u]? = some (choiceRec ns P u)

theorem passUpTo_inv (hv : Valid n ns) : ∀ j, j ≤ ns.size → PassInv ns P j (passUpTo ns P j) := by
  intro j
  induction j with
  | zero =>
      intro _
      refine ⟨rfl, rfl, rfl, rfl, ?_, ?_⟩
      · intro u hu
        rcases (by omega : u = 0 ∨ u = 1) with rfl | rfl
        · simp [passUpTo, PassSt.init, cellRec_zero]
        · simp [passUpTo, PassSt.init, cellRec_one]
      · intro u hu
        rcases (by omega : u = 0 ∨ u = 1) with rfl | rfl
        · simp [passUpTo, PassSt.init, choiceRec, getNode]
        · simp [passUpTo, PassSt.init, choiceRec, getNode]
  | succ j ih =>
      intro hj
      have I := ih (by omega)
      have hjs : j < ns.size := by omega
      have hunfold : passUpTo ns P (j + 1) = passStep P (passUpTo ns P j) ns[j] := by
        unfold passUpTo
        rw [List.take_add_one, List.foldl_append, Array.getElem?_toList,
          Array.getElem?_eq_getElem hjs]
        rfl
      rw [hunfold]
      have hg := getNode_idx ns j hjs
      obtain ⟨_, hl, hh, _, _, _⟩ := hv.node hg
      have look : ∀ u < j + 2, (passUpTo ns P j).cells.getD u none = cellRec ns P u := fun u hu => by
        rw [Array.getD_eq_getD_getElem?, I.cells u hu]; rfl
      have hcell : (stepCell P (passUpTo ns P j).cells ns[j]).1 = cellRec ns P (j + 2) := by
        rw [stepCell_eq, look _ hl, look _ hh, cellRec_node hg hl hh]
      have hchoice : (stepCell P (passUpTo ns P j).cells ns[j]).2 = choiceRec ns P (j + 2) := by
        rw [stepCell_eq, look _ hl, look _ hh]
        simp only [choiceRec, hg, nodeChoice]
      refine ⟨by simp [passStep, I.cells_size], by simp [passStep, I.choices_size],
        by simp [passStep, I.computations], by simp [passStep, I.inspections]; omega, ?_, ?_⟩
      · intro u hu
        simp only [passStep, Array.getElem?_push, I.cells_size]
        split
        · rename_i e; subst e; rw [hcell]
        · exact I.cells u (by omega)
      · intro u hu
        simp only [passStep, Array.getElem?_push, I.choices_size]
        split
        · rename_i e; subst e; rw [hchoice]
        · exact I.choices u (by omega)

/-- **Single-pass contract.** -/
theorem bellmanPass_spec (hv : Valid n ns) :
    PassInv ns P ns.size (bellmanPass ns P) := by
  have : bellmanPass ns P = passUpTo ns P ns.size := by
    unfold bellmanPass passUpTo
    rw [← Array.length_toList, List.take_length, Array.foldl_toList]
    rfl
  rw [this]
  exact passUpTo_inv hv _ (Nat.le_refl _)

/-! ## Python-shaped reconstruction walk -/

/-- Follow recorded choices from `root`, setting each visited variable (fuel-bounded). -/
def walkPy (ns : Nodes) (choices : Array (Option Bool)) : Nat → Nat → List Bool → Option (List Bool)
  | 0, _, _ => none
  | fuel + 1, root, asg =>
      if root < 2 then (if root = 1 then some asg else none)
      else match getNode ns root, choices.getD root none with
        | some nd, some x => walkPy ns choices fuel (if x then nd.high else nd.low) (asg.set nd.var x)
        | _, _ => none

/-- The baseline as a total assignment. -/
def baseList (P : Prices) (n : Nat) : List Bool := (List.range n).map P.base

theorem choiceRec_node {u : Nat} {nd : Node} (hg : getNode ns u = some nd) (hl : nd.low < u)
    (hh : nd.high < u) {c : Cell} (hc : cellRec ns P u = some c) :
    choiceRec ns P u = some (nodeChoice ns P nd) := by
  rw [cellRec_node hg hl hh] at hc
  simp [choiceRec, hg, hc]

/-- The chosen branch of a resolved node has a resolved child cell. -/
theorem chosen_child_some {u : Nat} {nd : Node} (hg : getNode ns u = some nd) (hl : nd.low < u)
    (hh : nd.high < u) {c : Cell} (hc : cellRec ns P u = some c) :
    ∃ c', cellRec ns P (if nodeChoice ns P nd then nd.high else nd.low) = some c' := by
  rw [cellRec_node hg hl hh] at hc
  unfold nodeCell at hc
  unfold nodeChoice
  cases hF : bcell P nd.var false (cellRec ns P nd.low) with
  | none =>
      rw [hF] at hc; simp only [comb] at hc
      obtain ⟨_, c', h, _⟩ := bcell_some hc
      exact ⟨c', by simp [choiceOf, h]⟩
  | some a =>
      cases hT : bcell P nd.var true (cellRec ns P nd.high) with
      | none =>
          obtain ⟨_, c', h, _⟩ := bcell_some hF
          exact ⟨c', by simp [choiceOf, h]⟩
      | some b =>
          by_cases hab : b.cost < a.cost
          · obtain ⟨_, c', h, _⟩ := bcell_some hT
            exact ⟨c', by simp [choiceOf, hab, h]⟩
          · obtain ⟨_, c', h, _⟩ := bcell_some hF
            exact ⟨c', by simp [choiceOf, hab, h]⟩

theorem walkPy_level (hv : Valid n ns) {choices : Array (Option Bool)}
    (hch : ∀ u < ns.size + 2, choices.getD u none = choiceRec ns P u) :
    ∀ d k u, n - k = d → u < ns.size + 2 → k ≤ topVar n ns u → ∀ c, cellRec ns P u = some c →
      ∀ fuel asg, u ≤ fuel → asg.length = n → (∀ i, k ≤ i → i < n → asg.getD i false = P.base i) →
        walkPy ns choices fuel u asg = some (asg.take k ++ recon n ns P k u) := by
  intro d
  induction d with
  | zero =>
      intro k u hd hu hk c hc fuel asg hf hl hb
      have hu2 : u < 2 := terminal_of_topVar hv hu (by have := topVar_le hv u; omega)
      have h1 : u = 1 := by
        rcases (by omega : u = 0 ∨ u = 1) with rfl | rfl
        · rw [cellRec_zero] at hc; cases hc
        · rfl
      subst h1
      obtain ⟨f, rfl⟩ : ∃ f, fuel = f + 1 := ⟨fuel - 1, by omega⟩
      have hkn : n ≤ k := by omega
      rw [walkPy, if_pos (by omega), if_pos rfl, recon, if_neg (by omega)]
      simp [List.take_of_length_le (by omega : asg.length ≤ k)]
  | succ d ih =>
      intro k u hd hu hk c hc fuel asg hf hl hb
      have hkn : k < n := by omega
      have htake' : ∀ (l : List Bool) x, k < l.length → l.getD k false = x →
          l.take (k + 1) = l.take k ++ [x] := by
        intro l x this hx
        rw [List.take_add_one]
        congr 1
        rw [List.getElem?_eq_getElem this]
        simp only [List.getD_eq_getElem?_getD, List.getElem?_eq_getElem this, Option.getD_some] at hx
        simp [hx]
      have htake : ∀ x, asg.getD k false = x → asg.take (k + 1) = asg.take k ++ [x] :=
        fun x hx => htake' asg x (by omega) hx
      have skip : k < topVar n ns u → recon n ns P k u = P.base k :: recon n ns P (k + 1) u →
          walkPy ns choices fuel u asg = some (asg.take k ++ recon n ns P k u) := by
        intro hlt hr
        rw [ih (k + 1) u (by omega) hu (by omega) c hc fuel asg hf hl
          (fun i hi hin => hb i (by omega) hin), hr, htake _ (hb k (Nat.le_refl _) hkn)]
        simp
      cases hg : getNode ns u with
      | none =>
          exact skip (by simp [topVar, hg]; omega) (by rw [recon, if_pos hkn]; simp [hg])
      | some nd =>
          have htv := topVar_node (n := n) hg
          by_cases hvar : nd.var = k
          · obtain ⟨_, hl', hh', _, htl, hth⟩ := hv.node hg
            have h2 : 2 ≤ u := (getNode_lt hg).1
            obtain ⟨f, rfl⟩ : ∃ f, fuel = f + 1 := ⟨fuel - 1, by omega⟩
            have hchu := hch u hu
            rw [choiceRec_node hg hl' hh' hc] at hchu
            obtain ⟨c', hc'⟩ := chosen_child_some hg hl' hh' hc
            have hr : recon n ns P k u = nodeChoice ns P nd ::
                recon n ns P (k + 1) (if nodeChoice ns P nd then nd.high else nd.low) := by
              rw [recon, if_pos hkn]; simp [hg, hvar]
            rw [walkPy, if_neg (by omega), hg, hchu, hr]
            simp only
            have hchild : (if nodeChoice ns P nd then nd.high else nd.low) < u := by split <;> omega
            have hchildTop : k + 1 ≤ topVar n ns (if nodeChoice ns P nd then nd.high else nd.low) := by
              split <;> omega
            have hl2 : (asg.set nd.var (nodeChoice ns P nd)).length = n := by simp [hl]
            rw [ih (k + 1) _ (by omega) (by omega) hchildTop c' hc' f _ (by omega) hl2
              (fun i hi hin => by
                rw [List.getD_eq_getElem?_getD, List.getElem?_set_ne (by omega),
                  ← List.getD_eq_getElem?_getD]
                exact hb i (by omega) hin)]
            rw [htake' _ (nodeChoice ns P nd) (by simp; omega) (by
              rw [List.getD_eq_getElem?_getD, hvar, List.getElem?_set_self (by omega)]; rfl)]
            rw [hvar, List.take_set_of_le (Nat.le_refl _)]
            simp
          · exact skip (by omega) (by rw [recon, if_pos hkn]; simp [hg, hvar])

/-- **The Python reconstruction loop returns the lexicographically least optimal total
assignment** (when it is run on the choices produced by the pass). -/
theorem walkPy_spec (hv : Valid n ns) (hpos : ∀ k < n, 0 < P.cost k) {u : Nat}
    (hu : u < ns.size + 2) {c : Cell} (hc : cellRec ns P u = some c) :
    ∃ a, walkPy ns (bellmanPass ns P).choices (ns.size + 1) u (baseList P n) = some a ∧
      a = recon n ns P 0 u ∧ IsLexLeast (Optimal n ns P u) a ∧ objective P a = c.cost := by
  have I := bellmanPass_spec (P := P) hv
  have hch : ∀ w < ns.size + 2, (bellmanPass ns P).choices.getD w none = choiceRec ns P w :=
    fun w hw => by rw [Array.getD_eq_getD_getElem?, I.choices w hw]; rfl
  have := walkPy_level hv hch (n - 0) 0 u rfl hu (Nat.zero_le _) c hc (ns.size + 1) (baseList P n)
    (by omega) (by simp [baseList]) (fun i _ hin => by simp [baseList, List.getD_eq_getElem?_getD, hin])
  simp only [List.take_zero, List.nil_append] at this
  obtain ⟨h1, h2, _⟩ := recon_spec hv hpos hu hc
  exact ⟨_, this, rfl, h1, h2⟩

end PCSDD
