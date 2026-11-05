import PCSConditionalRuntime.PyAlloc

/-!
# `check`: input copies, limit validation and the `Diagram` constructor
-/

namespace PCSCR.Py

open PCSCR PCSDD PCSOmega

def limObj (lim : Limits) : Obj :=
  .dict [(.str "nodes", .int (lim.nodes : Int)), (.str "operations", .int (lim.operations : Int))]

theorem allocT_limT (h : Heap) (lim : Limits) :
    allocT h (limT lim) = (.ref h.length, h ++ [limObj lim]) := by
  simp [allocT, limT, allocKV, limObj]

theorem exact_limits (ext : Ext) (k : Nat) (h : Heap) (LA : Nat) (lim : Limits)
    (hL : hget h LA = some (limObj lim)) :
    (interp (pyCtx ext) (k + 1)).call "exact" [.ref LA, mkSet [.str "nodes", .str "operations"]] h =
      .ok (.ref LA) h := by
  rw [interp_succ_call]
  simp only [callBody, show lookupFn (pyCtx ext).prog "exact" = some py_exact from rfl, py_exact]
  simp only [List.length, List.zip, List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append,
    List.cons_append, ne_eq, not_true, if_false]
  simp only [limObj] at hL
  pystep [hL, typeName, mkSet, dedup, memPy, subsetPrim, memPrim, eqPrim]
  pystep []
  simp [finishCall]

def limBody : List S :=
  [S.ifte
    (E.or (E.typeIs (E.sub (E.var "limits") (E.var "field")) "int" true)
      (E.not (E.cmp2 BinOp.le BinOp.le (E.lit (V.int 1)) (E.sub (E.var "limits") (E.var "field"))
        (E.sub (E.var "DEFAULT_LIMITS") (E.var "field")))))
    [S.raise (E.call "ValueError" [E.lit (V.str "Invalid symbolic work limit")])] []]

theorem limits_loop (ext : Ext) (k : Nat) (env : Env) (h : Heap) (LA : Nat) (lim : Limits)
    (hval : lim.valid = true) (hL : hget h LA = some (limObj lim))
    (h0 : hget h 0 = some (.dict [(.str "nodes", .int 4096), (.str "operations", .int 100000)]))
    (hlv : env.get "limits" = some (.ref LA)) (hdl : env.get "DEFAULT_LIMITS" = none) :
    (interp (pyCtx ext) (k + 3)).forLoop env h (.name "field") (.ref LA) 0 limBody =
      .ok (.normal ((env.set "field" (.str "nodes")).set "field" (.str "operations"))) h := by
  simp only [Limits.valid, decide_eq_true_eq] at hval
  obtain ⟨n1, n2, o1, o2⟩ := hval
  simp only [limObj] at hL
  have hdl' : (env.set "field" (.str "nodes")).get "DEFAULT_LIMITS" = none := by simp [hdl]
  have hlv' : (env.set "field" (.str "nodes")).get "limits" = some (.ref LA) := by simp [hlv]
  rw [interp_succ_forLoop]
  simp only [forIter, elemAt, hL, List.map, bindE, assignT, List.getElem?_cons_zero,
    List.getElem?_cons_succ, limBody]
  have n1' : (1 : Int) ≤ (lim.nodes : Int) := by omega
  have n2' : (lim.nodes : Int) ≤ 4096 := by omega
  have o1' : (1 : Int) ≤ (lim.operations : Int) := by omega
  have o2' : (lim.operations : Int) ≤ 100000 := by omega
  pystepA [hlv, hL, h0, hdl, typeName, pyGlobals, n1', n2', o1', o2', dictFind, keyEq, eqPrim, Env.get]
  simp only [execB_nil_eq, loopK, Nat.zero_add]
  rw [interp_succ_forLoop]
  simp only [forIter, elemAt, hL, List.map, bindE, assignT, List.getElem?_cons_zero,
    List.getElem?_cons_succ]
  pystepA [hlv', hL, h0, hdl', typeName, pyGlobals, n1', n2', o1', o2', dictFind, keyEq, eqPrim, Env.get]
  simp only [execB_nil_eq, loopK]
  rw [interp_succ_forLoop]
  simp [forIter, elemAt, hL]


