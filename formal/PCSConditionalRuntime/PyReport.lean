import PCSConditionalRuntime.PyFields

/-!
# `check`: the consistent-context report

```
result['context_example'] = manager.world(context)
world = manager.world(difference)
if world is None: result['decision'] = 'equivalent_under_assumptions'
else: ... (the disagreement report, `cex_branch`)
```
-/

namespace PCSCR.Py

open PCSCR PCSDD PCSOmega

def repBody : List S :=
  [S.assign [Tgt.sub (E.var "result") (E.lit (V.str "context_example"))]
     (E.mcall (E.var "manager") "world" [E.var "context"]),
   S.assign [Tgt.name "world"] (E.mcall (E.var "manager") "world" [E.var "difference"]),
   S.ifte (E.isNone (E.var "world") false)
     [S.assign [Tgt.sub (E.var "result") (E.lit (V.str "decision"))]
        (E.lit (V.str "equivalent_under_assumptions"))]
     cexBody]

/-- The counterexample record of `check` for the difference root `d`. -/
def cexOf {n : Nat} (t : CTask n) (ns : Nodes) (d : Nat) : Option CexRec :=
  (world n ns d).map (fun w =>
    ({ assignment := w, sourceTrue := t.source.eval (envOf w),
       candidateTrue := t.candidate.eval (envOf w),
       assumptionsTrue := t.assumptions.map (fun f => f.eval (envOf w)) } : CexRec))

/-- The JSON fields after the report. -/
def repT (names : List String) (t : CTask names.length) (ns : Nodes) (ctx d : Nat)
    (kts : List (String × T)) : List (String × T) :=
  if d = 0 then
    tset (tset kts "context_example" (optT (asgT names) (world names.length ns ctx))) "decision"
      (decisionT .equivalentUnderAssumptions)
  else
    tset (tset (tset kts "context_example" (optT (asgT names) (world names.length ns ctx))) "decision"
      (decisionT .counterexample)) "counterexample" (optT (cexT names) (cexOf t ns d))

def finM (n : Nat) (m : Mgr) (ctx d : Nat) : Mgr :=
  { m with wsteps := m.wsteps + witSteps n m.nodes 0 ctx + witSteps n m.nodes 0 d }

