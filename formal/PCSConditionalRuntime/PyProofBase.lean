import PCSConditionalRuntime.PyRun
import PCSDecisionDiagram.Conditional

/-!
# Proof infrastructure for the Python conditional-checker refinement

Heap lemmas, program-table lookups, dictionary lemmas for well-shaped keys, and the
simulation relation `MRel` between a heap holding a live `Diagram` instance and the reference
manager state `PCSDD.Mgr`.
-/

namespace PCSCR.Py

open PCSCR PCSDD PCSOmega

/-! ## Heap lemmas -/

@[simp] theorem hget_append_lt {h : Heap} {a : Nat} (o : Obj) (ha : a < h.length) :
    hget (h ++ [o]) a = hget h a := by
  simp [hget, List.getElem?_append_left ha]

@[simp] theorem hget_append_self (h : Heap) (o : Obj) : hget (h ++ [o]) h.length = some o := by
  simp [hget]

theorem hget_append (h : Heap) (o : Obj) (a : Nat) :
    hget (h ++ [o]) a = if a < h.length then hget h a else if a = h.length then some o else none := by
  unfold hget
  by_cases h1 : a < h.length
  · simp [h1, List.getElem?_append_left h1]
  · by_cases h2 : a = h.length
    · subst h2; simp
    · simp [h1, h2, List.getElem?_append_right (Nat.le_of_not_lt h1)]
      intro h3; omega

theorem hget_lt {h : Heap} {a : Nat} {o : Obj} (hg : hget h a = some o) : a < h.length := by
  unfold hget at hg
  exact (List.getElem?_eq_some_iff.1 hg).1

@[simp] theorem hget_hset_same {h : Heap} {a : Nat} (o : Obj) (ha : a < h.length) :
    hget (hset h a o) a = some o := by
  simp [hget, hset, ha]

@[simp] theorem hget_hset_ne {h : Heap} {a b : Nat} (o : Obj) (hab : a ≠ b) :
    hget (hset h a o) b = hget h b := by
  simp [hget, hset, hab]

theorem hget_hset (h : Heap) (a b : Nat) (o : Obj) :
    hget (hset h a o) b = if a = b then (if a < h.length then some o else none) else hget h b := by
  by_cases e : a = b
  · subst e
    by_cases hl : a < h.length
    · simp [hget, hset, hl]
    · simp [hget, hset, hl]
  · simp [hget, hset, e]

@[simp] theorem length_hset (h : Heap) (a : Nat) (o : Obj) : (hset h a o).length = h.length := by
  simp [hset]

/-! ## Well-shaped dictionary keys (tuples of strings / integers) -/

def primSI : V → Bool
  | .str _ => true
  | .int _ => true
  | _ => false

/-- A dictionary key that is a tuple of strings and integers. -/
def KeyOK : V → Prop
  | .tup xs => ∀ x ∈ xs, primSI x = true
  | _ => False

theorem eqPy_prim : ∀ {a b : V}, primSI a = true → primSI b = true → eqPy a b = some (decide (a = b))
  | .str x, .str y, _, _ => by by_cases e : x = y <;> simp [eqPy, e]
  | .int x, .int y, _, _ => by by_cases e : x = y <;> simp [eqPy, num, e]
  | .str x, .int y, _, _ => by simp [eqPy, num]
  | .int x, .str y, _, _ => by simp [eqPy, num]

theorem eqPyL_prim : ∀ {xs ys : List V}, (∀ x ∈ xs, primSI x = true) → (∀ y ∈ ys, primSI y = true) →
    eqPyL xs ys = some (decide (xs = ys))
  | [], [], _, _ => by simp [eqPyL]
  | [], _ :: _, _, _ => by simp [eqPyL]
  | _ :: _, [], _, _ => by simp [eqPyL]
  | x :: xs, y :: ys, hx, hy => by
      simp only [eqPyL]
      rw [eqPy_prim (hx x (by simp)) (hy y (by simp)),
        eqPyL_prim (fun z hz => hx z (by simp [hz])) (fun z hz => hy z (by simp [hz]))]
      by_cases h1 : x = y <;> by_cases h2 : xs = ys <;> simp [h1, h2]

