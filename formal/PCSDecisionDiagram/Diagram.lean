import PCSOmega.Formula

/-!
# Validated reduced ordered decision diagrams (append-ordered node table)

Reference model of the diagram representation in `pcs/experimental/conditional.py` and
`public/conditional-core.mjs`: identifiers `0`/`1` are the false/true terminals; identifier
`k ≥ 2` names `nodes[k-2] = [var, low, high]`.

* `Valid n ns` — every node has `var < n`, children that precede it (`low, high < id`),
  strictly increasing variables along edges (terminals have top variable `n`),
  unequal children (reduced) and a unique triple.  `validB` is an executable checker with
  `validB_iff`.
* `evalD` — diagram evaluation, defined independently of formula evaluation.
* `evalD_support` — a diagram rooted at `u` reads only variables `≥ topVar u`.
* `evalD_extend` — appending nodes preserves the meaning of every old identifier.
* `evalD_shannon` — Shannon decomposition at a node; children are independent of the
  node variable.
* `exists_sat`, `exists_unsat`, `eq_zero_iff_unsat`, `eq_one_iff_valid` — constant-root
  completeness: a valid identifier is unsatisfiable iff it is `0`.
* `canonical` — two valid identifiers with the same meaning are equal.
-/

namespace PCSDD

open PCSOmega

/-- A decision-diagram node `[var, low, high]`. -/
structure Node where
  var : Nat
  low : Nat
  high : Nat
  deriving DecidableEq, Repr

abbrev Nodes := Array Node

/-- The node named by identifier `u` (none for terminals and out-of-range identifiers). -/
def getNode (ns : Nodes) (u : Nat) : Option Node := if u < 2 then none else ns[u - 2]?

/-- Top variable; terminals (and invalid identifiers) have top variable `n`. -/
def topVar (n : Nat) (ns : Nodes) (u : Nat) : Nat :=
  match getNode ns u with
  | some nd => nd.var
  | none => n

/-- Local well-formedness of the node at index `i` (identifier `i + 2`). -/
def NodeOK (n : Nat) (ns : Nodes) (i : Nat) (nd : Node) : Prop :=
  nd.var < n ∧ nd.low < i + 2 ∧ nd.high < i + 2 ∧ nd.low ≠ nd.high ∧
    nd.var < topVar n ns nd.low ∧ nd.var < topVar n ns nd.high

/-- Validated reduced ordered diagram over `n` variables. -/
structure Valid (n : Nat) (ns : Nodes) : Prop where
  ok : ∀ i (h : i < ns.size), NodeOK n ns i ns[i]
  uniq : ∀ i j (hi : i < ns.size) (hj : j < ns.size), ns[i] = ns[j] → i = j

/-- Diagram evaluation (independent of formula evaluation). -/
def evalD (ns : Nodes) (ρ : Nat → Bool) (u : Nat) : Bool :=
  if u = 0 then false else if u = 1 then true else
  match ns[u - 2]? with
  | none => false
  | some nd =>
      if nd.low < u ∧ nd.high < u then
        (if ρ nd.var then evalD ns ρ nd.high else evalD ns ρ nd.low)
      else false
termination_by u
decreasing_by all_goals omega

theorem evalD_zero (ns : Nodes) (ρ : Nat → Bool) : evalD ns ρ 0 = false := by
  rw [evalD]; simp

theorem evalD_one (ns : Nodes) (ρ : Nat → Bool) : evalD ns ρ 1 = true := by
  rw [evalD]; simp

theorem getNode_idx (ns : Nodes) (i : Nat) (h : i < ns.size) : getNode ns (i + 2) = some ns[i] := by
  simp [getNode, h]

theorem getNode_lt {ns : Nodes} {u : Nat} {nd : Node} (h : getNode ns u = some nd) :
    2 ≤ u ∧ ∃ hi : u - 2 < ns.size, ns[u - 2] = nd := by
  unfold getNode at h
  split at h
  · cases h
  · refine ⟨by omega, ?_⟩
    rw [Array.getElem?_eq_some_iff] at h
    exact h

theorem getNode_none_of_ge {ns : Nodes} {u : Nat} (h : ns.size + 2 ≤ u) : getNode ns u = none := by
  unfold getNode; split
  · rfl
  · simp; omega

