import PCSConditionalRuntime.PyConj
import PCSConditionalRuntime.PyWalk

/-!
# `Diagram.world` refines `PCSDD.world` and the witness-step counter

The values dictionary is the freshly allocated last heap object; the loop only writes the
`Diagram` instance and that dictionary.  `world_loop` follows the `while root >= 2` loop along
`pyWalk`; `world_sim` combines it with `pyWalk_world`.
-/

namespace PCSCR.Py

open PCSCR PCSDD PCSOmega

theorem hset_append_left {G : Heap} {a : Nat} (o x : Obj) (ha : a < G.length) :
    hset (G ++ [o]) a x = hset G a x ++ [o] := by
  simp [hset, List.set_append_left _ _ ha]

theorem hset_append_last (G : Heap) (o x : Obj) : hset (G ++ [o]) G.length x = G ++ [x] := by
  simp [hset]

theorem hset_append_last' (G : Heap) (o x : Obj) (n : Nat) (hn : G.length = n) :
    hset (G ++ [o]) n x = G ++ [x] := by
  subst hn; simp [hset]

theorem interp_succ_whileLoop (c : Ctx) (k : Nat) (env : Env) (h : Heap) (e : E) (body : List S) :
    (interp c (k + 1)).whileLoop env h e body = whileIter c (interp c k) env h e body := rfl

def worldCond : E := E.bin BinOp.ge (E.var "root") (E.lit (V.int 2))

def worldBody : List S :=
  [S.aug (Tgt.attr (E.var "self") "witness_steps") BinOp.add (E.lit (V.int 1)),
   S.assign [Tgt.tup [Tgt.name "var", Tgt.name "low", Tgt.name "high"]]
     (E.sub (E.attr (E.var "self") "nodes") (E.bin BinOp.sub (E.var "root") (E.lit (V.int 2)))),
   S.assign [Tgt.sub (E.var "values") (E.sub (E.attr (E.var "self") "names") (E.var "var"))]
     (E.bin BinOp.eq (E.var "low") (E.lit (V.int 0))),
   S.assign [Tgt.name "root"]
     (E.cond (E.bin BinOp.eq (E.var "low") (E.lit (V.int 0))) (E.var "high") (E.var "low"))]

