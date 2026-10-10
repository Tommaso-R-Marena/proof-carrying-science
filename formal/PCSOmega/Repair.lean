import PCSOmega.Check

/-!
# Bounded repair edits, counterexample-guided search and replay (typed reference)

Typed reference model of `pcs/experimental/omega/{logic,adaptive}.py` (repair language,
`actions`, `apply_action`, adaptive `search` and `replay`).  The Omega protocol bounds are
kept: AST size ≤ 63, depth ≤ 8, ≤ 128 actions, checker budget 1–128, depth 1–4,
proposal budget 1–1024.  Declared variable count 1–4 is enforced by the decoder layer
(`omegaVarsOk`), not silently extended.

* `applyAction` — legal bounded edits (`insert_not`, `remove_not`, `swap`, `replace_*`).
* `search rk …` — best-first repair, **parameterised by an arbitrary frontier ordering**
  `rk` (learned weights only change this ordering).  Remembered counterexamples screen
  candidates; only a fresh exhaustive `checkReceipt` can accept.
* `search_solution_sound` — for *every* ordering, an accepted solution is semantically
  equivalent to the immutable source.
* `search_accounting` — `1 ≤ checksUsed ≤ checks`, attempts ≤ proposals,
  witnesses ≤ checks used, witness evaluations ≤ attempts · checks, ranked proposals
  ≤ 128 · (attempts + 1).
* `replay` — independent verifier of a recorded episode (checked parent states, legal
  edits, source-bound witnesses, fresh receipts, exact work accounting);
  `replay_sound` — an accepted replayed solution is equivalent to the source.

Not claimed: bounded-search completeness, fairness, global repair optimality, learned
accuracy, training improvement, or scientific grounding.  Digest-based `seen` sets are
modelled by structural equality of typed ASTs.
-/

namespace PCSOmega

variable {n : Nat}

inductive Dir where
  | body
  | left
  | right
  deriving DecidableEq, Repr

inductive EditOp where
  | insertNot
  | removeNot
  | swap
  | replaceAnd
  | replaceOr
  | replaceImp
  deriving DecidableEq, Repr

structure Action where
  path : List Dir
  op : EditOp
  deriving DecidableEq, Repr

def MAX_NODES : Nat := 63
def MAX_DEPTH : Nat := 8
def MAX_ACTIONS : Nat := 128

/-- The Omega AST bound (`validate_formula`). -/
def bounded (f : BForm n) : Bool := decide (f.size ≤ MAX_NODES) && decide (f.depth ≤ MAX_DEPTH)

/-- Edit at the addressed node. -/
def editNode : BForm n → EditOp → Option (BForm n)
  | f, .insertNot => some (.not f)
  | .not a, .removeNot => some a
  | .and a b, .swap => some (.and b a)
  | .or a b, .swap => some (.or b a)
  | .imp a b, .swap => some (.imp b a)
  | .and a b, .replaceAnd => some (.and a b)
  | .or a b, .replaceAnd => some (.and a b)
  | .imp a b, .replaceAnd => some (.and a b)
  | .and a b, .replaceOr => some (.or a b)
  | .or a b, .replaceOr => some (.or a b)
  | .imp a b, .replaceOr => some (.or a b)
  | .and a b, .replaceImp => some (.imp a b)
  | .or a b, .replaceImp => some (.imp a b)
  | .imp a b, .replaceImp => some (.imp a b)
  | _, _ => none

/-- Edit at a path (`body` / `left` / `right`). -/
def editAt : BForm n → List Dir → EditOp → Option (BForm n)
  | f, [], op => editNode f op
  | .not a, .body :: p, op => (editAt a p op).map .not
  | .and a b, .left :: p, op => (editAt a p op).map (fun x => .and x b)
  | .and a b, .right :: p, op => (editAt b p op).map (fun x => .and a x)
  | .or a b, .left :: p, op => (editAt a p op).map (fun x => .or x b)
  | .or a b, .right :: p, op => (editAt b p op).map (fun x => .or a x)
  | .imp a b, .left :: p, op => (editAt a p op).map (fun x => .imp x b)
  | .imp a b, .right :: p, op => (editAt b p op).map (fun x => .imp a x)
  | _, _ :: _, _ => none

