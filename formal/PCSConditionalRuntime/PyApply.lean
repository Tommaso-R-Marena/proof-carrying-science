import PCSConditionalRuntime.PyNode

/-!
# `Diagram.apply` refines `PCSDD.apply`

Induction on the reference structural fuel; each Python recursion level consumes one
interpreter level.  The hypothesis `lim.operations < fuel + m.ops` (always true for the
top-level fuel `applyFuel lim = lim.operations + 1`) guarantees that the reference never runs
out of structural fuel before the operation budget is exhausted, so the two agree exactly.
-/

namespace PCSCR.Py

open PCSCR PCSDD PCSOmega

/-- The reference `apply` after the budget check and argument normalisation. -/
def applyRest (n : Nat) (lim : Limits) (fuel : Nat) (op : BOp) (a b : Nat) (m : Mgr) :
    Except (LimitReached × Mgr) (Nat × Mgr) :=
  match memoLookup m.memo op a b with
  | some r => .ok (r, m)
  | none =>
    if a < 2 ∧ b < 2 then
      .ok (termOp op a b, { m with memo := ((op, a, b), termOp op a b) :: m.memo })
    else
      match apply n lim fuel op (cof m.nodes (min (topVar n m.nodes a) (topVar n m.nodes b)) a).1
          (cof m.nodes (min (topVar n m.nodes a) (topVar n m.nodes b)) b).1 m with
      | .error e => .error e
      | .ok (lo, m1) =>
        match apply n lim fuel op (cof m.nodes (min (topVar n m.nodes a) (topVar n m.nodes b)) a).2
            (cof m.nodes (min (topVar n m.nodes a) (topVar n m.nodes b)) b).2 m1 with
        | .error e => .error e
        | .ok (hi, m2) =>
          match mkNode lim m2 (min (topVar n m.nodes a) (topVar n m.nodes b)) lo hi with
          | .error e => .error e
          | .ok (r, m3) => .ok (r, { m3 with memo := ((op, a, b), r) :: m3.memo })

theorem apply_succ_eq (n : Nat) (lim : Limits) (fuel : Nat) (op : BOp) (a0 b0 : Nat) (m0 : Mgr) :
    apply n lim (fuel + 1) op a0 b0 m0 =
      if m0.ops ≥ lim.operations then .error (.operations, m0)
      else applyRest n lim fuel op (min a0 b0) (max a0 b0) { m0 with ops := m0.ops + 1 } := rfl

theorem lookup_apply' (ext : Ext) : lookupFn (pyCtx ext).prog "Diagram.apply" = some py_Diagram_apply := by rfl


theorem node_ptr {D : Addrs} {h : Heap} {ptrs : List V} {ns : Nodes} (hpr : NodesRel D h ptrs ns)
    {u : Nat} (h2 : 2 ≤ u) (hu : u < ns.size + 2) :
    ∃ nd b, getNode ns u = some nd ∧ ptrs[u - 2]? = some (.ref b) ∧ ¬ D.mut b ∧
      hget h b = some (.list [iv nd.var, iv nd.low, iv nd.high]) := by
  obtain ⟨b, hb, hm, hg⟩ := hpr.2 (u - 2) (by omega)
  refine ⟨_, b, ?_, hb, hm, hg⟩
  unfold getNode
  rw [if_neg (by omega), Array.getElem?_eq_getElem]

theorem interp_succ_call (c : Ctx) (k : Nat) (f : String) (args : List V) (h : Heap) :
    (interp c (k + 1)).call f args h = callBody c (interp c k) f args h := rfl

theorem SimOut.frame {names : List String} {lim : Limits} {D : Addrs} {h0 h : Heap}
    {x : Except (LimitReached × Mgr) (Nat × Mgr)} {o : Out V} (hf : Frame D h0 h)
    (hs : SimOut names lim D h x o) : SimOut names lim D h0 x o := by
  unfold SimOut at *
  split at hs
  · obtain ⟨h', e, R, F⟩ := hs; exact ⟨h', e, R, hf.trans F⟩
  · obtain ⟨h', a, e, ha, R, F⟩ := hs; exact ⟨h', a, e, ha, R, hf.trans F⟩

