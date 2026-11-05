import PCSDecisionDiagram.Diagram

/-!
# Bounded memoised apply and AST compilation (executable Lean reference protocol)

Reference model of `Diagram.node`, `Diagram.apply` and `Diagram.compile` of
`pcs/experimental/conditional.py` / `public/conditional-core.mjs`:

* `mkNode` — reduction (`low = high` returns the child), unique-table lookup, node budget.
* `apply` — operation budget checked and incremented **before** the memo lookup, so cache
  hits consume budget; commutative argument normalisation; memo table as an association
  list; explicit structural fuel (exhaustion is reported as an operations limit).
  Errors carry the partial manager so that resource-limit receipts can report partial work.
* `compile` — AST compilation (`NOT f = f XOR 1`, `a → b = (a XOR 1) OR b`).

Principal results: `mkNode_spec`, `apply_spec`, `compile_spec` — a *successful* call
preserves the diagram invariants (`Inv`), only appends nodes, and denotes the requested
connective / the AST meaning.  `apply_ops` — every successful call consumes at least one
operation and never exceeds the operation limit.  Failure (`Except.error`) carries no
semantic claim.

Exact operational parity with the Python/JavaScript code (hash maps, recursion order of
side effects, integer encodings) is **not** proved; this is a separate reference protocol.
-/

namespace PCSDD

open PCSOmega

inductive BOp where
  | and
  | or
  | xor
  deriving DecidableEq, Repr

def BOp.app : BOp → Bool → Bool → Bool
  | .and, x, y => x && y
  | .or, x, y => x || y
  | .xor, x, y => x != y

theorem BOp.app_comm (op : BOp) (x y : Bool) : op.app x y = op.app y x := by
  cases op <;> cases x <;> cases y <;> rfl

/-- Work limits (`DEFAULT_LIMITS = {nodes: 4096, operations: 100000}`). -/
structure Limits where
  nodes : Nat
  operations : Nat
  deriving DecidableEq, Repr

def DEFAULT_LIMITS : Limits := ⟨4096, 100000⟩

/-- Limits must lie in `1 … default`. -/
def Limits.valid (l : Limits) : Bool :=
  decide (1 ≤ l.nodes ∧ l.nodes ≤ 4096 ∧ 1 ≤ l.operations ∧ l.operations ≤ 100000)

inductive LimitReached where
  | nodes
  | operations
  deriving DecidableEq, Repr

abbrev MemoEntry := (BOp × Nat × Nat) × Nat

/-- Manager state: node table, memo table and work counters. -/
structure Mgr where
  nodes : Nodes
  memo : List MemoEntry
  ops : Nat
  visits : Nat
  wsteps : Nat
  deriving Repr

def Mgr.empty : Mgr := ⟨#[], [], 0, 0, 0⟩

/-- Unique-table lookup (linear scan reference for the hash map). -/
def findNode (ns : Nodes) (nd : Node) : Option Nat :=
  (List.range ns.size).find? (fun i => ns[i]? == some nd)

theorem findNode_some {ns : Nodes} {nd : Node} {i : Nat} (h : findNode ns nd = some i) :
    ∃ hi : i < ns.size, ns[i] = nd := by
  have hm := List.mem_of_find?_eq_some h
  have hp := List.find?_some h
  simp at hm hp
  exact ⟨hm, by rw [Array.getElem?_eq_some_iff] at hp; exact hp.2⟩

theorem findNode_none {ns : Nodes} {nd : Node} (h : findNode ns nd = none) :
    ∀ i (hi : i < ns.size), ns[i] ≠ nd := by
  intro i hi he
  unfold findNode at h
  rw [List.find?_eq_none] at h
  have := h i (by simp [hi])
  simp [Array.getElem?_eq_getElem hi, he] at this

/-- `Diagram.node`. -/
def mkNode (lim : Limits) (m : Mgr) (v lo hi : Nat) : Except (LimitReached × Mgr) (Nat × Mgr) :=
  if lo = hi then .ok (lo, m) else
  match findNode m.nodes ⟨v, lo, hi⟩ with
  | some i => .ok (i + 2, m)
  | none =>
      if m.nodes.size ≥ lim.nodes then .error (.nodes, m)
      else .ok (m.nodes.size + 2, { m with nodes := m.nodes.push ⟨v, lo, hi⟩ })

