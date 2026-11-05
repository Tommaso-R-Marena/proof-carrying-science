import PCSRuntimeRefinement.Python
import PCSRuntimeRefinement.Eventually
import PCSDecisionDiagram

/-!
# The extracted Python `bellman` refines the Lean reference pass

For every valid input — a node table whose variable indices are in range and whose children
precede each node (append order), names / baseline / costs / locked agreeing with prices `P` —
executing the source-extracted program `bellmanCore` under the Python semantics returns, for all
sufficiently large fuel, exactly the encoding of `PCSDD.bellmanPass ns P`: the full `cells`
list (`None` or `[cost, count, mandatory-mask, possible-mask]`) and the full `choices` list
(`None` or the first-winning Boolean, so `False` wins ties).
-/

namespace PCSRuntimeRefinement.PyBellman

open PCSRuntimeRefinement PCSDD

/-! ## Encodings -/

def encRaw (c : Cell) : Val := .list [.int c.cost, .int c.count, .int c.mand, .int c.poss]

def encCell : Option Cell → Val
  | none => .none
  | some c => encRaw c

def encChoice : Option Bool → Val
  | none => .none
  | some b => .bool b

def encBr (p : Bool × Cell) : Val := .tuple [.bool p.1, encRaw p.2]

def encNode (nd : Node) : Val := .list [.int nd.var, .int nd.low, .int nd.high]

/-! ## The extracted program, by parts -/

def v (x : String) : E := .var x
def i (k : Int) : E := .lit (.int k)
def at' (x : String) (k : Int) : E := .index (v x) (i k)