/-- `apply_action`: bounded input, bounded path, bounded output. -/
def applyAction (f : BForm n) (act : Action) : Option (BForm n) :=
  if bounded f && decide (act.path.length ≤ MAX_DEPTH) then
    match editAt f act.path act.op with
    | some g => if bounded g then some g else none
    | none => none
  else none

theorem applyAction_bounded {f g : BForm n} {act : Action} (h : applyAction f act = some g) :
    bounded g = true := by
  unfold applyAction at h
  split at h
  · split at h
    · split at h
      · cases h; assumption
      · cases h
    · cases h
  · cases h

/-- Preorder walk with paths (`walk`). -/
def walk : BForm n → List (List Dir × BForm n)
  | .not a => ([], .not a) :: (walk a).map (fun x => (Dir.body :: x.1, x.2))
  | .and a b => ([], .and a b) :: ((walk a).map (fun x => (Dir.left :: x.1, x.2)) ++
      (walk b).map (fun x => (Dir.right :: x.1, x.2)))
  | .or a b => ([], .or a b) :: ((walk a).map (fun x => (Dir.left :: x.1, x.2)) ++
      (walk b).map (fun x => (Dir.right :: x.1, x.2)))
  | .imp a b => ([], .imp a b) :: ((walk a).map (fun x => (Dir.left :: x.1, x.2)) ++
      (walk b).map (fun x => (Dir.right :: x.1, x.2)))
  | f => [([], f)]

/-- Candidate operations at a node. -/
def opsFor : BForm n → List EditOp
  | .not _ => [.insertNot, .removeNot]
  | .and _ _ => [.insertNot, .swap, .replaceAnd, .replaceOr, .replaceImp]
  | .or _ _ => [.insertNot, .swap, .replaceAnd, .replaceOr, .replaceImp]
  | .imp _ _ => [.insertNot, .swap, .replaceAnd, .replaceOr, .replaceImp]
  | _ => [.insertNot]

/-- Deduplicating action collection, stopping at `MAX_ACTIONS`. -/
def actionsAux (f : BForm n) : List Action → List (BForm n) → List Action → List Action
  | [], _, acc => acc.reverse
  | a :: rest, seen, acc =>
      if acc.length ≥ MAX_ACTIONS then acc.reverse else
      match applyAction f a with
      | none => actionsAux f rest seen acc
      | some c => if c ∈ seen then actionsAux f rest seen acc
                  else actionsAux f rest (c :: seen) (a :: acc)

/-- `actions(formula)`. -/
def actionsOf (f : BForm n) : List Action :=
  if bounded f then
    actionsAux f ((walk f).flatMap (fun x => (opsFor x.2).map (fun op => ⟨x.1, op⟩))) [f] []
  else []

theorem actionsAux_length (f : BForm n) :
    ∀ (l : List Action) (seen : List (BForm n)) (acc : List Action),
      acc.length ≤ MAX_ACTIONS → (actionsAux f l seen acc).length ≤ MAX_ACTIONS
  | [], _, acc, h => by simpa [actionsAux] using h
  | a :: rest, seen, acc, h => by
      unfold actionsAux
      split
      · simpa using h
      · rename_i hlt
        split
        · exact actionsAux_length f rest seen acc h
        · split
          · exact actionsAux_length f rest seen acc h
          · exact actionsAux_length f rest _ _ (by simp; omega)

theorem actionsOf_length (f : BForm n) : (actionsOf f).length ≤ MAX_ACTIONS := by
  unfold actionsOf
  split
  · exact actionsAux_length f _ _ _ (by simp [MAX_ACTIONS])
  · simp [MAX_ACTIONS]

/-! ## Budgets, frontier entries, attempts and episodes -/

structure Budget where
  checks : Nat
  depth : Nat
  proposals : Nat
  deriving DecidableEq, Repr

/-- The protocol budget ranges. -/
def Budget.valid (b : Budget) : Bool :=
  decide (1 ≤ b.checks ∧ b.checks ≤ 128 ∧ 1 ≤ b.depth ∧ b.depth ≤ 4 ∧
    1 ≤ b.proposals ∧ b.proposals ≤ 1024)

/-- A frontier entry: (level, parent, action, candidate). -/
structure Entry (n : Nat) where
  level : Nat
  parent : BForm n
  action : Action
  cand : BForm n
  deriving DecidableEq, Repr

