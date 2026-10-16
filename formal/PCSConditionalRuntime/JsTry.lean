import PCSConditionalRuntime.JsDecided
import PCSConditionalRuntime.PyTry

/-!
# `checkConditional`: the body of the `try` statement

```
const premises=[];let context=1,source=null,candidate=null,difference=null;
for(const f of t.assumptions){ … }                                    (`jprem_loop`)
if(context===0){ … }                                                  (`jincons_sim`)
else{ … }                                                             (`jdec_compute`, `jreport_sim`)
r.diagram={ … };                                                      (`jdiag_sim`)
```
simulates `PCSDD.pipeline`.  The two side conditions bound the `visits` and `witnessSteps`
counters by `2^53 - 1` (they hold for every task accepted by `validateConditional`, which
enforces at most 24 variables, 8 assumptions and 128 nodes per formula).
-/

namespace PCSCR.Js

open PCSCR PCSDD PCSOmega PCSCR.Py

theorem compile_wsteps {n : Nat} {lim : Limits} :
    ∀ (f : BForm n) (m : Mgr) (r : Nat) (m' : Mgr),
      compile n lim f m = .ok (r, m') → m'.wsteps = m.wsteps := by
  intro f
  induction f with
  | atom i => intro m r m' h; simp only [compile] at h; rw [mkNode_wsteps h]
  | tt => intro m r m' h; simp only [compile] at h; cases h; rfl
  | ff => intro m r m' h; simp only [compile] at h; cases h; rfl
  | not f ih =>
    intro m r m' h; simp only [compile] at h
    split at h
    · cases h
    · rename_i x m1 h1
      rw [apply_wsteps _ _ _ _ _ _ _ h, ih _ _ _ h1]
  | and f g ihf ihg =>
    intro m r m' h; simp only [compile] at h
    split at h
    · cases h
    · rename_i x m1 h1
      split at h
      · cases h
      · rename_i y m2 h2
        rw [apply_wsteps _ _ _ _ _ _ _ h, ihg _ _ _ h2, ihf _ _ _ h1]
  | or f g ihf ihg =>
    intro m r m' h; simp only [compile] at h
    split at h
    · cases h
    · rename_i x m1 h1
      split at h
      · cases h
      · rename_i y m2 h2
        rw [apply_wsteps _ _ _ _ _ _ _ h, ihg _ _ _ h2, ihf _ _ _ h1]
  | imp f g ihf ihg =>
    intro m r m' h; simp only [compile] at h
    split at h
    · cases h
    · rename_i x m1 h1
      split at h
      · cases h
      · rename_i y m2 h2
        split at h
        · cases h
        · rename_i z m3 h3
          rw [apply_wsteps _ _ _ _ _ _ _ h, apply_wsteps _ _ _ _ _ _ _ h3, ihg _ _ _ h2, ihf _ _ _ h1]

theorem premLoop_wsteps {n : Nat} {lim : Limits} :
    ∀ (fs : List (BForm n)) (prs : List (Nat × BForm n)) (ctx : Nat) (m : Mgr) prs' ctx' (m' : Mgr),
      premLoop n lim fs prs ctx m = .ok (prs', ctx', m') → m'.wsteps = m.wsteps
  | [], _, _, _, _, _, _, h => by simp only [premLoop] at h; cases h; rfl
  | f :: fs, prs, ctx, m, prs', ctx', m', h => by
      simp only [premLoop] at h
      split at h
      · cases h
      rename_i p m1 h1
      split at h
      · cases h
      rename_i c m2 h2
      split at h
      · cases h; rw [apply_wsteps _ _ _ _ _ _ _ h2, compile_wsteps _ _ _ _ h1]
      · rw [premLoop_wsteps fs _ _ _ _ _ _ h, apply_wsteps _ _ _ _ _ _ _ h2, compile_wsteps _ _ _ _ h1]

theorem premLoop_visits {n : Nat} {lim : Limits} :
    ∀ (fs : List (BForm n)) (prs : List (Nat × BForm n)) (ctx : Nat) (m : Mgr) prs' ctx' (m' : Mgr),
      premLoop n lim fs prs ctx m = .ok (prs', ctx', m') → m'.visits ≤ m.visits + fsizeL fs
  | [], _, _, _, _, _, _, h => by simp only [premLoop] at h; cases h; simp
  | f :: fs, prs, ctx, m, prs', ctx', m', h => by
      simp only [premLoop] at h
      split at h
      · cases h
      rename_i p m1 h1
      split at h
      · cases h
      rename_i c m2 h2
      have e1 := compile_visits _ _ _ _ h1
      have e2 := apply_visits _ _ _ _ _ _ _ h2
      split at h
      · cases h; simp only [fsizeL]; omega
      · have := premLoop_visits fs _ _ _ _ _ _ h; simp only [fsizeL]; omega

theorem fsizeL_le_take {n : Nat} : ∀ (fs : List (BForm n)) (k : Nat), fsizeL (fs.take k) ≤ fsizeL fs
  | [], _ => by simp [fsizeL]
  | f :: fs, 0 => by simp [fsizeL]
  | f :: fs, k + 1 => by simp only [List.take_succ_cons, fsizeL]; have := fsizeL_le_take fs k; omega

def jtryBody : List S :=
  [S.assign [Tgt.name "premises"] (E.listD []),
   S.assign [Tgt.name "context"] (E.lit (V.int 1)),
   S.assign [Tgt.name "source"] (E.lit V.none),
   S.assign [Tgt.name "candidate"] (E.lit V.none),
   S.assign [Tgt.name "difference"] (E.lit V.none),
   S.forIn (Tgt.name "f") (E.attr (E.var "t") "assumptions") jpremBody,
   S.ifte (E.bin BinOp.eq (E.var "context") (E.lit (V.int 0))) jincBody (jdecBodyA ++ jrepBody),
   jdiagS]

def JTryOut (names : List String) (t : CTask names.length) (D : Addrs) (R : Nat) (h : Heap)
    (kvs : List (V × V)) (kts : List (String × T)) :
    Except (LimitReached × Mgr) (Body names.length × Mgr) → Out Flow → Prop
  | .ok (b, m), o => ∃ env' h' kvs', o = .ok (.normal env') h' ∧ hget h' R = some (.dict kvs') ∧
      ReadsKV (fun a => a = R) h' kvs' (bodyT names t kts b m) ∧ JWorkOK D h' m ∧ FrameS (Big D h.length) h h'
  | .error (e, m), o => ∃ env' h' a, o = .ok (.raise (.obj (.ref a)) env') h' ∧
      hget h' a = some (.inst "ResourceLimit" [("message", .str e.name)]) ∧
      hget h' R = some (.dict kvs) ∧ JWorkOK D h' m ∧ FrameS (Big D h.length) h h'

theorem JWorkOK.of_addOwn {D : Addrs} {N : Nat} {h : Heap} {m : Mgr} (w : JWorkOK (D.addOwn N) h m) :
    JWorkOK D h m :=
  ⟨by have := w.1; rwa [jdiagramFields_addOwn] at this, w.2⟩

set_option maxHeartbeats 1000000 in
theorem jtry_sim (ext : Ext) {names : List String} {lim : Limits} {D : Addrs} (hnd : names.Nodup)
    (t : CTask names.length) (k : Nat) (env : Env) (h : Heap) (A AS R : Nat)
    (vkvs : List (V × V)) (as : List V) (vs vc : V) (kvs : List (V × V)) (kts : List (String × T))
    (hk : applyFuel lim + fdepthL t.assumptions + fdepth t.source + fdepth t.candidate +
      2 * t.assumptions.length + names.length + 10 ≤ k)
    (hmg : env.get "m" = some (.ref D.self)) (hval : env.get "t" = some (.ref A))
    (hres : env.get "r" = some (.ref R))
    (hA : hget h A = some (.dict vkvs)) (hmA : ¬ D.mut A)
    (has : dictFind .js vkvs (.str "assumptions") = some (.ref AS))
    (hAS : hget h AS = some (.list as)) (hmAS : ¬ D.mut AS) (hl : as.length = t.assumptions.length)
    (hz : ∀ p ∈ as.zip t.assumptions, JFRel D h names p.1 p.2)
    (hs : dictFind .js vkvs (.str "source") = some vs) (hc : dictFind .js vkvs (.str "candidate") = some vc)
    (hfs : JFRel D h names vs t.source) (hfc : JFRel D h names vc t.candidate)
    (hR : JMRel names lim D h Mgr.empty)
    (hRo : R ∈ D.own) (r1 : R ≠ D.self) (r2 : R ≠ D.nodes) (r3 : R ≠ D.uniq) (r4 : R ≠ D.memo)
    (hRk : hget h R = some (.dict kvs)) (hkv : ReadsKV (Big D h.length) h kvs kts)
    (hvisB : fsizeL t.assumptions + t.source.size + t.candidate.size ≤ 9007199254740991)
    (hwsB : (t.assumptions.length + 2) * names.length ≤ 9007199254740991) :
    JTryOut names t D R h kvs kts (pipeline t lim)
      (execB (jsCtx ext) (interp (jsCtx ext) (k + 1)) env h jtryBody) := by
  have hRlt := hget_lt hRk
  have hlt := hR.addrs_lt
  simp only [jtryBody]
  jsstepA []
  jsstepA []
  jsstepA []
  jsstepA []
  jsstepA []
  generalize hPdef : h.length = P at *
  have RP : JMRel names lim (D.addOwn P) (h ++ [Obj.list []]) Mgr.empty := by
    have := hR.addOwn (Obj.list []); rw [hPdef] at this; exact this
  have hmA' : ¬ (D.addOwn P).mut A := fun e => by
    rcases Addrs.addOwn_mut e with e | e
    · exact hmA e
    · have := hget_lt hA; omega
  have hmAS' : ¬ (D.addOwn P).mut AS := fun e => by
    rcases Addrs.addOwn_mut e with e | e
    · exact hmAS e
    · have := hget_lt hAS; omega
  have hFP : ∀ {n : Nat} {f : BForm n} {v : V}, JFRel D h names v f →
      JFRel (D.addOwn P) (h ++ [Obj.list []]) names v f := fun hf => by
    have := JFRel.addOwn hf (Obj.list []); rw [hPdef] at this; exact this
  have pl := jprem_loop ext (D := D.addOwn P) hnd AS P as (by simp) (by simp; omega) (by simp; omega)
    (by simp; omega) (by simp; omega) t.assumptions as k 0
    (((((env.set "premises" (.ref P)).set "context" (.int 1)).set "source" V.none).set "candidate" V.none).set
      "difference" V.none) (h ++ [Obj.list []]) Mgr.empty [] 1
    (by omega) (by rw [hget_append_lt_list _ (hget_lt hAS)]; exact hAS) hmAS' (by simp) hl
    (fun p hp => hFP (hz p hp)) (by simp [Env.get_set]) (by simp [Env.get_set, hmg]) (by simp [Env.get_set, iv])
    (by simp [hget, ← hPdef]) RP (Inv.empty _ _) (by simp [Mgr.empty]) (fun _ h => by simp at h)
    (by simp only [Mgr.empty]; omega)
  rw [execB_cons']
  conv in execS _ _ _ _ _ => simp [execS, evalE, bindS, Env.get_set, hval, hA, hget_append_lt_list _ (hget_lt hA),
    subOp, attrOp, has, hashable]
  have FPB : ∀ {X Y : Heap}, FrameS (MutP (D.addOwn P) P) X Y → FrameS (Big D h.length) X Y :=
    fun F => F.mono (fun x e => by
      rcases e with e | e
      · exact Or.inl (Addrs.base_mut (by simpa using e))
      · exact Or.inr (by omega))
  have FB0 : FrameS (Big D h.length) h (h ++ [Obj.list []]) := FrameS.append _ _ _
  have hRb : ¬ D.base.mut R := by
    simp only [Addrs.mut, Addrs.base_self, Addrs.base_nodes, Addrs.base_uniq, Addrs.base_memo,
      Addrs.base_own, List.not_mem_nil, or_false]; omega
  have hRP : R ≠ P := by omega
  have hRMP : ¬ MutP (D.addOwn P) P R := fun e => by
    rcases e with e | e
    · exact hRb (by simpa using e)
    · exact hRP e
  have hR0 : hget (h ++ [Obj.list []]) R = some (.dict kvs) := by
    rw [hget_append_lt_list _ (by omega)]; exact hRk
  unfold pipeline
  cases hpl : premLoop names.length lim t.assumptions [] 1 Mgr.empty with
  | error q =>
    obtain ⟨e, m1⟩ := q
    rw [hpl] at pl
    obtain ⟨env1, h1, a1, e1, ha1, R1, F1⟩ := pl
    rw [e1]
    simp only [seqF_raise, JTryOut]
    refine ⟨env1, h1, a1, rfl, ha1, ?_, (JWorkOK.of_mrel R1).of_addOwn, FB0.trans (FPB F1)⟩
    rw [F1.2 R (by simp; omega) hRMP]; exact hR0
  | ok q =>
    obtain ⟨prs, ctx, m1⟩ := q
    rw [hpl] at pl
    obtain ⟨env1, h1, e1, hctx1, hy1, hP1, R1, F1⟩ := pl
    rw [e1]
    simp only [seqF_normal]
    obtain ⟨i1, ro1, d1, ⟨kk, hkk⟩, hfin⟩ := pipeline_premises hpl
    have g1 : ∀ y, y ≠ "context" → y ≠ "f" → y ≠ "premises" → y ≠ "source" → y ≠ "candidate" →
        y ≠ "difference" → env1.get y = env.get y := fun y a b c d e f => by
      rw [hy1 y a b]; simp [Env.get_set, Ne.symm a, Ne.symm c, Ne.symm d, Ne.symm e, Ne.symm f]
    have hv1 := premLoop_visits t.assumptions [] 1 Mgr.empty prs ctx m1 hpl
    have hw1 := premLoop_wsteps t.assumptions [] 1 Mgr.empty prs ctx m1 hpl
    simp only [Mgr.empty] at hv1 hw1
    generalize hE2 : env1 = env2 at g1 ⊢
    have hctx2 : env2.get "context" = some (iv ctx) := by rw [← hE2]; simp [Env.get_set, hctx1]
    have hmg2 : env2.get "m" = some (.ref D.self) := by
      rw [g1 _ (by decide) (by decide) (by decide) (by decide) (by decide) (by decide)]; exact hmg
    have hres2 : env2.get "r" = some (.ref R) := by
      rw [g1 _ (by decide) (by decide) (by decide) (by decide) (by decide) (by decide)]; exact hres
    have hval2 : env2.get "t" = some (.ref A) := by
      rw [g1 _ (by decide) (by decide) (by decide) (by decide) (by decide) (by decide)]; exact hval
    have hprem2 : env2.get "premises" = some (.ref P) := by
      rw [← hE2, hy1 _ (by decide) (by decide)]; simp [Env.get_set]
    have hsrc2 : env2.get "source" = some V.none := by
      rw [← hE2, hy1 _ (by decide) (by decide)]; simp [Env.get_set]
    have hcand2 : env2.get "candidate" = some V.none := by
      rw [← hE2, hy1 _ (by decide) (by decide)]; simp [Env.get_set]
    have hdif2 : env2.get "difference" = some V.none := by
      rw [← hE2, hy1 _ (by decide) (by decide)]; simp [Env.get_set]
    have FB1 : FrameS (Big D h.length) h h1 := FB0.trans (FPB F1)
    have hR1 : hget h1 R = some (.dict kvs) := by rw [F1.2 R (by simp; omega) hRMP]; exact hR0
    have hkvB : ReadsKV (Big D h.length) h kvs kts := by rw [hPdef]; exact hkv
    have hkv1 : ReadsKV (D.addOwn P).mut h1 kvs kts := (hkvB.frame FB1).anti (fun a e => by
      rcases Addrs.addOwn_mut e with e | e
      · exact Or.inl e
      · exact Or.inr (by omega))
    have hmPb : ¬ (D.addOwn P).base.mut P := by
      simp only [Addrs.addOwn_base, Addrs.mut, Addrs.base_self, Addrs.base_nodes, Addrs.base_uniq,
        Addrs.base_memo, Addrs.base_own, List.not_mem_nil, or_false]; omega
    have hplen : prs.length ≤ t.assumptions.length := by
      have := congrArg List.length hkk; simp at this; omega
    have hBig' : ∀ {X Y : Heap}, FrameS (Big (D.addOwn P) h1.length) X Y → FrameS (Big D h.length) X Y :=
      fun F => F.mono (fun x e => by
        rcases e with e | e
        · rcases Addrs.addOwn_mut e with e | e
          · exact Or.inl e
          · exact Or.inr (by omega)
        · exact Or.inr (by have := F1.1; simp at this; omega))
    have hRm' : ∀ a, a = R → (D.addOwn P).mut a := fun a e => e ▸ Addrs.mut_addOwn (Or.inr (Or.inr (Or.inr (Or.inr hRo))))
    rw [execB_cons']
    conv in execS _ _ _ _ _ => simp only [execS]
    simp [evalE, bindS, hctx2, binOp, eqD, eqJs, iv, truthy, num]
    by_cases hc0 : ctx = 0
    · subst hc0
      simp only [if_true]
      have hinc := jincons_sim ext (D := D.addOwn P) hnd prs k env2 h1 m1 P R kvs kts (by omega) hprem2
        (by simpa using hmg2) hres2 hP1 hmPb R1 i1 ro1 (by simp [hRo]) (by simpa using r1) (by simpa using r2)
        (by simpa using r3) (by simpa using r4) hR1 hkv1
        (by rw [hw1]; have := Nat.mul_le_mul_right names.length hplen; simp only [Nat.add_mul] at hwsB; omega)
      have keep := fun y (hy : y ∉ bindsB jincBody) => execB_keeps_interp (jsCtx ext) (k + 1) y jincBody env2 h1 hy
      simp only [incCompute] at hinc
      cases hs : shrink names.length lim prs (List.range prs.length) (List.range prs.length) m1 with
      | error q =>
        obtain ⟨e, m2⟩ := q
        simp only [hs] at hinc
        obtain ⟨env3, h3, a3, e3, ha3, hR3, W3, F3⟩ := hinc
        rw [e3]
        simp only [seqF_raise, JTryOut]
        exact ⟨env3, h3, a3, rfl, ha3, hR3, W3.of_addOwn, FB1.trans (hBig' F3)⟩
      | ok q =>
        obtain ⟨core, m2⟩ := q
        simp only [hs] at hinc
        dsimp only
        cases hcw : coreWits names.length lim prs core core m2 with
        | error q =>
          obtain ⟨e, m3⟩ := q
          simp only [hcw] at hinc
          obtain ⟨env3, h3, a3, e3, ha3, hR3, W3, F3⟩ := hinc
          rw [e3]
          simp only [seqF_raise, JTryOut]
          exact ⟨env3, h3, a3, rfl, ha3, hR3, W3.of_addOwn, FB1.trans (hBig' F3)⟩
        | ok q =>
          obtain ⟨ws, m3⟩ := q
          simp only [hcw] at hinc
          obtain ⟨env3, h3, kvs3, N, e3, hN, hR3, hkv3, R3, F3⟩ := hinc
          have k1 := keep "m" (by decide)
          have k2 := keep "r" (by decide)
          have k3 := keep "source" (by decide)
          have k4 := keep "candidate" (by decide)
          have k5 := keep "context" (by decide)
          have k6 := keep "difference" (by decide)
          rw [e3] at k1 k2 k3 k4 k5 k6
          simp only [FK] at k1 k2 k3 k4 k5 k6
          rw [e3]
          simp only [seqF_normal]
          obtain ⟨d1, dR, dF, dRd⟩ := jdiag_sim ext (D := (D.addOwn P).addOwn N) k env3 h3 m3 R kvs3 none none none 0
            (by rw [k1]; simpa using hmg2) (by rw [k2]; exact hres2) (by rw [k3]; exact hsrc2)
            (by rw [k4]; exact hcand2) (by rw [k5]; exact hctx2) (by rw [k6]; exact hdif2) R3
            (by simp [hRo]) (by simpa using r1) (by simpa using r2) (by simpa using r3) (by simpa using r4) hR3
          rw [execB_cons', d1]
          simp only [seqF_normal, execB_nil_eq, JTryOut, bodyT]
          refine ⟨_, _, _, rfl, hget_hset_same _ (by simp; have := hget_lt hR3; omega), ?_,
            (JWorkOK.of_mrel dR).of_addOwn.of_addOwn, (FB1.trans (hBig' F3)).trans (dF.mono (fun x e => by
              subst e; exact Or.inl (Or.inr (Or.inr (Or.inr (Or.inr hRo))))))⟩
          exact ReadsKV.jdictSet _ dRd _ _ ((hkv3.anti hRm').frame dF)
    · simp only [hc0, if_false]
      have hnotB : ∀ x, x < h.length → ¬ D.mut x → ¬ Big D h.length x := fun x hx hm e => by
        rcases e with e | e
        · exact hm e
        · omega
      have hA1 : hget h1 A = some (.dict vkvs) := by
        rw [FB1.2 A (hget_lt hA) (hnotB _ (hget_lt hA) hmA)]; exact hA
      have hAS1 : hget h1 AS = some (.list as) := by
        rw [FB1.2 AS (hget_lt hAS) (hnotB _ (hget_lt hAS) hmAS)]; exact hAS
      have hPm : ∀ x, MutP (D.addOwn P) P x → (D.addOwn P).mut x := fun x e => by
        rcases e with e | e
        · exact Addrs.base_mut e
        · subst e; exact Or.inr (Or.inr (Or.inr (Or.inr List.mem_cons_self)))
      have Fr1 : Frame (D.addOwn P) (h ++ [Obj.list []]) h1 := F1.to_frame hPm
      have hF1 : ∀ {f : BForm names.length} {v : V}, JFRel D h names v f → JFRel (D.addOwn P) h1 names v f :=
        fun hf => JFRel.frame Fr1 _ _ (hFP hf)
      have hdc := jdec_compute ext (D := D.addOwn P) hnd t.source t.candidate k env2 h1 m1 ctx A vkvs vs vc
        (by omega) (by simpa using hmg2) hval2 hctx2 hA1 hmA' hs hc (hF1 hfs) (hF1 hfc) R1 i1 d1.1
        (by omega)
      have hRbase : ¬ (D.addOwn P).base.mut R := by simpa using hRb
      have hR1lt := hget_lt hR1
      have FbB : ∀ {X Y : Heap}, Frame (D.addOwn P).base X Y → FrameS (Big D h.length) X Y :=
        fun F => (FrameS.of_frame F).mono (fun x e => Or.inl (Addrs.base_mut (by simpa using e)))
      have herr : ∀ e m', decCompute names.length lim t.source t.candidate ctx m1 = .error (e, m') →
          JTryOut names t D R h kvs kts (.error (e, m'))
            (seqF (seqF (execB (jsCtx ext) (interp (jsCtx ext) (k + 1)) env2 h1 jdecBodyA) fun env' h' =>
              execB (jsCtx ext) (interp (jsCtx ext) (k + 1)) env' h' jrepBody) fun env' h' =>
              execB (jsCtx ext) (interp (jsCtx ext) (k + 1)) env' h' [jdiagS]) := by
        intro e m' H
        rw [H] at hdc
        obtain ⟨env', h', a, e3, ha, R5, F5⟩ := hdc
        rw [e3]
        simp only [seqF_raise, JTryOut]
        refine ⟨env', h', a, rfl, ha, ?_, (JWorkOK.of_mrel R5).of_addOwn, FB1.trans (FbB F5)⟩
        rw [F5.2 R hR1lt hRbase]; exact hR1
      rw [execB_append]
      cases hc1 : compile names.length lim t.source m1 with
      | error q => exact herr q.1 q.2 (by simp [decCompute, hc1])
      | ok q1 =>
      obtain ⟨s, m2⟩ := q1
      dsimp only
      cases hc2 : compile names.length lim t.candidate m2 with
      | error q => exact herr q.1 q.2 (by simp [decCompute, hc1, hc2])
      | ok q2 =>
      obtain ⟨c, m3⟩ := q2
      dsimp only
      cases hc3 : apply names.length lim (applyFuel lim) BOp.xor s c m3 with
      | error q => exact herr q.1 q.2 (by simp [decCompute, hc1, hc2, hc3])
      | ok q3 =>
      obtain ⟨x, m4⟩ := q3
      dsimp only
      cases hc4 : apply names.length lim (applyFuel lim) BOp.and ctx x m4 with
      | error q => exact herr q.1 q.2 (by simp [decCompute, hc1, hc2, hc3, hc4])
      | ok q4 =>
      obtain ⟨d, m5⟩ := q4
      dsimp only
      have hpipe : pipeline t lim = .ok (.decided ctx s c d, finM names.length m5 ctx d) := by
        unfold pipeline; rw [hpl]; simp [hc0, hc1, hc2, hc3, hc4, finM]
      obtain ⟨i5f, _, dctx, dd⟩ := pipeline_decided hpipe
      have i5 : PCSDD.Inv names.length lim m5 := ⟨i5f.valid, i5f.size_le, i5f.ops_le, i5f.memo⟩
      have hok : decCompute names.length lim t.source t.candidate ctx m1 = .ok (s, c, d, m5) := by
        simp [decCompute, hc1, hc2, hc3, hc4]
      rw [hok] at hdc
      obtain ⟨env3, h3, e3, hs3, hc3', hd3, hy3, R5, F5⟩ := hdc
      rw [e3]
      simp only [seqF_normal]
      have hnb : ∀ y, ¬ (D.addOwn P).mut y → ¬ (D.addOwn P).base.mut y := fun y hm e =>
        hm (Addrs.base_mut e)
      have hA3 : hget h3 A = some (.dict vkvs) := by
        rw [F5.2 A (hget_lt hA1) (hnb _ hmA')]; exact hA1
      have hAS3 : hget h3 AS = some (.list as) := by
        rw [F5.2 AS (hget_lt hAS1) (hnb _ hmAS')]; exact hAS1
      have hR3 : hget h3 R = some (.dict kvs) := by rw [F5.2 R hR1lt hRbase]; exact hR1
      have hF3 : ∀ {f : BForm names.length} {v : V}, JFRel D h names v f → JFRel (D.addOwn P) h3 names v f :=
        fun hf => JFRel.frame (Frame.ofBase F5) _ _ (hF1 hf)
      have rp := jreport_sim ext (D := D.addOwn P) hnd t k env3 h3 m5 ctx d A AS R vkvs as vs vc kvs kts
        (by omega)
        (by rw [hy3 _ (by decide) (by decide) (by decide)]; simpa using hmg2) (by rw [hy3 _ (by decide) (by decide) (by decide)]; exact hctx2)
        (by rw [hd3])
        (by rw [hy3 _ (by decide) (by decide) (by decide)]; exact hval2)
        (by rw [hy3 _ (by decide) (by decide) (by decide)]; exact hres2)
        hA3 hmA' has hAS3 hmAS' hl (fun p hp => hF3 (hz p hp)) hs hc (hF3 hfs) (hF3 hfc) R5 i5
        (by simp [hRo]) (by simpa using r1) (by simpa using r2) (by simpa using r3) (by simpa using r4)
        hR3 (hkv1.frame (FrameS.of_frame (Frame.ofBase F5))) dctx hc0 dd
        (by
          have e5 := compile_wsteps _ _ _ _ hc1
          have e6 := compile_wsteps _ _ _ _ hc2
          have e7 := apply_wsteps _ _ _ _ _ _ _ hc3
          have e8 := apply_wsteps _ _ _ _ _ _ _ hc4
          simp only [Nat.add_mul] at hwsB; omega)
      obtain ⟨env4, h4, kvs4, e4, hy4, hR4, hkv4, R6, F6⟩ := rp
      rw [e4]
      simp only [seqF_normal]
      have g4 : ∀ y, y ≠ "world" → y ≠ "truths" → y ≠ "a" → y ≠ "b" → y ≠ "source" → y ≠ "candidate" →
          y ≠ "difference" → env4.get y = env2.get y := fun y a b c' d' e f g => by
        rw [hy4 y a b c' d', hy3 y e f g]
      obtain ⟨dd1, dR, dF, dRd⟩ := jdiag_sim ext (D := D.addOwn P) k env4 h4 (finM names.length m5 ctx d) R kvs4
        (some s) (some c) (some d) ctx
        (by rw [g4 _ (by decide) (by decide) (by decide) (by decide) (by decide) (by decide) (by decide)]; simpa using hmg2)
        (by rw [g4 _ (by decide) (by decide) (by decide) (by decide) (by decide) (by decide) (by decide)]; exact hres2)
        (by rw [hy4 _ (by decide) (by decide) (by decide) (by decide)]; exact hs3)
        (by rw [hy4 _ (by decide) (by decide) (by decide) (by decide)]; exact hc3')
        (by rw [hy4 _ (by decide) (by decide) (by decide) (by decide), hy3 _ (by decide) (by decide) (by decide)]; exact hctx2)
        (by rw [hy4 _ (by decide) (by decide) (by decide) (by decide)]; exact hd3)
        R6 (by simp [hRo]) (by simpa using r1) (by simpa using r2) (by simpa using r3) (by simpa using r4) hR4
      rw [execB_cons', dd1]
      simp only [seqF_normal, execB_nil_eq, JTryOut, bodyT]
      have F6B : FrameS (Big D h.length) h3 h4 := F6.mono (fun x e => by
        rcases Addrs.addOwn_mut e with e | e
        · exact Or.inl e
        · exact Or.inr (by omega))
      refine ⟨_, _, _, rfl, hget_hset_same _ (by simp; have := hget_lt hR4; omega), ?_,
        (JWorkOK.of_mrel dR).of_addOwn, ((FB1.trans (FbB F5)).trans F6B).trans (dF.mono (fun x e => by
          subst e; exact Or.inl (Or.inr (Or.inr (Or.inr (Or.inr hRo))))))⟩
      exact ReadsKV.jdictSet _ dRd _ _ ((hkv4.anti hRm').frame dF)

end PCSCR.Js
