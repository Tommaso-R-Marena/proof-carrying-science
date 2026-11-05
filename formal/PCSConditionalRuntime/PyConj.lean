import PCSConditionalRuntime.PyCompile

/-!
# Local-store lemmas, and `Diagram.conjunction` refines `PCSDD.conjList`

`Env.get_set` lets the symbolic executor work with an *abstract* local store described by the
values of the names it reads (needed for loops, whose store shape changes after the first
iteration).  `conj_loop` follows the live `for root in roots` loop element by element.
-/

namespace PCSCR

theorem Env.get_replace : ∀ (env : Env) (x : String) (v : V) (y : String),
    (env.replace x v).get y = if x = y then (if env.has x then some v else none) else env.get y
  | [], x, v, y => by simp [Env.replace, Env.get, Env.has]
  | (k, w) :: rest, x, v, y => by
      have ih := Env.get_replace rest x v y
      by_cases hkx : k = x
      · subst hkx
        by_cases hky : k = y
        · subst hky; simp [Env.replace, Env.get, Env.has]
        · simp [Env.replace, Env.get, Env.has, hky, ih]
      · by_cases hky : k = y
        · subst hky
          simp [Env.replace, Env.get, Env.has, hkx, Ne.symm hkx]
        · simp only [Env.replace, Env.get, Env.has, hkx, hky, if_false, ih]
          by_cases hxy : x = y
          · subst hxy; simp [hkx]
          · simp [hxy]

@[simp] theorem Env.get_set (env : Env) (x y : String) (v : V) :
    (env.set x v).get y = if x = y then some v else env.get y := by
  unfold Env.set
  split
  · rename_i hh; rw [Env.get_replace]; simp [hh]
  · simp [Env.get]

end PCSCR

namespace PCSCR.Py

open PCSCR PCSDD PCSOmega

