import PCSConditionalRuntime.JsInput
import PCSConditionalRuntime.PyCheckPrefix

/-!
# `checkConditional`: options, input clones, limit validation and the `Diagram` constructor
-/

namespace PCSCR.Js

open PCSCR PCSDD PCSOmega PCSCR.Py

def jinitHeap (h0 : Heap) (N L : Nat) : Heap :=
  h0 ++ [.inst "Diagram" (jdiagramFields (initAddrs h0.length N L) Mgr.empty), .list [], .dict [], .dict []]

@[simp] theorem jinitHeap_length (h0 : Heap) (N L : Nat) : (jinitHeap h0 N L).length = h0.length + 4 := by
  simp [jinitHeap]

theorem jinit_mrel {h0 : Heap} {names : List String} {lim : Limits} {N L : Nat} (hlv : lim.valid = true)
    (hN : hget h0 N = some (.list (names.map .str))) (hL : hget h0 L = some (limObj lim)) :
    JMRel names lim (initAddrs h0.length N L) (jinitHeap h0 N L) Mgr.empty := by
  have n1 := hget_lt hN
  have n2 := hget_lt hL
  have e0 : ∀ a, a < h0.length → hget (jinitHeap h0 N L) a = hget h0 a := fun a ha => by
    simp [jinitHeap, hget_append_lt_list _ ha]
  have hS : hget (jinitHeap h0 N L) h0.length =
      some (.inst "Diagram" (jdiagramFields (initAddrs h0.length N L) Mgr.empty)) := by simp [jinitHeap]
  have hs1 : hget (jinitHeap h0 N L) (h0.length + 1) = some (.list []) := by simp [jinitHeap, hget]
  have hs2 : hget (jinitHeap h0 N L) (h0.length + 2) = some (.dict []) := by simp [jinitHeap, hget]
  have hs3 : hget (jinitHeap h0 N L) (h0.length + 3) = some (.dict []) := by simp [jinitHeap, hget]
  refine ⟨hS, by simp only [initAddrs]; rw [e0 N n1]; exact hN,
    ⟨_, by simp only [initAddrs]; rw [e0 L n2]; exact hL, ?_⟩,
    ⟨[], hs1, by simp [NodesRel, Mgr.empty]⟩, ⟨[], hs2, ?_⟩, ⟨[], hs3, ?_⟩, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, hlv⟩
  · simp [JLimRel, dictFind, jkeyEq_str, iv]
  · intro v lo hi
    simp [dictFind, Mgr.empty, findNode]
  · intro op a b
    simp [dictFind, Mgr.empty, memoLookup]
  all_goals simp [Addrs.mut, initAddrs]
  all_goals omega

theorem jinit_call (ext : Ext) (k : Nat) (h0 : Heap) (N L : Nat) :
    (interp (jsCtx ext) (k + 1)).call "Diagram.__init__" [.ref h0.length, .ref N, .ref L]
        (h0 ++ [.inst "Diagram" []]) =
      .ok .undef (jinitHeap h0 N L) := by
  unfold jinitHeap
  rw [interp_succ_call]
  simp only [callBody, show lookupFn (jsCtx ext).prog "Diagram.__init__" = some js_Diagram___init__ from rfl,
    js_Diagram___init__]
  simp only [List.length, List.zip, List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append,
    List.cons_append, ne_eq, not_true, if_false]
  repeat jsstep [pairUp, hget_append_lt_list, hset]
  simp [finishCall, jdiagramFields, initAddrs, iv, Mgr.empty, execB_nil_eq]

/-! ## Contracts of the imported `omega-core.mjs` helpers and of `validateConditional` -/

/-- `validateConditional` accepts (every heap copy of) the task `tj` and returns its argument. -/
def JValidateAccepts (ext : Ext) (tj : T) : Prop :=
  ∀ (h : Heap) (v : V) (fu : Nat), readback fu h v = some tj → ext "validateConditional" [v] h = .ok v h

/-- `exact(x, keys)` returns `x`, without heap effects, when the own keys of the plain object `x`
are the strings of the array `keys` (here: in the same order). -/
def JExactOK (ext : Ext) : Prop :=
  ∀ (h : Heap) (a b : Nat) (kvs : List (V × V)), hget h a = some (.dict kvs) →
    hget h b = some (.list (kvs.map (·.1))) → ext "exact" [.ref a, .ref b] h = .ok (.ref a) h

