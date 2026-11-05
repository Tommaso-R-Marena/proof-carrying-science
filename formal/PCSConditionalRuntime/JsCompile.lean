import PCSConditionalRuntime.JsApply
import PCSConditionalRuntime.PyCompile

/-!
# `Diagram.compile` refines `PCSDD.compile`

The formula argument is a heap dictionary tree (`JFRel`): every node is a dictionary whose
`'op'` entry names the connective and whose children are found under `'symbol'`, `'body'`,
`'left'` and `'right'`.  The relation is stated through dictionary lookup, so it holds for any
key order.  Formula dictionaries live at addresses the `Diagram` methods never write.
-/

namespace PCSCR.Js

open PCSCR PCSDD PCSOmega PCSCR.Py

/-- `v` is a heap-encoded formula dictionary tree for the typed formula `f`. -/
def JFRel (D : Addrs) (h : Heap) (names : List String) {n : Nat} : V → BForm n → Prop
  | .ref a, .atom i => ¬ D.mut a ∧ ∃ kvs, hget h a = some (.dict kvs) ∧
      dictFind .js kvs (.str "op") = some (.str "atom") ∧
      dictFind .js kvs (.str "symbol") = some (.str (names.getD i.val ""))
  | .ref a, .tt => ¬ D.mut a ∧ ∃ kvs, hget h a = some (.dict kvs) ∧
      dictFind .js kvs (.str "op") = some (.str "true")
  | .ref a, .ff => ¬ D.mut a ∧ ∃ kvs, hget h a = some (.dict kvs) ∧
      dictFind .js kvs (.str "op") = some (.str "false")
  | .ref a, .not f => ¬ D.mut a ∧ ∃ kvs c, hget h a = some (.dict kvs) ∧
      dictFind .js kvs (.str "op") = some (.str "not") ∧ dictFind .js kvs (.str "body") = some c ∧
      JFRel D h names c f
  | .ref a, .and f g => ¬ D.mut a ∧ ∃ kvs c1 c2, hget h a = some (.dict kvs) ∧
      dictFind .js kvs (.str "op") = some (.str "and") ∧ dictFind .js kvs (.str "left") = some c1 ∧
      dictFind .js kvs (.str "right") = some c2 ∧ JFRel D h names c1 f ∧ JFRel D h names c2 g
  | .ref a, .or f g => ¬ D.mut a ∧ ∃ kvs c1 c2, hget h a = some (.dict kvs) ∧
      dictFind .js kvs (.str "op") = some (.str "or") ∧ dictFind .js kvs (.str "left") = some c1 ∧
      dictFind .js kvs (.str "right") = some c2 ∧ JFRel D h names c1 f ∧ JFRel D h names c2 g
  | .ref a, .imp f g => ¬ D.mut a ∧ ∃ kvs c1 c2, hget h a = some (.dict kvs) ∧
      dictFind .js kvs (.str "op") = some (.str "implies") ∧ dictFind .js kvs (.str "left") = some c1 ∧
      dictFind .js kvs (.str "right") = some c2 ∧ JFRel D h names c1 f ∧ JFRel D h names c2 g
  | _, _ => False

theorem JFRel.frame {D : Addrs} {h h' : Heap} {names : List String} {n : Nat} (hf : Frame D h h') :
    ∀ (f : BForm n) (v : V), JFRel D h names v f → JFRel D h' names v f := by
  intro f
  induction f with
  | atom i =>
    intro v hv; match v, hv with
    | .ref a, ⟨hm, kvs, hg, h1, h2⟩ => exact ⟨hm, kvs, by rw [hf.2 a (hget_lt hg) hm]; exact hg, h1, h2⟩
  | tt =>
    intro v hv; match v, hv with
    | .ref a, ⟨hm, kvs, hg, h1⟩ => exact ⟨hm, kvs, by rw [hf.2 a (hget_lt hg) hm]; exact hg, h1⟩
  | ff =>
    intro v hv; match v, hv with
    | .ref a, ⟨hm, kvs, hg, h1⟩ => exact ⟨hm, kvs, by rw [hf.2 a (hget_lt hg) hm]; exact hg, h1⟩
  | not f ih =>
    intro v hv; match v, hv with
    | .ref a, ⟨hm, kvs, c, hg, h1, h2, h3⟩ =>
      exact ⟨hm, kvs, c, by rw [hf.2 a (hget_lt hg) hm]; exact hg, h1, h2, ih c h3⟩
  | and f g ih1 ih2 =>
    intro v hv; match v, hv with
    | .ref a, ⟨hm, kvs, c1, c2, hg, h1, h2, h3, h4, h5⟩ =>
      exact ⟨hm, kvs, c1, c2, by rw [hf.2 a (hget_lt hg) hm]; exact hg, h1, h2, h3, ih1 c1 h4, ih2 c2 h5⟩
  | or f g ih1 ih2 =>
    intro v hv; match v, hv with
    | .ref a, ⟨hm, kvs, c1, c2, hg, h1, h2, h3, h4, h5⟩ =>
      exact ⟨hm, kvs, c1, c2, by rw [hf.2 a (hget_lt hg) hm]; exact hg, h1, h2, h3, ih1 c1 h4, ih2 c2 h5⟩
  | imp f g ih1 ih2 =>
    intro v hv; match v, hv with
    | .ref a, ⟨hm, kvs, c1, c2, hg, h1, h2, h3, h4, h5⟩ =>
      exact ⟨hm, kvs, c1, c2, by rw [hf.2 a (hget_lt hg) hm]; exact hg, h1, h2, h3, ih1 c1 h4, ih2 c2 h5⟩