/-- **The witness loop follows `pyWalk`.** -/
theorem world_loop (ext : Ext) {names : List String} {lim : Limits} {D : Addrs} :
    ∀ (f k : Nat), f ≤ k → ∀ (H : Heap) (m : Mgr) (u : Nat) (kvs kvs' : List (V × V)) (st' : Nat) (env : Env),
      MRel names lim D H m → Inv names.length lim m → u < m.nodes.size + 2 →
      env.get "root" = some (iv u) → env.get "values" = some (.ref H.length) →
      env.get "self" = some (.ref D.self) →
      pyWalk names m.nodes f u kvs m.wsteps = (kvs', st', 1) →
      ∃ env' H', (interp (pyCtx ext) (k + 1)).whileLoop env (H ++ [.dict kvs]) worldCond worldBody =
          .ok (.normal env') (H' ++ [.dict kvs']) ∧
        env'.get "root" = some (iv 1) ∧ env'.get "values" = some (.ref H.length) ∧
        MRel names lim D H' { m with wsteps := st' } ∧ Frame D H H' ∧ H'.length = H.length := by
  intro f
  induction f with
  | zero =>
    intro k _ H m u kvs kvs' st' env hR hinv hu hroot hval hself hw
    simp only [pyWalk, Prod.mk.injEq] at hw
    obtain ⟨rfl, rfl, rfl⟩ := hw
    rw [interp_succ_whileLoop]
    simp [whileIter, worldCond, evalE, hroot, binOp, cmpOp, bindS, truthy, iv]
    refine ⟨env, H, ⟨rfl, rfl⟩, hroot, hval, ?_, Frame.refl D H, rfl⟩
    simpa using hR
  | succ f ih =>
    intro k hk H m u kvs kvs' st' env hR hinv hu hroot hval hself hw
    obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by omega⟩
    by_cases h2 : 2 ≤ u
    · obtain ⟨ptrs, hp, hpr⟩ := hR.nodes
      obtain ⟨nd, b, hg, hpb, hmb, hb⟩ := node_ptr hpr h2 hu
      obtain ⟨hvn, hlo, hhi, hne0, _, _⟩ := hinv.valid.node hg
      have hself' := hR.self
      simp only [diagramFields, iv] at hself' hb
      have hnames := hR.names
      have hl := hR.addrs_lt
      have hne := hR.neqs
      have hbl := hget_lt hb
      simp only [pyWalk, h2, if_true, hg] at hw
      rw [interp_succ_whileLoop]
      have h2' : ((u:Int) ≥ 2) := by omega
      simp only [whileIter, worldCond, evalE, hroot, Out.bind_ok, binOp, cmpOp, bindS, truthy, iv, h2',
        decide_true, if_true]
      have eb1 : ¬ ((u:Int) - 2 < 0) := by omega
      have eb2 : ((u:Int) - 2).toNat = u - 2 := by omega
      have eb3 : (u:Int) - 2 < ↑ptrs.length := by rw [hpr.1]; omega
      have eb4 : (2:Int) ≤ ↑u := by omega
      simp only [worldBody]
      pystepA [hself, hl.1, hself']
      rw [hset_append_left _ _ hl.1]
      have hbs : D.self ≠ b := fun e => hmb (Or.inl e.symm)
      pystepA [hself, hl.1, hl.2.2.2.1, hne, hp, eb1, eb2, eb3, eb4, hpb, hbl, hb, hroot, hbs]
      have hvn' : nd.var < names.length := hvn
      have ev1 : ¬ ((nd.var:Int) < 0) := by omega
      have ev2 : ((nd.var:Int)).toNat = nd.var := by simp
      have ev3 : (nd.var:Int) < (names.length:Int) := by omega
      have ev4 : names[nd.var]? = some names[nd.var] := List.getElem?_eq_getElem hvn'
      pystepA [hval, hself, hl.1, hl.2.1, hne, hnames, hvn', ev1, ev2, ev3, ev4]
      rw [hset_append_last' _ _ _ _ (length_hset _ _ _)]
      obtain ⟨hR1, hF1⟩ := hR.setCounters { m with wsteps := m.wsteps + 1 } rfl rfl
      simp only [diagramFields, iv, Int.natCast_add, Int.natCast_one] at hR1 hF1
      have hgd : names.getD nd.var "" = names[nd.var] := by
        rw [List.getD_eq_getElem?_getD, ev4]; rfl
      rw [hgd] at hw
      have hL1 : (hset H D.self (Obj.inst "Diagram"
                  [("names", V.ref D.names), ("limits", V.ref D.lim), ("nodes", V.ref D.nodes),
                    ("unique", V.ref D.uniq), ("memo", V.ref D.memo), ("operations", V.int ↑m.ops),
                    ("visits", V.int ↑m.visits), ("witness_steps", V.int (↑m.wsteps + 1))])).length = H.length :=
        length_hset _ _ _
      by_cases hl0 : nd.low = 0
      · have hb0 : ((nd.low : Int) == 0) = true := by simp [hl0]
        rw [hb0]
        pystepA [hb0]
        simp only [execB_nil_eq, loopK]
        rw [if_pos hl0, show (nd.low == 0) = true by simp [hl0]] at hw
        obtain ⟨env', H', e1, r1, v1, R1, F1, L1⟩ := ih k' (by omega) _ { m with wsteps := m.wsteps + 1 }
          nd.high _ kvs' st'
          ((((env.set "var" (V.int ↑nd.var)).set "low" (V.int ↑nd.low)).set "high" (V.int ↑nd.high)).set "root"
            (V.int ↑nd.high)) hR1 (hinv.wsteps _) (by show nd.high < m.nodes.size + 2; omega)
          (by simp [iv]) (by simp [hval, hL1]) (by simp [hself]) hw
        refine ⟨env', H', ?_, r1, by rw [v1, hL1], R1, hF1.trans F1, by rw [L1, hL1]⟩
        exact e1
      · have hb0 : ((nd.low : Int) == 0) = false := by simp [hl0]
        rw [hb0]
        pystepA [hb0]
        simp only [execB_nil_eq, loopK]
        rw [if_neg hl0, show (nd.low == 0) = false by simp [hl0]] at hw
        obtain ⟨env', H', e1, r1, v1, R1, F1, L1⟩ := ih k' (by omega) _ { m with wsteps := m.wsteps + 1 }
          nd.low _ kvs' st'
          ((((env.set "var" (V.int ↑nd.var)).set "low" (V.int ↑nd.low)).set "high" (V.int ↑nd.high)).set "root"
            (V.int ↑nd.low)) hR1 (hinv.wsteps _) (by show nd.low < m.nodes.size + 2; omega)
          (by simp [iv]) (by simp [hval, hL1]) (by simp [hself]) hw
        refine ⟨env', H', ?_, r1, by rw [v1, hL1], R1, hF1.trans F1, by rw [L1, hL1]⟩
        exact e1
    · simp only [pyWalk, h2, if_false, Prod.mk.injEq] at hw
      obtain ⟨rfl, rfl, rfl⟩ := hw
      rw [interp_succ_whileLoop]
      simp [whileIter, worldCond, evalE, hroot, binOp, cmpOp, bindS, truthy, iv]
      refine ⟨env, H, ⟨rfl, rfl⟩, hroot, hval, ?_, Frame.refl D H, rfl⟩
      simpa using hR

theorem lookup_world' (ext : Ext) : lookupFn (pyCtx ext).prog "Diagram.world" = some py_Diagram_world := by rfl

/-- `Diagram.world(0)` returns `None` and changes nothing. -/
theorem world_sim_zero (ext : Ext) (k : Nat) (h : Heap) (D : Addrs) :
    (interp (pyCtx ext) (k + 1)).call "Diagram.world" [.ref D.self, iv 0] h = .ok .none h := by
  rw [interp_succ_call]
  simp only [callBody, lookup_world', py_Diagram_world]
  simp only [List.length, List.zip, List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append,
    List.cons_append, ne_eq, not_true, if_false]
  pystep []
  simp [finishCall]

/-- **`Diagram.world(u)` for `u ≠ 0` returns the reference witness as a fresh name → bool
dictionary and adds exactly `witSteps` to `witness_steps`.** -/
theorem world_sim_pos (ext : Ext) {names : List String} {lim : Limits} {D : Addrs} (hnd : names.Nodup)
    (k : Nat) (hk : names.length + 1 ≤ k) (h : Heap) (m : Mgr) (u : Nat) (hR : MRel names lim D h m)
    (hinv : Inv names.length lim m) (hu : u < m.nodes.size + 2) (h0 : u ≠ 0) :
    ∃ H', (interp (pyCtx ext) (k + 1)).call "Diagram.world" [.ref D.self, iv u] h =
        .ok (.ref h.length) (H' ++ [.dict (encVals names (wit names.length m.nodes 0 u))]) ∧
      MRel names lim D H' { m with wsteps := m.wsteps + witSteps names.length m.nodes 0 u } ∧
      Frame D h H' ∧ H'.length = h.length := by
  obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by omega⟩
  have hself := hR.self
  simp only [diagramFields, iv] at hself
  have hnames := hR.names
  have hl := hR.addrs_lt
  have hne := hR.neqs
  rw [interp_succ_call]
  simp only [callBody, lookup_world', py_Diagram_world]
  simp only [List.length, List.zip, List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append,
    List.cons_append, ne_eq, not_true, if_false]
  have h0' : ¬ ((u : Int) = 0) := by omega
  pystep [h0', h0]
  have hfk := fromkeys_encVals [] names (by simpa using hnd)
  simp only [List.length_nil, List.replicate_zero, List.nil_append] at hfk
  have he0 : encVals [] [] = [] := rfl
  rw [he0] at hfk
  pystep [hself, hl.1, hnames, hl.2.1, hfk]
  have hw := pyWalk_world hinv.valid hnd hu h0 m.wsteps names.length (Nat.le_refl _)
  obtain ⟨env', H', e1, r1, v1, R1, F1, L1⟩ := world_loop ext names.length k' (by omega) h m u _ _ _
    [("values", .ref h.length), ("root", .int u), ("self", .ref D.self)] hR hinv hu
    (by simp [Env.get, iv]) (by simp [Env.get]) (by simp [Env.get]) hw
  rw [execB_cons']
  simp only [worldCond, worldBody] at e1
  conv in execS _ _ _ _ _ => simp only [execS]
  rw [e1]
  simp only [seqF_normal]
  pystepA [r1, iv]
  pystepA [v1]
  exact ⟨H', by simp [finishCall], R1, F1, L1⟩

end PCSCR.Py
