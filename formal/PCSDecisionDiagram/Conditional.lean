import PCSDecisionDiagram.Witness

/-!
# Conditional outcomes: prefix-stopping contexts, witnesses and minimal conflicts

Typed reference model of `pcs/experimental/conditional.py::check`.

* Premises are compiled first, conjoining into the context and **stopping at the first
  inconsistent prefix** (`premLoop`).  `premLoop_spec`: the compiled premises are a prefix of
  the assumptions; the context root denotes their conjunction; if it is not `0`, all
  assumptions were compiled.  Hence prefix inconsistency is full-context inconsistency, and
  in that case the query (source/candidate) is never compiled.
* Deletion-based core shrinking (`shrink`) and per-premise removal witnesses (`coreWits`).
* `check` produces the receipt; principal results:
  `check_inconsistent` (core inconsistent, removal witnesses satisfy the *other core*
  premises, inclusion-minimality; nothing is claimed about premises outside the core),
  `check_equivalent` (a satisfying context witness exists and every satisfying assignment
  gives equal source/candidate values), `check_counterexample` (the returned total
  assignment satisfies every premise, separates the meanings and is lexicographically least
  among such assignments), `check_resource_limit` (no semantic field is populated).
-/

namespace PCSDD

open PCSOmega

variable {n : Nat} {lim : Limits}

/-- `r` denotes the Boolean function `P` in manager `m`. -/
def Denotes (m : Mgr) (r : Nat) (P : (Nat → Bool) → Bool) : Prop :=
  r < m.nodes.size + 2 ∧ ∀ ρ, evalD m.nodes ρ r = P ρ

