import PCSConditionalRuntime.PyWits

/-!
# `check`: the consistent-context branch, symbolic part

```
source = manager.compile(value['source']); candidate = manager.compile(value['candidate'])
difference = manager.apply('and', context, manager.apply('xor', source, candidate))
```
-/

namespace PCSCR.Py

open PCSCR PCSDD PCSOmega

/-- The four manager calls of the consistent branch of `PCSDD.pipeline`. -/
def decCompute (n : Nat) (lim : Limits) (src cand : BForm n) (ctx : Nat) (m1 : Mgr) :
    Except (LimitReached × Mgr) (Nat × Nat × Nat × Mgr) :=
  match compile n lim src m1 with
  | .error e => .error e
  | .ok (s, m2) => match compile n lim cand m2 with
    | .error e => .error e
    | .ok (c, m3) => match apply n lim (applyFuel lim) .xor s c m3 with
      | .error e => .error e
      | .ok (x, m4) => match apply n lim (applyFuel lim) .and ctx x m4 with
        | .error e => .error e
        | .ok (d, m5) => .ok (s, c, d, m5)

def DecOutA (names : List String) (lim : Limits) (D : Addrs) (h : Heap) (env : Env) :
    Except (LimitReached × Mgr) (Nat × Nat × Nat × Mgr) → Out Flow → Prop
  | .ok (s, c, d, m5), o => ∃ env' h', o = .ok (.normal env') h' ∧ env'.get "source" = some (iv s) ∧
      env'.get "candidate" = some (iv c) ∧ env'.get "difference" = some (iv d) ∧
      (∀ y, y ≠ "source" → y ≠ "candidate" → y ≠ "difference" → env'.get y = env.get y) ∧
      MRel names lim D h' m5 ∧ Frame D.base h h'
  | .error (e, m'), o => ∃ env' h' a, o = .ok (.raise (.obj (.ref a)) env') h' ∧
      hget h' a = some (.inst "ResourceLimit" [("args", .tup [.str e.name])]) ∧
      MRel names lim D h' m' ∧ Frame D.base h h'

def decBodyA : List S :=
  [S.assign [Tgt.name "source"]
     (E.mcall (E.var "manager") "compile" [E.sub (E.var "value") (E.lit (V.str "source"))]),
   S.assign [Tgt.name "candidate"]
     (E.mcall (E.var "manager") "compile" [E.sub (E.var "value") (E.lit (V.str "candidate"))]),
   S.assign [Tgt.name "difference"]
     (E.mcall (E.var "manager") "apply"
       [E.lit (V.str "and"), E.var "context",
        E.mcall (E.var "manager") "apply" [E.lit (V.str "xor"), E.var "source", E.var "candidate"]])]

theorem Frame.ofBase {D : Addrs} {h h' : Heap} (F : Frame D.base h h') : Frame D h h' :=
  FrameS.to_frame (FrameS.of_frame F) (fun _ e => Addrs.base_mut e)

theorem dec_compute (ext : Ext) {names : List String} {lim : Limits} {D : Addrs} (hnd : names.Nodup)
    (src cand : BForm names.length) (k : Nat) (env : Env) (h : Heap) (m1 : Mgr) (ctx A : Nat)
    (vkvs : List (V × V)) (vs vc : V)
    (hk : applyFuel lim + fdepth src + fdepth cand + 1 ≤ k)
    (hmg : env.get "manager" = some (.ref D.self)) (hval : env.get "value" = some (.ref A))
    (hctx : env.get "context" = some (iv ctx))
    (hA : hget h A = some (.dict vkvs)) (hmA : ¬ D.mut A)
    (hs : dictFind .py vkvs (.str "source") = some vs) (hc : dictFind .py vkvs (.str "candidate") = some vc)
    (hfs : FRel D h names vs src) (hfc : FRel D h names vc cand)
    (hR : MRel names lim D h m1) (hinv : Inv names.length lim m1) (hctxb : ctx < m1.nodes.size + 2) :
    DecOutA names lim D h env (decCompute names.length lim src cand ctx m1)
      (execB (pyCtx ext) (interp (pyCtx ext) (k + 1)) env h decBodyA) := by
  have hselfR := hR.self
  simp only [diagramFields, iv] at hselfR
  have s1 := SimOut.both ((compile_sim ext hnd src) k (by omega) h m1 vs hR hinv hfs)
    ((compile_sim ext (D := D.base) hnd src) k (by omega) h m1 vs hR.base hinv hfs.base)
  unfold decCompute
  simp only [decBodyA]
  cases hc1 : compile names.length lim src m1 with
  | error q =>
    obtain ⟨e, m2⟩ := q
    rw [hc1] at s1
    obtain ⟨H1, a1, e1, ha1, R1, F1⟩ := s1
    pystepA [hmg, hval, hA, hs, hselfR, e1]
    exact ⟨_, H1, a1, rfl, ha1, R1, F1⟩
  | ok q =>
    obtain ⟨sr, m2⟩ := q
    rw [hc1] at s1
    obtain ⟨H1, e1, R1, F1⟩ := s1
    obtain ⟨i2, ex2, _, r2, _⟩ := compile_spec src m1 sr m2 hinv hc1
    have hA1 : hget H1 A = some (.dict vkvs) := by
      rw [F1.2 A (hget_lt hA) (fun e => hmA (Addrs.base_mut e))]; exact hA
    have hfc1 := FRel.frame (Frame.ofBase F1) _ _ hfc
    have hselfR1 := R1.self
    simp only [diagramFields, iv] at hselfR1
    have s2 := SimOut.both ((compile_sim ext hnd cand) k (by omega) H1 m2 vc R1 i2 hfc1)
      ((compile_sim ext (D := D.base) hnd cand) k (by omega) H1 m2 vc R1.base i2 hfc1.base)
    pystepA [hmg, hval, hA, hs, hselfR, e1]
    cases hc2 : compile names.length lim cand m2 with
    | error q =>
      obtain ⟨e, m3⟩ := q
      rw [hc2] at s2
      obtain ⟨H2, a2, e2, ha2, R2, F2⟩ := s2
      pystepA [hmg, hval, hA1, hc, hselfR1, e2]
      exact ⟨_, H2, a2, rfl, ha2, R2, F1.trans F2⟩
    | ok q =>
      obtain ⟨cr, m3⟩ := q
      rw [hc2] at s2
      obtain ⟨H2, e2, R2, F2⟩ := s2
      obtain ⟨i3, ex3, _, r3, _⟩ := compile_spec cand m2 cr m3 i2 hc2
      have hselfR2 := R2.self
      simp only [diagramFields, iv] at hselfR2
      pystepA [hmg, hval, hA1, hc, hselfR1, e2]
      have hsr : sr < m3.nodes.size + 2 := by have := ex3.1; omega
      have hfu : lim.operations < applyFuel lim + m3.ops := by unfold applyFuel; omega
      have s3 := SimOut.both (apply_sim ext .xor (applyFuel lim) k (by omega) H2 m3 sr cr R2 i3 hsr r3 hfu)
        (apply_sim ext (D := D.base) .xor (applyFuel lim) k (by omega) H2 m3 sr cr R2.base i3 hsr r3 hfu)
      cases hc3 : apply names.length lim (applyFuel lim) .xor sr cr m3 with
      | error q =>
        obtain ⟨e, m4⟩ := q
        rw [hc3] at s3
        obtain ⟨H3, a3, e3, ha3, R3, F3⟩ := s3
        simp only [iv, BOp.name] at e3
        pystepA [hmg, hctx, hselfR2, e3]
        exact ⟨_, H3, a3, rfl, ha3, R3, (F1.trans F2).trans F3⟩
      | ok q =>
        obtain ⟨xr, m4⟩ := q
        rw [hc3] at s3
        obtain ⟨H3, e3, R3, F3⟩ := s3
        obtain ⟨i4, ex4, _, _, r4, _, _⟩ := apply_spec _ _ _ _ _ xr m4 i3 hsr r3 hc3
        simp only [iv, BOp.name] at e3
        have hselfR3 := R3.self
        simp only [diagramFields, iv] at hselfR3
        have hcx : ctx < m4.nodes.size + 2 := by have := ex2.1; have := ex3.1; have := ex4.1; omega
        have hfu4 : lim.operations < applyFuel lim + m4.ops := by unfold applyFuel; omega
        have s4 := SimOut.both (apply_sim ext .and (applyFuel lim) k (by omega) H3 m4 ctx xr R3 i4 hcx r4 hfu4)
          (apply_sim ext (D := D.base) .and (applyFuel lim) k (by omega) H3 m4 ctx xr R3.base i4 hcx r4 hfu4)
        cases hc4 : apply names.length lim (applyFuel lim) .and ctx xr m4 with
        | error q =>
          obtain ⟨e, m5⟩ := q
          rw [hc4] at s4
          obtain ⟨H4, a4, e4, ha4, R4, F4⟩ := s4
          simp only [iv, BOp.name] at e4
          pystepA [hmg, hctx, hselfR2, e3, hselfR3, e4]
          simp only [hc4]
          exact ⟨_, H4, a4, rfl, ha4, R4, ((F1.trans F2).trans F3).trans F4⟩
        | ok q =>
          obtain ⟨dr, m5⟩ := q
          rw [hc4] at s4
          obtain ⟨H4, e4, R4, F4⟩ := s4
          simp only [iv, BOp.name] at e4
          pystepA [hmg, hctx, hselfR2, e3, hselfR3, e4]
          simp only [hc4]
          refine ⟨_, H4, rfl, by simp [iv], by simp [iv], by simp [iv], fun y h1 h2 h3 => ?_, R4,
            ((F1.trans F2).trans F3).trans F4⟩
          simp [Ne.symm h1, Ne.symm h2, Ne.symm h3]

end PCSCR.Py
