import PCSConditionalRuntime.PyTry

/-!
# `check`: the `except ResourceLimit as error` handler

```
for field in ['context_example', 'counterexample', 'unsat_core', 'core_necessity_witnesses', 'diagram']:
    result[field] = None
result.update(decision='resource_limit', limit_reached=str(error))
```
-/

namespace PCSCR.Py

open PCSCR PCSDD PCSOmega

def handlerB : List S :=
  [S.forIn (Tgt.name "field")
     (E.listD [E.lit (V.str "context_example"), E.lit (V.str "counterexample"), E.lit (V.str "unsat_core"),
       E.lit (V.str "core_necessity_witnesses"), E.lit (V.str "diagram")])
     [S.assign [Tgt.sub (E.var "result") (E.var "field")] (E.lit V.none)],
   S.expr (E.kwcall (E.var "result") "update" ["decision", "limit_reached"]
     [E.lit (V.str "resource_limit"), E.call "str" [E.var "error"]])]

/-- The JSON fields after the handler. -/
def limKT (kts : List (String × T)) (e : LimitReached) : List (String × T) :=
  tset (tset (tset (tset (tset (tset (tset kts "context_example" .null) "counterexample" .null) "unsat_core" .null)
    "core_necessity_witnesses" .null) "diagram" .null) "decision" (.str "resource_limit"))
    "limit_reached" (.str e.name)

theorem hset_hset_same (H : Heap) (a : Nat) (x y : Obj) : hset (hset H a x) a y = hset H a y := by
  simp [hset]

def nullBody : List S := [S.assign [Tgt.sub (E.var "result") (E.var "field")] (E.lit V.none)]

theorem null_step (ext : Ext) (j i : Nat) (env : Env) (H : Heap) (L R : Nat) (xs : List V) (kvs : List (V × V))
    (f : String) (hL : hget H L = some (.list xs)) (hx : xs[i]? = some (.str f))
    (hRk : hget H R = some (.dict kvs)) (hres : env.get "result" = some (.ref R)) :
    forIter (pyCtx ext) (interp (pyCtx ext) (j + 1)) env H (Tgt.name "field") (.ref L) i nullBody =
      forIter (pyCtx ext) (interp (pyCtx ext) j) (env.set "field" (.str f))
        (hset H R (.dict (dictSet .py kvs (.str f) .none))) (Tgt.name "field") (.ref L) (i + 1) nullBody := by
  have hRlt := hget_lt hRk
  conv =>
    lhs
    simp [forIter, elemAt, hL, hx, bindE, assignT, nullBody, execB, execS, evalE, bindS, assignAll,
      Env.get_set, hres, storeOp, hRk, hashable, loopK]
  rfl

