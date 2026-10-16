import PCSConditionalRuntime.JsKeys

/-!
# Proof infrastructure for the JavaScript conditional-checker refinement

The simulation relation `JMRel` between a heap holding a live JavaScript `Diagram` instance and
the reference manager `PCSDD.Mgr`: as for Python (`PCSCR.Py.MRel`), but the unique table and
the memo cache are `Map`s with comma-joined string keys (`jukey`, `jmkey`), the witness counter
field is `witnessSteps`, and `ResourceLimit` instances carry their `message`.  Heap lemmas,
`Addrs`, `Frame` and `NodesRel` are shared with the Python development.
-/

namespace PCSCR.Js

open PCSCR PCSDD PCSOmega PCSCR.Py

def jdiagramFields (D : Addrs) (m : Mgr) : List (String × V) :=
  [("names", .ref D.names), ("limits", .ref D.lim), ("nodes", .ref D.nodes), ("unique", .ref D.uniq),
   ("memo", .ref D.memo), ("operations", iv m.ops), ("visits", iv m.visits),
   ("witnessSteps", iv m.wsteps)]

def JUniqRel (ukv : List (V × V)) (ns : Nodes) : Prop :=
  ∀ v lo hi, dictFind .js ukv (jukey v lo hi) = (findNode ns ⟨v, lo, hi⟩).map (fun i => iv (i + 2))

def JMemoRel (mkv : List (V × V)) (memo : List MemoEntry) : Prop :=
  ∀ op a b, dictFind .js mkv (jmkey op a b) = (memoLookup memo op a b).map iv

def JLimRel (kvs : List (V × V)) (lim : Limits) : Prop :=
  dictFind .js kvs (.str "nodes") = some (iv lim.nodes) ∧
  dictFind .js kvs (.str "operations") = some (iv lim.operations)

/-- **Simulation relation** (JavaScript): the heap holds a `Diagram` instance at `D.self` whose
fields encode the reference manager `m` exactly. -/
structure JMRel (names : List String) (lim : Limits) (D : Addrs) (h : Heap) (m : Mgr) : Prop where
  self : hget h D.self = some (.inst "Diagram" (jdiagramFields D m))
  names : hget h D.names = some (.list (names.map .str))
  limK : ∃ kvs, hget h D.lim = some (.dict kvs) ∧ JLimRel kvs lim
  nodes : ∃ ptrs, hget h D.nodes = some (.list ptrs) ∧ NodesRel D h ptrs m.nodes
  uniq : ∃ ukv, hget h D.uniq = some (.dict ukv) ∧ JUniqRel ukv m.nodes
  memo : ∃ mkv, hget h D.memo = some (.dict mkv) ∧ JMemoRel mkv m.memo
  names_nm : ¬ D.mut D.names
  lim_nm : ¬ D.mut D.lim
  d1 : D.self ≠ D.nodes
  d2 : D.self ≠ D.uniq
  d3 : D.self ≠ D.memo
  d4 : D.nodes ≠ D.uniq
  d5 : D.nodes ≠ D.memo
  d6 : D.uniq ≠ D.memo
  own_lt : ∀ a ∈ D.own, a < h.length
  /-- Valid limits (`1 ≤ nodes ≤ 4096`, `1 ≤ operations ≤ 100000`): all counters and identifiers
  stay exact safe integers. -/
  lv : lim.valid = true

/-! ## Symbolic execution -/

@[simp] theorem jsCtx_dialect (ext : Ext) : (jsCtx ext).dialect = .js := rfl
@[simp] theorem jsCtx_prog (ext : Ext) : (jsCtx ext).prog = jsProg := rfl
@[simp] theorem jsCtx_globals (ext : Ext) : (jsCtx ext).globals = jsGlobals := rfl
@[simp] theorem jsCtx_ext (ext : Ext) : (jsCtx ext).ext = ext := rfl