/-- An arbitrary frontier ordering (`≤` used by the stable merge sort).  A learned model
only chooses this ordering. -/
abbrev Ranker (n : Nat) := Entry n → Entry n → Bool

structure Attempt (n : Nat) where
  parent : BForm n
  action : Action
  cand : BForm n
  depth : Nat
  rejectedBy : Option (List Bool)
  receipt : Option CheckReceipt
  deriving DecidableEq, Repr

inductive Status where
  | booleanVerified
  | budgetOrSearchExhausted
  deriving DecidableEq, Repr

structure Episode (n : Nat) where
  source : BForm n
  candidate : BForm n
  budget : Budget
  initial : CheckReceipt
  attempts : List (Attempt n)
  checksUsed : Nat
  witnessEvaluations : Nat
  solution : Option (BForm n)
  status : Status
  pcsAuthority : Bool
  leanKernelChecked : Bool
  deriving DecidableEq, Repr

/-- Screening with work: the first rejecting witness and the number of evaluations. -/
def screenWork (src cand : BForm n) : List (List Bool) → Option (List Bool) × Nat
  | [] => (none, 0)
  | w :: ws => if disagree src cand w then (some w, 1)
               else let r := screenWork src cand ws; (r.1, r.2 + 1)

theorem screenWork_fst (src cand : BForm n) :
    ∀ W, (screenWork src cand W).1 = screen src cand W
  | [] => rfl
  | w :: ws => by
      unfold screenWork screen
      by_cases h : disagree src cand w = true
      · simp [h]
      · simp [h]; exact screenWork_fst src cand ws

theorem screenWork_snd_le (src cand : BForm n) :
    ∀ W, (screenWork src cand W).2 ≤ W.length
  | [] => by simp [screenWork]
  | w :: ws => by
      unfold screenWork
      split
      · simp
      · have := screenWork_snd_le src cand ws; simp; omega

/-- The counterexample assignment of a receipt. -/
def CheckReceipt.witness (r : CheckReceipt) : Option (List Bool) := r.counterexample.map (·.1)

/-! ## Adaptive search state and loop -/

structure SState (n : Nat) where
  frontier : List (Entry n)
  seen : List (BForm n)
  witnesses : List (List Bool)
  attempts : List (Attempt n)
  used : Nat
  screened : Nat
  ranked : Nat
  solution : Option (BForm n)

/-- Stable insertion of `x` after every element not ranked strictly after it. -/
def insertBy (le : α → α → Bool) (x : α) : List α → List α
  | [] => [x]
  | y :: ys => if le y x then y :: insertBy le x ys else x :: y :: ys

/-- Stable sort by an arbitrary comparator (structural, so kernel-reducible); for a total
preorder it agrees with any stable sort such as Python's `list.sort`. -/
def sortBy (le : α → α → Bool) (l : List α) : List α := l.foldl (fun acc x => insertBy le x acc) []

/-- Expand a formula: generate, count and rank all outgoing proposals. -/
def expand (rk : Ranker n) (b : Budget) (st : SState n) (f : BForm n) (level : Nat) :
    SState n :=
  if level ≥ b.depth then st else
  let new := (actionsOf f).filterMap (fun a => (applyAction f a).map (fun c =>
    ({ level := level + 1, parent := f, action := a, cand := c } : Entry n)))
  { st with frontier := sortBy rk (st.frontier ++ new), ranked := st.ranked + new.length }

/-- Record an examined attempt and its screening work. -/
def recordAttempt (st : SState n) (a : Attempt n) (work : Nat) (checked : Bool) : SState n :=
  { st with
    screened := st.screened + work
    used := if checked then st.used + 1 else st.used
    attempts := st.attempts ++ [a] }

/-- Remember a fresh counterexample (if new). -/
def remember (st : SState n) : Option (List Bool) → SState n
  | some w => if w ∈ st.witnesses then st else { st with witnesses := st.witnesses ++ [w] }
  | none => st