/-- `pystep` for an abstract local store: names are resolved with `Env.get_set`. -/
macro "pystepA" "[" ls:Lean.Parser.Tactic.simpLemma,* "]" : tactic => `(tactic| (
  rw [execB_cons']
  conv in execS _ _ _ _ _ => simp [execS, evalE, evalL, iv, binOp, eqD, eqPy, num, bindS, bindE,
    truthy, execB, assignAll, assignT, assignTs, Env.get_set, attrOp, subOp, memOp,
    fieldGet, fieldSet, setAttrOp, storeOp, elems, hashable, builtin, builtinMethod, normIdx, safeNum,
    cmpOp, Int.natCast_inj, hget_append, hget_hset, $ls,*]
  try simp only [seqF_normal, seqF_ret, seqF_raise]))

/-- Loop outcome of `for root in roots: result = self.apply('and', result, root)`. -/
def SimLoop (names : List String) (lim : Limits) (D : Addrs) (h : Heap) (env : Env) :
    Except (LimitReached × Mgr) (Nat × Mgr) → Out Flow → Prop
  | .ok (r, m'), o => ∃ env' h', o = .ok (.normal env') h' ∧ env'.get "result" = some (iv r) ∧
      (∀ y, y ≠ "result" → y ≠ "root" → env'.get y = env.get y) ∧ MRel names lim D h' m' ∧ Frame D h h'
  | .error (e, m'), o => ∃ env' h' a, o = .ok (.raise (.obj (.ref a)) env') h' ∧
      hget h' a = some (.inst "ResourceLimit" [("args", .tup [.str e.name])]) ∧
      MRel names lim D h' m' ∧ Frame D h h'

def conjBody : List S :=
  [S.assign [Tgt.name "result"] ((E.var "self").mcall "apply" [E.lit (V.str "and"), E.var "result", E.var "root"])]

theorem interp_succ_forLoop (c : Ctx) (k : Nat) (env : Env) (h : Heap) (t : Tgt) (v : V) (j : Nat) (body : List S) :
    (interp c (k + 1)).forLoop env h t v j body = forIter c (interp c k) env h t v j body := rfl

/-- **The conjunction loop simulates `conjList`.** -/
theorem conj_loop (ext : Ext) {names : List String} {lim : Limits} {D : Addrs} (L : Nat) (xs : List V) :
    ∀ (ps : List (Nat × BForm names.length)) (k j : Nat) (env : Env) (h : Heap) (m : Mgr) (acc : Nat),
      applyFuel lim + ps.length + 1 ≤ k →
      hget h L = some (.list xs) → ¬ D.mut L → xs.drop j = ps.map (fun p => iv p.1) →
      env.get "self" = some (.ref D.self) → env.get "result" = some (iv acc) →
      MRel names lim D h m → Inv names.length lim m → acc < m.nodes.size + 2 →
      (∀ p ∈ ps, p.1 < m.nodes.size + 2) →
      SimLoop names lim D h env (conjList names.length lim ps acc m)
        ((interp (pyCtx ext) (k + 1)).forLoop env h (.name "root") (.ref L) j conjBody)
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
      simp only [diagramFields, iv] at hselfR
      have s1 := apply_sim ext .and (applyFuel lim) k' (by simp at hk; omega) h m acc p.1 hR hinv hacc hp
        (by unfold applyFuel; omega)
      simp only [forIter, elemAt, hL, hj, bindE, assignT, conjList]
      cases hx1 : apply names.length lim (applyFuel lim) .and acc p.1 m with
      | error q =>
        obtain ⟨e, m1⟩ := q
        try rw [hx1] at s1
        obtain ⟨H1, a1, e1, ha1, R1, F1⟩ := s1
        simp only [iv, BOp.name] at e1
        simp only [conjBody]
        pystepA [hself, hres, hselfR, e1]
        exact ⟨_, H1, a1, rfl, ha1, R1, F1⟩
      | ok q =>
        obtain ⟨acc', m1⟩ := q
        try rw [hx1] at s1
        obtain ⟨H1, e1, R1, F1⟩ := s1
        simp only [iv, BOp.name] at e1
        obtain ⟨i1, ex1, _, _, r1, _, _⟩ := apply_spec _ _ _ _ _ acc' m1 hinv hacc hp hx1
        have ih := conj_loop ext L xs ps k' (j + 1) (((env.set "root" (iv p.1)).set "result" (iv acc')))
          H1 m1 acc' (by simp at hk; omega) (by rw [F1.2 L (hget_lt hL) hmL]; exact hL) hmL
          (by rw [← List.drop_drop, hxs]; simp) (by simp [hself]) (by simp)
          R1 i1 r1 (fun q hq => by have e := ex1.1; have h1 := hps q (List.mem_cons_of_mem _ hq); omega)
        simp only [conjBody]
        pystepA [hself, hres, hselfR, e1]
        simp only [execB_nil_eq, loopK]
        generalize conjList names.length lim ps acc' m1 = res at ih ⊢
        rcases res with ⟨e, m'⟩ | ⟨r, m'⟩
        · obtain ⟨env', h', a', eo, ha', R', F'⟩ := ih
          exact ⟨env', h', a', eo, ha', R', F1.trans F'⟩
        · obtain ⟨env', h', eo, hr, hy, R', F'⟩ := ih
          refine ⟨env', h', eo, hr, fun y h1 h2 => ?_, R', F1.trans F'⟩
          rw [hy y h1 h2]; simp [Ne.symm h1, Ne.symm h2]

theorem lookup_conjunction' (ext : Ext) :
    lookupFn (pyCtx ext).prog "Diagram.conjunction" = some py_Diagram_conjunction := by rfl

/-- **`Diagram.conjunction` simulates `conjList` from the root `1`.** -/
theorem conjunction_sim (ext : Ext) {names : List String} {lim : Limits} {D : Addrs}
    (ps : List (Nat × BForm names.length)) (k : Nat) (hk : applyFuel lim + ps.length + 2 ≤ k)
    (h : Heap) (m : Mgr) (L : Nat) (hL : hget h L = some (.list (ps.map (fun p => iv p.1))))
    (hmL : ¬ D.mut L) (hR : MRel names lim D h m) (hinv : Inv names.length lim m)
    (hps : ∀ p ∈ ps, p.1 < m.nodes.size + 2) :
    SimOut names lim D h (conjList names.length lim ps 1 m)
      ((interp (pyCtx ext) (k + 1)).call "Diagram.conjunction" [.ref D.self, .ref L] h) := by
  obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by omega⟩
  rw [interp_succ_call]
  simp only [callBody, lookup_conjunction', py_Diagram_conjunction]
  simp only [List.length, List.zip, List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append,
    List.cons_append, ne_eq, not_true, if_false]
  pystep []
  have s := conj_loop ext L _ ps k' 0 [("result", .int 1), ("roots", .ref L), ("self", .ref D.self)] h m 1
    (by omega) hL hmL (by simp) (by simp [Env.get]) (by simp [Env.get, iv]) hR hinv (by omega) hps
  rw [execB_cons']
  conv in execS _ _ _ _ _ => simp [execS, evalE, Env.get, bindS]
  simp only [conjBody] at s
  generalize conjList names.length lim ps 1 m = res at s ⊢
  rcases res with ⟨e, m'⟩ | ⟨r, m'⟩
  · obtain ⟨env', h', a', eo, ha', R', F'⟩ := s
    rw [eo]
    exact ⟨h', a', by simp [finishCall, seqF], ha', R', F'⟩
  · obtain ⟨env', h', eo, hr, hy, R', F'⟩ := s
    rw [eo]
    simp only [seqF_normal]
    pystepA [hr]
    exact ⟨h', by simp [finishCall, iv], R', F'⟩

end PCSCR.Py