/-- The addresses of a freshly constructed `Diagram` at `S` (its three containers follow). -/
def initAddrs (S N L : Nat) : Addrs := ⟨S, N, L, S + 1, S + 2, S + 3, []⟩

@[simp] theorem hget_append_cons_len (h : Heap) (o : Obj) (l : List Obj) :
    hget (h ++ o :: l) h.length = some o := by simp [hget]

def initHeap (h0 : Heap) (N L : Nat) : Heap :=
  h0 ++ [.inst "Diagram" (diagramFields (initAddrs h0.length N L) Mgr.empty), .list [], .dict [], .dict []]

@[simp] theorem initHeap_length (h0 : Heap) (N L : Nat) : (initHeap h0 N L).length = h0.length + 4 := by
  simp [initHeap]

theorem init_mrel {h0 : Heap} {names : List String} {lim : Limits} {N L : Nat}
    (hN : hget h0 N = some (.list (names.map .str))) (hL : hget h0 L = some (limObj lim)) :
    MRel names lim (initAddrs h0.length N L) (initHeap h0 N L) Mgr.empty := by
  have n1 := hget_lt hN
  have n2 := hget_lt hL
  have e0 : ∀ a, a < h0.length → hget (initHeap h0 N L) a = hget h0 a := fun a ha => by
    simp [initHeap, hget_append_lt_list _ ha]
  have hS : hget (initHeap h0 N L) h0.length =
      some (.inst "Diagram" (diagramFields (initAddrs h0.length N L) Mgr.empty)) := by simp [initHeap]
  have hs1 : hget (initHeap h0 N L) (h0.length + 1) = some (.list []) := by simp [initHeap, hget]
  have hs2 : hget (initHeap h0 N L) (h0.length + 2) = some (.dict []) := by simp [initHeap, hget]
  have hs3 : hget (initHeap h0 N L) (h0.length + 3) = some (.dict []) := by simp [initHeap, hget]
  refine ⟨hS, by simp only [initAddrs]; rw [e0 N n1]; exact hN,
    ⟨_, by simp only [initAddrs]; rw [e0 L n2]; exact hL, ?_⟩,
    ⟨[], hs1, by simp [NodesRel, Mgr.empty]⟩, ⟨[], hs2, ?_⟩, ⟨[], hs3, ?_⟩, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_⟩
  · simp [LimRel, dictFind, keyEq_str, iv]
  · refine ⟨fun _ h => by simp at h, fun v lo hi => ?_⟩
    simp [dictFind, Mgr.empty, findNode]
  · refine ⟨fun _ h => by simp at h, fun op a b => ?_⟩
    simp [dictFind, Mgr.empty, memoLookup]
  all_goals simp [Addrs.mut, initAddrs]
  all_goals omega

theorem init_call (ext : Ext) (k : Nat) (h0 : Heap) (N L : Nat) :
    (interp (pyCtx ext) (k + 1)).call "Diagram.__init__" [.ref h0.length, .ref N, .ref L]
        (h0 ++ [.inst "Diagram" []]) =
      .ok .none (initHeap h0 N L) := by
  unfold initHeap
  rw [interp_succ_call]
  simp only [callBody, show lookupFn (pyCtx ext).prog "Diagram.__init__" = some py_Diagram___init__ from rfl,
    py_Diagram___init__]
  simp only [List.length, List.zip, List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append,
    List.cons_append, ne_eq, not_true, if_false]
  pystep []
  pystep [pairUp, hget_append_lt_list, hset]
  pystep [hget_append_lt_list, hset]
  simp [finishCall, diagramFields, initAddrs, iv, Mgr.empty, hset, execB_nil_eq, Nat.add_assoc]