theorem Denotes.extend {m m' : Mgr} {r : Nat} {P : (Nat → Bool) → Bool} (hinv : Inv n lim m)
    (he : Extends m.nodes m'.nodes) (h : Denotes m r P) : Denotes m' r P :=
  ⟨by have := he.1; have := h.1; omega, fun ρ => by rw [evalD_extend hinv.valid he _ h.1]; exact h.2 ρ⟩

/-- Every recorded root denotes its formula. -/
def RootsOK (m : Mgr) (rs : List (Nat × BForm n)) : Prop :=
  ∀ p ∈ rs, Denotes m p.1 (fun ρ => p.2.eval ρ)

theorem RootsOK.extend {m m' : Mgr} {rs : List (Nat × BForm n)} (hinv : Inv n lim m)
    (he : Extends m.nodes m'.nodes) (h : RootsOK m rs) : RootsOK m' rs :=
  fun p hp => (h p hp).extend hinv he

/-- Conjunction of formula values. -/
def allEval (fs : List (BForm n)) (ρ : Nat → Bool) : Bool := fs.all (fun f => f.eval ρ)

theorem allEval_append (fs gs : List (BForm n)) (ρ : Nat → Bool) :
    allEval (fs ++ gs) ρ = (allEval fs ρ && allEval gs ρ) := by
  simp [allEval, List.all_append]

theorem allEval_take (fs : List (BForm n)) (k : Nat) (ρ : Nat → Bool) (h : allEval fs ρ = true) :
    allEval (fs.take k) ρ = true := by
  simp only [allEval, List.all_eq_true] at *
  exact fun x hx => h x (List.mem_of_mem_take hx)

/-! ## Conjunction of a list of roots (`Diagram.conjunction`) -/

def conjList (n : Nat) (lim : Limits) :
    List (Nat × BForm n) → Nat → Mgr → Except (LimitReached × Mgr) (Nat × Mgr)
  | [], acc, m => .ok (acc, m)
  | p :: ps, acc, m =>
      match apply n lim (applyFuel lim) .and acc p.1 m with
      | .error e => .error e
      | .ok (acc', m') => conjList n lim ps acc' m'

theorem conjList_spec :
    ∀ (ps : List (Nat × BForm n)) (acc : Nat) (m : Mgr) (P : (Nat → Bool) → Bool) r (m' : Mgr),
      Inv n lim m → RootsOK m ps → Denotes m acc P → conjList n lim ps acc m = .ok (r, m') →
      Inv n lim m' ∧ Extends m.nodes m'.nodes ∧
        Denotes m' r (fun ρ => P ρ && allEval (ps.map (·.2)) ρ)
  | [], acc, m, P, r, m', hinv, _, hacc, h => by
      simp only [conjList] at h; cases h
      exact ⟨hinv, Extends.refl _, ⟨hacc.1, fun ρ => by simp [hacc.2 ρ, allEval]⟩⟩
  | p :: ps, acc, m, P, r, m', hinv, hps, hacc, h => by
      simp only [conjList] at h
      split at h
      · cases h
      rename_i acc' m1 h1
      have hp := hps p (List.mem_cons_self ..)
      obtain ⟨i1, e1, _, _, r1, _, v1⟩ := apply_spec _ _ _ _ _ _ _ hinv hacc.1 hp.1 h1
      have hd : Denotes m1 acc' (fun ρ => P ρ && p.2.eval ρ) :=
        ⟨r1, fun ρ => by rw [v1 ρ, hacc.2 ρ, hp.2 ρ]; rfl⟩
      obtain ⟨i2, e2, d2⟩ := conjList_spec ps acc' m1 _ r m' i1
        ((fun q hq => hps q (List.mem_cons_of_mem _ hq)) |> RootsOK.extend hinv e1) hd h
      refine ⟨i2, e1.trans e2, d2.1, fun ρ => ?_⟩
      rw [d2.2 ρ]; simp [allEval, Bool.and_assoc]

theorem denotes_one (m : Mgr) : Denotes m 1 (fun _ => true) :=
  ⟨by omega, fun ρ => evalD_one _ _⟩

/-! ## Premise compilation with prefix stopping -/

def premLoop (n : Nat) (lim : Limits) :
    List (BForm n) → List (Nat × BForm n) → Nat → Mgr →
      Except (LimitReached × Mgr) (List (Nat × BForm n) × Nat × Mgr)
  | [], prs, ctx, m => .ok (prs, ctx, m)
  | f :: fs, prs, ctx, m =>
      match compile n lim f m with
      | .error e => .error e
      | .ok (p, m1) =>
        match apply n lim (applyFuel lim) .and ctx p m1 with
        | .error e => .error e
        | .ok (ctx', m2) =>
          if ctx' = 0 then .ok (prs ++ [(p, f)], 0, m2)
          else premLoop n lim fs (prs ++ [(p, f)]) ctx' m2

/-- **Prefix-stopping premise compilation.** -/
theorem premLoop_spec :
    ∀ (fs : List (BForm n)) (prs : List (Nat × BForm n)) (ctx : Nat) (m : Mgr) prs' ctx' (m' : Mgr),
      Inv n lim m → RootsOK m prs → Denotes m ctx (allEval (prs.map (·.2))) →
      premLoop n lim fs prs ctx m = .ok (prs', ctx', m') →
      Inv n lim m' ∧ Extends m.nodes m'.nodes ∧ RootsOK m' prs' ∧
        Denotes m' ctx' (allEval (prs'.map (·.2))) ∧
        (∃ k, prs'.map (·.2) = prs.map (·.2) ++ fs.take k) ∧
        (ctx' = 0 ∨ prs'.map (·.2) = prs.map (·.2) ++ fs)
  | [], prs, ctx, m, prs', ctx', m', hinv, hr, hc, h => by
      simp only [premLoop] at h; cases h
      exact ⟨hinv, Extends.refl _, hr, hc, ⟨0, by simp⟩, Or.inr (by simp)⟩
  | f :: fs, prs, ctx, m, prs', ctx', m', hinv, hr, hc, h => by
      simp only [premLoop] at h
      split at h
      · cases h
      rename_i p m1 h1
      split at h
      · cases h
      rename_i c2 m2 h2
      obtain ⟨i1, e1, _, r1, v1⟩ := compile_spec f m p m1 hinv h1
      obtain ⟨i2, e2, _, _, r2, _, v2⟩ :=
        apply_spec _ _ _ _ _ _ _ i1 (by have := e1.1; have := hc.1; omega) r1 h2
      have hr2 : RootsOK m2 (prs ++ [(p, f)]) := by
        intro q hq
        rcases List.mem_append.1 hq with hq | hq
        · exact ((hr q hq).extend hinv e1).extend i1 e2
        · simp at hq; subst hq
          exact Denotes.extend i1 e2 ⟨r1, v1⟩
      have hc2 : Denotes m2 c2 (allEval ((prs ++ [(p, f)]).map (·.2))) := by
        refine ⟨r2, fun ρ => ?_⟩
        rw [v2 ρ, evalD_extend hinv.valid e1 _ hc.1, hc.2 ρ, v1 ρ]
        simp [allEval, List.all_append, BOp.app]
      split at h
      · rename_i hz
        cases h
        refine ⟨i2, e1.trans e2, hr2, by rw [← hz]; exact hc2, ⟨1, by simp⟩, Or.inl rfl⟩
      · obtain ⟨i3, e3, r3, d3, ⟨k, hk⟩, hfin⟩ := premLoop_spec fs _ c2 m2 prs' ctx' m' i2 hr2 hc2 h
        refine ⟨i3, e1.trans (e2.trans e3), r3, d3, ⟨k + 1, by rw [hk]; simp⟩, ?_⟩
        rcases hfin with h0 | hall
        · exact Or.inl h0
        · exact Or.inr (by rw [hall]; simp)

/-! ## Minimal-conflict extraction -/

/-- Premises selected by indices (default `(1, TRUE)` is harmless). -/
def pick (prs : List (Nat × BForm n)) (J : List Nat) : List (Nat × BForm n) :=
  J.map (fun j => prs.getD j (1, .tt))

/-- The premise formula at index `j`. -/
def premAt (prs : List (Nat × BForm n)) (j : Nat) : BForm n := (prs.getD j (1, .tt)).2

theorem allEval_pick_iff (prs : List (Nat × BForm n)) (J : List Nat) (ρ : Nat → Bool) :
    allEval ((pick prs J).map (·.2)) ρ = true ↔ ∀ j ∈ J, (premAt prs j).eval ρ = true := by
  simp [allEval, pick, premAt, List.all_eq_true]

theorem RootsOK.pick {m : Mgr} {prs : List (Nat × BForm n)} (h : RootsOK m prs) (J : List Nat) :
    RootsOK m (pick prs J) := by
  intro q hq
  simp only [PCSDD.pick, List.mem_map] at hq
  obtain ⟨j, _, rfl⟩ := hq
  rw [List.getD_eq_getElem?_getD]
  cases hj : prs[j]? with
  | none => simp; exact ⟨by omega, fun ρ => by rw [evalD_one]; rfl⟩
  | some q => simp; exact h q (List.mem_of_getElem? hj)

/-- Deletion-based conflict shrinking over the original index order. -/
def shrink (n : Nat) (lim : Limits) (prs : List (Nat × BForm n)) :
    List Nat → List Nat → Mgr → Except (LimitReached × Mgr) (List Nat × Mgr)
  | core, [], m => .ok (core, m)
  | core, i :: is, m =>
      match conjList n lim (pick prs (core.filter (· != i))) 1 m with
      | .error e => .error e
      | .ok (c, m1) =>
        if c = 0 then shrink n lim prs (core.filter (· != i)) is m1
        else shrink n lim prs core is m1

/-- Satisfiability of an index set of premises. -/
def SatSet (prs : List (Nat × BForm n)) (J : List Nat) (ρ : Nat → Bool) : Prop :=
  ∀ j ∈ J, (premAt prs j).eval ρ = true

theorem SatSet.mono {prs : List (Nat × BForm n)} {J J' : List Nat} {ρ : Nat → Bool}
    (h : SatSet prs J ρ) (hs : ∀ j ∈ J', j ∈ J) : SatSet prs J' ρ := fun j hj => h j (hs j hj)

theorem shrink_spec (prs : List (Nat × BForm n)) :
    ∀ (is core : List Nat) (m : Mgr) core' (m' : Mgr), Inv n lim m → RootsOK m prs →
      shrink n lim prs core is m = .ok (core', m') →
      Inv n lim m' ∧ Extends m.nodes m'.nodes ∧ (∀ j ∈ core', j ∈ core) ∧
        ((∀ ρ, ¬ SatSet prs core ρ) → ∀ ρ, ¬ SatSet prs core' ρ) ∧
        (∀ i ∈ is, i ∈ core' → ∃ ρ, SatSet prs (core'.filter (· != i)) ρ)
  | [], core, m, core', m', hinv, _, h => by
      simp only [shrink] at h; cases h
      exact ⟨hinv, Extends.refl _, fun _ h => h, fun h => h, fun _ h => by simp at h⟩
  | i :: is, core, m, core', m', hinv, hr, h => by
      simp only [shrink] at h
      split at h
      · cases h
      rename_i c m1 h1
      obtain ⟨i1, e1, d1⟩ := conjList_spec _ 1 m _ c m1 hinv (hr.pick _) (denotes_one m) h1
      have hr1 := hr.extend hinv e1
      have hsem : ∀ ρ, evalD m1.nodes ρ c = true ↔ SatSet prs (core.filter (· != i)) ρ := by
        intro ρ; rw [d1.2 ρ]; simp only [Bool.true_and]
        exact allEval_pick_iff prs _ ρ
      split at h
      · rename_i hz
        obtain ⟨i2, e2, sub, uns, mins⟩ := shrink_spec prs is _ m1 core' m' i1 hr1 h
        refine ⟨i2, e1.trans e2, fun j hj => ?_, fun _ => ?_, fun i' hi' hc => ?_⟩
        · have := sub j hj; simp at this; exact this.1
        · apply uns; intro ρ hs
          have := (hsem ρ).2 hs; rw [hz, evalD_zero] at this; cases this
        · rcases List.mem_cons.1 hi' with rfl | hi'
          · have := sub _ hc; simp at this
          · exact mins i' hi' hc
      · rename_i hnz
        obtain ⟨i2, e2, sub, uns, mins⟩ := shrink_spec prs is core m1 core' m' i1 hr1 h
        refine ⟨i2, e1.trans e2, sub, uns, fun i' hi' hc => ?_⟩
        rcases List.mem_cons.1 hi' with rfl | hi'
        · obtain ⟨ρ, hρ⟩ := (exists_sat_unsat i1.valid c d1.1).1 hnz
          refine ⟨ρ, SatSet.mono ((hsem ρ).1 hρ) (fun j hj => ?_)⟩
          simp at hj ⊢; exact ⟨sub j hj.1, hj.2⟩
        · exact mins i' hi' hc

/-- Removal witnesses for each core premise, with witness-step accounting. -/
def coreWits (n : Nat) (lim : Limits) (prs : List (Nat × BForm n)) (core : List Nat) :
    List Nat → Mgr → Except (LimitReached × Mgr) (List (Nat × List Bool) × Mgr)
  | [], m => .ok ([], m)
  | i :: is, m =>
      match conjList n lim (pick prs (core.filter (· != i))) 1 m with
      | .error e => .error e
      | .ok (c, m1) =>
        let m1' := { m1 with wsteps := m1.wsteps + witSteps n m1.nodes 0 c }
        match coreWits n lim prs core is m1' with
        | .error e => .error e
        | .ok (ws, m2) => .ok ((i, (world n m1.nodes c).getD []) :: ws, m2)

theorem coreWits_spec (prs : List (Nat × BForm n)) (core : List Nat)
    (hmin : ∀ i ∈ core, ∃ ρ, SatSet prs (core.filter (· != i)) ρ) :
    ∀ (is : List Nat) (m : Mgr) ws (m' : Mgr), Inv n lim m → RootsOK m prs →
      (∀ i ∈ is, i ∈ core) → coreWits n lim prs core is m = .ok (ws, m') →
      Inv n lim m' ∧ Extends m.nodes m'.nodes ∧ ws.map (·.1) = is ∧
        ∀ p ∈ ws, p.2.length = n ∧ SatSet prs (core.filter (· != p.1)) (envOf p.2)
  | [], m, ws, m', hinv, _, _, h => by
      simp only [coreWits] at h; cases h
      exact ⟨hinv, Extends.refl _, rfl, fun _ h => by simp at h⟩
  | i :: is, m, ws, m', hinv, hr, hin, h => by
      simp only [coreWits] at h
      split at h
      · cases h
      rename_i c m1 h1
      split at h
      · cases h
      rename_i ws2 m2 h2
      cases h
      obtain ⟨i1, e1, d1⟩ := conjList_spec _ 1 m _ c m1 hinv (hr.pick _) (denotes_one m) h1
      have i1' := i1.wsteps (m1.wsteps + witSteps n m1.nodes 0 c)
      obtain ⟨i2, e2, hmap, hws⟩ := coreWits_spec prs core hmin is _ ws2 m' i1'
        (hr.extend hinv e1) (fun j hj => hin j (List.mem_cons_of_mem _ hj)) h2
      refine ⟨i2, e1.trans e2, by simp [hmap], fun p hp => ?_⟩
      rcases List.mem_cons.1 hp with rfl | hp
      · -- the witness of `i`
        obtain ⟨ρ, hρ⟩ := hmin i (hin i (List.mem_cons_self ..))
        have hsem : ∀ ρ, evalD m1.nodes ρ c = true ↔ SatSet prs (core.filter (· != i)) ρ := by
          intro ρ; rw [d1.2 ρ]; simp only [Bool.true_and]; exact allEval_pick_iff prs _ ρ
        have hc0 : c ≠ 0 := by
          intro hz; have := (hsem ρ).2 hρ; rw [hz, evalD_zero] at this; cases this
        have hw := world_spec i1.valid d1.1
        cases hwo : world n m1.nodes c with
        | none => exact absurd ((eq_zero_iff_unsat i1.valid d1.1).2 (hw.1.1 hwo)) hc0
        | some w =>
          obtain ⟨⟨hl, hev⟩, _⟩ := hw.2 w hwo
          simp only [Option.getD_some]
          exact ⟨hl, (hsem _).1 hev⟩
      · exact hws p hp

/-! ## The conditional checker and its receipt -/

/-- A typed conditional task (`pcs-conditional-boolean-task-v1`). -/
structure CTask (n : Nat) where
  source : BForm n
  candidate : BForm n
  assumptions : List (BForm n)
  deriving DecidableEq, Repr

inductive Decision where
  | equivalentUnderAssumptions
  | counterexample
  | inconsistentAssumptions
  | resourceLimit
  deriving DecidableEq, Repr

structure CexRec where
  assignment : List Bool
  sourceTrue : Bool
  candidateTrue : Bool
  assumptionsTrue : List Bool
  deriving DecidableEq, Repr

structure DiagramRec where
  nodes : Nodes
  source : Option Nat
  candidate : Option Nat
  context : Nat
  difference : Option Nat
  deriving DecidableEq, Repr

structure Work where
  bddNodes : Nat
  applyCalls : Nat
  astVisits : Nat
  witnessSteps : Nat
  deriving DecidableEq, Repr

def Mgr.work (m : Mgr) : Work := ⟨m.nodes.size, m.ops, m.visits, m.wsteps⟩

/-- Successful pipeline bodies. -/
inductive Body (n : Nat) where
  | inconsistent (prs : List (Nat × BForm n)) (core : List Nat) (ws : List (Nat × List Bool))
  | decided (ctx s c d : Nat)

/-- The bounded symbolic pipeline. -/
def pipeline (t : CTask n) (lim : Limits) : Except (LimitReached × Mgr) (Body n × Mgr) :=
  match premLoop n lim t.assumptions [] 1 Mgr.empty with
  | .error e => .error e
  | .ok (prs, ctx, m1) =>
    if ctx = 0 then
      match shrink n lim prs (List.range prs.length) (List.range prs.length) m1 with
      | .error e => .error e
      | .ok (core, m2) =>
        match coreWits n lim prs core core m2 with
        | .error e => .error e
        | .ok (ws, m3) => .ok (.inconsistent prs core ws, m3)
    else
      match compile n lim t.source m1 with
      | .error e => .error e
      | .ok (s, m2) =>
        match compile n lim t.candidate m2 with
        | .error e => .error e
        | .ok (c, m3) =>
          match apply n lim (applyFuel lim) .xor s c m3 with
          | .error e => .error e
          | .ok (x, m4) =>
            match apply n lim (applyFuel lim) .and ctx x m4 with
            | .error e => .error e
            | .ok (d, m5) =>
              .ok (.decided ctx s c d,
                { m5 with wsteps := m5.wsteps + witSteps n m5.nodes 0 ctx + witSteps n m5.nodes 0 d })

/-- Conditional receipt content (hash fields are outside the model). -/
structure CReceipt (n : Nat) where
  task : CTask n
  limits : Limits
  decision : Decision
  contextExample : Option (List Bool)
  counterexample : Option CexRec
  unsatCore : Option (List Nat)
  coreWitnesses : Option (List (Nat × List Bool))
  diagram : Option DiagramRec
  limitReached : Option LimitReached
  work : Work
  pcsAuthority : Bool
  leanKernelChecked : Bool
  deriving DecidableEq, Repr

/-- `check(task, limits)`. -/
def check (t : CTask n) (lim : Limits) : CReceipt n :=
  match pipeline t lim with
  | .error (e, m) =>
      { task := t, limits := lim, decision := .resourceLimit, contextExample := none,
        counterexample := none, unsatCore := none, coreWitnesses := none, diagram := none,
        limitReached := some e, work := m.work, pcsAuthority := false, leanKernelChecked := false }
  | .ok (.inconsistent _ core ws, m) =>
      { task := t, limits := lim, decision := .inconsistentAssumptions, contextExample := none,
        counterexample := none, unsatCore := some core, coreWitnesses := some ws,
        diagram := some ⟨m.nodes, none, none, 0, none⟩, limitReached := none, work := m.work,
        pcsAuthority := false, leanKernelChecked := false }
  | .ok (.decided ctx s c d, m) =>
      let cex := (world n m.nodes d).map (fun w =>
        ({ assignment := w, sourceTrue := t.source.eval (envOf w),
           candidateTrue := t.candidate.eval (envOf w),
           assumptionsTrue := t.assumptions.map (fun f => f.eval (envOf w)) } : CexRec))
      { task := t, limits := lim,
        decision := if d = 0 then .equivalentUnderAssumptions else .counterexample,
        contextExample := world n m.nodes ctx, counterexample := cex, unsatCore := none,
        coreWitnesses := none, diagram := some ⟨m.nodes, some s, some c, ctx, some d⟩,
        limitReached := none, work := m.work, pcsAuthority := false, leanKernelChecked := false }

/-- Receipt replay: regenerate and compare the entire content. -/
def verify (r : CReceipt n) : Bool := r == check r.task r.limits

theorem verify_iff (r : CReceipt n) : verify r = true ↔ r = check r.task r.limits := by
  simp [verify]

theorem check_flags (t : CTask n) (lim : Limits) :
    (check t lim).pcsAuthority = false ∧ (check t lim).leanKernelChecked = false := by
  unfold check; split
  · exact ⟨rfl, rfl⟩
  · exact ⟨rfl, rfl⟩
  · exact ⟨rfl, rfl⟩

/-- Premise `j` of a task (default `TRUE` out of range). -/
def CTask.premise (t : CTask n) (j : Nat) : BForm n := t.assumptions.getD j .tt

/-- **Resource exhaustion establishes no semantic outcome.** -/
theorem check_resource_limit (t : CTask n) (lim : Limits)
    (h : (check t lim).decision = .resourceLimit) :
    (check t lim).contextExample = none ∧ (check t lim).counterexample = none ∧
    (check t lim).unsatCore = none ∧ (check t lim).coreWitnesses = none ∧
    (check t lim).diagram = none ∧ (check t lim).limitReached.isSome := by
  unfold check at *
  split at h
  · simp
  · cases h
  · simp only at h; split at h <;> cases h

theorem premAt_eq {prs : List (Nat × BForm n)} {fs : List (BForm n)} {k : Nat}
    (hk : prs.map (·.2) = fs.take k) {j : Nat} (hj : j < prs.length) :
    premAt prs j = fs.getD j .tt := by
  have hl : (prs.map (·.2)).length = (fs.take k).length := by rw [hk]
  simp only [List.length_map, List.length_take] at hl
  have e := congrArg (fun l => l[j]?) hk
  simp only [List.getElem?_map, List.getElem?_take] at e
  simp only [premAt, List.getD_eq_getElem?_getD]
  rw [List.getElem?_eq_getElem hj] at e ⊢
  simp only [Option.map_some, Option.getD_some] at e ⊢
  rw [if_pos (by omega)] at e
  rw [← e]; rfl

/-- Pipeline facts for the premise phase. -/
theorem pipeline_premises {t : CTask n} {prs : List (Nat × BForm n)} {ctx : Nat} {m1 : Mgr}
    (h : premLoop n lim t.assumptions [] 1 Mgr.empty = .ok (prs, ctx, m1)) :
    Inv n lim m1 ∧ RootsOK m1 prs ∧ Denotes m1 ctx (allEval (prs.map (·.2))) ∧
      (∃ k, prs.map (·.2) = t.assumptions.take k) ∧
      (ctx = 0 ∨ prs.map (·.2) = t.assumptions) := by
  obtain ⟨i, _, r, d, ⟨k, hk⟩, hfin⟩ := premLoop_spec t.assumptions [] 1 Mgr.empty prs ctx m1
    (Inv.empty n lim) (fun _ h => by simp at h) ⟨by simp [Mgr.empty], fun ρ => by
      rw [evalD_one]; simp [allEval]⟩ h
  exact ⟨i, r, d, ⟨k, by simpa using hk⟩, by simpa using hfin⟩

/-- **Inconsistent assumptions: inconsistent context, inconsistent inclusion-minimal core with
removal witnesses, and the query is never compiled.** -/
theorem check_inconsistent (t : CTask n) (lim : Limits)
    (h : (check t lim).decision = .inconsistentAssumptions) :
    (∀ ρ, allEval t.assumptions ρ = false) ∧
    ∃ core ws, (check t lim).unsatCore = some core ∧ (check t lim).coreWitnesses = some ws ∧
      (∀ j ∈ core, j < t.assumptions.length) ∧
      (∀ ρ, ¬ ∀ j ∈ core, (t.premise j).eval ρ = true) ∧
      ws.map (·.1) = core ∧
      (∀ p ∈ ws, p.2.length = n ∧ ∀ j ∈ core, j ≠ p.1 → (t.premise j).eval (envOf p.2) = true) ∧
      (∀ i ∈ core, ∃ ρ, ∀ j ∈ core, j ≠ i → (t.premise j).eval ρ = true) ∧
      (∃ d, (check t lim).diagram = some d ∧ d.source = none ∧ d.candidate = none) := by
  unfold check at h ⊢
  split at h
  · cases h
  · rename_i prs core ws m hp
    unfold pipeline at hp
    split at hp
    · cases hp
    rename_i prs1 ctx m1 h1
    obtain ⟨i1, r1, d1, ⟨k, hk⟩, _⟩ := pipeline_premises h1
    split at hp
    · rename_i hz
      split at hp
      · cases hp
      rename_i core2 m2 h2
      split at hp
      · cases hp
      rename_i ws3 m3 h3
      cases hp
      obtain ⟨i2, e2, sub, uns, mins⟩ := shrink_spec prs _ _ m1 core m2 i1 r1 h2
      have hunsat0 : ∀ ρ, ¬ SatSet prs (List.range prs.length) ρ := by
        intro ρ hs
        have := d1.2 ρ; rw [hz, evalD_zero] at this
        have hall : allEval (prs.map (·.2)) ρ = true := by
          simp only [allEval, List.all_eq_true, List.mem_map]
          rintro f ⟨q, hq, rfl⟩
          obtain ⟨j, hj, rfl⟩ := List.getElem_of_mem hq
          have := hs j (by simp [hj])
          simpa [premAt, List.getD_eq_getElem?_getD, hj] using this
        rw [hall] at this; cases this
      have hmin : ∀ i ∈ core, ∃ ρ, SatSet prs (core.filter (· != i)) ρ :=
        fun i hi => mins i (by have := sub i hi; exact this) hi
      obtain ⟨_, _, hmap, hws⟩ := coreWits_spec prs core hmin core m2 ws m i2
        (r1.extend i1 e2) (fun _ h => h) h3
      have hlen : prs.length ≤ t.assumptions.length := by
        have := congrArg List.length hk; simp at this; omega
      have hidx : ∀ j ∈ core, j < prs.length := fun j hj => by have := sub j hj; simpa using this
      have hprem : ∀ j ∈ core, premAt prs j = t.premise j := fun j hj =>
        premAt_eq hk (hidx j hj)
      refine ⟨?_, core, ws, rfl, rfl, fun j hj => by have := hidx j hj; omega, ?_, hmap, ?_, ?_,
        ⟨_, rfl, rfl, rfl⟩⟩
      · intro ρ
        cases hρ : allEval t.assumptions ρ
        · rfl
        · exfalso
          have hpre := allEval_take t.assumptions k ρ hρ
          rw [← hk] at hpre
          have := d1.2 ρ; rw [hz, evalD_zero, hpre] at this; cases this
      · intro ρ hs
        refine uns hunsat0 ρ (fun j hj => ?_)
        rw [hprem j hj]; exact hs j hj
      · intro p hp
        obtain ⟨hl, hsat⟩ := hws p hp
        refine ⟨hl, fun j hj hne => ?_⟩
        rw [← hprem j hj]; exact hsat j (by simp [hj, hne])
      · intro i hi
        obtain ⟨ρ, hρ⟩ := hmin i hi
        exact ⟨ρ, fun j hj hne => by rw [← hprem j hj]; exact hρ j (by simp [hj, hne])⟩
    · split at hp
      · cases hp
      split at hp
      · cases hp
      split at hp
      · cases hp
      split at hp
      · cases hp
      cases hp
  · simp only at h; split at h <;> cases h

/-- Pipeline facts for the decided branch. -/
theorem pipeline_decided {t : CTask n} {ctx s c d : Nat} {m : Mgr}
    (hp : pipeline t lim = .ok (.decided ctx s c d, m)) :
    Inv n lim m ∧ ctx ≠ 0 ∧ Denotes m ctx (allEval t.assumptions) ∧
      Denotes m d (fun ρ => allEval t.assumptions ρ && (t.source.eval ρ != t.candidate.eval ρ)) := by
  unfold pipeline at hp
  split at hp
  · cases hp
  rename_i prs1 ctx1 m1 h1
  obtain ⟨i1, _, d1, _, hfin⟩ := pipeline_premises h1
  split at hp
  · split at hp
    · cases hp
    split at hp
    · cases hp
    cases hp
  rename_i hnz
  have hall : prs1.map (·.2) = t.assumptions := by
    rcases hfin with h0 | h0
    · exact absurd h0 hnz
    · exact h0
  rw [hall] at d1
  split at hp
  · cases hp
  rename_i s2 m2 h2
  split at hp
  · cases hp
  rename_i c3 m3 h3
  split at hp
  · cases hp
  rename_i x4 m4 h4
  split at hp
  · cases hp
  rename_i d5 m5 h5
  cases hp
  obtain ⟨i2, e2, _, r2, v2⟩ := compile_spec _ _ _ _ i1 h2
  obtain ⟨i3, e3, _, r3, v3⟩ := compile_spec _ _ _ _ i2 h3
  obtain ⟨i4, e4, _, _, r4, _, v4⟩ :=
    apply_spec _ _ _ _ _ _ _ i3 (by have := e3.1; omega) r3 h4
  have d1' : Denotes m4 ctx (allEval t.assumptions) :=
    ((d1.extend i1 e2).extend i2 e3).extend i3 e4
  obtain ⟨i5, e5, _, _, r5, _, v5⟩ := apply_spec _ _ _ _ _ _ _ i4 d1'.1 r4 h5
  refine ⟨i5.wsteps _, hnz, d1'.extend i4 e5, r5, fun ρ => ?_⟩
  show evalD m5.nodes ρ d = _
  rw [v5 ρ, d1'.2 ρ, v4 ρ, evalD_extend i2.valid e3 _ r2 ρ, v2 ρ, v3 ρ]
  rfl

/-- **Equivalent under assumptions**: a satisfying context witness exists and every
assignment satisfying all premises gives equal source and candidate values. -/
theorem check_equivalent (t : CTask n) (lim : Limits)
    (h : (check t lim).decision = .equivalentUnderAssumptions) :
    (∃ ce, (check t lim).contextExample = some ce ∧ ce.length = n ∧
        allEval t.assumptions (envOf ce) = true) ∧
    (check t lim).counterexample = none ∧
    ∀ ρ, allEval t.assumptions ρ = true → t.source.eval ρ = t.candidate.eval ρ := by
  unfold check at h ⊢
  split at h
  · cases h
  · cases h
  · rename_i ctx s c d m hp
    simp only at h ⊢
    split at h
    · rename_i hd
      obtain ⟨hinv, hnz, dctx, dd⟩ := pipeline_decided hp
      have hw := world_spec hinv.valid dctx.1
      refine ⟨?_, ?_, ?_⟩
      · cases hwo : world n m.nodes ctx with
        | none => exact absurd ((eq_zero_iff_unsat hinv.valid dctx.1).2 (hw.1.1 hwo)) hnz
        | some w =>
          obtain ⟨⟨hl, hev⟩, _⟩ := hw.2 w hwo
          exact ⟨w, rfl, hl, by rw [← dctx.2]; exact hev⟩
      · simp [world, hd]
      · intro ρ hρ
        have := dd.2 ρ
        rw [hd, evalD_zero] at this
        simp only [hρ, Bool.true_and] at this
        revert this
        cases t.source.eval ρ <;> cases t.candidate.eval ρ <;> simp
    · cases h

/-- **Disagreement**: the returned total assignment satisfies every premise, separates the
meanings and is the lexicographically least such assignment. -/
theorem check_counterexample (t : CTask n) (lim : Limits)
    (h : (check t lim).decision = .counterexample) :
    ∃ rec, (check t lim).counterexample = some rec ∧
      IsLexLeast (fun a => a.length = n ∧ allEval t.assumptions (envOf a) = true ∧
        t.source.eval (envOf a) ≠ t.candidate.eval (envOf a)) rec.assignment ∧
      rec.sourceTrue = t.source.eval (envOf rec.assignment) ∧
      rec.candidateTrue = t.candidate.eval (envOf rec.assignment) ∧
      rec.sourceTrue ≠ rec.candidateTrue ∧
      (∀ b ∈ rec.assumptionsTrue, b = true) := by
  unfold check at h ⊢
  split at h
  · cases h
  · cases h
  · rename_i ctx s c d m hp
    simp only at h ⊢
    split at h
    · cases h
    · rename_i hd
      obtain ⟨hinv, _, _, dd⟩ := pipeline_decided hp
      have hw := world_spec hinv.valid dd.1
      have hiff : ∀ a, SatTotal n m.nodes d a ↔ (a.length = n ∧ allEval t.assumptions (envOf a) = true ∧
          t.source.eval (envOf a) ≠ t.candidate.eval (envOf a)) := by
        intro a; simp only [SatTotal, dd.2]
        cases allEval t.assumptions (envOf a) <;>
          cases t.source.eval (envOf a) <;> cases t.candidate.eval (envOf a) <;> simp
      cases hwo : world n m.nodes d with
      | none => exact absurd ((eq_zero_iff_unsat hinv.valid dd.1).2 (hw.1.1 hwo)) hd
      | some w =>
        have hl := hw.2 w hwo
        have hP := (hiff w).1 hl.1
        refine ⟨_, rfl, ⟨hP, fun b hb => hl.2 b ((hiff b).2 hb)⟩, rfl, rfl, hP.2.2, ?_⟩
        intro b hb
        simp only [List.mem_map] at hb
        obtain ⟨f, hf, rfl⟩ := hb
        have := hP.2.1; simp only [allEval, List.all_eq_true] at this; exact this f hf

end PCSDD
