import PCSConditionalRuntime.JsCheckBase
import PCSConditionalRuntime.PyPrem

/-!
# `checkConditional`: the premise loop refines `PCSDD.premLoop`

`for(const f of t.assumptions){premises.push(m.compile(f));
  context=m.apply('and',context,premises.at(-1));if(context===0)break;}`

As for Python (`PCSCR.Py.prem_loop`), plus the safe-integer side condition of `Diagram.compile`:
the `visits` counter plus the total size of the remaining formulas stays below `2^53 - 1`.
-/

namespace PCSCR.Js

open PCSCR PCSDD PCSOmega PCSCR.Py

/-- `jsstepA` that keeps ECMAScript array methods folded (resolved by `at_last_m` & co.). -/
macro "jsstepM" "[" ls:Lean.Parser.Tactic.simpLemma,* "]" : tactic => `(tactic| (
  rw [execB_cons']
  conv in execS _ _ _ _ _ => simp [execS, evalE, evalL, iv, binOp, eqD, eqJs, num, bindS, bindE,
    truthy, execB, assignAll, assignT, assignTs, Env.get_set, attrOp, subOp, memOp,
    fieldGet, fieldSet, setAttrOp, storeOp, elems, hashable, builtin, builtinMethod, builtinJs, jsJoin, jsElemStr, normIdx, safeNum,
    cmpOp, isBoolV, MAX_SAFE, Int.natCast_inj, hget_append, hget_hset, $ls,*]
  try simp only [seqF_normal, seqF_ret, seqF_raise]))

def jpremBody : List S :=
  [S.expr (E.mcall (E.var "premises") "push" [E.mcall (E.var "m") "compile" [E.var "f"]]),
   S.assign [Tgt.name "context"] (E.mcall (E.var "m") "apply"
     [E.lit (V.str "and"), E.var "context", E.mcall (E.var "premises") "at" [E.lit (V.int (-1))]]),
   S.ifte (E.bin BinOp.eq (E.var "context") (E.lit (V.int 0))) [S.brk] []]

/-- Total size of a list of formulas. -/
def fsizeL {n : Nat} : List (BForm n) → Nat
  | [] => 0
  | f :: fs => f.size + fsizeL fs

def JPremOut (names : List String) (lim : Limits) (D : Addrs) (P : Nat) (h : Heap) (env : Env) :
    Except (LimitReached × Mgr) (List (Nat × BForm names.length) × Nat × Mgr) → Out Flow → Prop
  | .ok (prs', ctx', m'), o => ∃ env' h', o = .ok (.normal env') h' ∧ env'.get "context" = some (iv ctx') ∧
      (∀ y, y ≠ "context" → y ≠ "f" → env'.get y = env.get y) ∧
      hget h' P = some (.list (prs'.map (fun p => iv p.1))) ∧ JMRel names lim D h' m' ∧ FrameS (MutP D P) h h'
  | .error (e, m'), o => ∃ env' h' a, o = .ok (.raise (.obj (.ref a)) env') h' ∧
      hget h' a = some (.inst "ResourceLimit" [("message", .str e.name)]) ∧
      JMRel names lim D h' m' ∧ FrameS (MutP D P) h h'

theorem at_last {l : List V} {x : V} :
    (if 0 ≤ normIdx (-1) (l ++ [x]).length ∧ normIdx (-1) (l ++ [x]).length < ((l ++ [x]).length : Int)
      then (l ++ [x]).getD (normIdx (-1) (l ++ [x]).length).toNat .undef else .undef) = x := by
  have e : normIdx (-1) (l ++ [x]).length = (l.length : Int) := by
    simp [normIdx]; omega
  rw [e]
  simp only [List.length_append, List.length_singleton]
  have h1 : (0 : Int) ≤ (l.length : Int) := by omega
  have h2 : (l.length : Int) < ((l.length + 1 : Nat) : Int) := by omega
  rw [if_pos ⟨h1, h2⟩]
  simp

theorem at_last_m (c : Ctx) (hc : c.dialect = .js) {h : Heap} {P : Nat} {l : List V} {x : V}
    (hP : hget h P = some (.list (l ++ [x]))) :
    builtinMethodJs c P "at" [.int (-1)] h = .ok x h := by
  simp only [builtinMethodJs, hc, ne_eq, not_true_eq_false, if_false, hP]
  rw [at_last]

theorem jprem_loop (ext : Ext) {names : List String} {lim : Limits} {D : Addrs} (hnd : names.Nodup)
    (AS P : Nat) (xs : List V) (hP : P ∈ D.own) (p1 : P ≠ D.self) (p2 : P ≠ D.nodes) (p3 : P ≠ D.uniq)
    (p4 : P ≠ D.memo) :
    ∀ (fs : List (BForm names.length)) (vs : List V) (k j : Nat) (env : Env) (h : Heap) (m : Mgr)
      (prs : List (Nat × BForm names.length)) (ctx : Nat),
      applyFuel lim + fdepthL fs + fs.length + 2 ≤ k →
      hget h AS = some (.list xs) → ¬ D.mut AS → xs.drop j = vs → vs.length = fs.length →
      (∀ p ∈ vs.zip fs, JFRel D h names p.1 p.2) →
      env.get "premises" = some (.ref P) → env.get "m" = some (.ref D.self) →
      env.get "context" = some (iv ctx) →
      hget h P = some (.list (prs.map (fun p => iv p.1))) →
      JMRel names lim D h m → Inv names.length lim m → ctx < m.nodes.size + 2 →
      (∀ p ∈ prs, p.1 < m.nodes.size + 2) →
      m.visits + fsizeL fs ≤ 9007199254740991 →
      JPremOut names lim D P h env (premLoop names.length lim fs prs ctx m)
        ((interp (jsCtx ext) (k + 1)).forLoop env h (.name "f") (.ref AS) j jpremBody)
  | [], vs, k, j, env, h, m, prs, ctx, hk, hAS, hmAS, hxs, hlen, hfr, hp, hmg, hctx, hPl, hR, hinv,
      hc, hprs, hvis => by
      rw [interp_succ_forLoop]
      have hv : vs = [] := List.eq_nil_of_length_eq_zero hlen
      subst hv
      have hj : xs[j]? = none := by
        have := congrArg List.length hxs; simp at this
        exact List.getElem?_eq_none (by omega)
      simp only [forIter, elemAt, hAS, hj, premLoop]
      exact ⟨env, h, rfl, hctx, fun _ _ _ => rfl, hPl, hR, FrameS.refl _ _⟩
  | f :: fs, vs, k, j, env, h, m, prs, ctx, hk, hAS, hmAS, hxs, hlen, hfr, hp, hmg, hctx, hPl, hR, hinv,
      hc, hprs, hvis => by
      obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by simp at hk; omega⟩
      rw [interp_succ_forLoop]
      obtain ⟨v, vs', rfl⟩ : ∃ v vs', vs = v :: vs' := by
        cases vs with
        | nil => simp at hlen
        | cons v vs' => exact ⟨v, vs', rfl⟩
      have hj : xs[j]? = some v := by
        have := congrArg (fun l => l[0]?) hxs; simpa using this
      have hfv : JFRel D h names v f := hfr (v, f) (by simp)
      have hselfR := hR.self
      simp only [jdiagramFields, iv] at hselfR
      have hk1 : applyFuel lim + fdepth f + 1 ≤ k' := by
        simp only [fdepthL, List.length_cons] at hk; omega
      have hv1 : m.visits + f.size ≤ 9007199254740991 := by simp only [fsizeL] at hvis; omega
      have s2 := JSimOut.both ((jcompile_sim ext hnd f) k' hk1 h m v hR hinv hv1 hfv)
        ((jcompile_sim ext (D := D.base) hnd f) k' hk1 h m v hR.base hinv hv1 hfv.base)
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
        simp only [jpremBody]
        jsstepA [hp, hmg, hselfR, e1]
        exact ⟨_, H1, a1, rfl, ha1, R1, (FrameS.of_frame F1).mono (fun x hx => Or.inl hx)⟩
      | ok q =>
        obtain ⟨p, m1⟩ := q
        rw [hc1] at s2
        obtain ⟨H1, e1, R1, F1⟩ := s2
        obtain ⟨i1, ex1, _, r1, _⟩ := compile_spec f m p m1 hinv hc1
        have hvis1 := compile_visits f m p m1 hc1
        have hP1 : hget H1 P = some (.list (prs.map (fun p => iv p.1))) := by
          rw [F1.2 P hPlt hPb]; exact hPl
        obtain ⟨R2, F2⟩ := R1.hsetOwn hP p1 p2 p3 p4 (.list (prs.map (fun p => iv p.1) ++ [iv p]))
        have hc' : ctx < m1.nodes.size + 2 := by have := ex1.1; omega
        have hfu : lim.operations < applyFuel lim + m1.ops := by unfold applyFuel; omega
        have hfk : applyFuel lim ≤ k' := by simp only [fdepthL, List.length_cons] at hk; omega
        have sa := JSimOut.both (japply_sim ext .and (applyFuel lim) k' hfk _ m1 ctx p R2 i1 hc' r1 hfu)
          (japply_sim ext (D := D.base) .and (applyFuel lim) k' hfk _ m1 ctx p R2.base i1 hc' r1 hfu)
        have hP1' : hget (hset H1 P (.list (prs.map (fun p => iv p.1) ++ [iv p]))) P =
            some (.list (prs.map (fun p => iv p.1) ++ [iv p])) :=
          hget_hset_same _ (by have := F1.1; omega)
        have hat := at_last_m (jsCtx ext) rfl hP1'
        simp only [iv] at hat
        have hselfR1 := R1.self
        simp only [jdiagramFields, iv] at hselfR1
        have hselfR2 := R2.self
        simp only [jdiagramFields, iv] at hselfR2
        cases ha1 : apply names.length lim (applyFuel lim) .and ctx p m1 with
        | error q =>
          obtain ⟨e, m2⟩ := q
          rw [ha1] at sa
          obtain ⟨H2, a2, e2, ha2, R3, F3⟩ := sa
          simp only [iv, BOp.name] at e2
          simp only [jpremBody]
          jsstepA [hp, hmg, hselfR, e1, hP1, hselfR1, hctx, hP1', at_last, e2]
          simp only [ha1]
          jsstepM [hp, hmg, hctx, hP1', hat, e2, hselfR2]
          simp only [loopK]
          exact ⟨_, H2, a2, rfl, ha2, R3, ((FrameS.of_frame F1).mono (fun x hx => Or.inl hx)).trans
            ((FrameS.hset H1 _ (Or.inr rfl)).trans ((FrameS.of_frame F3).mono (fun x hx => Or.inl hx)))⟩
        | ok q =>
          obtain ⟨ctx', m2⟩ := q
          rw [ha1] at sa
          obtain ⟨H2, e2, R3, F3⟩ := sa
          simp only [iv, BOp.name] at e2
          obtain ⟨i2, ex2, _, hv2, r2, _, _⟩ := apply_spec _ _ _ _ _ ctx' m2 i1 hc' r1 ha1
          simp only [jpremBody]
          jsstepA [hp, hmg, hselfR, e1, hP1, hselfR1, hctx, hP1', e2]
          simp only [ha1]
          jsstepM [hp, hmg, hctx, hP1', hat, e2, hselfR2]
          have hP2 : hget H2 P = some (.list ((prs ++ [(p, f)]).map (fun p => iv p.1))) := by
            rw [F3.2 P (by have := F1.1; simp; omega) hPb, hget_hset_same _ (by have := F1.1; omega)]; simp [iv]
          have FF : FrameS (MutP D P) h H2 := ((FrameS.of_frame F1).mono (fun x hx => Or.inl hx)).trans
            ((FrameS.hset H1 _ (Or.inr rfl)).trans ((FrameS.of_frame F3).mono (fun x hx => Or.inl hx)))
          by_cases hz : ctx' = 0
          · subst hz
            rw [if_pos rfl]
            jsstepM []
            simp only [loopK]
            refine ⟨_, H2, rfl, by simp [iv], fun y h1 h2 => ?_, hP2, R3, FF⟩
            simp [Ne.symm h1, Ne.symm h2]
          · jsstepM []
            simp only [hz, if_false, seqF_normal, loopK]
            have ih := jprem_loop ext hnd AS P xs hP p1 p2 p3 p4 fs vs' k' (j + 1)
              ((env.set "f" v).set "context" (V.int ctx')) H2 m2 (prs ++ [(p, f)]) ctx'
              (by simp only [fdepthL, List.length_cons] at hk; omega)
              (by rw [FF.2 AS (hget_lt hAS) (fun e => hmAS (MutP_mut hP e))]; exact hAS) hmAS
              (by rw [← List.drop_drop, hxs]; simp) (by simpa using hlen)
              (fun q hq => JFRel.frame (FF.to_frame (fun x e => MutP_mut hP e)) _ _
                (hfr q (by simp [hq])))
              (by simp [hp]) (by simp [hmg]) (by simp [iv]) hP2 R3 i2 r2
              (fun q hq => by
                rcases List.mem_append.1 hq with hq | hq
                · have := hprs q hq; have := ex1.1; have := ex2.1; omega
                · simp at hq; subst hq; have := ex2.1; simp; omega)
              (by simp only [fsizeL] at hvis; omega)
            generalize premLoop names.length lim fs (prs ++ [(p, f)]) ctx' m2 = res at ih ⊢
            rcases res with ⟨e, m'⟩ | ⟨prs', c', m'⟩
            · obtain ⟨env', h', a', eo, ha', R', F'⟩ := ih
              exact ⟨env', h', a', eo, ha', R', FF.trans F'⟩
            · obtain ⟨env', h', eo, hc2, hy, hP', R', F'⟩ := ih
              refine ⟨env', h', eo, hc2, fun y h1 h2 => ?_, hP', R', FF.trans F'⟩
              rw [hy y h1 h2]; simp [Ne.symm h1, Ne.symm h2]

end PCSCR.Js