/-- One examined candidate (already known not to be in `seen`). -/
def examine (src : BForm n) (rk : Ranker n) (b : Budget) (st : SState n) (e : Entry n) :
    SState n :=
  let sw := screenWork src e.cand st.witnesses
  match sw.1 with
  | some w =>
      expand rk b (recordAttempt st ⟨e.parent, e.action, e.cand, e.level, some w, none⟩ sw.2 false)
        e.cand e.level
  | none =>
      let r := checkReceipt src e.cand
      let st1 := recordAttempt st ⟨e.parent, e.action, e.cand, e.level, none, some r⟩ sw.2 true
      if r.equivalent then { st1 with solution := some e.cand }
      else expand rk b (remember st1 r.witness) e.cand e.level

/-- The bounded search loop (structural fuel; fuel exhaustion is an unresolved result). -/
def loop (src : BForm n) (rk : Ranker n) (b : Budget) : Nat → SState n → SState n
  | 0, st => st
  | fuel + 1, st =>
      if st.solution.isSome || decide (st.used ≥ b.checks) ||
          decide (st.attempts.length ≥ b.proposals) then st else
      match st.frontier with
      | [] => st
      | e :: rest =>
          if e.cand ∈ st.seen then loop src rk b fuel { st with frontier := rest }
          else loop src rk b fuel (examine src rk b { st with frontier := rest, seen := e.cand :: st.seen } e)

/-- Initial state: one fresh exhaustive check of the original candidate. -/
def initState (src cand : BForm n) (rk : Ranker n) (b : Budget) : SState n :=
  let r := checkReceipt src cand
  if r.equivalent then
    { frontier := [], seen := [cand], witnesses := [], attempts := [], used := 1, screened := 0,
      ranked := 0, solution := some cand }
  else
    expand rk b
      { frontier := [], seen := [cand], witnesses := r.witness.toList, attempts := [],
        used := 1, screened := 0, ranked := 0, solution := none } cand 0

/-- Default loop fuel: every iteration either records an attempt or discards one of at most
`128 · (proposals + 1)` generated frontier entries. -/
def searchFuel (b : Budget) : Nat := (MAX_ACTIONS + 1) * (b.proposals + 1) + 1

/-- Additional work counters of the reference search (not all are recorded by Python). -/
structure SearchWork where
  checksUsed : Nat
  witnessEvaluations : Nat
  rankedProposals : Nat
  attempts : Nat
  deriving DecidableEq, Repr

def runSearch (src cand : BForm n) (rk : Ranker n) (b : Budget) : SState n :=
  loop src rk b (searchFuel b) (initState src cand rk b)

/-- The adaptive search episode for an arbitrary ranking. -/
def search (src cand : BForm n) (rk : Ranker n) (b : Budget) : Episode n :=
  let st := runSearch src cand rk b
  { source := src, candidate := cand, budget := b, initial := checkReceipt src cand,
    attempts := st.attempts, checksUsed := st.used, witnessEvaluations := st.screened,
    solution := st.solution,
    status := if st.solution.isSome then .booleanVerified else .budgetOrSearchExhausted,
    pcsAuthority := false, leanKernelChecked := false }

def searchWork (src cand : BForm n) (rk : Ranker n) (b : Budget) : SearchWork :=
  let st := runSearch src cand rk b
  ⟨st.used, st.screened, st.ranked, st.attempts.length⟩

/-! ## Soundness of acceptance (for every ranking) -/

/-- Invariant: a stored solution is equivalent to the source. -/
def SolInv (src : BForm n) (st : SState n) : Prop :=
  ∀ s, st.solution = some s → SemEquiv src s

theorem expand_solution (rk : Ranker n) (b : Budget) (st : SState n) (f : BForm n) (l : Nat) :
    (expand rk b st f l).solution = st.solution := by
  unfold expand; split <;> rfl

theorem remember_solution (st : SState n) (o : Option (List Bool)) :
    (remember st o).solution = st.solution := by
  unfold remember; split
  · split <;> rfl
  · rfl

theorem examine_solInv (src : BForm n) (rk : Ranker n) (b : Budget) (st : SState n) (e : Entry n)
    (h : SolInv src st) : SolInv src (examine src rk b st e) := by
  intro s hs
  unfold examine at hs
  dsimp only at hs
  split at hs
  · rw [expand_solution] at hs; exact h s hs
  · split at hs
    · rename_i heq
      simp at hs; subst hs
      exact (checkReceipt_equivalent_iff src e.cand).1 heq
    · rw [expand_solution, remember_solution] at hs
      exact h s (by simpa [recordAttempt] using hs)

