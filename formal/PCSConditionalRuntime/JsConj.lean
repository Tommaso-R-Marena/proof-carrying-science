import PCSConditionalRuntime.JsCompile
import PCSConditionalRuntime.PyConj

/-!
# JavaScript `Diagram.conjunction` refines `PCSDD.conjList`

`for(const n of roots) r = this.apply('and', r, n)` iterates the live array by index.
-/

namespace PCSCR.Js

open PCSCR PCSDD PCSOmega PCSCR.Py

/-- `jsstep` for an abstract local store: names are resolved with `Env.get_set`. -/
macro "jsstepA" "[" ls:Lean.Parser.Tactic.simpLemma,* "]" : tactic => `(tactic| (
  rw [execB_cons']
  conv in execS _ _ _ _ _ => simp [execS, evalE, evalL, iv, binOp, eqD, eqJs, num, bindS, bindE,
    truthy, execB, assignAll, assignT, assignTs, Env.get_set, attrOp, subOp, memOp,
    fieldGet, fieldSet, setAttrOp, storeOp, elems, hashable, builtin, builtinMethod, builtinJs, builtinMethodJs, jsJoin, jsElemStr, normIdx, safeNum,
    cmpOp, isBoolV, MAX_SAFE, Int.natCast_inj, hget_append, hget_hset, $ls,*]
  try simp only [seqF_normal, seqF_ret, seqF_raise]))

/-- Loop outcome of `for(const n of roots) r = this.apply('and', r, n)`. -/
def JSimLoop (names : List String) (lim : Limits) (D : Addrs) (h : Heap) (env : Env) :
    Except (LimitReached × Mgr) (Nat × Mgr) → Out Flow → Prop
  | .ok (r, m'), o => ∃ env' h', o = .ok (.normal env') h' ∧ env'.get "r" = some (iv r) ∧
      (∀ y, y ≠ "r" → y ≠ "n" → env'.get y = env.get y) ∧ JMRel names lim D h' m' ∧ Frame D h h'
  | .error (e, m'), o => ∃ env' h' a, o = .ok (.raise (.obj (.ref a)) env') h' ∧
      hget h' a = some (.inst "ResourceLimit" [("message", .str e.name)]) ∧
      JMRel names lim D h' m' ∧ Frame D h h'

def jconjBody : List S :=
  [S.assign [Tgt.name "r"] ((E.var "this").mcall "apply" [E.lit (V.str "and"), E.var "r", E.var "n"])]

/-- **The conjunction loop simulates `conjList`.** -/
theorem jconj_loop (ext : Ext) {names : List String} {lim : Limits} {D : Addrs} (L : Nat) (xs : List V) :
    ∀ (ps : List (Nat × BForm names.length)) (k j : Nat) (env : Env) (h : Heap) (m : Mgr) (acc : Nat),
      applyFuel lim + ps.length + 1 ≤ k →
      hget h L = some (.list xs) → ¬ D.mut L → xs.drop j = ps.map (fun p => iv p.1) →
      env.get "this" = some (.ref D.self) → env.get "r" = some (iv acc) →
      JMRel names lim D h m → Inv names.length lim m → acc < m.nodes.size + 2 →
      (∀ p ∈ ps, p.1 < m.nodes.size + 2) →
      JSimLoop names lim D h env (conjList names.length lim ps acc m)
        ((interp (jsCtx ext) (k + 1)).forLoop env h (.name "n") (.ref L) j jconjBody)
  | [], k, j, env, h, m, acc, hk, hL, hmL, hxs, hself, hres, hR, hinv, hacc, hps => by
      rw [interp_succ_forLoop]
      have hj : xs[j]? = none := by
        have := congrArg List.length hxs; simp at this
        exact List.getElem?_eq_none (by omega)
      simp only [forIter, elemAt, hL, hj, conjList]
      exact ⟨env, h, rfl, hres, fun _ _ _ => rfl, hR, Frame.refl D h⟩
  | p :: ps, k, j, env, h, m, acc, hk, hL, hmL, hxs, hself, hres, hR, hinv, hacc, hps => by
      obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by simp at hk; omega⟩
      rw [interp_succ_forLoop]
      have hj : xs[j]? = some (iv p.1) := by
        have := congrArg (fun l => l[0]?) hxs; simpa using this
      have hp := hps p (by simp)
      have hselfR := hR.self
      simp only [jdiagramFields, iv] at hselfR
      have s1 := japply_sim ext .and (applyFuel lim) k' (by simp at hk; omega) h m acc p.1 hR hinv hacc hp
        (by unfold applyFuel; omega)
      simp only [forIter, elemAt, hL, hj, bindE, assignT, conjList]
      cases hx1 : apply names.length lim (applyFuel lim) .and acc p.1 m with
      | error q =>
        obtain ⟨e, m1⟩ := q
        try rw [hx1] at s1
        obtain ⟨H1, a1, e1, ha1, R1, F1⟩ := s1
        simp only [iv, BOp.name] at e1
        simp only [jconjBody]
        jsstepA [hself, hres, hselfR, e1]
        exact ⟨_, H1, a1, rfl, ha1, R1, F1⟩
      | ok q =>
        obtain ⟨acc', m1⟩ := q
        try rw [hx1] at s1
        obtain ⟨H1, e1, R1, F1⟩ := s1
        simp only [iv, BOp.name] at e1
        obtain ⟨i1, ex1, _, _, r1, _, _⟩ := apply_spec _ _ _ _ _ acc' m1 hinv hacc hp hx1
        have ih := jconj_loop ext L xs ps k' (j + 1) (((env.set "n" (iv p.1)).set "r" (iv acc')))
          H1 m1 acc' (by simp at hk; omega) (by rw [F1.2 L (hget_lt hL) hmL]; exact hL) hmL
          (by rw [← List.drop_drop, hxs]; simp) (by simp [hself]) (by simp)
          R1 i1 r1 (fun q hq => by have e := ex1.1; have h1 := hps q (List.mem_cons_of_mem _ hq); omega)
        simp only [jconjBody]
        jsstepA [hself, hres, hselfR, e1]
        simp only [execB_nil_eq, loopK]
        generalize conjList names.length lim ps acc' m1 = res at ih ⊢
        rcases res with ⟨e, m'⟩ | ⟨r, m'⟩
        · obtain ⟨env', h', a', eo, ha', R', F'⟩ := ih
          exact ⟨env', h', a', eo, ha', R', F1.trans F'⟩
        · obtain ⟨env', h', eo, hr, hy, R', F'⟩ := ih
          refine ⟨env', h', eo, hr, fun y h1 h2 => ?_, R', F1.trans F'⟩
          rw [hy y h1 h2]; simp [Ne.symm h1, Ne.symm h2]

/-- **`Diagram.conjunction` simulates `conjList` from the root `1`.** -/
theorem jconjunction_sim (ext : Ext) {names : List String} {lim : Limits} {D : Addrs}
    (ps : List (Nat × BForm names.length)) (k : Nat) (hk : applyFuel lim + ps.length + 2 ≤ k)
    (h : Heap) (m : Mgr) (L : Nat) (hL : hget h L = some (.list (ps.map (fun p => iv p.1))))
    (hmL : ¬ D.mut L) (hR : JMRel names lim D h m) (hinv : Inv names.length lim m)
    (hps : ∀ p ∈ ps, p.1 < m.nodes.size + 2) :
    JSimOut names lim D h (conjList names.length lim ps 1 m)
      ((interp (jsCtx ext) (k + 1)).call "Diagram.conjunction" [.ref D.self, .ref L] h) := by
  obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by omega⟩
  rw [interp_succ_call]
  simp only [callBody, lookup_conjunction, js_Diagram_conjunction, jsCtx_prog]
  simp only [List.length, List.zip, List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append,
    List.cons_append, ne_eq, not_true, if_false]
  jsstep []
  have s := jconj_loop ext L _ ps k' 0 [("r", .int 1), ("roots", .ref L), ("this", .ref D.self)] h m 1
    (by omega) hL hmL (by simp) (by simp [Env.get]) (by simp [Env.get, iv]) hR hinv (by omega) hps
  rw [execB_cons']
  conv in execS _ _ _ _ _ => simp [execS, evalE, Env.get, bindS]
  simp only [jconjBody] at s
  generalize conjList names.length lim ps 1 m = res at s ⊢
  rcases res with ⟨e, m'⟩ | ⟨r, m'⟩
  · obtain ⟨env', h', a', eo, ha', R', F'⟩ := s
    rw [eo]
    exact ⟨h', a', by simp [finishCall, seqF], ha', R', F'⟩
  · obtain ⟨env', h', eo, hr, hy, R', F'⟩ := s
    rw [eo]
    simp only [seqF_normal]
    jsstepA [hr]
    exact ⟨h', by simp [finishCall, iv], R', F'⟩

end PCSCR.Js
