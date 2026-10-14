import PCSConditionalRuntime.PyComp

/-!
# `check`: deletion-based conflict shrinking refines `PCSDD.shrink`

```
core = list(range(len(premises)))
for i in list(core):
    remaining = [j for j in core if j != i]
    if manager.conjunction([premises[j] for j in remaining]) == 0: core = remaining
```
-/

namespace PCSCR.Py

open PCSCR PCSDD PCSOmega

theorem fresh_not_mut {names : List String} {lim : Limits} {D : Addrs} {h : Heap} {m : Mgr}
    (hR : MRel names lim D h m) {a : Nat} (ha : h.length ≤ a) : ¬ D.mut a := by
  have hl := hR.addrs_lt
  intro hm
  rcases hm with e | e | e | e | e
  · omega
  · omega
  · omega
  · omega
  · have := hR.own_lt a e; omega

theorem eqPy_int (a b : Int) : eqPy (.int a) (.int b) = some (decide (a = b)) := by
  simp only [eqPy, num]
  by_cases hab : a = b <;> simp [hab]

theorem filter_map_iv (i0 : Nat) : ∀ (cs : List Nat),
    (cs.map iv).filter (fun v => !(decide (v = iv i0))) = (cs.filter (· != i0)).map iv
  | [] => rfl
  | c :: cs => by
      have ih := filter_map_iv i0 cs
      by_cases hc : c = i0
      · subst hc; simp [ih]
      · have : iv c ≠ iv i0 := by simp [iv]; omega
        simp [hc, this, ih]

