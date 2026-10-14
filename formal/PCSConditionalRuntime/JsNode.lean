import PCSConditionalRuntime.JsProofBase

/-!
# JavaScript `Diagram.node` refines `PCSDD.mkNode`
-/

namespace PCSCR.Js

open PCSCR PCSDD PCSOmega PCSCR.Py

theorem jhget_append_lt_list {h : Heap} (l : List Obj) {a : Nat} (ha : a < h.length) :
    hget (h ++ l) a = hget h a := by
  simp [hget, List.getElem?_append_left ha]

theorem lim_bounds {lim : Limits} (h : lim.valid = true) :
    1 ≤ lim.nodes ∧ lim.nodes ≤ 4096 ∧ 1 ≤ lim.operations ∧ lim.operations ≤ 100000 := by
  simpa [Limits.valid] using h

/-- The heap after a successful node creation relates to the pushed node table. -/
theorem jmrel_push {names : List String} {lim : Limits} {D : Addrs} {h : Heap} {m : Mgr}
    (hR : JMRel names lim D h m) {ptrs : List V} {ukv : List (V × V)} {v lo hi : Nat}
    (hp : hget h D.nodes = some (.list ptrs)) (hpr : NodesRel D h ptrs m.nodes)
    (hu : hget h D.uniq = some (.dict ukv)) (hur : JUniqRel ukv m.nodes)
    (hf : findNode m.nodes ⟨v, lo, hi⟩ = none) :
    JMRel names lim D (hset (hset (h ++ [.list [iv v, iv lo, iv hi]]) D.nodes (.list (ptrs ++ [.ref h.length])))
        D.uniq (.dict (dictSet .js ukv (jukey v lo hi) (iv (m.nodes.size + 2)))))
      { m with nodes := m.nodes.push ⟨v, lo, hi⟩ } ∧
    Frame D h (hset (hset (h ++ [.list [iv v, iv lo, iv hi]]) D.nodes (.list (ptrs ++ [.ref h.length])))
        D.uniq (.dict (dictSet .js ukv (jukey v lo hi) (iv (m.nodes.size + 2))))) := by
  obtain ⟨l1, l2, l3, l4, l5, l6⟩ := hR.addrs_lt
  have hF : Frame D h (hset (hset (h ++ [.list [iv v, iv lo, iv hi]]) D.nodes (.list (ptrs ++ [.ref h.length])))
        D.uniq (.dict (dictSet .js ukv (jukey v lo hi) (iv (m.nodes.size + 2))))) :=
    ((Frame.append D h _).trans (Frame.hset _ _ (Or.inr (Or.inl rfl)))).trans
      (Frame.hset _ _ (Or.inr (Or.inr (Or.inl rfl))))
  have hmut : ¬ D.mut h.length := by
    have := hR.own_lt h.length
    simp only [Addrs.mut, not_or]
    exact ⟨by omega, by omega, by omega, by omega, fun hm => Nat.lt_irrefl _ (this hm)⟩
  refine ⟨hR.transport hF ?_ ⟨ptrs ++ [.ref h.length], ?_, ?_⟩
    ⟨dictSet .js ukv (jukey v lo hi) (iv (m.nodes.size + 2)), ?_, ?_⟩ ?_, hF⟩
  · simp [hget_hset, hget_append, hR.neqs, l1]
    exact hR.self
  · simp [hget_hset, Ne.symm hR.d4, Nat.lt_succ_of_lt l4]
  · refine ⟨by simp [hpr.1], fun i hi => ?_⟩
    simp only [Array.size_push] at hi
    by_cases hlt : i < m.nodes.size
    · obtain ⟨b, hb, hm, hg⟩ := hpr.2 i hlt
      refine ⟨b, by rw [List.getElem?_append_left (by rw [hpr.1]; exact hlt)]; exact hb, hm, ?_⟩
      rw [hF.2 b (hget_lt hg) hm, Array.getElem_push_lt hlt]; exact hg
    · have hi' : i = m.nodes.size := by omega
      subst hi'
      refine ⟨h.length, by rw [List.getElem?_append_right (by rw [hpr.1]; exact Nat.le_refl _)]; simp [hpr.1], hmut, ?_⟩
      have e1 : D.uniq ≠ h.length := by omega
      have e2 : D.nodes ≠ h.length := by omega
      simp [hget_hset, hget_append, e1, e2]
  · simp [hget_hset, Nat.lt_succ_of_lt l5]
  · intro v' lo' hi'
    rw [jukey, jukey, dictFind_js_set, findNode_push]
    by_cases e : jukey v lo hi = jukey v' lo' hi'
    · obtain ⟨rfl, rfl, rfl⟩ := jukey_inj e
      simp [hf]
    · have e2 : ¬ (jsIntStr (v : Int) ++ "," ++ (jsIntStr (lo : Int) ++ "," ++ jsIntStr (hi : Int)) =
          jsIntStr (v' : Int) ++ "," ++ (jsIntStr (lo' : Int) ++ "," ++ jsIntStr (hi' : Int))) := by
        intro h'; exact e (by simp only [jukey, h'])
      have e' : ¬ ({ var := v, low := lo, high := hi } : Node) = ⟨v', lo', hi'⟩ := by
        intro h'; cases h'; exact e rfl
      simp only [e2, if_false, e', Option.or_none]
      exact hur v' lo' hi'
  · obtain ⟨mm, hm, hmr⟩ := hR.memo
    exact ⟨mm, by simp [hget_hset, hget_append, hR.neqs, l6]; exact hm, hmr⟩

/-- **`Diagram.node` simulates `mkNode`** (reduction, unique-table hit, node budget, push). -/
theorem node_spec (ext : Ext) (r : Lvl) {names : List String} {lim : Limits} {D : Addrs} {h : Heap}
    {m : Mgr} (hR : JMRel names lim D h m) (v lo hi : Nat) :
    JSimOut names lim D h (mkNode lim m v lo hi)
      (callBody (jsCtx ext) r "Diagram.node" [.ref D.self, iv v, iv lo, iv hi] h) := by
  obtain ⟨kl, hkl, hlr⟩ := hR.limK
  obtain ⟨ptrs, hp, hpr⟩ := hR.nodes
  obtain ⟨ukv, hu, hur⟩ := hR.uniq
  have hself := hR.self
  obtain ⟨l1, l2, l3, l4, l5, l6⟩ := hR.addrs_lt
  have hlb := lim_bounds hR.lv
  have hun := hur v lo hi
  simp only [jukey, iv] at hun
  obtain ⟨hln, hlo⟩ := hlr
  simp only [iv] at hln
  simp only [jdiagramFields, iv] at hself
  simp only [callBody, lookup_node, js_Diagram_node, jsCtx_prog]
  simp only [List.length, List.zip, List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append,
    List.cons_append, ne_eq, not_true, if_false]
  unfold mkNode
  by_cases hlh : lo = hi
  · subst hlh
    simp only [if_true]
    jsstep []
    exact ⟨h, by simp [finishCall, iv], hR, Frame.refl D h⟩
  · simp only [hlh, if_false]
    jsstep [hlh]
    jsstep []
    cases hf : findNode m.nodes ⟨v, lo, hi⟩ with
    | some i =>
      jsstep [hself, hu, hun, hf, l1, l3, l4, l5]
      exact ⟨h ++ [.list [iv v, iv lo, iv hi]], by simp [finishCall, iv], hR.append _, Frame.append D h _⟩
    | none =>
      jsstep [hself, hu, hun, hf, l1, l3, l4, l5]
      have hR1 := hR.append (.list [iv v, iv lo, iv hi])
      have hF1 := Frame.append D h (.list [iv v, iv lo, iv hi])
      have hp1 : hget (h ++ [.list [iv v, iv lo, iv hi]]) D.nodes = some (.list ptrs) := by
        rw [hget_append_lt _ l4]; exact hp
      have hu1 : hget (h ++ [.list [iv v, iv lo, iv hi]]) D.uniq = some (.dict ukv) := by
        rw [hget_append_lt _ l5]; exact hu
      by_cases hsz : lim.nodes ≤ m.nodes.size
      · simp only [ge_iff_le, hsz, if_true]
        jsstep [hself, hp, hkl, hln, hpr.1, hsz, l1, l3, l4]
        refine ⟨h ++ [.list [iv v, iv lo, iv hi], .inst "ResourceLimit" [("message", .str "nodes")]],
          h.length + 1, ?_, ?_, ?_, ?_⟩
        · simp [finishCall, iv]
        · simp [LimitReached.name, hget]
        · have := hR1.append (.inst "ResourceLimit" [("message", .str "nodes")])
          simpa using this
        · have := hF1.trans (Frame.append D _ (.inst "ResourceLimit" [("message", .str "nodes")]))
          simpa using this
      · simp only [ge_iff_le, hsz, if_false]
        jsstep [hself, hp, hkl, hln, hpr.1, hsz, l1, l3, l4]
        have hs1 : ¬ (9007199254740991 : Int) < ↑(m.nodes.size) + 2 := by omega
        have hs2 : (-9007199254740991 : Int) ≤ ↑(m.nodes.size) + 2 := by omega
        jsstep [hself, hp, hpr.1, l1, l4, hs1, hs2]
        have l1' : D.self < h.length + 1 := by omega
        have l4' : D.nodes < h.length + 1 := by omega
        have l5' : D.uniq < h.length + 1 := by omega
        jsstep [hself, hp, l1, l4, l1', l4']
        have hne := hR.neqs
        jsstep [hself, hu, hne, l1', l5', jhget_append_lt_list _ l1, jhget_append_lt_list _ l5]
        jsstep []
        obtain ⟨hR', hF'⟩ := jmrel_push hR1 hp1 (hpr.frame hF1) hu1 hur hf
        refine ⟨_, ?_, hR', hF1.trans hF'⟩
        simp [finishCall, iv, hpr.1, jukey]

end PCSCR.Js