theorem handler_sim (ext : Ext) (k : Nat) (env : Env) (h : Heap) (R a : Nat) (kvs : List (V × V))
    (kts : List (String × T)) (e : LimitReached) (M : Nat → Prop) (hk : 6 ≤ k)
    (hres : env.get "result" = some (.ref R)) (herr : env.get "error" = some (.ref a))
    (ha : hget h a = some (.inst "ResourceLimit" [("args", .tup [.str e.name])]))
    (hRk : hget h R = some (.dict kvs)) (hkv : ReadsKV M h kvs kts) (hMR : M R) :
    ∃ env' h' kvs', execB (pyCtx ext) (interp (pyCtx ext) (k + 1)) env h handlerB = .ok (.normal env') h' ∧
      (∀ y, y ≠ "field" → env'.get y = env.get y) ∧
      hget h' R = some (.dict kvs') ∧ ReadsKV M h' kvs' (limKT kts e) ∧ FrameS (fun x => x = R) h h' := by
  obtain ⟨k, rfl⟩ : ∃ k', k = k' + 6 := ⟨k - 6, by omega⟩
  have hRlt := hget_lt hRk
  have hal := hget_lt ha
  generalize hL5 : [V.str "context_example", V.str "counterexample", V.str "unsat_core",
    V.str "core_necessity_witnesses", V.str "diagram"] = L5
  have e1 : execS (pyCtx ext) (interp (pyCtx ext) (k + 6 + 1)) env h (handlerB.head!) =
      forIter (pyCtx ext) (interp (pyCtx ext) (k + 6)) env (h ++ [Obj.list L5]) (Tgt.name "field")
        (.ref h.length) 0 nullBody := by
    rw [← hL5]; rfl
  simp only [handlerB]
  rw [execB_cons']
  simp only [handlerB, List.head!] at e1
  rw [e1]
  have hL0 : hget (h ++ [Obj.list L5]) h.length = some (.list L5) := by simp [hget]
  have hRL : R ≠ h.length := by omega
  have hR0 : hget (h ++ [Obj.list L5]) R = some (.dict kvs) := by rw [hget_append_lt_list _ hRlt]; exact hRk
  rw [show k + 6 = (k + 5) + 1 from rfl]
  rw [null_step ext (k + 5) 0 env _ h.length R L5 kvs "context_example" hL0 (by rw [← hL5]; rfl) hR0 hres]
  rw [null_step ext (k + 4) 1 _ _ h.length R L5 _ "counterexample" (by rw [hget_hset_ne _ hRL]; exact hL0)
    (by rw [← hL5]; rfl) (hget_hset_same _ (by simp; omega)) (by simp [Env.get_set, hres])]
  rw [null_step ext (k + 3) 2 _ _ h.length R L5 _ "unsat_core"
    (by rw [hget_hset_ne _ hRL, hget_hset_ne _ hRL]; exact hL0)
    (by rw [← hL5]; rfl) (hget_hset_same _ (by simp; omega)) (by simp [Env.get_set, hres])]
  rw [null_step ext (k + 2) 3 _ _ h.length R L5 _ "core_necessity_witnesses"
    (by rw [hget_hset_ne _ hRL, hget_hset_ne _ hRL, hget_hset_ne _ hRL]; exact hL0)
    (by rw [← hL5]; rfl) (hget_hset_same _ (by simp; omega)) (by simp [Env.get_set, hres])]
  rw [null_step ext (k + 1) 4 _ _ h.length R L5 _ "diagram"
    (by rw [hget_hset_ne _ hRL, hget_hset_ne _ hRL, hget_hset_ne _ hRL, hget_hset_ne _ hRL]; exact hL0)
    (by rw [← hL5]; rfl) (hget_hset_same _ (by simp; omega)) (by simp [Env.get_set, hres])]
  simp only [hset_hset_same]
  subst hL5
  have hel : forIter (pyCtx ext) (interp (pyCtx ext) (k + 1))
      (((((env.set "field" (V.str "context_example")).set "field" (V.str "counterexample")).set "field"
        (V.str "unsat_core")).set "field" (V.str "core_necessity_witnesses")).set "field" (V.str "diagram"))
      (hset (h ++ [Obj.list [V.str "context_example", V.str "counterexample", V.str "unsat_core",
        V.str "core_necessity_witnesses", V.str "diagram"]]) R (Obj.dict
          (dictSet Dialect.py (dictSet Dialect.py (dictSet Dialect.py (dictSet Dialect.py
            (dictSet Dialect.py kvs (V.str "context_example") V.none) (V.str "counterexample") V.none)
            (V.str "unsat_core") V.none) (V.str "core_necessity_witnesses") V.none) (V.str "diagram") V.none)))
      (Tgt.name "field") (V.ref (List.length h)) (4 + 1) nullBody =
      .ok (.normal (((((env.set "field" (V.str "context_example")).set "field" (V.str "counterexample")).set "field"
        (V.str "unsat_core")).set "field" (V.str "core_necessity_witnesses")).set "field" (V.str "diagram")))
      (hset (h ++ [Obj.list [V.str "context_example", V.str "counterexample", V.str "unsat_core",
        V.str "core_necessity_witnesses", V.str "diagram"]]) R (Obj.dict
          (dictSet Dialect.py (dictSet Dialect.py (dictSet Dialect.py (dictSet Dialect.py
            (dictSet Dialect.py kvs (V.str "context_example") V.none) (V.str "counterexample") V.none)
            (V.str "unsat_core") V.none) (V.str "core_necessity_witnesses") V.none) (V.str "diagram") V.none))) := by
    simp only [forIter, elemAt, hget_hset_ne _ hRL]
    simp [hget]
  rw [hel]
  simp only [seqF_normal]
  have haR : a ≠ R := fun e => by rw [e, hRk] at ha; cases ha
  have hal' : hget (hset (h ++ [Obj.list [V.str "context_example", V.str "counterexample", V.str "unsat_core",
        V.str "core_necessity_witnesses", V.str "diagram"]]) R (Obj.dict
          (dictSet Dialect.py (dictSet Dialect.py (dictSet Dialect.py (dictSet Dialect.py
            (dictSet Dialect.py kvs (V.str "context_example") V.none) (V.str "counterexample") V.none)
            (V.str "unsat_core") V.none) (V.str "core_necessity_witnesses") V.none) (V.str "diagram") V.none))) a =
      some (.inst "ResourceLimit" [("args", .tup [.str e.name])]) := by
    rw [hget_hset_ne _ (Ne.symm haR), hget_append_lt_list _ hal]; exact ha
  have hRl1 : R < (h ++ [Obj.list [V.str "context_example", V.str "counterexample", V.str "unsat_core",
        V.str "core_necessity_witnesses", V.str "diagram"]]).length := by simp; omega
  rw [execB_cons']
  simp [execS, evalE, evalL, bindS, Env.get_set, hres, herr, updateKw, builtin, hal', fieldGet,
    hget_hset_same _ hRl1]
  simp only [hset_hset_same, execB_nil_eq]
  have FF : FrameS (fun x => x = R) h (hset (h ++ [Obj.list [V.str "context_example", V.str "counterexample",
      V.str "unsat_core", V.str "core_necessity_witnesses", V.str "diagram"]]) R (Obj.dict
        (dictSet Dialect.py (dictSet Dialect.py (dictSet Dialect.py (dictSet Dialect.py (dictSet Dialect.py
          (dictSet Dialect.py (dictSet Dialect.py kvs (V.str "context_example") V.none) (V.str "counterexample")
          V.none) (V.str "unsat_core") V.none) (V.str "core_necessity_witnesses") V.none) (V.str "diagram") V.none)
          (V.str "decision") (V.str "resource_limit")) (V.str "limit_reached") (V.str e.name)))) :=
    (FrameS.append _ _ _).trans (FrameS.hset _ _ rfl)
  refine ⟨_, _, rfl, fun y hy => by simp [Env.get_set, Ne.symm hy], _, hget_hset_same _ hRl1, ?_, FF⟩
  have hk0 := hkv.frame (FF.mono (fun x e => e ▸ hMR))
  simp only [limKT]
  exact ReadsKV.dictSet _ (ReadsM.str _ _ _) _ _ (ReadsKV.dictSet _ (ReadsM.str _ _ _) _ _
    (ReadsKV.dictSet _ (ReadsM.none _ _) _ _ (ReadsKV.dictSet _ (ReadsM.none _ _) _ _
    (ReadsKV.dictSet _ (ReadsM.none _ _) _ _ (ReadsKV.dictSet _ (ReadsM.none _ _) _ _
    (ReadsKV.dictSet _ (ReadsM.none _ _) _ _ hk0))))))

end PCSCR.Py
