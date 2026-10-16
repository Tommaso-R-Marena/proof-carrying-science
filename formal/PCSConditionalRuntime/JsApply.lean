import PCSConditionalRuntime.JsNode
import PCSConditionalRuntime.PyApply

namespace PCSCR.Js

open PCSCR PCSDD PCSOmega PCSCR.Py

/-- Symbolic execution of an already unfolded statement sequence (whole goal). -/
macro "jsrun" "[" ls:Lean.Parser.Tactic.simpLemma,* "]" : tactic => `(tactic| (
  simp [execS, evalE, evalL, Env.get, iv, binOp, eqD, eqJs, num, bindS, bindE,
    truthy, execB, assignAll, assignT, assignTs, Env.set, Env.has, Env.replace, attrOp, subOp, memOp,
    fieldGet, fieldSet, setAttrOp, storeOp, elems, hashable, builtin, builtinMethod, builtinJs,
    builtinMethodJs, jsJoin, jsElemStr, normIdx, safeNum, cmpOp, isBoolV, MAX_SAFE, Int.natCast_inj,
    hget_append, hget_hset, seqF_normal, seqF_ret, seqF_raise, $ls,*]))

@[simp] theorem jexterns_mem_0 : ¬ "%Number" ∈ jsProg.externs := by decide
@[simp] theorem jexterns_mem_1 : ¬ "%Boolean" ∈ jsProg.externs := by decide
@[simp] theorem jexterns_mem_2 : ¬ "%Math.min" ∈ jsProg.externs := by decide
@[simp] theorem jexterns_mem_3 : ¬ "%spread" ∈ jsProg.externs := by decide
@[simp] theorem jexterns_mem_4 : ¬ "%keys" ∈ jsProg.externs := by decide
@[simp] theorem jexterns_mem_5 : ¬ "%indices" ∈ jsProg.externs := by decide
@[simp] theorem jexterns_mem_6 : ¬ "%every" ∈ jsProg.externs := by decide
@[simp] theorem jexterns_mem_7 : ¬ "%fromEntries" ∈ jsProg.externs := by decide
@[simp] theorem jexterns_mem_8 : ¬ "%structuredClone" ∈ jsProg.externs := by decide
@[simp] theorem jexterns_mem_9 : ¬ "Diagram" ∈ jsProg.externs := by decide

@[simp] theorem jhget_append_len (h : Heap) (l : List Obj) (i : Nat) :
    hget (h ++ l) (h.length + i) = l[i]? := by
  simp [hget, List.getElem?_append_right]

@[simp] theorem jhget_append_len0 (h : Heap) (l : List Obj) :
    hget (h ++ l) h.length = l[0]? := by
  simpa using jhget_append_len h l 0

/-- `this.f += 1` on an integer field (stated over an `Int` so that kernel checking never unfolds
numerals). -/
theorem js_aug_attr_add1 (ext : Ext) (r : Lvl) (env : Env) (h : Heap) (a : Nat) (cls : String)
    (fs : List (String × V)) (f : String) (o : Int)
    (hthis : env.get "this" = some (.ref a)) (ha : hget h a = some (.inst cls fs))
    (hf : fieldGet fs f = some (.int o)) (hb1 : o + 1 ≤ MAX_SAFE) (hb2 : -MAX_SAFE ≤ o + 1) :
    execS (jsCtx ext) r env h (S.aug (Tgt.attr (E.var "this") f) BinOp.add (E.lit (V.int 1))) =
      .ok (.normal env) (hset h a (.inst cls (fieldSet fs f (.int (o + 1))))) := by
  simp [execS, bindS, evalE, hthis, attrOp, ha, hf, binOp, num, isBoolV, safeNum, hb1, hb2, setAttrOp]

/-- The heap after the operation counter update relates to the incremented manager. -/
theorem JMRel.setOps {names : List String} {lim : Limits} {D : Addrs} {h : Heap} {m : Mgr}
    (hR : JMRel names lim D h m) :
    JMRel names lim D (hset h D.self (.inst "Diagram"
        [("names", .ref D.names), ("limits", .ref D.lim), ("nodes", .ref D.nodes), ("unique", .ref D.uniq),
          ("memo", .ref D.memo), ("operations", .int ((m.ops : Int) + 1)), ("visits", .int (m.visits : Int)),
          ("witnessSteps", .int (m.wsteps : Int))]))
      { m with ops := m.ops + 1 } ∧
    Frame D h (hset h D.self (.inst "Diagram"
        [("names", .ref D.names), ("limits", .ref D.lim), ("nodes", .ref D.nodes), ("unique", .ref D.uniq),
          ("memo", .ref D.memo), ("operations", .int ((m.ops : Int) + 1)), ("visits", .int (m.visits : Int)),
          ("witnessSteps", .int (m.wsteps : Int))])) := by
  have hl := hR.addrs_lt
  have hne := hR.neqs
  have hF : Frame D h (hset h D.self (.inst "Diagram"
        [("names", .ref D.names), ("limits", .ref D.lim), ("nodes", .ref D.nodes), ("unique", .ref D.uniq),
          ("memo", .ref D.memo), ("operations", .int ((m.ops : Int) + 1)), ("visits", .int (m.visits : Int)),
          ("witnessSteps", .int (m.wsteps : Int))])) := Frame.hset _ _ (Or.inl rfl)
  obtain ⟨p, hp, hpr⟩ := hR.nodes
  obtain ⟨u, hu, hur⟩ := hR.uniq
  obtain ⟨mm, hm, hmr⟩ := hR.memo
  refine ⟨hR.transport hF ?_ ⟨p, ?_, hpr.frame hF⟩ ⟨u, ?_, hur⟩ ⟨mm, ?_, hmr⟩, hF⟩
  · simp [hget_hset, hl.1, jdiagramFields, iv]
  · simp [hget_hset, hne]; exact hp
  · simp [hget_hset, hne]; exact hu
  · simp [hget_hset, hne]; exact hm

def japplyTail : List S := js_Diagram_apply.body.drop 3

def japplyCalls : List S :=
  [S.assign [Tgt.name "lo"] ((E.var "this").mcall "apply" [E.var "op", E.var "al", E.var "bl"]),
   S.assign [Tgt.name "hi"] ((E.var "this").mcall "apply" [E.var "op", E.var "ah", E.var "bh"]),
   S.assign [Tgt.name "result"] ((E.var "this").mcall "node" [E.var "v", E.var "lo", E.var "hi"])]

def japplyStore : List S :=
  [S.expr (((E.var "this").attr "memo").mcall "set" [E.var "key", E.var "result"]), S.ret (E.var "result")]

/-- The recursive part of `Diagram.apply`: two recursive calls, node construction, memo store. -/
theorem japply_tail (ext : Ext) (k : Nat) {names : List String} {lim : Limits} {D : Addrs} {H : Heap}
    {m : Mgr} (hR : JMRel names lim D H m) (hinv : Inv names.length lim m) (op : BOp)
    (a b v al ah bl bh fuel : Nat) (x y : V)
    (hal : al < m.nodes.size + 2) (hbl : bl < m.nodes.size + 2)
    (hah : ah < m.nodes.size + 2) (hbh : bh < m.nodes.size + 2)
    (IH : ∀ (h : Heap) (m : Mgr) (a b : Nat) (o : Out V), JMRel names lim D h m → Inv names.length lim m →
      a < m.nodes.size + 2 → b < m.nodes.size + 2 → lim.operations < fuel + m.ops →
      (interp (jsCtx ext) (k + 1)).call "Diagram.apply" [.ref D.self, .str op.name, iv a, iv b] h = o →
      JSimOut names lim D h (apply names.length lim fuel op a b m) o)
    (hfuel : lim.operations < fuel + m.ops) :
    JSimOut names lim D H
      (match apply names.length lim fuel op al bl m with
       | .error e => .error e
       | .ok (lo, m1) =>
         match apply names.length lim fuel op ah bh m1 with
         | .error e => .error e
         | .ok (hi, m2) =>
           match mkNode lim m2 v lo hi with
           | .error e => .error e
           | .ok (r, m3) => .ok (r, { m3 with memo := ((op, a, b), r) :: m3.memo }))
      (finishCall .js (seqF (execB (jsCtx ext) (interp (jsCtx ext) (k + 1))
        [("bh", iv bh), ("bl", iv bl), ("ah", iv ah), ("al", iv al), ("v", iv v), ("bv", x), ("av", y),
         ("result", .undef), ("key", jmkey op a b), ("b", iv b), ("a", iv a), ("op", .str op.name),
         ("this", .ref D.self)] H
        japplyCalls) (fun env' h' => execB (jsCtx ext) (interp (jsCtx ext) (k + 1)) env' h' japplyStore))) := by
  have hself := hR.self
  simp only [jdiagramFields, iv] at hself
  simp only [japplyCalls, japplyStore]
  have s1 := IH H m al bl _ hR hinv hal hbl hfuel rfl
  cases hx1 : apply names.length lim fuel op al bl m with
  | error p =>
    obtain ⟨e, m1⟩ := p
    rw [hx1] at s1
    obtain ⟨H1, a1, e1, ha1, R1, F1⟩ := s1
    simp only [iv] at e1
    jsstep [hself, e1]
    exact ⟨H1, a1, by simp [finishCall], ha1, R1, F1⟩
  | ok p =>
    obtain ⟨lo, m1⟩ := p
    rw [hx1] at s1
    obtain ⟨H1, e1, R1, F1⟩ := s1
    simp only [iv] at e1
    jsstep [hself, e1]
    obtain ⟨i1, ex1, o1, _, r1, _, _⟩ := apply_spec fuel op al bl m lo m1 hinv hal hbl hx1
    have hself1 := R1.self
    simp only [jdiagramFields, iv] at hself1
    have s2 := IH H1 m1 ah bh _ R1 i1 (by have := ex1.1; omega) (by have := ex1.1; omega) (by omega) rfl
    cases hx2 : apply names.length lim fuel op ah bh m1 with
    | error p =>
      obtain ⟨e, m2⟩ := p
      rw [hx2] at s2
      obtain ⟨H2, a2, e2, ha2, R2, F2⟩ := s2
      simp only [iv] at e2
      jsstep [hself1, e2]
      exact ⟨H2, a2, by simp [finishCall], ha2, R2, F1.trans F2⟩
    | ok p =>
      obtain ⟨hi, m2⟩ := p
      rw [hx2] at s2
      obtain ⟨H2, e2, R2, F2⟩ := s2
      simp only [iv] at e2
      jsstep [hself1, e2]
      have hself2 := R2.self
      simp only [jdiagramFields, iv] at hself2
      have s3 := node_spec ext (interp (jsCtx ext) k) R2 v lo hi
      cases hx3 : mkNode lim m2 v lo hi with
      | error p =>
        obtain ⟨e, m3⟩ := p
        rw [hx3] at s3
        obtain ⟨H3, a3, e3, ha3, R3, F3⟩ := s3
        simp only [iv] at e3
        jsstep [hself2, interp_succ_call, e3]
        exact ⟨H3, a3, by simp [finishCall], ha3, R3, F1.trans (F2.trans F3)⟩
      | ok p =>
        obtain ⟨r, m3⟩ := p
        rw [hx3] at s3
        obtain ⟨H3, e3, R3, F3⟩ := s3
        simp only [iv] at e3
        jsstep [hself2, interp_succ_call, e3]
        have hself3 := R3.self
        simp only [jdiagramFields, iv] at hself3
        obtain ⟨mkv, hm, hmr⟩ := R3.memo
        have hne := R3.neqs
        have hl3 := R3.addrs_lt
        simp only [execB_nil_eq, seqF_normal]
        jsstep [hself3, hm, hne, jmkey, hl3.1, hl3.2.2.2.2.2]
        jsstep []
        have hS := R3.setMemo hm hmr op a b r
        exact ⟨_, by simp [finishCall, iv, jmkey], hS.1, F1.trans (F2.trans (F3.trans hS.2))⟩

set_option maxHeartbeats 4000000 in
theorem japply_rest (ext : Ext) (k : Nat) {names : List String} {lim : Limits} {D : Addrs} {h : Heap}
    {m : Mgr} (hR : JMRel names lim D h m) (hinv : Inv names.length lim m) (op : BOp) (a b : Nat)
    (fuel : Nat) (hab : a ≤ b) (ha : a < m.nodes.size + 2) (hb : b < m.nodes.size + 2)
    (IH : ∀ (h : Heap) (m : Mgr) (a b : Nat) (o : Out V), JMRel names lim D h m → Inv names.length lim m →
      a < m.nodes.size + 2 → b < m.nodes.size + 2 → lim.operations < fuel + m.ops →
      (interp (jsCtx ext) (k + 1)).call "Diagram.apply" [.ref D.self, .str op.name, iv a, iv b] h = o →
      JSimOut names lim D h (apply names.length lim fuel op a b m) o)
    (hfuel : lim.operations < fuel + m.ops) :
    JSimOut names lim D h (applyRest names.length lim fuel op a b m)
      (finishCall .js (execB (jsCtx ext) (interp (jsCtx ext) (k + 1))
        [("b", iv b), ("a", iv a), ("op", .str op.name), ("this", .ref D.self)] h japplyTail)) := by
  obtain ⟨kl, hkl, hlr⟩ := hR.limK
  have hself := hR.self
  have hnames := hR.names
  obtain ⟨mkv, hm, hmr⟩ := hR.memo
  simp only [jdiagramFields, iv] at hself
  have hl := hR.addrs_lt
  have hne := hR.neqs
  have hmr' := hmr op a b
  simp only [jmkey, iv] at hmr'
  simp only [japplyTail, js_Diagram_apply, List.drop, iv]
  unfold applyRest
  jsstep []
  have hRk := hR.append (.list [.str op.name, iv a, iv b])
  have hFk := Frame.append D h (.list [.str op.name, iv a, iv b])
  have e1 := jhget_append_lt_list [Obj.list [V.str op.name, V.int ↑a, V.int ↑b]] hl.1
  have e2 := jhget_append_lt_list [Obj.list [V.str op.name, V.int ↑a, V.int ↑b]] hl.2.1
  have e4 := jhget_append_lt_list [Obj.list [V.str op.name, V.int ↑a, V.int ↑b]] hl.2.2.2.1
  have e6 := jhget_append_lt_list [Obj.list [V.str op.name, V.int ↑a, V.int ↑b]] hl.2.2.2.2.2
  cases hml : memoLookup m.memo op a b with
  | some r =>
    jsstep [hself, hm, hmr', hml, e1, e6]
    exact ⟨_, by simp [finishCall, iv], hRk, hFk⟩
  | none =>
    jsstep [hself, hm, hmr', hml, e1, e6]
    jsstep []
    have hm' : hget (h ++ [Obj.list [V.str op.name, V.int ↑a, V.int ↑b]]) D.memo = some (.dict mkv) := by
      rw [e6]; exact hm
    by_cases ht : a < 2 ∧ b < 2
    · simp only [ht, and_self, if_true]
      obtain ⟨ha2, hb2⟩ := ht
      rcases (show a = 0 ∨ a = 1 by omega) with rfl | rfl <;>
      rcases (show b = 0 ∨ b = 1 by omega) with rfl | rfl <;> cases op <;>
      (try omega) <;>
      jsstep [BOp.name] <;>
      jsstep [hself, hm, hl.1, hl.2.2.2.2.2] <;>
      jsstep [] <;>
      exact (let hS := hRk.setMemo hm' hmr _ _ _ _
        ⟨_, by simp [finishCall, iv, jmkey, termOp, BOp.app, BOp.name], hS.1, hFk.trans hS.2⟩)
    · simp only [ht, if_false]
      have hb2 : 2 ≤ b := by omega
      have hbi : ¬ ((b : Int) < 2) := by omega
      obtain ⟨ptrs, hp, hpr⟩ := hR.nodes
      obtain ⟨ndb, bb, hgb, hpb, hmb, hbb⟩ := node_ptr hpr hb2 hb
      obtain ⟨vb, lb, hhb, _, _, _⟩ := hinv.valid.node hgb
      have tb := topVar_node (n := names.length) hgb
      have eb1 : ¬ ((b:Int) - 2 < 0) := by omega
      have eb2 : ((b:Int) - 2).toNat = b - 2 := by omega
      have eb3 : (b:Int) - 2 < ↑ptrs.length := by rw [hpr.1]; omega
      have eb4 : (2:Int) ≤ ↑b := by omega
      simp only [iv] at hbb
      have lbb := hget_lt hbb
      have hlb := lim_bounds hR.lv
      have hsz := hinv.size_le
      have eb5 : (-9007199254740991 : Int) ≤ ↑b - 2 := by omega
      have eb6 : ¬ (9007199254740991 : Int) < ↑b - 2 := by omega
      by_cases ha2 : 2 ≤ a
      · have hai : ¬ ((a : Int) < 2) := by omega
        obtain ⟨nda, ba, hga, hpa, hma, hba⟩ := node_ptr hpr ha2 ha
        obtain ⟨va, la, hha, _, _, _⟩ := hinv.valid.node hga
        have ta := topVar_node (n := names.length) hga
        have ea1 : ¬ ((a:Int) - 2 < 0) := by omega
        have ea2 : ((a:Int) - 2).toNat = a - 2 := by omega
        have ea3 : (a:Int) - 2 < ↑ptrs.length := by rw [hpr.1]; omega
        have ea4 : (2:Int) ≤ ↑a := by omega
        simp only [iv] at hba
        have lba := hget_lt hba
        have ea5 : (-9007199254740991 : Int) ≤ ↑a - 2 := by omega
        have ea6 : ¬ (9007199254740991 : Int) < ↑a - 2 := by omega
        jsif [hai, hbi]
        jsstep [hself, hp, ea1, ea2, ea3, ea4, ea5, ea6, hpa, hba, hl.1, hl.2.2.2.1, lba]
        jsstep [hself, hp, eb1, eb2, eb3, eb4, eb5, eb6, hpb, hbb, hl.1, hl.2.2.2.1, lbb]
        by_cases hlt : ndb.var < nda.var
        · have hmin : min (nda.var : Int) ↑ndb.var = ↑ndb.var := by omega
          have hne1 : ¬ nda.var = ndb.var := by omega
          jsstep [hmin]
          jsstep [hne1, jhget_append_len]
          have As := fun l => jhget_append_lt_list l hl.1
          have An := fun l => jhget_append_lt_list l hl.2.2.2.1
          have Ab := fun l => jhget_append_lt_list l lbb
          have hmx : (max (1:Int) 0).toNat = 1 := by decide
          jsstep [hself, hp, eb1, eb2, eb3, eb4, eb5, eb6, hpb, hbb, As, An, Ab, hmx]
          simp only [ta, tb, Nat.min_eq_right (Nat.le_of_lt hlt), cof, hga, hgb, if_true,
            if_neg (Nat.ne_of_gt hlt)]
          have hRa := ((hR.append (.list [.str op.name, iv a, iv b])).append (.list [iv a, iv a])).append
            (.list [iv ndb.low, iv ndb.high])
          have hFa := ((Frame.append D h (.list [.str op.name, iv a, iv b])).trans
            (Frame.append D _ (.list [iv a, iv a]))).trans (Frame.append D _ (.list [iv ndb.low, iv ndb.high]))
          simp only [List.append_assoc, List.singleton_append, List.cons_append, List.nil_append] at hRa hFa
          exact (japply_tail ext k hRa hinv op a b ndb.var a a ndb.low ndb.high fuel _ _
            ha (by omega) ha (by omega) IH hfuel).frame hFa
        · have As := fun l => jhget_append_lt_list l hl.1
          have An := fun l => jhget_append_lt_list l hl.2.2.2.1
          have Ab := fun l => jhget_append_lt_list l lbb
          have Aa := fun l => jhget_append_lt_list l lba
          have hmx : (max (1:Int) 0).toNat = 1 := by decide
          by_cases heq : nda.var = ndb.var
          · have hmin : min (nda.var : Int) ↑ndb.var = ↑ndb.var := by omega
            jsstep [hmin]
            jsstep [heq, hself, hp, ea1, ea2, ea3, ea4, ea5, ea6, hpa, hba, As, An, Aa, hmx]
            jsstep [heq, hself, hp, eb1, eb2, eb3, eb4, eb5, eb6, hpb, hbb, As, An, Ab, hmx]
            simp only [ta, tb, heq, Nat.min_self, cof, hga, hgb, if_true]
            have hRa := ((hR.append (.list [.str op.name, iv a, iv b])).append (.list [iv nda.low, iv nda.high])).append
              (.list [iv ndb.low, iv ndb.high])
            have hFa := ((Frame.append D h (.list [.str op.name, iv a, iv b])).trans
              (Frame.append D _ (.list [iv nda.low, iv nda.high]))).trans
                (Frame.append D _ (.list [iv ndb.low, iv ndb.high]))
            simp only [List.append_assoc, List.cons_append, List.nil_append] at hRa hFa
            exact (japply_tail ext k hRa hinv op a b ndb.var nda.low nda.high ndb.low ndb.high fuel _ _
              (by omega) (by omega) (by omega) (by omega) IH hfuel).frame hFa
          · have hlt' : nda.var < ndb.var := by omega
            have hmin : min (nda.var : Int) ↑ndb.var = ↑nda.var := by omega
            have hne2 : ¬ ndb.var = nda.var := by omega
            jsstep [hmin]
            jsstep [hself, hp, ea1, ea2, ea3, ea4, ea5, ea6, hpa, hba, As, An, Aa, hmx]
            jsstep [hne2]
            simp only [ta, tb, Nat.min_eq_left (Nat.le_of_lt hlt'), cof, hga, hgb, if_true,
              if_neg (Nat.ne_of_gt hlt')]
            have hRa := ((hR.append (.list [.str op.name, iv a, iv b])).append (.list [iv nda.low, iv nda.high])).append
              (.list [iv b, iv b])
            have hFa := ((Frame.append D h (.list [.str op.name, iv a, iv b])).trans
              (Frame.append D _ (.list [iv nda.low, iv nda.high]))).trans (Frame.append D _ (.list [iv b, iv b]))
            simp only [List.append_assoc, List.cons_append, List.nil_append] at hRa hFa
            exact (japply_tail ext k hRa hinv op a b nda.var nda.low nda.high b b fuel _ _
              (by omega) hb (by omega) hb IH hfuel).frame hFa
      · have hai : (a : Int) < 2 := by omega
        have hga : getNode m.nodes a = none := by simp [getNode]; omega
        have ta : topVar names.length m.nodes a = names.length := by simp [topVar, hga]
        have hvb : ndb.var < names.length := vb
        have ea4 : ¬ (2:Int) ≤ ↑a := by omega
        have As := fun l => jhget_append_lt_list l hl.1
        have An := fun l => jhget_append_lt_list l hl.2.2.2.1
        have Am := fun l => jhget_append_lt_list l hl.2.1
        have Ab := fun l => jhget_append_lt_list l lbb
        have hmx : (max (1:Int) 0).toNat = 1 := by decide
        have hmin : min (names.length : Int) ↑ndb.var = ↑ndb.var := by omega
        have hne1 : ¬ names.length = ndb.var := by omega
        jsif [hai, hbi]
        jsstep [hself, hnames, ea4, As, Am]
        jsstep [hself, hp, eb1, eb2, eb3, eb4, eb5, eb6, hpb, hbb, As, An, Ab]
        jsstep [hmin]
        jsstep [hne1]
        jsstep [hself, hp, eb1, eb2, eb3, eb4, eb5, eb6, hpb, hbb, As, An, Ab, hmx]
        simp only [ta, tb, Nat.min_eq_right (Nat.le_of_lt hvb), cof, hga, hgb, if_true]
        have hRa := ((hR.append (.list [.str op.name, iv a, iv b])).append (.list [iv a, iv a])).append
          (.list [iv ndb.low, iv ndb.high])
        have hFa := ((Frame.append D h (.list [.str op.name, iv a, iv b])).trans
          (Frame.append D _ (.list [iv a, iv a]))).trans (Frame.append D _ (.list [iv ndb.low, iv ndb.high]))
        simp only [List.append_assoc, List.cons_append, List.nil_append] at hRa hFa
        exact (japply_tail ext k hRa hinv op a b ndb.var a a ndb.low ndb.high fuel _ _
          ha (by omega) ha (by omega) IH hfuel).frame hFa

/-- One JavaScript `Diagram.apply` call (budget check, counter update, argument swap) followed by
the recursive part. -/
theorem japply_call (ext : Ext) (k : Nat) {names : List String} {lim : Limits} {D : Addrs} {h : Heap}
    {m : Mgr} (hR : JMRel names lim D h m) (hinv : Inv names.length lim m) (op : BOp) (a b : Nat)
    (fuel : Nat) (ha : a < m.nodes.size + 2) (hb : b < m.nodes.size + 2)
    (IH : ∀ (h : Heap) (m : Mgr) (a b : Nat) (o : Out V), JMRel names lim D h m → Inv names.length lim m →
      a < m.nodes.size + 2 → b < m.nodes.size + 2 → lim.operations < fuel + m.ops →
      (interp (jsCtx ext) (k + 1)).call "Diagram.apply" [.ref D.self, .str op.name, iv a, iv b] h = o →
      JSimOut names lim D h (apply names.length lim fuel op a b m) o)
    (hfuel : lim.operations < fuel + 1 + m.ops) :
    JSimOut names lim D h (apply names.length lim (fuel + 1) op a b m)
      ((interp (jsCtx ext) (k + 2)).call "Diagram.apply" [.ref D.self, .str op.name, iv a, iv b] h) := by
  obtain ⟨kl, hkl, hlr⟩ := hR.limK
  have hself := hR.self
  obtain ⟨hln, hlo⟩ := hlr
  simp only [iv] at hlo
  simp only [jdiagramFields, iv] at hself
  have hl := hR.addrs_lt
  have hne := hR.neqs
  rw [interp_succ_call, apply_succ_eq]
  simp only [callBody, lookup_apply, js_Diagram_apply, jsCtx_prog]
  simp only [List.length, List.zip, List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append,
    List.cons_append, ne_eq, not_true, if_false]
  by_cases hops : lim.operations ≤ m.ops
  · simp only [ge_iff_le, hops, if_true]
    jsstep [hself, hkl, hlo, hops]
    refine ⟨h ++ [.inst "ResourceLimit" [("message", .str "operations")]], h.length, ?_, ?_,
      hR.append _, Frame.append D h _⟩
    · simp [finishCall]
    · simp [LimitReached.name, hget]
  · simp only [ge_iff_le, hops, if_false]
    have hlb := lim_bounds hR.lv
    jsstep [hself, hkl, hlo, hops]
    rw [execB_cons', js_aug_attr_add1 ext _ _ _ D.self "Diagram" _ "operations" (m.ops) (by simp [Env.get]) hself
      (by simp [fieldGet]) (by simp only [MAX_SAFE]; omega) (by simp only [MAX_SAFE]; omega)]
    simp only [seqF_normal, fieldSet, String.reduceEq, if_false, if_true]
    obtain ⟨hR1, hF1⟩ := hR.setOps
    have hinv1 : Inv names.length lim { m with ops := m.ops + 1 } :=
      ⟨hinv.valid, hinv.size_le, by simp; omega, hinv.memo⟩
    by_cases hab : b < a
    · jsstep [hab]
      rw [Nat.min_eq_right (by omega : b ≤ a), Nat.max_eq_left (by omega : b ≤ a)]
      exact (japply_rest ext k (hR1.append _) hinv1 op b a fuel (by omega) hb ha IH (by simp; omega)).frame
        (hF1.trans (Frame.append D _ _))
    · jsstep [hab]
      rw [Nat.min_eq_left (by omega : a ≤ b), Nat.max_eq_right (by omega : a ≤ b)]
      exact (japply_rest ext k hR1 hinv1 op a b fuel (by omega) ha hb IH (by simp; omega)).frame hF1

/-- **JavaScript `Diagram.apply` simulates the reference `apply`** at every interpreter level above
the structural fuel: success returns the same identifier with a related heap; budget exhaustion
throws `new ResourceLimit('operations')` / `new ResourceLimit('nodes')` with a related heap. -/
theorem japply_sim (ext : Ext) {names : List String} {lim : Limits} {D : Addrs} (op : BOp) :
    ∀ (fuel k : Nat), fuel ≤ k → ∀ (h : Heap) (m : Mgr) (a b : Nat), JMRel names lim D h m →
      Inv names.length lim m → a < m.nodes.size + 2 → b < m.nodes.size + 2 →
      lim.operations < fuel + m.ops →
      JSimOut names lim D h (apply names.length lim fuel op a b m)
        ((interp (jsCtx ext) (k + 1)).call "Diagram.apply" [.ref D.self, .str op.name, iv a, iv b] h)
  | 0, _, _, _, m, _, _, _, hinv, _, _, hf => by have := hinv.ops_le; omega
  | fuel + 1, k, hk, h, m, a, b, hR, hinv, ha, hb, hf => by
      obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by omega⟩
      exact japply_call ext k' hR hinv op a b fuel ha hb
        (fun h m a b o hR hinv ha hb hf e => e ▸ japply_sim ext op fuel k' (by omega) h m a b hR hinv ha hb hf)
        hf

end PCSCR.Js