theorem loop_solInv (src : BForm n) (rk : Ranker n) (b : Budget) :
    ∀ fuel (st : SState n), SolInv src st → SolInv src (loop src rk b fuel st)
  | 0, st, h => h
  | fuel + 1, st, h => by
      unfold loop
      split
      · exact h
      · split
        · exact h
        · split
          · exact loop_solInv src rk b fuel _ h
          · exact loop_solInv src rk b fuel _ (examine_solInv src rk b _ _ h)

theorem initState_solInv (src cand : BForm n) (rk : Ranker n) (b : Budget) :
    SolInv src (initState src cand rk b) := by
  intro s hs
  unfold initState at hs
  dsimp only at hs
  split at hs
  · rename_i heq; simp at hs; subst hs
    exact (checkReceipt_equivalent_iff src cand).1 heq
  · rw [expand_solution] at hs; cases hs

/-- **Accepted repair solutions preserve source semantics, for every ranking.** -/
theorem search_solution_sound (src cand : BForm n) (rk : Ranker n) (b : Budget) {s : BForm n}
    (h : (search src cand rk b).solution = some s) : SemEquiv src s :=
  loop_solInv src rk b _ _ (initState_solInv src cand rk b) s h

theorem search_status_iff (src cand : BForm n) (rk : Ranker n) (b : Budget) :
    (search src cand rk b).status = .booleanVerified ↔ (search src cand rk b).solution.isSome := by
  simp only [search]; split <;> simp_all

theorem search_flags (src cand : BForm n) (rk : Ranker n) (b : Budget) :
    (search src cand rk b).pcsAuthority = false ∧ (search src cand rk b).leanKernelChecked = false :=
  ⟨rfl, rfl⟩

/-! ## Work accounting -/

/-- Accounting invariant. -/
structure AccInv (b : Budget) (st : SState n) : Prop where
  used_pos : 1 ≤ st.used
  used_le : st.used ≤ b.checks
  att_le : st.attempts.length ≤ b.proposals
  wit_le : st.witnesses.length ≤ st.used
  screened_le : st.screened ≤ st.attempts.length * b.checks
  ranked_le : st.ranked ≤ MAX_ACTIONS * (st.attempts.length + 1)

theorem expand_fields (rk : Ranker n) (b : Budget) (st : SState n) (f : BForm n) (l : Nat) :
    (expand rk b st f l).used = st.used ∧ (expand rk b st f l).attempts = st.attempts ∧
    (expand rk b st f l).witnesses = st.witnesses ∧ (expand rk b st f l).screened = st.screened ∧
    st.ranked ≤ (expand rk b st f l).ranked ∧
    (expand rk b st f l).ranked ≤ st.ranked + MAX_ACTIONS := by
  unfold expand
  split
  · simp
  · simp only [Nat.le_add_right, Nat.add_le_add_iff_left, true_and]
    exact Nat.le_trans (List.length_filterMap_le _ _) (actionsOf_length f)

theorem recordAttempt_fields (st : SState n) (a : Attempt n) (w : Nat) (c : Bool) :
    (recordAttempt st a w c).attempts.length = st.attempts.length + 1 ∧
    (recordAttempt st a w c).screened = st.screened + w ∧
    (recordAttempt st a w c).used = (if c then st.used + 1 else st.used) ∧
    (recordAttempt st a w c).witnesses = st.witnesses ∧
    (recordAttempt st a w c).ranked = st.ranked := by
  simp [recordAttempt]

theorem remember_fields (st : SState n) (o : Option (List Bool)) :
    (remember st o).attempts = st.attempts ∧ (remember st o).screened = st.screened ∧
    (remember st o).used = st.used ∧
    (remember st o).witnesses.length ≤ st.witnesses.length + 1 ∧
    (remember st o).ranked = st.ranked := by
  unfold remember
  split
  · split <;> simp
  · simp

