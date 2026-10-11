import PCSOmega.Repair

/-!
# Omega search outputs pass independent replay

`omega_execution_replay_correct`: for every source and candidate inside the Omega protocol
bounds, every valid budget and **every** (learned, untrusted) frontier ordering, the episode
produced by the adaptive repair search `PCSOmega.search` is accepted by the independently
specified replay verifier `PCSOmega.replay` (parent-state checks, legal edits, depth bounds,
source-bound screening witnesses, fresh receipts and exact work accounting).  Together with
`PCSOmega.replay_sound`, every reported solution is semantically equivalent to the immutable
source, and the replayed accounting equals the reported accounting.

The proof is a simulation: a relation `Sim` between the search state and the replay state is
established initially and preserved by every examined frontier entry, while the replay of the
attempt list recorded so far stays defined.
-/

namespace PCSRuntimeRefinement.OmegaReplay

open PCSOmega

variable {n : Nat}

/-! ## Lookup lemmas -/

theorem lookup_append_old (l : List (BForm n × Nat)) (x : BForm n × Nat) (f : BForm n) (k : Nat)
    (h : lookupState l f = some k) : lookupState (l ++ [x]) f = some k := by
  unfold lookupState at *
  rw [List.find?_append]
  cases hf : l.find? (fun x => x.1 == f) with
  | none => simp [hf] at h
  | some y => simp [hf] at h ⊢; exact h

theorem lookup_append_none (l : List (BForm n × Nat)) (x : BForm n × Nat) (f : BForm n)
    (h : lookupState l f = none) : lookupState (l ++ [x]) f = if x.1 = f then some x.2 else none := by
  unfold lookupState at *
  rw [List.find?_append]
  cases hf : l.find? (fun x => x.1 == f) with
  | none =>
    by_cases hx : x.1 = f
    · simp [hx, List.find?]
    · have hb : (x.1 == f) = false := by simpa using hx
      simp [hx, List.find?, hb]
  | some y => simp [hf] at h

theorem lookup_append_isSome (l : List (BForm n × Nat)) (c : BForm n) (k : Nat) (f : BForm n) :
    (lookupState (l ++ [(c, k)]) f).isSome = true ↔ (lookupState l f).isSome = true ∨ f = c := by
  cases h : lookupState l f with
  | some k' => simp [lookup_append_old l (c, k) f k' h]
  | none =>
    rw [lookup_append_none l (c, k) f h]
    by_cases hc : c = f
    · subst hc; simp
    · simp [hc, Ne.symm hc]

/-! ## Stable sort keeps the elements -/

theorem mem_insertBy {α : Type} (le : α → α → Bool) (x y : α) :
    ∀ l : List α, y ∈ insertBy le x l ↔ y = x ∨ y ∈ l
  | [] => by simp [insertBy]
  | z :: zs => by
    unfold insertBy
    split
    · simp only [List.mem_cons, mem_insertBy le x y zs]; exact or_left_comm
    · simp only [List.mem_cons]

theorem mem_sortBy {α : Type} (le : α → α → Bool) (l : List α) (y : α) :
    y ∈ sortBy le l ↔ y ∈ l := by
  unfold sortBy
  suffices h : ∀ acc : List α, y ∈ l.foldl (fun acc x => insertBy le x acc) acc ↔ y ∈ acc ∨ y ∈ l by
    simpa using h []
  induction l with
  | nil => intro acc; simp
  | cons x xs ih =>
    intro acc
    simp only [List.foldl_cons, ih, mem_insertBy, List.mem_cons]
    rw [or_comm (a := y = x), or_assoc]

/-! ## The simulation relation -/

/-- Frontier entries are legal edits of replay-known parents, at their recorded level. -/
def FrontInv (b : Budget) (states : List (BForm n × Nat)) (fr : List (Entry n)) : Prop :=
  ∀ e ∈ fr, applyAction e.parent e.action = some e.cand ∧
    lookupState states e.parent = some (e.level - 1) ∧ 1 ≤ e.level ∧ e.level ≤ b.depth

structure Sim (b : Budget) (st : SState n) (rst : RState n) : Prop where
  wit : rst.witnesses = st.witnesses
  used : rst.used = st.used
  scr : rst.screened = st.screened
  sol : rst.solution = st.solution
  seen : ∀ f, f ∈ st.seen ↔ (lookupState rst.states f).isSome = true
  front : FrontInv b rst.states st.frontier

