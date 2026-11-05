import PCSConditionalRuntime.PyProofBase

/-!
# `Diagram.node` refines `PCSDD.mkNode`
-/

namespace PCSCR.Py

open PCSCR PCSDD PCSOmega

theorem ukey_inj {v lo hi v' lo' hi' : Nat} (h : ukey v lo hi = ukey v' lo' hi') :
    v = v' ∧ lo = lo' ∧ hi = hi' := by
  simp [ukey, iv] at h; omega

/-- The heap after a successful node creation relates to the pushed node table. -/
theorem mrel_push {names : List String} {lim : Limits} {D : Addrs} {h : Heap} {m : Mgr}
    (hR : MRel names lim D h m) {ptrs : List V} {ukv : List (V × V)} {v lo hi : Nat}
    (hp : hget h D.nodes = some (.list ptrs)) (hpr : NodesRel D h ptrs m.nodes)
    (hu : hget h D.uniq = some (.dict ukv)) (huk : KeysOK ukv)
    (hur : ∀ v lo hi, dictFind .py ukv (ukey v lo hi) = (findNode m.nodes ⟨v, lo, hi⟩).map (fun i => iv (i + 2)))
    (hf : findNode m.nodes ⟨v, lo, hi⟩ = none) :
    MRel names lim D (hset (hset (h ++ [.list [iv v, iv lo, iv hi]]) D.nodes (.list (ptrs ++ [.ref h.length])))
        D.uniq (.dict (dictSet .py ukv (ukey v lo hi) (iv (m.nodes.size + 2)))))
      { m with nodes := m.nodes.push ⟨v, lo, hi⟩ } ∧
    Frame D h (hset (hset (h ++ [.list [iv v, iv lo, iv hi]]) D.nodes (.list (ptrs ++ [.ref h.length])))
        D.uniq (.dict (dictSet .py ukv (ukey v lo hi) (iv (m.nodes.size + 2))))) := by
  obtain ⟨l1, l2, l3, l4, l5, l6⟩ := hR.addrs_lt
  have hF : Frame D h (hset (hset (h ++ [.list [iv v, iv lo, iv hi]]) D.nodes (.list (ptrs ++ [.ref h.length])))
        D.uniq (.dict (dictSet .py ukv (ukey v lo hi) (iv (m.nodes.size + 2))))) :=
    ((Frame.append D h _).trans (Frame.hset _ _ (Or.inr (Or.inl rfl)))).trans
      (Frame.hset _ _ (Or.inr (Or.inr (Or.inl rfl))))
  have hmut : ¬ D.mut h.length := by
    have := hR.own_lt h.length
    simp only [Addrs.mut, not_or]
    exact ⟨by omega, by omega, by omega, by omega, fun hm => Nat.lt_irrefl _ (this hm)⟩
  refine ⟨hR.transport hF ?_ ⟨ptrs ++ [.ref h.length], ?_, ?_⟩
    ⟨dictSet .py ukv (ukey v lo hi) (iv (m.nodes.size + 2)), ?_, ?_⟩ ?_, hF⟩
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
  · refine ⟨keysOK_set huk (ukey_ok _ _ _) _, fun v' lo' hi' => ?_⟩
    rw [dictFind_set huk (ukey_ok _ _ _) (ukey_ok _ _ _), findNode_push]
    by_cases e : ukey v lo hi = ukey v' lo' hi'
    · obtain ⟨rfl, rfl, rfl⟩ := ukey_inj e
      simp [hf]
    · have e' : ¬ ({ var := v, low := lo, high := hi } : Node) = ⟨v', lo', hi'⟩ := by
        intro h'; cases h'; exact e rfl
      simp only [e, if_false, e', Option.or_none]
      rw [hur]
  · obtain ⟨mm, hm, hmr⟩ := hR.memo
    exact ⟨mm, by simp [hget_hset, hget_append, hR.neqs, l6]; exact hm, hmr⟩

theorem lookup_node' (ext : Ext) : lookupFn (pyCtx ext).prog "Diagram.node" = some py_Diagram_node := by rfl

/-- **`Diagram.node` simulates `mkNode`** (reduction, unique-table hit, node budget, push). -/
theorem node_spec (ext : Ext) (r : Lvl) {names : List String} {lim : Limits} {D : Addrs} {h : Heap}
    {m : Mgr} (hR : MRel names lim D h m) (v lo hi : Nat) :
    SimOut names lim D h (mkNode lim m v lo hi)
      (callBody (pyCtx ext) r "Diagram.node" [.ref D.self, iv v, iv lo, iv hi] h) := by
  obtain ⟨kl, hkl, hlr⟩ := hR.limK
  obtain ⟨ptrs, hp, hpr⟩ := hR.nodes
  obtain ⟨ukv, hu, huk, hur⟩ := hR.uniq
  have hself := hR.self
  obtain ⟨l1, l2, l3, l4, l5, l6⟩ := hR.addrs_lt
  have d1 := hR.d1; have d2 := hR.d2; have d3 := hR.d3; have d4 := hR.d4; have d5 := hR.d5
  have d6 := hR.d6
  have d1' := d1.symm; have d2' := d2.symm; have d4' := d4.symm
  have hun := hur v lo hi
  simp only [ukey, iv] at hun
  obtain ⟨hln, hlo⟩ := hlr
  simp only [iv] at hln
  simp only [diagramFields, iv] at hself
  simp only [callBody, lookup_node', py_Diagram_node]
  simp only [List.length, List.zip, List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append,
    List.cons_append, ne_eq, not_true, if_false]
  unfold mkNode
  by_cases hlh : lo = hi
  · subst hlh
    simp only [if_true]
    pystep []
    exact ⟨h, by simp [finishCall, iv], hR, Frame.refl D h⟩
  · simp only [hlh, if_false]
    pystep [hlh]
    pystep []
    cases hf : findNode m.nodes ⟨v, lo, hi⟩ with
    | some i =>
      pystep [hself, hu, hun, hf]
      exact ⟨h, by simp [finishCall, iv], hR, Frame.refl D h⟩
    | none =>
      pystep [hself, hu, hun, hf]
      by_cases hsz : lim.nodes ≤ m.nodes.size
      · simp only [ge_iff_le, hsz, if_true]
        pystep [hself, hp, hkl, hln, hpr.1, hsz]
        refine ⟨h ++ [.inst "ResourceLimit" [("args", .tup [.str "nodes"])]], h.length, ?_, ?_,
          hR.append _, Frame.append D h _⟩
        · simp [finishCall]
        · simp [LimitReached.name]
      · simp only [ge_iff_le, hsz, if_false]
        pystep [hself, hp, hkl, hln, hpr.1, hsz]
        pystep [hself, hp, l1, l4, hget_append]
        pystep [hself, hp, l1, l4, hget_append]
        pystep! []
        pystep []
        obtain ⟨hR', hF'⟩ := mrel_push hR hp hpr hu huk hur hf
        refine ⟨_, ?_, hR', hF'⟩
        simp [finishCall, iv, hpr.1, ukey]

end PCSCR.Py
