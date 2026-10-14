import PCSConditionalRuntime.JsWalk
import PCSConditionalRuntime.PyWorld

/-!
# JavaScript `Diagram.world` refines `PCSDD.world` and the witness-step counter

The values object is allocated by `Object.fromEntries(this.names.map(n=>[n,false]))` (after the
pair arrays and the mapped array); the loop only writes the `Diagram` instance and that object.
`jworld_loop` follows the `while(root>=2)` loop along `jsWalk`.  Every `this.witnessSteps++`
stays an exact safe integer (`st' ≤ 2^53 - 1`).
-/

namespace PCSCR.Js

open PCSCR PCSDD PCSOmega PCSCR.Py

def jworldCond : E := E.bin BinOp.ge (E.var "root") (E.lit (V.int 2))

def jworldBody : List S :=
  [S.aug (Tgt.attr (E.var "this") "witnessSteps") BinOp.add (E.lit (V.int 1)),
   S.assign [Tgt.tup [Tgt.name "v", Tgt.name "lo", Tgt.name "hi"]]
     (E.sub (E.attr (E.var "this") "nodes") (E.bin BinOp.sub (E.var "root") (E.lit (V.int 2)))),
   S.assign [Tgt.sub (E.var "values") (E.sub (E.attr (E.var "this") "names") (E.var "v"))]
     (E.bin BinOp.eq (E.var "lo") (E.lit (V.int 0))),
   S.assign [Tgt.name "root"]
     (E.cond (E.bin BinOp.eq (E.var "lo") (E.lit (V.int 0))) (E.var "hi") (E.var "lo"))]