theorem examine_accInv (src : BForm n) (rk : Ranker n) (b : Budget) (st : SState n) (e : Entry n)
    (h : AccInv b st) (hu : st.used < b.checks) (ha : st.attempts.length < b.proposals) :
    AccInv b (examine src rk b st e) := by
  have hsw := screenWork_snd_le src e.cand st.witnesses
  have hscr := h.screened_le
  have hwit := h.wit_le
  have hrk := h.ranked_le
  have key : st.screened + (screenWork src e.cand st.witnesses).2 ≤
      (st.attempts.length + 1) * b.checks := by
    rw [Nat.succ_mul]; omega
  have hm : MAX_ACTIONS * (st.attempts.length + 1 + 1) =
      MAX_ACTIONS * (st.attempts.length + 1) + MAX_ACTIONS := by rw [Nat.mul_succ]
  unfold examine
  dsimp only
  split
  · rename_i w _
    obtain ⟨r1, r2, r3, r4, r5⟩ := recordAttempt_fields st
      ⟨e.parent, e.action, e.cand, e.level, some w, none⟩ (screenWork src e.cand st.witnesses).2 false
    obtain ⟨h1, h2, h3, h4, _, h6⟩ := expand_fields rk b (recordAttempt st
      ⟨e.parent, e.action, e.cand, e.level, some w, none⟩ (screenWork src e.cand st.witnesses).2 false)
      e.cand e.level
    simp only [Bool.false_eq_true, ite_false] at r3
    refine ⟨?_, ?_, ?_, ?_, ?_, ?_⟩ <;> simp only [h1, h2, h3, h4, r1, r2, r3, r4]
    · exact h.used_pos
    · exact h.used_le
    · omega
    · exact h.wit_le
    · exact key
    · rw [r5] at h6; omega
  · obtain ⟨r1, r2, r3, r4, r5⟩ := recordAttempt_fields st
      ⟨e.parent, e.action, e.cand, e.level, none, some (checkReceipt src e.cand)⟩
      (screenWork src e.cand st.witnesses).2 true
    simp only [ite_true] at r3
    split
    · refine ⟨?_, ?_, ?_, ?_, ?_, ?_⟩ <;> simp only [r1, r2, r3, r4, r5]
      · omega
      · omega
      · omega
      · omega
      · exact key
      · omega
    · obtain ⟨m1, m2, m3, m4, m5⟩ := remember_fields (recordAttempt st
        ⟨e.parent, e.action, e.cand, e.level, none, some (checkReceipt src e.cand)⟩
        (screenWork src e.cand st.witnesses).2 true) (checkReceipt src e.cand).witness
      obtain ⟨h1, h2, h3, h4, _, h6⟩ := expand_fields rk b (remember (recordAttempt st
        ⟨e.parent, e.action, e.cand, e.level, none, some (checkReceipt src e.cand)⟩
        (screenWork src e.cand st.witnesses).2 true) (checkReceipt src e.cand).witness)
        e.cand e.level
      refine ⟨?_, ?_, ?_, ?_, ?_, ?_⟩ <;> simp only [h1, h2, h3, h4, m1, m2, m3, r1, r2, r3]
      · omega
      · omega
      · omega
      · rw [r4] at m4; omega
      · exact key
      · rw [m5, r5] at h6; omega

theorem loop_accInv (src : BForm n) (rk : Ranker n) (b : Budget) :
    ∀ fuel (st : SState n), AccInv b st → AccInv b (loop src rk b fuel st)
  | 0, st, h => h
  | fuel + 1, st, h => by
      unfold loop
      split
      · exact h
      · rename_i hc
        simp only [Bool.or_eq_true, decide_eq_true_eq, not_or, Nat.not_le] at hc
        split
        · exact h
        · split
          · exact loop_accInv src rk b fuel _ ⟨h.1, h.2, h.3, h.4, h.5, h.6⟩
          · exact loop_accInv src rk b fuel _
              (examine_accInv src rk b _ _ ⟨h.1, h.2, h.3, h.4, h.5, h.6⟩ hc.1.2 hc.2)

theorem initState_accInv (src cand : BForm n) (rk : Ranker n) (b : Budget) (hb : b.valid = true) :
    AccInv b (initState src cand rk b) := by
  simp only [Budget.valid, decide_eq_true_eq] at hb
  unfold initState
  dsimp only
  split
  · exact ⟨Nat.le_refl 1, by show 1 ≤ b.checks; omega, Nat.zero_le _, Nat.zero_le _,
      Nat.zero_le _, Nat.zero_le _⟩
  · obtain ⟨h1, h2, h3, h4, _, h6⟩ := expand_fields rk b
      { frontier := [], seen := [cand], witnesses := (checkReceipt src cand).witness.toList,
        attempts := [], used := 1, screened := 0, ranked := 0, solution := none } cand 0
    refine ⟨?_, ?_, ?_, ?_, ?_, ?_⟩ <;> simp only [h1, h2, h3, h4]
    · exact Nat.le_refl 1
    · show 1 ≤ b.checks; omega
    · exact Nat.zero_le _
    · show (checkReceipt src cand).witness.toList.length ≤ 1
      cases (checkReceipt src cand).witness <;> simp
    · exact Nat.zero_le _
    · simp only at h6; simp; omega