/-- Memo validity w.r.t. a node table. -/
def MemoOK (n : Nat) (ns : Nodes) (memo : List MemoEntry) : Prop :=
  ∀ op a b r, ((op, a, b), r) ∈ memo →
    a < ns.size + 2 ∧ b < ns.size + 2 ∧ r < ns.size + 2 ∧
    (∀ ρ, evalD ns ρ r = op.app (evalD ns ρ a) (evalD ns ρ b)) ∧
    min (topVar n ns a) (topVar n ns b) ≤ topVar n ns r

/-- Manager invariant. -/
structure Inv (n : Nat) (lim : Limits) (m : Mgr) : Prop where
  valid : Valid n m.nodes
  size_le : m.nodes.size ≤ lim.nodes
  ops_le : m.ops ≤ lim.operations
  memo : MemoOK n m.nodes m.memo

theorem Inv.empty (n : Nat) (lim : Limits) : Inv n lim Mgr.empty :=
  ⟨⟨fun i h => by simp [Mgr.empty] at h, fun i _ h => by simp [Mgr.empty] at h⟩,
   by simp [Mgr.empty], by simp [Mgr.empty], fun _ _ _ _ h => by simp [Mgr.empty] at h⟩

theorem MemoOK.extend {n : Nat} {ns ns' : Nodes} {memo : List MemoEntry} (hm : MemoOK n ns memo)
    (hv : Valid n ns) (he : Extends ns ns') : MemoOK n ns' memo := by
  intro op a b r hmem
  obtain ⟨ha, hb, hr, hev, htv⟩ := hm op a b r hmem
  have hs := he.1
  refine ⟨by omega, by omega, by omega, ?_, ?_⟩
  · intro ρ
    rw [evalD_extend hv he _ hr, evalD_extend hv he _ ha, evalD_extend hv he _ hb]
    exact hev ρ
  · rw [he.topVar ha, he.topVar hb, he.topVar hr]; exact htv

/-- **Node construction preserves the invariants and denotes the Shannon combination.** -/
theorem mkNode_spec {n : Nat} {lim : Limits} {m m' : Mgr} {v lo hi r : Nat}
    (hinv : Inv n lim m) (hvn : v < n) (hlo : lo < m.nodes.size + 2) (hhi : hi < m.nodes.size + 2)
    (htl : v < topVar n m.nodes lo) (hth : v < topVar n m.nodes hi)
    (h : mkNode lim m v lo hi = .ok (r, m')) :
    Inv n lim m' ∧ Extends m.nodes m'.nodes ∧ m'.memo = m.memo ∧ m'.ops = m.ops ∧
      m'.visits = m.visits ∧ r < m'.nodes.size + 2 ∧ v ≤ topVar n m'.nodes r ∧
      (∀ ρ, evalD m'.nodes ρ r = if ρ v then evalD m.nodes ρ hi else evalD m.nodes ρ lo) := by
  unfold mkNode at h
  split at h
  · rename_i heq
    cases h; subst heq
    refine ⟨hinv, Extends.refl _, rfl, rfl, rfl, hlo, Nat.le_of_lt htl, fun ρ => ?_⟩
    split <;> rfl
  · rename_i hne
    split at h
    · rename_i i hf
      cases h
      obtain ⟨hi', hnd⟩ := findNode_some hf
      have hg : getNode m.nodes (i + 2) = some ⟨v, lo, hi⟩ := by rw [getNode_idx _ _ hi', hnd]
      obtain ⟨_, hl, hh, _, _, _⟩ := hinv.valid.node hg
      refine ⟨hinv, Extends.refl _, rfl, rfl, rfl, by omega, ?_, fun ρ => ?_⟩
      · rw [topVar_node hg]; exact Nat.le_refl _
      · exact evalD_node hg hl hh ρ
    · rename_i hf
      split at h
      · cases h
      · rename_i hsz
        cases h
        have he := Extends.push m.nodes ⟨v, lo, hi⟩
        have hg : getNode (m.nodes.push ⟨v, lo, hi⟩) (m.nodes.size + 2) = some ⟨v, lo, hi⟩ := by
          have := getNode_idx (m.nodes.push ⟨v, lo, hi⟩) m.nodes.size (by simp)
          rw [this]; simp
        have hvalid : Valid n (m.nodes.push ⟨v, lo, hi⟩) := by
          constructor
          · intro i hi'
            simp only [Array.size_push] at hi'
            by_cases hlt : i < m.nodes.size
            · have := hinv.valid.ok i hlt
              rw [Array.getElem_push_lt hlt]
              obtain ⟨a1, a2, a3, a4, a5, a6⟩ := this
              refine ⟨a1, a2, a3, a4, ?_, ?_⟩
              · rw [he.topVar (by omega)]; exact a5
              · rw [he.topVar (by omega)]; exact a6
            · have hi_eq : i = m.nodes.size := by omega
              subst hi_eq
              rw [Array.getElem_push_eq]
              refine ⟨hvn, hlo, hhi, hne, ?_, ?_⟩
              · rw [he.topVar hlo]; exact htl
              · rw [he.topVar hhi]; exact hth
          · intro i j hi' hj' hij
            simp only [Array.size_push] at hi' hj'
            by_cases hi2 : i < m.nodes.size <;> by_cases hj2 : j < m.nodes.size
            · rw [Array.getElem_push_lt hi2, Array.getElem_push_lt hj2] at hij
              exact hinv.valid.uniq i j hi2 hj2 hij
            · have : j = m.nodes.size := by omega
              subst this
              rw [Array.getElem_push_lt hi2, Array.getElem_push_eq] at hij
              exact absurd hij (findNode_none hf i hi2)
            · have : i = m.nodes.size := by omega
              subst this
              rw [Array.getElem_push_lt hj2, Array.getElem_push_eq] at hij
              exact absurd hij.symm (findNode_none hf j hj2)
            · omega
        have hl' : lo < m.nodes.size + 2 := hlo
        refine ⟨⟨hvalid, by simp; omega, hinv.ops_le, hinv.memo.extend hinv.valid he⟩, he, rfl, rfl,
          rfl, by simp, ?_, fun ρ => ?_⟩
        · rw [topVar_node hg]; exact Nat.le_refl _
        · rw [evalD_node hg (by omega) (by omega) ρ]
          simp only
          rw [evalD_extend hinv.valid he _ hhi, evalD_extend hinv.valid he _ hlo]

/-! ## Apply -/

/-- Terminal combination (`a, b ∈ {0, 1}`). -/
def termOp (op : BOp) (a b : Nat) : Nat := if op.app (a == 1) (b == 1) then 1 else 0

/-- Cofactors of `u` with respect to variable `v`. -/
def cof (ns : Nodes) (v u : Nat) : Nat × Nat :=
  match getNode ns u with
  | some nd => if nd.var = v then (nd.low, nd.high) else (u, u)
  | none => (u, u)

def memoLookup (memo : List MemoEntry) (op : BOp) (a b : Nat) : Option Nat :=
  (memo.find? (fun e => e.1 == (op, a, b))).map (·.2)

theorem memoLookup_mem {memo : List MemoEntry} {op : BOp} {a b r : Nat}
    (h : memoLookup memo op a b = some r) : ((op, a, b), r) ∈ memo := by
  unfold memoLookup at h
  cases hf : memo.find? (fun e => e.1 == (op, a, b)) with
  | none => rw [hf] at h; cases h
  | some e =>
      rw [hf] at h; simp at h
      have hm := List.mem_of_find?_eq_some hf
      have hp := List.find?_some hf
      simp at hp
      have : e = ((op, a, b), r) := by
        obtain ⟨k, rr⟩ := e; simp at hp h; subst hp; subst h; rfl
      rw [← this]; exact hm

/-- `Diagram.apply` with structural fuel. -/
def apply (n : Nat) (lim : Limits) : Nat → BOp → Nat → Nat → Mgr → Except (LimitReached × Mgr) (Nat × Mgr)
  | 0, _, _, _, m => .error (.operations, m)
  | fuel + 1, op, a0, b0, m0 =>
    if m0.ops ≥ lim.operations then .error (.operations, m0) else
    let m := { m0 with ops := m0.ops + 1 }
    let a := min a0 b0
    let b := max a0 b0
    match memoLookup m.memo op a b with
    | some r => .ok (r, m)
    | none =>
      if a < 2 ∧ b < 2 then
        .ok (termOp op a b, { m with memo := ((op, a, b), termOp op a b) :: m.memo })
      else
        let v := min (topVar n m.nodes a) (topVar n m.nodes b)
        let ca := cof m.nodes v a
        let cb := cof m.nodes v b
        match apply n lim fuel op ca.1 cb.1 m with
        | .error e => .error e
        | .ok (lo, m1) =>
          match apply n lim fuel op ca.2 cb.2 m1 with
          | .error e => .error e
          | .ok (hi, m2) =>
            match mkNode lim m2 v lo hi with
            | .error e => .error e
            | .ok (r, m3) => .ok (r, { m3 with memo := ((op, a, b), r) :: m3.memo })

theorem evalD_terminal (ns : Nodes) (ρ : Nat → Bool) {a : Nat} (h : a < 2) :
    evalD ns ρ a = (a == 1) := by
  rcases (show a = 0 ∨ a = 1 by omega) with rfl | rfl
  · rw [evalD_zero]; rfl
  · rw [evalD_one]; rfl

theorem termOp_spec (ns : Nodes) (ρ : Nat → Bool) (op : BOp) {a b : Nat} (ha : a < 2) (hb : b < 2) :
    termOp op a b < 2 ∧ evalD ns ρ (termOp op a b) = op.app (evalD ns ρ a) (evalD ns ρ b) := by
  rw [evalD_terminal ns ρ ha, evalD_terminal ns ρ hb]
  unfold termOp
  split
  · rename_i h; exact ⟨by omega, by rw [evalD_one, h]⟩
  · rename_i h; simp at h; exact ⟨by omega, by rw [evalD_zero, h]⟩

/-- Cofactor facts: both cofactors are valid identifiers with top variable above `v`, and
the identifier is their Shannon combination at `v`. -/
theorem cof_spec {n : Nat} {ns : Nodes} (hv : Valid n ns) {v u : Nat} (hu : u < ns.size + 2)
    (hle : v ≤ topVar n ns u) (hvn : v < n) :
    (cof ns v u).1 < ns.size + 2 ∧ (cof ns v u).2 < ns.size + 2 ∧
    v < topVar n ns (cof ns v u).1 ∧ v < topVar n ns (cof ns v u).2 ∧
    ∀ ρ, evalD ns ρ u = if ρ v then evalD ns ρ (cof ns v u).2 else evalD ns ρ (cof ns v u).1 := by
  unfold cof
  split
  · rename_i nd hg
    obtain ⟨_, hl, hh, _, htl, hth⟩ := hv.node hg
    have htv := topVar_node (n := n) hg
    split
    · rename_i hvar
      subst hvar
      exact ⟨by omega, by omega, htl, hth, fun ρ => evalD_node hg hl hh ρ⟩
    · rename_i hvar
      have : v < topVar n ns u := by omega
      exact ⟨hu, hu, this, this, fun ρ => by split <;> rfl⟩
  · rename_i hg
    have : topVar n ns u = n := by simp [topVar, hg]
    exact ⟨hu, hu, by show v < topVar n ns u; omega, by show v < topVar n ns u; omega,
      fun ρ => by split <;> rfl⟩

theorem topVar_lt_of_ge2 {n : Nat} {ns : Nodes} (hv : Valid n ns) {u : Nat} (h2 : 2 ≤ u)
    (hu : u < ns.size + 2) : topVar n ns u < n := by
  obtain ⟨nd, hg⟩ := getNode_some_of_ge2 h2 hu
  rw [topVar_node hg]; exact (hv.node hg).1

/-- **Successful apply preserves the invariants and denotes the requested connective.** -/
theorem apply_spec {n : Nat} {lim : Limits} :
    ∀ fuel op a0 b0 (m0 : Mgr) r (m' : Mgr), Inv n lim m0 →
      a0 < m0.nodes.size + 2 → b0 < m0.nodes.size + 2 →
      apply n lim fuel op a0 b0 m0 = .ok (r, m') →
      Inv n lim m' ∧ Extends m0.nodes m'.nodes ∧ m0.ops < m'.ops ∧ m'.visits = m0.visits ∧
      r < m'.nodes.size + 2 ∧
      min (topVar n m0.nodes a0) (topVar n m0.nodes b0) ≤ topVar n m'.nodes r ∧
      ∀ ρ, evalD m'.nodes ρ r = op.app (evalD m0.nodes ρ a0) (evalD m0.nodes ρ b0)
  | 0, _, _, _, _, _, _, _, _, _, h => by simp [apply] at h
  | fuel + 1, op, a0, b0, m0, r, m', hinv, ha0, hb0, h => by
    unfold apply at h
    split at h
    · cases h
    rename_i hops
    -- normalised arguments
    have hinvm : Inv n lim { m0 with ops := m0.ops + 1 } :=
      ⟨hinv.valid, hinv.size_le, by simp; omega, hinv.memo⟩
    have hsym : ∀ ρ, op.app (evalD m0.nodes ρ (min a0 b0)) (evalD m0.nodes ρ (max a0 b0)) =
        op.app (evalD m0.nodes ρ a0) (evalD m0.nodes ρ b0) := by
      intro ρ
      by_cases hab : a0 ≤ b0
      · rw [Nat.min_eq_left hab, Nat.max_eq_right hab]
      · rw [Nat.min_eq_right (show b0 ≤ a0 by omega), Nat.max_eq_left (show b0 ≤ a0 by omega),
          BOp.app_comm]
    have hsymv : min (topVar n m0.nodes (min a0 b0)) (topVar n m0.nodes (max a0 b0)) =
        min (topVar n m0.nodes a0) (topVar n m0.nodes b0) := by
      by_cases hab : a0 ≤ b0
      · rw [Nat.min_eq_left hab, Nat.max_eq_right hab]
      · rw [Nat.min_eq_right (show b0 ≤ a0 by omega), Nat.max_eq_left (show b0 ≤ a0 by omega),
          Nat.min_comm]
    have ha : min a0 b0 < m0.nodes.size + 2 := by omega
    have hb : max a0 b0 < m0.nodes.size + 2 := by omega
    generalize hA : min a0 b0 = a at *
    generalize hB : max a0 b0 = b at *
    simp only at h
    split at h
    · -- memo hit
      rename_i rr hlook
      cases h
      obtain ⟨_, _, hr, hev, htv⟩ := hinv.memo op a b r (memoLookup_mem hlook)
      refine ⟨hinvm, Extends.refl _, by simp, rfl, hr, by rw [← hsymv]; exact htv, ?_⟩
      intro ρ; rw [← hsym]; exact hev ρ
    · split at h
      · -- terminal case
        rename_i hterm
        cases h
        have ht := fun ρ => termOp_spec m0.nodes ρ op hterm.1 hterm.2
        refine ⟨⟨hinv.valid, hinv.size_le, by simp; omega, ?_⟩, Extends.refl _, by simp, rfl,
          by have := (ht (fun _ => false)).1; simp; omega, ?_, ?_⟩
        · intro op' a' b' r' hmem
          simp only [List.mem_cons] at hmem
          rcases hmem with hmem | hmem
          · simp only [Prod.mk.injEq] at hmem
            obtain ⟨⟨rfl, rfl, rfl⟩, rfl⟩ := hmem
            refine ⟨by omega, by omega, by have := (ht (fun _ => false)).1; omega,
              fun ρ => (ht ρ).2, ?_⟩
            rw [topVar_terminal n m0.nodes (ht (fun _ => false)).1]
            exact Nat.le_trans (Nat.min_le_left _ _) (topVar_le hinv.valid _)
          · exact hinv.memo op' a' b' r' hmem
        · show _ ≤ topVar n m0.nodes (termOp op a b)
          rw [topVar_terminal n m0.nodes (ht (fun _ => false)).1]
          exact Nat.le_trans (Nat.min_le_left _ _) (topVar_le hinv.valid _)
        · intro ρ; rw [← hsym]; exact (ht ρ).2
      · -- recursive case
        rename_i hnt
        have hvn : min (topVar n m0.nodes a) (topVar n m0.nodes b) < n := by
          by_cases h2 : 2 ≤ a
          · exact Nat.lt_of_le_of_lt (Nat.min_le_left _ _) (topVar_lt_of_ge2 hinv.valid h2 ha)
          · have h2b : 2 ≤ b := by omega
            exact Nat.lt_of_le_of_lt (Nat.min_le_right _ _) (topVar_lt_of_ge2 hinv.valid h2b hb)
        generalize hV : min (topVar n m0.nodes a) (topVar n m0.nodes b) = v at *
        have hca := cof_spec hinv.valid ha (by rw [← hV]; exact Nat.min_le_left _ _) hvn
        have hcb := cof_spec hinv.valid hb (by rw [← hV]; exact Nat.min_le_right _ _) hvn
        split at h
        · cases h
        rename_i lo m1 h1
        split at h
        · cases h
        rename_i hi m2 h2
        split at h
        · cases h
        rename_i rr m3 h3
        cases h
        obtain ⟨i1, e1, o1, w1, r1, t1, v1⟩ :=
          apply_spec fuel op _ _ _ lo m1 hinvm hca.1 hcb.1 h1
        have e1' : Extends m0.nodes m1.nodes := e1
        obtain ⟨i2, e2, o2, w2, r2, t2, v2⟩ :=
          apply_spec fuel op _ _ _ hi m2 i1 (by have := e1.1; simp at this; omega)
            (by have := e1.1; simp at this; omega) h2
        have hlo2 : lo < m2.nodes.size + 2 := by have := e2.1; omega
        have htlo : v < topVar n m2.nodes lo := by
          rw [e2.topVar r1]
          exact Nat.lt_of_lt_of_le (Nat.lt_min.2 ⟨hca.2.2.1, hcb.2.2.1⟩) t1
        have hthi : v < topVar n m2.nodes hi := by
          refine Nat.lt_of_lt_of_le ?_ t2
          rw [e1'.topVar hca.2.1, e1'.topVar hcb.2.1]
          exact Nat.lt_min.2 ⟨hca.2.2.2.1, hcb.2.2.2.1⟩
        obtain ⟨i3, e3, mm3, o3, w3, r3, t3, v3⟩ := mkNode_spec i2 hvn hlo2 r2 htlo hthi h3
        have e03 : Extends m0.nodes m3.nodes := e1'.trans (e2.trans e3)
        have ev03 : ∀ x, x < m0.nodes.size + 2 → ∀ ρ, evalD m3.nodes ρ x = evalD m0.nodes ρ x :=
          fun x hx ρ => evalD_extend hinv.valid e03 x hx ρ
        have hsem : ∀ ρ, evalD m3.nodes ρ r = op.app (evalD m0.nodes ρ a) (evalD m0.nodes ρ b) := by
          intro ρ
          rw [v3 ρ, hca.2.2.2.2 ρ, hcb.2.2.2.2 ρ]
          rw [v2 ρ, evalD_extend i1.valid e2 lo r1 ρ, v1 ρ]
          rw [evalD_extend hinv.valid e1' _ hca.2.1 ρ, evalD_extend hinv.valid e1' _ hcb.2.1 ρ]
          cases ρ v <;> rfl
        have htv3 : v ≤ topVar n m3.nodes r := t3
        have hs03 := e03.1
        refine ⟨⟨i3.valid, i3.size_le, i3.ops_le, ?_⟩, e03, ?_, ?_, r3, ?_, ?_⟩
        · intro op' a' b' r' hmem
          simp only [List.mem_cons] at hmem
          rcases hmem with hmem | hmem
          · simp only [Prod.mk.injEq] at hmem
            obtain ⟨⟨rfl, rfl, rfl⟩, rfl⟩ := hmem
            refine ⟨by show _ < m3.nodes.size + 2; omega, by show _ < m3.nodes.size + 2; omega,
              r3, fun ρ => ?_, ?_⟩
            · rw [hsem ρ, ev03 _ ha ρ, ev03 _ hb ρ]
            · rw [e03.topVar ha, e03.topVar hb, hV]; exact htv3
          · exact i3.memo op' a' b' r' hmem
        · show m0.ops < m3.ops
          simp at o1; omega
        · show m3.visits = m0.visits
          rw [w3, w2, w1]
        · show _ ≤ topVar n m3.nodes r
          first | exact htv3 | (rw [← hsymv, hV]; exact htv3) | (rw [← hsymv]; exact htv3)
        · intro ρ; show evalD m3.nodes ρ r = _; rw [hsem ρ, hsym ρ]

/-- Successful apply respects the operation budget (cache hits included). -/
theorem apply_ops_le {n : Nat} {lim : Limits} {fuel : Nat} {op : BOp} {a b r : Nat} {m m' : Mgr}
    (hinv : Inv n lim m) (ha : a < m.nodes.size + 2) (hb : b < m.nodes.size + 2)
    (h : apply n lim fuel op a b m = .ok (r, m')) : m.ops < m'.ops ∧ m'.ops ≤ lim.operations :=
  let hs := apply_spec fuel op a b m r m' hinv ha hb h
  ⟨hs.2.2.1, hs.1.ops_le⟩

/-- A call made with an exhausted operation budget fails (even if it would hit the cache). -/
theorem apply_exhausted {n : Nat} {lim : Limits} (fuel : Nat) (op : BOp) (a b : Nat) (m : Mgr)
    (h : lim.operations ≤ m.ops) : apply n lim fuel op a b m = .error (.operations, m) := by
  cases fuel with
  | zero => rfl
  | succ f => unfold apply; simp [h]

/-! ## AST compilation -/

/-- Structural fuel handed to each top-level `apply` call. -/
def applyFuel (lim : Limits) : Nat := lim.operations + 1

/-- `Diagram.compile`. -/
def compile (n : Nat) (lim : Limits) : BForm n → Mgr → Except (LimitReached × Mgr) (Nat × Mgr)
  | .atom i, m => mkNode lim { m with visits := m.visits + 1 } i.val 0 1
  | .tt, m => .ok (1, { m with visits := m.visits + 1 })
  | .ff, m => .ok (0, { m with visits := m.visits + 1 })
  | .not f, m =>
      match compile n lim f { m with visits := m.visits + 1 } with
      | .error e => .error e
      | .ok (x, m1) => apply n lim (applyFuel lim) .xor x 1 m1
  | .and f g, m =>
      match compile n lim f { m with visits := m.visits + 1 } with
      | .error e => .error e
      | .ok (x, m1) =>
        match compile n lim g m1 with
        | .error e => .error e
        | .ok (y, m2) => apply n lim (applyFuel lim) .and x y m2
  | .or f g, m =>
      match compile n lim f { m with visits := m.visits + 1 } with
      | .error e => .error e
      | .ok (x, m1) =>
        match compile n lim g m1 with
        | .error e => .error e
        | .ok (y, m2) => apply n lim (applyFuel lim) .or x y m2
  | .imp f g, m =>
      match compile n lim f { m with visits := m.visits + 1 } with
      | .error e => .error e
      | .ok (x, m1) =>
        match compile n lim g m1 with
        | .error e => .error e
        | .ok (y, m2) =>
          match apply n lim (applyFuel lim) .xor x 1 m2 with
          | .error e => .error e
          | .ok (nx, m3) => apply n lim (applyFuel lim) .or nx y m3

theorem Inv.visits {n : Nat} {lim : Limits} {m : Mgr} (h : Inv n lim m) (k : Nat) :
    Inv n lim { m with visits := k } := ⟨h.valid, h.size_le, h.ops_le, h.memo⟩

theorem Inv.wsteps {n : Nat} {lim : Limits} {m : Mgr} (h : Inv n lim m) (k : Nat) :
    Inv n lim { m with wsteps := k } := ⟨h.valid, h.size_le, h.ops_le, h.memo⟩

/-- **Successful compilation preserves the invariants and the AST meaning.** -/
theorem compile_spec {n : Nat} {lim : Limits} :
    ∀ (f : BForm n) (m : Mgr) r (m' : Mgr), Inv n lim m → compile n lim f m = .ok (r, m') →
      Inv n lim m' ∧ Extends m.nodes m'.nodes ∧ m.ops ≤ m'.ops ∧ r < m'.nodes.size + 2 ∧
      ∀ ρ, evalD m'.nodes ρ r = f.eval ρ := by
  intro f
  induction f with
  | atom i =>
      intro m r m' hinv h
      simp only [compile] at h
      have hz : (0 : Nat) < m.nodes.size + 2 := by omega
      have ho : (1 : Nat) < m.nodes.size + 2 := by omega
      obtain ⟨i3, e3, _, o3, _, r3, _, v3⟩ := mkNode_spec (hinv.visits (m.visits + 1)) i.isLt hz ho
        (by rw [topVar_terminal n _ (by omega)]; exact i.isLt)
        (by rw [topVar_terminal n _ (by omega)]; exact i.isLt) h
      refine ⟨i3, e3, by rw [o3]; exact Nat.le_refl _, r3, fun ρ => ?_⟩
      rw [v3 ρ, evalD_zero, evalD_one]; simp [BForm.eval]
  | tt =>
      intro m r m' hinv h
      simp only [compile] at h; cases h
      exact ⟨hinv.visits _, Extends.refl _, Nat.le_refl _, by simp, fun ρ => evalD_one _ _⟩
  | ff =>
      intro m r m' hinv h
      simp only [compile] at h; cases h
      exact ⟨hinv.visits _, Extends.refl _, Nat.le_refl _, by simp, fun ρ => evalD_zero _ _⟩
  | not f ih =>
      intro m r m' hinv h
      simp only [compile] at h
      split at h
      · cases h
      rename_i x m1 h1
      obtain ⟨i1, e1, o1, r1, v1⟩ := ih _ x m1 (hinv.visits _) h1
      obtain ⟨i2, e2, o2, _, r2, _, v2⟩ :=
        apply_spec _ _ _ _ _ r m' i1 r1 (by omega) h
      refine ⟨i2, e1.trans e2, by simp at o1; omega, r2, fun ρ => ?_⟩
      rw [v2 ρ, v1 ρ, evalD_one]; simp [BOp.app, BForm.eval]
  | and f g ihf ihg =>
      intro m r m' hinv h
      simp only [compile] at h
      split at h
      · cases h
      rename_i x m1 h1
      split at h
      · cases h
      rename_i y m2 h2
      obtain ⟨i1, e1, o1, r1, v1⟩ := ihf _ x m1 (hinv.visits _) h1
      obtain ⟨i2, e2, o2, r2, v2⟩ := ihg _ y m2 i1 h2
      obtain ⟨i3, e3, o3, _, r3, _, v3⟩ :=
        apply_spec _ _ _ _ _ r m' i2 (by have := e2.1; omega) r2 h
      refine ⟨i3, e1.trans (e2.trans e3), by simp at o1; omega, r3, fun ρ => ?_⟩
      rw [v3 ρ, evalD_extend i1.valid e2 x r1 ρ, v1 ρ, v2 ρ]; rfl
  | or f g ihf ihg =>
      intro m r m' hinv h
      simp only [compile] at h
      split at h
      · cases h
      rename_i x m1 h1
      split at h
      · cases h
      rename_i y m2 h2
      obtain ⟨i1, e1, o1, r1, v1⟩ := ihf _ x m1 (hinv.visits _) h1
      obtain ⟨i2, e2, o2, r2, v2⟩ := ihg _ y m2 i1 h2
      obtain ⟨i3, e3, o3, _, r3, _, v3⟩ :=
        apply_spec _ _ _ _ _ r m' i2 (by have := e2.1; omega) r2 h
      refine ⟨i3, e1.trans (e2.trans e3), by simp at o1; omega, r3, fun ρ => ?_⟩
      rw [v3 ρ, evalD_extend i1.valid e2 x r1 ρ, v1 ρ, v2 ρ]; rfl
  | imp f g ihf ihg =>
      intro m r m' hinv h
      simp only [compile] at h
      split at h
      · cases h
      rename_i x m1 h1
      split at h
      · cases h
      rename_i y m2 h2
      split at h
      · cases h
      rename_i nx m3 h3
      obtain ⟨i1, e1, o1, r1, v1⟩ := ihf _ x m1 (hinv.visits _) h1
      obtain ⟨i2, e2, o2, r2, v2⟩ := ihg _ y m2 i1 h2
      obtain ⟨i3, e3, o3, _, r3, _, v3⟩ :=
        apply_spec _ _ _ _ _ nx m3 i2 (by have := e2.1; omega) (by omega) h3
      obtain ⟨i4, e4, o4, _, r4, _, v4⟩ :=
        apply_spec _ _ _ _ _ r m' i3 r3 (by have := e3.1; omega) h
      refine ⟨i4, e1.trans (e2.trans (e3.trans e4)), by simp at o1; omega, r4, fun ρ => ?_⟩
      rw [v4 ρ, v3 ρ, evalD_extend i2.valid e3 y r2 ρ, evalD_extend i1.valid e2 x r1 ρ,
        v1 ρ, v2 ρ, evalD_one]
      simp [BOp.app, BForm.eval]

end PCSDD
