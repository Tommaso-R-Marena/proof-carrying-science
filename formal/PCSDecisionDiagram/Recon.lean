import PCSDecisionDiagram.Optimal

/-!
# False-before-True reconstruction with baseline completion

* `choiceOf bF bT` — the recorded choice of a node: `false` iff the false branch is present
  and not strictly more expensive than the true branch (False wins a tie).
* `recon n ns P k u` — level walk from `u`: at a node testing variable `k` take the recorded
  choice; a skipped variable (not tested on the path) keeps its baseline value.
* `optC_skip_iff` — **skipped-variable uniqueness**: with strictly positive costs, at a level
  skipped by `u`, every optimal suffix assigns the baseline value to that variable.
* `recon_least` / `recon_spec` — the reconstructed total assignment is the **lexicographically
  least optimal total assignment** (False < True, variable `0` most significant) and has the
  reported objective.
-/

namespace PCSDD

open PCSOmega

variable {n : Nat} {ns : Nodes} {P : Prices}

/-- Recorded choice of a node from its two branch cells. -/
def choiceOf : Option Cell → Option Cell → Bool
  | some a, some b => decide (b.cost < a.cost)
  | some _, none => false
  | none, _ => true

/-- The recorded choice of a node (from the recursive table). -/
def nodeChoice (ns : Nodes) (P : Prices) (nd : Node) : Bool :=
  choiceOf (bcell P nd.var false (cellRec ns P nd.low)) (bcell P nd.var true (cellRec ns P nd.high))

/-- Reconstruction walk with baseline completion. -/
def recon (n : Nat) (ns : Nodes) (P : Prices) (k u : Nat) : List Bool :=
  if k < n then
    match getNode ns u with
    | some nd =>
        if nd.var = k then
          nodeChoice ns P nd :: recon n ns P (k + 1) (if nodeChoice ns P nd then nd.high else nd.low)
        else P.base k :: recon n ns P (k + 1) u
    | none => P.base k :: recon n ns P (k + 1) u
  else []
termination_by n - k

/-- Optimal suffixes at level `k` for objective `c`. -/
def OptC (n : Nat) (ns : Nodes) (P : Prices) (k u c : Nat) (s : List Bool) : Prop :=
  s.length = n - k ∧ feasL ns P k u s = true ∧ objL P k s = c

theorem summ_min {k u : Nat} {c : Cell} (hS : Summ (candL n ns P k u) (some c)) {s : List Bool}
    (hl : s.length = n - k) (hf : feasL ns P k u s = true) : c.cost ≤ objL P k s :=
  hS.minimal c rfl (objL P k s, maskL P k s) (mem_candL.2 ⟨s, hl, hf, rfl, rfl⟩)

theorem summ_none {k u : Nat} (hS : Summ (candL n ns P k u) none) {s : List Bool}
    (hl : s.length = n - k) : feasL ns P k u s = false := by
  cases hf : feasL ns P k u s
  · rfl
  · have : (objL P k s, maskL P k s) ∈ candL n ns P k u := mem_candL.2 ⟨s, hl, hf, rfl, rfl⟩
    rw [hS.none_iff.1 rfl] at this; cases this

/-- One-position unfolding of `OptC`. -/
theorem optC_cons {k u ux C : Nat} (hk : k < n) (x : Bool) (t : List Bool)
    (hx : evalD ns (envL k (x :: t)) u = evalD ns (envL (k + 1) t) ux) :
    OptC n ns P k u C (x :: t) ↔ P.lockOK k x = true ∧ t.length = n - (k + 1) ∧
      feasL ns P (k + 1) ux t = true ∧ objL P (k + 1) t + P.flipC k x = C := by
  simp only [OptC, feasL, hx, locksB, objL, List.length_cons, Bool.and_eq_true]
  constructor
  · rintro ⟨hl, ⟨he, hlk, hls⟩, ho⟩; exact ⟨hlk, by omega, ⟨he, hls⟩, ho⟩
  · rintro ⟨hlk, hl, ⟨he, hls⟩, ho⟩; exact ⟨by omega, ⟨he, hlk, hls⟩, ho⟩

/-- **Skipped-variable uniqueness**: at a level skipped by `u`, optimal suffixes keep the
baseline value. -/
theorem optC_skip_iff (hv : Valid n ns) (hpos : ∀ k < n, 0 < P.cost k) {k u : Nat}
    (hk : k < n) (hu : u < ns.size + 2) (hlt : k < topVar n ns u) {c : Cell}
    (hc : cellRec ns P u = some c) (x : Bool) (t : List Bool) :
    OptC n ns P k u c.cost (x :: t) ↔ x = P.base k ∧ OptC n ns P (k + 1) u c.cost t := by
  have hS := summ_cellRec (P := P) hv hpos (n - (k + 1)) (k + 1) u rfl hu (by omega)
  rw [hc] at hS
  rw [optC_cons hk x t (evalD_skip hv hlt x t)]
  constructor
  · rintro ⟨hlk, hl, hf, ho⟩
    have hmin := summ_min hS hl hf
    by_cases hx : x = P.base k
    · refine ⟨hx, hl, hf, ?_⟩
      simp [Prices.flipC, hx] at ho; exact ho
    · have : P.flipC k x = P.cost k := by simp [Prices.flipC, hx]
      have := hpos k hk
      omega
  · rintro ⟨hx, hl, hf, ho⟩
    exact ⟨by simp [Prices.lockOK, hx], hl, hf, by simp [Prices.flipC, hx, ho]⟩