/-- **Implemented accounting bounds** (valid budgets, every ranking). -/
theorem search_accounting (src cand : BForm n) (rk : Ranker n) (b : Budget) (hb : b.valid = true) :
    let w := searchWork src cand rk b
    1 ≤ w.checksUsed ∧ w.checksUsed ≤ b.checks ∧ w.attempts ≤ b.proposals ∧
      w.witnessEvaluations ≤ w.attempts * b.checks ∧
      w.rankedProposals ≤ MAX_ACTIONS * (w.attempts + 1) := by
  have h := loop_accInv src rk b (searchFuel b) _ (initState_accInv src cand rk b hb)
  exact ⟨h.used_pos, h.used_le, h.att_le, h.screened_le, h.ranked_le⟩

theorem search_checksUsed_eq (src cand : BForm n) (rk : Ranker n) (b : Budget) :
    (search src cand rk b).checksUsed = (searchWork src cand rk b).checksUsed ∧
    (search src cand rk b).witnessEvaluations = (searchWork src cand rk b).witnessEvaluations ∧
    (search src cand rk b).attempts.length = (searchWork src cand rk b).attempts :=
  ⟨rfl, rfl, rfl⟩

/-! ## Independent replay of a recorded episode -/

structure RState (n : Nat) where
  states : List (BForm n × Nat)
  witnesses : List (List Bool)
  used : Nat
  screened : Nat
  solution : Option (BForm n)

def lookupState (st : List (BForm n × Nat)) (f : BForm n) : Option Nat :=
  (st.find? (fun x => x.1 == f)).map (·.2)

/-- Remember a replayed counterexample (if new). -/
def rememberR (st : RState n) : Option (List Bool) → RState n
  | some w => if w ∈ st.witnesses then st else { st with witnesses := st.witnesses ++ [w] }
  | none => st

/-- After a fresh exhaustive check of `c`: count it, accept only on equivalence. -/
def finishChecked (src : BForm n) (st1 : RState n) (c : BForm n) : RState n :=
  let st2 := { st1 with used := st1.used + 1 }
  if (checkReceipt src c).equivalent then { st2 with solution := some c }
  else rememberR st2 (checkReceipt src c).witness

/-- Screening / fresh-check part of a replayed attempt. -/
def replayCore (src : BForm n) (st : RState n) (c : BForm n) (level : Nat) (row : Attempt n) :
    Option (RState n) :=
  let st1 := { st with states := st.states ++ [(c, level + 1)],
                       screened := st.screened + (screenWork src c st.witnesses).2 }
  match (screenWork src c st.witnesses).1 with
  | some _ => if row.receipt.isSome then none else some st1
  | none => if row.receipt = some (checkReceipt src c) then some (finishChecked src st1 c) else none

/-- Replay one recorded attempt; `none` = rejection. -/
def replayRow (src : BForm n) (b : Budget) (st : RState n) (row : Attempt n) : Option (RState n) :=
  if st.solution.isSome || decide (st.used ≥ b.checks) then none else
  match lookupState st.states row.parent, applyAction row.parent row.action with
  | some level, some c =>
      if c = row.cand ∧ (lookupState st.states c).isNone ∧ row.depth = level + 1 ∧
          1 ≤ row.depth ∧ row.depth ≤ b.depth ∧ row.rejectedBy = (screenWork src c st.witnesses).1
      then replayCore src st c level row else none
  | _, _ => none

def replayRows (src : BForm n) (b : Budget) : RState n → List (Attempt n) → Option (RState n)
  | st, [] => some st
  | st, row :: rows => match replayRow src b st row with
      | none => none
      | some st' => replayRows src b st' rows