theorem mkNode_visits {lim : Limits} {m m' : Mgr} {v lo hi r : Nat}
    (h : mkNode lim m v lo hi = .ok (r, m')) : m'.visits = m.visits := by
  unfold mkNode at h
  split at h
  · cases h; rfl
  · split at h
    · cases h; rfl
    · split at h
      · cases h
      · cases h; rfl

theorem apply_visits {n : Nat} {lim : Limits} :
    ∀ (fuel : Nat) (op : BOp) (a b : Nat) (m : Mgr) (r : Nat) (m' : Mgr),
      apply n lim fuel op a b m = .ok (r, m') → m'.visits = m.visits
  | 0, _, _, _, _, _, _, h => by simp [apply] at h
  | fuel + 1, op, a, b, m, r, m', h => by
    rw [apply_succ_eq] at h
    split at h
    · cases h
    · unfold applyRest at h
      split at h
      · cases h; rfl
      · split at h
        · cases h; rfl
        · split at h
          · cases h
          · rename_i lo m1 h1
            split at h
            · cases h
            · rename_i hi m2 h2
              split at h
              · cases h
              · rename_i r3 m3 h3
                cases h
                simp only
                rw [mkNode_visits h3, apply_visits _ _ _ _ _ _ _ h2, apply_visits _ _ _ _ _ _ _ h1]

theorem compile_visits {n : Nat} {lim : Limits} :
    ∀ (f : BForm n) (m : Mgr) (r : Nat) (m' : Mgr),
      compile n lim f m = .ok (r, m') → m'.visits = m.visits + f.size := by
  intro f
  induction f with
  | atom i => intro m r m' h; simp only [compile] at h; rw [mkNode_visits h]; simp [BForm.size]
  | tt => intro m r m' h; simp only [compile] at h; cases h; simp [BForm.size]
  | ff => intro m r m' h; simp only [compile] at h; cases h; simp [BForm.size]
  | not f ih =>
    intro m r m' h; simp only [compile] at h
    split at h
    · cases h
    · rename_i x m1 h1
      rw [apply_visits _ _ _ _ _ _ _ h, ih _ _ _ h1]; simp [BForm.size]; omega
  | and f g ihf ihg =>
    intro m r m' h; simp only [compile] at h
    split at h
    · cases h
    · rename_i x m1 h1
      split at h
      · cases h
      · rename_i y m2 h2
        rw [apply_visits _ _ _ _ _ _ _ h, ihg _ _ _ h2, ihf _ _ _ h1]; simp [BForm.size]; omega
  | or f g ihf ihg =>
    intro m r m' h; simp only [compile] at h
    split at h
    · cases h
    · rename_i x m1 h1
      split at h
      · cases h
      · rename_i y m2 h2
        rw [apply_visits _ _ _ _ _ _ _ h, ihg _ _ _ h2, ihf _ _ _ h1]; simp [BForm.size]; omega
  | imp f g ihf ihg =>
    intro m r m' h; simp only [compile] at h
    split at h
    · cases h
    · rename_i x m1 h1
      split at h
      · cases h
      · rename_i y m2 h2
        split at h
        · cases h
        · rename_i z m3 h3
          rw [apply_visits _ _ _ _ _ _ _ h, apply_visits _ _ _ _ _ _ _ h3, ihg _ _ _ h2, ihf _ _ _ h1]
          simp [BForm.size]; omega

/-- `Array.prototype.indexOf` on a duplicate-free list of names. -/
theorem jfindIdx_names : ∀ {names : List String}, names.Nodup → ∀ {i : Nat} (hi : i < names.length),
    List.findIdx? ((fun y => eqJs y (V.str names[i])) ∘ V.str) names = some i
  | [], _, i, hi => by simp at hi
  | x :: xs, hd, 0, hi => by simp [List.findIdx?_cons, eqJs]
  | x :: xs, hd, j + 1, hi => by
      have hj : j < xs.length := by simp at hi; omega
      have hx : x ∉ xs := (List.nodup_cons.1 hd).1
      have hne : x ≠ xs[j] := fun e => hx (e ▸ List.getElem_mem _)
      have ih := jfindIdx_names (List.nodup_cons.1 hd).2 hj
      simp only [List.getElem_cons_succ, List.findIdx?_cons]
      simp [eqJs, hne] at ih ⊢
      simp [ih]

/-- The heap after a counter update relates to the updated manager. -/
theorem JMRel.setCounters {names : List String} {lim : Limits} {D : Addrs} {h : Heap} {m : Mgr}
    (hR : JMRel names lim D h m) (m' : Mgr) (hn : m'.nodes = m.nodes) (hm : m'.memo = m.memo) :
    JMRel names lim D (hset h D.self (.inst "Diagram" (jdiagramFields D m'))) m' ∧
    Frame D h (hset h D.self (.inst "Diagram" (jdiagramFields D m'))) := by
  have hl := hR.addrs_lt
  have hne := hR.neqs
  have hF : Frame D h (hset h D.self (.inst "Diagram" (jdiagramFields D m'))) :=
    Frame.hset _ _ (Or.inl rfl)
  obtain ⟨p, hp, hpr⟩ := hR.nodes
  obtain ⟨u, hu, hur⟩ := hR.uniq
  obtain ⟨mm, hmm, hmr⟩ := hR.memo
  refine ⟨hR.transport hF ?_ ⟨p, ?_, hn ▸ hpr.frame hF⟩ ⟨u, ?_, hn ▸ hur⟩ ⟨mm, ?_, hm ▸ hmr⟩, hF⟩
  · simp [hget_hset, hl.1]
  · simp [hget_hset, hne]; exact hp
  · simp [hget_hset, hne]; exact hu
  · simp [hget_hset, hne]; exact hmm


/-- The simulation statement for one formula. -/
def JCompileOK (ext : Ext) (names : List String) (lim : Limits) (D : Addrs) (f : BForm names.length) : Prop :=
  ∀ (k : Nat), applyFuel lim + fdepth f + 1 ≤ k →
    ∀ (h : Heap) (m : Mgr) (v : V), JMRel names lim D h m → Inv names.length lim m →
    m.visits + f.size ≤ 9007199254740991 → JFRel D h names v f →
    JSimOut names lim D h (compile names.length lim f m)
      ((interp (jsCtx ext) (k + 1)).call "Diagram.compile" [.ref D.self, v] h)

set_option maxHeartbeats 8000000 in
theorem jcompile_atom (ext : Ext) {names : List String} {lim : Limits} {D : Addrs} (hnd : names.Nodup) (i : Fin names.length) :
    JCompileOK ext names lim D (.atom i) := by
  intro k hk h m v hR hinv hvis hv
  obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by omega⟩
  match v, hv with
  | .ref a, ⟨hma, kvs, hg, hop, hsym⟩ =>
  have hself := hR.self
  simp only [jdiagramFields, iv] at hself
  have hl := hR.addrs_lt
  have hne := hR.neqs
  have hnames := hR.names
  rw [interp_succ_call]
  simp only [callBody, lookup_compile, js_Diagram_compile, jsCtx_prog]
  simp only [List.length, List.zip, List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append,
    List.cons_append, ne_eq, not_true, if_false]
  rw [execB_cons', js_aug_attr_add1 ext _ _ _ D.self "Diagram" _ "visits" (m.visits) (by simp [Env.get]) hself
    (by simp [fieldGet]) (by simp only [MAX_SAFE, BForm.size] at hvis ⊢; omega) (by simp only [MAX_SAFE]; omega)]
  simp only [seqF_normal, fieldSet, String.reduceEq, if_false, if_true]
  obtain ⟨hR1, hF1⟩ := hR.setCounters { m with visits := m.visits + 1 } rfl rfl
  simp only [jdiagramFields, iv, Int.natCast_add, Int.natCast_one] at hR1 hF1
  have hsa : D.self ≠ a := fun e => hma (Or.inl e.symm)
  have hin : i.val < names.length := i.isLt
  jsstep [hsa, hg, hop]
  have hidx := jfindIdx_names hnd hin
  simp only [eqJs] at hidx
  jsstep [hsa, hg, hop, hsym, hnames, hl.1, hl.2.1, hne, interp_succ_call, hidx]
  have s3 := node_spec ext (interp (jsCtx ext) k') hR1 i.val 0 1
  simp only [compile]
  cases hx3 : mkNode lim { m with visits := m.visits + 1 } i.val 0 1 with
  | error p =>
    obtain ⟨e, m3⟩ := p
    try rw [hx3] at s3
    obtain ⟨H3, a3, e3, ha3, R3, F3⟩ := s3
    simp only [iv, Int.natCast_zero, Int.natCast_one] at e3
    simp only [e3]
    exact ⟨H3, a3, by simp [finishCall], ha3, R3, hF1.trans F3⟩
  | ok p =>
    obtain ⟨r, m3⟩ := p
    try rw [hx3] at s3
    obtain ⟨H3, e3, R3, F3⟩ := s3
    simp only [iv, Int.natCast_zero, Int.natCast_one] at e3
    simp only [e3]
    exact ⟨H3, by simp [finishCall, iv], R3, hF1.trans F3⟩

set_option maxHeartbeats 8000000 in
theorem jcompile_tt (ext : Ext) {names : List String} {lim : Limits} {D : Addrs}  :
    JCompileOK ext names lim D (.tt) := by
  intro k hk h m v hR hinv hvis hv
  obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by omega⟩
  match v, hv with
  | .ref a, ⟨hma, kvs, hg, hop⟩ =>
  have hself := hR.self
  simp only [jdiagramFields, iv] at hself
  have hl := hR.addrs_lt
  have hne := hR.neqs
  rw [interp_succ_call]
  simp only [callBody, lookup_compile, js_Diagram_compile, jsCtx_prog]
  simp only [List.length, List.zip, List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append,
    List.cons_append, ne_eq, not_true, if_false]
  rw [execB_cons', js_aug_attr_add1 ext _ _ _ D.self "Diagram" _ "visits" (m.visits) (by simp [Env.get]) hself
    (by simp [fieldGet]) (by simp only [MAX_SAFE, BForm.size] at hvis ⊢; omega) (by simp only [MAX_SAFE]; omega)]
  simp only [seqF_normal, fieldSet, String.reduceEq, if_false, if_true]
  obtain ⟨hR1, hF1⟩ := hR.setCounters { m with visits := m.visits + 1 } rfl rfl
  simp only [jdiagramFields, iv, Int.natCast_add, Int.natCast_one] at hR1 hF1
  have hsa : D.self ≠ a := fun e => hma (Or.inl e.symm)
  jsstep [hsa, hg, hop]
  jsstep []
  exact ⟨_, by simp [finishCall, iv], hR1, hF1⟩

set_option maxHeartbeats 8000000 in
theorem jcompile_ff (ext : Ext) {names : List String} {lim : Limits} {D : Addrs}  :
    JCompileOK ext names lim D (.ff) := by
  intro k hk h m v hR hinv hvis hv
  obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by omega⟩
  match v, hv with
  | .ref a, ⟨hma, kvs, hg, hop⟩ =>
  have hself := hR.self
  simp only [jdiagramFields, iv] at hself
  have hl := hR.addrs_lt
  have hne := hR.neqs
  rw [interp_succ_call]
  simp only [callBody, lookup_compile, js_Diagram_compile, jsCtx_prog]
  simp only [List.length, List.zip, List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append,
    List.cons_append, ne_eq, not_true, if_false]
  rw [execB_cons', js_aug_attr_add1 ext _ _ _ D.self "Diagram" _ "visits" (m.visits) (by simp [Env.get]) hself
    (by simp [fieldGet]) (by simp only [MAX_SAFE, BForm.size] at hvis ⊢; omega) (by simp only [MAX_SAFE]; omega)]
  simp only [seqF_normal, fieldSet, String.reduceEq, if_false, if_true]
  obtain ⟨hR1, hF1⟩ := hR.setCounters { m with visits := m.visits + 1 } rfl rfl
  simp only [jdiagramFields, iv, Int.natCast_add, Int.natCast_one] at hR1 hF1
  have hsa : D.self ≠ a := fun e => hma (Or.inl e.symm)
  jsstep [hsa, hg, hop]
  jsstep []
  exact ⟨_, by simp [finishCall, iv], hR1, hF1⟩

set_option maxHeartbeats 8000000 in
theorem jcompile_not (ext : Ext) {names : List String} {lim : Limits} {D : Addrs} (f : BForm names.length) (ih : JCompileOK ext names lim D f) :
    JCompileOK ext names lim D (.not f) := by
  intro k hk h m v hR hinv hvis hv
  obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by omega⟩
  match v, hv with
  | .ref a, ⟨hma, kvs, c, hg, hop, hbody, hc⟩ =>
  have hself := hR.self
  simp only [jdiagramFields, iv] at hself
  have hl := hR.addrs_lt
  have hne := hR.neqs
  rw [interp_succ_call]
  simp only [callBody, lookup_compile, js_Diagram_compile, jsCtx_prog]
  simp only [List.length, List.zip, List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append,
    List.cons_append, ne_eq, not_true, if_false]
  rw [execB_cons', js_aug_attr_add1 ext _ _ _ D.self "Diagram" _ "visits" (m.visits) (by simp [Env.get]) hself
    (by simp [fieldGet]) (by simp only [MAX_SAFE, BForm.size] at hvis ⊢; omega) (by simp only [MAX_SAFE]; omega)]
  simp only [seqF_normal, fieldSet, String.reduceEq, if_false, if_true]
  obtain ⟨hR1, hF1⟩ := hR.setCounters { m with visits := m.visits + 1 } rfl rfl
  simp only [jdiagramFields, iv, Int.natCast_add, Int.natCast_one] at hR1 hF1
  have hsa : D.self ≠ a := fun e => hma (Or.inl e.symm)
  jsstep [hsa, hg, hop]
  have hinv1 : Inv names.length lim { m with visits := m.visits + 1 } := hinv.visits _
  have s1 := ih k' (by simp only [fdepth] at hk; omega) _ _ c hR1 hinv1 (by simp only [BForm.size] at hvis ⊢; omega) (JFRel.frame hF1 f c hc)
  simp only [compile]
  cases hx1 : compile names.length lim f { m with visits := m.visits + 1 } with
  | error p =>
    obtain ⟨e, m1⟩ := p
    try rw [hx1] at s1
    obtain ⟨H1, a1, e1, ha1, R1, F1⟩ := s1
    jsstep [hsa, hg, hbody, hself, hl.1, e1]
    exact ⟨H1, a1, by simp [finishCall], ha1, R1, hF1.trans F1⟩
  | ok p =>
    obtain ⟨x, m1⟩ := p
    try rw [hx1] at s1
    obtain ⟨H1, e1, R1, F1⟩ := s1
    dsimp only
    obtain ⟨i1, ex1, _, r1, _⟩ := compile_spec f _ x m1 hinv1 hx1
    have hself1 := R1.self
    simp only [jdiagramFields, iv] at hself1
    have s2 := japply_sim ext .xor (applyFuel lim) k' (by omega) H1 m1 x 1 R1 i1 r1 (by omega)
      (by unfold applyFuel; omega)
    cases hx2 : apply names.length lim (applyFuel lim) .xor x 1 m1 with
    | error p =>
      obtain ⟨e, m2⟩ := p
      try rw [hx2] at s2
      obtain ⟨H2, a2, e2, ha2, R2, F2⟩ := s2
      simp only [iv, BOp.name, Int.natCast_one] at e1 e2
      jsstep [hsa, hg, hbody, hself, hl.1, e1, hself1, e2]
      exact ⟨H2, a2, by simp [finishCall], ha2, R2, hF1.trans (F1.trans F2)⟩
    | ok p =>
      obtain ⟨r, m2⟩ := p
      try rw [hx2] at s2
      obtain ⟨H2, e2, R2, F2⟩ := s2
      simp only [iv, BOp.name, Int.natCast_one] at e1 e2
      jsstep [hsa, hg, hbody, hself, hl.1, e1, hself1, e2]
      exact ⟨H2, by simp [finishCall, iv], R2, hF1.trans (F1.trans F2)⟩

set_option maxHeartbeats 8000000 in
theorem jcompile_and (ext : Ext) {names : List String} {lim : Limits} {D : Addrs} (f g : BForm names.length) (ih1 : JCompileOK ext names lim D f) (ih2 : JCompileOK ext names lim D g) :
    JCompileOK ext names lim D (.and f g) := by
  intro k hk h m v hR hinv hvis hv
  obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by omega⟩
  match v, hv with
  | .ref a, ⟨hma, kvs, c1, c2, hg, hop, hleft, hright, hc1, hc2⟩ =>
  have hself := hR.self
  simp only [jdiagramFields, iv] at hself
  have hl := hR.addrs_lt
  have hne := hR.neqs
  rw [interp_succ_call]
  simp only [callBody, lookup_compile, js_Diagram_compile, jsCtx_prog]
  simp only [List.length, List.zip, List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append,
    List.cons_append, ne_eq, not_true, if_false]
  rw [execB_cons', js_aug_attr_add1 ext _ _ _ D.self "Diagram" _ "visits" (m.visits) (by simp [Env.get]) hself
    (by simp [fieldGet]) (by simp only [MAX_SAFE, BForm.size] at hvis ⊢; omega) (by simp only [MAX_SAFE]; omega)]
  simp only [seqF_normal, fieldSet, String.reduceEq, if_false, if_true]
  obtain ⟨hR1, hF1⟩ := hR.setCounters { m with visits := m.visits + 1 } rfl rfl
  simp only [jdiagramFields, iv, Int.natCast_add, Int.natCast_one] at hR1 hF1
  have hsa : D.self ≠ a := fun e => hma (Or.inl e.symm)
  jsstep [hsa, hg, hop]
  have hinv1 : Inv names.length lim { m with visits := m.visits + 1 } := hinv.visits _
  have s1 := ih1 k' (by simp only [fdepth] at hk; omega) _ _ c1 hR1 hinv1 (by simp only [BForm.size] at hvis ⊢; omega) (JFRel.frame hF1 f c1 hc1)
  simp only [compile]
  cases hx1 : compile names.length lim f { m with visits := m.visits + 1 } with
  | error p =>
    obtain ⟨e, m1⟩ := p
    try rw [hx1] at s1
    obtain ⟨H1, a1, e1, ha1, R1, F1⟩ := s1
    jsstep [hsa, hg, hleft, hself, hl.1, e1]
    exact ⟨H1, a1, by simp [finishCall], ha1, R1, hF1.trans F1⟩
  | ok p =>
    obtain ⟨x, m1⟩ := p
    try rw [hx1] at s1
    obtain ⟨H1, e1, R1, F1⟩ := s1
    dsimp only
    obtain ⟨i1, ex1, _, r1, _⟩ := compile_spec f _ x m1 hinv1 hx1
    jsstep [hsa, hg, hleft, hself, hl.1, e1]
    have hself1 := R1.self
    simp only [jdiagramFields, iv] at hself1
    have hF01 := hF1.trans F1
    have hg1 : hget H1 a = some (.dict kvs) := by rw [hF01.2 a (hget_lt hg) hma]; exact hg
    have s2 := ih2 k' (by simp only [fdepth] at hk; omega) _ _ c2 R1 i1 (by have := compile_visits f _ x m1 hx1; simp only [BForm.size] at hvis this; omega) (JFRel.frame hF01 g c2 hc2)
    cases hx2 : compile names.length lim g m1 with
    | error p =>
      obtain ⟨e, m2⟩ := p
      try rw [hx2] at s2
      obtain ⟨H2, a2, e2, ha2, R2, F2⟩ := s2
      jsrun [hg1, hright, hself1, e2]
      exact ⟨H2, a2, by simp [finishCall], ha2, R2, hF01.trans F2⟩
    | ok p =>
      obtain ⟨y, m2⟩ := p
      try rw [hx2] at s2
      obtain ⟨H2, e2, R2, F2⟩ := s2
      dsimp only
      obtain ⟨i2, ex2, _, r2, _⟩ := compile_spec g _ y m2 i1 hx2
      jsrun [hg1, hright, hself1, e2]
      have hself2 := R2.self
      simp only [jdiagramFields, iv] at hself2
      have hF02 := hF01.trans F2
      have hg2 : hget H2 a = some (.dict kvs) := by rw [hF02.2 a (hget_lt hg) hma]; exact hg
      have hx2' : x < m2.nodes.size + 2 := by have := ex2.1; omega
      have s3 := japply_sim ext .and (applyFuel lim) k' (by omega) H2 m2 x y R2 i2 hx2' r2
        (by unfold applyFuel; omega)
      cases hx3 : apply names.length lim (applyFuel lim) .and x y m2 with
      | error p =>
        obtain ⟨e, m3⟩ := p
        try rw [hx3] at s3
        obtain ⟨H3, a3, e3, ha3, R3, F3⟩ := s3
        simp only [iv, BOp.name] at e3
        jsrun [hg2, hop, hself2, e3]
        exact ⟨H3, a3, by simp [finishCall], ha3, R3, hF02.trans F3⟩
      | ok p =>
        obtain ⟨r, m3⟩ := p
        try rw [hx3] at s3
        obtain ⟨H3, e3, R3, F3⟩ := s3
        simp only [iv, BOp.name] at e3
        jsrun [hg2, hop, hself2, e3]
        exact ⟨H3, by simp [finishCall, iv], R3, hF02.trans F3⟩

set_option maxHeartbeats 8000000 in
theorem jcompile_or (ext : Ext) {names : List String} {lim : Limits} {D : Addrs} (f g : BForm names.length) (ih1 : JCompileOK ext names lim D f) (ih2 : JCompileOK ext names lim D g) :
    JCompileOK ext names lim D (.or f g) := by
  intro k hk h m v hR hinv hvis hv
  obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by omega⟩
  match v, hv with
  | .ref a, ⟨hma, kvs, c1, c2, hg, hop, hleft, hright, hc1, hc2⟩ =>
  have hself := hR.self
  simp only [jdiagramFields, iv] at hself
  have hl := hR.addrs_lt
  have hne := hR.neqs
  rw [interp_succ_call]
  simp only [callBody, lookup_compile, js_Diagram_compile, jsCtx_prog]
  simp only [List.length, List.zip, List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append,
    List.cons_append, ne_eq, not_true, if_false]
  rw [execB_cons', js_aug_attr_add1 ext _ _ _ D.self "Diagram" _ "visits" (m.visits) (by simp [Env.get]) hself
    (by simp [fieldGet]) (by simp only [MAX_SAFE, BForm.size] at hvis ⊢; omega) (by simp only [MAX_SAFE]; omega)]
  simp only [seqF_normal, fieldSet, String.reduceEq, if_false, if_true]
  obtain ⟨hR1, hF1⟩ := hR.setCounters { m with visits := m.visits + 1 } rfl rfl
  simp only [jdiagramFields, iv, Int.natCast_add, Int.natCast_one] at hR1 hF1
  have hsa : D.self ≠ a := fun e => hma (Or.inl e.symm)
  jsstep [hsa, hg, hop]
  have hinv1 : Inv names.length lim { m with visits := m.visits + 1 } := hinv.visits _
  have s1 := ih1 k' (by simp only [fdepth] at hk; omega) _ _ c1 hR1 hinv1 (by simp only [BForm.size] at hvis ⊢; omega) (JFRel.frame hF1 f c1 hc1)
  simp only [compile]
  cases hx1 : compile names.length lim f { m with visits := m.visits + 1 } with
  | error p =>
    obtain ⟨e, m1⟩ := p
    try rw [hx1] at s1
    obtain ⟨H1, a1, e1, ha1, R1, F1⟩ := s1
    jsstep [hsa, hg, hleft, hself, hl.1, e1]
    exact ⟨H1, a1, by simp [finishCall], ha1, R1, hF1.trans F1⟩
  | ok p =>
    obtain ⟨x, m1⟩ := p
    try rw [hx1] at s1
    obtain ⟨H1, e1, R1, F1⟩ := s1
    dsimp only
    obtain ⟨i1, ex1, _, r1, _⟩ := compile_spec f _ x m1 hinv1 hx1
    jsstep [hsa, hg, hleft, hself, hl.1, e1]
    have hself1 := R1.self
    simp only [jdiagramFields, iv] at hself1
    have hF01 := hF1.trans F1
    have hg1 : hget H1 a = some (.dict kvs) := by rw [hF01.2 a (hget_lt hg) hma]; exact hg
    have s2 := ih2 k' (by simp only [fdepth] at hk; omega) _ _ c2 R1 i1 (by have := compile_visits f _ x m1 hx1; simp only [BForm.size] at hvis this; omega) (JFRel.frame hF01 g c2 hc2)
    cases hx2 : compile names.length lim g m1 with
    | error p =>
      obtain ⟨e, m2⟩ := p
      try rw [hx2] at s2
      obtain ⟨H2, a2, e2, ha2, R2, F2⟩ := s2
      jsrun [hg1, hright, hself1, e2]
      exact ⟨H2, a2, by simp [finishCall], ha2, R2, hF01.trans F2⟩
    | ok p =>
      obtain ⟨y, m2⟩ := p
      try rw [hx2] at s2
      obtain ⟨H2, e2, R2, F2⟩ := s2
      dsimp only
      obtain ⟨i2, ex2, _, r2, _⟩ := compile_spec g _ y m2 i1 hx2
      jsrun [hg1, hright, hself1, e2]
      have hself2 := R2.self
      simp only [jdiagramFields, iv] at hself2
      have hF02 := hF01.trans F2
      have hg2 : hget H2 a = some (.dict kvs) := by rw [hF02.2 a (hget_lt hg) hma]; exact hg
      have hx2' : x < m2.nodes.size + 2 := by have := ex2.1; omega
      have s3 := japply_sim ext .or (applyFuel lim) k' (by omega) H2 m2 x y R2 i2 hx2' r2
        (by unfold applyFuel; omega)
      cases hx3 : apply names.length lim (applyFuel lim) .or x y m2 with
      | error p =>
        obtain ⟨e, m3⟩ := p
        try rw [hx3] at s3
        obtain ⟨H3, a3, e3, ha3, R3, F3⟩ := s3
        simp only [iv, BOp.name] at e3
        jsrun [hg2, hop, hself2, e3]
        exact ⟨H3, a3, by simp [finishCall], ha3, R3, hF02.trans F3⟩
      | ok p =>
        obtain ⟨r, m3⟩ := p
        try rw [hx3] at s3
        obtain ⟨H3, e3, R3, F3⟩ := s3
        simp only [iv, BOp.name] at e3
        jsrun [hg2, hop, hself2, e3]
        exact ⟨H3, by simp [finishCall, iv], R3, hF02.trans F3⟩

set_option maxHeartbeats 8000000 in
theorem jcompile_imp (ext : Ext) {names : List String} {lim : Limits} {D : Addrs} (f g : BForm names.length) (ih1 : JCompileOK ext names lim D f) (ih2 : JCompileOK ext names lim D g) :
    JCompileOK ext names lim D (.imp f g) := by
  intro k hk h m v hR hinv hvis hv
  obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by omega⟩
  match v, hv with
  | .ref a, ⟨hma, kvs, c1, c2, hg, hop, hleft, hright, hc1, hc2⟩ =>
  have hself := hR.self
  simp only [jdiagramFields, iv] at hself
  have hl := hR.addrs_lt
  have hne := hR.neqs
  rw [interp_succ_call]
  simp only [callBody, lookup_compile, js_Diagram_compile, jsCtx_prog]
  simp only [List.length, List.zip, List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append,
    List.cons_append, ne_eq, not_true, if_false]
  rw [execB_cons', js_aug_attr_add1 ext _ _ _ D.self "Diagram" _ "visits" (m.visits) (by simp [Env.get]) hself
    (by simp [fieldGet]) (by simp only [MAX_SAFE, BForm.size] at hvis ⊢; omega) (by simp only [MAX_SAFE]; omega)]
  simp only [seqF_normal, fieldSet, String.reduceEq, if_false, if_true]
  obtain ⟨hR1, hF1⟩ := hR.setCounters { m with visits := m.visits + 1 } rfl rfl
  simp only [jdiagramFields, iv, Int.natCast_add, Int.natCast_one] at hR1 hF1
  have hsa : D.self ≠ a := fun e => hma (Or.inl e.symm)
  jsstep [hsa, hg, hop]
  have hinv1 : Inv names.length lim { m with visits := m.visits + 1 } := hinv.visits _
  have s1 := ih1 k' (by simp only [fdepth] at hk; omega) _ _ c1 hR1 hinv1 (by simp only [BForm.size] at hvis ⊢; omega) (JFRel.frame hF1 f c1 hc1)
  simp only [compile]
  cases hx1 : compile names.length lim f { m with visits := m.visits + 1 } with
  | error p =>
    obtain ⟨e, m1⟩ := p
    try rw [hx1] at s1
    obtain ⟨H1, a1, e1, ha1, R1, F1⟩ := s1
    jsstep [hsa, hg, hleft, hself, hl.1, e1]
    exact ⟨H1, a1, by simp [finishCall], ha1, R1, hF1.trans F1⟩
  | ok p =>
    obtain ⟨x, m1⟩ := p
    try rw [hx1] at s1
    obtain ⟨H1, e1, R1, F1⟩ := s1
    dsimp only
    obtain ⟨i1, ex1, _, r1, _⟩ := compile_spec f _ x m1 hinv1 hx1
    jsstep [hsa, hg, hleft, hself, hl.1, e1]
    have hself1 := R1.self
    simp only [jdiagramFields, iv] at hself1
    have hF01 := hF1.trans F1
    have hg1 : hget H1 a = some (.dict kvs) := by rw [hF01.2 a (hget_lt hg) hma]; exact hg
    have s2 := ih2 k' (by simp only [fdepth] at hk; omega) _ _ c2 R1 i1 (by have := compile_visits f _ x m1 hx1; simp only [BForm.size] at hvis this; omega) (JFRel.frame hF01 g c2 hc2)
    cases hx2 : compile names.length lim g m1 with
    | error p =>
      obtain ⟨e, m2⟩ := p
      try rw [hx2] at s2
      obtain ⟨H2, a2, e2, ha2, R2, F2⟩ := s2
      jsrun [hg1, hright, hself1, e2]
      exact ⟨H2, a2, by simp [finishCall], ha2, R2, hF01.trans F2⟩
    | ok p =>
      obtain ⟨y, m2⟩ := p
      try rw [hx2] at s2
      obtain ⟨H2, e2, R2, F2⟩ := s2
      dsimp only
      obtain ⟨i2, ex2, _, r2, _⟩ := compile_spec g _ y m2 i1 hx2
      jsrun [hg1, hright, hself1, e2]
      have hself2 := R2.self
      simp only [jdiagramFields, iv] at hself2
      have hF02 := hF01.trans F2
      have hg2 : hget H2 a = some (.dict kvs) := by rw [hF02.2 a (hget_lt hg) hma]; exact hg
      have hx2' : x < m2.nodes.size + 2 := by have := ex2.1; omega
      have s3 := japply_sim ext .xor (applyFuel lim) k' (by omega) H2 m2 x 1 R2 i2 hx2' (by omega)
        (by unfold applyFuel; omega)
      cases hx3 : apply names.length lim (applyFuel lim) .xor x 1 m2 with
      | error p =>
        obtain ⟨e, m3⟩ := p
        try rw [hx3] at s3
        obtain ⟨H3, a3, e3, ha3, R3, F3⟩ := s3
        simp only [iv, BOp.name, Int.natCast_one] at e3
        jsrun [hg2, hop, hself2, e3]
        exact ⟨H3, a3, by simp [finishCall], ha3, R3, hF02.trans F3⟩
      | ok p =>
        obtain ⟨nx, m3⟩ := p
        try rw [hx3] at s3
        obtain ⟨H3, e3, R3, F3⟩ := s3
        dsimp only
        obtain ⟨i3, ex3, _, _, r3, _, _⟩ := apply_spec _ _ _ _ _ nx m3 i2 hx2' (by omega) hx3
        have hself3 := R3.self
        simp only [jdiagramFields, iv] at hself3
        have hy3 : y < m3.nodes.size + 2 := by have := ex3.1; omega
        have s4 := japply_sim ext .or (applyFuel lim) k' (by omega) H3 m3 nx y R3 i3 r3 hy3
          (by unfold applyFuel; omega)
        cases hx4 : apply names.length lim (applyFuel lim) .or nx y m3 with
        | error p =>
          obtain ⟨e, m4⟩ := p
          try rw [hx4] at s4
          obtain ⟨H4, a4, e4, ha4, R4, F4⟩ := s4
          simp only [iv, BOp.name, Int.natCast_one] at e3 e4
          jsrun [hg2, hop, hself2, e3, hself3, e4]
          exact ⟨H4, a4, by simp [finishCall], ha4, R4, hF02.trans (F3.trans F4)⟩
        | ok p =>
          obtain ⟨r, m4⟩ := p
          try rw [hx4] at s4
          obtain ⟨H4, e4, R4, F4⟩ := s4
          simp only [iv, BOp.name, Int.natCast_one] at e3 e4
          jsrun [hg2, hop, hself2, e3, hself3, e4]
          exact ⟨H4, by simp [finishCall, iv], R4, hF02.trans (F3.trans F4)⟩


/-- **`Diagram.compile` simulates the reference `compile`** (visit counter, node creation for
atoms, the `xor`/`or` encodings of negation and implication, and resource exhaustion). -/
theorem jcompile_sim (ext : Ext) {names : List String} {lim : Limits} {D : Addrs}
    (hnd : names.Nodup) : ∀ (f : BForm names.length), JCompileOK ext names lim D f
  | .atom i => jcompile_atom ext hnd i
  | .tt => jcompile_tt ext
  | .ff => jcompile_ff ext
  | .not f => jcompile_not ext f (jcompile_sim ext hnd f)
  | .and f g => jcompile_and ext f g (jcompile_sim ext hnd f) (jcompile_sim ext hnd g)
  | .or f g => jcompile_or ext f g (jcompile_sim ext hnd f) (jcompile_sim ext hnd g)
  | .imp f g => jcompile_imp ext f g (jcompile_sim ext hnd f) (jcompile_sim ext hnd g)

end PCSCR.Js
