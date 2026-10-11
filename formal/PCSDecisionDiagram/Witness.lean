import PCSDecisionDiagram.Apply

/-!
# Level-indexed suffix semantics and false-first witness extraction

* `envL k s` reads variable `v ≥ k` from position `v - k` of the suffix `s`; at level `0`
  this is `envOf` (`envL_zero`).  `evalD_skip` / `evalD_level_node` / `evalD_level_end`
  describe how a valid diagram consumes one suffix position.
* `wit n ns k u` — false-first walk (`Diagram.world`): at a node, choose `false` iff the low
  child is not `0`; unvisited variables are `false`.
* `wit_least` — for every valid non-`0` identifier, `wit` is the lexicographically least
  satisfying suffix.  `world_spec` packages the total-assignment statement:
  `world` is `none` iff the root is `0` iff it is unsatisfiable; otherwise it returns the
  lexicographically least satisfying total assignment.
-/

namespace PCSDD

open PCSOmega

/-- Level-`k` valuation of a suffix. -/
def envL (k : Nat) (s : List Bool) : Nat → Bool := fun v => if v < k then false else s.getD (v - k) false

theorem envL_zero (s : List Bool) : envL 0 s = envOf s := by
  funext v; simp [envL, envOf]

theorem envL_cons_self (k : Nat) (x : Bool) (s : List Bool) : envL k (x :: s) k = x := by
  simp [envL]

theorem envL_cons_succ {k v : Nat} (x : Bool) (s : List Bool) (h : k + 1 ≤ v) :
    envL k (x :: s) v = envL (k + 1) s v := by
  simp only [envL]
  rw [if_neg (by omega), if_neg (by omega)]
  have : v - k = (v - (k + 1)) + 1 := by omega
  rw [this]; simp

variable {n : Nat} {ns : Nodes}

