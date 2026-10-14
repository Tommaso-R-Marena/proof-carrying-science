import PCSConditionalRuntime.PyCheckPrefix

/-!
# `check`: the premise loop refines `PCSDD.premLoop`

`for formula in value['assumptions']: premises.append(manager.compile(formula));
 context = manager.apply('and', context, premises[-1]); if context == 0: break`
-/

namespace PCSCR.Py

open PCSCR PCSDD PCSOmega

/-- `pystepA` that keeps subscripts folded (they are resolved by `subOp_*` lemmas). -/
macro "pystepB" "[" ls:Lean.Parser.Tactic.simpLemma,* "]" : tactic => `(tactic| (
  rw [execB_cons']
  conv in execS _ _ _ _ _ => simp [execS, evalE, evalL, iv, binOp, eqD, eqPy, num, bindS, bindE,
    truthy, execB, assignAll, assignT, assignTs, Env.get_set, attrOp, memOp,
    fieldGet, fieldSet, setAttrOp, storeOp, elems, hashable, builtin, builtinMethod, normIdx, safeNum,
    cmpOp, Int.natCast_inj, hget_append, hget_hset, $ls,*]
  try simp only [seqF_normal, seqF_ret, seqF_raise]))

def premBody : List S :=
  [S.expr (E.mcall (E.var "premises") "append" [E.mcall (E.var "manager") "compile" [E.var "formula"]]),
   S.assign [Tgt.name "context"] (E.mcall (E.var "manager") "apply"
     [E.lit (V.str "and"), E.var "context", E.sub (E.var "premises") (E.lit (V.int (-1)))]),
   S.ifte (E.bin BinOp.eq (E.var "context") (E.lit (V.int 0))) [S.brk] []]

/-- Maximal nesting depth of a list of formulas. -/
def fdepthL {n : Nat} : List (BForm n) → Nat
  | [] => 0
  | f :: fs => max (fdepth f) (fdepthL fs)

/-- The mutable set of the check-level loops: the `Diagram` objects and one owned address. -/
def MutP (D : Addrs) (P : Nat) (a : Nat) : Prop := D.base.mut a ∨ a = P

def PremOut (names : List String) (lim : Limits) (D : Addrs) (P : Nat) (h : Heap) (env : Env) :
    Except (LimitReached × Mgr) (List (Nat × BForm names.length) × Nat × Mgr) → Out Flow → Prop
  | .ok (prs', ctx', m'), o => ∃ env' h', o = .ok (.normal env') h' ∧ env'.get "context" = some (iv ctx') ∧
      (∀ y, y ≠ "context" → y ≠ "formula" → env'.get y = env.get y) ∧
      hget h' P = some (.list (prs'.map (fun p => iv p.1))) ∧ MRel names lim D h' m' ∧ FrameS (MutP D P) h h'
  | .error (e, m'), o => ∃ env' h' a, o = .ok (.raise (.obj (.ref a)) env') h' ∧
      hget h' a = some (.inst "ResourceLimit" [("args", .tup [.str e.name])]) ∧
      MRel names lim D h' m' ∧ FrameS (MutP D P) h h'

theorem MutP_mut {D : Addrs} {P a : Nat} (hP : P ∈ D.own) (h : MutP D P a) : D.mut a := by
  rcases h with h | rfl
  · exact Addrs.base_mut h
  · exact Or.inr (Or.inr (Or.inr (Or.inr hP)))

theorem subOp_last {h : Heap} {P : Nat} {l : List V} {x : V} (hP : hget h P = some (.list (l ++ [x]))) :
    subOp .py h (.ref P) (.int (-1)) = .ok x h := by
  have e : (-1 : Int) + ((l.length : Int) + 1) = (l.length : Int) := by omega
  have h2 : (0 : Int) ≤ (l.length : Int) := by omega
  have h3 : (l.length : Int) < (l.length : Int) + 1 := by omega
  simp [subOp, hP, normIdx]
  rw [e, if_pos ⟨h2, h3⟩]
  simp

theorem subOp_idx {h : Heap} {P : Nat} {l : List V} {j : Nat} (hP : hget h P = some (.list l))
    (hj : j < l.length) : subOp .py h (.ref P) (.int j) = .ok (l.getD j .none) h := by
  have h1 : ¬ ((j : Int) < 0) := by omega
  have h2 : (j : Int) < (l.length : Int) := by omega
  simp [subOp, hP, normIdx, h1, h2]

theorem prem_loop (ext : Ext) {names : List String} {lim : Limits} {D : Addrs} (hnd : names.Nodup)
    (AS P : Nat) (xs : List V) (hP : P ∈ D.own) (p1 : P ≠ D.self) (p2 : P ≠ D.nodes) (p3 : P ≠ D.uniq)
    (p4 : P ≠ D.memo) :
    ∀ (fs : List (BForm names.length)) (vs : List V) (k j : Nat) (env : Env) (h : Heap) (m : Mgr)
      (prs : List (Nat × BForm names.length)) (ctx : Nat),
      applyFuel lim + fdepthL fs + fs.length + 2 ≤ k →
      hget h AS = some (.list xs) → ¬ D.mut AS → xs.drop j = vs → vs.length = fs.length →
      (∀ p ∈ vs.zip fs, FRel D h names p.1 p.2) →
      env.get "premises" = some (.ref P) → env.get "manager" = some (.ref D.self) →
      env.get "context" = some (iv ctx) →
      hget h P = some (.list (prs.map (fun p => iv p.1))) →
      MRel names lim D h m → Inv names.length lim m → ctx < m.nodes.size + 2 →
      (∀ p ∈ prs, p.1 < m.nodes.size + 2) →
      PremOut names lim D P h env (premLoop names.length lim fs prs ctx m)
        ((interp (pyCtx ext) (k + 1)).forLoop env h (.name "formula") (.ref AS) j premBody)
  | [], vs, k, j, env, h, m, prs, ctx, hk, hAS, hmAS, hxs, hlen, hfr, hp, hmg, hctx, hPl, hR, hinv,
      hc, hprs => by
      rw [interp_succ_forLoop]
      have hv : vs = [] := List.eq_nil_of_length_eq_zero hlen
      subst hv
      have hj : xs[j]? = none := by
        have := congrArg List.length hxs; simp at this
        exact List.getElem?_eq_none (by omega)
      simp only [forIter, elemAt, hAS, hj, premLoop]
      exact ⟨env, h, rfl, hctx, fun _ _ _ => rfl, hPl, hR, FrameS.refl _ _⟩
  | f :: fs, vs, k, j, env, h, m, prs, ctx, hk, hAS, hmAS, hxs, hlen, hfr, hp, hmg, hctx, hPl, hR, hinv,
      hc, hprs => by
      obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by simp at hk; omega⟩
      rw [interp_succ_forLoop]
      obtain ⟨v, vs', rfl⟩ : ∃ v vs', vs = v :: vs' := by
        cases vs with
        | nil => simp at hlen
        | cons v vs' => exact ⟨v, vs', rfl⟩
      have hj : xs[j]? = some v := by
        have := congrArg (fun l => l[0]?) hxs; simpa using this
      have hfv : FRel D h names v f := hfr (v, f) (by simp)
      have hselfR := hR.self
      simp only [diagramFields, iv] at hselfR
      have hk1 : applyFuel lim + fdepth f + 1 ≤ k' := by
        simp only [fdepthL, List.length_cons] at hk; omega
      have s2 := SimOut.both ((compile_sim ext hnd f) k' hk1 h m v hR hinv hfv)
        ((compile_sim ext (D := D.base) hnd f) k' hk1 h m v hR.base hinv hfv.base)
      have hPlt := hget_lt hPl
      have hPb : ¬ D.base.mut P := by
        simp only [Addrs.mut, Addrs.base_self, Addrs.base_nodes, Addrs.base_uniq, Addrs.base_memo,
          Addrs.base_own, List.not_mem_nil, or_false]
        omega
      simp only [forIter, elemAt, hAS, hj, bindE, assignT, premLoop]
      cases hc1 : compile names.length lim f m with
      | error q =>
        obtain ⟨e, m1⟩ := q
        rw [hc1] at s2
        obtain ⟨H1, a1, e1, ha1, R1, F1⟩ := s2
        simp only [premBody]
        pystepA [hp, hmg, hselfR, e1]
        exact ⟨_, H1, a1, rfl, ha1, R1, (FrameS.of_frame F1).mono (fun x hx => Or.inl hx)⟩
      | ok q =>
        obtain ⟨p, m1⟩ := q
        rw [hc1] at s2
        obtain ⟨H1, e1, R1, F1⟩ := s2
        obtain ⟨i1, ex1, _, r1, _⟩ := compile_spec f m p m1 hinv hc1
        have hP1 : hget H1 P = some (.list (prs.map (fun p => iv p.1))) := by
          rw [F1.2 P hPlt hPb]; exact hPl
        obtain ⟨R2, F2⟩ := R1.hsetOwn hP p1 p2 p3 p4 (.list (prs.map (fun p => iv p.1) ++ [iv p]))
        have hc' : ctx < m1.nodes.size + 2 := by have := ex1.1; omega
        have hfu : lim.operations < applyFuel lim + m1.ops := by unfold applyFuel; omega
        have hfk : applyFuel lim ≤ k' := by simp only [fdepthL, List.length_cons] at hk; omega
        have sa := SimOut.both (apply_sim ext .and (applyFuel lim) k' hfk _ m1 ctx p R2 i1 hc' r1 hfu)
          (apply_sim ext (D := D.base) .and (applyFuel lim) k' hfk _ m1 ctx p R2.base i1 hc' r1 hfu)
        have hlast := subOp_last (h := hset H1 P (.list (prs.map (fun p => iv p.1) ++ [iv p])))
          (P := P) (l := prs.map (fun p => iv p.1)) (x := iv p) (by rw [hget_hset_same _ (by have := F1.1; omega)])
        have hselfR1 := R1.self
        simp only [diagramFields, iv] at hselfR1
        have hselfR2 := R2.self
        simp only [diagramFields, iv] at hselfR2
        cases ha1 : apply names.length lim (applyFuel lim) .and ctx p m1 with
        | error q =>
          obtain ⟨e, m2⟩ := q
          rw [ha1] at sa
          obtain ⟨H2, a2, e2, ha2, R3, F3⟩ := sa
          simp only [iv, BOp.name] at e2 hlast
          simp only [premBody]
          pystepA [hp, hmg, hselfR, e1, hP1, hselfR1, hctx, hlast, e2]
          simp only [ha1]
          pystepB [hp, hmg, hctx, hlast, e2, hselfR2]
          simp only [loopK]
          exact ⟨_, H2, a2, rfl, ha2, R3, ((FrameS.of_frame F1).mono (fun x hx => Or.inl hx)).trans
            ((FrameS.hset H1 _ (Or.inr rfl)).trans ((FrameS.of_frame F3).mono (fun x hx => Or.inl hx)))⟩
        | ok q =>
          obtain ⟨ctx', m2⟩ := q
          rw [ha1] at sa
          obtain ⟨H2, e2, R3, F3⟩ := sa
          simp only [iv, BOp.name] at e2 hlast
          obtain ⟨i2, ex2, _, _, r2, _, _⟩ := apply_spec _ _ _ _ _ ctx' m2 i1 hc' r1 ha1
          simp only [premBody]
          pystepA [hp, hmg, hselfR, e1, hP1, hselfR1, hctx, hlast, e2]
          simp only [ha1]
          pystepB [hp, hmg, hctx, hlast, e2, hselfR2]
          have hP2 : hget H2 P = some (.list ((prs ++ [(p, f)]).map (fun p => iv p.1))) := by
            rw [F3.2 P (by have := F1.1; simp; omega) hPb, hget_hset_same _ (by have := F1.1; omega)]; simp [iv]
          have FF : FrameS (MutP D P) h H2 := ((FrameS.of_frame F1).mono (fun x hx => Or.inl hx)).trans
            ((FrameS.hset H1 _ (Or.inr rfl)).trans ((FrameS.of_frame F3).mono (fun x hx => Or.inl hx)))
          by_cases hz : ctx' = 0
          · subst hz
            rw [if_pos rfl]
            pystepB []
            simp only [loopK]
            refine ⟨_, H2, rfl, by simp [iv], fun y h1 h2 => ?_, hP2, R3, FF⟩
            simp [Ne.symm h1, Ne.symm h2]
          · pystepB []
            simp only [hz, if_false, seqF_normal, loopK]
            have ih := prem_loop ext hnd AS P xs hP p1 p2 p3 p4 fs vs' k' (j + 1)
              ((env.set "formula" v).set "context" (V.int ctx')) H2 m2 (prs ++ [(p, f)]) ctx'
              (by simp only [fdepthL, List.length_cons] at hk; omega)
              (by rw [FF.2 AS (hget_lt hAS) (fun e => hmAS (MutP_mut hP e))]; exact hAS) hmAS
              (by rw [← List.drop_drop, hxs]; simp) (by simpa using hlen)
              (fun q hq => FRel.frame (FF.to_frame (fun x e => MutP_mut hP e)) _ _
                (hfr q (by simp [hq])))
              (by simp [hp]) (by simp [hmg]) (by simp [iv]) hP2 R3 i2 r2
              (fun q hq => by
                rcases List.mem_append.1 hq with hq | hq
                · have := hprs q hq; have := ex1.1; have := ex2.1; omega
                · simp at hq; subst hq; have := ex2.1; simp; omega)
            generalize premLoop names.length lim fs (prs ++ [(p, f)]) ctx' m2 = res at ih ⊢
            rcases res with ⟨e, m'⟩ | ⟨prs', c', m'⟩
            · obtain ⟨env', h', a', eo, ha', R', F'⟩ := ih
              exact ⟨env', h', a', eo, ha', R', FF.trans F'⟩
            · obtain ⟨env', h', eo, hc2, hy, hP', R', F'⟩ := ih
              refine ⟨env', h', eo, hc2, fun y h1 h2 => ?_, hP', R', FF.trans F'⟩
              rw [hy y h1 h2]; simp [Ne.symm h1, Ne.symm h2]

end PCSCR.Py