def innerBody : List S := [
  .ifThen (.and (.mem (v "name") (v "locked")) (.bin .ne (v "value") (.index (v "baseline") (v "name"))))
    [.cont],
  .assign (.v "cell") (.index (v "cells") (v "child")),
  .ifThen (.isNone (v "cell")) [.cont],
  .assign (.v "flip") (.bin .ne (v "value") (.index (v "baseline") (v "name"))),
  .append "branches" (.tuple [v "value", .list [
    .bin .add (at' "cell" 0) (.cond (v "flip") (.index (v "costs") (v "name")) (i 0)),
    at' "cell" 1,
    .bin .bor (at' "cell" 2) (.cond (v "flip") (v "bit") (i 0)),
    .bin .bor (at' "cell" 3) (.cond (v "flip") (v "bit") (i 0))]])]

def mergeBody : List S := [
  .augIndex "cell" (i 1) .add (at' "other" 1),
  .augIndex "cell" (i 2) .band (at' "other" 2),
  .augIndex "cell" (i 3) .bor (at' "other" 3)]

def tailBody : List S := [
  .ifThen (.not (v "branches")) [.append "cells" (.lit .none), .append "choices" (.lit .none), .cont],
  .assign (.v "best") (.min (.comp (at' "cell" 0) (.tup ["_", "cell"]) (v "branches") none)),
  .assign (.v "winners") (.comp (.tuple [v "value", v "cell"]) (.tup ["value", "cell"]) (v "branches")
    (some (.bin .eq (at' "cell" 0) (v "best")))),
  .assign (.v "cell") (.copy (.index (at' "winners" 0) (i 1))),
  .forIn (.tup ["_", "other"]) (.sliceFrom (v "winners") (i 1)) mergeBody,
  .append "cells" (v "cell"),
  .append "choices" (.index (at' "winners" 0) (i 0))]

def branchPairs : E :=
  .tuple [.tuple [.lit (.bool false), v "low"], .tuple [.lit (.bool true), v "high"]]

def outerBody : List S :=
  .assign (.tup ["name", "bit"]) (.tuple [.index (v "names") (v "var"), .bin .shl (i 1) (v "var")]) ::
  .assign (.v "branches") (.list []) ::
  .forIn (.tup ["value", "child"]) branchPairs innerBody :: tailBody

theorem core_shape : Py.bellmanCore = ⟨["nodes", "names", "baseline", "costs", "locked"], [
    .assign (.v "cells") (.list [.lit .none, .list [i 0, i 1, i 0, i 0]]),
    .assign (.v "choices") (.list [.lit .none, .lit .none]),
    .forIn (.tup ["var", "low", "high"]) (v "nodes") outerBody,
    .ret (.tuple [v "cells", v "choices"])]⟩ := rfl

/-! ## Primitive facts -/

theorem pyEq_bool (a b : Bool) : pyEq (.bool a) (.bool b) = (a == b) := by
  cases a <;> cases b <;> rfl

theorem ne_bool (a b : Bool) : binOp .py .ne (.bool a) (.bool b) = .ok (.bool (a != b)) := by
  cases a <;> cases b <;> rfl

theorem eq_int (a b : Int) : binOp .py .eq (.int a) (.int b) = .ok (.bool (a == b)) := rfl

theorem add_int (a b : Int) : binOp .py .add (.int a) (.int b) = .ok (.int (a + b)) := rfl

theorem bor_nat (a b : Nat) : binOp .py .bor (.int a) (.int b) = .ok (.int ((a ||| b : Nat) : Int)) := rfl

theorem band_nat (a b : Nat) : binOp .py .band (.int a) (.int b) = .ok (.int ((a &&& b : Nat) : Int)) := rfl

theorem lt_int (a b : Int) : binOp .py .lt (.int a) (.int b) = .ok (.bool (decide (a < b))) := rfl

theorem shl_one (k : Nat) : binOp .py .shl (.int 1) (.int k) = .ok (.int ((2 ^ k : Nat) : Int)) := by
  simp [binOp, pyNum]

theorem index_raw0 (c : Cell) : indexOp .py (encRaw c) (.int 0) = .ok (.int c.cost) := rfl
theorem index_raw1 (c : Cell) : indexOp .py (encRaw c) (.int 1) = .ok (.int c.count) := rfl
theorem index_raw2 (c : Cell) : indexOp .py (encRaw c) (.int 2) = .ok (.int c.mand) := rfl
theorem index_raw3 (c : Cell) : indexOp .py (encRaw c) (.int 3) = .ok (.int c.poss) := rfl

theorem index_br0 (p : Bool × Cell) : indexOp .py (encBr p) (.int 0) = .ok (.bool p.1) := rfl
theorem index_br1 (p : Bool × Cell) : indexOp .py (encBr p) (.int 1) = .ok (encRaw p.2) := rfl

theorem index_list_nat {α : Type} (f : α → Val) (xs : List α) (k : Nat) (hk : k < xs.length) :
    indexOp .py (.list (xs.map f)) (.int k) = .ok (f xs[k]) := by
  have hk' : ((k : Int) < ((xs.map f).length : Int)) := by simp; omega
  simp only [indexOp, pyNum]
  have h0 : ¬ ((k : Int) < 0) := by omega
  simp only [h0, if_false]
  rw [if_pos ⟨by omega, hk'⟩]
  simp [List.getD_eq_getElem?_getD, hk]

theorem index_head0 (x : Val) (xs : List Val) : indexOp .py (.list (x :: xs)) (.int 0) = .ok x := by
  have := index_list_nat id (x :: xs) 0 (by simp)
  simpa using this

theorem bind_tup2 (a b : String) (x y : Val) (env : Env) :
    bindPat .py (.tup [a, b]) (.tuple [x, y]) env = .ok ((env.set a x).set b y) := rfl

theorem bind_tup3 (a b c : String) (x y z : Val) (env : Env) :
    bindPat .py (.tup [a, b, c]) (.list [x, y, z]) env = .ok (((env.set a x).set b y).set c z) := rfl

/-! ## Comprehensions, `min` and the merge loop -/

theorem costs_comp (env : Env) (brs : List (Bool × Cell)) :
    EvC .py env (at' "cell" 0) (.tup ["_", "cell"]) none (brs.map encBr)
      (.ok (brs.map (fun b => Val.int b.2.cost))) := by
  induction brs with
  | nil => exact EvC.nil
  | cons b brs ih =>
      refine EvC.cons_none (bind_tup2 _ _ _ _ env) ?_ ih
      have := EvE.index (d := .py) (EvE.var (Env.get_set_self _ "cell" (encRaw b.2)))
        (EvE.lit (env := ((env.set "_" (.bool b.1)).set "cell" (encRaw b.2))) (.int 0))
      rwa [index_raw0] at this

theorem min_fold (ys : List Nat) (a : Nat) :
    (ys.map (fun c : Nat => Val.int (c : Int))).foldlM (fun m y => (binOp .py .lt y m).bind fun c =>
      match c with
      | .bool true => .ok y
      | .bool false => .ok m
      | _ => .exc .typeError) (Val.int (a : Int)) = .ok (.int ((ys.foldl Nat.min a : Nat) : Int)) := by
  induction ys generalizing a with
  | nil => rfl
  | cons y ys ih =>
      simp only [List.map_cons, List.foldl_cons]
      show (Res.bind ((binOp .py .lt (.int y) (.int a)).bind _) _) = _
      rw [lt_int]
      by_cases h : (y : Int) < a
      · have hm : Nat.min a y = y := by simp only [Nat.min_def]; split <;> omega
        simp only [Res.bind_ok, decide_eq_true h]
        rw [hm]; exact ih y
      · have hm : Nat.min a y = a := by simp only [Nat.min_def]; split <;> omega
        simp only [Res.bind_ok, decide_eq_false h]
        rw [hm]; exact ih a

theorem min_costs (b : Bool × Cell) (brs : List (Bool × Cell)) :
    minOp .py ((b :: brs).map (fun b => Val.int b.2.cost)) =
      .ok (.int (((b :: brs).foldl (fun m p => Nat.min m p.2.cost) b.2.cost : Nat) : Int)) := by
  simp only [List.map_cons, minOp]
  have := min_fold (brs.map (·.2.cost)) b.2.cost
  rw [List.map_map] at this
  have hself : Nat.min b.2.cost b.2.cost = b.2.cost := by simp
  rw [List.foldl_cons, hself]
  rw [List.foldl_map] at this
  exact this

theorem winners_comp (env : Env) (best : Nat) (hb : env.get "best" = some (.int best))
    (brs : List (Bool × Cell)) :
    EvC .py env (.tuple [v "value", v "cell"]) (.tup ["value", "cell"])
      (some (.bin .eq (at' "cell" 0) (v "best"))) (brs.map encBr)
      (.ok ((brs.filter (fun p => p.2.cost == best)).map encBr)) := by
  induction brs with
  | nil => exact EvC.nil
  | cons b brs ih =>
      have hb' : ((env.set "value" (.bool b.1)).set "cell" (encRaw b.2)).get "best" = some (.int best) := by
        rw [Env.get_set_ne _ _ (by decide), Env.get_set_ne _ _ (by decide), hb]
      have hc : EvE .py ((env.set "value" (.bool b.1)).set "cell" (encRaw b.2))
          (.bin .eq (at' "cell" 0) (v "best")) (.ok (.bool ((b.2.cost : Int) == (best : Int)))) := by
        have h1 := EvE.index (d := .py) (EvE.var (Env.get_set_self _ "cell" (encRaw b.2)))
          (EvE.lit (env := ((env.set "value" (.bool b.1)).set "cell" (encRaw b.2))) (.int 0))
        rw [index_raw0] at h1
        have := EvE.bin (op := .eq) h1 (EvE.var hb')
        rwa [eq_int] at this
      by_cases hcost : b.2.cost = best
      · have he : EvE .py ((env.set "value" (.bool b.1)).set "cell" (encRaw b.2))
            (.tuple [v "value", v "cell"]) (.ok (encBr b)) := by
          refine EvE.tuple (EvL.cons ?_ (EvL.cons (EvE.var (Env.get_set_self _ _ _)) EvL.nil))
          exact EvE.var (by rw [Env.get_set_ne _ _ (by decide), Env.get_set_self])
        have := EvC.cons_keep (bind_tup2 _ _ _ _ env) hc (by simp [truthy, hcost]) he ih
        simpa [List.filter_cons, hcost] using this
      · have := EvC.cons_drop (elt := .tuple [v "value", v "cell"]) (bind_tup2 _ _ _ _ env) hc
          (by simp [truthy]; omega) ih
        simpa [List.filter_cons, hcost] using this

/-- Python's `cell[k] op= other[k]` on encoded cells. -/
theorem merge_loop (ws : List (Bool × Cell)) :
    ∀ (env : Env) (acc : Cell), env.get "cell" = some (encRaw acc) →
      ∃ env', ExF .py env (.tup ["_", "other"]) mergeBody (ws.map encBr) (.ok (.normal env')) ∧
        env'.get "cell" = some (encRaw (ws.foldl (fun a p => mergeCell a p.2) acc)) ∧
        ∀ y, y ≠ "_" → y ≠ "other" → y ≠ "cell" → env'.get y = env.get y := by
  induction ws with
  | nil => intro env acc h; exact ⟨env, ExF.nil, h, fun _ _ _ _ => rfl⟩
  | cons w ws ih =>
      intro env acc hc
      let env1 := (env.set "_" (.bool w.1)).set "other" (encRaw w.2)
      have hc1 : env1.get "cell" = some (encRaw acc) := by
        simp only [env1]; rw [Env.get_set_ne _ _ (by decide), Env.get_set_ne _ _ (by decide), hc]
      have ho1 : env1.get "other" = some (encRaw w.2) := Env.get_set_self _ _ _
      let x1 : Val := .list [.int acc.cost, .int ((acc.count : Int) + w.2.count), .int acc.mand, .int acc.poss]
      let env2 := env1.set "cell" x1
      have s1 : ExS .py env1 (.augIndex "cell" (i 1) .add (at' "other" 1)) (.ok (.normal env2)) := by
        refine ExS.augIndex hc1 (EvE.lit _) (index_raw1 acc) ?_ (add_int _ _) rfl
        have := EvE.index (d := .py) (EvE.var ho1) (EvE.lit (env := env1) (.int 1))
        rwa [index_raw1] at this
      have hc2 : env2.get "cell" = some x1 := Env.get_set_self _ _ _
      have ho2 : env2.get "other" = some (encRaw w.2) := by
        simp only [env2]; rw [Env.get_set_ne _ _ (by decide), ho1]
      let x2 : Val := .list [.int acc.cost, .int ((acc.count : Int) + w.2.count),
        .int ((acc.mand &&& w.2.mand : Nat) : Int), .int acc.poss]
      let env3 := env2.set "cell" x2
      have s2 : ExS .py env2 (.augIndex "cell" (i 2) .band (at' "other" 2)) (.ok (.normal env3)) := by
        refine ExS.augIndex hc2 (EvE.lit _) rfl ?_ (band_nat _ _) rfl
        have := EvE.index (d := .py) (EvE.var ho2) (EvE.lit (env := env2) (.int 2))
        rwa [index_raw2] at this
      have hc3 : env3.get "cell" = some x2 := Env.get_set_self _ _ _
      have ho3 : env3.get "other" = some (encRaw w.2) := by
        simp only [env3]; rw [Env.get_set_ne _ _ (by decide), ho2]
      let x3 : Val := .list [.int acc.cost, .int ((acc.count : Int) + w.2.count),
        .int ((acc.mand &&& w.2.mand : Nat) : Int), .int ((acc.poss ||| w.2.poss : Nat) : Int)]
      let env4 := env3.set "cell" x3
      have s3 : ExS .py env3 (.augIndex "cell" (i 3) .bor (at' "other" 3)) (.ok (.normal env4)) := by
        refine ExS.augIndex hc3 (EvE.lit _) rfl ?_ (bor_nat _ _) rfl
        have := EvE.index (d := .py) (EvE.var ho3) (EvE.lit (env := env3) (.int 3))
        rwa [index_raw3] at this
      have hb : ExB .py env1 mergeBody (.ok (.normal env4)) :=
        ExB.cons_normal s1 (ExB.cons_normal s2 (ExB.cons_normal s3 ExB.nil))
      have hc4 : env4.get "cell" = some (encRaw (mergeCell acc w.2)) := by
        simp only [env4, Env.get_set_self, x3, encRaw, mergeCell, Int.natCast_add]
      obtain ⟨env', hf, hcell, hframe⟩ := ih env4 (mergeCell acc w.2) hc4
      refine ⟨env', ExF.cons_normal (bind_tup2 _ _ _ _ env) hb hf, ?_, ?_⟩
      · simpa [List.foldl_cons] using hcell
      · intro y h1 h2 h3
        rw [hframe y h1 h2 h3]
        simp only [env4, env3, env2, env1]
        rw [Env.get_set_ne _ _ h3, Env.get_set_ne _ _ h3, Env.get_set_ne _ _ h3,
          Env.get_set_ne _ _ h2, Env.get_set_ne _ _ h1]

theorem foldl_min_attained (l : List (Bool × Cell)) (a : Nat) :
    l.foldl (fun m p => Nat.min m p.2.cost) a = a ∨
      ∃ p ∈ l, l.foldl (fun m p => Nat.min m p.2.cost) a = p.2.cost := by
  induction l generalizing a with
  | nil => exact Or.inl rfl
  | cons q l ih =>
      simp only [List.foldl_cons]
      rcases ih (Nat.min a q.2.cost) with h | ⟨p, hp, h⟩
      · rw [h]
        by_cases hq : a ≤ q.2.cost
        · left; simp [hq]
        · right; exact ⟨q, List.mem_cons_self, by simp [Nat.min_def, hq]⟩
      · right; exact ⟨p, List.mem_cons_of_mem _ hp, h⟩

theorem winners_nonempty (b : Bool × Cell) (rest : List (Bool × Cell)) :
    ∃ w others, (b :: rest).filter (fun p => p.2.cost == (b :: rest).foldl (fun m p => Nat.min m p.2.cost) b.2.cost)
      = w :: others := by
  generalize hbest : (b :: rest).foldl (fun m p => Nat.min m p.2.cost) b.2.cost = best
  have hmem : ∃ p ∈ b :: rest, p.2.cost = best := by
    rcases foldl_min_attained (b :: rest) b.2.cost with h | ⟨p, hp, h⟩
    · exact ⟨b, List.mem_cons_self, by rw [← hbest, h]⟩
    · exact ⟨p, hp, by rw [← hbest, h]⟩
  obtain ⟨p, hp, hpc⟩ := hmem
  cases hf : (b :: rest).filter (fun p => p.2.cost == best) with
  | nil =>
      have : p ∈ (b :: rest).filter (fun p => p.2.cost == best) := List.mem_filter.2 ⟨hp, by simp [hpc]⟩
      rw [hf] at this; cases this
  | cons w others => exact ⟨w, others, rfl⟩

/-- The statements after the branch loop compute `winnersCell` of the collected branches. -/
theorem tail_spec (env : Env) (brs : List (Bool × Cell)) (cellsL choicesL : List Val)
    (hbr : env.get "branches" = some (.list (brs.map encBr)))
    (hcl : env.get "cells" = some (.list cellsL)) (hch : env.get "choices" = some (.list choicesL)) :
    ∃ env', (ExB .py env tailBody (.ok (.normal env')) ∨ ExB .py env tailBody (.ok (.cont env'))) ∧
      env'.get "cells" = some (.list (cellsL ++ [encCell (winnersCell brs).1])) ∧
      env'.get "choices" = some (.list (choicesL ++ [encChoice (winnersCell brs).2])) ∧
      ∀ y, y ≠ "_" → y ≠ "other" → y ≠ "cell" → y ≠ "best" → y ≠ "winners" → y ≠ "cells" →
        y ≠ "choices" → env'.get y = env.get y := by
  cases brs with
  | nil =>
      let env1 := env.set "cells" (.list (cellsL ++ [.none]))
      let env2 := env1.set "choices" (.list (choicesL ++ [.none]))
      have hch1 : env1.get "choices" = some (.list choicesL) := by
        simp only [env1]; rw [Env.get_set_ne _ _ (by decide), hch]
      have hb : ExB .py env [.append "cells" (.lit .none), .append "choices" (.lit .none), .cont]
          (.ok (.cont env2)) :=
        ExB.cons_normal (ExS.append hcl (EvE.lit _))
          (ExB.cons_normal (ExS.append hch1 (EvE.lit _)) (ExB.cons_cont ExS.cont))
      have hs := ExS.if_cont (EvE.not (EvE.var hbr)) (by rfl) hb
      refine ⟨env2, Or.inr (ExB.cons_cont hs), ?_, ?_, ?_⟩
      · simp only [env2]; rw [Env.get_set_ne _ _ (by decide)]; simp [env1, winnersCell, encCell]
      · simp [env2, winnersCell, encChoice]
      · intro y _ _ _ _ _ h6 h7
        simp only [env2, env1]; rw [Env.get_set_ne _ _ h7, Env.get_set_ne _ _ h6]
  | cons b rest =>
      obtain ⟨w, others, hws⟩ := winners_nonempty b rest
      have hwc : winnersCell (b :: rest) =
          (some (others.foldl (fun acc p => mergeCell acc p.2) w.2), some w.1) := by
        unfold winnersCell; simp only; rw [hws]
      rw [hwc]
      have hmin0 := min_costs b rest
      generalize (b :: rest).foldl (fun m p => Nat.min m p.2.cost) b.2.cost = best at hws hmin0
      have s1 : ExS .py env (.ifThen (.not (v "branches"))
          [.append "cells" (.lit .none), .append "choices" (.lit .none), .cont]) (.ok (.normal env)) :=
        ExS.if_false (EvE.not (EvE.var hbr)) rfl
      have hmin : EvE .py env (.min (.comp (at' "cell" 0) (.tup ["_", "cell"]) (v "branches") none))
          (.ok (.int best)) := by
        have := EvE.min (EvE.comp (EvE.var hbr) rfl (costs_comp env (b :: rest))) rfl
        rwa [hmin0] at this
      let env1 := env.set "best" (.int best)
      have s2 := ExS.assign (p := .v "best") hmin (rfl : bindPat .py _ _ env = .ok env1)
      have hbr1 : env1.get "branches" = some (.list ((b :: rest).map encBr)) := by
        simp only [env1]; rw [Env.get_set_ne _ _ (by decide), hbr]
      have hcomp := EvE.comp (EvE.var hbr1) rfl
        (winners_comp env1 best (Env.get_set_self _ _ _) (b :: rest))
      rw [hws] at hcomp
      let env2 := env1.set "winners" (.list ((w :: others).map encBr))
      have s3 := ExS.assign (p := .v "winners") hcomp (rfl : bindPat .py _ _ env1 = .ok env2)
      have hw2 : env2.get "winners" = some (.list ((w :: others).map encBr)) := Env.get_set_self _ _ _
      have hw0 : ∀ env' : Env, env'.get "winners" = some (.list ((w :: others).map encBr)) →
          EvE .py env' (at' "winners" 0) (.ok (encBr w)) := by
        intro env' h
        have := EvE.index (d := .py) (EvE.var h) (EvE.lit (env := env') (.int 0))
        rw [List.map_cons, index_head0] at this; exact this
      have hcell : EvE .py env2 (.copy (.index (at' "winners" 0) (i 1))) (.ok (encRaw w.2)) := by
        have h1 := EvE.index (d := .py) (hw0 env2 hw2) (EvE.lit (env := env2) (.int 1))
        rw [index_br1] at h1
        exact EvE.copy h1 rfl
      let env3 := env2.set "cell" (encRaw w.2)
      have s4 := ExS.assign (p := .v "cell") hcell (rfl : bindPat .py _ _ env2 = .ok env3)
      have hc3 : env3.get "cell" = some (encRaw w.2) := Env.get_set_self _ _ _
      obtain ⟨env4, hf, hc4, hfr4⟩ := merge_loop others env3 w.2 hc3
      have hw3 : env3.get "winners" = some (.list ((w :: others).map encBr)) := by
        simp only [env3]; rw [Env.get_set_ne _ _ (by decide), hw2]
      have hsl : EvE .py env3 (.sliceFrom (v "winners") (i 1)) (.ok (.list (others.map encBr))) := by
        have := EvE.sliceFrom (d := .py) (EvE.var hw3) (EvE.lit (env := env3) (.int 1))
        exact this
      have s5 := ExS.forIn hsl rfl hf
      have hcl4 : env4.get "cells" = some (.list cellsL) := by
        rw [hfr4 _ (by decide) (by decide) (by decide)]
        simp only [env3, env2, env1]
        rw [Env.get_set_ne _ _ (by decide), Env.get_set_ne _ _ (by decide),
          Env.get_set_ne _ _ (by decide), hcl]
      let env5 := env4.set "cells" (.list (cellsL ++ [encRaw (others.foldl (fun a p => mergeCell a p.2) w.2)]))
      have s6 := ExS.append (d := .py) (e := v "cell") hcl4 (EvE.var hc4)
      have hch5 : env5.get "choices" = some (.list choicesL) := by
        simp only [env5]
        rw [Env.get_set_ne _ _ (by decide), hfr4 _ (by decide) (by decide) (by decide)]
        simp only [env3, env2, env1]
        rw [Env.get_set_ne _ _ (by decide), Env.get_set_ne _ _ (by decide),
          Env.get_set_ne _ _ (by decide), hch]
      have hw5 : env5.get "winners" = some (.list ((w :: others).map encBr)) := by
        simp only [env5]
        rw [Env.get_set_ne _ _ (by decide), hfr4 _ (by decide) (by decide) (by decide), hw3]
      have hch0 : EvE .py env5 (.index (at' "winners" 0) (i 0)) (.ok (.bool w.1)) := by
        have h1 := EvE.index (d := .py) (hw0 env5 hw5) (EvE.lit (env := env5) (.int 0))
        rwa [index_br0] at h1
      let env6 := env5.set "choices" (.list (choicesL ++ [.bool w.1]))
      have s7 := ExS.append (d := .py) (e := .index (at' "winners" 0) (i 0)) hch5 hch0
      refine ⟨env6, Or.inl (ExB.cons_normal s1 (ExB.cons_normal s2 (ExB.cons_normal s3
        (ExB.cons_normal s4 (ExB.cons_normal s5 (ExB.cons_normal s6 (ExB.cons_normal s7 ExB.nil))))))),
        ?_, ?_, ?_⟩
      · simp only [env6, env5]; rw [Env.get_set_ne _ _ (by decide)]; simp [encCell]
      · simp [env6, encChoice]
      · intro y h1 h2 h3 h4 h5 h6 h7
        simp only [env6, env5]
        rw [Env.get_set_ne _ _ h7, Env.get_set_ne _ _ h6, hfr4 y h1 h2 h3]
        simp only [env3, env2, env1]
        rw [Env.get_set_ne _ _ h3, Env.get_set_ne _ _ h5, Env.get_set_ne _ _ h4]

end PCSRuntimeRefinement.PyBellman