/-- `replay(episode)`: regenerate everything except the (unreplayed) ranking order. -/
def replay (ep : Episode n) : Bool :=
  ep.pcsAuthority == false && ep.leanKernelChecked == false && ep.budget.valid &&
  bounded ep.source && bounded ep.candidate &&
  ep.initial == checkReceipt ep.source ep.candidate &&
  decide (ep.attempts.length ≤ ep.budget.proposals) &&
  (let r := ep.initial
   let st0 : RState n :=
      { states := [(ep.candidate, 0)],
        witnesses := if r.equivalent then [] else r.witness.toList, used := 1, screened := 0,
        solution := if r.equivalent then some ep.candidate else none }
   match replayRows ep.source ep.budget st0 ep.attempts with
   | none => false
   | some st => st.used == ep.checksUsed && st.screened == ep.witnessEvaluations &&
       st.solution == ep.solution &&
       ep.status == (if st.solution.isSome then .booleanVerified else .budgetOrSearchExhausted))

def RSolInv (src : BForm n) (st : RState n) : Prop := ∀ s, st.solution = some s → SemEquiv src s

theorem finishChecked_sol (src : BForm n) (st1 : RState n) (c : BForm n) :
    (finishChecked src st1 c).solution = st1.solution ∨
      ((finishChecked src st1 c).solution = some c ∧ SemEquiv src c) := by
  unfold finishChecked
  dsimp only
  split
  · rename_i heq; exact Or.inr ⟨rfl, (checkReceipt_equivalent_iff src c).1 heq⟩
  · left; unfold rememberR; split
    · split <;> rfl
    · rfl

theorem finishChecked_sol' {src : BForm n} {st1 : RState n} {c s : BForm n}
    (hs : (finishChecked src st1 c).solution = some s) : st1.solution = some s ∨ SemEquiv src s := by
  rcases finishChecked_sol src st1 c with h1 | ⟨h1, h2⟩
  · rw [h1] at hs; exact Or.inl hs
  · rw [h1] at hs; cases hs; exact Or.inr h2

theorem replayRow_inv (src : BForm n) (b : Budget) (st st' : RState n) (row : Attempt n)
    (h : RSolInv src st) (hr : replayRow src b st row = some st') : RSolInv src st' := by
  intro s hs
  unfold replayRow at hr
  split at hr
  · cases hr
  · split at hr
    · split at hr
      · unfold replayCore at hr
        dsimp only at hr
        split at hr
        · split at hr
          · cases hr
          · cases hr; exact h s hs
        · split at hr
          · cases hr
            rcases finishChecked_sol' hs with h1 | h2
            · exact h s h1
            · exact h2
          · cases hr
      · cases hr
    · cases hr

theorem replayRows_inv (src : BForm n) (b : Budget) :
    ∀ (rows : List (Attempt n)) (st st' : RState n), RSolInv src st →
      replayRows src b st rows = some st' → RSolInv src st'
  | [], st, st', h, hr => by simp [replayRows] at hr; subst hr; exact h
  | row :: rows, st, st', h, hr => by
      unfold replayRows at hr
      split at hr
      · cases hr
      · rename_i st1 h1
        exact replayRows_inv src b rows st1 st' (replayRow_inv src b st st1 row h h1) hr

/-- **Replayed acceptance is sound**: an episode accepted by `replay` with a solution
carries a candidate semantically equivalent to its immutable source. -/
theorem replay_sound (ep : Episode n) (h : replay ep = true) {s : BForm n}
    (hs : ep.solution = some s) : SemEquiv ep.source s := by
  unfold replay at h
  simp only [Bool.and_eq_true, beq_iff_eq] at h
  obtain ⟨⟨⟨⟨⟨⟨⟨_, _⟩, _⟩, _⟩, _⟩, hinit⟩, _⟩, hrest⟩ := h
  split at hrest
  · cases hrest
  · rename_i st hst
    simp only [Bool.and_eq_true, beq_iff_eq] at hrest
    obtain ⟨⟨⟨_, _⟩, hsol⟩, _⟩ := hrest
    refine replayRows_inv ep.source ep.budget ep.attempts _ st ?_ hst s (hsol.trans hs)
    intro s' hs'
    simp only at hs'
    split at hs'
    · rename_i heq; simp at hs'; subst hs'
      rw [hinit] at heq
      exact (checkReceipt_equivalent_iff _ _).1 heq
    · cases hs'

end PCSOmega
