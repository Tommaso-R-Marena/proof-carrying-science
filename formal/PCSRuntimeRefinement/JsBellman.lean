import PCSRuntimeRefinement.JavaScript
import PCSRuntimeRefinement.PyBellmanLoop

/-!
# The extracted JavaScript `bellman`: primitives, comprehensions, merge loop and tail

JavaScript numbers are modelled exactly inside the safe-integer range; every arithmetic step
below is shown to stay inside that range (`+`, `**`) or inside the non-negative `int32`
range (`|`, `&`, whose operands pass through `ToInt32`).  Block exits drop `const` bindings
(`exitBlock .js`); all environment reasoning goes through `Env.get_exit_js`.
-/

namespace PCSRuntimeRefinement.JsBellman

open PCSRuntimeRefinement PCSDD
open PCSRuntimeRefinement.PyBellman (encRaw encCell encChoice encNode EvE.res_eq)

/-! ## Encodings and the extracted program -/

/-- A branch `[value, cell]` (a JS array). -/
def encBr (p : Bool × Cell) : Val := .list [.bool p.1, encRaw p.2]

def v (x : String) : E := .var x
def i (k : Int) : E := .lit (.int k)
def at' (x : String) (k : Int) : E := .index (v x) (i k)
def tf (k : String) : E := .index (.field (v "t") k) (v "n")
def flipOr (x : E) : E := .cond (v "flip") x (i 0)