/-- **The witness loop follows `jsWalk`.** -/
theorem jworld_loop (ext : Ext) {names : List String} {lim : Limits} {D : Addrs} :
    ∀ (f k : Nat), f ≤ k → ∀ (H : Heap) (m : Mgr) (u : Nat) (kvs kvs' : List (V × V)) (st' : Nat) (env : Env),
      JMRel names lim D H m → Inv names.length lim m → u < m.nodes.size + 2 →
      env.get "root" = some (iv u) → env.get "values" = some (.ref H.length) →
      env.get "this" = some (.ref D.self) →
      jsWalk names m.nodes f u kvs m.wsteps = (kvs', st', 1) → st' ≤ 9007199254740991 →
      ∃ env' H', (interp (jsCtx ext) (k + 1)).whileLoop env (H ++ [.dict kvs]) jworldCond jworldBody =
          .ok (.normal env') (H' ++ [.dict kvs']) ∧
        env'.get "root" = some (iv 1) ∧ env'.get "values" = some (.ref H.length) ∧
        JMRel names lim D H' { m with wsteps := st' } ∧ Frame D H H' ∧ H'.length = H.length := by
  intro f
  induction f with
  | zero =>
    intro k _ H m u kvs kvs' st' env hR hinv hu hroot hval hself hw hst
    simp only [jsWalk, Prod.mk.injEq] at hw
    obtain ⟨rfl, rfl, rfl⟩ := hw
    rw [interp_succ_whileLoop]
    simp [whileIter, jworldCond, evalE, hroot, binOp, cmpOp, bindS, truthy, iv]
    refine ⟨env, H, ⟨rfl, rfl⟩, hroot, hval, ?_, Frame.refl D H, rfl⟩
    simpa using hR
  | succ f ih =>
    intro k hk H m u kvs kvs' st' env hR hinv hu hroot hval hself hw hst
    obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by omega⟩
    by_cases h2 : 2 ≤ u
    · obtain ⟨ptrs, hp, hpr⟩ := hR.nodes
      obtain ⟨nd, b, hg, hpb, hmb, hb⟩ := node_ptr hpr h2 hu
      obtain ⟨hvn, hlo, hhi, hne0, _, _⟩ := hinv.valid.node hg
      have hself' := hR.self
      simp only [jdiagramFields, iv] at hself' hb
      have hnames := hR.names
      have hl := hR.addrs_lt
      have hne := hR.neqs
      have hbl := hget_lt hb
      simp only [jsWalk, h2, if_true, hg] at hw
      rw [interp_succ_whileLoop]
      have h2' : ((u:Int) ≥ 2) := by omega
      simp only [whileIter, jworldCond, evalE, hroot, Out.bind_ok, binOp, cmpOp, bindS, truthy, iv, h2',
        decide_true, if_true]
      have eb1 : ¬ ((u:Int) - 2 < 0) := by omega
      have eb2 : ((u:Int) - 2).toNat = u - 2 := by omega
      have eb3 : (u:Int) - 2 < ↑ptrs.length := by rw [hpr.1]; omega
      have eb4 : (2:Int) ≤ ↑u := by omega
      have hlb := lim_bounds hR.lv
      have hsz := hinv.size_le
      have eb5 : (-9007199254740991 : Int) ≤ ↑u - 2 := by omega
      have eb6 : ¬ (9007199254740991 : Int) < ↑u - 2 := by omega
      simp only [jworldBody]
      have hst1 : m.wsteps + 1 ≤ st' := by
        have := jsWalk_st_le names m.nodes f (if nd.low = 0 then nd.high else nd.low)
          (dictSet .js kvs (.str (names.getD nd.var "")) (.bool (nd.low == 0))) (m.wsteps + 1)
        rw [hw] at this; exact this
      rw [execB_cons', js_aug_attr_add1 ext (interp (jsCtx ext) (k' + 1)) env (H ++ [Obj.dict kvs]) D.self "Diagram" _ "witnessSteps" m.wsteps
        hself (by rw [jhget_append_lt_list _ hl.1]; exact hself') (by simp [fieldGet])
        (by simp only [MAX_SAFE]; omega) (by simp only [MAX_SAFE]; omega)]
      simp only [seqF_normal, fieldSet, String.reduceEq, if_false, if_true]
      rw [hset_append_left _ _ hl.1]
      have hbs : D.self ≠ b := fun e => hmb (Or.inl e.symm)
      jsstepA [hself, hl.1, hl.2.2.2.1, hne, hp, eb1, eb2, eb3, eb4, eb5, eb6, hpb, hbl, hb, hroot, hbs]
      have hvn' : nd.var < names.length := hvn
      have ev1 : ¬ ((nd.var:Int) < 0) := by omega
      have ev2 : ((nd.var:Int)).toNat = nd.var := by simp
      have ev3 : (nd.var:Int) < (names.length:Int) := by omega
      have ev4 : names[nd.var]? = some names[nd.var] := List.getElem?_eq_getElem hvn'
      jsstepA [hval, hself, hl.1, hl.2.1, hne, hnames, hvn', ev1, ev2, ev3, ev4]
      rw [hset_append_last' _ _ _ _ (length_hset _ _ _)]
      obtain ⟨hR1, hF1⟩ := hR.setCounters { m with wsteps := m.wsteps + 1 } rfl rfl
      simp only [jdiagramFields, iv, Int.natCast_add, Int.natCast_one] at hR1 hF1
      have hgd : names.getD nd.var "" = names[nd.var] := by
        rw [List.getD_eq_getElem?_getD, ev4]; rfl
      rw [hgd] at hw
      have hL1 : (hset H D.self (Obj.inst "Diagram"
                  [("names", V.ref D.names), ("limits", V.ref D.lim), ("nodes", V.ref D.nodes),
                    ("unique", V.ref D.uniq), ("memo", V.ref D.memo), ("operations", V.int ↑m.ops),
                    ("visits", V.int ↑m.visits), ("witnessSteps", V.int (↑m.wsteps + 1))])).length = H.length :=
        length_hset _ _ _
      by_cases hl0 : nd.low = 0
      · have hb0 : ((nd.low : Int) == 0) = true := by simp [hl0]
        rw [hb0]
        jsstepA [hb0]
        simp only [execB_nil_eq, loopK]
        rw [if_pos hl0, show (nd.low == 0) = true by simp [hl0]] at hw
        obtain ⟨env', H', e1, r1, v1, R1, F1, L1⟩ := ih k' (by omega) _ { m with wsteps := m.wsteps + 1 }
          nd.high _ kvs' st'
          ((((env.set "v" (V.int ↑nd.var)).set "lo" (V.int ↑nd.low)).set "hi" (V.int ↑nd.high)).set "root"
            (V.int ↑nd.high)) hR1 (hinv.wsteps _) (by show nd.high < m.nodes.size + 2; omega)
          (by simp [iv]) (by simp [hval, hL1]) (by simp [hself]) hw hst
        refine ⟨env', H', ?_, r1, by rw [v1, hL1], R1, hF1.trans F1, by rw [L1, hL1]⟩
        exact e1
      · have hb0 : ((nd.low : Int) == 0) = false := by simp [hl0]
        rw [hb0]
        jsstepA [hb0]
        simp only [execB_nil_eq, loopK]
        rw [if_neg hl0, show (nd.low == 0) = false by simp [hl0]] at hw
        obtain ⟨env', H', e1, r1, v1, R1, F1, L1⟩ := ih k' (by omega) _ { m with wsteps := m.wsteps + 1 }
          nd.low _ kvs' st'
          ((((env.set "v" (V.int ↑nd.var)).set "lo" (V.int ↑nd.low)).set "hi" (V.int ↑nd.high)).set "root"
            (V.int ↑nd.low)) hR1 (hinv.wsteps _) (by show nd.low < m.nodes.size + 2; omega)
          (by simp [iv]) (by simp [hval, hL1]) (by simp [hself]) hw hst
        refine ⟨env', H', ?_, r1, by rw [v1, hL1], R1, hF1.trans F1, by rw [L1, hL1]⟩
        exact e1
    · simp only [jsWalk, h2, if_false, Prod.mk.injEq] at hw
      obtain ⟨rfl, rfl, rfl⟩ := hw
      rw [interp_succ_whileLoop]
      simp [whileIter, jworldCond, evalE, hroot, binOp, cmpOp, bindS, truthy, iv]
      refine ⟨env, H, ⟨rfl, rfl⟩, hroot, hval, ?_, Frame.refl D H, rfl⟩
      simpa using hR


/-- `Diagram.world(0)` returns `null` and changes nothing. -/
theorem jworld_sim_zero (ext : Ext) (k : Nat) (h : Heap) (D : Addrs) :
    (interp (jsCtx ext) (k + 1)).call "Diagram.world" [.ref D.self, iv 0] h = .ok .none h := by
  rw [interp_succ_call]
  simp only [callBody, lookup_world, js_Diagram_world, jsCtx_prog]
  simp only [List.length, List.zip, List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append,
    List.cons_append, ne_eq, not_true, if_false]
  jsstep []
  simp [finishCall]

/-- References `base, base+1, …, base+n-1`. -/
def refsFrom (base n : Nat) : List V := (List.range n).map fun i => V.ref (base + i)

theorem refsFrom_succ (base n : Nat) : refsFrom base (n + 1) = refsFrom base n ++ [V.ref (base + n)] := by
  simp [refsFrom, List.range_succ]

theorem jcomp_pair_loop (c : Ctx) (h : Heap) (L : Nat) (xs : List V) (b : V) (x : String)
    (hL : hget h L = some (.list xs)) :
    ∀ (ys : List V) (objs : List Obj) (j k : Nat) (env : Env), xs.drop j = ys → ys.length + 1 ≤ k →
      ∃ env', (interp c k).forLoop env (h ++ .list (refsFrom (h.length + 1) objs.length) :: objs) (.name x)
          (.ref L) j (compBody h.length (.listD [.var x, .lit b]) none) =
        .ok (.normal env') (h ++ .list (refsFrom (h.length + 1) (objs.length + ys.length)) ::
          (objs ++ ys.map fun y => .list [y, b]))
  | [], objs, j, k, env, hys, hk => by
      obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by simp at hk; omega⟩
      rw [interp_succ_forLoop]
      have hj : xs[j]? = none := by
        have := congrArg List.length hys; simp at this
        exact List.getElem?_eq_none (by omega)
      have hLt := hget_lt hL
      exact ⟨env, by simp [forIter, elemAt, jhget_append_lt_list _ hLt, hL, hj]⟩
  | y :: ys, objs, j, k, env, hys, hk => by
      obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by simp at hk; omega⟩
      rw [interp_succ_forLoop]
      have hj : xs[j]? = some y := by
        have := congrArg (fun l => l[0]?) hys; simpa using this
      have hLt := hget_lt hL
      have hys' : xs.drop (j + 1) = ys := by rw [← List.drop_drop, hys]; simp
      obtain ⟨env', ih⟩ := jcomp_pair_loop c h L xs b x hL ys (objs ++ [.list [y, b]]) (j + 1) k'
        (env.set x y) hys' (by simp at hk; omega)
      refine ⟨env', ?_⟩
      have hacc : hget (h ++ .list (refsFrom (h.length + 1) objs.length) :: objs ++ [.list [y, b]]) h.length =
          some (.list (refsFrom (h.length + 1) objs.length)) := by simp [hget]
      have hset_eq : hset (h ++ .list (refsFrom (h.length + 1) objs.length) :: objs ++ [.list [y, b]]) h.length
          (.list (refsFrom (h.length + 1) objs.length ++ [V.ref (h.length + 1 + objs.length)])) =
          h ++ .list (refsFrom (h.length + 1) (objs ++ [Obj.list [y, b]]).length) :: (objs ++ [.list [y, b]]) := by
        simp [hset, refsFrom_succ]
      have hlen : (h ++ Obj.list (refsFrom (h.length + 1) objs.length) :: objs).length =
          h.length + 1 + objs.length := by simp; omega
      simp only [forIter, elemAt, jhget_append_lt_list _ hLt, hL, hj, bindE, assignT, compBody, execB, execS,
        evalE, evalL, Out.bind, bindS, Env.get_set, builtinMethod, seqF, loopK, List.append_assoc,
        List.cons_append] at ih ⊢
      simp only [if_true]
      simp [hget, hset, refsFrom_succ, hlen, List.set_append_right] at ih ⊢
      rw [ih, show objs.length + 1 + ys.length = objs.length + (ys.length + 1) by omega]

theorem refsFrom_cons (base n : Nat) : refsFrom base (n + 1) = V.ref base :: refsFrom (base + 1) n := by
  induction n generalizing base with
  | zero => simp [refsFrom]
  | succ n ih =>
    rw [refsFrom_succ, ih, refsFrom_succ]; simp [Nat.add_assoc, Nat.add_comm 1]

theorem JMRel.appendList {names : List String} {lim : Limits} {D : Addrs} {m : Mgr} :
    ∀ (l : List Obj) (h : Heap), JMRel names lim D h m → JMRel names lim D (h ++ l) m
  | [], h, hR => by simpa using hR
  | o :: l, h, hR => by
      have := JMRel.appendList l (h ++ [o]) (hR.append o)
      simpa using this

theorem Frame.appendList (D : Addrs) : ∀ (l : List Obj) (h : Heap), Frame D h (h ++ l)
  | [], h => by simpa using Frame.refl D h
  | o :: l, h => by
      have := (Frame.append D h o).trans (Frame.appendList D l (h ++ [o]))
      simpa using this

theorem jsEntries_pairs (H : Heap) (b : V) :
    ∀ (ns : List String) (base : Nat), (∀ i (hi : i < ns.length), hget H (base + i) = some (.list [.str ns[i], b])) →
      jsEntries H (refsFrom base ns.length) = some (ns.map fun s => (V.str s, b))
  | [], base, _ => by simp [refsFrom, jsEntries]
  | s :: ns, base, hH => by
      rw [List.length_cons, refsFrom_cons]
      have h0 := hH 0 (by simp)
      simp only [Nat.add_zero, List.getElem_cons_zero] at h0
      have ih := jsEntries_pairs H b ns (base + 1) (fun i hi => by
        have := hH (i + 1) (by simp; omega)
        simpa [Nat.add_assoc, Nat.add_comm 1] using this)
      simp [jsEntries, h0, ih]

/-- **`Diagram.world(u)` for `u ≠ 0` returns the reference witness as a fresh name → boolean
object and adds exactly `witSteps` to `witnessSteps`.**  The comprehension
`this.names.map(n=>[n,false])` first allocates the mapped array and one pair array per name, so
the values object sits at `h.length + 1 + names.length`.  The counter stays a safe integer
(`m.wsteps + names.length ≤ 2^53 - 1`, since `witSteps ≤ names.length`). -/
theorem jworld_sim_pos (ext : Ext) {names : List String} {lim : Limits} {D : Addrs} (hnd : names.Nodup)
    (k : Nat) (hk : names.length + 1 ≤ k) (h : Heap) (m : Mgr) (u : Nat) (hR : JMRel names lim D h m)
    (hinv : Inv names.length lim m) (hu : u < m.nodes.size + 2) (h0 : u ≠ 0)
    (hws : m.wsteps + names.length ≤ 9007199254740991) :
    ∃ H', (interp (jsCtx ext) (k + 1)).call "Diagram.world" [.ref D.self, iv u] h =
        .ok (.ref (h.length + 1 + names.length)) (H' ++ [.dict (encVals names (wit names.length m.nodes 0 u))]) ∧
      JMRel names lim D H' { m with wsteps := m.wsteps + witSteps names.length m.nodes 0 u } ∧
      Frame D h H' ∧ H'.length = h.length + 1 + names.length := by
  obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by omega⟩
  have hself := hR.self
  simp only [jdiagramFields, iv] at hself
  have hnames := hR.names
  have hl := hR.addrs_lt
  have hcomp : evalE (jsCtx ext) (interp (jsCtx ext) (k' + 1)) [("root", V.int ↑u), ("this", V.ref D.self)] h
      ((E.listD [E.var "n", E.lit (V.bool false)]).comp "n" ((E.var "this").attr "names") none) =
      .ok (.ref h.length) (h ++ .list (refsFrom (h.length + 1) names.length) ::
        names.map fun s => .list [.str s, .bool false]) := by
    obtain ⟨env', e⟩ := jcomp_pair_loop (jsCtx ext) h D.names (names.map V.str) (.bool false) "n" hnames
      (names.map V.str) [] 0 (k' + 1) [("root", V.int ↑u), ("this", V.ref D.self)] rfl (by simp; omega)
    simp only [List.length_nil, List.nil_append, List.map_map, List.length_map] at e
    have h0r : refsFrom (h.length + 1) 0 = [] := rfl
    rw [h0r] at e
    simp only [evalE, Env.get]
    simp [attrOp, hself, fieldGet, Out.bind, e, compResult]
  have hfk := jfromkeys_encVals [] names (by simpa using hnd)
  simp only [List.length_nil, List.replicate_zero, List.nil_append] at hfk
  have he0 : encVals [] [] = [] := rfl
  rw [he0] at hfk
  have hfe : builtin (jsCtx ext) "%fromEntries" [.ref h.length] (h ++ .list (refsFrom (h.length + 1) names.length) ::
        names.map fun s => .list [.str s, .bool false]) =
      .ok (.ref (h.length + 1 + names.length)) ((h ++ .list (refsFrom (h.length + 1) names.length) ::
        names.map fun s => .list [.str s, .bool false]) ++
          [.dict (encVals names (List.replicate names.length false))]) := by
    have hent := jsEntries_pairs (h ++ .list (refsFrom (h.length + 1) names.length) ::
        names.map fun s => .list [.str s, .bool false]) (.bool false) names (h.length + 1) (fun i hi => by
          simp [hget, List.getElem?_append_right, Nat.add_assoc, Nat.add_comm 1])
    have hacc : hget (h ++ .list (refsFrom (h.length + 1) names.length) ::
        names.map fun s => .list [.str s, .bool false]) h.length = some (.list (refsFrom (h.length + 1) names.length)) := by
      simp [hget]
    simp [builtin, builtinJs, elems, hacc, hent, jsCtx, List.foldl_map]
    exact ⟨by omega, by simpa [List.foldl_map] using hfk⟩
  rw [interp_succ_call]
  simp only [callBody, lookup_world, js_Diagram_world, jsCtx_prog]
  simp only [List.length, List.zip, List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append,
    List.cons_append, ne_eq, not_true, if_false]
  have h0' : ¬ ((u : Int) = 0) := by omega
  jsstep [h0', h0]
  rw [execB_cons']
  conv in execS _ _ _ _ _ => simp only [execS, bindS, evalE]
  have hnf : (lookupFn (jsCtx ext).prog "%fromEntries").isSome = false := rfl
  have hnc : lookupClass (jsCtx ext).prog "%fromEntries" = none := rfl
  have hne : (jsCtx ext).prog.externs.contains "%fromEntries" = false := rfl
  simp only [hnf, hnc, hne, evalL, hcomp, Out.bind, hfe, Bool.false_eq_true, if_false]
  simp only [assignAll, assignT, bindE, Out.bind, seqF_normal, Env.set, Env.has, Env.replace]
  simp only [beq_iff_eq, Bool.or_false, Bool.or_eq_true]
  have hlen1 : (h ++ Obj.list (refsFrom (h.length + 1) names.length) ::
    names.map fun s => Obj.list [.str s, .bool false]).length = h.length + 1 + names.length := by simp; omega
  generalize hH1 : h ++ Obj.list (refsFrom (h.length + 1) names.length) ::
    names.map (fun s => Obj.list [.str s, .bool false]) = H1 at hlen1 ⊢
  have hR1 : JMRel names lim D H1 m := hH1 ▸ JMRel.appendList _ h hR
  have hF1 : Frame D h H1 := hH1 ▸ Frame.appendList D _ h
  have hw := jsWalk_world hinv.valid hnd hu h0 m.wsteps names.length (Nat.le_refl _)
  have hwl := witSteps_le names.length m.nodes names.length 0 u rfl
  have hs1 : ("root" = "values") ↔ False := by decide
  have hs2 : ("this" = "values") ↔ False := by decide
  simp only [hs1, hs2, or_self, if_false, ← hlen1]
  obtain ⟨env', H', e1, r1, v1, R1, F1, L1⟩ := jworld_loop ext names.length k' (by omega) H1 m u _ _ _
    [("values", .ref H1.length), ("root", .int u), ("this", .ref D.self)] hR1 hinv hu
    (by simp [Env.get, iv]) (by simp [Env.get]) (by simp [Env.get]) hw (by simp at hwl ⊢; omega)
  rw [execB_cons']
  simp only [jworldCond, jworldBody] at e1
  conv in execS _ _ _ _ _ => simp only [execS]
  rw [e1]
  simp only [seqF_normal]
  jsstepA [r1, iv]
  jsstepA [v1]
  exact ⟨H', by simp [finishCall], R1, hF1.trans F1, L1⟩


end PCSCR.Js
