import PCSConditionalRuntime.JsIncons
import PCSConditionalRuntime.PyDecided

/-!
# `checkConditional`: the consistent-context branch, symbolic part

```
source=m.compile(t.source);candidate=m.compile(t.candidate);
difference=m.apply('and',context,m.apply('xor',source,candidate));
```
-/

namespace PCSCR.Js

open PCSCR PCSDD PCSOmega PCSCR.Py

def JDecOutA (names : List String) (lim : Limits) (D : Addrs) (h : Heap) (env : Env) :
    Except (LimitReached × Mgr) (Nat × Nat × Nat × Mgr) → Out Flow → Prop
  | .ok (s, c, d, m5), o => ∃ env' h', o = .ok (.normal env') h' ∧ env'.get "source" = some (iv s) ∧
      env'.get "candidate" = some (iv c) ∧ env'.get "difference" = some (iv d) ∧
      (∀ y, y ≠ "source" → y ≠ "candidate" → y ≠ "difference" → env'.get y = env.get y) ∧
      JMRel names lim D h' m5 ∧ Frame D.base h h'
  | .error (e, m'), o => ∃ env' h' a, o = .ok (.raise (.obj (.ref a)) env') h' ∧
      hget h' a = some (.inst "ResourceLimit" [("message", .str e.name)]) ∧
      JMRel names lim D h' m' ∧ Frame D.base h h'

def jdecBodyA : List S :=
  [S.assign [Tgt.name "source"]
     (E.mcall (E.var "m") "compile" [E.attr (E.var "t") "source"]),
   S.assign [Tgt.name "candidate"]
     (E.mcall (E.var "m") "compile" [E.attr (E.var "t") "candidate"]),
   S.assign [Tgt.name "difference"]
     (E.mcall (E.var "m") "apply"
       [E.lit (V.str "and"), E.var "context",
        E.mcall (E.var "m") "apply" [E.lit (V.str "xor"), E.var "source", E.var "candidate"]])]

theorem jdec_compute (ext : Ext) {names : List String} {lim : Limits} {D : Addrs} (hnd : names.Nodup)
    (src cand : BForm names.length) (k : Nat) (env : Env) (h : Heap) (m1 : Mgr) (ctx A : Nat)
    (vkvs : List (V × V)) (vs vc : V)
    (hk : applyFuel lim + fdepth src + fdepth cand + 1 ≤ k)
    (hmg : env.get "m" = some (.ref D.self)) (hval : env.get "t" = some (.ref A))
    (hctx : env.get "context" = some (iv ctx))
    (hA : hget h A = some (.dict vkvs)) (hmA : ¬ D.mut A)
    (hs : dictFind .js vkvs (.str "source") = some vs) (hc : dictFind .js vkvs (.str "candidate") = some vc)
    (hfs : JFRel D h names vs src) (hfc : JFRel D h names vc cand)
    (hR : JMRel names lim D h m1) (hinv : Inv names.length lim m1) (hctxb : ctx < m1.nodes.size + 2)
    (hvis : m1.visits + src.size + cand.size ≤ 9007199254740991) :
    JDecOutA names lim D h env (decCompute names.length lim src cand ctx m1)
      (execB (jsCtx ext) (interp (jsCtx ext) (k + 1)) env h jdecBodyA) := by
  have hselfR := hR.self
  simp only [jdiagramFields, iv] at hselfR
  have s1 := JSimOut.both ((jcompile_sim ext hnd src) k (by omega) h m1 vs hR hinv (by omega) hfs)
    ((jcompile_sim ext (D := D.base) hnd src) k (by omega) h m1 vs hR.base hinv (by omega) hfs.base)
  unfold decCompute
  simp only [jdecBodyA]
  cases hc1 : compile names.length lim src m1 with
  | error q =>
    obtain ⟨e, m2⟩ := q
    rw [hc1] at s1
    obtain ⟨H1, a1, e1, ha1, R1, F1⟩ := s1
    jsstepA [hmg, hval, hA, hs, hselfR, e1]
    exact ⟨_, H1, a1, rfl, ha1, R1, F1⟩
  | ok q =>
    obtain ⟨sr, m2⟩ := q
    rw [hc1] at s1
    obtain ⟨H1, e1, R1, F1⟩ := s1
    obtain ⟨i2, ex2, _, r2, _⟩ := compile_spec src m1 sr m2 hinv hc1
    have hv2 := compile_visits src m1 sr m2 hc1
    have hA1 : hget H1 A = some (.dict vkvs) := by
      rw [F1.2 A (hget_lt hA) (fun e => hmA (Addrs.base_mut e))]; exact hA
    have hfc1 := JFRel.frame (Frame.ofBase F1) _ _ hfc
    have hselfR1 := R1.self
    simp only [jdiagramFields, iv] at hselfR1
    have s2 := JSimOut.both ((jcompile_sim ext hnd cand) k (by omega) H1 m2 vc R1 i2 (by rw [hv2]; omega) hfc1)
      ((jcompile_sim ext (D := D.base) hnd cand) k (by omega) H1 m2 vc R1.base i2 (by rw [hv2]; omega) hfc1.base)
    jsstepA [hmg, hval, hA, hs, hselfR, e1]
    cases hc2 : compile names.length lim cand m2 with
    | error q =>
      obtain ⟨e, m3⟩ := q
      rw [hc2] at s2
      obtain ⟨H2, a2, e2, ha2, R2, F2⟩ := s2
      jsstepA [hmg, hval, hA1, hc, hselfR1, e2]
      exact ⟨_, H2, a2, rfl, ha2, R2, F1.trans F2⟩
    | ok q =>
      obtain ⟨cr, m3⟩ := q
      rw [hc2] at s2
      obtain ⟨H2, e2, R2, F2⟩ := s2
      obtain ⟨i3, ex3, _, r3, _⟩ := compile_spec cand m2 cr m3 i2 hc2
      have hselfR2 := R2.self
      simp only [jdiagramFields, iv] at hselfR2
      jsstepA [hmg, hval, hA1, hc, hselfR1, e2]
      have hsr : sr < m3.nodes.size + 2 := by have := ex3.1; omega
      have hfu : lim.operations < applyFuel lim + m3.ops := by unfold applyFuel; omega
      have s3 := JSimOut.both (japply_sim ext .xor (applyFuel lim) k (by omega) H2 m3 sr cr R2 i3 hsr r3 hfu)
        (japply_sim ext (D := D.base) .xor (applyFuel lim) k (by omega) H2 m3 sr cr R2.base i3 hsr r3 hfu)
      cases hc3 : apply names.length lim (applyFuel lim) .xor sr cr m3 with
      | error q =>
        obtain ⟨e, m4⟩ := q
        rw [hc3] at s3
        obtain ⟨H3, a3, e3, ha3, R3, F3⟩ := s3
        simp only [iv, BOp.name] at e3
        jsstepA [hmg, hctx, hselfR2, e3]
        exact ⟨_, H3, a3, rfl, ha3, R3, (F1.trans F2).trans F3⟩
      | ok q =>
        obtain ⟨xr, m4⟩ := q
        rw [hc3] at s3
        obtain ⟨H3, e3, R3, F3⟩ := s3
        obtain ⟨i4, ex4, _, _, r4, _, _⟩ := apply_spec _ _ _ _ _ xr m4 i3 hsr r3 hc3
        simp only [iv, BOp.name] at e3
        have hselfR3 := R3.self
        simp only [jdiagramFields, iv] at hselfR3
        have hcx : ctx < m4.nodes.size + 2 := by have := ex2.1; have := ex3.1; have := ex4.1; omega
        have hfu4 : lim.operations < applyFuel lim + m4.ops := by unfold applyFuel; omega
        have s4 := JSimOut.both (japply_sim ext .and (applyFuel lim) k (by omega) H3 m4 ctx xr R3 i4 hcx r4 hfu4)
          (japply_sim ext (D := D.base) .and (applyFuel lim) k (by omega) H3 m4 ctx xr R3.base i4 hcx r4 hfu4)
        cases hc4 : apply names.length lim (applyFuel lim) .and ctx xr m4 with
        | error q =>
          obtain ⟨e, m5⟩ := q
          rw [hc4] at s4
          obtain ⟨H4, a4, e4, ha4, R4, F4⟩ := s4
          simp only [iv, BOp.name] at e4
          jsstepA [hmg, hctx, hselfR2, e3, hselfR3, e4]
          simp only [hc4]
          exact ⟨_, H4, a4, rfl, ha4, R4, ((F1.trans F2).trans F3).trans F4⟩
        | ok q =>
          obtain ⟨dr, m5⟩ := q
          rw [hc4] at s4
          obtain ⟨H4, e4, R4, F4⟩ := s4
          simp only [iv, BOp.name] at e4
          jsstepA [hmg, hctx, hselfR2, e3, hselfR3, e4]
          simp only [hc4]
          refine ⟨_, H4, rfl, by simp [iv], by simp [iv], by simp [iv], fun y h1 h2 h3 => ?_, R4,
            ((F1.trans F2).trans F3).trans F4⟩
          simp [Ne.symm h1, Ne.symm h2, Ne.symm h3]

end PCSCR.Js