/-- Evaluation at a node identifier, for any locally ordered node. -/
theorem evalD_node {ns : Nodes} {u : Nat} {nd : Node} (hg : getNode ns u = some nd)
    (hl : nd.low < u) (hh : nd.high < u) (ρ : Nat → Bool) :
    evalD ns ρ u = if ρ nd.var then evalD ns ρ nd.high else evalD ns ρ nd.low := by
  obtain ⟨h2, hi, hnd⟩ := getNode_lt hg
  rw [evalD]
  have h0 : u ≠ 0 := by omega
  have h1 : u ≠ 1 := by omega
  simp only [h0, h1, ite_false]
  rw [Array.getElem?_eq_getElem hi, hnd]
  simp [hl, hh]

theorem Valid.node {n : Nat} {ns : Nodes} (hv : Valid n ns) {u : Nat} {nd : Node}
    (hg : getNode ns u = some nd) :
    nd.var < n ∧ nd.low < u ∧ nd.high < u ∧ nd.low ≠ nd.high ∧
      nd.var < topVar n ns nd.low ∧ nd.var < topVar n ns nd.high := by
  obtain ⟨h2, hi, hnd⟩ := getNode_lt hg
  have := hv.ok (u - 2) hi
  rw [hnd] at this
  obtain ⟨a, b, c, d, e, f⟩ := this
  exact ⟨a, by omega, by omega, d, e, f⟩

theorem topVar_le {n : Nat} {ns : Nodes} (hv : Valid n ns) (u : Nat) : topVar n ns u ≤ n := by
  unfold topVar
  split
  · rename_i nd hg; exact Nat.le_of_lt (hv.node hg).1
  · exact Nat.le_refl n

theorem topVar_terminal (n : Nat) (ns : Nodes) {u : Nat} (h : u < 2) : topVar n ns u = n := by
  simp [topVar, getNode, h]

theorem topVar_node {n : Nat} {ns : Nodes} {u : Nat} {nd : Node} (hg : getNode ns u = some nd) :
    topVar n ns u = nd.var := by
  simp [topVar, hg]

/-! ## Support: a diagram reads only variables at or below its top variable -/