theorem hget_append_lt_list {h : Heap} (l : List Obj) {a : Nat} (ha : a < h.length) :
    hget (h ++ l) a = hget h a := by
  simp [hget, List.getElem?_append_left ha]

theorem hget_append2 (h : Heap) (o1 o2 : Obj) : hget (h ++ [o1, o2]) (h.length + 1) = some o2 := by
  simp [hget]

def applyCalls : List S :=
  [S.assign [Tgt.name "low"] ((E.var "self").mcall "apply" [E.var "op", E.var "al", E.var "bl"]),
   S.assign [Tgt.name "high"] ((E.var "self").mcall "apply" [E.var "op", E.var "ah", E.var "bh"]),
   S.assign [Tgt.name "result"] ((E.var "self").mcall "node" [E.var "var", E.var "low", E.var "high"])]

def applyStore : List S :=
  [S.assign [Tgt.sub ((E.var "self").attr "memo") (E.var "key")] (E.var "result"), S.ret (E.var "result")]

/-- The recursive part of `Diagram.apply`: two recursive calls, node construction, memo store. -/
theorem apply_tail (ext : Ext) (k : Nat) {names : List String} {lim : Limits} {D : Addrs} {H : Heap}
    {m : Mgr} (hR : MRel names lim D H m) (hinv : Inv names.length lim m) (op : BOp)
    (a b v al ah bl bh fuel : Nat) (x y : V)
    (hal : al < m.nodes.size + 2) (hbl : bl < m.nodes.size + 2)
    (hah : ah < m.nodes.size + 2) (hbh : bh < m.nodes.size + 2)
    (IH : ∀ (h : Heap) (m : Mgr) (a b : Nat) (o : Out V), MRel names lim D h m → Inv names.length lim m →
      a < m.nodes.size + 2 → b < m.nodes.size + 2 → lim.operations < fuel + m.ops →
      (interp (pyCtx ext) (k + 1)).call "Diagram.apply" [.ref D.self, .str op.name, iv a, iv b] h = o →
      SimOut names lim D h (apply names.length lim fuel op a b m) o)
    (hfuel : lim.operations < fuel + m.ops) :
    SimOut names lim D H
      (match apply names.length lim fuel op al bl m with
       | .error e => .error e
       | .ok (lo, m1) =>
         match apply names.length lim fuel op ah bh m1 with
         | .error e => .error e
         | .ok (hi, m2) =>
           match mkNode lim m2 v lo hi with
           | .error e => .error e
           | .ok (r, m3) => .ok (r, { m3 with memo := ((op, a, b), r) :: m3.memo }))
      (finishCall .py (seqF (execB (pyCtx ext) (interp (pyCtx ext) (k + 1))
        [("bh", iv bh), ("bl", iv bl), ("ah", iv ah), ("al", iv al), ("var", iv v), ("bv", x), ("av", y),
         ("key", mkey op a b), ("b", iv b), ("a", iv a), ("op", .str op.name), ("self", .ref D.self)] H
        applyCalls) (fun env' h' => execB (pyCtx ext) (interp (pyCtx ext) (k + 1)) env' h' applyStore))) := by
  have hself := hR.self
  simp only [diagramFields, iv] at hself
  simp only [applyCalls, applyStore]
  have s1 := IH H m al bl _ hR hinv hal hbl hfuel rfl
  cases hx1 : apply names.length lim fuel op al bl m with
  | error p =>
    obtain ⟨e, m1⟩ := p
    rw [hx1] at s1
    obtain ⟨H1, a1, e1, ha1, R1, F1⟩ := s1
    simp only [iv] at e1
    pystep [hself, e1]
    exact ⟨H1, a1, by simp [finishCall], ha1, R1, F1⟩
  | ok p =>
    obtain ⟨lo, m1⟩ := p
    rw [hx1] at s1
    obtain ⟨H1, e1, R1, F1⟩ := s1
    simp only [iv] at e1
    pystep [hself, e1]
    obtain ⟨i1, ex1, o1, _, r1, _, _⟩ := apply_spec fuel op al bl m lo m1 hinv hal hbl hx1
    have hself1 := R1.self
    simp only [diagramFields, iv] at hself1
    have s2 := IH H1 m1 ah bh _ R1 i1 (by have := ex1.1; omega) (by have := ex1.1; omega) (by omega) rfl
    cases hx2 : apply names.length lim fuel op ah bh m1 with
    | error p =>
      obtain ⟨e, m2⟩ := p
      rw [hx2] at s2
      obtain ⟨H2, a2, e2, ha2, R2, F2⟩ := s2
      simp only [iv] at e2
      pystep [hself1, e2]
      exact ⟨H2, a2, by simp [finishCall], ha2, R2, F1.trans F2⟩
    | ok p =>
      obtain ⟨hi, m2⟩ := p
      rw [hx2] at s2
      obtain ⟨H2, e2, R2, F2⟩ := s2
      simp only [iv] at e2
      pystep [hself1, e2]
      have hself2 := R2.self
      simp only [diagramFields, iv] at hself2
      have s3 := node_spec ext (interp (pyCtx ext) k) R2 v lo hi
      cases hx3 : mkNode lim m2 v lo hi with
      | error p =>
        obtain ⟨e, m3⟩ := p
        rw [hx3] at s3
        obtain ⟨H3, a3, e3, ha3, R3, F3⟩ := s3
        simp only [iv] at e3
        pystep [hself2, interp_succ_call, e3]
        exact ⟨H3, a3, by simp [finishCall], ha3, R3, F1.trans (F2.trans F3)⟩
      | ok p =>
        obtain ⟨r, m3⟩ := p
        rw [hx3] at s3
        obtain ⟨H3, e3, R3, F3⟩ := s3
        simp only [iv] at e3
        pystep [hself2, interp_succ_call, e3]
        have hself3 := R3.self
        simp only [diagramFields, iv] at hself3
        obtain ⟨mkv, hm, hmr⟩ := R3.memo
        have hne := R3.neqs
        simp only [execB_nil_eq, seqF_normal]
        pystep [hself3, hm, hne, mkey]
        pystep []
        have hS := R3.setMemo hm hmr op a b r
        exact ⟨_, by simp [finishCall, iv, mkey], hS.1, F1.trans (F2.trans (F3.trans hS.2))⟩