theorem evalD_skip (hv : Valid n ns) {u k : Nat} (hk : k < topVar n ns u) (x : Bool)
    (s : List Bool) : evalD ns (envL k (x :: s)) u = evalD ns (envL (k + 1) s) u :=
  evalD_support hv u _ _ (fun v hv' => envL_cons_succ x s (by omega))

theorem evalD_level_node (hv : Valid n ns) {u k : Nat} {nd : Node} (hg : getNode ns u = some nd)
    (hk : nd.var = k) (x : Bool) (s : List Bool) :
    evalD ns (envL k (x :: s)) u =
      if x then evalD ns (envL (k + 1) s) nd.high else evalD ns (envL (k + 1) s) nd.low := by
  obtain ⟨_, hl, hh, _, htl, hth⟩ := hv.node hg
  rw [evalD_node hg hl hh, hk, envL_cons_self]
  cases x
  · exact evalD_support hv _ _ _ (fun v hv' => envL_cons_succ false s (by omega))
  · exact evalD_support hv _ _ _ (fun v hv' => envL_cons_succ true s (by omega))

/-- A valid identifier whose top variable is at least `n` is a terminal. -/
theorem terminal_of_topVar (hv : Valid n ns) {u : Nat} (hu : u < ns.size + 2)
    (ht : n ≤ topVar n ns u) : u < 2 := by
  refine Classical.byContradiction fun h2 => ?_
  have := topVar_lt_of_ge2 hv (by omega) hu
  omega

/-- Satisfying suffixes at level `k`. -/
def SatL (n : Nat) (ns : Nodes) (k u : Nat) (s : List Bool) : Prop :=
  s.length = n - k ∧ evalD ns (envL k s) u = true

/-- False-first walk with explicit structural fuel (kernel-reducible). -/
def witF (ns : Nodes) : Nat → Nat → Nat → List Bool
  | 0, _, _ => []
  | d + 1, k, u =>
    match getNode ns u with
    | some nd =>
        if nd.var = k then
          (if nd.low ≠ 0 then false :: witF ns d (k + 1) nd.low else true :: witF ns d (k + 1) nd.high)
        else false :: witF ns d (k + 1) u
    | none => false :: witF ns d (k + 1) u

/-- False-first witness walk at level `k` (fuel `n - k`). -/
def wit (n : Nat) (ns : Nodes) (k u : Nat) : List Bool := witF ns (n - k) k u

theorem wit_eq (n : Nat) (ns : Nodes) (k u : Nat) : wit n ns k u =
    if k < n then
      match getNode ns u with
      | some nd =>
          if nd.var = k then
            (if nd.low ≠ 0 then false :: wit n ns (k + 1) nd.low else true :: wit n ns (k + 1) nd.high)
          else false :: wit n ns (k + 1) u
      | none => false :: wit n ns (k + 1) u
    else [] := by
  unfold wit
  split
  · rename_i hk
    have e : n - k = (n - (k + 1)) + 1 := by omega
    rw [e]; rfl
  · rw [show n - k = 0 by omega]; rfl

theorem wit_length (n : Nat) (ns : Nodes) : ∀ d k u, n - k = d → (wit n ns k u).length = n - k := by
  intro d
  induction d with
  | zero =>
      intro k u h; rw [wit_eq]; split
      · omega
      · simp; omega
  | succ d ih =>
      intro k u h
      have ih' := fun u => ih (k + 1) u (by omega)
      rw [wit_eq]
      split
      · split
        · split
          · split <;> simp [ih'] <;> omega
          · simp [ih']; omega
        · simp [ih']; omega
      · omega

/-- **False-first extraction is the lexicographically least satisfying suffix.** -/
theorem wit_least (hv : Valid n ns) :
    ∀ d k u, n - k = d → u < ns.size + 2 → u ≠ 0 → k ≤ topVar n ns u →
      IsLexLeast (SatL n ns k u) (wit n ns k u) := by
  intro d
  induction d with
  | zero =>
      intro k u hd hu h0 hk
      have h1 : u = 1 := by
        have := terminal_of_topVar hv hu (by have := topVar_le hv u; omega); omega
      subst h1
      rw [wit_eq, if_neg (by omega)]
      refine ⟨⟨by simp; omega, evalD_one _ _⟩, fun b hb => ?_⟩
      left; have := hb.1; cases b
      · rfl
      · simp at this; omega
  | succ d ih =>
      intro k u hd hu h0 hk
      have hkn : k < n := by omega
      have hnil : ¬ SatL n ns k u [] := fun h => by have := h.1; simp at this; omega
      rw [wit_eq, if_pos hkn]
      split
      · rename_i nd hg
        obtain ⟨_, hl, hh, hne, htl, hth⟩ := hv.node hg
        have htv := topVar_node (n := n) hg
        split
        · rename_i hvar
          split
          · rename_i hlow
            refine isLexLeast_cons_false (Q0 := SatL n ns (k + 1) nd.low) (fun t => ?_)
              (ih _ _ (by omega) (by omega) hlow (by omega)) hnil
            simp only [SatL, evalD_level_node hv hg hvar, List.length_cons]
            constructor <;> intro h <;> exact ⟨by omega, h.2⟩
          · rename_i hlow
            simp only [ne_eq, Decidable.not_not] at hlow
            have hhigh : nd.high ≠ 0 := by omega
            refine isLexLeast_cons_true (Q1 := SatL n ns (k + 1) nd.high) (fun t => ?_)
              (fun t h => ?_) (ih _ _ (by omega) (by omega) hhigh (by omega)) hnil
            · simp only [SatL, evalD_level_node hv hg hvar, ite_true, List.length_cons]
              constructor <;> intro h <;> exact ⟨by omega, h.2⟩
            · have := h.2
              rw [evalD_level_node hv hg hvar, if_neg (by simp), hlow, evalD_zero] at this
              cases this
        · rename_i hvar
          have hlt : k < topVar n ns u := by omega
          refine isLexLeast_cons_false (Q0 := SatL n ns (k + 1) u) (fun t => ?_)
            (ih _ _ (by omega) hu h0 (by omega)) hnil
          simp only [SatL, evalD_skip hv hlt, List.length_cons]
          constructor <;> intro h <;> exact ⟨by omega, h.2⟩
      · rename_i hg
        have ht : topVar n ns u = n := by simp [topVar, hg]
        refine isLexLeast_cons_false (Q0 := SatL n ns (k + 1) u) (fun t => ?_)
          (ih _ _ (by omega) hu h0 (by omega)) hnil
        simp only [SatL, evalD_skip hv (show k < topVar n ns u by omega), List.length_cons]
        constructor <;> intro h <;> exact ⟨by omega, h.2⟩

/-- `Diagram.world`: `none` for the false root, otherwise the false-first total assignment. -/
def world (n : Nat) (ns : Nodes) (u : Nat) : Option (List Bool) :=
  if u = 0 then none else some (wit n ns 0 u)

/-- Satisfying total assignments of a diagram identifier. -/
def SatTotal (n : Nat) (ns : Nodes) (u : Nat) (a : List Bool) : Prop :=
  a.length = n ∧ evalD ns (envOf a) u = true

theorem satL_zero_iff (u : Nat) (a : List Bool) : SatL n ns 0 u a ↔ SatTotal n ns u a := by
  simp [SatL, SatTotal, envL_zero]

/-- **Witness extraction contract.** -/
theorem world_spec (hv : Valid n ns) {u : Nat} (hu : u < ns.size + 2) :
    (world n ns u = none ↔ ∀ ρ, evalD ns ρ u = false) ∧
    ∀ w, world n ns u = some w → IsLexLeast (SatTotal n ns u) w := by
  constructor
  · rw [← eq_zero_iff_unsat hv hu]; unfold world; split <;> simp_all
  · intro w hw
    unfold world at hw
    split at hw
    · cases hw
    · rename_i h0
      cases hw
      have := wit_least hv (n - 0) 0 u rfl hu h0 (Nat.zero_le _)
      exact ⟨(satL_zero_iff u _).1 this.1, fun b hb => this.2 b ((satL_zero_iff u b).2 hb)⟩

/-- Fuelled step counter. -/
def witStepsF (ns : Nodes) : Nat → Nat → Nat → Nat
  | 0, _, _ => 0
  | d + 1, k, u =>
    match getNode ns u with
    | some nd =>
        if nd.var = k then
          (if nd.low ≠ 0 then 1 + witStepsF ns d (k + 1) nd.low else 1 + witStepsF ns d (k + 1) nd.high)
        else witStepsF ns d (k + 1) u
    | none => witStepsF ns d (k + 1) u

/-- Number of internal nodes visited by the false-first walk (`witness_steps`). -/
def witSteps (n : Nat) (ns : Nodes) (k u : Nat) : Nat := witStepsF ns (n - k) k u

theorem witSteps_eq (n : Nat) (ns : Nodes) (k u : Nat) : witSteps n ns k u =
    if k < n then
      match getNode ns u with
      | some nd =>
          if nd.var = k then
            (if nd.low ≠ 0 then 1 + witSteps n ns (k + 1) nd.low else 1 + witSteps n ns (k + 1) nd.high)
          else witSteps n ns (k + 1) u
      | none => witSteps n ns (k + 1) u
    else 0 := by
  unfold witSteps
  split
  · rename_i hk
    have e : n - k = (n - (k + 1)) + 1 := by omega
    rw [e]; rfl
  · rw [show n - k = 0 by omega]; rfl

theorem witSteps_le (n : Nat) (ns : Nodes) : ∀ d k u, n - k = d → witSteps n ns k u ≤ n - k := by
  intro d
  induction d with
  | zero => intro k u h; rw [witSteps_eq]; split <;> omega
  | succ d ih =>
      intro k u h
      have ih' := fun u => ih (k + 1) u (by omega)
      rw [witSteps_eq]
      split
      · split
        · split
          · split
            · exact Nat.le_trans (Nat.add_le_add_left (ih' _) 1) (by omega)
            · exact Nat.le_trans (Nat.add_le_add_left (ih' _) 1) (by omega)
          · have := ih' u; omega
        · have := ih' u; omega
      · omega

end PCSDD
