import PCSRuntimeRefinement.JsBellman

/-!
# The branch loop and the node loop of the extracted JavaScript `bellman`
-/

namespace PCSRuntimeRefinement.JsBellman

open PCSRuntimeRefinement PCSDD
open PCSRuntimeRefinement.PyBellman (encRaw encCell encChoice encNode EvE.res_eq getD_encCell)

/-- Exactness bound on the cells already computed: adding a change cost `≤ B` stays a safe
integer and the masks are non-negative `int32` values. -/
def CellsBnd (B : Nat) (cells : Array (Option Cell)) : Prop :=
  ∀ (u : Nat) (c : Cell), cells[u]? = some (some c) → ((c.cost + B : Nat) : Int) ≤ MAX_SAFE ∧ c.mand < 2 ^ 31 ∧ c.poss < 2 ^ 31

/-- The variables the branch-loop body reads, with their meaning for variable `k`. -/
structure InnerCtx (P : Prices) (k : Nat) (cells : Array (Option Cell)) (env : Env) : Prop where
  name : ∃ nm tv bl cs lk, env.get "n" = some (.str nm) ∧ env.get "t" = some tv ∧
    fieldOp .js tv "baseline" = .ok bl ∧ indexOp .js bl (.str nm) = .ok (.bool (P.base k)) ∧
    fieldOp .js tv "costs" = .ok cs ∧ indexOp .js cs (.str nm) = .ok (.int (P.cost k)) ∧
    fieldOp .js tv "locked" = .ok lk ∧ memOp .js (.str nm) lk = .ok (P.lock k)
  bit : env.get "bit" = some (.int ((2 ^ k : Nat) : Int))
  cells : env.get "cells" = some (.list (cells.toList.map encCell))