theorem evalD_support {n : Nat} {ns : Nodes} (hv : Valid n ns) :
    ∀ u, ∀ ρ σ : Nat → Bool, (∀ v, topVar n ns u ≤ v → ρ v = σ v) → evalD ns ρ u = evalD ns σ u := by
  intro u
  induction u using Nat.strongRecOn with
  | _ u ih =>
    intro ρ σ h
    cases hg : getNode ns u with
    | none =>
        rw [evalD, evalD]
        by_cases h0 : u = 0
        · simp [h0]
        by_cases h1 : u = 1
        · simp [h1]
        simp only [h0, h1, ite_false]
        have : ns[u - 2]? = none := by
          unfold getNode at hg; split at hg
          · omega
          · exact hg
        rw [this]
    | some nd =>
        obtain ⟨hvar, hl, hh, _, htl, hth⟩ := hv.node hg
        rw [evalD_node hg hl hh, evalD_node hg hl hh]
        have htv := topVar_node (n := n) hg
        have e1 : ρ nd.var = σ nd.var := h _ (by omega)
        rw [e1]
        split
        · exact ih _ hh ρ σ (fun v hv' => h v (by omega))
        · exact ih _ hl ρ σ (fun v hv' => h v (by omega))

/-- Update a valuation at one variable. -/
def upd (ρ : Nat → Bool) (v : Nat) (b : Bool) : Nat → Bool := fun x => if x = v then b else ρ x

/-- **Shannon decomposition** at a valid node, with children independent of its variable. -/
theorem evalD_shannon {n : Nat} {ns : Nodes} (hv : Valid n ns) {u : Nat} {nd : Node}
    (hg : getNode ns u = some nd) (ρ : Nat → Bool) :
    evalD ns ρ u = ((ρ nd.var && evalD ns ρ nd.high) || (!ρ nd.var && evalD ns ρ nd.low)) ∧
    (∀ b, evalD ns (upd ρ nd.var b) nd.low = evalD ns ρ nd.low) ∧
    (∀ b, evalD ns (upd ρ nd.var b) nd.high = evalD ns ρ nd.high) ∧
    evalD ns (upd ρ nd.var false) u = evalD ns ρ nd.low ∧
    evalD ns (upd ρ nd.var true) u = evalD ns ρ nd.high := by
  obtain ⟨_, hl, hh, _, htl, hth⟩ := hv.node hg
  have il : ∀ b, evalD ns (upd ρ nd.var b) nd.low = evalD ns ρ nd.low := fun b =>
    evalD_support hv _ _ _ (fun v hv' => by simp [upd]; intro e; omega)
  have ih : ∀ b, evalD ns (upd ρ nd.var b) nd.high = evalD ns ρ nd.high := fun b =>
    evalD_support hv _ _ _ (fun v hv' => by simp [upd]; intro e; omega)
  refine ⟨?_, il, ih, ?_, ?_⟩
  · rw [evalD_node hg hl hh]; cases ρ nd.var <;> simp
  · rw [evalD_node hg hl hh]; simp [upd, il]
  · rw [evalD_node hg hl hh]; simp [upd, ih]

/-! ## Extension preserves old meanings -/

/-- `ns'` extends `ns` by appending nodes. -/
def Extends (ns ns' : Nodes) : Prop :=
  ns.size ≤ ns'.size ∧ ∀ i (h : i < ns.size) (h' : i < ns'.size), ns'[i] = ns[i]

theorem Extends.refl (ns : Nodes) : Extends ns ns := ⟨Nat.le_refl _, fun _ _ _ => rfl⟩

theorem Extends.trans {a b c : Nodes} (h1 : Extends a b) (h2 : Extends b c) : Extends a c :=
  ⟨Nat.le_trans h1.1 h2.1, fun i h h' => by
    rw [h2.2 i (by have := h1.1; omega) h', h1.2 i h (by have := h1.1; omega)]⟩

theorem Extends.push (ns : Nodes) (nd : Node) : Extends ns (ns.push nd) :=
  ⟨by simp, fun i h _ => by simp [Array.getElem_push, h]⟩

theorem Extends.getNode {ns ns' : Nodes} (he : Extends ns ns') {u : Nat} (hu : u < ns.size + 2) :
    getNode ns' u = getNode ns u := by
  unfold PCSDD.getNode
  split
  · rfl
  · have h1 : u - 2 < ns.size := by omega
    have h2 : u - 2 < ns'.size := by have := he.1; omega
    rw [Array.getElem?_eq_getElem h1, Array.getElem?_eq_getElem h2, he.2 _ h1 h2]

theorem Extends.topVar {n : Nat} {ns ns' : Nodes} (he : Extends ns ns') {u : Nat}
    (hu : u < ns.size + 2) : PCSDD.topVar n ns' u = PCSDD.topVar n ns u := by
  unfold PCSDD.topVar; rw [he.getNode hu]

/-- **Appending nodes preserves the meaning of every old identifier.** -/
theorem evalD_extend {n : Nat} {ns ns' : Nodes} (hv : Valid n ns) (he : Extends ns ns') :
    ∀ u, u < ns.size + 2 → ∀ ρ, evalD ns' ρ u = evalD ns ρ u := by
  intro u
  induction u using Nat.strongRecOn with
  | _ u ih =>
    intro hu ρ
    cases hg : getNode ns u with
    | none =>
        have hg' : getNode ns' u = none := by rw [he.getNode hu]; exact hg
        have : u < 2 := by
          unfold getNode at hg; split at hg
          · assumption
          · simp at hg; omega
        rw [evalD, evalD]
        by_cases h0 : u = 0
        · simp [h0]
        · have h1 : u = 1 := by omega
          simp [h1]
    | some nd =>
        obtain ⟨_, hl, hh, _, _, _⟩ := hv.node hg
        have hg' : getNode ns' u = some nd := by rw [he.getNode hu]; exact hg
        rw [evalD_node hg' hl hh, evalD_node hg hl hh,
          ih _ hl (by omega) ρ, ih _ hh (by omega) ρ]

/-! ## Constant-root completeness -/

/-- Every valid non-`0` identifier is satisfiable and every valid non-`1` identifier is
falsifiable. -/
theorem exists_sat_unsat {n : Nat} {ns : Nodes} (hv : Valid n ns) :
    ∀ u, u < ns.size + 2 →
      (u ≠ 0 → ∃ ρ, evalD ns ρ u = true) ∧ (u ≠ 1 → ∃ ρ, evalD ns ρ u = false) := by
  intro u
  induction u using Nat.strongRecOn with
  | _ u ih =>
    intro hu
    cases hg : getNode ns u with
    | none =>
        have : u < 2 := by
          unfold getNode at hg; split at hg
          · assumption
          · simp at hg; omega
        refine ⟨fun h => ⟨fun _ => false, ?_⟩, fun h => ⟨fun _ => false, ?_⟩⟩
        · have : u = 1 := by omega
          subst this; exact evalD_one _ _
        · have : u = 0 := by omega
          subst this; exact evalD_zero _ _
    | some nd =>
        obtain ⟨_, hl, hh, hne, _, _⟩ := hv.node hg
        have ihl := ih _ hl (by omega)
        have ihh := ih _ hh (by omega)
        -- choose a branch and fix the node variable accordingly
        have pick : ∀ (b : Bool) (c : Nat), c = (if b then nd.high else nd.low) →
            ∀ ρ, evalD ns ρ c = evalD ns (upd ρ nd.var b) u := by
          intro b c hc ρ
          have hs := evalD_shannon hv hg ρ
          cases b
          · simp at hc; subst hc; rw [hs.2.2.2.1]
          · simp at hc; subst hc; rw [hs.2.2.2.2]
        refine ⟨fun _ => ?_, fun _ => ?_⟩
        · by_cases h0 : nd.low = 0
          · have : nd.high ≠ 0 := by omega
            obtain ⟨ρ, hρ⟩ := ihh.1 this
            exact ⟨upd ρ nd.var true, by rw [← pick true nd.high (by simp) ρ]; exact hρ⟩
          · obtain ⟨ρ, hρ⟩ := ihl.1 h0
            exact ⟨upd ρ nd.var false, by rw [← pick false nd.low (by simp) ρ]; exact hρ⟩
        · by_cases h1 : nd.low = 1
          · have : nd.high ≠ 1 := by omega
            obtain ⟨ρ, hρ⟩ := ihh.2 this
            exact ⟨upd ρ nd.var true, by rw [← pick true nd.high (by simp) ρ]; exact hρ⟩
          · obtain ⟨ρ, hρ⟩ := ihl.2 h1
            exact ⟨upd ρ nd.var false, by rw [← pick false nd.low (by simp) ρ]; exact hρ⟩

/-- **Root `0` is exactly unsatisfiability** (for valid identifiers). -/
theorem eq_zero_iff_unsat {n : Nat} {ns : Nodes} (hv : Valid n ns) {u : Nat}
    (hu : u < ns.size + 2) : u = 0 ↔ ∀ ρ, evalD ns ρ u = false := by
  constructor
  · intro h ρ; subst h; exact evalD_zero _ _
  · intro h
    refine Classical.byContradiction fun h0 => ?_
    obtain ⟨ρ, hρ⟩ := (exists_sat_unsat hv u hu).1 h0
    rw [h ρ] at hρ; cases hρ

/-- Root `1` is exactly validity. -/
theorem eq_one_iff_valid {n : Nat} {ns : Nodes} (hv : Valid n ns) {u : Nat}
    (hu : u < ns.size + 2) : u = 1 ↔ ∀ ρ, evalD ns ρ u = true := by
  constructor
  · intro h ρ; subst h; exact evalD_one _ _
  · intro h
    refine Classical.byContradiction fun h1 => ?_
    obtain ⟨ρ, hρ⟩ := (exists_sat_unsat hv u hu).2 h1
    rw [h ρ] at hρ; cases hρ

/-! ## Canonicity -/

theorem getNode_some_of_ge2 {ns : Nodes} {u : Nat} (h2 : 2 ≤ u) (hu : u < ns.size + 2) :
    ∃ nd, getNode ns u = some nd := by
  refine ⟨ns[u - 2]'(by omega), ?_⟩
  unfold getNode
  simp [show ¬ u < 2 by omega, Array.getElem?_eq_getElem (show u - 2 < ns.size by omega)]

/-- If a node at variable `v` agrees with an identifier independent of `v`, both of its
children agree with that identifier. -/
theorem children_agree {n : Nat} {ns : Nodes} (hv : Valid n ns) {u w : Nat} {nd : Node}
    (hg : getNode ns u = some nd) (hw : nd.var < topVar n ns w)
    (heq : ∀ ρ, evalD ns ρ u = evalD ns ρ w) :
    (∀ ρ, evalD ns ρ nd.low = evalD ns ρ w) ∧ (∀ ρ, evalD ns ρ nd.high = evalD ns ρ w) := by
  have indep : ∀ ρ b, evalD ns (upd ρ nd.var b) w = evalD ns ρ w := fun ρ b =>
    evalD_support hv _ _ _ (fun v hv' => by simp [upd]; intro e; omega)
  constructor
  · intro ρ
    have hs := evalD_shannon hv hg ρ
    rw [← hs.2.2.2.1, heq, indep]
  · intro ρ
    have hs := evalD_shannon hv hg ρ
    rw [← hs.2.2.2.2, heq, indep]

/-- Two nodes with the same variable whose children agree pairwise. -/
theorem children_agree_same {n : Nat} {ns : Nodes} (hv : Valid n ns) {u w : Nat} {a b : Node}
    (hu : getNode ns u = some a) (hw : getNode ns w = some b) (hab : a.var = b.var)
    (heq : ∀ ρ, evalD ns ρ u = evalD ns ρ w) :
    (∀ ρ, evalD ns ρ a.low = evalD ns ρ b.low) ∧ (∀ ρ, evalD ns ρ a.high = evalD ns ρ b.high) := by
  constructor
  · intro ρ
    have ha := evalD_shannon hv hu ρ
    have hb := evalD_shannon hv hw ρ
    rw [← ha.2.2.2.1, ← hb.2.2.2.1, ← hab, heq]
  · intro ρ
    have ha := evalD_shannon hv hu ρ
    have hb := evalD_shannon hv hw ρ
    rw [← ha.2.2.2.2, ← hb.2.2.2.2, ← hab, heq]

/-- **Canonicity**: valid identifiers with equal meanings are equal. -/
theorem canonical {n : Nat} {ns : Nodes} (hv : Valid n ns) :
    ∀ s u w, u + w = s → u < ns.size + 2 → w < ns.size + 2 →
      (∀ ρ, evalD ns ρ u = evalD ns ρ w) → u = w := by
  intro s
  induction s using Nat.strongRecOn with
  | _ s ih =>
    intro u w hs hu hw heq
    -- one-sided case: `u` is a node whose variable is below the top variable of `w`
    have oneSided : ∀ u w, u + w = s → u < ns.size + 2 → w < ns.size + 2 →
        (∀ ρ, evalD ns ρ u = evalD ns ρ w) → ∀ nd, getNode ns u = some nd →
        nd.var < topVar n ns w → False := by
      intro u w hs hu hw heq nd hg hlt
      obtain ⟨_, hl, hh, hne, _, _⟩ := hv.node hg
      obtain ⟨cl, ch⟩ := children_agree hv hg hlt heq
      have e1 := ih (nd.low + w) (by omega) nd.low w rfl (by omega) hw cl
      have e2 := ih (nd.high + w) (by omega) nd.high w rfl (by omega) hw ch
      exact hne (e1.trans e2.symm)
    by_cases hu2 : u < 2
    · by_cases hw2 : w < 2
      · -- terminals
        have h0 := heq (fun _ => false)
        rcases (show u = 0 ∨ u = 1 by omega) with rfl | rfl <;>
          rcases (show w = 0 ∨ w = 1 by omega) with rfl | rfl <;>
          first | rfl | (simp [evalD_zero, evalD_one] at h0)
      · obtain ⟨b, hb⟩ := getNode_some_of_ge2 (by omega) hw
        exact (oneSided w u (by omega) hw hu (fun ρ => (heq ρ).symm) b hb
          (by rw [topVar_terminal n ns hu2]; exact (hv.node hb).1)).elim
    · obtain ⟨a, ha⟩ := getNode_some_of_ge2 (by omega) hu
      by_cases hw2 : w < 2
      · exact (oneSided u w hs hu hw heq a ha
          (by rw [topVar_terminal n ns hw2]; exact (hv.node ha).1)).elim
      · obtain ⟨b, hb⟩ := getNode_some_of_ge2 (by omega) hw
        rcases Nat.lt_trichotomy a.var b.var with hlt | heqv | hgt
        · exact (oneSided u w hs hu hw heq a ha (by rw [topVar_node hb]; exact hlt)).elim
        · obtain ⟨cl, ch⟩ := children_agree_same hv ha hb heqv heq
          obtain ⟨_, hal, hah, _, _, _⟩ := hv.node ha
          obtain ⟨_, hbl, hbh, _, _, _⟩ := hv.node hb
          have e1 := ih (a.low + b.low) (by omega) a.low b.low rfl (by omega) (by omega) cl
          have e2 := ih (a.high + b.high) (by omega) a.high b.high rfl (by omega) (by omega) ch
          have hab : a = b := by
            cases a; cases b; simp only at heqv e1 e2; subst heqv; subst e1; subst e2; rfl
          obtain ⟨_, hi, hai⟩ := getNode_lt ha
          obtain ⟨_, hj, hbj⟩ := getNode_lt hb
          have := hv.uniq _ _ hi hj (by rw [hai, hbj, hab])
          omega
        · exact (oneSided w u (by omega) hw hu (fun ρ => (heq ρ).symm) b hb
            (by rw [topVar_node ha]; exact hgt)).elim

theorem canonical' {n : Nat} {ns : Nodes} (hv : Valid n ns) {u w : Nat}
    (hu : u < ns.size + 2) (hw : w < ns.size + 2) (heq : ∀ ρ, evalD ns ρ u = evalD ns ρ w) :
    u = w :=
  canonical hv _ u w rfl hu hw heq

end PCSDD
