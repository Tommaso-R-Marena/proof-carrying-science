import PCSDecisionDiagram.Summary

/-!
# Positive-cost Bellman pass over a valid ordered diagram

Typed reference model of `pcs/experimental/intervention.py::bellman`.

* `Prices` — baseline, change costs and locks, read per variable index.
* `bcell` — the contribution of one branch (`value`, child cell): skipped if the variable is
  locked and `value ≠ baseline`, `none` if the child cell is `none`; otherwise the child cell
  shifted by the flip cost and flip bit.
* `nodeCell` / `cellRec` — the cell of a node is `comb` of its false and true branches
  (`comb` is the two-branch instance of the `min`/winners loop: smaller cost wins; at ties counts
  add, mandatory masks intersect, possible masks unite).
* `candL n ns P k u` — the exact candidate list: one `(objective, flipMask)` pair for every
  feasible suffix of length `n - k` (diagram true, locks respected), enumerated without
  duplicates.
* `summ_cellRec` — **main invariant**: for every valid diagram and **strictly positive**
  costs, `cellRec u` is the exact summary (`Summ`) of `candL n ns P k u` at every level
  `k ≤ topVar u`.  The skipped-variable case uses positivity (`comb_bcell_skip`): a skipped
  variable keeps its baseline in every optimal completion.
-/

namespace PCSDD

open PCSOmega

/-- Baseline, positive change costs and locks of an intervention task, by variable index. -/
structure Prices where
  base : Nat → Bool
  cost : Nat → Nat
  lock : Nat → Bool

namespace Prices

/-- Cost of assigning `x` to variable `k`. -/
def flipC (P : Prices) (k : Nat) (x : Bool) : Nat := if x = P.base k then 0 else P.cost k

/-- Flip bit of assigning `x` to variable `k`. -/
def flipM (P : Prices) (k : Nat) (x : Bool) : Nat := if x = P.base k then 0 else 2 ^ k

/-- Whether assigning `x` to variable `k` respects the locks. -/
def lockOK (P : Prices) (k : Nat) (x : Bool) : Bool := !P.lock k || x == P.base k

end Prices

variable {n : Nat} {ns : Nodes} {P : Prices}

/-- One inspected branch. -/
def bcell (P : Prices) (k : Nat) (x : Bool) (oc : Option Cell) : Option Cell :=
  if P.lockOK k x then oc.map (shiftCell (P.flipC k x) (P.flipM k x)) else none

/-- The cell computation of a node from its two child cells. -/
def nodeCell (P : Prices) (nd : Node) (lo hi : Option Cell) : Option Cell :=
  comb (bcell P nd.var false lo) (bcell P nd.var true hi)

/-- Recursive specification of the Bellman table. -/
def cellRec (ns : Nodes) (P : Prices) (u : Nat) : Option Cell :=
  if u = 0 then none else if u = 1 then some Cell.one else
  match ns[u - 2]? with
  | none => none
  | some nd =>
      if nd.low < u ∧ nd.high < u then
        nodeCell P nd (cellRec ns P nd.low) (cellRec ns P nd.high)
      else none
termination_by u
decreasing_by all_goals omega

theorem cellRec_zero (ns : Nodes) (P : Prices) : cellRec ns P 0 = none := by
  rw [cellRec]; simp

theorem cellRec_one (ns : Nodes) (P : Prices) : cellRec ns P 1 = some Cell.one := by
  rw [cellRec]; simp

theorem cellRec_node {u : Nat} {nd : Node} (hg : getNode ns u = some nd)
    (hl : nd.low < u) (hh : nd.high < u) :
    cellRec ns P u = nodeCell P nd (cellRec ns P nd.low) (cellRec ns P nd.high) := by
  obtain ⟨h2, hi, hnd⟩ := getNode_lt hg
  rw [cellRec]
  have h0 : u ≠ 0 := by omega
  have h1 : u ≠ 1 := by omega
  simp only [h0, h1, ite_false]
  rw [Array.getElem?_eq_getElem hi, hnd]
  simp [hl, hh]

/-! ## Level-indexed candidates -/

