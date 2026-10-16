import PCSConditionalRuntime.JsComp
import PCSConditionalRuntime.PyShrink

/-!
# `checkConditional`: deletion-based conflict shrinking refines `PCSDD.shrink`

```
let core=premises.map((_,i)=>i);
for(const i of [...core]){const remaining=core.filter(j=>j!==i);
  if(m.conjunction(remaining.map(j=>premises[j]))===0)core=remaining;}
```

(The lowering renames the shadowing callback/loop variables to `i#2`, `j#2`.)
-/

namespace PCSCR.Js

open PCSCR PCSDD PCSOmega PCSCR.Py

theorem jfresh_not_mut {names : List String} {lim : Limits} {D : Addrs} {h : Heap} {m : Mgr}
    (hR : JMRel names lim D h m) {a : Nat} (ha : h.length ≤ a) : ¬ D.mut a := by
  have hl := hR.addrs_lt
  intro hm
  rcases hm with e | e | e | e | e
  · omega
  · omega
  · omega
  · omega
  · have := hR.own_lt a e; omega

theorem eqJs_int (a b : Int) : eqJs (.int a) (.int b) = decide (a = b) := by
  simp only [eqJs]
  by_cases hab : a = b <;> simp [hab]

/-- `premises.map((_, i) => i)`. -/
theorem jcomp_indices (ext : Ext) (k : Nat) (env : Env) (h : Heap) (P : Nat) (ps : List V)
    (hprem : env.get "premises" = some (.ref P)) (hP : hget h P = some (.list ps)) (hk : ps.length + 1 ≤ k) :
    evalE (jsCtx ext) (interp (jsCtx ext) k) env h
        (E.comp (E.var "i") "i" (E.call "%indices" [E.var "premises"]) none) =
      .ok (.ref h.length) (h ++ [.list ((List.range ps.length).map iv)]) := by
  have hev : evalE (jsCtx ext) (interp (jsCtx ext) k) env h (E.call "%indices" [E.var "premises"]) =
      .ok (.tup ((List.range ps.length).map iv)) h := by
    have hlc : lookupClass jsProg "%indices" = none := by rfl
    simp [evalE, evalL, hprem, Out.bind, builtin, builtinJs, elems, hP, iv, hlc]
  have e := jcomp_eval ext k env h "i" (E.call "%indices" [E.var "premises"]) (E.var "i") none
    (.tup ((List.range ps.length).map iv)) ((List.range ps.length).map iv) id (fun _ => true) 0 hev
    (IterOK.tup _ _) (by simpa using hk) (fun y _ k' _ env' H hx _ _ => by simp [evalE, hx]) (fun _ _ => rfl)
  rw [e, List.filter_eq_self.2 (fun _ _ => rfl), List.map_id]