theorem InnerCtx.frame {P : Prices} {k : Nat} {cells : Array (Option Cell)} {env env' : Env}
    (h : InnerCtx P k cells env)
    (hf : ∀ y, y = "n" ∨ y = "t" ∨ y = "bit" ∨ y = "cells" → env'.get y = env.get y) :
    InnerCtx P k cells env' := by
  obtain ⟨⟨nm, tv, bl, cs, lk, hn, ht, h1, h2, h3, h4, h5, h6⟩, hbit, hcells⟩ := h
  exact ⟨⟨nm, tv, bl, cs, lk, (hf _ (by simp)).trans hn, (hf _ (by simp)).trans ht, h1, h2, h3, h4, h5, h6⟩,
    (hf _ (by simp)).trans hbit, (hf _ (by simp)).trans hcells⟩

theorem tf_eval {env : Env} {tv o val : Val} {nm key : String} (ht : env.get "t" = some tv)
    (hn : env.get "n" = some (.str nm)) (hf : fieldOp .js tv key = .ok o)
    (hi : indexOp .js o (.str nm) = .ok val) : EvE .js env (tf key) (.ok val) := by
  have h1 := EvE.field (d := .js) (k := key) (EvE.var ht)
  rw [hf] at h1
  have h2 := EvE.index (d := .js) h1 (EvE.var hn)
  rwa [hi] at h2

theorem getD_encCell_js (cells : Array (Option Cell)) (child : Nat) (h : child < cells.size) :
    indexOp .js (.list (cells.toList.map encCell)) (.int child) = .ok (encCell (cells.getD child none)) := by
  rw [index_list _ child (by simpa using h)]
  simp [Array.getD, h]

/-- The value appended to `branches` for a present child cell (exact JS arithmetic). -/
theorem branch_value (P : Prices) (k : Nat) (x : Bool) (c : Cell) (env : Env)
    (hcs : EvE .js env (tf "costs") (.ok (.int (P.cost k))))
    (hbit : env.get "bit" = some (.int ((2 ^ k : Nat) : Int)))
    (hval : env.get "value" = some (.bool x)) (hcell : env.get "cell" = some (encRaw c))
    (hflip : env.get "flip" = some (.bool (x != P.base k)))
    (hk : k < 31) (hcost : ((c.cost + P.cost k : Nat) : Int) ≤ MAX_SAFE)
    (hm : c.mand < 2 ^ 31) (hp : c.poss < 2 ^ 31) :
    EvE .js env (.list [v "value", .list [
      .bin .add (at' "cell" 0) (flipOr (tf "costs")), at' "cell" 1,
      .bin .bor (at' "cell" 2) (flipOr (v "bit")), .bin .bor (at' "cell" 3) (flipOr (v "bit"))]])
      (.ok (encBr (x, shiftCell (P.flipC k x) (P.flipM k x) c))) := by
  have hpow : 2 ^ k < 2 ^ 31 := Nat.pow_lt_pow_right (by omega) hk
  have c0 : EvE .js env (at' "cell" 0) (.ok (.int c.cost)) := by
    have := EvE.index (d := .js) (EvE.var hcell) (EvE.lit (env := env) (.int 0)); rwa [index_raw0] at this
  have c1 : EvE .js env (at' "cell" 1) (.ok (.int c.count)) := by
    have := EvE.index (d := .js) (EvE.var hcell) (EvE.lit (env := env) (.int 1)); rwa [index_raw1] at this
  have c2 : EvE .js env (at' "cell" 2) (.ok (.int c.mand)) := by
    have := EvE.index (d := .js) (EvE.var hcell) (EvE.lit (env := env) (.int 2)); rwa [index_raw2] at this
  have c3 : EvE .js env (at' "cell" 3) (.ok (.int c.poss)) := by
    have := EvE.index (d := .js) (EvE.var hcell) (EvE.lit (env := env) (.int 3)); rwa [index_raw3] at this
  by_cases hx : x = P.base k
  · subst hx
    have hf : env.get "flip" = some (.bool false) := by simpa using hflip
    have k0 : ∀ t : E, EvE .js env (flipOr t) (.ok (.int ((0 : Nat) : Int))) :=
      fun t => EvE.cond (EvE.var hf) (EvE.lit _)
    have e0 := EvE.bin (op := .add) c0 (k0 (tf "costs"))
    have e2 := EvE.bin (op := .bor) c2 (k0 (v "bit"))
    have e3 := EvE.bin (op := .bor) c3 (k0 (v "bit"))
    rw [add_int _ _ (by unfold MAX_SAFE; omega) (by omega)] at e0
    rw [bor_nat _ _ hm (by omega)] at e2; rw [bor_nat _ _ hp (by omega)] at e3
    have := EvE.list (EvL.cons (EvE.var hval) (EvL.cons (EvE.list (EvL.cons e0 (EvL.cons c1
      (EvL.cons e2 (EvL.cons e3 EvL.nil))))) EvL.nil))
    refine EvE.res_eq this ?_
    simp [encBr, encRaw, shiftCell, Prices.flipC, Prices.flipM]
  · have hf : env.get "flip" = some (.bool true) := by
      cases x <;> cases hb' : P.base k <;> simp_all
    have kc : EvE .js env (flipOr (tf "costs")) (.ok (.int (P.cost k))) := EvE.cond (EvE.var hf) hcs
    have kb : EvE .js env (flipOr (v "bit")) (.ok (.int ((2 ^ k : Nat) : Int))) :=
      EvE.cond (EvE.var hf) (EvE.var hbit)
    have e0 := EvE.bin (op := .add) c0 kc
    have e2 := EvE.bin (op := .bor) c2 kb
    have e3 := EvE.bin (op := .bor) c3 kb
    rw [add_int _ _ (by unfold MAX_SAFE; omega) (by push_cast at hcost; omega)] at e0
    rw [bor_nat _ _ hm hpow] at e2; rw [bor_nat _ _ hp hpow] at e3
    have := EvE.list (EvL.cons (EvE.var hval) (EvL.cons (EvE.list (EvL.cons e0 (EvL.cons c1
      (EvL.cons e2 (EvL.cons e3 EvL.nil))))) EvL.nil))
    refine EvE.res_eq this ?_
    simp [encBr, encRaw, shiftCell, Prices.flipC, Prices.flipM, hx]

/-- **One iteration of the JS branch loop** is `inspect`. -/
theorem inner_body (P : Prices) (k : Nat) (cells : Array (Option Cell)) (env : Env) (x : Bool)
    (child : Nat) (brs : List (Bool × Cell)) (hctx : InnerCtx P k cells env)
    (hval : env.get "value" = some (.bool x)) (hch : env.get "child" = some (.int child))
    (hlt : child < cells.size) (hbr : env.get "branches" = some (.list (brs.map encBr)))
    (hk : k < 31) (hbnd : CellsBnd (P.cost k) cells) :
    ∃ env', (ExB .js env innerBody (.ok (.normal env')) ∨ ExB .js env innerBody (.ok (.cont env'))) ∧
      env'.get "branches" = some (.list ((brs ++ (inspect P cells k x child).toList).map encBr)) ∧
      ∀ y, y ≠ "cell" → y ≠ "flip" → y ≠ "branches" → env'.get y = env.get y := by
  obtain ⟨⟨nm, tv, bl, cs, lk, hn, ht, hfb, hb, hfc, hc, hfl, hl⟩, hbit, hcells⟩ := hctx
  have hne : ∀ env1 : Env, env1.get "value" = some (.bool x) → env1.get "t" = some tv →
      env1.get "n" = some (.str nm) →
      EvE .js env1 (.bin .ne (v "value") (tf "baseline")) (.ok (.bool (x != P.base k))) := by
    intro env1 h1 h2 h3
    have := EvE.bin (op := .ne) (EvE.var h1) (tf_eval h2 h3 hfb hb)
    rwa [ne_bool] at this
  have hmem : EvE .js env (.mem (v "n") (.field (v "t") "locked")) (.ok (.bool (P.lock k))) := by
    have h1 := EvE.field (d := .js) (k := "locked") (EvE.var ht)
    rw [hfl] at h1
    exact EvE.mem (EvE.var hn) h1 hl
  by_cases hskip : P.lock k = true ∧ x ≠ P.base k
  · have hx : (x != P.base k) = true := by simp [hskip.2]
    have hand : EvE .js env (.and (.mem (v "n") (.field (v "t") "locked"))
        (.bin .ne (v "value") (tf "baseline"))) (.ok (.bool true)) := by
      have := hne env hval ht hn; rw [hx] at this
      exact EvE.and_t hmem (by simp [truthy, hskip.1]) this
    have s1 := ExS.if_cont (body := [.cont]) hand rfl (ExB.cons_cont ExS.cont)
    refine ⟨_, Or.inr (ExB.cons_cont s1), ?_, fun y _ _ _ => exit_frame rfl⟩
    rw [exit_keep hbr]; simp [inspect, hskip, hbr]
  · have hand : EvE .js env (.and (.mem (v "n") (.field (v "t") "locked"))
        (.bin .ne (v "value") (tf "baseline"))) (.ok (.bool false)) := by
      cases hlock : P.lock k
      · rw [hlock] at hmem; exact EvE.and_f hmem rfl
      · have hxb : x = P.base k := Classical.byContradiction fun h => hskip ⟨hlock, h⟩
        have := hne env hval ht hn
        rw [hxb] at this; simp only [bne_self_eq_false] at this
        rw [hlock] at hmem; exact EvE.and_t hmem rfl this
    have s1 := ExS.if_false (body := [.cont]) hand rfl
    have hinsp : inspect P cells k x child =
        (cells.getD child none).map (fun c => (x, shiftCell (P.flipC k x) (P.flipM k x) c)) := by
      unfold inspect; rw [if_neg hskip]; cases cells.getD child none <;> rfl
    have hcellv := EvE.index (d := .js) (EvE.var hcells) (EvE.var hch)
    rw [getD_encCell_js _ _ hlt] at hcellv
    rw [hinsp]
    cases hcg : cells.getD child none with
    | none =>
        rw [hcg] at hcellv
        let env1 := env.set "cell" .none
        have s2 := ExS.assign (p := .v "cell") hcellv (rfl : bindPat .js _ _ env = .ok env1)
        have s3 := ExS.if_cont (body := [.cont]) (EvE.isNone (d := .js) (EvE.var (Env.get_set_self env "cell" .none)))
          rfl (ExB.cons_cont ExS.cont)
        refine ⟨_, Or.inr (ExB.cons_normal s1 (ExB.cons_normal s2 (ExB.cons_cont s3))), ?_, ?_⟩
        · have hb1 : env1.get "branches" = some (.list (brs.map encBr)) := by
            simp only [env1]; rw [Env.get_set_ne _ _ (by decide), hbr]
          rw [exit_keep hb1, hb1]; simp
        · intro y h1 _ _
          rw [exit_frame rfl]; exact Env.get_set_ne _ _ h1
    | some c =>
        rw [hcg] at hcellv
        have hcb := hbnd child c (by
          have e : cells.getD child none = cells[child] := by simp [Array.getD, hlt]
          rw [Array.getElem?_eq_getElem hlt, ← e, hcg])
        let env1 := env.set "cell" (encRaw c)
        have g1 : ∀ y, y ≠ "cell" → env1.get y = env.get y := fun y h => Env.get_set_ne _ _ h
        have s2 := ExS.assign (p := .v "cell") hcellv (rfl : bindPat .js _ _ env = .ok env1)
        have s3 := ExS.if_false (body := [.cont]) (EvE.isNone (d := .js) (EvE.var (Env.get_set_self env "cell" (encRaw c))))
          rfl
        let env2 := env1.set "flip" (.bool (x != P.base k))
        have g2 : ∀ y, y ≠ "cell" → y ≠ "flip" → env2.get y = env.get y := fun y h h' =>
          (Env.get_set_ne _ _ h').trans (g1 y h)
        have s4 := ExS.assign (p := .v "flip")
          (hne env1 ((g1 _ (by decide)).trans hval) ((g1 _ (by decide)).trans ht) ((g1 _ (by decide)).trans hn))
          (rfl : bindPat .js _ _ env1 = .ok env2)
        have hv := branch_value P k x c env2
          (tf_eval ((g2 _ (by decide) (by decide)).trans ht) ((g2 _ (by decide) (by decide)).trans hn) hfc hc)
          ((g2 _ (by decide) (by decide)).trans hbit)
          ((g2 _ (by decide) (by decide)).trans hval)
          ((Env.get_set_ne _ _ (by decide)).trans (Env.get_set_self env "cell" (encRaw c)))
          (Env.get_set_self _ _ _) hk hcb.1 hcb.2.1 hcb.2.2
        have s5 := ExS.append (d := .js) ((g2 _ (by decide) (by decide)).trans hbr) hv
        refine ⟨_, Or.inl (ExB.cons_normal s1 (ExB.cons_normal s2 (ExB.cons_normal s3
          (ExB.cons_normal s4 (ExB.cons_normal s5 ExB.nil))))), ?_, ?_⟩
        · simp
        · intro y h1 h2 h3; rw [Env.get_set_ne _ _ h3]; exact g2 y h1 h2

/-! ## The node loop -/

/-- The meaning of the argument `t` (and of `names = t.problem.variables`) for prices `P` over
`n` variables. -/
def ArgsJ (P : Prices) (n : Nat) (tv names : Val) : Prop :=
  ∃ (nms : List String) (bl cs lk : Val), names = .list (nms.map .str) ∧ n ≤ nms.length ∧
    fieldOp .js tv "baseline" = .ok bl ∧ fieldOp .js tv "costs" = .ok cs ∧
    fieldOp .js tv "locked" = .ok lk ∧
    ∀ k, k < n → indexOp .js bl (.str (nms.getD k "")) = .ok (.bool (P.base k)) ∧
      indexOp .js cs (.str (nms.getD k "")) = .ok (.int (P.cost k)) ∧
      memOp .js (.str (nms.getD k "")) lk = .ok (P.lock k)

def GlobalCtx (P : Prices) (n : Nat) (env : Env) : Prop :=
  ∃ tv names, env.get "t" = some tv ∧ env.get "names" = some names ∧ ArgsJ P n tv names

theorem GlobalCtx.frame {P : Prices} {n : Nat} {env env' : Env} (h : GlobalCtx P n env)
    (hf : ∀ y, y = "t" ∨ y = "names" → env'.get y = env.get y) : GlobalCtx P n env' := by
  obtain ⟨a, b, h1, h2, h3⟩ := h
  exact ⟨a, b, (hf _ (by simp)).trans h1, (hf _ (by simp)).trans h2, h3⟩

theorem inspect_some {P : Prices} {cells : Array (Option Cell)} {k : Nat} {x : Bool} {child : Nat}
    {p : Bool × Cell} (h : inspect P cells k x child = some p) :
    ∃ c, cells[child]? = some (some c) ∧ p = (x, shiftCell (P.flipC k x) (P.flipM k x) c) := by
  unfold inspect at h
  split at h
  · cases h
  · cases hc : cells.getD child none with
    | none => rw [hc] at h; cases h
    | some c =>
        rw [hc] at h
        simp only [Option.some.injEq] at h
        refine ⟨c, ?_, h.symm⟩
        unfold Array.getD at hc
        split at hc
        · rename_i hlt; rw [Array.getElem?_eq_getElem hlt]; exact congrArg some hc
        · cases hc

theorem inspect_mask {P : Prices} {cells : Array (Option Cell)} {k B : Nat} (hk : k < 31)
    (hb : CellsBnd B cells) (lo hi : Nat) :
    ∀ p ∈ [inspect P cells k false lo, inspect P cells k true hi].filterMap id,
      p.2.mand < 2 ^ 31 ∧ p.2.poss < 2 ^ 31 := by
  have hpow : 2 ^ k < 2 ^ 31 := Nat.pow_lt_pow_right (by omega) hk
  have key : ∀ x child p, inspect P cells k x child = some p → p.2.mand < 2 ^ 31 ∧ p.2.poss < 2 ^ 31 := by
    intro x child p h
    obtain ⟨c, hc, rfl⟩ := inspect_some h
    obtain ⟨-, hm, hp⟩ := hb child c hc
    have hf : P.flipM k x < 2 ^ 31 := by unfold Prices.flipM; split <;> omega
    exact ⟨Nat.or_lt_two_pow hm hf, Nat.or_lt_two_pow hp hf⟩
  intro p hp
  rw [List.mem_filterMap] at hp
  obtain ⟨o, ho, hop⟩ := hp
  simp only [List.mem_cons, List.mem_nil_iff, or_false] at ho
  rcases ho with rfl | rfl <;> exact key _ _ _ hop

/-- **One iteration of the JS node loop** is `passStep`. -/
theorem outer_body (P : Prices) (n B : Nat) (st : PassSt) (nd : Node) (env : Env)
    (hg : GlobalCtx P n env)
    (hcl : env.get "cells" = some (.list (st.cells.toList.map encCell)))
    (hch : env.get "choices" = some (.list (st.choices.toList.map encChoice)))
    (hv : env.get "v" = some (.int nd.var)) (hl : env.get "lo" = some (.int nd.low))
    (hh : env.get "hi" = some (.int nd.high))
    (hvar : nd.var < n) (hn31 : n ≤ 31) (hlo : nd.low < st.cells.size) (hhi : nd.high < st.cells.size)
    (hcostB : P.cost nd.var ≤ B) (hbnd : CellsBnd B st.cells)
    (hstep : ∀ c, (stepCell P st.cells nd).1 = some c → (c.count : Int) ≤ MAX_SAFE) :
    ∃ env', (ExB .js env outerBody (.ok (.normal env')) ∨ ExB .js env outerBody (.ok (.cont env'))) ∧
      env'.get "cells" = some (.list ((passStep P st nd).cells.toList.map encCell)) ∧
      env'.get "choices" = some (.list ((passStep P st nd).choices.toList.map encChoice)) ∧
      ∀ y, y = "t" ∨ y = "names" → env'.get y = env.get y := by
  have hk : nd.var < 31 := by omega
  have hbndk : CellsBnd (P.cost nd.var) st.cells := fun u c h => by
    obtain ⟨a, b, d⟩ := hbnd u c h; exact ⟨by push_cast at a ⊢; omega, b, d⟩
  obtain ⟨tv, names, ht, hn, nms, bl, cs, lk, rfl, hlen, hfb, hfc, hfl, hk'⟩ := hg
  obtain ⟨hbk, hck, hlkk⟩ := hk' nd.var hvar
  generalize hnm : nms.getD nd.var "" = nm at hbk hck hlkk
  have e1 : EvE .js env (.index (v "names") (v "v")) (.ok (.str nm)) := by
    have h1 := EvE.index (d := .js) (EvE.var hn) (EvE.var hv)
    rw [index_list _ _ (by simp; omega)] at h1
    rw [← hnm]; simpa [List.getD_eq_getElem?_getD, show nd.var < nms.length by omega] using h1
  let env1 := env.set "n" (.str nm)
  have s1 := ExS.assign (p := .v "n") e1 (rfl : bindPat .js _ _ env = .ok env1)
  have e2 : EvE .js env1 (.bin .pow (i 2) (v "v")) (.ok (.int ((2 ^ nd.var : Nat) : Int))) := by
    have := EvE.bin (op := .pow) (EvE.lit (d := .js) (env := env1) (.int 2))
      (EvE.var ((Env.get_set_ne _ _ (by decide)).trans hv))
    rwa [pow_two _ hk] at this
  let env2 := env1.set "bit" (.int ((2 ^ nd.var : Nat) : Int))
  have s2 := ExS.assign (p := .v "bit") e2 (rfl : bindPat .js _ _ env1 = .ok env2)
  let env3 := env2.set "branches" (.list [])
  have s3 := ExS.assign (p := .v "branches") (EvE.list (d := .js) (env := env2) EvL.nil)
    (rfl : bindPat .js _ _ env2 = .ok env3)
  have g3 : ∀ y, y ≠ "n" → y ≠ "bit" → y ≠ "branches" → env3.get y = env.get y := by
    intro y h1 h2 h3
    simp only [env3, env2, env1]; rw [Env.get_set_ne _ _ h3, Env.get_set_ne _ _ h2, Env.get_set_ne _ _ h1]
  have ctx3 : InnerCtx P nd.var st.cells env3 := by
    refine ⟨⟨nm, tv, bl, cs, lk, ?_, (g3 _ (by decide) (by decide) (by decide)).trans ht,
      hfb, hbk, hfc, hck, hfl, hlkk⟩, ?_, (g3 _ (by decide) (by decide) (by decide)).trans hcl⟩
    · simp only [env3, env2, env1]
      rw [Env.get_set_ne _ _ (by decide), Env.get_set_ne _ _ (by decide), Env.get_set_self]
    · simp only [env3, env2]; rw [Env.get_set_ne _ _ (by decide), Env.get_set_self]
  have hbp : EvE .js env3 branchPairs (.ok (.list [.list [.bool false, .int nd.low],
      .list [.bool true, .int nd.high]])) := by
    have hl3 := (g3 _ (by decide) (by decide) (by decide)).trans hl
    have hh3 := (g3 _ (by decide) (by decide) (by decide)).trans hh
    exact EvE.list (EvL.cons (EvE.list (EvL.cons (EvE.lit _) (EvL.cons (EvE.var hl3) EvL.nil)))
      (EvL.cons (EvE.list (EvL.cons (EvE.lit _) (EvL.cons (EvE.var hh3) EvL.nil))) EvL.nil))
  have hbr3 : env3.get "branches" = some (.list (([] : List (Bool × Cell)).map encBr)) := by
    simp [env3]
  -- first iteration
  let env4 := (env3.set "value" (.bool false)).set "child" (.int nd.low)
  have ctx4 : InnerCtx P nd.var st.cells env4 := ctx3.frame (fun y hy => by
    simp only [env4]
    rcases hy with h | h | h | h <;> subst h <;>
      rw [Env.get_set_ne _ _ (by decide), Env.get_set_ne _ _ (by decide)])
  obtain ⟨env5, hor5, hbr5, hfr5⟩ := inner_body P nd.var st.cells env4 false nd.low [] ctx4
    (by simp only [env4]; rw [Env.get_set_ne _ _ (by decide), Env.get_set_self])
    (Env.get_set_self _ _ _) hlo
    (by simp only [env4]; rw [Env.get_set_ne _ _ (by decide), Env.get_set_ne _ _ (by decide), hbr3])
    hk hbndk
  have f5 : ∀ y, y ≠ "cell" → y ≠ "flip" → y ≠ "branches" → y ≠ "value" → y ≠ "child" →
      env5.get y = env3.get y := by
    intro y a b c d e
    rw [hfr5 y a b c]; simp only [env4]; rw [Env.get_set_ne _ _ e, Env.get_set_ne _ _ d]
  let env6 := exitBlock .js env3 env5
  have f6 : ∀ y, y ≠ "cell" → y ≠ "flip" → y ≠ "branches" → y ≠ "value" → y ≠ "child" →
      env6.get y = env3.get y := fun y a b c d e => exit_frame (f5 y a b c d e)
  have hbr6 : env6.get "branches" = some (.list (([] ++ (inspect P st.cells nd.var false nd.low).toList).map encBr)) := by
    simp only [env6]; rw [exit_keep hbr3, hbr5]
  -- second iteration
  let env7 := (env6.set "value" (.bool true)).set "child" (.int nd.high)
  have ctx7 : InnerCtx P nd.var st.cells env7 := ctx3.frame (fun y hy => by
    simp only [env7]
    rcases hy with h | h | h | h <;> subst h <;>
      rw [Env.get_set_ne _ _ (by decide), Env.get_set_ne _ _ (by decide),
        f6 _ (by decide) (by decide) (by decide) (by decide) (by decide)])
  obtain ⟨env8, hor8, hbr8, hfr8⟩ := inner_body P nd.var st.cells env7 true nd.high _ ctx7
    (by simp only [env7]; rw [Env.get_set_ne _ _ (by decide), Env.get_set_self])
    (Env.get_set_self _ _ _) hhi
    (by simp only [env7]; rw [Env.get_set_ne _ _ (by decide), Env.get_set_ne _ _ (by decide), hbr6])
    hk hbndk
  let env9 := exitBlock .js env6 env8
  have s4 : ExS .js env3 (.forIn (.tup ["value", "child"]) branchPairs innerBody) (.ok (.normal env9)) :=
    ExS.forIn hbp rfl (ExF.cons_or (bind_vc _ _ env3) hor5
      (ExF.cons_or (bind_vc _ _ env6) hor8 ExF.nil))
  have hbr9 : env9.get "branches" = some (.list (([inspect P st.cells nd.var false nd.low,
      inspect P st.cells nd.var true nd.high].filterMap id).map encBr)) := by
    simp only [env9]; rw [exit_keep hbr6, hbr8, PyBellman.filterMap_two]
  have g9 : ∀ y, y ≠ "n" → y ≠ "bit" → y ≠ "branches" → y ≠ "value" → y ≠ "child" →
      y ≠ "cell" → y ≠ "flip" → env9.get y = env.get y := by
    intro y a1 a2 a3 a4 a5 a6 a7
    simp only [env9]
    rw [exit_frame (y := y) (by rw [hfr8 y a6 a7 a3]; simp only [env7]; rw [Env.get_set_ne _ _ a5, Env.get_set_ne _ _ a4]),
      f6 y a6 a7 a3 a4 a5, g3 y a1 a2 a3]
  obtain ⟨env10, hor10, hcl10, hch10, hfr10⟩ := tail_spec env9 _ _ _ hbr9
    ((g9 _ (by decide) (by decide) (by decide) (by decide) (by decide) (by decide) (by decide)).trans hcl)
    ((g9 _ (by decide) (by decide) (by decide) (by decide) (by decide) (by decide) (by decide)).trans hch)
    (inspect_mask hk hbnd _ _) hstep
  have hpre : ∀ r, ExB .js env9 tailBody r → ExB .js env outerBody r := fun r h =>
    ExB.cons_normal s1 (ExB.cons_normal s2 (ExB.cons_normal s3 (ExB.cons_normal s4 h)))
  refine ⟨env10, hor10.imp (hpre _) (hpre _), ?_, ?_, ?_⟩
  · rw [hcl10]; simp [passStep, stepCell]
  · rw [hch10]; simp [passStep, stepCell]
  · intro y hy
    rcases hy with h | h <;> subst h <;>
      rw [hfr10 _ (by decide) (by decide) (by decide) (by decide) (by decide) (by decide),
        g9 _ (by decide) (by decide) (by decide) (by decide) (by decide) (by decide) (by decide)]

theorem passUpTo_succ (ns : Nodes) (P : Prices) (j : Nat) (hj : j < ns.size) :
    passUpTo ns P (j + 1) = passStep P (passUpTo ns P j) ns[j] := by
  unfold passUpTo
  rw [List.take_add_one, List.foldl_append]
  simp [List.getElem?_eq_getElem (by simpa using hj : j < ns.toList.length)]

theorem bellmanPass_eq_passUpTo (ns : Nodes) (P : Prices) : bellmanPass ns P = passUpTo ns P ns.size := by
  unfold bellmanPass passUpTo
  rw [← Array.length_toList, List.take_length, Array.foldl_toList]
  rfl

/-- **The JS node loop** runs the whole reference pass, with exact arithmetic throughout. -/
theorem node_loop {n : Nat} {ns : Nodes} {P : Prices} {B : Nat} (hv : Valid n ns)
    (hpos : ∀ k < n, 0 < P.cost k) (hB : ∀ k, P.cost k ≤ B) (hn31 : n ≤ 31)
    (hNB : ((n * B + B : Nat) : Int) ≤ MAX_SAFE) :
    ∀ d j, j + d = ns.size → ∀ env, GlobalCtx P n env →
      env.get "cells" = some (.list ((passUpTo ns P j).cells.toList.map encCell)) →
      env.get "choices" = some (.list ((passUpTo ns P j).choices.toList.map encChoice)) →
      ∃ env', ExF .js env (.tup ["v", "lo", "hi"]) outerBody ((ns.toList.drop j).map encNode)
          (.ok (.normal env')) ∧
        env'.get "cells" = some (.list ((bellmanPass ns P).cells.toList.map encCell)) ∧
        env'.get "choices" = some (.list ((bellmanPass ns P).choices.toList.map encChoice)) := by
  intro d
  induction d with
  | zero =>
      intro j hj env _ hcl hch
      have hj' : j = ns.size := by omega
      subst hj'
      refine ⟨env, ?_, ?_, ?_⟩
      · rw [show ns.toList.drop ns.size = [] by simp]; exact ExF.nil
      · rw [bellmanPass_eq_passUpTo]; exact hcl
      · rw [bellmanPass_eq_passUpTo]; exact hch
  | succ d ih =>
      intro j hj env hg hcl hch
      have hjs : j < ns.size := by omega
      have I := passUpTo_inv (P := P) hv j (by omega)
      have I1 := passUpTo_inv (P := P) hv (j + 1) (by omega)
      obtain ⟨hvar, hlo, hhi, -⟩ := hv.ok j hjs
      have h2n : 2 ^ n ≤ 2 ^ 31 := Nat.pow_le_pow_right (by omega) hn31
      have hbnd : CellsBnd B (passUpTo ns P j).cells := by
        intro u c hu
        have hlt : u < j + 2 := by
          have := I.cells_size
          rcases Nat.lt_or_ge u (passUpTo ns P j).cells.size with h | h
          · omega
          · rw [Array.getElem?_eq_none h] at hu; cases hu
        rw [I.cells u hlt] at hu
        simp only [Option.some.injEq] at hu
        obtain ⟨-, hm, hp, -, -, hc⟩ := bellman_bounds hv hpos (by omega) hu
        have hcB := hc B hB
        refine ⟨?_, by omega, by omega⟩
        have : c.cost + B ≤ n * B + B := by omega
        push_cast at hNB ⊢; omega
      have hstep : ∀ c, (stepCell P (passUpTo ns P j).cells ns[j]).1 = some c → (c.count : Int) ≤ MAX_SAFE := by
        intro c hc
        have h1 := I1.cells (j + 2) (by omega)
        rw [passUpTo_succ ns P j hjs] at h1
        simp only [passStep] at h1
        rw [Array.getElem?_push, if_pos (by rw [I.cells_size])] at h1
        simp only [Option.some.injEq] at h1
        rw [hc] at h1
        obtain ⟨hcnt, -⟩ := bellman_bounds hv hpos (u := j + 2) (by omega) h1.symm
        unfold MAX_SAFE; omega
      let env1 := ((env.set "v" (.int ns[j].var)).set "lo" (.int ns[j].low)).set "hi" (.int ns[j].high)
      have g1 : ∀ y, y ≠ "v" → y ≠ "lo" → y ≠ "hi" → env1.get y = env.get y := by
        intro y a b c; simp only [env1]
        rw [Env.get_set_ne _ _ c, Env.get_set_ne _ _ b, Env.get_set_ne _ _ a]
      have hg1 : GlobalCtx P n env1 := hg.frame (fun y hy => by
        rcases hy with h | h <;> subst h <;> exact g1 _ (by decide) (by decide) (by decide))
      obtain ⟨env2, hor, hcl2, hch2, hfr2⟩ := outer_body P n B (passUpTo ns P j) ns[j] env1 hg1
        ((g1 _ (by decide) (by decide) (by decide)).trans hcl)
        ((g1 _ (by decide) (by decide) (by decide)).trans hch)
        (by simp only [env1]; rw [Env.get_set_ne _ _ (by decide), Env.get_set_ne _ _ (by decide),
          Env.get_set_self])
        (by simp only [env1]; rw [Env.get_set_ne _ _ (by decide), Env.get_set_self])
        (Env.get_set_self _ _ _) hvar hn31 (by rw [I.cells_size]; omega) (by rw [I.cells_size]; omega)
        (hB _) hbnd hstep
      let env3 := exitBlock .js env env2
      have hg3 : GlobalCtx P n env3 := hg.frame (fun y hy => exit_frame ((hfr2 y hy).trans
        (by rcases hy with h | h <;> subst h <;> exact g1 _ (by decide) (by decide) (by decide))))
      rw [← passUpTo_succ ns P j hjs] at hcl2 hch2
      obtain ⟨env4, hf, hcl4, hch4⟩ := ih (j + 1) (by omega) env3 hg3
        (by simp only [env3]; rw [exit_keep hcl]; exact hcl2)
        (by simp only [env3]; rw [exit_keep hch]; exact hch2)
      refine ⟨env4, ?_, hcl4, hch4⟩
      rw [List.drop_eq_getElem_cons (by simpa using hjs)]
      simp only [List.map_cons, Array.getElem_toList]
      exact ExF.cons_or (bind_node _ _ _ env) hor hf

/-- **Refinement of the extracted JavaScript `bellman`**: for every valid diagram over
`n ≤ 31` variables with positive change costs bounded by `B` such that `(n+1)·B` is a safe
integer, and every argument object `t` satisfying `ArgsJ`, the extracted program returns — for
all sufficiently large fuel — exactly the encoded cells and choices of `bellmanPass`, and no
intermediate number leaves the exactly-representable range. -/
theorem bellman_exec {n : Nat} {ns : Nodes} {P : Prices} {B : Nat} (hv : Valid n ns)
    (hpos : ∀ k < n, 0 < P.cost k) (hB : ∀ k, P.cost k ≤ B) (hn31 : n ≤ 31)
    (hNB : ((n * B + B : Nat) : Int) ≤ MAX_SAFE) {tv names pr : Val}
    (hpr : fieldOp .js tv "problem" = .ok pr) (hvars : fieldOp .js pr "variables" = .ok names)
    (hargs : ArgsJ P n tv names) :
    ∃ N, ∀ fuel, N ≤ fuel →
      callFn .js fuel Js.bellmanCore [.list (ns.toList.map encNode), tv] =
        .ok (.obj [("cells", .list ((bellmanPass ns P).cells.toList.map encCell)),
                   ("choices", .list ((bellmanPass ns P).choices.toList.map encChoice))]) := by
  rw [core_shape]
  refine callFn_of_ExB rfl ?_
  let env0 : Env := [("t", tv), ("nodes", .list (ns.toList.map encNode))]
  show ExB .js env0 _ _
  have e1 : EvE .js env0 (.list [.lit .none, .list [i 0, i 1, i 0, i 0]])
      (.ok (.list (PassSt.init.cells.toList.map encCell))) :=
    EvE.res_eq (EvE.list (EvL.cons (EvE.lit _) (EvL.cons (EvE.list (EvL.cons (EvE.lit _)
      (EvL.cons (EvE.lit _) (EvL.cons (EvE.lit _) (EvL.cons (EvE.lit _) EvL.nil))))) EvL.nil))) rfl
  let env1 := env0.set "cells" (.list (PassSt.init.cells.toList.map encCell))
  have s1 := ExS.assign (p := .v "cells") e1 (rfl : bindPat .js _ _ env0 = .ok env1)
  have e2 : EvE .js env1 (.list [.lit .none, .lit .none])
      (.ok (.list (PassSt.init.choices.toList.map encChoice))) :=
    EvE.res_eq (EvE.list (EvL.cons (EvE.lit _) (EvL.cons (EvE.lit _) EvL.nil))) rfl
  let env2 := env1.set "choices" (.list (PassSt.init.choices.toList.map encChoice))
  have s2 := ExS.assign (p := .v "choices") e2 (rfl : bindPat .js _ _ env1 = .ok env2)
  have e3 : EvE .js env2 (.field (.field (v "t") "problem") "variables") (.ok names) := by
    have h1 := EvE.field (d := .js) (k := "problem") (EvE.var (env := env2) (x := "t") rfl)
    rw [hpr] at h1
    have h2 := EvE.field (d := .js) (k := "variables") h1
    rwa [hvars] at h2
  let env3 := env2.set "names" names
  have s3 := ExS.assign (p := .v "names") e3 (rfl : bindPat .js _ _ env2 = .ok env3)
  have hg : GlobalCtx P n env3 := ⟨tv, names, rfl, Env.get_set_self _ _ _, hargs⟩
  have hinit : passUpTo ns P 0 = PassSt.init := rfl
  obtain ⟨env4, hf, hcl4, hch4⟩ := node_loop hv hpos hB hn31 hNB ns.size 0 (by omega) env3 hg
    (by rw [hinit]; rfl) (by rw [hinit]; rfl)
  have s4 := ExS.forIn (p := .tup ["v", "lo", "hi"]) (body := outerBody)
    (EvE.var (d := .js) (env := env3) (x := "nodes") rfl) rfl (by simpa using hf)
  have e5 := EvE.objLit (d := .js) (ks := ["cells", "choices"])
    (EvL.cons (EvE.var hcl4) (EvL.cons (EvE.var hch4) EvL.nil))
  exact ExB.cons_normal s1 (ExB.cons_normal s2 (ExB.cons_normal s3 (ExB.cons_normal s4
    (ExB.cons_ret (ExS.ret e5)))))

end PCSRuntimeRefinement.JsBellman