def innerBody : List S := [
  .ifThen (.and (.mem (v "n") (.field (v "t") "locked")) (.bin .ne (v "value") (tf "baseline"))) [.cont],
  .assign (.v "cell") (.index (v "cells") (v "child")),
  .ifThen (.isNone (v "cell")) [.cont],
  .assign (.v "flip") (.bin .ne (v "value") (tf "baseline")),
  .append "branches" (.list [v "value", .list [
    .bin .add (at' "cell" 0) (flipOr (tf "costs")), at' "cell" 1,
    .bin .bor (at' "cell" 2) (flipOr (v "bit")), .bin .bor (at' "cell" 3) (flipOr (v "bit"))]])]

def mergeBody : List S := [
  .augIndex "cell" (i 1) .add (at' "other" 1),
  .augIndex "cell" (i 2) .band (at' "other" 2),
  .augIndex "cell" (i 3) .bor (at' "other" 3)]

def tailBody : List S := [
  .ifThen (.not (.field (v "branches") "length")) [.append "cells" (.lit .none), .append "choices" (.lit .none), .cont],
  .assign (.v "best") (.min (.comp (at' "c" 0) (.tup ["", "c"]) (v "branches") none)),
  .assign (.v "winners") (.comp (v Js.wholeName) (.whole Js.wholeName ["", "c"]) (v "branches")
    (some (.bin .eq (at' "c" 0) (v "best")))),
  .assign (.v "cell") (.copy (.index (at' "winners" 0) (i 1))),
  .forIn (.tup ["", "other"]) (.sliceFrom (v "winners") (i 1)) mergeBody,
  .append "cells" (v "cell"),
  .append "choices" (.index (at' "winners" 0) (i 0))]

def branchPairs : E := .list [.list [.lit (.bool false), v "lo"], .list [.lit (.bool true), v "hi"]]

def outerBody : List S :=
  .assign (.v "n") (.index (v "names") (v "v")) ::
  .assign (.v "bit") (.bin .pow (i 2) (v "v")) ::
  .assign (.v "branches") (.list []) ::
  .forIn (.tup ["value", "child"]) branchPairs innerBody :: tailBody

theorem core_shape : Js.bellmanCore = ⟨["nodes", "t"], [
    .assign (.v "cells") (.list [.lit .none, .list [i 0, i 1, i 0, i 0]]),
    .assign (.v "choices") (.list [.lit .none, .lit .none]),
    .assign (.v "names") (.field (.field (v "t") "problem") "variables"),
    .forIn (.tup ["v", "lo", "hi"]) (v "nodes") outerBody,
    .ret (.objLit ["cells", "choices"] [v "cells", v "choices"])]⟩ := rfl

/-! ## Primitive facts -/

theorem toInt32_id (x : Int) (h0 : 0 ≤ x) (h : x < 2 ^ 31) : toInt32 x = x := by
  unfold toInt32; omega

theorem ne_bool (a b : Bool) : binOp .js .ne (.bool a) (.bool b) = .ok (.bool (a != b)) := by
  cases a <;> cases b <;> rfl

theorem eq_int (a b : Int) : binOp .js .eq (.int a) (.int b) = .ok (.bool (a == b)) := rfl

theorem lt_int (a b : Int) : binOp .js .lt (.int a) (.int b) = .ok (.bool (decide (a < b))) := rfl

theorem add_int (a b : Int) (h1 : -MAX_SAFE ≤ a + b) (h2 : a + b ≤ MAX_SAFE) :
    binOp .js .add (.int a) (.int b) = .ok (.int (a + b)) := by
  simp [binOp, jsNumOf, jsNum, h1, h2]

theorem bor_nat (a b : Nat) (ha : a < 2 ^ 31) (hb : b < 2 ^ 31) :
    binOp .js .bor (.int a) (.int b) = .ok (.int ((a ||| b : Nat) : Int)) := by
  have hab : a ||| b < 2 ^ 31 := Nat.or_lt_two_pow ha hb
  simp only [binOp, jsNumOf]
  rw [toInt32_id a (by omega) (by omega), toInt32_id b (by omega) (by omega)]
  show Res.ok (Val.int (toInt32 ((a ||| b : Nat) : Int))) = _
  rw [toInt32_id _ (by omega) (by omega)]

theorem band_nat (a b : Nat) (ha : a < 2 ^ 31) (hb : b < 2 ^ 31) :
    binOp .js .band (.int a) (.int b) = .ok (.int ((a &&& b : Nat) : Int)) := by
  have hab : a &&& b < 2 ^ 31 := Nat.lt_of_le_of_lt Nat.and_le_left ha
  simp only [binOp, jsNumOf]
  rw [toInt32_id a (by omega) (by omega), toInt32_id b (by omega) (by omega)]
  show Res.ok (Val.int (toInt32 ((a &&& b : Nat) : Int))) = _
  rw [toInt32_id _ (by omega) (by omega)]

theorem pow_two (k : Nat) (hk : k < 31) :
    binOp .js .pow (.int 2) (.int k) = .ok (.int ((2 ^ k : Nat) : Int)) := by
  have h : 2 ^ k < 2 ^ 31 := Nat.pow_lt_pow_right (by omega) hk
  have e : (2 : Int) ^ k = ((2 ^ k : Nat) : Int) := by simp
  generalize hm : 2 ^ k = m at h e
  simp only [binOp, jsNumOf, Int.toNat_natCast, show ¬ ((k : Int) < 0) by omega, if_false, jsNum, e]
  rw [if_pos ⟨by unfold MAX_SAFE; omega, by unfold MAX_SAFE; omega⟩]

theorem index_list (xs : List Val) (k : Nat) (hk : k < xs.length) :
    indexOp .js (.list xs) (.int k) = .ok xs[k] := by
  simp [indexOp, hk, List.getD_eq_getElem?_getD]

theorem index_head0 (x : Val) (xs : List Val) : indexOp .js (.list (x :: xs)) (.int 0) = .ok x := by
  simp [indexOp]

theorem index_raw0 (c : Cell) : indexOp .js (encRaw c) (.int 0) = .ok (.int c.cost) := rfl
theorem index_raw1 (c : Cell) : indexOp .js (encRaw c) (.int 1) = .ok (.int c.count) := rfl
theorem index_raw2 (c : Cell) : indexOp .js (encRaw c) (.int 2) = .ok (.int c.mand) := rfl
theorem index_raw3 (c : Cell) : indexOp .js (encRaw c) (.int 3) = .ok (.int c.poss) := rfl
theorem index_br0 (p : Bool × Cell) : indexOp .js (encBr p) (.int 0) = .ok (.bool p.1) := rfl
theorem index_br1 (p : Bool × Cell) : indexOp .js (encBr p) (.int 1) = .ok (encRaw p.2) := rfl

theorem field_length (xs : List Val) : fieldOp .js (.list xs) "length" = .ok (.int xs.length) := rfl

theorem bind_vc (x y : Val) (env : Env) :
    bindPat .js (.tup ["value", "child"]) (.list [x, y]) env = .ok ((env.set "value" x).set "child" y) := rfl

theorem bind_node (x y z : Val) (env : Env) :
    bindPat .js (.tup ["v", "lo", "hi"]) (.list [x, y, z]) env =
      .ok (((env.set "v" x).set "lo" y).set "hi" z) := rfl

theorem bind_hole (b : String) (x y : Val) (env : Env) (hb : b ≠ "") :
    bindPat .js (.tup ["", b]) (.list [x, y]) env = .ok (env.set b y) := by
  simp [bindPat, List.zipIdx, hb]

theorem bind_whole (x y : Val) (env : Env) :
    bindPat .js (.whole Js.wholeName ["", "c"]) (.list [x, y]) env =
      .ok ((env.set "c" y).set Js.wholeName (.list [x, y])) := by
  simp [bindPat, List.zipIdx]

/-! ## Environment facts across JS block exits -/

theorem get_none_of_has_false {env : Env} {y : String} (h : env.has y = false) : env.get y = none := by
  cases hg : env.get y with
  | none => rfl
  | some w => rw [Env.has_of_get hg] at h; cases h

theorem exit_keep {outer env : Env} {y : String} {w : Val} (ho : outer.get y = some w) :
    (exitBlock .js outer env).get y = env.get y := by
  rw [Env.get_exit_js, if_pos (Env.has_of_get ho)]

theorem exit_frame {outer env : Env} {y : String} (h : env.get y = outer.get y) :
    (exitBlock .js outer env).get y = outer.get y := by
  rw [Env.get_exit_js]
  split
  · exact h
  · rename_i hh; exact (get_none_of_has_false (by simpa using hh)).symm

theorem ExF.cons_or {env env1 env' : Env} {p : Pat} {body : List S} {x : Val} {xs : List Val}
    {r : Res Flow} (hb : bindPat .js p x env = .ok env1)
    (h1 : ExB .js env1 body (.ok (.normal env')) ∨ ExB .js env1 body (.ok (.cont env')))
    (h2 : ExF .js (exitBlock .js env env') p body xs r) : ExF .js env p body (x :: xs) r := by
  rcases h1 with h1 | h1
  · exact ExF.cons_normal hb h1 h2
  · exact ExF.cons_cont hb h1 h2

/-! ## Comprehensions, `Math.min` and the merge loop -/

theorem costs_comp (env : Env) (brs : List (Bool × Cell)) :
    EvC .js env (at' "c" 0) (.tup ["", "c"]) none (brs.map encBr)
      (.ok (brs.map (fun b => Val.int b.2.cost))) := by
  induction brs with
  | nil => exact EvC.nil
  | cons b brs ih =>
      refine EvC.cons_none (bind_hole "c" _ _ env (by decide)) ?_ ih
      have := EvE.index (d := .js) (EvE.var (Env.get_set_self env "c" (encRaw b.2)))
        (EvE.lit (env := env.set "c" (encRaw b.2)) (.int 0))
      rwa [index_raw0] at this

theorem min_fold (ys : List Nat) (a : Nat) :
    (ys.map (fun c : Nat => Val.int (c : Int))).foldlM (fun m y => (binOp .js .lt y m).bind fun c =>
      match c with
      | .bool true => .ok y
      | .bool false => .ok m
      | _ => .exc .typeError) (Val.int (a : Int)) = .ok (.int ((ys.foldl Nat.min a : Nat) : Int)) := by
  induction ys generalizing a with
  | nil => rfl
  | cons y ys ih =>
      simp only [List.map_cons, List.foldl_cons]
      show (Res.bind ((binOp .js .lt (.int y) (.int a)).bind _) _) = _
      rw [lt_int]
      by_cases h : (y : Int) < a
      · have hm : Nat.min a y = y := by simp only [Nat.min_def]; split <;> omega
        simp only [Res.bind_ok, decide_eq_true h]
        rw [hm]; exact ih y
      · have hm : Nat.min a y = a := by simp only [Nat.min_def]; split <;> omega
        simp only [Res.bind_ok, decide_eq_false h]
        rw [hm]; exact ih a

theorem min_costs (b : Bool × Cell) (brs : List (Bool × Cell)) :
    minOp .js ((b :: brs).map (fun b => Val.int b.2.cost)) =
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
    EvC .js env (v Js.wholeName) (.whole Js.wholeName ["", "c"])
      (some (.bin .eq (at' "c" 0) (v "best"))) (brs.map encBr)
      (.ok ((brs.filter (fun p => p.2.cost == best)).map encBr)) := by
  induction brs with
  | nil => exact EvC.nil
  | cons b brs ih =>
      let env' := (env.set "c" (encRaw b.2)).set Js.wholeName (.list [.bool b.1, encRaw b.2])
      have hb' : env'.get "best" = some (.int best) := by
        simp only [env']; rw [Env.get_set_ne _ _ (by decide), Env.get_set_ne _ _ (by decide), hb]
      have hcget : env'.get "c" = some (encRaw b.2) := by
        simp only [env']; rw [Env.get_set_ne _ _ (by decide), Env.get_set_self]
      have hc : EvE .js env' (.bin .eq (at' "c" 0) (v "best"))
          (.ok (.bool ((b.2.cost : Int) == (best : Int)))) := by
        have h1 := EvE.index (d := .js) (EvE.var hcget) (EvE.lit (env := env') (.int 0))
        rw [index_raw0] at h1
        have := EvE.bin (op := .eq) h1 (EvE.var hb')
        rwa [eq_int] at this
      have hbind : bindPat .js (.whole Js.wholeName ["", "c"]) (encBr b) env = .ok env' := bind_whole _ _ env
      by_cases hcost : b.2.cost = best
      · have he : EvE .js env' (v Js.wholeName) (.ok (encBr b)) := EvE.var (Env.get_set_self _ _ _)
        have := EvC.cons_keep hbind hc (by simp [truthy, hcost]) he ih
        simpa [List.filter_cons, hcost] using this
      · have := EvC.cons_drop (elt := v Js.wholeName) hbind hc (by simp [truthy]; omega) ih
        simpa [List.filter_cons, hcost] using this

theorem merge_count (ws : List (Bool × Cell)) (acc : Cell) :
    (ws.foldl (fun a p => mergeCell a p.2) acc).count = acc.count + (ws.map (·.2.count)).sum := by
  induction ws generalizing acc with
  | nil => simp
  | cons w ws ih =>
      simp only [List.foldl_cons]; rw [ih]; simp only [mergeCell, List.map_cons, List.sum_cons]; omega

/-- Masks below `2^31` are preserved by the merge. -/
theorem merge_masks (ws : List (Bool × Cell)) (acc : Cell) (h0 : acc.mand < 2 ^ 31 ∧ acc.poss < 2 ^ 31)
    (hw : ∀ p ∈ ws, p.2.mand < 2 ^ 31 ∧ p.2.poss < 2 ^ 31) :
    (ws.foldl (fun a p => mergeCell a p.2) acc).mand < 2 ^ 31 ∧
      (ws.foldl (fun a p => mergeCell a p.2) acc).poss < 2 ^ 31 := by
  induction ws generalizing acc with
  | nil => exact h0
  | cons w ws ih =>
      simp only [List.foldl_cons]
      refine ih _ ⟨Nat.lt_of_le_of_lt Nat.and_le_left h0.1,
        Nat.or_lt_two_pow h0.2 (hw w List.mem_cons_self).2⟩ (fun p hp => hw p (List.mem_cons_of_mem _ hp))

/-- JavaScript's `cell[k] op= other[k]` loop on encoded cells, with exact arithmetic. -/
theorem merge_loop (ws : List (Bool × Cell)) :
    ∀ (env : Env) (acc : Cell), env.get "cell" = some (encRaw acc) →
      acc.mand < 2 ^ 31 → acc.poss < 2 ^ 31 → (∀ p ∈ ws, p.2.mand < 2 ^ 31 ∧ p.2.poss < 2 ^ 31) →
      (acc.count + (ws.map (·.2.count)).sum : Int) ≤ MAX_SAFE →
      ∃ env', ExF .js env (.tup ["", "other"]) mergeBody (ws.map encBr) (.ok (.normal env')) ∧
        env'.get "cell" = some (encRaw (ws.foldl (fun a p => mergeCell a p.2) acc)) ∧
        ∀ y, y ≠ "cell" → y ≠ "other" → env'.get y = env.get y := by
  induction ws with
  | nil => intro env acc h _ _ _ _; exact ⟨env, ExF.nil, h, fun _ _ _ => rfl⟩
  | cons w ws ih =>
      intro env acc hc hm hp hws hsum
      have hw := hws w List.mem_cons_self
      let env1 := env.set "other" (encRaw w.2)
      have hc1 : env1.get "cell" = some (encRaw acc) := by
        simp only [env1]; rw [Env.get_set_ne _ _ (by decide), hc]
      have ho1 : env1.get "other" = some (encRaw w.2) := Env.get_set_self _ _ _
      have hsum' : ((acc.count : Int) + w.2.count) ≤ MAX_SAFE := by
        simp only [List.map_cons, List.sum_cons] at hsum; omega
      let x1 : Val := .list [.int acc.cost, .int ((acc.count : Int) + w.2.count), .int acc.mand, .int acc.poss]
      let env2 := env1.set "cell" x1
      have s1 : ExS .js env1 (.augIndex "cell" (i 1) .add (at' "other" 1)) (.ok (.normal env2)) := by
        refine ExS.augIndex hc1 (EvE.lit _) (index_raw1 acc) ?_
          (add_int _ _ (by unfold MAX_SAFE; omega) hsum') rfl
        have := EvE.index (d := .js) (EvE.var ho1) (EvE.lit (env := env1) (.int 1))
        rwa [index_raw1] at this
      have hc2 : env2.get "cell" = some x1 := Env.get_set_self _ _ _
      have ho2 : env2.get "other" = some (encRaw w.2) := by
        simp only [env2]; rw [Env.get_set_ne _ _ (by decide), ho1]
      let x2 : Val := .list [.int acc.cost, .int ((acc.count : Int) + w.2.count),
        .int ((acc.mand &&& w.2.mand : Nat) : Int), .int acc.poss]
      let env3 := env2.set "cell" x2
      have s2 : ExS .js env2 (.augIndex "cell" (i 2) .band (at' "other" 2)) (.ok (.normal env3)) := by
        refine ExS.augIndex hc2 (EvE.lit _) rfl ?_ (band_nat _ _ hm hw.1) rfl
        have := EvE.index (d := .js) (EvE.var ho2) (EvE.lit (env := env2) (.int 2))
        rwa [index_raw2] at this
      have hc3 : env3.get "cell" = some x2 := Env.get_set_self _ _ _
      have ho3 : env3.get "other" = some (encRaw w.2) := by
        simp only [env3]; rw [Env.get_set_ne _ _ (by decide), ho2]
      let x3 : Val := .list [.int acc.cost, .int ((acc.count : Int) + w.2.count),
        .int ((acc.mand &&& w.2.mand : Nat) : Int), .int ((acc.poss ||| w.2.poss : Nat) : Int)]
      let env4 := env3.set "cell" x3
      have s3 : ExS .js env3 (.augIndex "cell" (i 3) .bor (at' "other" 3)) (.ok (.normal env4)) := by
        refine ExS.augIndex hc3 (EvE.lit _) rfl ?_ (bor_nat _ _ hp hw.2) rfl
        have := EvE.index (d := .js) (EvE.var ho3) (EvE.lit (env := env3) (.int 3))
        rwa [index_raw3] at this
      have hb : ExB .js env1 mergeBody (.ok (.normal env4)) :=
        ExB.cons_normal s1 (ExB.cons_normal s2 (ExB.cons_normal s3 ExB.nil))
      let env5 := exitBlock .js env env4
      have hc5 : env5.get "cell" = some (encRaw (mergeCell acc w.2)) := by
        simp only [env5]; rw [exit_keep hc]
        simp only [env4, Env.get_set_self, x3, encRaw, mergeCell, Int.natCast_add]
      have hfr5 : ∀ y, y ≠ "cell" → y ≠ "other" → env5.get y = env.get y := by
        intro y hy ho
        refine exit_frame ?_
        simp only [env4, env3, env2, env1]
        rw [Env.get_set_ne _ _ hy, Env.get_set_ne _ _ hy, Env.get_set_ne _ _ hy, Env.get_set_ne _ _ ho]
      have hmm := merge_masks [w] acc ⟨hm, hp⟩ (fun p hp' => by simp at hp'; subst hp'; exact hw)
      simp only [List.foldl_cons, List.foldl_nil] at hmm
      obtain ⟨env', hf, hcell, hframe⟩ := ih env5 (mergeCell acc w.2) hc5 hmm.1 hmm.2
        (fun p hp' => hws p (List.mem_cons_of_mem _ hp'))
        (by simp only [List.map_cons, List.sum_cons, mergeCell] at hsum ⊢; push_cast at hsum ⊢; omega)
      refine ⟨env', ExF.cons_normal (bind_hole "other" _ _ env (by decide)) hb hf, ?_, ?_⟩
      · simpa [List.foldl_cons] using hcell
      · intro y h1 h2
        rw [hframe y h1 h2, hfr5 y h1 h2]

theorem winners_sub (brs : List (Bool × Cell)) (best : Nat) (w : Bool × Cell) (others : List (Bool × Cell))
    (h : brs.filter (fun p => p.2.cost == best) = w :: others) : ∀ p ∈ w :: others, p ∈ brs := by
  intro p hp; rw [← h] at hp; exact (List.mem_filter.1 hp).1

/-- The statements after the branch loop compute `winnersCell` of the collected branches. -/
theorem tail_spec (env : Env) (brs : List (Bool × Cell)) (cellsL choicesL : List Val)
    (hbr : env.get "branches" = some (.list (brs.map encBr)))
    (hcl : env.get "cells" = some (.list cellsL)) (hch : env.get "choices" = some (.list choicesL))
    (hmask : ∀ p ∈ brs, p.2.mand < 2 ^ 31 ∧ p.2.poss < 2 ^ 31)
    (hcount : ∀ c, (winnersCell brs).1 = some c → (c.count : Int) ≤ MAX_SAFE) :
    ∃ env', (ExB .js env tailBody (.ok (.normal env')) ∨ ExB .js env tailBody (.ok (.cont env'))) ∧
      env'.get "cells" = some (.list (cellsL ++ [encCell (winnersCell brs).1])) ∧
      env'.get "choices" = some (.list (choicesL ++ [encChoice (winnersCell brs).2])) ∧
      ∀ y, y ≠ "other" → y ≠ "cell" → y ≠ "best" → y ≠ "winners" → y ≠ "cells" →
        y ≠ "choices" → env'.get y = env.get y := by
  have hlen : ∀ (xs : List Val), EvE .js env (.not (.field (v "branches") "length"))
      (.ok (.bool !(truthy .js (.int (brs.map encBr).length)))) := fun _ => by
    have := EvE.field (d := .js) (k := "length") (EvE.var hbr)
    rw [field_length] at this
    exact EvE.not this
  cases brs with
  | nil =>
      let env1 := env.set "cells" (.list (cellsL ++ [.none]))
      let env2 := env1.set "choices" (.list (choicesL ++ [.none]))
      have hch1 : env1.get "choices" = some (.list choicesL) := by
        simp only [env1]; rw [Env.get_set_ne _ _ (by decide), hch]
      have hb : ExB .js env [.append "cells" (.lit .none), .append "choices" (.lit .none), .cont]
          (.ok (.cont env2)) :=
        ExB.cons_normal (ExS.append hcl (EvE.lit _))
          (ExB.cons_normal (ExS.append hch1 (EvE.lit _)) (ExB.cons_cont ExS.cont))
      have hs := ExS.if_cont (hlen []) (by rfl) hb
      refine ⟨_, Or.inr (ExB.cons_cont hs), ?_, ?_, ?_⟩
      · rw [exit_keep hcl]; simp only [env2]; rw [Env.get_set_ne _ _ (by decide)]
        simp [env1, winnersCell, encCell]
      · rw [exit_keep hch]; simp [env2, winnersCell, encChoice]
      · intro y _ _ _ _ h6 h7
        refine exit_frame ?_
        simp only [env2, env1]; rw [Env.get_set_ne _ _ h7, Env.get_set_ne _ _ h6]
  | cons b rest =>
      obtain ⟨w, others, hws⟩ := PyBellman.winners_nonempty b rest
      have hwc : winnersCell (b :: rest) =
          (some (others.foldl (fun acc p => mergeCell acc p.2) w.2), some w.1) := by
        unfold winnersCell; simp only; rw [hws]
      have hcnt := hcount _ (by rw [hwc])
      rw [hwc]
      have hmin0 := min_costs b rest
      generalize (b :: rest).foldl (fun m p => Nat.min m p.2.cost) b.2.cost = best at hws hmin0
      have hsub := winners_sub _ _ _ _ hws
      have s1 : ExS .js env (.ifThen (.not (.field (v "branches") "length"))
          [.append "cells" (.lit .none), .append "choices" (.lit .none), .cont]) (.ok (.normal env)) :=
        ExS.if_false (hlen []) (by simp [truthy]; omega)
      have hmin : EvE .js env (.min (.comp (at' "c" 0) (.tup ["", "c"]) (v "branches") none))
          (.ok (.int best)) := by
        have := EvE.min (EvE.comp (EvE.var hbr) rfl (costs_comp env (b :: rest))) rfl
        rwa [hmin0] at this
      let env1 := env.set "best" (.int best)
      have s2 := ExS.assign (p := .v "best") hmin (rfl : bindPat .js _ _ env = .ok env1)
      have hbr1 : env1.get "branches" = some (.list ((b :: rest).map encBr)) := by
        simp only [env1]; rw [Env.get_set_ne _ _ (by decide), hbr]
      have hcomp := EvE.comp (EvE.var hbr1) rfl
        (winners_comp env1 best (Env.get_set_self _ _ _) (b :: rest))
      rw [hws] at hcomp
      let env2 := env1.set "winners" (.list ((w :: others).map encBr))
      have s3 := ExS.assign (p := .v "winners") hcomp (rfl : bindPat .js _ _ env1 = .ok env2)
      have hw2 : env2.get "winners" = some (.list ((w :: others).map encBr)) := Env.get_set_self _ _ _
      have hw0 : ∀ env' : Env, env'.get "winners" = some (.list ((w :: others).map encBr)) →
          EvE .js env' (at' "winners" 0) (.ok (encBr w)) := by
        intro env' h
        have := EvE.index (d := .js) (EvE.var h) (EvE.lit (env := env') (.int 0))
        rw [List.map_cons, index_head0] at this; exact this
      have hcell : EvE .js env2 (.copy (.index (at' "winners" 0) (i 1))) (.ok (encRaw w.2)) := by
        have h1 := EvE.index (d := .js) (hw0 env2 hw2) (EvE.lit (env := env2) (.int 1))
        rw [index_br1] at h1
        exact EvE.copy h1 rfl
      let env3 := env2.set "cell" (encRaw w.2)
      have s4 := ExS.assign (p := .v "cell") hcell (rfl : bindPat .js _ _ env2 = .ok env3)
      have hc3 : env3.get "cell" = some (encRaw w.2) := Env.get_set_self _ _ _
      have hmw := hmask w (hsub w List.mem_cons_self)
      rw [merge_count] at hcnt
      obtain ⟨env4, hf, hc4, hfr4⟩ := merge_loop others env3 w.2 hc3 hmw.1 hmw.2
        (fun p hp => hmask p (hsub p (List.mem_cons_of_mem _ hp))) hcnt
      have hw3 : env3.get "winners" = some (.list ((w :: others).map encBr)) := by
        simp only [env3]; rw [Env.get_set_ne _ _ (by decide), hw2]
      have hsl : EvE .js env3 (.sliceFrom (v "winners") (i 1)) (.ok (.list (others.map encBr))) :=
        EvE.sliceFrom (d := .js) (EvE.var hw3) (EvE.lit (env := env3) (.int 1))
      have s5 := ExS.forIn hsl rfl hf
      have hcl4 : env4.get "cells" = some (.list cellsL) := by
        rw [hfr4 _ (by decide) (by decide)]
        simp only [env3, env2, env1]
        rw [Env.get_set_ne _ _ (by decide), Env.get_set_ne _ _ (by decide),
          Env.get_set_ne _ _ (by decide), hcl]
      let env5 := env4.set "cells" (.list (cellsL ++ [encRaw (others.foldl (fun a p => mergeCell a p.2) w.2)]))
      have s6 := ExS.append (d := .js) (e := v "cell") hcl4 (EvE.var hc4)
      have hch5 : env5.get "choices" = some (.list choicesL) := by
        simp only [env5]
        rw [Env.get_set_ne _ _ (by decide), hfr4 _ (by decide) (by decide)]
        simp only [env3, env2, env1]
        rw [Env.get_set_ne _ _ (by decide), Env.get_set_ne _ _ (by decide),
          Env.get_set_ne _ _ (by decide), hch]
      have hw5 : env5.get "winners" = some (.list ((w :: others).map encBr)) := by
        simp only [env5]
        rw [Env.get_set_ne _ _ (by decide), hfr4 _ (by decide) (by decide), hw3]
      have hch0 : EvE .js env5 (.index (at' "winners" 0) (i 0)) (.ok (.bool w.1)) := by
        have h1 := EvE.index (d := .js) (hw0 env5 hw5) (EvE.lit (env := env5) (.int 0))
        rwa [index_br0] at h1
      let env6 := env5.set "choices" (.list (choicesL ++ [.bool w.1]))
      have s7 := ExS.append (d := .js) (e := .index (at' "winners" 0) (i 0)) hch5 hch0
      refine ⟨env6, Or.inl (ExB.cons_normal s1 (ExB.cons_normal s2 (ExB.cons_normal s3
        (ExB.cons_normal s4 (ExB.cons_normal s5 (ExB.cons_normal s6 (ExB.cons_normal s7 ExB.nil))))))),
        ?_, ?_, ?_⟩
      · simp only [env6, env5]; rw [Env.get_set_ne _ _ (by decide)]; simp [encCell]
      · simp [env6, encChoice]
      · intro y h2 h3 h4 h5 h6 h7
        simp only [env6, env5]
        rw [Env.get_set_ne _ _ h7, Env.get_set_ne _ _ h6, hfr4 y h3 h2]
        simp only [env3, env2, env1]
        rw [Env.get_set_ne _ _ h3, Env.get_set_ne _ _ h5, Env.get_set_ne _ _ h4]

end PCSRuntimeRefinement.JsBellman