/-- Initial contents of the result dictionary. -/
def resultKVs (VA LA : V) (d : String) : List (V × V) :=
  [(.str "format", .str "pcs-conditional-boolean-receipt-v1"), (.str "checker", .str "pcs-conditional-bdd/1"),
   (.str "original_task", VA), (.str "task_sha256", .str d), (.str "limits", LA), (.str "decision", .none),
   (.str "context_example", .none), (.str "counterexample", .none), (.str "unsat_core", .none),
   (.str "core_necessity_witnesses", .none), (.str "diagram", .none), (.str "limit_reached", .none),
   (.str "scope", .str "Declared Boolean interpretations and explicit assumptions only"),
   (.str "pcs_authority", .bool false), (.str "lean_kernel_checked", .bool false)]

/-- The local store after the prefix of `check`. -/
def prefixEnv (L0 : Nat) (V0 VA : V) (LA : Nat) : Env :=
  Env.set (Env.set (Env.set (Env.set (Env.set (Env.set [("limits", .ref L0), ("value", V0)]
    "value" VA) "limits" (.ref LA)) "field" (.str "nodes")) "field" (.str "operations"))
    "manager" (.ref (LA + 1))) "result" (.ref (LA + 5))

theorem check_prefix (ext : Ext) (k : Nat) (hin h1 : Heap) (V0 VA : V) (L0 A NL : Nat) (tj : T)
    (lim : Limits) (names : List String) (vkvs : List (V × V)) (d : String)
    (hdeep : readback (hin.length + 1) hin V0 = some tj) (halloc : allocT hin tj = (VA, h1))
    (hval : ext "validate" [VA] h1 = .ok VA h1)
    (hL0 : readback (h1.length + 1) h1 (.ref L0) = some (limT lim)) (hlv : lim.valid = true)
    (hVA : VA = .ref A) (hA : hget h1 A = some (.dict vkvs))
    (hvar : dictFind .py vkvs (.str "variables") = some (.ref NL))
    (h0 : hget h1 0 = some (.dict [(.str "nodes", .int 4096), (.str "operations", .int 100000)]))
    (hdg : ext "digest" [VA] (initHeap (h1 ++ [limObj lim]) NL h1.length) =
      .ok (.str d) (initHeap (h1 ++ [limObj lim]) NL h1.length)) :
    execB (pyCtx ext) (interp (pyCtx ext) (k + 4)) [("limits", .ref L0), ("value", V0)] hin py_check.body =
      execB (pyCtx ext) (interp (pyCtx ext) (k + 4))
        (prefixEnv L0 V0 VA h1.length)
        (initHeap (h1 ++ [limObj lim]) NL h1.length ++
          [.dict (resultKVs VA (.ref h1.length) d)])
        (py_check.body.drop 6) := by
  have hex := exact_limits ext (k + 3) (h1 ++ [limObj lim]) h1.length lim (by simp)
  have hloop := limits_loop ext (k + 1) [("limits", .ref h1.length), ("value", VA)]
    (h1 ++ [limObj lim]) h1.length lim hlv (by simp)
    (by rw [hget_append_lt _ (hget_lt h0)]; exact h0) (by simp [Env.get]) (by simp [Env.get])
  rw [show k + 1 + 3 = k + 4 from rfl] at hloop
  simp only [limBody, Env.set, Env.has, Env.replace] at hloop
  have hinit := init_call ext (k + 3) (h1 ++ [limObj lim]) NL h1.length
  simp only [py_check, List.drop]
  pystep [hdeep, halloc, hval]
  pystep [hL0, allocT_limT, isNoneV]
  pystep [hex]
  pystep [hloop]
  subst hVA
  have hAlt := hget_lt hA
  simp only [List.length_append, List.length_singleton, List.append_assoc, List.singleton_append] at hinit
  pystep [hA, hAlt, hvar, hinit]
  pystep [hdg, pairUp, pyGlobals, dictSet, keyEq, eqPy]
  simp [prefixEnv, resultKVs, Env.set, Env.has, Env.replace]
  done


end PCSCR.Py