/-- One statement of symbolic execution (JavaScript dialect). -/
macro "jsstep" "[" ls:Lean.Parser.Tactic.simpLemma,* "]" : tactic => `(tactic| (
  rw [execB_cons']
  conv in execS _ _ _ _ _ => simp [execS, evalE, evalL, Env.get, iv, binOp, eqD, eqJs, num, bindS, bindE,
    truthy, execB, assignAll, assignT, assignTs, Env.set, Env.has, Env.replace, attrOp, subOp, memOp,
    fieldGet, fieldSet, setAttrOp, storeOp, elems, hashable, builtin, builtinMethod, builtinJs,
    builtinMethodJs, jsJoin, jsElemStr, normIdx, safeNum, cmpOp, isBoolV, MAX_SAFE, Int.natCast_inj, hget_append, hget_hset, $ls,*]
  try simp only [seqF_normal, seqF_ret, seqF_raise]))

/-- Step a statement without unfolding nested blocks. -/
macro "jsif" "[" ls:Lean.Parser.Tactic.simpLemma,* "]" : tactic => `(tactic| (
  rw [execB_cons']
  conv in execS _ _ _ _ _ => simp [execS, evalE, evalL, Env.get, iv, binOp, eqD, eqJs, num, bindS, bindE,
    truthy, execB_nil_eq, assignAll, assignT, assignTs, Env.set, Env.has, Env.replace, attrOp, subOp, memOp,
    fieldGet, fieldSet, setAttrOp, storeOp, elems, hashable, builtin, builtinMethod, builtinJs,
    builtinMethodJs, jsJoin, jsElemStr, normIdx, safeNum, cmpOp, isBoolV, MAX_SAFE, Int.natCast_inj, hget_append, hget_hset, $ls,*]))

/-- `jsstep` that also uses every local hypothesis. -/
macro "jsstep!" "[" ls:Lean.Parser.Tactic.simpLemma,* "]" : tactic => `(tactic| (
  rw [execB_cons']
  conv in execS _ _ _ _ _ => simp [*, execS, evalE, evalL, Env.get, iv, binOp, eqD, eqJs, num, bindS, bindE,
    truthy, execB, assignAll, assignT, assignTs, Env.set, Env.has, Env.replace, attrOp, subOp, memOp,
    fieldGet, fieldSet, setAttrOp, storeOp, elems, hashable, builtin, builtinMethod, builtinJs,
    builtinMethodJs, jsJoin, jsElemStr, normIdx, safeNum, cmpOp, isBoolV, MAX_SAFE, Int.natCast_inj, hget_append, hget_hset, $ls,*]
  try simp only [seqF_normal, seqF_ret, seqF_raise]))

/-! ## Simulation of manager-method outcomes -/

/-- JavaScript outcome `o` of a manager method simulates the reference outcome `x`: success
returns the identifier, failure throws a `ResourceLimit` instance whose `message` names the
exhausted budget. -/
def JSimOut (names : List String) (lim : Limits) (D : Addrs) (h : Heap) :
    Except (LimitReached × Mgr) (Nat × Mgr) → Out V → Prop
  | .ok (r, m'), o => ∃ h', o = .ok (iv r) h' ∧ JMRel names lim D h' m' ∧ Frame D h h'
  | .error (e, m'), o => ∃ h' a, o = .exc (.obj (.ref a)) h' ∧
      hget h' a = some (.inst "ResourceLimit" [("message", .str e.name)]) ∧
      JMRel names lim D h' m' ∧ Frame D h h'

theorem JMRel.addrs_lt {names : List String} {lim : Limits} {D : Addrs} {h : Heap} {m : Mgr}
    (hR : JMRel names lim D h m) :
    D.self < h.length ∧ D.names < h.length ∧ D.lim < h.length ∧ D.nodes < h.length ∧
      D.uniq < h.length ∧ D.memo < h.length := by
  obtain ⟨kl, hl, _⟩ := hR.limK
  obtain ⟨p, hp, _⟩ := hR.nodes
  obtain ⟨u, hu, _⟩ := hR.uniq
  obtain ⟨mm, hm, _⟩ := hR.memo
  exact ⟨hget_lt hR.self, hget_lt hR.names, hget_lt hl, hget_lt hp, hget_lt hu, hget_lt hm⟩

theorem JMRel.neqs {names : List String} {lim : Limits} {D : Addrs} {h : Heap} {m : Mgr}
    (hR : JMRel names lim D h m) :
    D.self ≠ D.nodes ∧ D.self ≠ D.uniq ∧ D.self ≠ D.memo ∧ D.nodes ≠ D.uniq ∧ D.nodes ≠ D.memo ∧
    D.uniq ≠ D.memo ∧ D.nodes ≠ D.self ∧ D.uniq ≠ D.self ∧ D.memo ≠ D.self ∧ D.uniq ≠ D.nodes ∧
    D.memo ≠ D.nodes ∧ D.memo ≠ D.uniq ∧
    D.names ≠ D.self ∧ D.names ≠ D.nodes ∧ D.names ≠ D.uniq ∧ D.names ≠ D.memo ∧
    D.self ≠ D.names ∧ D.nodes ≠ D.names ∧ D.uniq ≠ D.names ∧ D.memo ≠ D.names ∧
    D.lim ≠ D.self ∧ D.lim ≠ D.nodes ∧ D.lim ≠ D.uniq ∧ D.lim ≠ D.memo ∧
    D.self ≠ D.lim ∧ D.nodes ≠ D.lim ∧ D.uniq ≠ D.lim ∧ D.memo ≠ D.lim := by
  have a := hR.names_nm; have b := hR.lim_nm
  simp only [Addrs.mut, not_or] at a b
  have := hR.d1; have := hR.d2; have := hR.d3; have := hR.d4; have := hR.d5; have := hR.d6
  omega

theorem JMRel.transport {names : List String} {lim : Limits} {D : Addrs} {h h' : Heap} {m m' : Mgr}
    (hR : JMRel names lim D h m) (hf : Frame D h h')
    (hs : hget h' D.self = some (.inst "Diagram" (jdiagramFields D m')))
    (hn : ∃ ptrs, hget h' D.nodes = some (.list ptrs) ∧ NodesRel D h' ptrs m'.nodes)
    (hu : ∃ ukv, hget h' D.uniq = some (.dict ukv) ∧ JUniqRel ukv m'.nodes)
    (hm : ∃ mkv, hget h' D.memo = some (.dict mkv) ∧ JMemoRel mkv m'.memo) :
    JMRel names lim D h' m' := by
  have hl := hR.addrs_lt
  obtain ⟨kl, hkl, hlr⟩ := hR.limK
  exact ⟨hs, by rw [hf.2 _ hl.2.1 hR.names_nm]; exact hR.names,
    ⟨kl, by rw [hf.2 _ hl.2.2.1 hR.lim_nm]; exact hkl, hlr⟩, hn, hu, hm, hR.names_nm, hR.lim_nm,
    hR.d1, hR.d2, hR.d3, hR.d4, hR.d5, hR.d6, fun a ha => Nat.lt_of_lt_of_le (hR.own_lt a ha) hf.1, hR.lv⟩

theorem JMRel.append {names : List String} {lim : Limits} {D : Addrs} {h : Heap} {m : Mgr}
    (hR : JMRel names lim D h m) (o : Obj) : JMRel names lim D (h ++ [o]) m := by
  have hl := hR.addrs_lt
  have hf := Frame.append D h o
  obtain ⟨p, hp, hpr⟩ := hR.nodes
  obtain ⟨u, hu, hur⟩ := hR.uniq
  obtain ⟨mm, hm, hmr⟩ := hR.memo
  refine hR.transport hf ?_ ⟨p, ?_, hpr.frame hf⟩ ⟨u, ?_, hur⟩ ⟨mm, ?_, hmr⟩
  · rw [hget_append_lt o hl.1]; exact hR.self
  · rw [hget_append_lt o hl.2.2.2.1]; exact hp
  · rw [hget_append_lt o hl.2.2.2.2.1]; exact hu
  · rw [hget_append_lt o hl.2.2.2.2.2]; exact hm

/-- Storing a memo entry keeps the relation with the extended reference memo. -/
theorem JMRel.setMemo {names : List String} {lim : Limits} {D : Addrs} {h : Heap} {m : Mgr}
    (hR : JMRel names lim D h m) {mkv : List (V × V)} (hm : hget h D.memo = some (.dict mkv))
    (hmr : JMemoRel mkv m.memo) (op : BOp) (a b r : Nat) :
    JMRel names lim D (hset h D.memo (.dict (dictSet .js mkv (jmkey op a b) (iv r))))
      { m with memo := ((op, a, b), r) :: m.memo } ∧
    Frame D h (hset h D.memo (.dict (dictSet .js mkv (jmkey op a b) (iv r)))) := by
  have hl := hR.addrs_lt
  have hne := hR.neqs
  have hF : Frame D h (hset h D.memo (.dict (dictSet .js mkv (jmkey op a b) (iv r)))) :=
    Frame.hset _ _ (Or.inr (Or.inr (Or.inr (Or.inl rfl))))
  obtain ⟨p, hp, hpr⟩ := hR.nodes
  obtain ⟨u, hu, hur⟩ := hR.uniq
  refine ⟨hR.transport hF ?_ ⟨p, ?_, hpr.frame hF⟩ ⟨u, ?_, hur⟩
    ⟨dictSet .js mkv (jmkey op a b) (iv r), ?_, ?_⟩, hF⟩
  · simp [hget_hset, hne]; exact hR.self
  · simp [hget_hset, hne]; exact hp
  · simp [hget_hset, hne]; exact hu
  · simp [hget_hset, hl]
  · intro op' a' b'
    rw [jmkey, jmkey, dictFind_js_set, memoLookup_cons]
    by_cases e : (op, a, b) = (op', a', b')
    · simp only [Prod.mk.injEq] at e
      obtain ⟨rfl, rfl, rfl⟩ := e
      simp
    · have e' : ¬ (op.name ++ "," ++ (jsIntStr (a : Int) ++ "," ++ jsIntStr (b : Int)) =
          op'.name ++ "," ++ (jsIntStr (a' : Int) ++ "," ++ jsIntStr (b' : Int))) := by
        intro h'
        obtain ⟨e1, e2, e3⟩ := jmkey_inj (op := op) (op' := op') (a := a) (b := b) (a' := a') (b' := b')
          (by simp only [jmkey, h'])
        exact e (by rw [e1, e2, e3])
      simp only [e', if_false, e]
      exact hmr op' a' b'

theorem JSimOut.frame {names : List String} {lim : Limits} {D : Addrs} {h0 h : Heap}
    {x : Except (LimitReached × Mgr) (Nat × Mgr)} {o : Out V} (hf : Frame D h0 h)
    (hs : JSimOut names lim D h x o) : JSimOut names lim D h0 x o := by
  unfold JSimOut at *
  split at hs
  · obtain ⟨h', e, R, F⟩ := hs; exact ⟨h', e, R, hf.trans F⟩
  · obtain ⟨h', a, e, ha, R, F⟩ := hs; exact ⟨h', a, e, ha, R, hf.trans F⟩

/-! ## Program-table lookups -/

theorem lookup_node : lookupFn jsProg "Diagram.node" = some js_Diagram_node := by rfl
theorem lookup_apply : lookupFn jsProg "Diagram.apply" = some js_Diagram_apply := by rfl
theorem lookup_compile : lookupFn jsProg "Diagram.compile" = some js_Diagram_compile := by rfl
theorem lookup_conjunction : lookupFn jsProg "Diagram.conjunction" = some js_Diagram_conjunction := by rfl
theorem lookup_world : lookupFn jsProg "Diagram.world" = some js_Diagram_world := by rfl
theorem lookup_work : lookupFn jsProg "Diagram.work" = some js_Diagram_work := by rfl
theorem lookup_init : lookupFn jsProg "Diagram.__init__" = some js_Diagram___init__ := by rfl
theorem lookup_evaluate : lookupFn jsProg "evaluateConditional" = some js_evaluateConditional := by rfl
theorem lookup_check : lookupFn jsProg "checkConditional" = some js_checkConditional := by rfl

@[simp] theorem jlookupFn_newError : lookupFn jsProg "%newError" = none := by rfl
@[simp] theorem jlookupFn_Number : lookupFn jsProg "%Number" = none := by rfl
@[simp] theorem jlookupFn_Boolean : lookupFn jsProg "%Boolean" = none := by rfl
@[simp] theorem jlookupFn_min : lookupFn jsProg "%Math.min" = none := by rfl
@[simp] theorem jlookupFn_spread : lookupFn jsProg "%spread" = none := by rfl
@[simp] theorem jlookupFn_keys : lookupFn jsProg "%keys" = none := by rfl
@[simp] theorem jlookupFn_indices : lookupFn jsProg "%indices" = none := by rfl
@[simp] theorem jlookupFn_every : lookupFn jsProg "%every" = none := by rfl
@[simp] theorem jlookupFn_fromEntries : lookupFn jsProg "%fromEntries" = none := by rfl
@[simp] theorem jlookupFn_clone : lookupFn jsProg "%structuredClone" = none := by rfl
@[simp] theorem jlookupFn_Diagram : lookupFn jsProg "Diagram" = none := by rfl
@[simp] theorem jlookupFn_digest : lookupFn jsProg "digest" = none := by rfl
@[simp] theorem jlookupFn_validate : lookupFn jsProg "validateConditional" = none := by rfl
@[simp] theorem jlookupFn_exact : lookupFn jsProg "exact" = none := by rfl
@[simp] theorem jlookupFn_integer : lookupFn jsProg "integer" = none := by rfl
@[simp] theorem jlookupClass_newError : lookupClass jsProg "%newError" = none := by rfl
@[simp] theorem jlookupClass_Number : lookupClass jsProg "%Number" = none := by rfl
@[simp] theorem jlookupClass_Boolean : lookupClass jsProg "%Boolean" = none := by rfl
@[simp] theorem jlookupClass_min : lookupClass jsProg "%Math.min" = none := by rfl
@[simp] theorem jlookupClass_spread : lookupClass jsProg "%spread" = none := by rfl
@[simp] theorem jlookupClass_keys : lookupClass jsProg "%keys" = none := by rfl
@[simp] theorem jlookupClass_indices : lookupClass jsProg "%indices" = none := by rfl
@[simp] theorem jlookupClass_every : lookupClass jsProg "%every" = none := by rfl
@[simp] theorem jlookupClass_fromEntries : lookupClass jsProg "%fromEntries" = none := by rfl
@[simp] theorem jlookupClass_clone : lookupClass jsProg "%structuredClone" = none := by rfl
@[simp] theorem jlookupClass_digest : lookupClass jsProg "digest" = none := by rfl
@[simp] theorem jlookupClass_validate : lookupClass jsProg "validateConditional" = none := by rfl
@[simp] theorem jlookupClass_exact : lookupClass jsProg "exact" = none := by rfl
@[simp] theorem jlookupClass_integer : lookupClass jsProg "integer" = none := by rfl
@[simp] theorem jlookupClass_evaluate : lookupClass jsProg "evaluateConditional" = none := by rfl
@[simp] theorem jlookupClass_Diagram : lookupClass jsProg "Diagram" = some { name := "Diagram", methods := ["__init__", "node", "apply", "compile", "conjunction", "world", "work"], isException := false } := by rfl
@[simp] theorem jexterns_newError : jsProg.externs.contains "%newError" = false := by rfl
@[simp] theorem jexterns_newError_mem : ¬ "%newError" ∈ jsProg.externs := by decide
@[simp] theorem jexterns_Number : jsProg.externs.contains "%Number" = false := by rfl
@[simp] theorem jexterns_Boolean : jsProg.externs.contains "%Boolean" = false := by rfl
@[simp] theorem jexterns_min : jsProg.externs.contains "%Math.min" = false := by rfl
@[simp] theorem jexterns_spread : jsProg.externs.contains "%spread" = false := by rfl
@[simp] theorem jexterns_keys : jsProg.externs.contains "%keys" = false := by rfl
@[simp] theorem jexterns_indices : jsProg.externs.contains "%indices" = false := by rfl
@[simp] theorem jexterns_every : jsProg.externs.contains "%every" = false := by rfl
@[simp] theorem jexterns_fromEntries : jsProg.externs.contains "%fromEntries" = false := by rfl
@[simp] theorem jexterns_clone : jsProg.externs.contains "%structuredClone" = false := by rfl
@[simp] theorem jexterns_digest : jsProg.externs.contains "digest" = true := by rfl
@[simp] theorem jexterns_validate : jsProg.externs.contains "validateConditional" = true := by rfl
@[simp] theorem jexterns_exact : jsProg.externs.contains "exact" = true := by rfl
@[simp] theorem jexterns_integer : jsProg.externs.contains "integer" = true := by rfl
@[simp] theorem jclassHasMethod_node : classHasMethod jsProg "Diagram" "node" = true := by rfl
@[simp] theorem jclassHasMethod_apply : classHasMethod jsProg "Diagram" "apply" = true := by rfl
@[simp] theorem jclassHasMethod_compile : classHasMethod jsProg "Diagram" "compile" = true := by rfl
@[simp] theorem jclassHasMethod_conjunction : classHasMethod jsProg "Diagram" "conjunction" = true := by rfl
@[simp] theorem jclassHasMethod_world : classHasMethod jsProg "Diagram" "world" = true := by rfl
@[simp] theorem jclassHasMethod_work : classHasMethod jsProg "Diagram" "work" = true := by rfl
@[simp] theorem jclassHasMethod_init : classHasMethod jsProg "Diagram" "__init__" = true := by rfl
@[simp] theorem jclassHasMethod_push : classHasMethod jsProg "Diagram" "push" = false := by rfl
@[simp] theorem jclassHasMethod_has : classHasMethod jsProg "Diagram" "has" = false := by rfl
@[simp] theorem jclassHasMethod_get : classHasMethod jsProg "Diagram" "get" = false := by rfl
@[simp] theorem jclassHasMethod_set : classHasMethod jsProg "Diagram" "set" = false := by rfl
@[simp] theorem jclassHasMethod_join : classHasMethod jsProg "Diagram" "join" = false := by rfl
@[simp] theorem jclassHasMethod_slice : classHasMethod jsProg "Diagram" "slice" = false := by rfl
@[simp] theorem jclassHasMethod_indexOf : classHasMethod jsProg "Diagram" "indexOf" = false := by rfl
@[simp] theorem jclassHasMethod_at : classHasMethod jsProg "Diagram" "at" = false := by rfl
@[simp] theorem jisSome_node : (lookupFn jsProg "Diagram.node").isSome = true := by rfl
@[simp] theorem jisSome_apply : (lookupFn jsProg "Diagram.apply").isSome = true := by rfl
@[simp] theorem jisSome_compile : (lookupFn jsProg "Diagram.compile").isSome = true := by rfl
@[simp] theorem jisSome_conjunction : (lookupFn jsProg "Diagram.conjunction").isSome = true := by rfl
@[simp] theorem jisSome_world : (lookupFn jsProg "Diagram.world").isSome = true := by rfl
@[simp] theorem jisSome_work : (lookupFn jsProg "Diagram.work").isSome = true := by rfl
@[simp] theorem jisSome_init : (lookupFn jsProg "Diagram.__init__").isSome = true := by rfl
@[simp] theorem jisSome_evaluate : (lookupFn jsProg "evaluateConditional").isSome = true := by rfl
@[simp] theorem jisSome_check : (lookupFn jsProg "checkConditional").isSome = true := by rfl

end PCSCR.Js