/-- Objective of a suffix starting at variable `k`. -/
def objL (P : Prices) : Nat → List Bool → Nat
  | _, [] => 0
  | k, x :: t => objL P (k + 1) t + P.flipC k x

/-- Flip mask of a suffix starting at variable `k`. -/
def maskL (P : Prices) : Nat → List Bool → Nat
  | _, [] => 0
  | k, x :: t => maskL P (k + 1) t ||| P.flipM k x

/-- Lock check of a suffix starting at variable `k`. -/
def locksB (P : Prices) : Nat → List Bool → Bool
  | _, [] => true
  | k, x :: t => P.lockOK k x && locksB P (k + 1) t

/-- Feasibility of a suffix at level `k` for identifier `u`. -/
def feasL (ns : Nodes) (P : Prices) (k u : Nat) (s : List Bool) : Bool :=
  evalD ns (envL k s) u && locksB P k s

/-- Exact candidate list at level `k`. -/
def candL (n : Nat) (ns : Nodes) (P : Prices) (k u : Nat) : List (Nat × Nat) :=
  ((allAsg (n - k)).filter (feasL ns P k u)).map (fun s => (objL P k s, maskL P k s))

theorem mem_candL {k u : Nat} {p : Nat × Nat} :
    p ∈ candL n ns P k u ↔ ∃ s, s.length = n - k ∧ feasL ns P k u s = true ∧
      objL P k s = p.1 ∧ maskL P k s = p.2 := by
  unfold candL
  simp only [List.mem_map, List.mem_filter, mem_allAsg]
  constructor
  · rintro ⟨s, ⟨hl, hf⟩, rfl⟩; exact ⟨s, hl, hf, rfl, rfl⟩
  · rintro ⟨s, hl, hf, h1, h2⟩; exact ⟨s, ⟨hl, hf⟩, by rw [h1, h2]⟩

theorem branch_split (k u ux : Nat) (x : Bool) (A : List (List Bool))
    (hx : ∀ t, evalD ns (envL k (x :: t)) u = evalD ns (envL (k + 1) t) ux) :
    ((A.map (x :: ·)).filter (feasL ns P k u)).map (fun s => (objL P k s, maskL P k s)) =
      (if P.lockOK k x then
        ((A.filter (feasL ns P (k + 1) ux)).map (fun s => (objL P (k + 1) s, maskL P (k + 1) s))).map
          (shiftP (P.flipC k x) (P.flipM k x))
       else []) := by
  rw [List.filter_map, List.map_map]
  split
  · rename_i hl
    rw [List.map_map]
    have : A.filter (feasL ns P k u ∘ (x :: ·)) = A.filter (feasL ns P (k + 1) ux) := by
      apply List.filter_congr
      intro t _
      simp [feasL, hx, locksB, hl]
    rw [this]
    rfl
  · rename_i hl
    have : A.filter (feasL ns P k u ∘ (x :: ·)) = [] := by
      rw [List.filter_eq_nil_iff]
      intro t _
      simp [feasL, locksB, hl]
    rw [this]; rfl

/-- **Shannon split of the candidate list at level `k`.** -/
theorem candL_split {k u u0 u1 : Nat} (hk : k < n)
    (h0 : ∀ t, evalD ns (envL k (false :: t)) u = evalD ns (envL (k + 1) t) u0)
    (h1 : ∀ t, evalD ns (envL k (true :: t)) u = evalD ns (envL (k + 1) t) u1) :
    candL n ns P k u =
      (if P.lockOK k false then (candL n ns P (k + 1) u0).map (shiftP (P.flipC k false) (P.flipM k false))
       else []) ++
      (if P.lockOK k true then (candL n ns P (k + 1) u1).map (shiftP (P.flipC k true) (P.flipM k true))
       else []) := by
  have e : n - k = (n - (k + 1)) + 1 := by omega
  unfold candL
  rw [e, allAsg, List.filter_append, List.map_append, branch_split k u u0 false _ h0,
    branch_split k u u1 true _ h1]