theorem report_sim (ext : Ext) {names : List String} {lim : Limits} {D : Addrs} (hnd : names.Nodup)
    (t : CTask names.length) (k : Nat) (env : Env) (h : Heap) (m : Mgr) (ctx d A AS R : Nat)
    (vkvs : List (V × V)) (as : List V) (vs vc : V) (kvs : List (V × V)) (kts : List (String × T))
    (hk : names.length + fdepthL t.assumptions + fdepth t.source + fdepth t.candidate + as.length + 6 ≤ k)
    (hmg : env.get "manager" = some (.ref D.self)) (hctx : env.get "context" = some (iv ctx))
    (hdif : env.get "difference" = some (iv d))
    (hval : env.get "value" = some (.ref A)) (hres : env.get "result" = some (.ref R))
    (hA : hget h A = some (.dict vkvs)) (hmA : ¬ D.mut A)
    (has : dictFind .py vkvs (.str "assumptions") = some (.ref AS))
    (hAS : hget h AS = some (.list as)) (hmAS : ¬ D.mut AS) (hl : as.length = t.assumptions.length)
    (hz : ∀ p ∈ as.zip t.assumptions, FRel D h names p.1 p.2)
    (hs : dictFind .py vkvs (.str "source") = some vs) (hc : dictFind .py vkvs (.str "candidate") = some vc)
    (hfs : FRel D h names vs t.source) (hfc : FRel D h names vc t.candidate)
    (hR : MRel names lim D h m) (hinv : Inv names.length lim m)
    (hRo : R ∈ D.own) (r1 : R ≠ D.self) (r2 : R ≠ D.nodes) (r3 : R ≠ D.uniq) (r4 : R ≠ D.memo)
    (hRk : hget h R = some (.dict kvs)) (hkv : ReadsKV D.mut h kvs kts)
    (dctx : Denotes m ctx (allEval t.assumptions)) (hnz : ctx ≠ 0)
    (dd : Denotes m d (fun ρ => allEval t.assumptions ρ && (t.source.eval ρ != t.candidate.eval ρ))) :
    ∃ env' h' kvs', execB (pyCtx ext) (interp (pyCtx ext) (k + 1)) env h repBody = .ok (.normal env') h' ∧
      (∀ y, y ≠ "world" → y ≠ "truths" → y ≠ "a" → y ≠ "b" → env'.get y = env.get y) ∧
      hget h' R = some (.dict kvs') ∧ ReadsKV D.mut h' kvs' (repT names t m.nodes ctx d kts) ∧
      MRel names lim D h' (finM names.length m ctx d) ∧ FrameS D.mut h h' := by
  have hselfR := hR.self
  simp only [diagramFields, iv] at hselfR
  have hcl3 : classHasMethod pyProg "Diagram" "world" = true := by decide
  obtain ⟨H1, ew1, R1, F1, L1⟩ := world_sim_pos2 ext hnd k (by omega) h m ctx hR hinv dctx.1 hnz
  simp only [repBody]
  rw [execB_cons']
  simp [execS, bindS, evalE, evalL, hmg, hctx, Out.bind, hselfR, hcl3, ew1, assignAll, assignT, bindE]
  have hRb : ¬ D.base.mut R := by
    simp only [Addrs.mut, Addrs.base_self, Addrs.base_nodes, Addrs.base_uniq, Addrs.base_memo,
      Addrs.base_own, List.not_mem_nil, or_false]; omega
  have hRm : D.mut R := Or.inr (Or.inr (Or.inr (Or.inr hRo)))
  have hRlt := hget_lt hRk
  have hR1 : hget H1 R = some (.dict kvs) := by rw [F1.2 R hRlt hRb]; exact hRk
  have hR1lt : R < H1.length := by omega
  simp [hres, storeOp, hget_append_lt_list _ hR1lt, hR1, hashable]
  have hW1lt : h.length < H1.length + 1 := by omega
  generalize hG : hset (H1 ++ [Obj.dict (encVals names (wit names.length m.nodes 0 ctx))]) R
    (Obj.dict (dictSet Dialect.py kvs (V.str "context_example") (V.ref (List.length h)))) = G
  generalize hkvs1 : dictSet Dialect.py kvs (V.str "context_example") (V.ref (List.length h)) = kvs1 at hG
  obtain ⟨R2, FG⟩ := (R1.append (Obj.dict (encVals names (wit names.length m.nodes 0 ctx)))).hsetOwn hRo r1 r2 r3 r4
    (Obj.dict kvs1)
  rw [hG] at R2 FG
  have FhG : Frame D h G := ((Frame.ofBase F1).trans (Frame.append _ _ _)).trans FG
  have hGR : hget G R = some (.dict kvs1) := by rw [← hG]; exact hget_hset_same _ (by simp; omega)
  have hmW1 : ¬ D.mut h.length := fresh_not_mut R1 (by omega)
  have hGW1 : hget G h.length = some (.dict (encVals names (wit names.length m.nodes 0 ctx))) := by
    rw [← hG, hget_hset_ne _ (by omega)]; simp [hget, ← L1]
  have hkvG : ReadsKV D.mut G kvs kts := hkv.frame (FrameS.of_frame FhG)
  have hctxw : world names.length m.nodes ctx = some (wit names.length m.nodes 0 ctx) := by
    simp [world, hnz]
  have hkv1 : ReadsKV D.mut G kvs1 (tset kts "context_example" (optT (asgT names) (world names.length m.nodes ctx))) := by
    rw [← hkvs1, hctxw]; exact ReadsKV.dictSet _ (reads_world hGW1 hmW1) _ _ hkvG
  have hselfG := R2.self
  simp only [diagramFields, iv] at hselfG
  by_cases hd0 : d = 0
  · subst hd0
    have ew2 : (interp (pyCtx ext) (k + 1)).call "Diagram.world" [.ref D.self, .int 0] G = .ok .none G :=
      world_sim_zero ext k G D
    pystepA [hmg, hdif, hselfG, hcl3, ew2]
    pystepA [isNoneV]
    simp [hres, hGR, execB, Out.bind]
    obtain ⟨R3, F3⟩ := R2.hsetOwn hRo r1 r2 r3 r4
      (Obj.dict (dictSet .py kvs1 (.str "decision") (.str "equivalent_under_assumptions")))
    have hfin : finM names.length m ctx 0 = { m with wsteps := m.wsteps + witSteps names.length m.nodes 0 ctx } := by
      simp [finM, witSteps_zero]
    refine ⟨_, _, ⟨rfl, rfl⟩, fun y h1 _ _ _ => by simp [Env.get_set, Ne.symm h1], _,
      hget_hset_same _ (hget_lt hGR), ?_, hfin ▸ R3, FrameS.of_frame (FhG.trans F3)⟩
    simp only [repT, if_true]
    exact ReadsKV.dictSet _ (ReadsM.str _ _ _) _ _ (hkv1.frame (FrameS.of_frame F3))
  · obtain ⟨H2, ew2, R3, F2, L2⟩ := world_sim_pos2 ext hnd k (by omega) G
      { m with wsteps := m.wsteps + witSteps names.length m.nodes 0 ctx } d R2 (hinv.wsteps _) dd.1 hd0
    simp only [iv] at ew2
    pystepA [hmg, hdif, hselfG, hcl3, ew2]
    rw [execB_cons']
    simp only [execS, evalE, isNoneV, truthy, bindS, Env.get_set]
    simp
    generalize hw : wit names.length m.nodes 0 d = w at R3 ew2 ⊢
    have hwd : world names.length m.nodes d = some w := by simp [world, hd0, hw]
    obtain ⟨⟨hwl, hwev⟩, _⟩ := (world_spec hinv.valid dd.1).2 w hwd
    rw [dd.2] at hwev
    simp only [Bool.and_eq_true, bne_iff_ne, ne_eq] at hwev
    obtain ⟨hsat, hne⟩ := hwev
    generalize hHc : H2 ++ [Obj.dict (encVals names w)] = Hc
    have FGc : Frame D G Hc := by rw [← hHc]; exact (Frame.ofBase F2).trans (Frame.append _ _ _)
    have Fhc : Frame D h Hc := FhG.trans FGc
    have keep : ∀ a o, hget h a = some o → ¬ D.mut a → hget Hc a = some o := fun a o hg hm => by
      rw [Fhc.2 a (hget_lt hg) hm]; exact hg
    have hRG := hget_lt hGR
    have hRc : hget Hc R = some (.dict kvs1) := by
      rw [← hHc, hget_append_lt _ (by omega), F2.2 R (hget_lt hGR) hRb]; exact hGR
    have hWc : hget Hc G.length = some (.dict (encVals names w)) := by
      rw [← hHc, ← L2]; simp [hget]
    have hcb := cex_branch ext (D := D) hnd t k (env.set "world" (.ref G.length)) Hc A AS G.length R vkvs as vs vc w
      kvs1 (by rw [hwl]) (by simp [Env.get_set, hval]) (by simp [Env.get_set]) (by simp [Env.get_set, hres])
      (keep _ _ hA hmA) has (keep _ _ hAS hmAS) hl (fun p hp => FRel.frame Fhc _ _ (hz p hp)) hs hc
      (FRel.frame Fhc _ _ hfs) (FRel.frame Fhc _ _ hfc) hWc hRc hsat hne (by omega)
    rw [hcb]
    simp only [seqF_normal, execB_nil_eq]
    have RC : MRel names lim D Hc (finM names.length m ctx d) := by rw [← hHc]; exact R3.append _
    have hlc : G.length < Hc.length := by rw [← hHc, ← L2]; simp
    generalize hTr : truthsV t.assumptions w = trs
    generalize hCx : cexKV G.length Hc.length (t.source.eval (envOf w)) (t.candidate.eval (envOf w)) = cx
    have RD := (RC.append (Obj.list trs)).append (Obj.dict cx)
    simp only [List.append_assoc, List.singleton_append] at RD
    obtain ⟨RF, FF⟩ := RD.hsetOwn hRo r1 r2 r3 r4 (Obj.dict (dictSet Dialect.py (dictSet Dialect.py kvs1
      (V.str "decision") (V.str "counterexample")) (V.str "counterexample") (V.ref (Hc.length + 1))))
    have FcF : FrameS D.mut Hc (hset (Hc ++ [Obj.list trs, Obj.dict cx]) R (Obj.dict (dictSet Dialect.py
        (dictSet Dialect.py kvs1 (V.str "decision") (V.str "counterexample")) (V.str "counterexample")
        (V.ref (Hc.length + 1))))) := by
      refine FrameS.trans ?_ (FrameS.of_frame FF)
      have := (FrameS.append D.mut Hc (Obj.list trs)).trans (FrameS.append D.mut _ (Obj.dict cx))
      simpa using this
    have hRlc : R < Hc.length := by omega
    have hmT : ¬ D.mut Hc.length := fresh_not_mut RC (Nat.le_refl _)
    have hmX : ¬ D.mut (Hc.length + 1) := fresh_not_mut RC (by omega)
    have hmW : ¬ D.mut G.length := fresh_not_mut R2 (Nat.le_refl _)
    refine ⟨_, _, rfl, fun y h1 h2 h3 h4 => by simp [Env.get_set, Ne.symm h1, Ne.symm h2, Ne.symm h3, Ne.symm h4],
      _, hget_hset_same _ (by simp; omega), ?_, RF, (FrameS.of_frame Fhc).trans FcF⟩
    have hcex : cexOf t m.nodes d = some ⟨w, t.source.eval (envOf w), t.candidate.eval (envOf w),
        t.assumptions.map (fun f => f.eval (envOf w))⟩ := by
      simp [cexOf, hwd]
    simp only [repT, hd0, if_false, hcex, optT]
    refine ReadsKV.dictSet _ ?_ _ _ (ReadsKV.dictSet _ (ReadsM.str _ _ _) _ _
      (hkv1.frame ((FrameS.of_frame FGc).trans FcF)))
    have hbools : ∀ fs : List (BForm names.length), ∀ H : Heap,
        ReadsL D.mut H (fs.map fun f => V.bool (f.eval (envOf w)))
          ((fs.map fun f => f.eval (envOf w)).map T.bool) := by
      intro fs H
      induction fs with
      | nil => exact ReadsL.nil _ _
      | cons f fs ih => exact ReadsL.cons (ReadsM.bool _ _ _) ih
    refine ReadsM.dict (kvs := cx) (by rw [hget_hset_ne _ (by omega)]; simp [hget]) hmX ?_
    rw [← hCx]
    refine ReadsKV.cons (reads_world ?_ hmW) (ReadsKV.cons (ReadsM.bool _ _ _) (ReadsKV.cons (ReadsM.bool _ _ _)
      (ReadsKV.cons (ReadsM.list (vs := trs) ?_ hmT ?_) (ReadsKV.nil _ _))))
    · rw [hget_hset_ne _ (by omega), hget_append_lt_list _ hlc]; exact hWc
    · rw [hget_hset_ne _ (by omega)]; simp [hget]
    · rw [← hTr]; exact hbools _ _

/-- An optional diagram identifier as a Python value (`None` when absent). -/
def ovT : Option Nat → V
  | none => .none
  | some s => iv s

theorem reads_ovT (M : Nat → Prop) (h : Heap) (o : Option Nat) : ReadsM M h (ovT o) (optT natT o) := by
  cases o with
  | none => exact ReadsM.none M h
  | some s => exact ReadsM.int M h _

def diagS : S :=
  S.assign [Tgt.sub (E.var "result") (E.lit (V.str "diagram"))]
    (E.dictD [E.lit (V.str "nodes"), E.attr (E.var "manager") "nodes", E.lit (V.str "source"), E.var "source",
      E.lit (V.str "candidate"), E.var "candidate", E.lit (V.str "context"), E.var "context",
      E.lit (V.str "difference"), E.var "difference"])

def diagKV (N : Nat) (s c : Option Nat) (ctx : Nat) (d : Option Nat) : List (V × V) :=
  [(.str "nodes", .ref N), (.str "source", ovT s), (.str "candidate", ovT c), (.str "context", iv ctx),
   (.str "difference", ovT d)]

theorem reads_nodes {names : List String} {lim : Limits} {D : Addrs} {h : Heap} {m : Mgr}
    (hR : MRel names lim D h m) {M : Nat → Prop} (hM : ∀ a, M a → D.mut a) (hN : ¬ M D.nodes) :
    ReadsM M h (.ref D.nodes) (.arr (m.nodes.toList.map nodeT)) := by
  obtain ⟨ptrs, hp, hl, hpr⟩ := hR.nodes
  refine ReadsM.list hp hN ?_
  have key : ∀ (j : Nat) (rest : List Node) (hj : j + rest.length = m.nodes.size),
      (∀ i (hi : i < rest.length), rest[i] = m.nodes[j + i]'(by omega)) →
      ReadsL M h (ptrs.drop j) (rest.map nodeT) := by
    intro j rest
    induction rest generalizing j with
    | nil =>
      intro hj _
      have : ptrs.drop j = [] := List.drop_eq_nil_of_le (by simp at hj; omega)
      rw [this]; exact ReadsL.nil _ _
    | cons nd rest ih =>
      intro hj he
      have hjs : j < m.nodes.size := by simp at hj; omega
      obtain ⟨b, hb, hnm, hg⟩ := hpr j hjs
      have hd : ptrs.drop j = .ref b :: ptrs.drop (j + 1) := by
        rw [List.drop_eq_getElem_cons (by omega)]
        congr 1
        have := List.getElem?_eq_getElem (l := ptrs) (i := j) (by omega)
        rw [hb] at this; exact (Option.some.inj this).symm
      rw [hd]
      have e0 : nd = m.nodes[j] := by simpa using he 0 (by simp)
      refine ReadsL.cons ?_ (ih (j + 1) (by simp at hj ⊢; omega) (fun i hi => by
        have := he (i + 1) (by simp; omega); simpa [Nat.add_assoc, Nat.add_comm 1 i] using this))
      rw [e0]
      exact ReadsM.list hg (fun e => hnm (hM _ e))
        (ReadsL.cons (ReadsM.int _ _ _) (ReadsL.cons (ReadsM.int _ _ _) (ReadsL.cons (ReadsM.int _ _ _)
          (ReadsL.nil _ _))))
  have := key 0 m.nodes.toList (by simp) (fun i hi => by simp)
  simpa using this

theorem diag_sim (ext : Ext) {names : List String} {lim : Limits} {D : Addrs} (k : Nat) (env : Env) (h : Heap)
    (m : Mgr) (R : Nat) (kvs : List (V × V)) (s c d : Option Nat) (ctx : Nat)
    (hmg : env.get "manager" = some (.ref D.self)) (hres : env.get "result" = some (.ref R))
    (hs : env.get "source" = some (ovT s)) (hc : env.get "candidate" = some (ovT c))
    (hctx : env.get "context" = some (iv ctx)) (hd : env.get "difference" = some (ovT d))
    (hR : MRel names lim D h m) (hRo : R ∈ D.own) (r1 : R ≠ D.self) (r2 : R ≠ D.nodes) (r3 : R ≠ D.uniq)
    (r4 : R ≠ D.memo) (hRk : hget h R = some (.dict kvs)) :
    execS (pyCtx ext) (interp (pyCtx ext) (k + 1)) env h diagS =
      .ok (.normal env) (hset (h ++ [.dict (diagKV D.nodes s c ctx d)]) R
        (.dict (dictSet .py kvs (.str "diagram") (.ref h.length)))) ∧
    MRel names lim D (hset (h ++ [.dict (diagKV D.nodes s c ctx d)]) R
        (.dict (dictSet .py kvs (.str "diagram") (.ref h.length)))) m ∧
    FrameS (fun a => a = R) h (hset (h ++ [.dict (diagKV D.nodes s c ctx d)]) R
        (.dict (dictSet .py kvs (.str "diagram") (.ref h.length)))) ∧
    ReadsM (fun a => a = R) (hset (h ++ [.dict (diagKV D.nodes s c ctx d)]) R
        (.dict (dictSet .py kvs (.str "diagram") (.ref h.length)))) (.ref h.length)
      (diagramT ⟨m.nodes, s, c, ctx, d⟩) := by
  have hselfR := hR.self
  simp only [diagramFields, iv] at hselfR
  have hRlt := hget_lt hRk
  have h1 : execS (pyCtx ext) (interp (pyCtx ext) (k + 1)) env h diagS =
      .ok (.normal env) (hset (h ++ [.dict (diagKV D.nodes s c ctx d)]) R
        (.dict (dictSet .py kvs (.str "diagram") (.ref h.length)))) := by
    simp [diagS, execS, evalE, evalL, bindS, bindE, assignAll, assignT, storeOp, attrOp, hmg, hres, hs, hc, hctx, hd,
      hselfR, fieldGet, Out.bind, hget_append_lt_list _ hRlt, hRk, hashable, diagKV, pairUp, iv, dictSet, keyEq, eqD, eqPy]
  obtain ⟨R1, _⟩ := (hR.append (Obj.dict (diagKV D.nodes s c ctx d))).hsetOwn hRo r1 r2 r3 r4
    (.dict (dictSet .py kvs (.str "diagram") (.ref h.length)))
  have FF : FrameS (fun a => a = R) h (hset (h ++ [.dict (diagKV D.nodes s c ctx d)]) R
      (.dict (dictSet .py kvs (.str "diagram") (.ref h.length)))) :=
    (FrameS.append _ _ _).trans (FrameS.hset _ _ rfl)
  refine ⟨h1, R1, FF, ?_⟩
  have hRm : ∀ a, a = R → D.mut a := fun a e => e ▸ Or.inr (Or.inr (Or.inr (Or.inr hRo)))
  refine ReadsM.dict (kvs := diagKV D.nodes s c ctx d) (by rw [hget_hset_ne _ (by omega)]; simp [hget])
    (by omega) ?_
  simp only [diagKV]
  exact ReadsKV.cons (reads_nodes R1 hRm r2.symm) (ReadsKV.cons (reads_ovT _ _ _) (ReadsKV.cons (reads_ovT _ _ _)
    (ReadsKV.cons (ReadsM.int _ _ _) (ReadsKV.cons (reads_ovT _ _ _) (ReadsKV.nil _ _)))))

end PCSCR.Py