def applyTail : List S := py_Diagram_apply.body.drop 3


set_option maxHeartbeats 4000000 in
theorem apply_rest (ext : Ext) (k : Nat) {names : List String} {lim : Limits} {D : Addrs} {h : Heap}
    {m : Mgr} (hR : MRel names lim D h m) (hinv : Inv names.length lim m) (op : BOp) (a b : Nat)
    (fuel : Nat) (hab : a ≤ b) (ha : a < m.nodes.size + 2) (hb : b < m.nodes.size + 2)
    (IH : ∀ (h : Heap) (m : Mgr) (a b : Nat) (o : Out V), MRel names lim D h m → Inv names.length lim m →
      a < m.nodes.size + 2 → b < m.nodes.size + 2 → lim.operations < fuel + m.ops →
      (interp (pyCtx ext) (k + 1)).call "Diagram.apply" [.ref D.self, .str op.name, iv a, iv b] h = o →
      SimOut names lim D h (apply names.length lim fuel op a b m) o)
    (hfuel : lim.operations < fuel + m.ops) :
    SimOut names lim D h (applyRest names.length lim fuel op a b m)
      (finishCall .py (execB (pyCtx ext) (interp (pyCtx ext) (k + 1))
        [("b", iv b), ("a", iv a), ("op", .str op.name), ("self", .ref D.self)] h applyTail)) := by
  obtain ⟨kl, hkl, hlr⟩ := hR.limK
  have hself := hR.self
  have hnames := hR.names
  obtain ⟨mkv, hm, hmk, hmr⟩ := hR.memo
  simp only [diagramFields, iv] at hself
  have hl := hR.addrs_lt
  have hne := hR.neqs
  have hmr' := hmr op a b
  simp only [mkey, iv] at hmr'
  simp only [applyTail, py_Diagram_apply, List.drop, iv]
  unfold applyRest
  pystep []
  cases hml : memoLookup m.memo op a b with
  | some r =>
    pystep [hself, hm, hmr', hml]
    exact ⟨h, by simp [finishCall, iv], hR, Frame.refl D h⟩
  | none =>
    pystep [hself, hm, hmr', hml]
    by_cases ht : a < 2 ∧ b < 2
    · simp only [ht, and_self, if_true]
      obtain ⟨ha2, hb2⟩ := ht
      rcases (show a = 0 ∨ a = 1 by omega) with rfl | rfl <;>
      rcases (show b = 0 ∨ b = 1 by omega) with rfl | rfl <;> cases op <;>
      (try omega) <;>
      pystep [BOp.name] <;>
      pystep [hself, hm, hne] <;>
      pystep [] <;>
      exact (let hS := hR.setMemo hm ⟨hmk, hmr⟩ _ _ _ _
        ⟨_, by simp [finishCall, iv, mkey, termOp, BOp.app, BOp.name], hS.1, hS.2⟩)
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
      have hRa := hR.append (.list [iv ndb.low, iv ndb.high])
      have hFa := Frame.append D h (.list [iv ndb.low, iv ndb.high])
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
        pyif [hai, hbi]
        pystep [hself, hp, ea1, ea2, ea3, ea4, hpa, hba]
        pystep [hself, hp, eb1, eb2, eb3, eb4, hpb, hbb]
        by_cases hlt : ndb.var < nda.var
        · pystep [hlt]
          pystep [hlt, Nat.ne_of_gt hlt]
          pystep [hlt, hself, hp, eb1, eb2, eb3, eb4, hpb, hbb]
          simp only [ta, tb, Nat.min_eq_right (Nat.le_of_lt hlt), cof, hga, hgb, if_true,
            if_neg (Nat.ne_of_gt hlt)]
          exact (apply_tail ext k hRa hinv op a b ndb.var a a ndb.low ndb.high fuel _ _
            ha (by omega) ha (by omega) IH hfuel).frame hFa
        · by_cases heq : nda.var = ndb.var
          · pystep [heq]
            pystep [heq, hself, hp, ea1, ea2, ea3, ea4, hpa, hba]
            have l1 := hl.1; have l4 := hl.2.2.2.1; have lbb := hget_lt hbb
            pystep [heq, hself, hp, eb1, eb2, eb3, eb4, hpb, hbb, l1, l4, lbb, hget_append_lt_list,
              hget_append2]
            simp only [ta, tb, heq, Nat.min_self, cof, hga, hgb, if_true]
            have hRa' := (hR.append (.list [iv nda.low, iv nda.high])).append (.list [iv ndb.low, iv ndb.high])
            have hFa' := (Frame.append D h (.list [iv nda.low, iv nda.high])).trans
              (Frame.append D _ (.list [iv ndb.low, iv ndb.high]))
            simp only [List.append_assoc, List.singleton_append] at hRa' hFa'
            exact (apply_tail ext k hRa' hinv op a b ndb.var nda.low nda.high ndb.low ndb.high fuel _ _
              (by omega) (by omega) (by omega) (by omega) IH hfuel).frame hFa'
          · have hlt' : nda.var < ndb.var := by omega
            pystep [hlt', Nat.not_lt.mpr (Nat.le_of_lt hlt')]
            pystep [hself, hp, ea1, ea2, ea3, ea4, hpa, hba]
            pystep [Nat.ne_of_lt hlt', Nat.ne_of_gt hlt']
            simp only [ta, tb, Nat.min_eq_left (Nat.le_of_lt hlt'), cof, hga, hgb, if_true,
              if_neg (Nat.ne_of_gt hlt')]
            have hRa' := hR.append (.list [iv nda.low, iv nda.high])
            have hFa' := Frame.append D h (.list [iv nda.low, iv nda.high])
            exact (apply_tail ext k hRa' hinv op a b nda.var nda.low nda.high b b fuel _ _
              (by omega) hb (by omega) hb IH hfuel).frame hFa'
      · have hai : (a : Int) < 2 := by omega
        have hga : getNode m.nodes a = none := by simp [getNode]; omega
        have ta : topVar names.length m.nodes a = names.length := by simp [topVar, hga]
        have hvb : ndb.var < names.length := vb
        have ea4 : ¬ (2:Int) ≤ ↑a := by omega
        pyif [hai, hbi]
        pystep [hself, hnames, ea4]
        pystep [hself, hp, eb1, eb2, eb3, eb4, hpb, hbb]
        pystep [Nat.not_lt.mpr (Nat.le_of_lt hvb), hvb]
        pystep [Nat.ne_of_gt hvb]
        pystep [hself, hp, eb1, eb2, eb3, eb4, hpb, hbb]
        simp only [ta, tb, Nat.min_eq_right (Nat.le_of_lt hvb), cof, hga, hgb, if_true]
        exact (apply_tail ext k hRa hinv op a b ndb.var a a ndb.low ndb.high fuel _ _
          ha (by omega) ha (by omega) IH hfuel).frame hFa

/-- The heap after the operation counter update relates to the incremented manager. -/
theorem MRel.setOps {names : List String} {lim : Limits} {D : Addrs} {h : Heap} {m : Mgr}
    (hR : MRel names lim D h m) :
    MRel names lim D (hset h D.self (.inst "Diagram"
        [("names", .ref D.names), ("limits", .ref D.lim), ("nodes", .ref D.nodes), ("unique", .ref D.uniq),
          ("memo", .ref D.memo), ("operations", .int ((m.ops : Int) + 1)), ("visits", .int (m.visits : Int)),
          ("witness_steps", .int (m.wsteps : Int))]))
      { m with ops := m.ops + 1 } ∧
    Frame D h (hset h D.self (.inst "Diagram"
        [("names", .ref D.names), ("limits", .ref D.lim), ("nodes", .ref D.nodes), ("unique", .ref D.uniq),
          ("memo", .ref D.memo), ("operations", .int ((m.ops : Int) + 1)), ("visits", .int (m.visits : Int)),
          ("witness_steps", .int (m.wsteps : Int))])) := by
  have hl := hR.addrs_lt
  have hne := hR.neqs
  have hF : Frame D h (hset h D.self (.inst "Diagram"
        [("names", .ref D.names), ("limits", .ref D.lim), ("nodes", .ref D.nodes), ("unique", .ref D.uniq),
          ("memo", .ref D.memo), ("operations", .int ((m.ops : Int) + 1)), ("visits", .int (m.visits : Int)),
          ("witness_steps", .int (m.wsteps : Int))])) := Frame.hset _ _ (Or.inl rfl)
  obtain ⟨p, hp, hpr⟩ := hR.nodes
  obtain ⟨u, hu, hur⟩ := hR.uniq
  obtain ⟨mm, hm, hmr⟩ := hR.memo
  refine ⟨hR.transport hF ?_ ⟨p, ?_, hpr.frame hF⟩ ⟨u, ?_, hur⟩ ⟨mm, ?_, hmr⟩, hF⟩
  · simp [hget_hset, hl.1, diagramFields, iv]
  · simp [hget_hset, hne]; exact hp
  · simp [hget_hset, hne]; exact hu
  · simp [hget_hset, hne]; exact hm

/-- One Python `Diagram.apply` call (budget check, counter update, argument swap) followed by
the recursive part. -/
theorem apply_call (ext : Ext) (k : Nat) {names : List String} {lim : Limits} {D : Addrs} {h : Heap}
    {m : Mgr} (hR : MRel names lim D h m) (hinv : Inv names.length lim m) (op : BOp) (a b : Nat)
    (fuel : Nat) (ha : a < m.nodes.size + 2) (hb : b < m.nodes.size + 2)
    (IH : ∀ (h : Heap) (m : Mgr) (a b : Nat) (o : Out V), MRel names lim D h m → Inv names.length lim m →
      a < m.nodes.size + 2 → b < m.nodes.size + 2 → lim.operations < fuel + m.ops →
      (interp (pyCtx ext) (k + 1)).call "Diagram.apply" [.ref D.self, .str op.name, iv a, iv b] h = o →
      SimOut names lim D h (apply names.length lim fuel op a b m) o)
    (hfuel : lim.operations < fuel + 1 + m.ops) :
    SimOut names lim D h (apply names.length lim (fuel + 1) op a b m)
      ((interp (pyCtx ext) (k + 2)).call "Diagram.apply" [.ref D.self, .str op.name, iv a, iv b] h) := by
  obtain ⟨kl, hkl, hlr⟩ := hR.limK
  have hself := hR.self
  obtain ⟨hln, hlo⟩ := hlr
  simp only [iv] at hlo
  simp only [diagramFields, iv] at hself
  have hl := hR.addrs_lt
  have hne := hR.neqs
  rw [interp_succ_call, apply_succ_eq]
  simp only [callBody, lookup_apply', py_Diagram_apply]
  simp only [List.length, List.zip, List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append,
    List.cons_append, ne_eq, not_true, if_false]
  by_cases hops : lim.operations ≤ m.ops
  · simp only [ge_iff_le, hops, if_true]
    pystep [hself, hkl, hlo, hops]
    refine ⟨h ++ [.inst "ResourceLimit" [("args", .tup [.str "operations"])]], h.length, ?_, ?_,
      hR.append _, Frame.append D h _⟩
    · simp [finishCall]
    · simp [LimitReached.name]
  · simp only [ge_iff_le, hops, if_false]
    pystep [hself, hkl, hlo, hops]
    pystep [hself, hl.1]
    obtain ⟨hR1, hF1⟩ := hR.setOps
    have hinv1 : Inv names.length lim { m with ops := m.ops + 1 } :=
      ⟨hinv.valid, hinv.size_le, by simp; omega, hinv.memo⟩
    by_cases hab : b < a
    · pystep [hab]
      rw [Nat.min_eq_right (by omega : b ≤ a), Nat.max_eq_left (by omega : b ≤ a)]
      exact (apply_rest ext k hR1 hinv1 op b a fuel (by omega) hb ha IH (by simp; omega)).frame hF1
    · pystep [hab]
      rw [Nat.min_eq_left (by omega : a ≤ b), Nat.max_eq_right (by omega : a ≤ b)]
      exact (apply_rest ext k hR1 hinv1 op a b fuel (by omega) ha hb IH (by simp; omega)).frame hF1

/-- **`Diagram.apply` simulates the reference `apply`** at every interpreter level above the
structural fuel: success returns the same identifier with a related heap; budget exhaustion
raises `ResourceLimit('operations')` / `ResourceLimit('nodes')` with a related heap. -/
theorem apply_sim (ext : Ext) {names : List String} {lim : Limits} {D : Addrs} (op : BOp) :
    ∀ (fuel k : Nat), fuel ≤ k → ∀ (h : Heap) (m : Mgr) (a b : Nat), MRel names lim D h m →
      Inv names.length lim m → a < m.nodes.size + 2 → b < m.nodes.size + 2 →
      lim.operations < fuel + m.ops →
      SimOut names lim D h (apply names.length lim fuel op a b m)
        ((interp (pyCtx ext) (k + 1)).call "Diagram.apply" [.ref D.self, .str op.name, iv a, iv b] h)
  | 0, _, _, _, m, _, _, _, hinv, _, _, hf => by have := hinv.ops_le; omega
  | fuel + 1, k, hk, h, m, a, b, hR, hinv, ha, hb, hf => by
      obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by omega⟩
      exact apply_call ext k' hR hinv op a b fuel ha hb
        (fun h m a b o hR hinv ha hb hf e => e ▸ apply_sim ext op fuel k' (by omega) h m a b hR hinv ha hb hf)
        hf

end PCSCR.Py