/-- `integer(x, low, high)` returns `x`, without heap effects, for an integer `low ≤ x ≤ high`. -/
def JIntegerOK (ext : Ext) : Prop :=
  ∀ (h : Heap) (i lo hi : Int), lo ≤ i → i ≤ hi → ext "integer" [.int i, .int lo, .int hi] h = .ok (.int i) h

def jlimBody : List S :=
  [S.expr (E.call "integer" [E.sub (E.var "limits") (E.var "k"), E.lit (V.int 1),
    E.sub (E.var "DEFAULT_LIMITS") (E.var "k")])]

theorem jlimits_loop (ext : Ext) (hint : JIntegerOK ext) (k : Nat) (env : Env) (h : Heap) (LA KA : Nat)
    (lim : Limits) (hval : lim.valid = true) (hL : hget h LA = some (limObj lim))
    (hK : hget h KA = some (.list [.str "nodes", .str "operations"]))
    (h2 : hget h 2 = some (.dict [(.str "nodes", .int 4096), (.str "operations", .int 100000)]))
    (hlv : env.get "limits" = some (.ref LA)) (hdl : env.get "DEFAULT_LIMITS" = none) :
    (interp (jsCtx ext) (k + 3)).forLoop env h (.name "k") (.ref KA) 0 jlimBody =
      .ok (.normal ((env.set "k" (.str "nodes")).set "k" (.str "operations"))) h := by
  simp only [Limits.valid, decide_eq_true_eq] at hval
  obtain ⟨n1, n2, o1, o2⟩ := hval
  simp only [limObj] at hL
  have hdl' : (env.set "k" (.str "nodes")).get "DEFAULT_LIMITS" = none := by simp [hdl]
  have hlv' : (env.set "k" (.str "nodes")).get "limits" = some (.ref LA) := by simp [hlv]
  have e1 := hint h (lim.nodes : Int) 1 4096 (by omega) (by omega)
  have e2 := hint h (lim.operations : Int) 1 100000 (by omega) (by omega)
  have hx : "integer" ∈ jsProg.externs := by decide
  rw [interp_succ_forLoop]
  simp only [forIter, elemAt, hK, bindE, assignT, List.getElem?_cons_zero, jlimBody]
  have hk1 : (env.set "k" (.str "nodes")).get "k" = some (.str "nodes") := by simp
  generalize env.set "k" (.str "nodes") = env1 at hk1 hlv' hdl' ⊢
  jsstep [hlv', hk1, hL, h2, hdl', jsGlobals, dictFind, keyEq, hx, e1]
  simp only [execB_nil_eq, loopK, Nat.zero_add]
  rw [interp_succ_forLoop]
  simp only [forIter, elemAt, hK, bindE, assignT, List.getElem?_cons_zero, List.getElem?_cons_succ]
  have hk2 : (env1.set "k" (.str "operations")).get "k" = some (.str "operations") := by simp
  have hlv2 : (env1.set "k" (.str "operations")).get "limits" = some (.ref LA) := by simp [hlv']
  have hdl2 : (env1.set "k" (.str "operations")).get "DEFAULT_LIMITS" = none := by simp [hdl']
  generalize env1.set "k" (.str "operations") = env2 at hk2 hlv2 hdl2 ⊢
  jsstep [hlv2, hk2, hL, h2, hdl2, jsGlobals, dictFind, keyEq, hx, e2]
  simp only [execB_nil_eq, loopK]
  rw [interp_succ_forLoop]
  simp [forIter, elemAt, hK]

def keysObj : Obj := .list [.str "nodes", .str "operations"]

/-- The heap after the limit clone, the `exact` key array and the `Object.keys` array. -/
def jpreHeap (h1 : Heap) (lim : Limits) : Heap := h1 ++ [limObj lim, keysObj, keysObj]

theorem jcheck_prefix (ext : Ext) (hint : JIntegerOK ext) (hexact : JExactOK ext) (k : Nat)
    (hin h1 : Heap) (V0 VA : V) (O L0 A NL : Nat) (tj : T)
    (lim : Limits) (vkvs : List (V × V)) (d : String)
    (hO : hget hin O = some (.dict [(.str "limits", .ref L0)]))
    (hdeep : readback (hin.length + 1) hin V0 = some tj) (halloc : allocT hin tj = (VA, h1))
    (hval : ext "validateConditional" [VA] h1 = .ok VA h1)
    (hL0 : readback (h1.length + 1) h1 (.ref L0) = some (limT lim)) (hlv : lim.valid = true)
    (hVA : VA = .ref A) (hA : hget h1 A = some (.dict vkvs))
    (hvar : dictFind .js vkvs (.str "variables") = some (.ref NL))
    (h2 : hget h1 2 = some (.dict [(.str "nodes", .int 4096), (.str "operations", .int 100000)]))
    (hdg : ext "digest" [VA] (jinitHeap (jpreHeap h1 lim) NL h1.length) =
      .ok (.str d) (jinitHeap (jpreHeap h1 lim) NL h1.length)) :
    ∃ env, env.get "t" = some VA ∧ env.get "m" = some (.ref (h1.length + 3)) ∧
      env.get "r" = some (.ref (h1.length + 7)) ∧
      execB (jsCtx ext) (interp (jsCtx ext) (k + 4)) [("%opts", .ref O), ("input", V0)] hin
          js_checkConditional.body =
        execB (jsCtx ext) (interp (jsCtx ext) (k + 4)) env
          (jinitHeap (jpreHeap h1 lim) NL h1.length ++ [.dict (resultKVs VA (.ref h1.length) d)])
          (js_checkConditional.body.drop 9) := by
  have hOlt := hget_lt hO
  have xv : "validateConditional" ∈ jsProg.externs := by decide
  have xe : "exact" ∈ jsProg.externs := by decide
  have xd : "digest" ∈ jsProg.externs := by decide
  have hex := hexact (h1 ++ [limObj lim, keysObj]) h1.length (h1.length + 1)
    [(.str "nodes", .int (lim.nodes : Int)), (.str "operations", .int (lim.operations : Int))]
    (by simp [hget, limObj]) (by simp [hget, keysObj])
  simp only [keysObj] at hex
  have hloop := jlimits_loop ext hint (k + 1)
    [("t", VA), ("limits", .ref h1.length), ("%opts", .ref O), ("input", V0)]
    (h1 ++ [limObj lim, .list [.str "nodes", .str "operations"], .list [.str "nodes", .str "operations"]])
    h1.length (h1.length + 2) lim hlv (by simp [hget]) (by simp [hget])
    (by rw [hget_append_lt_list _ (hget_lt h2)]; exact h2) (by simp [Env.get]) (by simp [Env.get])
  rw [show k + 1 + 3 = k + 4 from rfl] at hloop
  simp only [jlimBody, limObj, Env.set, Env.has, Env.replace] at hloop
  have hinit := jinit_call ext (k + 3)
    (h1 ++ [limObj lim, .list [.str "nodes", .str "operations"], .list [.str "nodes", .str "operations"]])
    NL h1.length
  subst hVA
  have hAlt := hget_lt hA
  have hA' : hget (h1 ++ [Obj.dict [(V.str "nodes", V.int ↑lim.nodes), (V.str "operations", V.int ↑lim.operations)],
      Obj.list [V.str "nodes", V.str "operations"], Obj.list [V.str "nodes", V.str "operations"]]) A =
      some (.dict vkvs) := by rw [hget_append_lt_list _ hAlt]; exact hA
  rw [check_body_drop9]
  simp only [js_checkConditional]
  jsstep [hO, dictFind, keyEq]
  jsstep [hO, dictFind, keyEq]
  jsstep []
  jsstep [hdeep, halloc, hval, xv]
  jsstep [hL0, allocT_limT]
  jsstep [hex, xe]
  jsstep [hloop, limObj]
  simp only [List.length_append, List.length_cons, List.length_nil, List.append_assoc, List.cons_append, List.nil_append, limObj] at hinit
  jsstep [hA', hvar, hinit]
  simp only [jpreHeap, keysObj, limObj] at hdg ⊢
  jsstep [hdg, xd, pairUp, jsGlobals, dictSet, keyEq]
  refine ⟨[("r", V.ref (h1.length + 3 + 4)), ("m", V.ref (h1.length + 3)), ("k", V.str "operations"),
    ("t", V.ref A), ("limits", V.ref h1.length), ("%opts", V.ref O), ("input", V0)],
    by simp [Env.get], by simp [Env.get], by simp [Env.get], by simp [resultKVs]; rfl⟩

end PCSCR.Js
