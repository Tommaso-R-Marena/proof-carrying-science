import PCSRuntimeRefinement.PyBellman

/-!
# The branch loop and the node loop of the extracted Python `bellman`
-/

namespace PCSRuntimeRefinement.PyBellman

open PCSRuntimeRefinement PCSDD

/-- The variables the branch-loop body reads, with their meaning for variable `k`. -/
structure InnerCtx (P : Prices) (k : Nat) (cells : Array (Option Cell)) (env : Env) : Prop where
  name : ∃ nm, env.get "name" = some (.str nm) ∧
    (∃ bl, env.get "baseline" = some bl ∧ indexOp .py bl (.str nm) = .ok (.bool (P.base k))) ∧
    (∃ cs, env.get "costs" = some cs ∧ indexOp .py cs (.str nm) = .ok (.int (P.cost k))) ∧
    (∃ lk, env.get "locked" = some lk ∧ memOp .py (.str nm) lk = .ok (P.lock k))
  bit : env.get "bit" = some (.int ((2 ^ k : Nat) : Int))
  cells : env.get "cells" = some (.list (cells.toList.map encCell))

theorem InnerCtx.frame {P : Prices} {k : Nat} {cells : Array (Option Cell)} {env env' : Env}
    (h : InnerCtx P k cells env)
    (hf : ∀ y, y = "name" ∨ y = "baseline" ∨ y = "costs" ∨ y = "locked" ∨ y = "bit" ∨ y = "cells" →
      env'.get y = env.get y) : InnerCtx P k cells env' := by
  obtain ⟨⟨nm, hnm, ⟨bl, hbl, hb⟩, ⟨cs, hcs, hc⟩, ⟨lk, hlk, hl⟩⟩, hbit, hcells⟩ := h
  refine ⟨⟨nm, ?_, ⟨bl, ?_, hb⟩, ⟨cs, ?_, hc⟩, ⟨lk, ?_, hl⟩⟩, ?_, ?_⟩
  · rw [hf _ (by simp)]; exact hnm
  · rw [hf _ (by simp)]; exact hbl
  · rw [hf _ (by simp)]; exact hcs
  · rw [hf _ (by simp)]; exact hlk
  · rw [hf _ (by simp)]; exact hbit
  · rw [hf _ (by simp)]; exact hcells

theorem EvE.res_eq {d : Dialect} {env : Env} {e : E} {r r' : Res Val} (h : EvE d env e r) (hr : r = r') :
    EvE d env e r' := hr ▸ h

theorem truthy_bool (b : Bool) : truthy .py (.bool b) = b := rfl

theorem getD_encCell (cells : Array (Option Cell)) (child : Nat) (h : child < cells.size) :
    indexOp .py (.list (cells.toList.map encCell)) (.int child) = .ok (encCell (cells.getD child none)) := by
  rw [index_list_nat encCell cells.toList child (by simpa using h)]
  simp [Array.getD, h]

/-- The value appended to `branches` for a present child cell. -/
theorem branch_value (P : Prices) (k : Nat) (x : Bool) (c : Cell) (env : Env) (nm : String)
    (cs : Val) (hnm : env.get "name" = some (.str nm)) (hcs : env.get "costs" = some cs)
    (hc : indexOp .py cs (.str nm) = .ok (.int (P.cost k)))
    (hbit : env.get "bit" = some (.int ((2 ^ k : Nat) : Int)))
    (hval : env.get "value" = some (.bool x)) (hcell : env.get "cell" = some (encRaw c))
    (hflip : env.get "flip" = some (.bool (x != P.base k))) :
    EvE .py env (.tuple [v "value", .list [
      .bin .add (at' "cell" 0) (.cond (v "flip") (.index (v "costs") (v "name")) (i 0)),
      at' "cell" 1,
      .bin .bor (at' "cell" 2) (.cond (v "flip") (v "bit") (i 0)),
      .bin .bor (at' "cell" 3) (.cond (v "flip") (v "bit") (i 0))]])
      (.ok (encBr (x, shiftCell (P.flipC k x) (P.flipM k x) c))) := by
  have c0 : EvE .py env (at' "cell" 0) (.ok (.int c.cost)) := by
    have := EvE.index (d := .py) (EvE.var hcell) (EvE.lit (env := env) (.int 0)); rwa [index_raw0] at this
  have c1 : EvE .py env (at' "cell" 1) (.ok (.int c.count)) := by
    have := EvE.index (d := .py) (EvE.var hcell) (EvE.lit (env := env) (.int 1)); rwa [index_raw1] at this
  have c2 : EvE .py env (at' "cell" 2) (.ok (.int c.mand)) := by
    have := EvE.index (d := .py) (EvE.var hcell) (EvE.lit (env := env) (.int 2)); rwa [index_raw2] at this
  have c3 : EvE .py env (at' "cell" 3) (.ok (.int c.poss)) := by
    have := EvE.index (d := .py) (EvE.var hcell) (EvE.lit (env := env) (.int 3)); rwa [index_raw3] at this
  by_cases hx : x = P.base k
  · subst hx
    have hf : env.get "flip" = some (.bool false) := by simpa using hflip
    have k0 : ∀ t : E, EvE .py env (.cond (v "flip") t (i 0)) (.ok (.int ((0 : Nat) : Int))) :=
      fun t => EvE.cond (EvE.var hf) (EvE.lit _)
    have e0 := EvE.bin (op := .add) c0 (k0 (.index (v "costs") (v "name")))
    have e2 := EvE.bin (op := .bor) c2 (k0 (v "bit"))
    have e3 := EvE.bin (op := .bor) c3 (k0 (v "bit"))
    rw [add_int] at e0; rw [bor_nat] at e2 e3
    have := EvE.tuple (EvL.cons (EvE.var hval) (EvL.cons (EvE.list (EvL.cons e0 (EvL.cons c1
      (EvL.cons e2 (EvL.cons e3 EvL.nil))))) EvL.nil))
    refine EvE.res_eq this ?_
    simp [encBr, encRaw, shiftCell, Prices.flipC, Prices.flipM]
  · have hf : env.get "flip" = some (.bool true) := by
      cases x <;> cases hb' : P.base k <;> simp_all
    have kc := EvE.cond (t := .index (v "costs") (v "name")) (f := i 0) (EvE.var hf)
      (EvE.index (d := .py) (EvE.var hcs) (EvE.var hnm))
    rw [hc] at kc
    have kb : EvE .py env (.cond (v "flip") (v "bit") (i 0)) (.ok (.int ((2 ^ k : Nat) : Int))) :=
      EvE.cond (EvE.var hf) (EvE.var hbit)
    have e0 := EvE.bin (op := .add) c0 kc
    have e2 := EvE.bin (op := .bor) c2 kb
    have e3 := EvE.bin (op := .bor) c3 kb
    rw [add_int] at e0; rw [bor_nat] at e2 e3
    have := EvE.tuple (EvL.cons (EvE.var hval) (EvL.cons (EvE.list (EvL.cons e0 (EvL.cons c1
      (EvL.cons e2 (EvL.cons e3 EvL.nil))))) EvL.nil))
    refine EvE.res_eq this ?_
    simp [encBr, encRaw, shiftCell, Prices.flipC, Prices.flipM, hx]

/-- **One iteration of the branch loop** is `inspect`: it appends exactly the inspected branch. -/
theorem inner_body (P : Prices) (k : Nat) (cells : Array (Option Cell)) (env : Env) (x : Bool)
    (child : Nat) (brs : List (Bool × Cell)) (hctx : InnerCtx P k cells env)
    (hval : env.get "value" = some (.bool x)) (hch : env.get "child" = some (.int child))
    (hlt : child < cells.size) (hbr : env.get "branches" = some (.list (brs.map encBr))) :
    ∃ env', (ExB .py env innerBody (.ok (.normal env')) ∨ ExB .py env innerBody (.ok (.cont env'))) ∧
      env'.get "branches" = some (.list ((brs ++ (inspect P cells k x child).toList).map encBr)) ∧
      ∀ y, y ≠ "cell" → y ≠ "flip" → y ≠ "branches" → env'.get y = env.get y := by
  obtain ⟨⟨nm, hnm, ⟨bl, hbl, hb⟩, ⟨cs, hcs, hc⟩, ⟨lk, hlk, hl⟩⟩, hbit, hcells⟩ := hctx
  have hne : ∀ env1 : Env, env1.get "value" = some (.bool x) → env1.get "baseline" = some bl →
      env1.get "name" = some (.str nm) →
      EvE .py env1 (.bin .ne (v "value") (.index (v "baseline") (v "name"))) (.ok (.bool (x != P.base k))) := by
    intro env1 h1 h2 h3
    have hi := EvE.index (d := .py) (EvE.var h2) (EvE.var h3)
    rw [hb] at hi
    have := EvE.bin (op := .ne) (EvE.var h1) hi
    rw [ne_bool] at this; exact this
  have hmem : EvE .py env (.mem (v "name") (v "locked")) (.ok (.bool (P.lock k))) :=
    EvE.mem (EvE.var hnm) (EvE.var hlk) hl
  by_cases hskip : P.lock k = true ∧ x ≠ P.base k
  · have hx : (x != P.base k) = true := by simp [hskip.2]
    have hand : EvE .py env (.and (.mem (v "name") (v "locked"))
        (.bin .ne (v "value") (.index (v "baseline") (v "name")))) (.ok (.bool true)) := by
      have := hne env hval hbl hnm; rw [hx] at this
      exact EvE.and_t hmem (by simp [truthy_bool, hskip.1]) this
    have s1 := ExS.if_cont (body := [.cont]) hand rfl (ExB.cons_cont ExS.cont)
    refine ⟨env, Or.inr (ExB.cons_cont s1), ?_, fun _ _ _ _ => rfl⟩
    simp [inspect, hskip, hbr]
  · have hand : EvE .py env (.and (.mem (v "name") (v "locked"))
        (.bin .ne (v "value") (.index (v "baseline") (v "name")))) (.ok (.bool false)) := by
      cases hlock : P.lock k
      · rw [hlock] at hmem; exact EvE.and_f hmem rfl
      · have hxb : x = P.base k := Classical.byContradiction fun h => hskip ⟨hlock, h⟩
        have := hne env hval hbl hnm
        rw [hxb] at this; simp only [bne_self_eq_false] at this
        rw [hlock] at hmem; exact EvE.and_t hmem rfl this
    have s1 := ExS.if_false (body := [.cont]) hand rfl
    have hinsp : inspect P cells k x child =
        (cells.getD child none).map (fun c => (x, shiftCell (P.flipC k x) (P.flipM k x) c)) := by
      unfold inspect; rw [if_neg hskip]; cases cells.getD child none <;> rfl
    have hcellv := EvE.index (d := .py) (EvE.var hcells) (EvE.var hch)
    rw [getD_encCell _ _ hlt] at hcellv
    rw [hinsp]
    cases hcg : cells.getD child none with
    | none =>
        rw [hcg] at hcellv
        let env1 := env.set "cell" .none
        have s2 := ExS.assign (p := .v "cell") hcellv (rfl : bindPat .py _ _ env = .ok env1)
        have s3 := ExS.if_cont (body := [.cont]) (EvE.isNone (d := .py) (EvE.var (Env.get_set_self env "cell" .none)))
          rfl (ExB.cons_cont ExS.cont)
        refine ⟨env1, Or.inr (ExB.cons_normal s1 (ExB.cons_normal s2 (ExB.cons_cont s3))), ?_, ?_⟩
        · simp only [env1]; rw [Env.get_set_ne _ _ (by decide)]; simpa using hbr
        · intro y h1 _ _; exact Env.get_set_ne _ _ h1
    | some c =>
        rw [hcg] at hcellv
        let env1 := env.set "cell" (encRaw c)
        have g1 : ∀ y, y ≠ "cell" → env1.get y = env.get y := fun y h => Env.get_set_ne _ _ h
        have s2 := ExS.assign (p := .v "cell") hcellv (rfl : bindPat .py _ _ env = .ok env1)
        have s3 := ExS.if_false (body := [.cont]) (EvE.isNone (d := .py) (EvE.var (Env.get_set_self env "cell" (encRaw c))))
          rfl
        let env2 := env1.set "flip" (.bool (x != P.base k))
        have g2 : ∀ y, y ≠ "cell" → y ≠ "flip" → env2.get y = env.get y := fun y h h' =>
          (Env.get_set_ne _ _ h').trans (g1 y h)
        have s4 := ExS.assign (p := .v "flip")
          (hne env1 ((g1 _ (by decide)).trans hval) ((g1 _ (by decide)).trans hbl) ((g1 _ (by decide)).trans hnm))
          (rfl : bindPat .py _ _ env1 = .ok env2)
        have hv := branch_value P k x c env2 nm cs ((g2 _ (by decide) (by decide)).trans hnm)
          ((g2 _ (by decide) (by decide)).trans hcs) hc ((g2 _ (by decide) (by decide)).trans hbit)
          ((g2 _ (by decide) (by decide)).trans hval)
          ((Env.get_set_ne _ _ (by decide)).trans (Env.get_set_self env "cell" (encRaw c)))
          (Env.get_set_self _ _ _)
        have s5 := ExS.append (d := .py) ((g2 _ (by decide) (by decide)).trans hbr) hv
        refine ⟨_, Or.inl (ExB.cons_normal s1 (ExB.cons_normal s2 (ExB.cons_normal s3
          (ExB.cons_normal s4 (ExB.cons_normal s5 ExB.nil))))), ?_, ?_⟩
        · simp
        · intro y h1 h2 h3; rw [Env.get_set_ne _ _ h3]; exact g2 y h1 h2

/-! ## The node loop -/

/-- The meaning of the four input arguments for prices `P` over `n` variables: `names` is a
list of strings; for every variable `k < n`, `baseline[names[k]]` is the Boolean `P.base k`,
`costs[names[k]]` the integer `P.cost k`, and `names[k] in locked` is `P.lock k`. -/
def Args (P : Prices) (n : Nat) (names baseline costs locked : Val) : Prop :=
  ∃ nms : List String, names = .list (nms.map .str) ∧ n ≤ nms.length ∧
    ∀ k, k < n → indexOp .py baseline (.str (nms.getD k "")) = .ok (.bool (P.base k)) ∧
      indexOp .py costs (.str (nms.getD k "")) = .ok (.int (P.cost k)) ∧
      memOp .py (.str (nms.getD k "")) locked = .ok (P.lock k)

/-- The environment holds arguments satisfying `Args`. -/
def GlobalCtx (P : Prices) (n : Nat) (env : Env) : Prop :=
  ∃ names bl cs lk, env.get "names" = some names ∧ env.get "baseline" = some bl ∧
    env.get "costs" = some cs ∧ env.get "locked" = some lk ∧ Args P n names bl cs lk

theorem GlobalCtx.frame {P : Prices} {n : Nat} {env env' : Env} (h : GlobalCtx P n env)
    (hf : ∀ y, y = "names" ∨ y = "baseline" ∨ y = "costs" ∨ y = "locked" → env'.get y = env.get y) :
    GlobalCtx P n env' := by
  obtain ⟨a, b, c, d, h1, h2, h3, h4, h5⟩ := h
  exact ⟨a, b, c, d, (hf _ (by simp)).trans h1, (hf _ (by simp)).trans h2, (hf _ (by simp)).trans h3,
    (hf _ (by simp)).trans h4, h5⟩

theorem ExF.cons_or {env env1 env' : Env} {p : Pat} {body : List S} {x : Val} {xs : List Val}
    {r : Res Flow} (hb : bindPat .py p x env = .ok env1)
    (h1 : ExB .py env1 body (.ok (.normal env')) ∨ ExB .py env1 body (.ok (.cont env')))
    (h2 : ExF .py env' p body xs r) : ExF .py env p body (x :: xs) r := by
  rcases h1 with h1 | h1
  · exact ExF.cons_normal hb h1 h2
  · exact ExF.cons_cont hb h1 h2

theorem index_names (nms : List String) (k : Nat) (hk : k < nms.length) :
    indexOp .py (.list (nms.map .str)) (.int k) = .ok (.str (nms.getD k "")) := by
  rw [index_list_nat Val.str nms k hk]
  simp [List.getD_eq_getElem?_getD, hk]

theorem filterMap_two {α : Type} (a b : Option α) : ([] ++ a.toList ++ b.toList) = [a, b].filterMap id := by
  cases a <;> cases b <;> rfl

/-- **One iteration of the node loop** is `passStep`. -/
theorem outer_body (P : Prices) (n : Nat) (st : PassSt) (nd : Node) (env : Env)
    (hg : GlobalCtx P n env)
    (hcl : env.get "cells" = some (.list (st.cells.toList.map encCell)))
    (hch : env.get "choices" = some (.list (st.choices.toList.map encChoice)))
    (hv : env.get "var" = some (.int nd.var)) (hl : env.get "low" = some (.int nd.low))
    (hh : env.get "high" = some (.int nd.high))
    (hvar : nd.var < n) (hlo : nd.low < st.cells.size) (hhi : nd.high < st.cells.size) :
    ∃ env', (ExB .py env outerBody (.ok (.normal env')) ∨ ExB .py env outerBody (.ok (.cont env'))) ∧
      env'.get "cells" = some (.list ((passStep P st nd).cells.toList.map encCell)) ∧
      env'.get "choices" = some (.list ((passStep P st nd).choices.toList.map encChoice)) ∧
      ∀ y, y = "names" ∨ y = "baseline" ∨ y = "costs" ∨ y = "locked" → env'.get y = env.get y := by
  obtain ⟨names, bl, cs, lk, hn, hb, hc, hlk, nms, rfl, hlen, hk⟩ := hg
  obtain ⟨hbk, hck, hlkk⟩ := hk nd.var hvar
  generalize hnm : nms.getD nd.var "" = nm at hbk hck hlkk
  have e1 : EvE .py env (.tuple [.index (v "names") (v "var"), .bin .shl (i 1) (v "var")])
      (.ok (.tuple [.str nm, .int ((2 ^ nd.var : Nat) : Int)])) := by
    have h1 := EvE.index (d := .py) (EvE.var hn) (EvE.var hv)
    rw [index_names nms _ (by omega), hnm] at h1
    have h2 := EvE.bin (op := .shl) (EvE.lit (d := .py) (env := env) (.int 1)) (EvE.var hv)
    rw [shl_one] at h2
    exact EvE.tuple (EvL.cons h1 (EvL.cons h2 EvL.nil))
  let env1 := (env.set "name" (.str nm)).set "bit" (.int ((2 ^ nd.var : Nat) : Int))
  have s1 := ExS.assign (p := .tup ["name", "bit"]) e1 (bind_tup2 _ _ _ _ env)
  let env2 := env1.set "branches" (.list [])
  have s2 := ExS.assign (p := .v "branches") (EvE.list (d := .py) (env := env1) EvL.nil)
    (rfl : bindPat .py _ _ env1 = .ok env2)
  have g2 : ∀ y, y ≠ "name" → y ≠ "bit" → y ≠ "branches" → env2.get y = env.get y := by
    intro y h1 h2 h3
    simp only [env2, env1]; rw [Env.get_set_ne _ _ h3, Env.get_set_ne _ _ h2, Env.get_set_ne _ _ h1]
  have ctx2 : InnerCtx P nd.var st.cells env2 := by
    refine ⟨⟨nm, ?_, ⟨bl, (g2 _ (by decide) (by decide) (by decide)).trans hb, hbk⟩,
      ⟨cs, (g2 _ (by decide) (by decide) (by decide)).trans hc, hck⟩,
      ⟨lk, (g2 _ (by decide) (by decide) (by decide)).trans hlk, hlkk⟩⟩, ?_,
      (g2 _ (by decide) (by decide) (by decide)).trans hcl⟩
    · simp only [env2, env1]
      rw [Env.get_set_ne _ _ (by decide), Env.get_set_ne _ _ (by decide), Env.get_set_self]
    · simp only [env2, env1]; rw [Env.get_set_ne _ _ (by decide), Env.get_set_self]
  have hbp : EvE .py env2 branchPairs (.ok (.tuple [.tuple [.bool false, .int nd.low],
      .tuple [.bool true, .int nd.high]])) := by
    have hl2 := (g2 _ (by decide) (by decide) (by decide)).trans hl
    have hh2 := (g2 _ (by decide) (by decide) (by decide)).trans hh
    exact EvE.tuple (EvL.cons (EvE.tuple (EvL.cons (EvE.lit _) (EvL.cons (EvE.var hl2) EvL.nil)))
      (EvL.cons (EvE.tuple (EvL.cons (EvE.lit _) (EvL.cons (EvE.var hh2) EvL.nil))) EvL.nil))
  let env3 := (env2.set "value" (.bool false)).set "child" (.int nd.low)
  have ctx3 : InnerCtx P nd.var st.cells env3 := ctx2.frame (fun y hy => by
    simp only [env3]
    rcases hy with h | h | h | h | h | h <;> subst h <;>
      rw [Env.get_set_ne _ _ (by decide), Env.get_set_ne _ _ (by decide)])
  have hbr3 : env3.get "branches" = some (.list (([] : List (Bool × Cell)).map encBr)) := by
    simp only [env3]; rw [Env.get_set_ne _ _ (by decide), Env.get_set_ne _ _ (by decide)]
    simp [env2]
  obtain ⟨env4, hor4, hbr4, hfr4⟩ := inner_body P nd.var st.cells env3 false nd.low [] ctx3
    (by simp only [env3]; rw [Env.get_set_ne _ _ (by decide), Env.get_set_self])
    (Env.get_set_self _ _ _) hlo hbr3
  let env5 := (env4.set "value" (.bool true)).set "child" (.int nd.high)
  have ctx5 : InnerCtx P nd.var st.cells env5 := ctx3.frame (fun y hy => by
    simp only [env5]
    rcases hy with h | h | h | h | h | h <;> subst h <;>
      rw [Env.get_set_ne _ _ (by decide), Env.get_set_ne _ _ (by decide),
        hfr4 _ (by decide) (by decide) (by decide)])
  obtain ⟨env6, hor6, hbr6, hfr6⟩ := inner_body P nd.var st.cells env5 true nd.high _ ctx5
    (by simp only [env5]; rw [Env.get_set_ne _ _ (by decide), Env.get_set_self])
    (Env.get_set_self _ _ _) hhi
    (by simp only [env5]; rw [Env.get_set_ne _ _ (by decide), Env.get_set_ne _ _ (by decide), hbr4])
  have s3 : ExS .py env2 (.forIn (.tup ["value", "child"]) branchPairs innerBody) (.ok (.normal env6)) :=
    ExS.forIn hbp rfl (ExF.cons_or (bind_tup2 _ _ _ _ env2) hor4
      (ExF.cons_or (bind_tup2 _ _ _ _ env4) hor6 ExF.nil))
  rw [filterMap_two] at hbr6
  -- lookups of untouched variables in `env6`
  have g6 : ∀ y, y ≠ "name" → y ≠ "bit" → y ≠ "branches" → y ≠ "value" → y ≠ "child" →
      y ≠ "cell" → y ≠ "flip" → env6.get y = env.get y := by
    intro y a1 a2 a3 a4 a5 a6 a7
    rw [hfr6 y a6 a7 a3]; simp only [env5]
    rw [Env.get_set_ne _ _ a5, Env.get_set_ne _ _ a4, hfr4 y a6 a7 a3]; simp only [env3]
    rw [Env.get_set_ne _ _ a5, Env.get_set_ne _ _ a4, g2 y a1 a2 a3]
  obtain ⟨env7, hor7, hcl7, hch7, hfr7⟩ := tail_spec env6 _ _ _ hbr6
    ((g6 _ (by decide) (by decide) (by decide) (by decide) (by decide) (by decide) (by decide)).trans hcl)
    ((g6 _ (by decide) (by decide) (by decide) (by decide) (by decide) (by decide) (by decide)).trans hch)
  have hpre : ∀ r, ExB .py env6 tailBody r → ExB .py env outerBody r := fun r h =>
    ExB.cons_normal s1 (ExB.cons_normal s2 (ExB.cons_normal s3 h))
  refine ⟨env7, hor7.imp (hpre _) (hpre _), ?_, ?_, ?_⟩
  · rw [hcl7]; simp [passStep, stepCell]
  · rw [hch7]; simp [passStep, stepCell]
  · intro y hy
    rcases hy with h | h | h | h <;> subst h <;>
      rw [hfr7 _ (by decide) (by decide) (by decide) (by decide) (by decide) (by decide) (by decide),
        g6 _ (by decide) (by decide) (by decide) (by decide) (by decide) (by decide) (by decide)]

/-- **The node loop** is the fold of `passStep`. -/
theorem node_loop (P : Prices) (n : Nat) (rest : List Node) : ∀ (st : PassSt) (env : Env),
    GlobalCtx P n env →
    env.get "cells" = some (.list (st.cells.toList.map encCell)) →
    env.get "choices" = some (.list (st.choices.toList.map encChoice)) →
    (∀ m (h : m < rest.length), rest[m].var < n ∧ rest[m].low < st.cells.size + m ∧
      rest[m].high < st.cells.size + m) →
    ∃ env', ExF .py env (.tup ["var", "low", "high"]) outerBody (rest.map encNode) (.ok (.normal env')) ∧
      env'.get "cells" = some (.list ((rest.foldl (passStep P) st).cells.toList.map encCell)) ∧
      env'.get "choices" = some (.list ((rest.foldl (passStep P) st).choices.toList.map encChoice)) := by
  induction rest with
  | nil => intro st env _ hcl hch _; exact ⟨env, ExF.nil, hcl, hch⟩
  | cons nd rest ih =>
      intro st env hg hcl hch hb
      let env1 := ((env.set "var" (.int nd.var)).set "low" (.int nd.low)).set "high" (.int nd.high)
      have g1 : ∀ y, y ≠ "var" → y ≠ "low" → y ≠ "high" → env1.get y = env.get y := by
        intro y a b c; simp only [env1]
        rw [Env.get_set_ne _ _ c, Env.get_set_ne _ _ b, Env.get_set_ne _ _ a]
      have hg1 : GlobalCtx P n env1 := hg.frame (fun y hy => by
        rcases hy with h | h | h | h <;> subst h <;> exact g1 _ (by decide) (by decide) (by decide))
      obtain ⟨h0v, h0l, h0h⟩ := hb 0 (by simp)
      simp only [List.getElem_cons_zero, Nat.add_zero] at h0v h0l h0h
      obtain ⟨env2, hor, hcl2, hch2, hfr2⟩ := outer_body P n st nd env1 hg1
        ((g1 _ (by decide) (by decide) (by decide)).trans hcl)
        ((g1 _ (by decide) (by decide) (by decide)).trans hch)
        (by simp only [env1]; rw [Env.get_set_ne _ _ (by decide), Env.get_set_ne _ _ (by decide),
          Env.get_set_self])
        (by simp only [env1]; rw [Env.get_set_ne _ _ (by decide), Env.get_set_self])
        (Env.get_set_self _ _ _) h0v h0l h0h
      have hg2 : GlobalCtx P n env2 := hg1.frame hfr2
      obtain ⟨env3, hf, hcl3, hch3⟩ := ih (passStep P st nd) env2 hg2 hcl2 hch2 (fun m hm => by
        obtain ⟨a, b, c⟩ := hb (m + 1) (by simp; omega)
        simp only [List.getElem_cons_succ] at a b c
        simp only [passStep, Array.size_push]
        exact ⟨a, by omega, by omega⟩)
      exact ⟨env3, ExF.cons_or (bind_tup3 _ _ _ _ _ _ env) hor hf, by simpa using hcl3, by simpa using hch3⟩

/-- **Refinement of the extracted Python `bellman`**: for every valid diagram and every
arguments satisfying `Args`, the extracted program returns — for all sufficiently large fuel —
exactly the encoded cells and choices of the Lean reference pass `bellmanPass`. -/
theorem bellman_exec {n : Nat} {ns : Nodes} {P : Prices} (hv : Valid n ns)
    {names bl cs lk : Val} (hargs : Args P n names bl cs lk) :
    ∃ N, ∀ fuel, N ≤ fuel →
      callFn .py fuel Py.bellmanCore [.list (ns.toList.map encNode), names, bl, cs, lk] =
        .ok (.tuple [.list ((bellmanPass ns P).cells.toList.map encCell),
                     .list ((bellmanPass ns P).choices.toList.map encChoice)]) := by
  rw [core_shape]
  refine callFn_of_ExB rfl ?_
  let env0 : Env := [("locked", lk), ("costs", cs), ("baseline", bl), ("names", names),
    ("nodes", .list (ns.toList.map encNode))]
  show ExB .py env0 _ _
  have e1 : EvE .py env0 (.list [.lit .none, .list [i 0, i 1, i 0, i 0]])
      (.ok (.list (PassSt.init.cells.toList.map encCell))) :=
    EvE.res_eq (EvE.list (EvL.cons (EvE.lit _) (EvL.cons (EvE.list (EvL.cons (EvE.lit _)
      (EvL.cons (EvE.lit _) (EvL.cons (EvE.lit _) (EvL.cons (EvE.lit _) EvL.nil))))) EvL.nil))) rfl
  let env1 := env0.set "cells" (.list (PassSt.init.cells.toList.map encCell))
  have s1 := ExS.assign (p := .v "cells") e1 (rfl : bindPat .py _ _ env0 = .ok env1)
  have e2 : EvE .py env1 (.list [.lit .none, .lit .none])
      (.ok (.list (PassSt.init.choices.toList.map encChoice))) :=
    EvE.res_eq (EvE.list (EvL.cons (EvE.lit _) (EvL.cons (EvE.lit _) EvL.nil))) rfl
  let env2 := env1.set "choices" (.list (PassSt.init.choices.toList.map encChoice))
  have s2 := ExS.assign (p := .v "choices") e2 (rfl : bindPat .py _ _ env1 = .ok env2)
  have hg : GlobalCtx P n env2 := ⟨names, bl, cs, lk, rfl, rfl, rfl, rfl, hargs⟩
  obtain ⟨env3, hf, hcl3, hch3⟩ := node_loop P n ns.toList PassSt.init env2 hg rfl rfl (fun m hm => by
    have hm' : m < ns.size := by simpa using hm
    obtain ⟨a, b, c, -⟩ := hv.ok m hm'
    simp only [Array.getElem_toList]
    exact ⟨a, by simp [PassSt.init]; omega, by simp [PassSt.init]; omega⟩)
  have s3 := ExS.forIn (p := .tup ["var", "low", "high"]) (body := outerBody)
    (EvE.var (d := .py) (env := env2) (x := "nodes") rfl) rfl hf
  have e4 := EvE.tuple (d := .py) (EvL.cons (EvE.var hcl3) (EvL.cons (EvE.var hch3) EvL.nil))
  rw [Array.foldl_toList] at e4
  exact ExB.cons_normal s1 (ExB.cons_normal s2 (ExB.cons_normal s3 (ExB.cons_ret (ExS.ret e4))))

end PCSRuntimeRefinement.PyBellman