/-- `[j for j in core if j != i]`. -/
theorem comp_filter_ne (ext : Ext) (k : Nat) (env : Env) (h : Heap) (C : Nat) (cs : List Nat) (i0 : Nat)
    (hcore : env.get "core" = some (.ref C)) (hi : env.get "i" = some (iv i0))
    (hC : hget h C = some (.list (cs.map iv))) (hk : cs.length + 1 ≤ k) :
    evalE (pyCtx ext) (interp (pyCtx ext) k) env h
        (E.comp (E.var "j") "j" (E.var "core") (some (E.bin BinOp.ne (E.var "j") (E.var "i")))) =
      .ok (.ref h.length) (h ++ [.list ((cs.filter (· != i0)).map iv)]) := by
  have e := comp_eval ext k env h "j" (E.var "core") (E.var "j")
    (some (E.bin BinOp.ne (E.var "j") (E.var "i"))) C (cs.map iv) id
    (fun v => !(decide (v = iv i0))) 0 (by simp [evalE, hcore]) hC (by simpa using hk)
    (fun y _ k' _ env' H hx _ _ => by simp [evalE, hx])
    (fun y hy k' _ env' H hx hz _ => by
      simp only [List.mem_map] at hy
      obtain ⟨c, _, rfl⟩ := hy
      have hi' : env'.get "i" = some (iv i0) := by rw [hz "i" (by decide)]; exact hi
      simp [evalE, hx, hi', binOp, eqD, iv, eqPy_int])
  rw [e, List.map_id, filter_map_iv]

/-- Index lookup into the premise list (out-of-range indices are never used). -/
def premG (prs : List (Nat × BForm n)) : V → V
  | .int z => (prs.map (fun p => iv p.1)).getD z.toNat .none
  | _ => .none

theorem premG_map (prs : List (Nat × BForm n)) :
    ∀ (rs : List Nat), (∀ r ∈ rs, r < prs.length) →
      (rs.map iv).map (premG prs) = (pick prs rs).map (fun p => iv p.1)
  | [], _ => rfl
  | r :: rs, hr => by
      have h1 := hr r (by simp)
      have ih := premG_map prs rs (fun x hx => hr x (by simp [hx]))
      simp only [List.map_cons, pick] at ih ⊢
      rw [ih]
      simp [premG, iv, List.getD_eq_getElem?_getD, h1]

/-- `[premises[j] for j in remaining]`. -/
theorem comp_pick (ext : Ext) (k : Nat) (env : Env) (h : Heap) (P R : Nat) (prs : List (Nat × BForm n))
    (rs : List Nat) (hprem : env.get "premises" = some (.ref P)) (hrem : env.get "remaining" = some (.ref R))
    (hP : hget h P = some (.list (prs.map (fun p => iv p.1)))) (hR : hget h R = some (.list (rs.map iv)))
    (hrs : ∀ r ∈ rs, r < prs.length) (hk : rs.length + 1 ≤ k) :
    evalE (pyCtx ext) (interp (pyCtx ext) k) env h
        (E.comp (E.sub (E.var "premises") (E.var "j")) "j" (E.var "remaining") none) =
      .ok (.ref h.length) (h ++ [.list ((pick prs rs).map (fun p => iv p.1))]) := by
  have e := comp_eval ext k env h "j" (E.var "remaining") (E.sub (E.var "premises") (E.var "j")) none R
    (rs.map iv) (premG prs) (fun _ => true) 0 (by simp [evalE, hrem]) hR (by simpa using hk)
    (fun y hy k' _ env' H hx hz hag => by
      simp only [List.mem_map] at hy
      obtain ⟨r, hr, rfl⟩ := hy
      have hp' : env'.get "premises" = some (.ref P) := by rw [hz "premises" (by decide)]; exact hprem
      have hPH : hget H P = some (.list (prs.map (fun p => iv p.1))) := by
        rw [hag.2 P (hget_lt hP)]; exact hP
      have := subOp_idx (h := H) (j := r) hPH (by simp; exact hrs r hr)
      simp only [iv] at this
      simp [evalE, hx, hp', Out.bind, iv, this, premG])
    (fun _ _ => rfl)
  rw [e, List.filter_eq_self.2 (fun _ _ => rfl), premG_map prs rs hrs]

theorem conjList_inv {n : Nat} {lim : Limits} :
    ∀ (ps : List (Nat × BForm n)) (acc : Nat) (m : Mgr) r (m' : Mgr), Inv n lim m →
      (∀ p ∈ ps, p.1 < m.nodes.size + 2) → acc < m.nodes.size + 2 → conjList n lim ps acc m = .ok (r, m') →
      Inv n lim m' ∧ Extends m.nodes m'.nodes ∧ r < m'.nodes.size + 2
  | [], acc, m, r, m', hinv, _, hacc, h => by
      simp only [conjList] at h; cases h; exact ⟨hinv, Extends.refl _, hacc⟩
  | p :: ps, acc, m, r, m', hinv, hps, hacc, h => by
      simp only [conjList] at h
      split at h
      · cases h
      rename_i acc' m1 h1
      obtain ⟨i1, e1, _, _, r1, _, _⟩ := apply_spec _ _ _ _ _ _ _ hinv hacc (hps p (by simp)) h1
      obtain ⟨i2, e2, r2⟩ := conjList_inv ps acc' m1 r m' i1
        (fun q hq => by have := hps q (by simp [hq]); have := e1.1; omega) r1 h
      exact ⟨i2, e1.trans e2, r2⟩

theorem pick_bound {n : Nat} {prs : List (Nat × BForm n)} {N : Nat} (h : ∀ p ∈ prs, p.1 < N) (hN : 1 < N)
    (J : List Nat) : ∀ p ∈ pick prs J, p.1 < N := by
  intro q hq
  simp only [pick, List.mem_map] at hq
  obtain ⟨j, _, rfl⟩ := hq
  rw [List.getD_eq_getElem?_getD]
  cases hj : prs[j]? with
  | none => simp; omega
  | some q => simp; exact h q (List.mem_of_getElem? hj)

def shrinkBody : List S :=
  [S.assign [Tgt.name "remaining"]
     (E.comp (E.var "j") "j" (E.var "core") (some (E.bin BinOp.ne (E.var "j") (E.var "i")))),
   S.ifte (E.bin BinOp.eq (E.mcall (E.var "manager") "conjunction"
       [E.comp (E.sub (E.var "premises") (E.var "j")) "j" (E.var "remaining") none]) (E.lit (V.int 0)))
     [S.assign [Tgt.name "core"] (E.var "remaining")] []]

def ShrinkOut (names : List String) (lim : Limits) (D : Addrs) (h : Heap) (env : Env) :
    Except (LimitReached × Mgr) (List Nat × Mgr) → Out Flow → Prop
  | .ok (core', m'), o => ∃ env' h' C', o = .ok (.normal env') h' ∧ env'.get "core" = some (.ref C') ∧
      hget h' C' = some (.list (core'.map iv)) ∧ ¬ D.mut C' ∧
      (∀ y, y ≠ "core" → y ≠ "i" → y ≠ "remaining" → env'.get y = env.get y) ∧
      MRel names lim D h' m' ∧ Frame D.base h h'
  | .error (e, m'), o => ∃ env' h' a, o = .ok (.raise (.obj (.ref a)) env') h' ∧
      hget h' a = some (.inst "ResourceLimit" [("args", .tup [.str e.name])]) ∧
      MRel names lim D h' m' ∧ Frame D.base h h'

theorem ShrinkOut_lift {names : List String} {lim : Limits} {D : Addrs} {h H : Heap} {env env1 : Env}
    {r : Except (LimitReached × Mgr) (List Nat × Mgr)} {o : Out Flow} (FF : Frame D.base h H)
    (he : ∀ y, y ≠ "core" → y ≠ "i" → y ≠ "remaining" → env1.get y = env.get y)
    (hx : ShrinkOut names lim D H env1 r o) : ShrinkOut names lim D h env r o := by
  rcases r with ⟨e, m'⟩ | ⟨c', m'⟩
  · obtain ⟨env', h', a', eo, ha', R', F'⟩ := hx
    exact ⟨env', h', a', eo, ha', R', FF.trans F'⟩
  · obtain ⟨env', h', C', eo, hc, hC, hm, hy, R', F'⟩ := hx
    exact ⟨env', h', C', eo, hc, hC, hm, fun y h1 h2 h3 => by rw [hy y h1 h2 h3, he y h1 h2 h3], R',
      FF.trans F'⟩

theorem shrink_loop (ext : Ext) {names : List String} {lim : Limits} {D : Addrs}
    (P I : Nat) (prs : List (Nat × BForm names.length)) (xs : List V) :
    ∀ (is : List Nat) (k j : Nat) (env : Env) (h : Heap) (m : Mgr) (core : List Nat) (C : Nat),
      applyFuel lim + prs.length + is.length + 4 ≤ k →
      hget h I = some (.list xs) → ¬ D.base.mut I → xs.drop j = is.map iv →
      env.get "premises" = some (.ref P) → env.get "manager" = some (.ref D.self) →
      env.get "core" = some (.ref C) → hget h C = some (.list (core.map iv)) → ¬ D.mut C →
      hget h P = some (.list (prs.map (fun p => iv p.1))) → ¬ D.base.mut P →
      (∀ c ∈ core, c < prs.length) → core.length ≤ prs.length →
      MRel names lim D h m → Inv names.length lim m → (∀ p ∈ prs, p.1 < m.nodes.size + 2) →
      ShrinkOut names lim D h env (shrink names.length lim prs core is m)
        ((interp (pyCtx ext) (k + 1)).forLoop env h (.name "i") (.ref I) j shrinkBody)
  | [], k, j, env, h, m, core, C, hk, hI, hmI, hxs, hp, hmg, hc, hC, hmC, hP, hmP, hcl, hcn, hR, hinv,
      hprs => by
      rw [interp_succ_forLoop]
      have hj : xs[j]? = none := by
        have := congrArg List.length hxs; simp at this
        exact List.getElem?_eq_none (by omega)
      simp only [forIter, elemAt, hI, hj, shrink]
      exact ⟨env, h, C, rfl, hc, hC, hmC, fun _ _ _ _ => rfl, hR, Frame.refl _ _⟩
  | i0 :: is, k, j, env, h, m, core, C, hk, hI, hmI, hxs, hp, hmg, hc, hC, hmC, hP, hmP, hcl, hcn, hR,
      hinv, hprs => by
      obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by simp at hk; omega⟩
      rw [interp_succ_forLoop]
      have hj : xs[j]? = some (iv i0) := by
        have := congrArg (fun l => l[0]?) hxs; simpa using this
      have hselfR := hR.self
      simp only [diagramFields, iv] at hselfR
      simp only [forIter, elemAt, hI, hj, bindE, assignT, shrink]
      -- `remaining = [j for j in core if j != i]`
      have hc1 := comp_filter_ne ext (k' + 1) (env.set "i" (iv i0)) h C core i0 (by simp [hc]) (by simp)
        hC (by simp at hk; omega)
      obtain ⟨rem, hrem⟩ : ∃ rem, rem = core.filter (· != i0) := ⟨_, rfl⟩
      rw [← hrem] at hc1 ⊢
      have hreml : rem.length ≤ core.length := by rw [hrem]; exact List.length_filter_le _ _
      have hremb : ∀ r ∈ rem, r < prs.length := fun r hr => by
        rw [hrem] at hr; exact hcl r (List.mem_filter.1 hr).1
      have hR1 : MRel names lim D (h ++ [Obj.list (rem.map iv)]) m := hR.append _
      -- `[premises[j] for j in remaining]`
      have hc2 := comp_pick ext (k' + 1) ((env.set "i" (iv i0)).set "remaining" (.ref h.length))
        (h ++ [Obj.list (rem.map iv)]) P h.length prs rem (by simp [hp]) (by simp)
        (by rw [hget_append_lt _ (hget_lt hP)]; exact hP) (by simp [hget]) hremb (by simp at hk; omega)
      have hR2 := hR1.append (Obj.list ((pick prs rem).map (fun p => iv p.1)))
      have hL2 : hget (h ++ [Obj.list (rem.map iv)] ++ [Obj.list ((pick prs rem).map (fun p => iv p.1))])
          (h ++ [Obj.list (rem.map iv)]).length = some (.list ((pick prs rem).map (fun p => iv p.1))) := by
        simp [hget]
      have hmL := fresh_not_mut hR1 (Nat.le_refl _)
      have hmLb : ¬ D.base.mut (h ++ [Obj.list (rem.map iv)]).length := fun e => hmL (Addrs.base_mut e)
      have hpsb : ∀ p ∈ pick prs rem, p.1 < m.nodes.size + 2 := pick_bound hprs (by omega) rem
      have hpsl : (pick prs rem).length = rem.length := by simp [pick]
      have scj := SimOut.both
        (conjunction_sim ext (pick prs rem) k' (by simp at hk; omega) _ m _ hL2 hmL hR2 hinv hpsb)
        (conjunction_sim ext (D := D.base) (pick prs rem) k' (by simp at hk; omega) _ m _ hL2 hmLb hR2.base
          hinv hpsb)
      have hselfR2 : hget (h ++ [Obj.list (rem.map iv)] ++ [Obj.list ((pick prs rem).map (fun p => iv p.1))])
          D.self = hget h D.self := by
        rw [hget_append_lt _ (by simp; have := hR.addrs_lt.1; omega), hget_append_lt _ hR.addrs_lt.1]
      rw [hselfR] at hselfR2
      simp only [shrinkBody]
      rw [execB_cons']
      simp only [execS, bindS, hc1, assignAll, assignT, bindE, Out.bind, seqF_normal]
      have hcl2 : classHasMethod pyProg "Diagram" "conjunction" = true := by decide
      cases hcj : conjList names.length lim (pick prs rem) 1 m with
      | error q =>
        obtain ⟨e, m1⟩ := q
        rw [hcj] at scj
        obtain ⟨H3, a3, e3, ha3, R3, F3⟩ := scj
        simp only [List.append_assoc, List.singleton_append, List.length_append, List.length_singleton]
          at e3 hselfR2
        rw [execB_cons']
        simp [execS, bindS, evalE, evalL, Env.get_set, hmg, ↓hc2, Out.bind, hselfR2, hcl2, e3]
        simp only [loopK]
        exact ⟨_, H3, a3, rfl, ha3, R3, ((Frame.append _ _ _).trans (Frame.append _ _ _)).trans F3⟩
      | ok q =>
        obtain ⟨c, m1⟩ := q
        rw [hcj] at scj
        obtain ⟨H3, e3, R3, F3⟩ := scj
        obtain ⟨i1, ex1, _⟩ := conjList_inv _ 1 m c m1 hinv hpsb (by omega) hcj
        have FF : Frame D.base h H3 := ((Frame.append _ _ _).trans (Frame.append _ _ _)).trans F3
        have hmh' : ¬ D.mut h.length := fresh_not_mut hR (Nat.le_refl _)
        have hmh : ¬ D.base.mut h.length := fun e => hmh' (Addrs.base_mut e)
        have hpres : ∀ a, a < h.length → ¬ D.base.mut a → hget H3 a = hget h a := fun a ha hm => FF.2 a ha hm
        have hremH : hget H3 h.length = some (.list (rem.map iv)) := by
          rw [F3.2 _ (by simp) hmh]; simp [hget]
        have hIH : hget H3 I = some (.list xs) := by rw [hpres I (hget_lt hI) hmI]; exact hI
        have hPH : hget H3 P = some (.list (prs.map (fun p => iv p.1))) := by
          rw [hpres P (hget_lt hP) hmP]; exact hP
        have hCH : hget H3 C = some (.list (core.map iv)) := by rw [hpres C (hget_lt hC) (fun e => hmC (Addrs.base_mut e))]; exact hC
        have hprs1 : ∀ p ∈ prs, p.1 < m1.nodes.size + 2 := fun p hp' => by
          have := hprs p hp'; have := ex1.1; omega
        have hxs' : xs.drop (j + 1) = is.map iv := by rw [← List.drop_drop, hxs]; simp
        simp only [List.append_assoc, List.singleton_append, List.length_append, List.length_singleton]
          at e3 hselfR2
        rw [execB_cons']
        simp [execS, bindS, evalE, evalL, Env.get_set, hmg, ↓hc2, Out.bind, hselfR2, hcl2, e3]
        by_cases hz : c = 0
        · subst hz
          simp only [if_true]
          simp [binOp, eqD, iv, eqPy_int, truthy, execB, execS, evalE, bindS, bindE, assignAll, assignT,
            Env.get_set, Out.bind, loopK, seqF]
          have ih := shrink_loop ext P I prs xs is k' (j + 1)
            (((env.set "i" (iv i0)).set "remaining" (V.ref h.length)).set "core" (V.ref h.length)) H3 m1 rem
            h.length (by simp at hk; omega) hIH hmI hxs' (by simp [hp]) (by simp [hmg]) (by simp) hremH hmh'
            hPH hmP hremb (by omega) R3 i1 hprs1
          simp only [shrinkBody] at ih
          exact ShrinkOut_lift FF (fun y h1 h2 h3 => by simp [Ne.symm h1, Ne.symm h2, Ne.symm h3]) ih
        · have hz' : ¬ ((c : Int) = 0) := by omega
          simp [binOp, eqD, iv, eqPy_int, truthy, execB, execS, evalE, bindS, bindE, assignAll, assignT,
            Env.get_set, Out.bind, loopK, seqF, hz, hz']
          have ih := shrink_loop ext P I prs xs is k' (j + 1)
            ((env.set "i" (iv i0)).set "remaining" (V.ref h.length)) H3 m1 core
            C (by simp at hk; omega) hIH hmI hxs' (by simp [hp]) (by simp [hmg]) (by simp [hc]) hCH hmC
            hPH hmP hcl hcn R3 i1 hprs1
          simp only [shrinkBody] at ih
          exact ShrinkOut_lift FF (fun y h1 h2 h3 => by simp [Ne.symm h1, Ne.symm h2, Ne.symm h3]) ih

end PCSCR.Py