theorem summ_branch {k : Nat} {x : Bool} {l : List (Nat × Nat)} {oc : Option Cell} (h : Summ l oc) :
    Summ (if P.lockOK k x then l.map (shiftP (P.flipC k x) (P.flipM k x)) else []) (bcell P k x oc) := by
  unfold bcell
  split
  · exact h.shift _ _
  · exact Summ.nil

/-- **Skipped variables keep their baseline** (strictly positive cost). -/
theorem comb_bcell_skip {k : Nat} (hpos : 0 < P.cost k) (X : Option Cell) :
    comb (bcell P k false X) (bcell P k true X) = X := by
  have hid : X.map (shiftCell 0 0) = X := by cases X <;> simp [shiftCell_zero]
  cases hb : P.base k
  · have e1 : bcell P k false X = X := by
      simp [bcell, Prices.lockOK, Prices.flipC, Prices.flipM, hb, hid]
    rw [e1]
    unfold bcell
    split
    · have : P.flipC k true = P.cost k := by simp [Prices.flipC, hb]
      rw [this]; exact (comb_shift_pos X hpos _).1
    · cases X <;> rfl
  · have e1 : bcell P k true X = X := by
      simp [bcell, Prices.lockOK, Prices.flipC, Prices.flipM, hb, hid]
    rw [e1]
    unfold bcell
    split
    · have : P.flipC k false = P.cost k := by simp [Prices.flipC, hb]
      rw [this]; exact (comb_shift_pos X hpos _).2
    · rfl

/-- **Main Bellman invariant**: each cell is the exact summary of its feasible suffixes. -/
theorem summ_cellRec (hv : Valid n ns) (hpos : ∀ k < n, 0 < P.cost k) :
    ∀ d k u, n - k = d → u < ns.size + 2 → k ≤ topVar n ns u →
      Summ (candL n ns P k u) (cellRec ns P u) := by
  intro d
  induction d with
  | zero =>
      intro k u hd hu hk
      have hu2 : u < 2 := terminal_of_topVar hv hu (by have := topVar_le hv u; omega)
      unfold candL
      rw [hd]
      rcases (by omega : u = 0 ∨ u = 1) with rfl | rfl
      · simp only [allAsg, feasL, evalD_zero, Bool.false_and, List.filter_cons, List.filter_nil]
        rw [cellRec_zero]; exact Summ.nil
      · simp only [allAsg, feasL, evalD_one, locksB, Bool.and_self, List.filter_cons,
          List.filter_nil, ite_true, List.map_cons, List.map_nil, objL, maskL]
        rw [cellRec_one]; exact Summ.single 0 0
  | succ d ih =>
      intro k u hd hu hk
      have hkn : k < n := by omega
      have skip : k < topVar n ns u → Summ (candL n ns P k u) (cellRec ns P u) := by
        intro hlt
        have hs := evalD_skip hv hlt
        rw [candL_split hkn (u0 := u) (u1 := u) (hs false) (hs true)]
        have := (summ_branch (k := k) (x := false) (P := P) (ih (k + 1) u (by omega) hu (by omega))).append
          (summ_branch (k := k) (x := true) (P := P) (ih (k + 1) u (by omega) hu (by omega)))
        rwa [comb_bcell_skip (hpos k hkn)] at this
      cases hg : getNode ns u with
      | none => exact skip (by simp [topVar, hg]; omega)
      | some nd =>
          have htv := topVar_node (n := n) hg
          by_cases hvar : nd.var = k
          · obtain ⟨_, hl, hh, _, htl, hth⟩ := hv.node hg
            rw [candL_split hkn (u0 := nd.low) (u1 := nd.high)
              (fun t => by rw [evalD_level_node hv hg hvar]; rfl)
              (fun t => by rw [evalD_level_node hv hg hvar]; rfl), cellRec_node hg hl hh]
            unfold nodeCell
            rw [hvar]
            exact (summ_branch (ih (k + 1) nd.low (by omega) (by omega) (by omega))).append
              (summ_branch (ih (k + 1) nd.high (by omega) (by omega) (by omega)))
          · exact skip (by omega)

end PCSDD
