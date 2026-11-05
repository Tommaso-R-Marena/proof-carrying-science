import PCSConditionalRuntime.JsShrink
import PCSConditionalRuntime.PyWits

/-!
# `checkConditional`: core-necessity witnesses refine `PCSDD.coreWits`

```
const necessities=core.map(i=>{const assignment=m.world(m.conjunction(
    core.filter(j=>j!==i).map(j=>premises[j])));
  if(assignment===null)throw Error('Invalid minimal conflict');
  return {removed_assumption:i,assignment};});
```
(lowered to a loop over `core` pushing onto a fresh array; the callback variables are renamed
`i#3`, `j#3`, `j#4`).  The `throw` is never reached: by inclusion-minimality of the core
(`shrink_spec`), every conjunction with one premise removed is satisfiable, hence not `0`.
The witness counter stays a safe integer: every call adds at most `names.length` steps.
-/

namespace PCSCR.Js

open PCSCR PCSDD PCSOmega PCSCR.Py

/-! ## Counters untouched by `apply` -/

theorem mkNode_wsteps {lim : Limits} {m m' : Mgr} {v lo hi r : Nat}
    (h : mkNode lim m v lo hi = .ok (r, m')) : m'.wsteps = m.wsteps := by
  unfold mkNode at h
  split at h
  · cases h; rfl
  · split at h
    · cases h; rfl
    · split at h
      · cases h
      · cases h; rfl

theorem apply_wsteps {n : Nat} {lim : Limits} :
    ∀ (fuel : Nat) (op : BOp) (a b : Nat) (m : Mgr) (r : Nat) (m' : Mgr),
      apply n lim fuel op a b m = .ok (r, m') → m'.wsteps = m.wsteps
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
                rw [mkNode_wsteps h3, apply_wsteps _ _ _ _ _ _ _ h2, apply_wsteps _ _ _ _ _ _ _ h1]

theorem conjList_wsteps {n : Nat} {lim : Limits} :
    ∀ (ps : List (Nat × BForm n)) (acc : Nat) (m : Mgr) (r : Nat) (m' : Mgr),
      conjList n lim ps acc m = .ok (r, m') → m'.wsteps = m.wsteps
  | [], _, _, _, _, h => by simp only [conjList] at h; cases h; rfl
  | p :: ps, acc, m, r, m', h => by
      simp only [conjList] at h
      split at h
      · cases h
      · rename_i acc' m1 h1
        rw [conjList_wsteps ps acc' m1 r m' h, apply_wsteps _ _ _ _ _ _ _ h1]

/-! ## Comprehensions whose iterable allocates -/

theorem jcomp_eval' (ext : Ext) (k : Nat) (env : Env) (h h1 : Heap) (x : String) (it elt : E)
    (filt : Option E) (vi : V) (xs : List V) (g : V → V) (p : V → Bool) (K0 : Nat)
    (hev : evalE (jsCtx ext) (interp (jsCtx ext) k) env h it = .ok vi h1)
    (hit : IterOK h1 vi xs) (hk : K0 + xs.length + 1 ≤ k)
    (helt : ∀ y ∈ xs, JEvalPure ext K0 h1 env x y elt (g y))
    (hfilt : ∀ y ∈ xs, JFiltOK ext K0 h1 env x y filt (p y)) :
    evalE (jsCtx ext) (interp (jsCtx ext) k) env h (.comp elt x it filt) =
      .ok (.ref h1.length) (h1 ++ [.list ((xs.filter p).map g)]) := by
  obtain ⟨env'', e⟩ := jcomp_loop ext h1 env x vi xs elt filt g p K0 hit helt hfilt xs [] 0 k env rfl hk
    (fun _ _ => rfl)
  simp only [evalE, hev, Out.bind, e, compResult, List.nil_append]

/-- `core.filter(j => j !== i).map(j => premises[j])` (two fresh arrays). -/
theorem jcomp_pick_ne (ext : Ext) (k : Nat) (env : Env) (h : Heap) (P C : Nat) (prs : List (Nat × BForm n))
    (cs : List Nat) (i0 : Nat) (hprem : env.get "premises" = some (.ref P))
    (hcore : env.get "core" = some (.ref C)) (hi : env.get "i#3" = some (iv i0))
    (hP : hget h P = some (.list (prs.map (fun p => iv p.1)))) (hC : hget h C = some (.list (cs.map iv)))
    (hcs : ∀ r ∈ cs, r < prs.length) (hk : cs.length + 1 ≤ k) :
    evalE (jsCtx ext) (interp (jsCtx ext) k) env h
        (E.comp (E.sub (E.var "premises") (E.var "j#4")) "j#4"
          (E.comp (E.var "j#3") "j#3" (E.var "core") (some (E.bin BinOp.ne (E.var "j#3") (E.var "i#3"))))
          none) =
      .ok (.ref (h.length + 1)) (h ++ [.list ((cs.filter (· != i0)).map iv),
        .list ((pick prs (cs.filter (· != i0))).map (fun p => iv p.1))]) := by
  have hin : evalE (jsCtx ext) (interp (jsCtx ext) k) env h
      (E.comp (E.var "j#3") "j#3" (E.var "core") (some (E.bin BinOp.ne (E.var "j#3") (E.var "i#3")))) =
      .ok (.ref h.length) (h ++ [.list ((cs.filter (· != i0)).map iv)]) := by
    have e := jcomp_eval ext k env h "j#3" (E.var "core") (E.var "j#3")
      (some (E.bin BinOp.ne (E.var "j#3") (E.var "i#3"))) (.ref C) (cs.map iv) id
      (fun v => !(decide (v = iv i0))) 0 (by simp [evalE, hcore]) (IterOK.ref hC) (by simpa using hk)
      (fun y _ k' _ env' H hx _ _ => by simp [evalE, hx])
      (fun y hy k' _ env' H hx hz _ => by
        simp only [List.mem_map] at hy
        obtain ⟨c, _, rfl⟩ := hy
        have hi' : env'.get "i#3" = some (iv i0) := by rw [hz "i#3" (by decide)]; exact hi
        simp [evalE, hx, hi', binOp, eqD, iv, eqJs_int])
    rw [e, List.map_id, filter_map_iv]
  have hrs : ∀ r ∈ cs.filter (· != i0), r < prs.length := fun r hr => hcs r (List.mem_filter.1 hr).1
  have hR : hget (h ++ [.list ((cs.filter (· != i0)).map iv)]) h.length =
      some (.list ((cs.filter (· != i0)).map iv)) := by simp [hget]
  have hP1 : hget (h ++ [.list ((cs.filter (· != i0)).map iv)]) P = some (.list (prs.map (fun p => iv p.1))) := by
    rw [hget_append_lt _ (hget_lt hP)]; exact hP
  have e := jcomp_eval' ext k env h (h ++ [.list ((cs.filter (· != i0)).map iv)]) "j#4" _
    (E.sub (E.var "premises") (E.var "j#4")) none (.ref h.length) ((cs.filter (· != i0)).map iv)
    (jpremG prs) (fun _ => true) 0 hin (IterOK.ref hR) (by simp; have := List.length_filter_le (· != i0) cs; omega)
    (fun y hy k' _ env' H hx hz hag => by
      simp only [List.mem_map] at hy
      obtain ⟨r, hr, rfl⟩ := hy
      have hp' : env'.get "premises" = some (.ref P) := by rw [hz "premises" (by decide)]; exact hprem
      have hPH : hget H P = some (.list (prs.map (fun p => iv p.1))) := by
        rw [hag.2 P (hget_lt hP1)]; exact hP1
      have := jsubOp_idx (h := H) (j := r) hPH (by simp; exact hrs r hr)
      simp only [iv] at this
      simp [evalE, hx, hp', Out.bind, iv, this, jpremG])
    (fun _ _ => rfl)
  rw [e, List.filter_eq_self.2 (fun _ _ => rfl), jpremG_map prs _ hrs]
  simp

/-- `Diagram.world` with the base frame (owned addresses untouched). -/
theorem jworld_sim_pos2 (ext : Ext) {names : List String} {lim : Limits} {D : Addrs} (hnd : names.Nodup)
    (k : Nat) (hk : names.length + 1 ≤ k) (h : Heap) (m : Mgr) (u : Nat) (hR : JMRel names lim D h m)
    (hinv : Inv names.length lim m) (hu : u < m.nodes.size + 2) (h0 : u ≠ 0)
    (hws : m.wsteps + names.length ≤ 9007199254740991) :
    ∃ H', (interp (jsCtx ext) (k + 1)).call "Diagram.world" [.ref D.self, iv u] h =
        .ok (.ref (h.length + 1 + names.length)) (H' ++ [.dict (encVals names (wit names.length m.nodes 0 u))]) ∧
      JMRel names lim D H' { m with wsteps := m.wsteps + witSteps names.length m.nodes 0 u } ∧
      Frame D.base h H' ∧ H'.length = h.length + 1 + names.length := by
  obtain ⟨H1, e1, R1, _, L1⟩ := jworld_sim_pos ext hnd k hk h m u hR hinv hu h0 hws
  obtain ⟨H2, e2, _, F2, _⟩ := jworld_sim_pos ext (D := D.base) hnd k hk h m u hR.base hinv hu h0 hws
  simp only [Addrs.base_self] at e2
  rw [e1] at e2
  simp only [Out.ok.injEq, true_and] at e2
  have := List.append_inj_left' e2 rfl
  subst this
  exact ⟨H1, e1, R1, F2, L1⟩

def jwitsBody : List S :=
  [S.assign [Tgt.name "assignment"]
     (E.mcall (E.var "m") "world"
       [E.mcall (E.var "m") "conjunction"
         [E.comp (E.sub (E.var "premises") (E.var "j#4")) "j#4"
           (E.comp (E.var "j#3") "j#3" (E.var "core") (some (E.bin BinOp.ne (E.var "j#3") (E.var "i#3"))))
           none]]),
   S.ifte (E.bin BinOp.eq (E.var "assignment") (E.lit V.none))
     [S.raise (E.call "%newError" [E.lit (V.str "Error"), E.lit (V.str "Invalid minimal conflict")])] [],
   S.expr (E.mcall (E.var "necessities") "push"
     [E.dictD [E.lit (V.str "removed_assumption"), E.var "i#3", E.lit (V.str "assignment"), E.var "assignment"]])]

def JWitsOut (names : List String) (lim : Limits) (D : Addrs) (N : Nat) (h : Heap) (env : Env) (ds : List V) :
    Except (LimitReached × Mgr) (List (Nat × List Bool) × Mgr) → Out Flow → Prop
  | .ok (ws, m'), o => ∃ env' h' ds', o = .ok (.normal env') h' ∧ hget h' N = some (.list (ds ++ ds')) ∧
      ReadsL D.mut h' ds' (ws.map (witT names)) ∧
      (∀ y, y ≠ "i#3" → y ≠ "assignment" → env'.get y = env.get y) ∧
      JMRel names lim D h' m' ∧ FrameS (MutP D N) h h'
  | .error (e, m'), o => ∃ env' h' a, o = .ok (.raise (.obj (.ref a)) env') h' ∧
      hget h' a = some (.inst "ResourceLimit" [("message", .str e.name)]) ∧
      JMRel names lim D h' m' ∧ FrameS (MutP D N) h h'

theorem jwits_loop (ext : Ext) {names : List String} {lim : Limits} {D : Addrs} (hnd : names.Nodup)
    (P N C : Nat) (prs : List (Nat × BForm names.length)) (core : List Nat)
    (hmin : ∀ i ∈ core, ∃ ρ, SatSet prs (core.filter (· != i)) ρ) (hcl : ∀ c ∈ core, c < prs.length)
    (hcn : core.length ≤ prs.length)
    (hN : N ∈ D.own) (n1 : N ≠ D.self) (n2 : N ≠ D.nodes) (n3 : N ≠ D.uniq) (n4 : N ≠ D.memo)
    (hPN : P ≠ N) :
    ∀ (is : List Nat) (k j : Nat) (env : Env) (h : Heap) (m : Mgr) (ds : List V),
      applyFuel lim + prs.length + names.length + is.length + 4 ≤ k →
      hget h C = some (.list (core.map iv)) → ¬ D.mut C → (core.map iv).drop j = is.map iv →
      (∀ i ∈ is, i ∈ core) →
      env.get "premises" = some (.ref P) → env.get "m" = some (.ref D.self) →
      env.get "core" = some (.ref C) → env.get "necessities" = some (.ref N) →
      hget h P = some (.list (prs.map (fun p => iv p.1))) → ¬ D.base.mut P →
      hget h N = some (.list ds) →
      JMRel names lim D h m → Inv names.length lim m → RootsOK m prs →
      m.wsteps + is.length * names.length ≤ 9007199254740991 →
      JWitsOut names lim D N h env ds (coreWits names.length lim prs core is m)
        ((interp (jsCtx ext) (k + 1)).forLoop env h (.name "i#3") (.ref C) j jwitsBody)
  | [], k, j, env, h, m, ds, hk, hC, hmC, hxs, his, hp, hmg, hc, hn, hP, hmP, hNl, hR, hinv, hroots, hws => by
      rw [interp_succ_forLoop]
      have hj : (core.map iv)[j]? = none := by
        have := congrArg List.length hxs; simp at this
        exact List.getElem?_eq_none (by simp; omega)
      simp only [forIter, elemAt, hC, hj, coreWits]
      exact ⟨env, h, [], rfl, by simpa using hNl, ReadsL.nil _ _, fun _ _ _ => rfl, hR, FrameS.refl _ _⟩
  | i0 :: is, k, j, env, h, m, ds, hk, hC, hmC, hxs, his, hp, hmg, hc, hn, hP, hmP, hNl, hR, hinv,
      hroots, hws => by
      obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by simp at hk; omega⟩
      rw [interp_succ_forLoop]
      have hj : (core.map iv)[j]? = some (iv i0) := by
        have := congrArg (fun l => l[0]?) hxs; simpa using this
      have hi0 : i0 ∈ core := his i0 (by simp)
      have hselfR := hR.self
      simp only [jdiagramFields, iv] at hselfR
      have hprsb : ∀ p ∈ prs, p.1 < m.nodes.size + 2 := fun p hp' => (hroots p hp').1
      simp only [forIter, elemAt, hC, hj, bindE, assignT, coreWits]
      have hc1 := jcomp_pick_ne ext (k' + 1) (env.set "i#3" (iv i0)) h P C prs core i0 (by simp [hp])
        (by simp [hc]) (by simp) hP hC hcl (by simp at hk; omega)
      obtain ⟨rem, hrem⟩ : ∃ rem, rem = core.filter (· != i0) := ⟨_, rfl⟩
      rw [← hrem] at hc1 ⊢
      have hreml : rem.length ≤ core.length := by rw [hrem]; exact List.length_filter_le _ _
      have hR0 := hR.append (Obj.list (rem.map iv))
      have hR1 := hR0.append (Obj.list ((pick prs rem).map (fun p => iv p.1)))
      simp only [List.append_assoc, List.singleton_append] at hR1
      have hL1 : hget (h ++ [Obj.list (rem.map iv), Obj.list ((pick prs rem).map (fun p => iv p.1))])
          (h.length + 1) = some (.list ((pick prs rem).map (fun p => iv p.1))) := by simp [hget]
      have hmL := jfresh_not_mut hR0 (a := h.length + 1) (by simp)
      have hmLb : ¬ D.base.mut (h.length + 1) := fun e => hmL (Addrs.base_mut e)
      have hpsb : ∀ p ∈ pick prs rem, p.1 < m.nodes.size + 2 := pick_bound hprsb (by omega) rem
      have hpsl : (pick prs rem).length = rem.length := by simp [pick]
      have scj := JSimOut.both
        (jconjunction_sim ext (pick prs rem) k' (by simp at hk; omega) _ m _ hL1 hmL hR1 hinv hpsb)
        (jconjunction_sim ext (D := D.base) (pick prs rem) k' (by simp at hk; omega) _ m _ hL1 hmLb hR1.base
          hinv hpsb)
      have hselfR1 : hget (h ++ [Obj.list (rem.map iv), Obj.list ((pick prs rem).map (fun p => iv p.1))])
          D.self = hget h D.self := by
        rw [← List.singleton_append, ← List.append_assoc]
        rw [hget_append_lt _ (by simp; have := hR.addrs_lt.1; omega), hget_append_lt _ hR.addrs_lt.1]
      rw [hselfR] at hselfR1
      have hcl2 : classHasMethod jsProg "Diagram" "conjunction" = true := by decide
      have hcl3 : classHasMethod jsProg "Diagram" "world" = true := by decide
      have FN : ∀ {X Y : Heap}, Frame D.base X Y → FrameS (MutP D N) X Y :=
        fun F => (FrameS.of_frame F).mono (fun x hx => Or.inl hx)
      have FA : Frame D.base h (h ++ [Obj.list (rem.map iv), Obj.list ((pick prs rem).map (fun p => iv p.1))]) := by
        have := (Frame.append D.base h (Obj.list (rem.map iv))).trans
          (Frame.append D.base _ (Obj.list ((pick prs rem).map (fun p => iv p.1))))
        simpa using this
      cases hcj : conjList names.length lim (pick prs rem) 1 m with
      | error q =>
        obtain ⟨e, m1⟩ := q
        rw [hcj] at scj
        obtain ⟨H3, a3, e3, ha3, R3, F3⟩ := scj
        simp only [jwitsBody]
        rw [execB_cons']
        simp [execS, bindS, evalE, evalL, Env.get_set, hmg, ↓hc1, Out.bind, hselfR1, hcl2, e3]
        simp only [loopK]
        exact ⟨_, H3, a3, rfl, ha3, R3, FN (FA.trans F3)⟩
      | ok q =>
        obtain ⟨c, m1⟩ := q
        rw [hcj] at scj
        obtain ⟨H3, e3, R3, F3⟩ := scj
        obtain ⟨i1, ex1, hc1b⟩ := conjList_inv _ 1 m c m1 hinv hpsb (by omega) hcj
        have hw1 := conjList_wsteps _ 1 m c m1 hcj
        have hc0 : c ≠ 0 := satset_ne_zero hinv hroots hcj (by rw [hrem]; exact hmin i0 hi0)
        have hws1 : m1.wsteps + names.length ≤ 9007199254740991 := by
          rw [hw1]; simp only [List.length_cons, Nat.add_mul, Nat.one_mul] at hws; omega
        obtain ⟨H4, ew, R4, F4, L4⟩ := jworld_sim_pos2 ext hnd k' (by simp at hk; omega) H3 m1 c R3 i1 hc1b hc0
          hws1
        have hselfR3 := R3.self
        simp only [jdiagramFields, iv] at hselfR3
        simp only [jwitsBody]
        rw [execB_cons']
        simp [execS, bindS, evalE, evalL, Env.get_set, hmg, ↓hc1, Out.bind, hselfR1, hcl2, e3, hselfR3, hcl3,
          ew, assignAll, assignT, bindE]
        simp only [world, hc0, if_false, Option.getD_some]
        rw [← L4]
        have hNlt : N < h.length := hget_lt hNl
        have hNb : ¬ D.base.mut N := by
          simp only [Addrs.mut, Addrs.base_self, Addrs.base_nodes, Addrs.base_uniq, Addrs.base_memo,
            Addrs.base_own, List.not_mem_nil, or_false]; omega
        have hN3 : hget H3 N = some (.list ds) := by
          rw [F3.2 N (by simp; omega) hNb, ← List.singleton_append, ← List.append_assoc,
            hget_append_lt _ (by simp; omega), hget_append_lt _ hNlt]; exact hNl
        have hN4 : hget H4 N = some (.list ds) := by
          rw [F4.2 N (by have := F3.1; simp at this; omega) hNb]; exact hN3
        have hNlt4 : N < H4.length := hget_lt hN4
        have hNlt4' : N < H4.length + 1 := by omega
        jsstepA [isNoneV]
        jsstepA [hn, hN4, hNlt4, hNlt4', dictSet, keyEq, eqD, eqJs, pairUp, hget_append_lt_list]
        simp only [execB_nil_eq, loopK]
        have hmW : ¬ D.mut H4.length := jfresh_not_mut R4 (Nat.le_refl _)
        have hmE : ¬ D.mut (H4.length + 1) := jfresh_not_mut R4 (by omega)
        have hR5 := (R4.append (Obj.dict (encVals names (wit names.length m1.nodes 0 c)))).append
          (Obj.dict [(V.str "removed_assumption", V.int ↑i0), (V.str "assignment", V.ref (List.length H4))])
        simp only [List.append_assoc, List.singleton_append] at hR5
        obtain ⟨R5, _⟩ := hR5.hsetOwn hN n1 n2 n3 n4 (Obj.list (ds ++ [V.ref (List.length H4 + 1)]))
        have FF : FrameS (MutP D N) h (hset (H4 ++
            [Obj.dict (encVals names (wit names.length m1.nodes 0 c)),
              Obj.dict [(V.str "removed_assumption", V.int ↑i0), (V.str "assignment", V.ref (List.length H4))]])
            N (Obj.list (ds ++ [V.ref (List.length H4 + 1)]))) := by
          refine (FN ((FA.trans F3).trans F4)).trans ?_
          refine FrameS.trans ?_ (FrameS.hset _ _ (Or.inr rfl))
          have := (FrameS.append (MutP D N) H4 (Obj.dict (encVals names (wit names.length m1.nodes 0 c)))).trans
            (FrameS.append (MutP D N) _
              (Obj.dict [(V.str "removed_assumption", V.int ↑i0), (V.str "assignment", V.ref (List.length H4))]))
          simpa using this
        have hnotM : ∀ a, ¬ D.mut a → ¬ MutP D N a := fun a ha hm => ha (MutP_mut hN hm)
        have hC5 := FF.2 C (hget_lt hC) (hnotM C hmC)
        rw [hC] at hC5
        have hPN' : ¬ MutP D N P := by
          intro hm; rcases hm with hm | hm
          · exact hmP hm
          · exact hPN hm
        have hP5 := FF.2 P (hget_lt hP) hPN'
        rw [hP] at hP5
        have hxs' : (core.map iv).drop (j + 1) = is.map iv := by rw [← List.drop_drop, hxs]; simp
        have hwl := witSteps_le names.length m1.nodes names.length 0 c (by simp)
        have ih := jwits_loop ext hnd P N C prs core hmin hcl hcn hN n1 n2 n3 n4 hPN is k' (j + 1)
          ((env.set "i#3" (V.int ↑i0)).set "assignment" (V.ref (List.length H4))) _ _
          (ds ++ [V.ref (List.length H4 + 1)]) (by simp at hk; omega) hC5 hmC hxs'
          (fun i hi => his i (by simp [hi])) (by simp [hp]) (by simp [hmg]) (by simp [hc]) (by simp [hn])
          hP5 hmP (by rw [hget_hset_same _ (by simp; omega)]) R5 (i1.wsteps _)
          (hroots.extend hinv ex1)
          (by
            have e1 : (i0 :: is).length * names.length = is.length * names.length + names.length := by
              simp [Nat.add_mul]
            rw [e1] at hws
            simp only [Nat.sub_zero] at hwl
            show m1.wsteps + witSteps names.length m1.nodes 0 c + is.length * names.length ≤ 9007199254740991
            rw [hw1]; omega)
        simp only [jwitsBody] at ih
        generalize coreWits names.length lim prs core is
          { m1 with wsteps := m1.wsteps + witSteps names.length m1.nodes 0 c } = res at ih ⊢
        rcases res with ⟨e, m'⟩ | ⟨ws, m'⟩
        · obtain ⟨env', h', a', eo, ha', R', F'⟩ := ih
          exact ⟨env', h', a', eo, ha', R', FF.trans F'⟩
        · obtain ⟨env', h', ds', eo, hN', hr, hy, R', F'⟩ := ih
          have hel : ReadsM D.mut (hset (H4 ++
              [Obj.dict (encVals names (wit names.length m1.nodes 0 c)),
                Obj.dict [(V.str "removed_assumption", V.int ↑i0), (V.str "assignment", V.ref (List.length H4))]])
              N (Obj.list (ds ++ [V.ref (List.length H4 + 1)]))) (V.ref (List.length H4 + 1))
              (witT names (i0, wit names.length m1.nodes 0 c)) := by
            refine ReadsM.dict (kvs := [(V.str "removed_assumption", V.int ↑i0),
                (V.str "assignment", V.ref (List.length H4))]) ?_ hmE
              (ReadsKV.cons (ReadsM.int _ _ _)
                (ReadsKV.cons (reads_world (names := names) (w := wit names.length m1.nodes 0 c) ?_
                  hmW) (ReadsKV.nil _ _)))
            · rw [hget_hset_ne _ (by omega)]; simp [hget]
            · rw [hget_hset_ne _ (by omega)]; simp [hget]
          refine ⟨env', h', V.ref (List.length H4 + 1) :: ds', eo, by simpa using hN',
            ReadsL.cons ((hel.frame ((F'.mono (fun x hx => MutP_mut hN hx)))) ) hr,
            fun y h1 h2 => by rw [hy y h1 h2]; simp [Ne.symm h1, Ne.symm h2], R', FF.trans F'⟩

end PCSCR.Js