theorem comb_cost_le {a b c : Cell} (hab : a.cost ≤ b.cost) (h : comb (some a) (some b) = some c) :
    c.cost = a.cost := by
  simp only [comb] at h
  split at h
  · cases h; rfl
  · split at h
    · omega
    · cases h; rfl

theorem comb_lt {a b : Cell} (hab : b.cost < a.cost) : comb (some a) (some b) = some b := by
  simp only [comb]; rw [if_neg (by omega), if_pos hab]

theorem bcell_some {k : Nat} {x : Bool} {oc : Option Cell} {a : Cell} (h : bcell P k x oc = some a) :
    P.lockOK k x = true ∧ ∃ c, oc = some c ∧ a.cost = c.cost + P.flipC k x := by
  unfold bcell at h
  split at h
  · rename_i hl
    cases oc with
    | none => cases h
    | some c => cases h; exact ⟨hl, c, rfl, rfl⟩
  · cases h

/-- **Reconstruction is the lexicographically least optimal suffix.** -/
theorem recon_least (hv : Valid n ns) (hpos : ∀ k < n, 0 < P.cost k) :
    ∀ d k u, n - k = d → u < ns.size + 2 → k ≤ topVar n ns u → ∀ c, cellRec ns P u = some c →
      IsLexLeast (OptC n ns P k u c.cost) (recon n ns P k u) := by
  intro d
  induction d with
  | zero =>
      intro k u hd hu hk c hc
      have hu2 : u < 2 := terminal_of_topVar hv hu (by have := topVar_le hv u; omega)
      have h1 : u = 1 := by
        rcases (by omega : u = 0 ∨ u = 1) with rfl | rfl
        · rw [cellRec_zero] at hc; cases hc
        · rfl
      subst h1
      rw [cellRec_one] at hc; cases hc
      rw [recon, if_neg (by omega)]
      refine ⟨⟨by simp; omega, by simp [feasL, evalD_one, locksB], rfl⟩, fun b hb => ?_⟩
      left; have := hb.1; cases b
      · rfl
      · simp at this; omega
  | succ d ih =>
      intro k u hd hu hk c hc
      have hkn : k < n := by omega
      have hnil : ¬ OptC n ns P k u c.cost [] := fun h => by have := h.1; simp at this; omega
      have skip : k < topVar n ns u → recon n ns P k u = P.base k :: recon n ns P (k + 1) u →
          IsLexLeast (OptC n ns P k u c.cost) (recon n ns P k u) := by
        intro hlt hr
        rw [hr]
        have ihu := ih (k + 1) u (by omega) hu (by omega) c hc
        cases hb : P.base k
        · exact isLexLeast_cons_false (fun t => by
            rw [optC_skip_iff hv hpos hkn hu hlt hc, hb]; simp) ihu hnil
        · exact isLexLeast_cons_true (fun t => by
            rw [optC_skip_iff hv hpos hkn hu hlt hc, hb]; simp)
            (fun t h => by rw [optC_skip_iff hv hpos hkn hu hlt hc, hb] at h; cases h.1) ihu hnil
      cases hg : getNode ns u with
      | none =>
          exact skip (by simp [topVar, hg]; omega) (by rw [recon, if_pos hkn]; simp [hg])
      | some nd =>
          have htv := topVar_node (n := n) hg
          by_cases hvar : nd.var = k
          · obtain ⟨_, hl, hh, _, htl, hth⟩ := hv.node hg
            have hr : recon n ns P k u = nodeChoice ns P nd ::
                recon n ns P (k + 1) (if nodeChoice ns P nd then nd.high else nd.low) := by
              rw [recon, if_pos hkn]; simp [hg, hvar]
            rw [hr]
            have hc' := hc
            rw [cellRec_node hg hl hh] at hc'
            unfold nodeCell at hc'
            have e0 : ∀ t, evalD ns (envL k (false :: t)) u = evalD ns (envL (k + 1) t) nd.low :=
              fun t => by rw [evalD_level_node hv hg hvar]; rfl
            have e1 : ∀ t, evalD ns (envL k (true :: t)) u = evalD ns (envL (k + 1) t) nd.high :=
              fun t => by rw [evalD_level_node hv hg hvar]; rfl
            have hSl := summ_cellRec (P := P) hv hpos _ (k + 1) nd.low rfl (by omega) (by omega)
            have hSh := summ_cellRec (P := P) hv hpos _ (k + 1) nd.high rfl (by omega) (by omega)
            unfold nodeChoice
            rw [hvar] at hc' ⊢
            -- False-branch facts.
            have caseF : ∀ a, bcell P k false (cellRec ns P nd.low) = some a → c.cost = a.cost →
                IsLexLeast (OptC n ns P k u c.cost) (false :: recon n ns P (k + 1) nd.low) := by
              intro a ha hca
              obtain ⟨hlk, cl, hcl, hac⟩ := bcell_some ha
              have ihl := ih (k + 1) nd.low (by omega) (by omega) (by omega) cl hcl
              refine isLexLeast_cons_false (fun t => ?_) ihl hnil
              rw [optC_cons hkn false t (e0 t)]
              simp only [OptC]
              constructor
              · rintro ⟨_, h1, h2, h3⟩; exact ⟨h1, h2, by omega⟩
              · rintro ⟨h1, h2, h3⟩; exact ⟨hlk, h1, h2, by omega⟩
            have caseT : ∀ b, bcell P k true (cellRec ns P nd.high) = some b → c.cost = b.cost →
                (∀ t, ¬ OptC n ns P k u c.cost (false :: t)) →
                IsLexLeast (OptC n ns P k u c.cost) (true :: recon n ns P (k + 1) nd.high) := by
              intro b hb hcb hno
              obtain ⟨hlk, ch, hch, hbc⟩ := bcell_some hb
              have ihh := ih (k + 1) nd.high (by omega) (by omega) (by omega) ch hch
              refine isLexLeast_cons_true (fun t => ?_) hno ihh hnil
              rw [optC_cons hkn true t (e1 t)]
              simp only [OptC]
              constructor
              · rintro ⟨_, h1, h2, h3⟩; exact ⟨h1, h2, by omega⟩
              · rintro ⟨h1, h2, h3⟩; exact ⟨hlk, h1, h2, by omega⟩
            -- No optimal suffix starts with `false` when the false branch is absent or dearer.
            have noF : ∀ C, (∀ a, bcell P k false (cellRec ns P nd.low) = some a → C < a.cost) →
                ∀ t, ¬ OptC n ns P k u C (false :: t) := by
              intro C hC t hopt
              rw [optC_cons hkn false t (e0 t)] at hopt
              obtain ⟨hlk, hl', hf, ho⟩ := hopt
              cases hcl : cellRec ns P nd.low with
              | none =>
                  rw [hcl] at hSl
                  rw [summ_none hSl hl'] at hf; cases hf
              | some cl =>
                  rw [hcl] at hSl
                  have hm := summ_min hSl hl' hf
                  have hbF : bcell P k false (cellRec ns P nd.low) =
                      some (shiftCell (P.flipC k false) (P.flipM k false) cl) := by
                    simp [bcell, hlk, hcl]
                  have := hC _ hbF
                  simp only [shiftCell] at this
                  omega
            cases hF : bcell P k false (cellRec ns P nd.low) with
            | none =>
                rw [hF] at hc'
                simp only [comb] at hc'
                simp only [choiceOf, ite_true]
                exact caseT c hc' rfl (noF _ (fun a ha => by rw [hF] at ha; cases ha))
            | some a =>
                cases hT : bcell P k true (cellRec ns P nd.high) with
                | none =>
                    rw [hF, hT] at hc'
                    simp only [comb] at hc'
                    cases hc'
                    simp only [choiceOf, Bool.false_eq_true, ite_false]
                    exact caseF _ hF rfl
                | some b =>
                    rw [hF, hT] at hc'
                    by_cases hab : b.cost < a.cost
                    · rw [comb_lt hab] at hc'
                      cases hc'
                      simp only [choiceOf, decide_eq_true hab, ite_true]
                      exact caseT c hT rfl (noF _ (fun a' ha' => by
                        rw [hF] at ha'; cases ha'; omega))
                    · have := comb_cost_le (by omega) hc'
                      simp only [choiceOf, decide_eq_false hab, Bool.false_eq_true, ite_false]
                      exact caseF a hF this
          · exact skip (by omega) (by rw [recon, if_pos hkn]; simp [hg, hvar])

/-- **Reconstruction contract at the total-assignment level.** -/
theorem recon_spec (hv : Valid n ns) (hpos : ∀ k < n, 0 < P.cost k) {u : Nat}
    (hu : u < ns.size + 2) {c : Cell} (hc : cellRec ns P u = some c) :
    IsLexLeast (Optimal n ns P u) (recon n ns P 0 u) ∧
      objective P (recon n ns P 0 u) = c.cost ∧ Feasible n ns P u (recon n ns P 0 u) := by
  obtain ⟨_, h⟩ := bellman_correct (P := P) hv hpos hu
  obtain ⟨_, _, hopt, _⟩ := h c hc
  have hiff : ∀ a, OptC n ns P 0 u c.cost a ↔ Optimal n ns P u a := by
    intro a
    rw [hopt, ← feasL_zero_iff, ← objL_zero]
    simp [OptC, and_assoc]
  have hl := recon_least (P := P) hv hpos (n - 0) 0 u rfl hu (Nat.zero_le _) c hc
  have hl' : IsLexLeast (Optimal n ns P u) (recon n ns P 0 u) :=
    ⟨(hiff _).1 hl.1, fun b hb => hl.2 b ((hiff b).2 hb)⟩
  exact ⟨hl', ((hopt _).1 hl'.1).2, hl'.1.1⟩

end PCSDD
