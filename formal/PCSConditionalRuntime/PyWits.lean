import PCSConditionalRuntime.PyRead

/-!
# `check`: core-necessity witnesses refine `PCSDD.coreWits`

```
necessities = []
for i in core:
    world = manager.world(manager.conjunction([premises[j] for j in core if j != i]))
    assert world is not None
    necessities.append({'removed_assumption': i, 'assignment': world})
```
The assertion never fails: by inclusion-minimality of the core (`shrink_spec`), every
conjunction with one premise removed is satisfiable, hence not the identifier `0`.
-/

namespace PCSCR.Py

open PCSCR PCSDD PCSOmega

/-- `[premises[j] for j in core if j != i]`. -/
theorem comp_pick_ne (ext : Ext) (k : Nat) (env : Env) (h : Heap) (P C : Nat) (prs : List (Nat × BForm n))
    (cs : List Nat) (i0 : Nat) (hprem : env.get "premises" = some (.ref P)) (hcore : env.get "core" = some (.ref C))
    (hi : env.get "i" = some (iv i0))
    (hP : hget h P = some (.list (prs.map (fun p => iv p.1)))) (hC : hget h C = some (.list (cs.map iv)))
    (hcs : ∀ r ∈ cs, r < prs.length) (hk : cs.length + 1 ≤ k) :
    evalE (pyCtx ext) (interp (pyCtx ext) k) env h
        (E.comp (E.sub (E.var "premises") (E.var "j")) "j" (E.var "core")
          (some (E.bin BinOp.ne (E.var "j") (E.var "i")))) =
      .ok (.ref h.length) (h ++ [.list ((pick prs (cs.filter (· != i0))).map (fun p => iv p.1))]) := by
  have e := comp_eval ext k env h "j" (E.var "core") (E.sub (E.var "premises") (E.var "j"))
    (some (E.bin BinOp.ne (E.var "j") (E.var "i"))) C (cs.map iv) (premG prs)
    (fun v => !(decide (v = iv i0))) 0 (by simp [evalE, hcore]) hC (by simpa using hk)
    (fun y hy k' _ env' H hx hz hag => by
      simp only [List.mem_map] at hy
      obtain ⟨r, hr, rfl⟩ := hy
      have hp' : env'.get "premises" = some (.ref P) := by rw [hz "premises" (by decide)]; exact hprem
      have hPH : hget H P = some (.list (prs.map (fun p => iv p.1))) := by
        rw [hag.2 P (hget_lt hP)]; exact hP
      have := subOp_idx (h := H) (j := r) hPH (by simp; exact hcs r hr)
      simp only [iv] at this
      simp [evalE, hx, hp', Out.bind, iv, this, premG])
    (fun y hy k' _ env' H hx hz _ => by
      simp only [List.mem_map] at hy
      obtain ⟨c, _, rfl⟩ := hy
      have hi' : env'.get "i" = some (iv i0) := by rw [hz "i" (by decide)]; exact hi
      simp [evalE, hx, hi', binOp, eqD, iv, eqPy_int])
  rw [e, filter_map_iv, premG_map prs _ (fun r hr => hcs r (List.mem_filter.1 hr).1)]

/-- `Diagram.world` with the base frame (owned addresses untouched). -/
theorem world_sim_pos2 (ext : Ext) {names : List String} {lim : Limits} {D : Addrs} (hnd : names.Nodup)
    (k : Nat) (hk : names.length + 1 ≤ k) (h : Heap) (m : Mgr) (u : Nat) (hR : MRel names lim D h m)
    (hinv : Inv names.length lim m) (hu : u < m.nodes.size + 2) (h0 : u ≠ 0) :
    ∃ H', (interp (pyCtx ext) (k + 1)).call "Diagram.world" [.ref D.self, iv u] h =
        .ok (.ref h.length) (H' ++ [.dict (encVals names (wit names.length m.nodes 0 u))]) ∧
      MRel names lim D H' { m with wsteps := m.wsteps + witSteps names.length m.nodes 0 u } ∧
      Frame D.base h H' ∧ H'.length = h.length := by
  obtain ⟨H1, e1, R1, _, L1⟩ := world_sim_pos ext hnd k hk h m u hR hinv hu h0
  obtain ⟨H2, e2, _, F2, _⟩ := world_sim_pos ext (D := D.base) hnd k hk h m u hR.base hinv hu h0
  simp only [Addrs.base_self] at e2
  rw [e1] at e2
  simp only [Out.ok.injEq, true_and] at e2
  have := List.append_inj_left' e2 rfl
  subst this
  exact ⟨H1, e1, R1, F2, L1⟩

theorem readsKV_encVals (M : Nat → Prop) (h : Heap) :
    ∀ (ps : List (String × Bool)),
      ReadsKV M h (ps.map (fun p => ((.str p.1 : V), (.bool p.2 : V)))) (ps.map fun p => (p.1, .bool p.2))
  | [] => ReadsKV.nil M h
  | p :: ps => ReadsKV.cons (ReadsM.bool M h p.2) (readsKV_encVals M h ps)

theorem reads_world {M : Nat → Prop} {h : Heap} {a : Nat} {names : List String} {w : List Bool}
    (hg : hget h a = some (.dict (encVals names w))) (hm : ¬ M a) :
    ReadsM M h (.ref a) (asgT names w) :=
  ReadsM.dict hg hm (readsKV_encVals M h (names.zip w))

/-- One necessity witness as a JSON tree. -/
def witT (names : List String) (p : Nat × List Bool) : T :=
  .obj [("removed_assumption", natT p.1), ("assignment", asgT names p.2)]

theorem witsT_eq (names : List String) (ws : List (Nat × List Bool)) :
    witsT names ws = .arr (ws.map (witT names)) := rfl

def witsBody : List S :=
  [S.assign [Tgt.name "world"]
     (E.mcall (E.var "manager") "world"
       [E.mcall (E.var "manager") "conjunction"
         [E.comp (E.sub (E.var "premises") (E.var "j")) "j" (E.var "core")
           (some (E.bin BinOp.ne (E.var "j") (E.var "i")))]]),
   S.assert (E.isNone (E.var "world") true),
   S.expr (E.mcall (E.var "necessities") "append"
     [E.dictD [E.lit (V.str "removed_assumption"), E.var "i", E.lit (V.str "assignment"), E.var "world"]])]

def WitsOut (names : List String) (lim : Limits) (D : Addrs) (N : Nat) (h : Heap) (env : Env) (ds : List V) :
    Except (LimitReached × Mgr) (List (Nat × List Bool) × Mgr) → Out Flow → Prop
  | .ok (ws, m'), o => ∃ env' h' ds', o = .ok (.normal env') h' ∧ hget h' N = some (.list (ds ++ ds')) ∧
      ReadsL D.mut h' ds' (ws.map (witT names)) ∧
      (∀ y, y ≠ "i" → y ≠ "world" → env'.get y = env.get y) ∧
      MRel names lim D h' m' ∧ FrameS (MutP D N) h h'
  | .error (e, m'), o => ∃ env' h' a, o = .ok (.raise (.obj (.ref a)) env') h' ∧
      hget h' a = some (.inst "ResourceLimit" [("args", .tup [.str e.name])]) ∧
      MRel names lim D h' m' ∧ FrameS (MutP D N) h h'

theorem satset_ne_zero {names : List String} {lim : Limits} {prs : List (Nat × BForm names.length)}
    {J : List Nat} {m m1 : Mgr} {c : Nat} (hinv : Inv names.length lim m) (hr : RootsOK m prs)
    (hcj : conjList names.length lim (pick prs J) 1 m = .ok (c, m1)) (hs : ∃ ρ, SatSet prs J ρ) :
    c ≠ 0 := by
  obtain ⟨_, _, d1⟩ := conjList_spec _ 1 m _ c m1 hinv (hr.pick _) (denotes_one m) hcj
  obtain ⟨ρ, hρ⟩ := hs
  intro hz
  have h1 := d1.2 ρ
  rw [hz, evalD_zero] at h1
  simp only [Bool.true_and] at h1
  have h2 := (allEval_pick_iff prs J ρ).2 hρ
  rw [← h1] at h2
  cases h2

theorem wits_loop (ext : Ext) {names : List String} {lim : Limits} {D : Addrs} (hnd : names.Nodup)
    (P N C : Nat) (prs : List (Nat × BForm names.length)) (core : List Nat)
    (hmin : ∀ i ∈ core, ∃ ρ, SatSet prs (core.filter (· != i)) ρ) (hcl : ∀ c ∈ core, c < prs.length)
    (hcn : core.length ≤ prs.length)
    (hN : N ∈ D.own) (n1 : N ≠ D.self) (n2 : N ≠ D.nodes) (n3 : N ≠ D.uniq) (n4 : N ≠ D.memo)
    (hPN : P ≠ N) :
    ∀ (is : List Nat) (k j : Nat) (env : Env) (h : Heap) (m : Mgr) (ds : List V),
      applyFuel lim + prs.length + names.length + is.length + 4 ≤ k →
      hget h C = some (.list (core.map iv)) → ¬ D.mut C → (core.map iv).drop j = is.map iv →
      (∀ i ∈ is, i ∈ core) →
      env.get "premises" = some (.ref P) → env.get "manager" = some (.ref D.self) →
      env.get "core" = some (.ref C) → env.get "necessities" = some (.ref N) →
      hget h P = some (.list (prs.map (fun p => iv p.1))) → ¬ D.base.mut P →
      hget h N = some (.list ds) →
      MRel names lim D h m → Inv names.length lim m → RootsOK m prs →
      WitsOut names lim D N h env ds (coreWits names.length lim prs core is m)
        ((interp (pyCtx ext) (k + 1)).forLoop env h (.name "i") (.ref C) j witsBody)
  | [], k, j, env, h, m, ds, hk, hC, hmC, hxs, his, hp, hmg, hc, hn, hP, hmP, hNl, hR, hinv, hroots => by
      rw [interp_succ_forLoop]
      have hj : (core.map iv)[j]? = none := by
        have := congrArg List.length hxs; simp at this
        exact List.getElem?_eq_none (by simp; omega)
      simp only [forIter, elemAt, hC, hj, coreWits]
      exact ⟨env, h, [], rfl, by simpa using hNl, ReadsL.nil _ _, fun _ _ _ => rfl, hR, FrameS.refl _ _⟩
  | i0 :: is, k, j, env, h, m, ds, hk, hC, hmC, hxs, his, hp, hmg, hc, hn, hP, hmP, hNl, hR, hinv,
      hroots => by
      obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by simp at hk; omega⟩
      rw [interp_succ_forLoop]
      have hj : (core.map iv)[j]? = some (iv i0) := by
        have := congrArg (fun l => l[0]?) hxs; simpa using this
      have hi0 : i0 ∈ core := his i0 (by simp)
      have hselfR := hR.self
      simp only [diagramFields, iv] at hselfR
      have hprsb : ∀ p ∈ prs, p.1 < m.nodes.size + 2 := fun p hp' => (hroots p hp').1
      simp only [forIter, elemAt, hC, hj, bindE, assignT, coreWits]
      have hc1 := comp_pick_ne ext (k' + 1) (env.set "i" (iv i0)) h P C prs core i0 (by simp [hp])
        (by simp [hc]) (by simp) hP hC hcl (by simp at hk; omega)
      obtain ⟨rem, hrem⟩ : ∃ rem, rem = core.filter (· != i0) := ⟨_, rfl⟩
      rw [← hrem] at hc1 ⊢
      have hreml : rem.length ≤ core.length := by rw [hrem]; exact List.length_filter_le _ _
      have hR1 := hR.append (Obj.list ((pick prs rem).map (fun p => iv p.1)))
      have hL1 : hget (h ++ [Obj.list ((pick prs rem).map (fun p => iv p.1))]) h.length =
          some (.list ((pick prs rem).map (fun p => iv p.1))) := by simp [hget]
      have hmL := fresh_not_mut hR (Nat.le_refl _)
      have hmLb : ¬ D.base.mut h.length := fun e => hmL (Addrs.base_mut e)
      have hpsb : ∀ p ∈ pick prs rem, p.1 < m.nodes.size + 2 := pick_bound hprsb (by omega) rem
      have hpsl : (pick prs rem).length = rem.length := by simp [pick]
      have scj := SimOut.both
        (conjunction_sim ext (pick prs rem) k' (by simp at hk; omega) _ m _ hL1 hmL hR1 hinv hpsb)
        (conjunction_sim ext (D := D.base) (pick prs rem) k' (by simp at hk; omega) _ m _ hL1 hmLb hR1.base
          hinv hpsb)
      have hselfR1 : hget (h ++ [Obj.list ((pick prs rem).map (fun p => iv p.1))]) D.self = hget h D.self :=
        hget_append_lt _ hR.addrs_lt.1
      rw [hselfR] at hselfR1
      have hcl2 : classHasMethod pyProg "Diagram" "conjunction" = true := by decide
      have hcl3 : classHasMethod pyProg "Diagram" "world" = true := by decide
      have FN : ∀ {X Y : Heap}, Frame D.base X Y → FrameS (MutP D N) X Y :=
        fun F => (FrameS.of_frame F).mono (fun x hx => Or.inl hx)
      cases hcj : conjList names.length lim (pick prs rem) 1 m with
      | error q =>
        obtain ⟨e, m1⟩ := q
        rw [hcj] at scj
        obtain ⟨H3, a3, e3, ha3, R3, F3⟩ := scj
        simp only [witsBody]
        rw [execB_cons']
        simp [execS, bindS, evalE, evalL, Env.get_set, hmg, ↓hc1, Out.bind, hselfR1, hcl2, e3]
        simp only [loopK]
        exact ⟨_, H3, a3, rfl, ha3, R3, FN ((Frame.append _ _ _).trans F3)⟩
      | ok q =>
        obtain ⟨c, m1⟩ := q
        rw [hcj] at scj
        obtain ⟨H3, e3, R3, F3⟩ := scj
        obtain ⟨i1, ex1, hc1b⟩ := conjList_inv _ 1 m c m1 hinv hpsb (by omega) hcj
        have hc0 : c ≠ 0 := satset_ne_zero hinv hroots hcj (by rw [hrem]; exact hmin i0 hi0)
        obtain ⟨H4, ew, R4, F4, L4⟩ := world_sim_pos2 ext hnd k' (by simp at hk; omega) H3 m1 c R3 i1 hc1b hc0
        have hselfR3 := R3.self
        simp only [diagramFields, iv] at hselfR3
        simp only [witsBody]
        rw [execB_cons']
        simp [execS, bindS, evalE, evalL, Env.get_set, hmg, ↓hc1, Out.bind, hselfR1, hcl2, e3, hselfR3, hcl3,
          ew, assignAll, assignT, bindE]
        simp only [world, hc0, if_false, Option.getD_some]
        have hNlt : N < h.length := hget_lt hNl
        have hNb : ¬ D.base.mut N := by
          simp only [Addrs.mut, Addrs.base_self, Addrs.base_nodes, Addrs.base_uniq, Addrs.base_memo,
            Addrs.base_own, List.not_mem_nil, or_false]; omega
        have hN3 : hget H3 N = some (.list ds) := by
          rw [F3.2 N (by simp; omega) hNb, hget_append_lt _ hNlt]; exact hNl
        have hN4 : hget H4 N = some (.list ds) := by
          rw [F4.2 N (by have := F3.1; simp at this; omega) hNb]; exact hN3
        have hNlt4 : N < H4.length := hget_lt hN4
        have hNlt4' : N < H4.length + 1 := by omega
        pystepA [isNoneV]
        pystepA [hn, hN4, hNlt4, hNlt4', dictSet, keyEq, eqD, eqPy, pairUp, hget_append_lt_list]
        simp only [execB_nil_eq, loopK]
        have hW : H3.length = H4.length := L4.symm
        have hmW : ¬ D.mut H4.length := fresh_not_mut R4 (Nat.le_refl _)
        have hmE : ¬ D.mut (H4.length + 1) := fresh_not_mut R4 (by omega)
        have hR5 := (R4.append (Obj.dict (encVals names (wit names.length m1.nodes 0 c)))).append
          (Obj.dict [(V.str "removed_assumption", V.int ↑i0), (V.str "assignment", V.ref (List.length H3))])
        simp only [List.append_assoc, List.singleton_append] at hR5
        obtain ⟨R5, _⟩ := hR5.hsetOwn hN n1 n2 n3 n4 (Obj.list (ds ++ [V.ref (List.length H4 + 1)]))
        have FF : FrameS (MutP D N) h (hset (H4 ++
            [Obj.dict (encVals names (wit names.length m1.nodes 0 c)),
              Obj.dict [(V.str "removed_assumption", V.int ↑i0), (V.str "assignment", V.ref (List.length H3))]])
            N (Obj.list (ds ++ [V.ref (List.length H4 + 1)]))) := by
          refine (FN (((Frame.append _ _ _).trans F3).trans F4)).trans ?_
          refine FrameS.trans ?_ (FrameS.hset _ _ (Or.inr rfl))
          have := (FrameS.append (MutP D N) H4 (Obj.dict (encVals names (wit names.length m1.nodes 0 c)))).trans
            (FrameS.append (MutP D N) _
              (Obj.dict [(V.str "removed_assumption", V.int ↑i0), (V.str "assignment", V.ref (List.length H3))]))
          simpa using this
        have hnotM : ∀ a, ¬ D.mut a → ¬ MutP D N a := fun a ha hm => ha (MutP_mut hN hm)
        have hlen5 : ∀ a, a < h.length → a < (hset (H4 ++
            [Obj.dict (encVals names (wit names.length m1.nodes 0 c)),
              Obj.dict [(V.str "removed_assumption", V.int ↑i0), (V.str "assignment", V.ref (List.length H3))]])
            N (Obj.list (ds ++ [V.ref (List.length H4 + 1)]))).length := fun a ha => by
          have := FF.1; omega
        have hC5 := FF.2 C (hget_lt hC) (hnotM C hmC)
        rw [hC] at hC5
        have hPN' : ¬ MutP D N P := by
          intro hm; rcases hm with hm | hm
          · exact hmP hm
          · exact hPN hm
        have hP5 := FF.2 P (hget_lt hP) hPN'
        rw [hP] at hP5
        have hxs' : (core.map iv).drop (j + 1) = is.map iv := by rw [← List.drop_drop, hxs]; simp
        have ih := wits_loop ext hnd P N C prs core hmin hcl hcn hN n1 n2 n3 n4 hPN is k' (j + 1)
          ((env.set "i" (V.int ↑i0)).set "world" (V.ref (List.length H3))) _ _
          (ds ++ [V.ref (List.length H4 + 1)]) (by simp at hk; omega) hC5 hmC hxs'
          (fun i hi => his i (by simp [hi])) (by simp [hp]) (by simp [hmg]) (by simp [hc]) (by simp [hn])
          hP5 hmP (by rw [hget_hset_same _ (by simp; omega)]) R5 (i1.wsteps _)
          (hroots.extend hinv ex1)
        simp only [witsBody] at ih
        generalize coreWits names.length lim prs core is
          { m1 with wsteps := m1.wsteps + witSteps names.length m1.nodes 0 c } = res at ih ⊢
        rcases res with ⟨e, m'⟩ | ⟨ws, m'⟩
        · obtain ⟨env', h', a', eo, ha', R', F'⟩ := ih
          exact ⟨env', h', a', eo, ha', R', FF.trans F'⟩
        · obtain ⟨env', h', ds', eo, hN', hr, hy, R', F'⟩ := ih
          have hel : ReadsM D.mut (hset (H4 ++
              [Obj.dict (encVals names (wit names.length m1.nodes 0 c)),
                Obj.dict [(V.str "removed_assumption", V.int ↑i0), (V.str "assignment", V.ref (List.length H3))]])
              N (Obj.list (ds ++ [V.ref (List.length H4 + 1)]))) (V.ref (List.length H4 + 1))
              (witT names (i0, wit names.length m1.nodes 0 c)) := by
            refine ReadsM.dict (kvs := [(V.str "removed_assumption", V.int ↑i0),
                (V.str "assignment", V.ref (List.length H3))]) ?_ hmE
              (ReadsKV.cons (ReadsM.int _ _ _)
                (ReadsKV.cons (reads_world (names := names) (w := wit names.length m1.nodes 0 c) ?_
                  (by rw [hW]; exact hmW)) (ReadsKV.nil _ _)))
            · rw [hget_hset_ne _ (by omega)]; simp [hget]
            · rw [hW, hget_hset_ne _ (by omega)]; simp [hget]
          refine ⟨env', h', V.ref (List.length H4 + 1) :: ds', eo, by simpa using hN',
            ReadsL.cons ((hel.frame ((F'.mono (fun x hx => MutP_mut hN hx)))) ) hr,
            fun y h1 h2 => by rw [hy y h1 h2]; simp [Ne.symm h1, Ne.symm h2], R', FF.trans F'⟩

end PCSCR.Py