/-- `core.filter(j => j !== i)`. -/
theorem jcomp_filter_ne (ext : Ext) (k : Nat) (env : Env) (h : Heap) (C : Nat) (cs : List Nat) (i0 : Nat)
    (hcore : env.get "core" = some (.ref C)) (hi : env.get "i#2" = some (iv i0))
    (hC : hget h C = some (.list (cs.map iv))) (hk : cs.length + 1 ≤ k) :
    evalE (jsCtx ext) (interp (jsCtx ext) k) env h
        (E.comp (E.var "j") "j" (E.var "core") (some (E.bin BinOp.ne (E.var "j") (E.var "i#2")))) =
      .ok (.ref h.length) (h ++ [.list ((cs.filter (· != i0)).map iv)]) := by
  have e := jcomp_eval ext k env h "j" (E.var "core") (E.var "j")
    (some (E.bin BinOp.ne (E.var "j") (E.var "i#2"))) (.ref C) (cs.map iv) id
    (fun v => !(decide (v = iv i0))) 0 (by simp [evalE, hcore]) (IterOK.ref hC) (by simpa using hk)
    (fun y _ k' _ env' H hx _ _ => by simp [evalE, hx])
    (fun y hy k' _ env' H hx hz _ => by
      simp only [List.mem_map] at hy
      obtain ⟨c, _, rfl⟩ := hy
      have hi' : env'.get "i#2" = some (iv i0) := by rw [hz "i#2" (by decide)]; exact hi
      simp [evalE, hx, hi', binOp, eqD, iv, eqJs_int])
  rw [e, List.map_id, filter_map_iv]

/-- Index lookup into the premise array (out-of-range indices are never used). -/
def jpremG (prs : List (Nat × BForm n)) : V → V
  | .int z => (prs.map (fun p => iv p.1)).getD z.toNat .undef
  | _ => .undef

theorem jpremG_map (prs : List (Nat × BForm n)) :
    ∀ (rs : List Nat), (∀ r ∈ rs, r < prs.length) →
      (rs.map iv).map (jpremG prs) = (pick prs rs).map (fun p => iv p.1)
  | [], _ => rfl
  | r :: rs, hr => by
      have h1 := hr r (by simp)
      have ih := jpremG_map prs rs (fun x hx => hr x (by simp [hx]))
      simp only [List.map_cons, pick] at ih ⊢
      rw [ih]
      simp [jpremG, iv, List.getD_eq_getElem?_getD, h1]

theorem jsubOp_idx {h : Heap} {P : Nat} {l : List V} {j : Nat} (hP : hget h P = some (.list l))
    (hj : j < l.length) : subOp .js h (.ref P) (.int j) = .ok (l.getD j .undef) h := by
  have h2 : (j : Int) < (l.length : Int) := by omega
  simp [subOp, hP, h2]

/-- `remaining.map(j => premises[j])` (any element/iteration variable names). -/
theorem jcomp_pick (ext : Ext) (k : Nat) (env : Env) (h : Heap) (x rv : String) (P R : Nat)
    (prs : List (Nat × BForm n)) (rs : List Nat) (hxp : x ≠ "premises")
    (hprem : env.get "premises" = some (.ref P)) (hrem : env.get rv = some (.ref R))
    (hP : hget h P = some (.list (prs.map (fun p => iv p.1)))) (hR : hget h R = some (.list (rs.map iv)))
    (hrs : ∀ r ∈ rs, r < prs.length) (hk : rs.length + 1 ≤ k) :
    evalE (jsCtx ext) (interp (jsCtx ext) k) env h
        (E.comp (E.sub (E.var "premises") (E.var x)) x (E.var rv) none) =
      .ok (.ref h.length) (h ++ [.list ((pick prs rs).map (fun p => iv p.1))]) := by
  have e := jcomp_eval ext k env h x (E.var rv) (E.sub (E.var "premises") (E.var x)) none (.ref R)
    (rs.map iv) (jpremG prs) (fun _ => true) 0 (by simp [evalE, hrem]) (IterOK.ref hR) (by simpa using hk)
    (fun y hy k' _ env' H hx hz hag => by
      simp only [List.mem_map] at hy
      obtain ⟨r, hr, rfl⟩ := hy
      have hp' : env'.get "premises" = some (.ref P) := by rw [hz "premises" (Ne.symm hxp)]; exact hprem
      have hPH : hget H P = some (.list (prs.map (fun p => iv p.1))) := by
        rw [hag.2 P (hget_lt hP)]; exact hP
      have := jsubOp_idx (h := H) (j := r) hPH (by simp; exact hrs r hr)
      simp only [iv] at this
      simp [evalE, hx, hp', Out.bind, iv, this, jpremG])
    (fun _ _ => rfl)
  rw [e, List.filter_eq_self.2 (fun _ _ => rfl), jpremG_map prs rs hrs]

def jshrinkBody : List S :=
  [S.assign [Tgt.name "remaining"]
     (E.comp (E.var "j") "j" (E.var "core") (some (E.bin BinOp.ne (E.var "j") (E.var "i#2")))),
   S.ifte (E.bin BinOp.eq (E.mcall (E.var "m") "conjunction"
       [E.comp (E.sub (E.var "premises") (E.var "j#2")) "j#2" (E.var "remaining") none]) (E.lit (V.int 0)))
     [S.assign [Tgt.name "core"] (E.var "remaining")] []]

def JShrinkOut (names : List String) (lim : Limits) (D : Addrs) (h : Heap) (env : Env) :
    Except (LimitReached × Mgr) (List Nat × Mgr) → Out Flow → Prop
  | .ok (core', m'), o => ∃ env' h' C', o = .ok (.normal env') h' ∧ env'.get "core" = some (.ref C') ∧
      hget h' C' = some (.list (core'.map iv)) ∧ ¬ D.mut C' ∧
      (∀ y, y ≠ "core" → y ≠ "i#2" → y ≠ "remaining" → env'.get y = env.get y) ∧
      JMRel names lim D h' m' ∧ Frame D.base h h'
  | .error (e, m'), o => ∃ env' h' a, o = .ok (.raise (.obj (.ref a)) env') h' ∧
      hget h' a = some (.inst "ResourceLimit" [("message", .str e.name)]) ∧
      JMRel names lim D h' m' ∧ Frame D.base h h'

theorem JShrinkOut_lift {names : List String} {lim : Limits} {D : Addrs} {h H : Heap} {env env1 : Env}
    {r : Except (LimitReached × Mgr) (List Nat × Mgr)} {o : Out Flow} (FF : Frame D.base h H)
    (he : ∀ y, y ≠ "core" → y ≠ "i#2" → y ≠ "remaining" → env1.get y = env.get y)
    (hx : JShrinkOut names lim D H env1 r o) : JShrinkOut names lim D h env r o := by
  rcases r with ⟨e, m'⟩ | ⟨c', m'⟩
  · obtain ⟨env', h', a', eo, ha', R', F'⟩ := hx
    exact ⟨env', h', a', eo, ha', R', FF.trans F'⟩
  · obtain ⟨env', h', C', eo, hc, hC, hm, hy, R', F'⟩ := hx
    exact ⟨env', h', C', eo, hc, hC, hm, fun y h1 h2 h3 => by rw [hy y h1 h2 h3, he y h1 h2 h3], R',
      FF.trans F'⟩

theorem jshrink_loop (ext : Ext) {names : List String} {lim : Limits} {D : Addrs}
    (P I : Nat) (prs : List (Nat × BForm names.length)) (xs : List V) :
    ∀ (is : List Nat) (k j : Nat) (env : Env) (h : Heap) (m : Mgr) (core : List Nat) (C : Nat),
      applyFuel lim + prs.length + is.length + 4 ≤ k →
      hget h I = some (.list xs) → ¬ D.base.mut I → xs.drop j = is.map iv →
      env.get "premises" = some (.ref P) → env.get "m" = some (.ref D.self) →
      env.get "core" = some (.ref C) → hget h C = some (.list (core.map iv)) → ¬ D.mut C →
      hget h P = some (.list (prs.map (fun p => iv p.1))) → ¬ D.base.mut P →
      (∀ c ∈ core, c < prs.length) → core.length ≤ prs.length →
      JMRel names lim D h m → Inv names.length lim m → (∀ p ∈ prs, p.1 < m.nodes.size + 2) →
      JShrinkOut names lim D h env (shrink names.length lim prs core is m)
        ((interp (jsCtx ext) (k + 1)).forLoop env h (.name "i#2") (.ref I) j jshrinkBody)
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
      simp only [jdiagramFields, iv] at hselfR
      simp only [forIter, elemAt, hI, hj, bindE, assignT, shrink]
      have hc1 := jcomp_filter_ne ext (k' + 1) (env.set "i#2" (iv i0)) h C core i0 (by simp [hc]) (by simp)
        hC (by simp at hk; omega)
      obtain ⟨rem, hrem⟩ : ∃ rem, rem = core.filter (· != i0) := ⟨_, rfl⟩
      rw [← hrem] at hc1 ⊢
      have hreml : rem.length ≤ core.length := by rw [hrem]; exact List.length_filter_le _ _
      have hremb : ∀ r ∈ rem, r < prs.length := fun r hr => by
        rw [hrem] at hr; exact hcl r (List.mem_filter.1 hr).1
      have hR1 : JMRel names lim D (h ++ [Obj.list (rem.map iv)]) m := hR.append _
      have hc2 := jcomp_pick ext (k' + 1) ((env.set "i#2" (iv i0)).set "remaining" (.ref h.length))
        (h ++ [Obj.list (rem.map iv)]) "j#2" "remaining" P h.length prs rem (by decide) (by simp [hp]) (by simp)
        (by rw [hget_append_lt _ (hget_lt hP)]; exact hP) (by simp [hget]) hremb (by simp at hk; omega)
      have hR2 := hR1.append (Obj.list ((pick prs rem).map (fun p => iv p.1)))
      have hL2 : hget (h ++ [Obj.list (rem.map iv)] ++ [Obj.list ((pick prs rem).map (fun p => iv p.1))])
          (h ++ [Obj.list (rem.map iv)]).length = some (.list ((pick prs rem).map (fun p => iv p.1))) := by
        simp [hget]
      have hmL := jfresh_not_mut hR1 (Nat.le_refl _)
      have hmLb : ¬ D.base.mut (h ++ [Obj.list (rem.map iv)]).length := fun e => hmL (Addrs.base_mut e)
      have hpsb : ∀ p ∈ pick prs rem, p.1 < m.nodes.size + 2 := pick_bound hprs (by omega) rem
      have hpsl : (pick prs rem).length = rem.length := by simp [pick]
      have scj := JSimOut.both
        (jconjunction_sim ext (pick prs rem) k' (by simp at hk; omega) _ m _ hL2 hmL hR2 hinv hpsb)
        (jconjunction_sim ext (D := D.base) (pick prs rem) k' (by simp at hk; omega) _ m _ hL2 hmLb hR2.base
          hinv hpsb)
      have hselfR2 : hget (h ++ [Obj.list (rem.map iv)] ++ [Obj.list ((pick prs rem).map (fun p => iv p.1))])
          D.self = hget h D.self := by
        rw [hget_append_lt _ (by simp; have := hR.addrs_lt.1; omega), hget_append_lt _ hR.addrs_lt.1]
      rw [hselfR] at hselfR2
      simp only [jshrinkBody]
      rw [execB_cons']
      simp only [execS, bindS, hc1, assignAll, assignT, bindE, Out.bind, seqF_normal]
      have hcl2 : classHasMethod jsProg "Diagram" "conjunction" = true := by decide
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
        have hmh' : ¬ D.mut h.length := jfresh_not_mut hR (Nat.le_refl _)
        have hmh : ¬ D.base.mut h.length := fun e => hmh' (Addrs.base_mut e)
        have hpres : ∀ a, a < h.length → ¬ D.base.mut a → hget H3 a = hget h a := fun a ha hm => FF.2 a ha hm
        have hremH : hget H3 h.length = some (.list (rem.map iv)) := by
          rw [F3.2 _ (by simp) hmh]; simp [hget]
        have hIH : hget H3 I = some (.list xs) := by rw [hpres I (hget_lt hI) hmI]; exact hI
        have hPH : hget H3 P = some (.list (prs.map (fun p => iv p.1))) := by
          rw [hpres P (hget_lt hP) hmP]; exact hP
        have hCH : hget H3 C = some (.list (core.map iv)) := by
          rw [hpres C (hget_lt hC) (fun e => hmC (Addrs.base_mut e))]; exact hC
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
          simp [binOp, eqD, iv, eqJs_int, truthy, execB, execS, evalE, bindS, bindE, assignAll, assignT,
            Env.get_set, Out.bind, loopK, seqF]
          have ih := jshrink_loop ext P I prs xs is k' (j + 1)
            (((env.set "i#2" (iv i0)).set "remaining" (V.ref h.length)).set "core" (V.ref h.length)) H3 m1 rem
            h.length (by simp at hk; omega) hIH hmI hxs' (by simp [hp]) (by simp [hmg]) (by simp) hremH hmh'
            hPH hmP hremb (by omega) R3 i1 hprs1
          simp only [jshrinkBody] at ih
          exact JShrinkOut_lift FF (fun y h1 h2 h3 => by simp [Ne.symm h1, Ne.symm h2, Ne.symm h3]) ih
        · have hz' : ¬ ((c : Int) = 0) := by omega
          simp [binOp, eqD, iv, eqJs_int, truthy, execB, execS, evalE, bindS, bindE, assignAll, assignT,
            Env.get_set, Out.bind, loopK, seqF, hz, hz']
          have ih := jshrink_loop ext P I prs xs is k' (j + 1)
            ((env.set "i#2" (iv i0)).set "remaining" (V.ref h.length)) H3 m1 core
            C (by simp at hk; omega) hIH hmI hxs' (by simp [hp]) (by simp [hmg]) (by simp [hc]) hCH hmC
            hPH hmP hcl hcn R3 i1 hprs1
          simp only [jshrinkBody] at ih
          exact JShrinkOut_lift FF (fun y h1 h2 h3 => by simp [Ne.symm h1, Ne.symm h2, Ne.symm h3]) ih

end PCSCR.Js