theorem frontInv_append (b : Budget) (states : List (BForm n × Nat)) (fr : List (Entry n))
    (x : BForm n × Nat) (h : FrontInv b states fr) : FrontInv b (states ++ [x]) fr := by
  intro e he
  obtain ⟨h1, h2, h3, h4⟩ := h e he
  exact ⟨h1, lookup_append_old _ _ _ _ h2, h3, h4⟩

theorem frontInv_sub (b : Budget) (states : List (BForm n × Nat)) (fr fr' : List (Entry n))
    (h : FrontInv b states fr) (hs : ∀ e ∈ fr', e ∈ fr) : FrontInv b states fr' :=
  fun e he => h e (hs e he)

/-- `expand` preserves the frontier invariant when the expanded formula is replay-known at
the expansion level. -/
theorem expand_front (rk : Ranker n) (b : Budget) (st : SState n) (f : BForm n) (level : Nat)
    (states : List (BForm n × Nat)) (hf : lookupState states f = some level)
    (h : FrontInv b states st.frontier) : FrontInv b states (expand rk b st f level).frontier := by
  unfold expand
  split
  · exact h
  · rename_i hlt
    intro e he
    simp only at he
    rw [mem_sortBy] at he
    rcases List.mem_append.1 he with he | he
    · exact h e he
    · simp only [List.mem_filterMap, Option.map_eq_some_iff] at he
      obtain ⟨a, -, c, hc, rfl⟩ := he
      refine ⟨hc, by simpa using hf, by simp, by simp only; omega⟩

theorem expand_other (rk : Ranker n) (b : Budget) (st : SState n) (f : BForm n) (level : Nat) :
    (expand rk b st f level).witnesses = st.witnesses ∧ (expand rk b st f level).used = st.used ∧
    (expand rk b st f level).screened = st.screened ∧
    (expand rk b st f level).solution = st.solution ∧ (expand rk b st f level).seen = st.seen ∧
    (expand rk b st f level).attempts = st.attempts := by
  unfold expand; split <;> simp

/-! ## Replaying an appended attempt -/

theorem replayRows_append (src : BForm n) (b : Budget) :
    ∀ (rows : List (Attempt n)) (row : Attempt n) (st : RState n),
      replayRows src b st (rows ++ [row]) = (replayRows src b st rows).bind (replayRow src b · row)
  | [], row, st => by
    simp only [List.nil_append, replayRows, Option.bind_some]
    cases replayRow src b st row <;> rfl
  | r :: rs, row, st => by
    simp only [List.cons_append, replayRows]
    cases replayRow src b st r with
    | none => rfl
    | some st' => exact replayRows_append src b rs row st'

/-! ## One examined entry -/

/-- Examining a fresh frontier entry is matched by replaying its recorded attempt. -/
theorem examine_sim (src : BForm n) (rk : Ranker n) (b : Budget) (st : SState n) (rst : RState n)
    (e : Entry n) (rest : List (Entry n)) (hfr : st.frontier = e :: rest) (hS : Sim b st rst)
    (hsol : st.solution = none) (hused : st.used < b.checks) (hnew : e.cand ∉ st.seen) :
    ∃ row rst',
      (examine src rk b { st with frontier := rest, seen := e.cand :: st.seen } e).attempts =
        st.attempts ++ [row] ∧
      replayRow src b rst row = some rst' ∧
      Sim b (examine src rk b { st with frontier := rest, seen := e.cand :: st.seen } e) rst' := by
  obtain ⟨hA, hL, h1, hD⟩ := hS.front e (by rw [hfr]; exact List.mem_cons_self)
  have hnone : lookupState rst.states e.cand = none := by
    cases hl : lookupState rst.states e.cand with
    | none => rfl
    | some k => exact absurd ((hS.seen e.cand).2 (by simp [hl])) hnew
  have hlev : e.level - 1 + 1 = e.level := by omega
  have hguard : (rst.solution.isSome || decide (rst.used ≥ b.checks)) = false := by
    rw [hS.sol, hS.used, hsol]; simp; omega
  have hrest : FrontInv b rst.states rest :=
    frontInv_sub b _ _ _ hS.front (fun x hx => by rw [hfr]; exact List.mem_cons_of_mem _ hx)
  have hlook' : lookupState (rst.states ++ [(e.cand, e.level)]) e.cand = some e.level := by
    rw [lookup_append_none _ _ _ hnone]; simp
  have hseen' : ∀ f, f ∈ e.cand :: st.seen ↔
      (lookupState (rst.states ++ [(e.cand, e.level)]) f).isSome = true := by
    intro f
    rw [lookup_append_isSome, ← hS.seen f, List.mem_cons]
    exact or_comm
  have hrow : ∀ (rb : Option (List Bool)) (rc : Option CheckReceipt),
      rb = (screenWork src e.cand st.witnesses).1 →
      replayRow src b rst ⟨e.parent, e.action, e.cand, e.level, rb, rc⟩ =
        replayCore src rst e.cand (e.level - 1) ⟨e.parent, e.action, e.cand, e.level, rb, rc⟩ := by
    intro rb rc hrb
    unfold replayRow
    rw [hguard]
    simp only [Bool.false_eq_true, if_false, hL, hA, hnone, Option.isNone_none, hlev, h1, hD,
      hS.wit, hrb, and_self, if_true]
  unfold examine
  simp only
  cases hsw : (screenWork src e.cand st.witnesses).1 with
  | some w =>
    simp only
    obtain ⟨x1, x2, x3, x4, x5, x6⟩ := expand_other rk b
      (recordAttempt { st with frontier := rest, seen := e.cand :: st.seen }
        ⟨e.parent, e.action, e.cand, e.level, some w, none⟩ (screenWork src e.cand st.witnesses).2 false)
      e.cand e.level
    refine ⟨⟨e.parent, e.action, e.cand, e.level, some w, none⟩, { rst with
        states := rst.states ++ [(e.cand, e.level - 1 + 1)]
        screened := rst.screened + (screenWork src e.cand rst.witnesses).2 }, ?_, ?_, ?_⟩
    · rw [x6]; simp [recordAttempt]
    · rw [hrow _ _ hsw.symm]
      simp [replayCore, hS.wit, hsw]
    · rw [hlev]
      refine ⟨by rw [x1]; simp [recordAttempt, hS.wit], by rw [x2]; simp [recordAttempt, hS.used],
        by rw [x3]; simp [recordAttempt, hS.scr, hS.wit], by rw [x4]; simp [recordAttempt, hS.sol],
        by rw [x5]; simpa [recordAttempt] using hseen', ?_⟩
      apply expand_front rk b _ e.cand e.level _ hlook'
      simpa [recordAttempt] using frontInv_append b _ _ _ hrest
  | none =>
    simp only
    have hrow' := hrow none (some (checkReceipt src e.cand)) hsw.symm
    have hsw' : (screenWork src e.cand rst.witnesses).1 = none := by rw [hS.wit]; exact hsw
    by_cases heq : (checkReceipt src e.cand).equivalent = true
    · simp only [heq, if_true]
      refine ⟨⟨e.parent, e.action, e.cand, e.level, none, some (checkReceipt src e.cand)⟩,
        { rst with
          states := rst.states ++ [(e.cand, e.level - 1 + 1)]
          screened := rst.screened + (screenWork src e.cand rst.witnesses).2
          used := rst.used + 1
          solution := some e.cand }, by simp [recordAttempt], ?_, ?_⟩
      · rw [hrow']
        simp [replayCore, hsw', finishChecked, heq]
      · rw [hlev]
        refine ⟨by simp [recordAttempt, hS.wit], by simp [recordAttempt, hS.used],
          by simp [recordAttempt, hS.scr, hS.wit], by simp,
          by simpa [recordAttempt] using hseen', ?_⟩
        simpa [recordAttempt] using frontInv_append b _ _ _ hrest
    · have hne : (checkReceipt src e.cand).equivalent = false := by simpa using heq
      simp only [hne, Bool.false_eq_true, if_false]
      obtain ⟨x1, x2, x3, x4, x5, x6⟩ := expand_other rk b
        (remember (recordAttempt { st with frontier := rest, seen := e.cand :: st.seen }
          ⟨e.parent, e.action, e.cand, e.level, none, some (checkReceipt src e.cand)⟩
          (screenWork src e.cand st.witnesses).2 true) (checkReceipt src e.cand).witness)
        e.cand e.level
      refine ⟨⟨e.parent, e.action, e.cand, e.level, none, some (checkReceipt src e.cand)⟩,
        rememberR { rst with
          states := rst.states ++ [(e.cand, e.level - 1 + 1)]
          screened := rst.screened + (screenWork src e.cand rst.witnesses).2
          used := rst.used + 1 } (checkReceipt src e.cand).witness, ?_, ?_, ?_⟩
      · rw [x6]; unfold remember; split
        · split <;> simp [recordAttempt]
        · simp [recordAttempt]
      · rw [hrow']
        simp [replayCore, hsw', finishChecked, hne]
      · rw [hlev]
        have hrem : ∀ (o : Option (List Bool)),
            (remember (recordAttempt { st with frontier := rest, seen := e.cand :: st.seen }
              ⟨e.parent, e.action, e.cand, e.level, none, some (checkReceipt src e.cand)⟩
              (screenWork src e.cand st.witnesses).2 true) o).witnesses =
            (rememberR { rst with
              states := rst.states ++ [(e.cand, e.level)]
              screened := rst.screened + (screenWork src e.cand rst.witnesses).2
              used := rst.used + 1 } o).witnesses ∧
            (remember (recordAttempt { st with frontier := rest, seen := e.cand :: st.seen }
              ⟨e.parent, e.action, e.cand, e.level, none, some (checkReceipt src e.cand)⟩
              (screenWork src e.cand st.witnesses).2 true) o).used = st.used + 1 ∧
            (remember (recordAttempt { st with frontier := rest, seen := e.cand :: st.seen }
              ⟨e.parent, e.action, e.cand, e.level, none, some (checkReceipt src e.cand)⟩
              (screenWork src e.cand st.witnesses).2 true) o).screened =
                st.screened + (screenWork src e.cand st.witnesses).2 ∧
            (remember (recordAttempt { st with frontier := rest, seen := e.cand :: st.seen }
              ⟨e.parent, e.action, e.cand, e.level, none, some (checkReceipt src e.cand)⟩
              (screenWork src e.cand st.witnesses).2 true) o).solution = st.solution ∧
            (remember (recordAttempt { st with frontier := rest, seen := e.cand :: st.seen }
              ⟨e.parent, e.action, e.cand, e.level, none, some (checkReceipt src e.cand)⟩
              (screenWork src e.cand st.witnesses).2 true) o).seen = e.cand :: st.seen ∧
            (remember (recordAttempt { st with frontier := rest, seen := e.cand :: st.seen }
              ⟨e.parent, e.action, e.cand, e.level, none, some (checkReceipt src e.cand)⟩
              (screenWork src e.cand st.witnesses).2 true) o).frontier = rest ∧
            (rememberR { rst with
              states := rst.states ++ [(e.cand, e.level)]
              screened := rst.screened + (screenWork src e.cand rst.witnesses).2
              used := rst.used + 1 } o).states = rst.states ++ [(e.cand, e.level)] ∧
            (rememberR { rst with
              states := rst.states ++ [(e.cand, e.level)]
              screened := rst.screened + (screenWork src e.cand rst.witnesses).2
              used := rst.used + 1 } o).used = rst.used + 1 ∧
            (rememberR { rst with
              states := rst.states ++ [(e.cand, e.level)]
              screened := rst.screened + (screenWork src e.cand rst.witnesses).2
              used := rst.used + 1 } o).screened = rst.screened + (screenWork src e.cand rst.witnesses).2 ∧
            (rememberR { rst with
              states := rst.states ++ [(e.cand, e.level)]
              screened := rst.screened + (screenWork src e.cand rst.witnesses).2
              used := rst.used + 1 } o).solution = rst.solution := by
          intro o
          cases o with
          | none => simp [remember, rememberR, recordAttempt, hS.wit]
          | some w =>
            by_cases hw : w ∈ st.witnesses
            · simp [remember, rememberR, recordAttempt, hw, hS.wit]
            · simp [remember, rememberR, recordAttempt, hw, hS.wit]
        obtain ⟨r1, r2, r3, r4, r5, r6, r7, r8, r9, r10⟩ := hrem (checkReceipt src e.cand).witness
        refine ⟨by rw [x1, r1], by rw [x2, r2, r8, hS.used], by rw [x3, r3, r9, hS.scr, hS.wit],
          by rw [x4, r4, r10, hS.sol], ?_, ?_⟩
        · intro f; rw [x5, r5, r7]; exact hseen' f
        · rw [r7]
          apply expand_front rk b _ e.cand e.level _ hlook'
          rw [r6]
          exact frontInv_append b _ _ _ hrest

/-! ## The whole loop -/

theorem loop_sim (src : BForm n) (rk : Ranker n) (b : Budget) (rst0 : RState n) :
    ∀ (fuel : Nat) (st : SState n) (rst : RState n), Sim b st rst →
      replayRows src b rst0 st.attempts = some rst →
      ∃ rst', replayRows src b rst0 (loop src rk b fuel st).attempts = some rst' ∧
        Sim b (loop src rk b fuel st) rst'
  | 0, st, rst, hS, hR => ⟨rst, hR, hS⟩
  | fuel + 1, st, rst, hS, hR => by
    unfold loop
    split
    · exact ⟨rst, hR, hS⟩
    · rename_i hg
      simp only [Bool.or_eq_true, decide_eq_true_eq, not_or, Nat.not_le] at hg
      obtain ⟨⟨hsol, hused⟩, -⟩ := hg
      have hsol' : st.solution = none := by simpa using hsol
      split
      · exact ⟨rst, hR, hS⟩
      · rename_i e rest hfr
        split
        · exact loop_sim src rk b rst0 fuel { st with frontier := rest } rst
            ⟨hS.wit, hS.used, hS.scr, hS.sol, hS.seen, frontInv_sub b _ _ _ hS.front
              (fun x hx => by rw [hfr]; exact List.mem_cons_of_mem _ hx)⟩ hR
        · rename_i hnew
          obtain ⟨row, rst', hatt, hrow, hS'⟩ := examine_sim src rk b st rst e rest hfr hS hsol' hused hnew
          apply loop_sim src rk b rst0 fuel _ rst' hS'
          rw [hatt, replayRows_append, hR]
          exact hrow

/-- The replay start state built by `replay` from the recorded initial receipt. -/
def replayStart (src cand : BForm n) : RState n :=
  let r := checkReceipt src cand
  { states := [(cand, 0)], witnesses := if r.equivalent then [] else r.witness.toList, used := 1,
    screened := 0, solution := if r.equivalent then some cand else none }

theorem initState_sim (src cand : BForm n) (rk : Ranker n) (b : Budget) :
    Sim b (initState src cand rk b) (replayStart src cand) := by
  have hl : lookupState [(cand, 0)] cand = some 0 := by simp [lookupState]
  have hseen : ∀ f, f ∈ [cand] ↔ (lookupState [(cand, 0)] f).isSome = true := by
    intro f
    by_cases hf : cand = f
    · subst hf; simp [hl]
    · have hb : (cand == f) = false := by simpa using hf
      simp [lookupState, List.find?, hb, Ne.symm hf]
  unfold initState replayStart
  simp only
  by_cases heq : (checkReceipt src cand).equivalent = true
  · simp only [heq, if_true]
    exact ⟨rfl, rfl, rfl, rfl, hseen, by intro e he; cases he⟩
  · have hne : (checkReceipt src cand).equivalent = false := by simpa using heq
    simp only [hne, Bool.false_eq_true, if_false]
    obtain ⟨x1, x2, x3, x4, x5, -⟩ := expand_other rk b
      { frontier := [], seen := [cand], witnesses := (checkReceipt src cand).witness.toList,
        attempts := [], used := 1, screened := 0, ranked := 0, solution := none } cand 0
    refine ⟨by rw [x1], by rw [x2], by rw [x3], by rw [x4], by rw [x5]; exact hseen, ?_⟩
    apply expand_front rk b _ cand 0 _ hl
    intro e he; cases he

/-- **`omega_execution_replay_correct`.**  For every source and candidate inside the protocol
bounds, every valid budget and every frontier ordering `rk` (the only thing a learned model
controls), the episode produced by the adaptive repair search passes the independent replay
verifier; consequently (by `replay_sound`) any reported solution is semantically equivalent to
the immutable source. -/
theorem omega_execution_replay_correct (src cand : BForm n) (rk : Ranker n) (b : Budget)
    (hb : b.valid = true) (hsrc : bounded src = true) (hcand : bounded cand = true) :
    replay (search src cand rk b) = true ∧
      ∀ s, (search src cand rk b).solution = some s → SemEquiv src s := by
  have hrep : replay (search src cand rk b) = true := by
    obtain ⟨rst, hR, hS⟩ := loop_sim src rk b (replayStart src cand) (searchFuel b)
      (initState src cand rk b) (replayStart src cand) (initState_sim src cand rk b)
      (by simp [initState]; split <;> simp [expand_other, replayRows])
    have hacc := (search_accounting src cand rk b hb).2.2.1
    simp only [searchWork, runSearch] at hacc
    unfold replay
    simp only [search, runSearch, Bool.and_eq_true, beq_iff_eq, hb, hsrc, hcand, decide_eq_true_eq,
      true_and, and_true]
    refine ⟨hacc, ?_⟩
    have hR' : replayRows src b
        { states := [(cand, 0)],
          witnesses := if (checkReceipt src cand).equivalent then [] else (checkReceipt src cand).witness.toList,
          used := 1, screened := 0,
          solution := if (checkReceipt src cand).equivalent then some cand else none }
        (loop src rk b (searchFuel b) (initState src cand rk b)).attempts = some rst := hR
    rw [hR']
    simp only [Bool.and_eq_true, beq_iff_eq, hS.used, hS.scr, hS.sol, and_self]
  exact ⟨hrep, fun s hs => replay_sound _ hrep hs⟩

end PCSRuntimeRefinement.OmegaReplay