theorem keyEq_ok {a b : V} (ha : KeyOK a) (hb : KeyOK b) : keyEq .py a b = decide (a = b) := by
  match a, b, ha, hb with
  | .tup xs, .tup ys, ha, hb =>
    simp only [keyEq, eqD, eqPy]
    rw [eqPyL_prim ha hb]
    by_cases h : xs = ys <;> simp [h]

/-- All keys of an association list are well shaped. -/
def KeysOK (kvs : List (V × V)) : Prop := ∀ p ∈ kvs, KeyOK p.1

theorem dictFind_set {kvs : List (V × V)} (hk : KeysOK kvs) {k x : V} (hkk : KeyOK k) (hx : KeyOK x)
    (v : V) : dictFind .py (dictSet .py kvs k v) x = if k = x then some v else dictFind .py kvs x := by
  induction kvs with
  | nil => simp [dictSet, dictFind, keyEq_ok hkk hx]
  | cons p rest ih =>
    obtain ⟨k', v'⟩ := p
    have hk' : KeyOK k' := hk (k', v') (by simp)
    have hr : KeysOK rest := fun q hq => hk q (by simp [hq])
    simp only [dictSet, keyEq_ok hk' hkk]
    by_cases e : k' = k
    · subst e
      by_cases e2 : k' = x
      · subst e2; simp [dictFind, keyEq_ok hk' hk']
      · simp [dictFind, keyEq_ok hk' hx, e2]
    · simp only [e, decide_false, Bool.false_eq_true, if_false, dictFind, keyEq_ok hk' hx]
      rw [ih hr]
      by_cases e2 : k' = x
      · subst e2; simp [Ne.symm e]
      · simp [e2]

theorem keysOK_set {kvs : List (V × V)} (hk : KeysOK kvs) {k : V} (hkk : KeyOK k) (v : V) :
    KeysOK (dictSet .py kvs k v) := by
  induction kvs with
  | nil => simp [dictSet, KeysOK, hkk]
  | cons p rest ih =>
    obtain ⟨k', v'⟩ := p
    have hk' : KeyOK k' := hk (k', v') (by simp)
    have hr : KeysOK rest := fun q hq => hk q (by simp [hq])
    simp only [dictSet]
    split
    · intro q hq; simp at hq; rcases hq with rfl | hq
      · exact hk'
      · exact hr q hq
    · intro q hq; simp at hq; rcases hq with rfl | hq
      · exact hk'
      · exact ih hr q hq

/-! ## Encodings of reference data -/

def _root_.PCSDD.BOp.name : BOp → String
  | .and => "and"
  | .or => "or"
  | .xor => "xor"

def _root_.PCSDD.LimitReached.name : LimitReached → String
  | .nodes => "nodes"
  | .operations => "operations"

def iv (x : Nat) : V := .int (x : Int)

/-- Unique-table key `(var, low, high)`. -/
def ukey (v lo hi : Nat) : V := .tup [iv v, iv lo, iv hi]

/-- Memo key `(op, a, b)`. -/
def mkey (op : BOp) (a b : Nat) : V := .tup [.str op.name, iv a, iv b]

theorem ukey_ok (v lo hi : Nat) : KeyOK (ukey v lo hi) := by simp [KeyOK, ukey, iv, primSI]
theorem mkey_ok (op : BOp) (a b : Nat) : KeyOK (mkey op a b) := by simp [KeyOK, mkey, iv, primSI]

/-- The heap addresses of a live `Diagram`. -/
structure Addrs where
  self : Nat
  names : Nat
  lim : Nat
  nodes : Nat
  uniq : Nat
  memo : Nat
  /-- Further addresses owned (and possibly overwritten) by the caller of the methods. -/
  own : List Nat := []
  deriving DecidableEq, Repr

/-- The addresses that may be overwritten while the relation is maintained: the mutable
`Diagram` objects and the caller-owned addresses. -/
def Addrs.mut (D : Addrs) (a : Nat) : Prop :=
  a = D.self ∨ a = D.nodes ∨ a = D.uniq ∨ a = D.memo ∨ a ∈ D.own

def diagramFields (D : Addrs) (m : Mgr) : List (String × V) :=
  [("names", .ref D.names), ("limits", .ref D.lim), ("nodes", .ref D.nodes), ("unique", .ref D.uniq),
   ("memo", .ref D.memo), ("operations", iv m.ops), ("visits", iv m.visits),
   ("witness_steps", iv m.wsteps)]

/-- Node pointer list: pointer `i` names an immutable list `[var, low, high]`. -/
def NodesRel (D : Addrs) (h : Heap) (ptrs : List V) (ns : Nodes) : Prop :=
  ptrs.length = ns.size ∧ ∀ i (hi : i < ns.size), ∃ b, ptrs[i]? = some (.ref b) ∧ ¬ D.mut b ∧
    hget h b = some (.list [iv ns[i].var, iv ns[i].low, iv ns[i].high])

def UniqRel (ukv : List (V × V)) (ns : Nodes) : Prop :=
  KeysOK ukv ∧ ∀ v lo hi, dictFind .py ukv (ukey v lo hi) = (findNode ns ⟨v, lo, hi⟩).map (fun i => iv (i + 2))

def MemoRel (mkv : List (V × V)) (memo : List MemoEntry) : Prop :=
  KeysOK mkv ∧ ∀ op a b, dictFind .py mkv (mkey op a b) = (memoLookup memo op a b).map iv

def LimRel (kvs : List (V × V)) (lim : Limits) : Prop :=
  dictFind .py kvs (.str "nodes") = some (iv lim.nodes) ∧
  dictFind .py kvs (.str "operations") = some (iv lim.operations)

/-- **Simulation relation**: the heap holds a `Diagram` instance at `D.self` whose fields
encode the reference manager `m` exactly (node table, unique table, memo table, counters). -/
structure MRel (names : List String) (lim : Limits) (D : Addrs) (h : Heap) (m : Mgr) : Prop where
  self : hget h D.self = some (.inst "Diagram" (diagramFields D m))
  names : hget h D.names = some (.list (names.map .str))
  limK : ∃ kvs, hget h D.lim = some (.dict kvs) ∧ LimRel kvs lim
  nodes : ∃ ptrs, hget h D.nodes = some (.list ptrs) ∧ NodesRel D h ptrs m.nodes
  uniq : ∃ ukv, hget h D.uniq = some (.dict ukv) ∧ UniqRel ukv m.nodes
  memo : ∃ mkv, hget h D.memo = some (.dict mkv) ∧ MemoRel mkv m.memo
  names_nm : ¬ D.mut D.names
  lim_nm : ¬ D.mut D.lim
  d1 : D.self ≠ D.nodes
  d2 : D.self ≠ D.uniq
  d3 : D.self ≠ D.memo
  d4 : D.nodes ≠ D.uniq
  d5 : D.nodes ≠ D.memo
  d6 : D.uniq ≠ D.memo
  own_lt : ∀ a ∈ D.own, a < h.length

/-- Heap evolution allowed to `Diagram` methods: growth, and changes only at mutable
addresses. -/
def Frame (D : Addrs) (h h' : Heap) : Prop :=
  h.length ≤ h'.length ∧ ∀ a, a < h.length → ¬ D.mut a → hget h' a = hget h a

theorem Frame.refl (D : Addrs) (h : Heap) : Frame D h h := ⟨Nat.le_refl _, fun _ _ _ => rfl⟩

theorem Frame.trans {D : Addrs} {h1 h2 h3 : Heap} (a : Frame D h1 h2) (b : Frame D h2 h3) :
    Frame D h1 h3 :=
  ⟨Nat.le_trans a.1 b.1, fun x hx hm => by rw [b.2 x (by have := a.1; omega) hm, a.2 x hx hm]⟩

theorem Frame.append (D : Addrs) (h : Heap) (o : Obj) : Frame D h (h ++ [o]) :=
  ⟨by simp, fun a ha _ => hget_append_lt o ha⟩

theorem Frame.hset {D : Addrs} (h : Heap) {a : Nat} (o : Obj) (ha : D.mut a) : Frame D h (hset h a o) :=
  ⟨by simp, fun b _ hb => hget_hset_ne o (fun e => hb (e ▸ ha))⟩


/-! ## Symbolic execution helpers -/

theorem execB_cons' (c : Ctx) (r : Lvl) (env : Env) (h : Heap) (s : S) (ss : List S) :
    execB c r env h (s :: ss) = seqF (execS c r env h s) (fun env' h' => execB c r env' h' ss) := rfl
@[simp] theorem seqF_normal (e : Env) (h : Heap) (k : Env → Heap → Out Flow) :
    seqF (.ok (.normal e) h) k = k e h := rfl
@[simp] theorem seqF_ret (v : V) (h : Heap) (k : Env → Heap → Out Flow) :
    seqF (.ok (.ret v) h) k = .ok (.ret v) h := rfl
@[simp] theorem seqF_raise (e : Exc) (env : Env) (h : Heap) (k : Env → Heap → Out Flow) :
    seqF (.ok (.raise e env) h) k = .ok (.raise e env) h := rfl
@[simp] theorem pyCtx_dialect (ext : Ext) : (pyCtx ext).dialect = .py := rfl
@[simp] theorem pyCtx_prog (ext : Ext) : (pyCtx ext).prog = pyProg := rfl
@[simp] theorem pyCtx_globals (ext : Ext) : (pyCtx ext).globals = pyGlobals := rfl
@[simp] theorem pyCtx_ext (ext : Ext) : (pyCtx ext).ext = ext := rfl

/-- One statement of symbolic execution: unfold the head statement of a block, simplify it to
its outcome, and continue with the rest of the block when it completed normally. -/
macro "pystep" "[" ls:Lean.Parser.Tactic.simpLemma,* "]" : tactic => `(tactic| (
  rw [execB_cons']
  conv in execS _ _ _ _ _ => simp [execS, evalE, evalL, Env.get, iv, binOp, eqD, eqPy, num, bindS, bindE,
    truthy, execB, assignAll, assignT, assignTs, Env.set, Env.has, Env.replace, attrOp, subOp, memOp,
    fieldGet, fieldSet, setAttrOp, storeOp, elems, hashable, builtin, builtinMethod, normIdx, safeNum,
    cmpOp, Int.natCast_inj, hget_append, hget_hset, $ls,*]
  try simp only [seqF_normal, seqF_ret, seqF_raise]))

theorem execB_nil_eq (c : Ctx) (r : Lvl) (env : Env) (h : Heap) : execB c r env h [] = .ok (.normal env) h := rfl

/-- Step a statement *without* unfolding nested blocks (used for `if` statements whose branches
contain calls: the chosen branch is then executed statement by statement). -/
macro "pyif" "[" ls:Lean.Parser.Tactic.simpLemma,* "]" : tactic => `(tactic| (
  rw [execB_cons']
  conv in execS _ _ _ _ _ => simp [execS, evalE, evalL, Env.get, iv, binOp, eqD, eqPy, num, bindS, bindE,
    truthy, execB_nil_eq, assignAll, assignT, assignTs, Env.set, Env.has, Env.replace, attrOp, subOp, memOp,
    fieldGet, fieldSet, setAttrOp, storeOp, elems, hashable, builtin, builtinMethod, normIdx, safeNum,
    cmpOp, Int.natCast_inj, hget_append, hget_hset, $ls,*]))

/-- `pystep` that also uses every local hypothesis. -/
macro "pystep!" "[" ls:Lean.Parser.Tactic.simpLemma,* "]" : tactic => `(tactic| (
  rw [execB_cons']
  conv in execS _ _ _ _ _ => simp [*, execS, evalE, evalL, Env.get, iv, binOp, eqD, eqPy, num, bindS, bindE,
    truthy, execB, assignAll, assignT, assignTs, Env.set, Env.has, Env.replace, attrOp, subOp, memOp,
    fieldGet, fieldSet, setAttrOp, storeOp, elems, hashable, builtin, builtinMethod, normIdx, safeNum,
    cmpOp, Int.natCast_inj, hget_append, hget_hset, $ls,*]
  try simp only [seqF_normal, seqF_ret, seqF_raise]))

/-! ## Simulation of manager-method outcomes -/

/-- Python outcome `o` of a manager method simulates the reference outcome `x`: success returns
the identifier, failure raises a `ResourceLimit(e)` instance; in both cases the final heap
relates to the final reference manager and only mutable addresses changed. -/
def SimOut (names : List String) (lim : Limits) (D : Addrs) (h : Heap) :
    Except (LimitReached × Mgr) (Nat × Mgr) → Out V → Prop
  | .ok (r, m'), o => ∃ h', o = .ok (iv r) h' ∧ MRel names lim D h' m' ∧ Frame D h h'
  | .error (e, m'), o => ∃ h' a, o = .exc (.obj (.ref a)) h' ∧
      hget h' a = some (.inst "ResourceLimit" [("args", .tup [.str e.name])]) ∧
      MRel names lim D h' m' ∧ Frame D h h'

theorem NodesRel.frame {D : Addrs} {h h' : Heap} {ptrs : List V} {ns : Nodes}
    (hn : NodesRel D h ptrs ns) (hf : Frame D h h') : NodesRel D h' ptrs ns := by
  refine ⟨hn.1, fun i hi => ?_⟩
  obtain ⟨b, hb, hm, hg⟩ := hn.2 i hi
  exact ⟨b, hb, hm, by rw [hf.2 b (hget_lt hg) hm]; exact hg⟩

theorem MRel.addrs_lt {names : List String} {lim : Limits} {D : Addrs} {h : Heap} {m : Mgr}
    (hR : MRel names lim D h m) :
    D.self < h.length ∧ D.names < h.length ∧ D.lim < h.length ∧ D.nodes < h.length ∧
      D.uniq < h.length ∧ D.memo < h.length := by
  obtain ⟨kl, hl, _⟩ := hR.limK
  obtain ⟨p, hp, _⟩ := hR.nodes
  obtain ⟨u, hu, _⟩ := hR.uniq
  obtain ⟨mm, hm, _⟩ := hR.memo
  exact ⟨hget_lt hR.self, hget_lt hR.names, hget_lt hl, hget_lt hp, hget_lt hu, hget_lt hm⟩

/-- All pairwise distinctness facts between the four mutable addresses (both orientations), and
the read-only addresses are not mutable. -/
theorem MRel.neqs {names : List String} {lim : Limits} {D : Addrs} {h : Heap} {m : Mgr}
    (hR : MRel names lim D h m) :
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

/-- Rebuild the relation after a frame step from the four mutable objects. -/
theorem MRel.transport {names : List String} {lim : Limits} {D : Addrs} {h h' : Heap} {m m' : Mgr}
    (hR : MRel names lim D h m) (hf : Frame D h h')
    (hs : hget h' D.self = some (.inst "Diagram" (diagramFields D m')))
    (hn : ∃ ptrs, hget h' D.nodes = some (.list ptrs) ∧ NodesRel D h' ptrs m'.nodes)
    (hu : ∃ ukv, hget h' D.uniq = some (.dict ukv) ∧ UniqRel ukv m'.nodes)
    (hm : ∃ mkv, hget h' D.memo = some (.dict mkv) ∧ MemoRel mkv m'.memo) :
    MRel names lim D h' m' := by
  have hl := hR.addrs_lt
  obtain ⟨kl, hkl, hlr⟩ := hR.limK
  exact ⟨hs, by rw [hf.2 _ hl.2.1 hR.names_nm]; exact hR.names,
    ⟨kl, by rw [hf.2 _ hl.2.2.1 hR.lim_nm]; exact hkl, hlr⟩, hn, hu, hm, hR.names_nm, hR.lim_nm,
    hR.d1, hR.d2, hR.d3, hR.d4, hR.d5, hR.d6, fun a ha => Nat.lt_of_lt_of_le (hR.own_lt a ha) hf.1⟩

theorem MRel.append {names : List String} {lim : Limits} {D : Addrs} {h : Heap} {m : Mgr}
    (hR : MRel names lim D h m) (o : Obj) : MRel names lim D (h ++ [o]) m := by
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

theorem BOp.name_inj {a b : BOp} (h : a.name = b.name) : a = b := by
  cases a <;> cases b <;> first | rfl | (simp [BOp.name] at h)

theorem memoLookup_cons (e : MemoEntry) (memo : List MemoEntry) (op : BOp) (a b : Nat) :
    memoLookup (e :: memo) op a b = if e.1 = (op, a, b) then some e.2 else memoLookup memo op a b := by
  unfold memoLookup
  by_cases h : e.1 = (op, a, b) <;> simp [List.find?_cons, h]

/-- Storing a memo entry keeps the relation with the extended reference memo. -/
theorem MRel.setMemo {names : List String} {lim : Limits} {D : Addrs} {h : Heap} {m : Mgr}
    (hR : MRel names lim D h m) {mkv : List (V × V)} (hm : hget h D.memo = some (.dict mkv))
    (hmr : MemoRel mkv m.memo) (op : BOp) (a b r : Nat) :
    MRel names lim D (hset h D.memo (.dict (dictSet .py mkv (mkey op a b) (iv r))))
      { m with memo := ((op, a, b), r) :: m.memo } ∧
    Frame D h (hset h D.memo (.dict (dictSet .py mkv (mkey op a b) (iv r)))) := by
  have hl := hR.addrs_lt
  have hne := hR.neqs
  have hF : Frame D h (hset h D.memo (.dict (dictSet .py mkv (mkey op a b) (iv r)))) :=
    Frame.hset _ _ (Or.inr (Or.inr (Or.inr (Or.inl rfl))))
  obtain ⟨p, hp, hpr⟩ := hR.nodes
  obtain ⟨u, hu, hur⟩ := hR.uniq
  refine ⟨hR.transport hF ?_ ⟨p, ?_, hpr.frame hF⟩ ⟨u, ?_, hur⟩
    ⟨dictSet .py mkv (mkey op a b) (iv r), ?_, ?_⟩, hF⟩
  · simp [hget_hset, hne]; exact hR.self
  · simp [hget_hset, hne]; exact hp
  · simp [hget_hset, hne]; exact hu
  · simp [hget_hset, hl]
  · refine ⟨keysOK_set hmr.1 (mkey_ok _ _ _) _, fun op' a' b' => ?_⟩
    rw [dictFind_set hmr.1 (mkey_ok _ _ _) (mkey_ok _ _ _), memoLookup_cons]
    by_cases e : (op, a, b) = (op', a', b')
    · simp only [Prod.mk.injEq] at e
      obtain ⟨rfl, rfl, rfl⟩ := e
      simp
    · have e' : mkey op a b ≠ mkey op' a' b' := by
        intro h'
        simp only [mkey, iv, V.tup.injEq, V.str.injEq, V.int.injEq, List.cons.injEq, Int.natCast_inj,
          and_true] at h'
        exact e (by rw [BOp.name_inj h'.1, h'.2.1, h'.2.2])
      simp only [e', if_false, e]
      exact hmr.2 op' a' b'

theorem find?_congr' {α : Type} {p q : α → Bool} : ∀ (l : List α), (∀ x ∈ l, p x = q x) → l.find? p = l.find? q
  | [], _ => rfl
  | x :: xs, h => by
      simp only [List.find?_cons, h x (by simp)]
      rw [find?_congr' xs (fun y hy => h y (by simp [hy]))]

theorem findNode_push (ns : Nodes) (x y : Node) :
    findNode (ns.push x) y = (findNode ns y).or (if x = y then some ns.size else none) := by
  unfold findNode
  rw [Array.size_push, List.range_succ, List.find?_append]
  have e1 : (List.range ns.size).find? (fun i => (ns.push x)[i]? == some y) =
      (List.range ns.size).find? (fun i => ns[i]? == some y) := by
    apply find?_congr'
    intro i hi
    simp at hi
    rw [Array.getElem?_push_lt hi, Array.getElem?_eq_getElem hi]
  rw [e1]
  cases (List.range ns.size).find? (fun i => ns[i]? == some y) with
  | some i => simp
  | none => by_cases e : x = y <;> simp [e]

/-! ## Program-table lookups -/

theorem lookup_node : lookupFn pyProg "Diagram.node" = some py_Diagram_node := by rfl
theorem lookup_apply : lookupFn pyProg "Diagram.apply" = some py_Diagram_apply := by rfl
theorem lookup_compile : lookupFn pyProg "Diagram.compile" = some py_Diagram_compile := by rfl
theorem lookup_conjunction : lookupFn pyProg "Diagram.conjunction" = some py_Diagram_conjunction := by rfl
theorem lookup_world : lookupFn pyProg "Diagram.world" = some py_Diagram_world := by rfl
theorem lookup_work : lookupFn pyProg "Diagram.work" = some py_Diagram_work := by rfl
theorem lookup_init : lookupFn pyProg "Diagram.__init__" = some py_Diagram___init__ := by rfl
theorem lookup_evaluate : lookupFn pyProg "evaluate" = some py_evaluate := by rfl
theorem lookup_exact : lookupFn pyProg "exact" = some py_exact := by rfl
theorem lookup_check : lookupFn pyProg "check" = some py_check := by rfl

/-! Resolution of the non-function names used by the extracted code (built-ins, classes, externs). -/

@[simp] theorem lookupFn_b0 : lookupFn pyProg "len" = none := by rfl
@[simp] theorem lookupFn_b1 : lookupFn pyProg "list" = none := by rfl
@[simp] theorem lookupFn_b2 : lookupFn pyProg "int" = none := by rfl
@[simp] theorem lookupFn_b3 : lookupFn pyProg "min" = none := by rfl
@[simp] theorem lookupFn_b4 : lookupFn pyProg "range" = none := by rfl
@[simp] theorem lookupFn_b5 : lookupFn pyProg "all" = none := by rfl
@[simp] theorem lookupFn_b6 : lookupFn pyProg "str" = none := by rfl
@[simp] theorem lookupFn_b7 : lookupFn pyProg "set" = none := by rfl
@[simp] theorem lookupFn_b8 : lookupFn pyProg "deepcopy" = none := by rfl
@[simp] theorem lookupFn_b9 : lookupFn pyProg "dict.fromkeys" = none := by rfl
@[simp] theorem lookupFn_b10 : lookupFn pyProg "ValueError" = none := by rfl
@[simp] theorem lookupFn_b11 : lookupFn pyProg "ResourceLimit" = none := by rfl
@[simp] theorem lookupFn_b12 : lookupFn pyProg "Diagram" = none := by rfl
@[simp] theorem lookupFn_b13 : lookupFn pyProg "digest" = none := by rfl
@[simp] theorem lookupFn_b14 : lookupFn pyProg "validate" = none := by rfl
@[simp] theorem lookupClass_b0 : lookupClass pyProg "len" = none := by rfl
@[simp] theorem lookupClass_b1 : lookupClass pyProg "list" = none := by rfl
@[simp] theorem lookupClass_b2 : lookupClass pyProg "int" = none := by rfl
@[simp] theorem lookupClass_b3 : lookupClass pyProg "min" = none := by rfl
@[simp] theorem lookupClass_b4 : lookupClass pyProg "range" = none := by rfl
@[simp] theorem lookupClass_b5 : lookupClass pyProg "all" = none := by rfl
@[simp] theorem lookupClass_b6 : lookupClass pyProg "str" = none := by rfl
@[simp] theorem lookupClass_b7 : lookupClass pyProg "set" = none := by rfl
@[simp] theorem lookupClass_b8 : lookupClass pyProg "deepcopy" = none := by rfl
@[simp] theorem lookupClass_b9 : lookupClass pyProg "dict.fromkeys" = none := by rfl
@[simp] theorem lookupClass_b10 : lookupClass pyProg "ValueError" = none := by rfl
@[simp] theorem lookupClass_b11 : lookupClass pyProg "digest" = none := by rfl
@[simp] theorem lookupClass_b12 : lookupClass pyProg "validate" = none := by rfl
@[simp] theorem lookupClass_RL : lookupClass pyProg "ResourceLimit" = some { name := "ResourceLimit", methods := [], isException := true } := by rfl
@[simp] theorem lookupClass_Diagram : lookupClass pyProg "Diagram" = some { name := "Diagram", methods := ["__init__", "node", "apply", "compile", "conjunction", "world", "work"], isException := false } := by rfl
@[simp] theorem externs_b0 : pyProg.externs.contains "len" = false := by rfl
@[simp] theorem externs_b1 : pyProg.externs.contains "list" = false := by rfl
@[simp] theorem externs_b2 : pyProg.externs.contains "int" = false := by rfl
@[simp] theorem externs_b3 : pyProg.externs.contains "min" = false := by rfl
@[simp] theorem externs_b4 : pyProg.externs.contains "range" = false := by rfl
@[simp] theorem externs_b5 : pyProg.externs.contains "all" = false := by rfl
@[simp] theorem externs_b6 : pyProg.externs.contains "str" = false := by rfl
@[simp] theorem externs_b7 : pyProg.externs.contains "set" = false := by rfl
@[simp] theorem externs_b8 : pyProg.externs.contains "deepcopy" = false := by rfl
@[simp] theorem externs_b9 : pyProg.externs.contains "dict.fromkeys" = false := by rfl
@[simp] theorem externs_b10 : pyProg.externs.contains "ValueError" = false := by rfl
@[simp] theorem externs_digest : pyProg.externs.contains "digest" = true := by rfl
@[simp] theorem externs_validate : pyProg.externs.contains "validate" = true := by rfl
@[simp] theorem classHasMethod_node : classHasMethod pyProg "Diagram" "node" = true := by rfl
@[simp] theorem classHasMethod_apply : classHasMethod pyProg "Diagram" "apply" = true := by rfl
@[simp] theorem classHasMethod_compile : classHasMethod pyProg "Diagram" "compile" = true := by rfl
@[simp] theorem classHasMethod_conjunction : classHasMethod pyProg "Diagram" "conjunction" = true := by rfl
@[simp] theorem classHasMethod_world : classHasMethod pyProg "Diagram" "world" = true := by rfl
@[simp] theorem classHasMethod_work : classHasMethod pyProg "Diagram" "work" = true := by rfl
@[simp] theorem classHasMethod_init : classHasMethod pyProg "Diagram" "__init__" = true := by rfl
@[simp] theorem classHasMethod_append : classHasMethod pyProg "Diagram" "append" = false := by rfl
@[simp] theorem classHasMethod_index : classHasMethod pyProg "Diagram" "index" = false := by rfl
@[simp] theorem isSome_py_Diagram_node : (lookupFn pyProg "Diagram.node").isSome = true := by rfl
@[simp] theorem isSome_py_Diagram_apply : (lookupFn pyProg "Diagram.apply").isSome = true := by rfl
@[simp] theorem isSome_py_Diagram_compile : (lookupFn pyProg "Diagram.compile").isSome = true := by rfl
@[simp] theorem isSome_py_Diagram_conjunction : (lookupFn pyProg "Diagram.conjunction").isSome = true := by rfl
@[simp] theorem isSome_py_Diagram_world : (lookupFn pyProg "Diagram.world").isSome = true := by rfl
@[simp] theorem isSome_py_Diagram_work : (lookupFn pyProg "Diagram.work").isSome = true := by rfl
@[simp] theorem isSome_py_Diagram___init__ : (lookupFn pyProg "Diagram.__init__").isSome = true := by rfl
@[simp] theorem isSome_py_evaluate : (lookupFn pyProg "evaluate").isSome = true := by rfl
@[simp] theorem isSome_py_exact : (lookupFn pyProg "exact").isSome = true := by rfl
@[simp] theorem isSome_py_check : (lookupFn pyProg "check").isSome = true := by rfl
@[simp] theorem externs_nm0 : "len" ∉ pyProg.externs := by decide
@[simp] theorem externs_nm1 : "list" ∉ pyProg.externs := by decide
@[simp] theorem externs_nm2 : "int" ∉ pyProg.externs := by decide
@[simp] theorem externs_nm3 : "min" ∉ pyProg.externs := by decide
@[simp] theorem externs_nm4 : "range" ∉ pyProg.externs := by decide
@[simp] theorem externs_nm5 : "all" ∉ pyProg.externs := by decide
@[simp] theorem externs_nm6 : "str" ∉ pyProg.externs := by decide
@[simp] theorem externs_nm7 : "set" ∉ pyProg.externs := by decide
@[simp] theorem externs_nm8 : "deepcopy" ∉ pyProg.externs := by decide
@[simp] theorem externs_nm9 : "dict.fromkeys" ∉ pyProg.externs := by decide
@[simp] theorem externs_nm10 : "ValueError" ∉ pyProg.externs := by decide
@[simp] theorem externs_mdigest : "digest" ∈ pyProg.externs := by decide
@[simp] theorem externs_mvalidate : "validate" ∈ pyProg.externs := by decide

end PCSCR.Py
