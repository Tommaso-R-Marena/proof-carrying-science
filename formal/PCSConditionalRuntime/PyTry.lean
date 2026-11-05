import PCSConditionalRuntime.PyIncons

/-!
# `check`: the body of the `try` statement

```
premises = []; context = 1
for formula in value['assumptions']: ...           (premise loop)
source = candidate = difference = None
if context == 0: ...                               (inconsistent branch)
else: ...                                          (decided branch and report)
result['diagram'] = {...}
```
simulates `PCSDD.pipeline`: on success the result dictionary holds the reference fields, on
`ResourceLimit` the exception object carries the reference limit name and the result
dictionary is untouched.
-/

namespace PCSCR.Py

open PCSCR PCSDD PCSOmega

def tryBody : List S :=
  [S.assign [Tgt.name "premises"] (E.listD []),
   S.assign [Tgt.name "context"] (E.lit (V.int 1)),
   S.forIn (Tgt.name "formula") (E.sub (E.var "value") (E.lit (V.str "assumptions"))) premBody,
   S.assign [Tgt.name "source", Tgt.name "candidate", Tgt.name "difference"] (E.lit V.none),
   S.ifte (E.bin BinOp.eq (E.var "context") (E.lit (V.int 0))) incBody (decBodyA ++ repBody),
   diagS]

/-- The JSON fields after a successful pipeline body. -/
def bodyT (names : List String) (t : CTask names.length) (kts : List (String × T)) :
    Body names.length → Mgr → List (String × T)
  | .inconsistent _ core ws, m =>
      tset (incT names core ws kts) "diagram" (diagramT ⟨m.nodes, none, none, 0, none⟩)
  | .decided ctx s c d, m =>
      tset (repT names t m.nodes ctx d kts) "diagram" (diagramT ⟨m.nodes, some s, some c, ctx, some d⟩)

def TryOut (names : List String) (t : CTask names.length) (D : Addrs) (R : Nat) (h : Heap)
    (kvs : List (V × V)) (kts : List (String × T)) :
    Except (LimitReached × Mgr) (Body names.length × Mgr) → Out Flow → Prop
  | .ok (b, m), o => ∃ env' h' kvs', o = .ok (.normal env') h' ∧ hget h' R = some (.dict kvs') ∧
      ReadsKV (fun a => a = R) h' kvs' (bodyT names t kts b m) ∧ WorkOK D h' m ∧ FrameS (Big D h.length) h h'
  | .error (e, m), o => ∃ env' h' a, o = .ok (.raise (.obj (.ref a)) env') h' ∧
      hget h' a = some (.inst "ResourceLimit" [("args", .tup [.str e.name])]) ∧
      hget h' R = some (.dict kvs) ∧ WorkOK D h' m ∧ FrameS (Big D h.length) h h'

theorem seqF_assoc (x : Out Flow) (f g : Env → Heap → Out Flow) :
    seqF (seqF x f) g = seqF x (fun e h => seqF (f e h) g) := by
  rcases x with ⟨(_ | _ | _ | _), _⟩ | _ | _ <;> rfl

theorem execB_append (c : Ctx) (r : Lvl) (env : Env) (h : Heap) (a b : List S) :
    execB c r env h (a ++ b) = seqF (execB c r env h a) (fun e h' => execB c r e h' b) := by
  induction a generalizing env h with
  | nil => rfl
  | cons s ss ih =>
    simp only [List.cons_append, execB_cons', seqF_assoc]
    congr 1; funext e h'; exact ih e h'

theorem WorkOK.of_addOwn {D : Addrs} {N : Nat} {h : Heap} {m : Mgr} (w : WorkOK (D.addOwn N) h m) :
    WorkOK D h m :=
  ⟨by have := w.1; rwa [diagramFields_addOwn] at this, w.2⟩

theorem try_sim (ext : Ext) {names : List String} {lim : Limits} {D : Addrs} (hnd : names.Nodup)
    (t : CTask names.length) (k : Nat) (env : Env) (h : Heap) (A AS R : Nat)
    (vkvs : List (V × V)) (as : List V) (vs vc : V) (kvs : List (V × V)) (kts : List (String × T))
    (hk : applyFuel lim + fdepthL t.assumptions + fdepth t.source + fdepth t.candidate +
      2 * t.assumptions.length + names.length + 10 ≤ k)
    (hmg : env.get "manager" = some (.ref D.self)) (hval : env.get "value" = some (.ref A))
    (hres : env.get "result" = some (.ref R))
    (hA : hget h A = some (.dict vkvs)) (hmA : ¬ D.mut A)
    (has : dictFind .py vkvs (.str "assumptions") = some (.ref AS))
    (hAS : hget h AS = some (.list as)) (hmAS : ¬ D.mut AS) (hl : as.length = t.assumptions.length)
    (hz : ∀ p ∈ as.zip t.assumptions, FRel D h names p.1 p.2)
    (hs : dictFind .py vkvs (.str "source") = some vs) (hc : dictFind .py vkvs (.str "candidate") = some vc)
    (hfs : FRel D h names vs t.source) (hfc : FRel D h names vc t.candidate)
    (hR : MRel names lim D h Mgr.empty)
    (hRo : R ∈ D.own) (r1 : R ≠ D.self) (r2 : R ≠ D.nodes) (r3 : R ≠ D.uniq) (r4 : R ≠ D.memo)
    (hRk : hget h R = some (.dict kvs)) (hkv : ReadsKV (Big D h.length) h kvs kts) :
    TryOut names t D R h kvs kts (pipeline t lim)
      (execB (pyCtx ext) (interp (pyCtx ext) (k + 1)) env h tryBody) := by
  have hRlt := hget_lt hRk
  have hlt := hR.addrs_lt
  simp only [tryBody]
  pystepA []
  pystepA []
  generalize hPdef : h.length = P at *
  have RP : MRel names lim (D.addOwn P) (h ++ [Obj.list []]) Mgr.empty := by
    have := hR.addOwn (Obj.list []); rw [hPdef] at this; exact this
  have hmA' : ¬ (D.addOwn P).mut A := fun e => by
    rcases Addrs.addOwn_mut e with e | e
    · exact hmA e
    · have := hget_lt hA; omega
  have hmAS' : ¬ (D.addOwn P).mut AS := fun e => by
    rcases Addrs.addOwn_mut e with e | e
    · exact hmAS e
    · have := hget_lt hAS; omega
  have hFP : ∀ {n : Nat} {f : BForm n} {v : V}, FRel D h names v f →
      FRel (D.addOwn P) (h ++ [Obj.list []]) names v f := fun hf => by
    have := FRel.addOwn hf (Obj.list []); rw [hPdef] at this; exact this
  have pl := prem_loop ext (D := D.addOwn P) hnd AS P as (by simp) (by simp; omega) (by simp; omega)
    (by simp; omega) (by simp; omega) t.assumptions as k 0
    ((env.set "premises" (.ref P)).set "context" (.int 1)) (h ++ [Obj.list []]) Mgr.empty [] 1
    (by omega) (by rw [hget_append_lt_list _ (hget_lt hAS)]; exact hAS) hmAS' (by simp) hl
    (fun p hp => hFP (hz p hp)) (by simp [Env.get_set]) (by simp [Env.get_set, hmg]) (by simp [Env.get_set, iv])
    (by simp [hget, ← hPdef]) RP (Inv.empty _ _) (by simp [Mgr.empty]) (fun _ h => by simp at h)
  rw [execB_cons']
  conv in execS _ _ _ _ _ => simp [execS, evalE, bindS, Env.get_set, hval, hA, hget_append_lt_list _ (hget_lt hA),
    subOp, has, hashable]
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
    simp only [seqF_raise, TryOut]
    refine ⟨env1, h1, a1, rfl, ha1, ?_, (WorkOK.of_mrel R1).of_addOwn, FB0.trans (FPB F1)⟩
    rw [F1.2 R (by simp; omega) hRMP]; exact hR0
  | ok q =>
    obtain ⟨prs, ctx, m1⟩ := q
    rw [hpl] at pl
    obtain ⟨env1, h1, e1, hctx1, hy1, hP1, R1, F1⟩ := pl
    rw [e1]
    simp only [seqF_normal]
    obtain ⟨i1, ro1, d1, ⟨kk, hkk⟩, hfin⟩ := pipeline_premises hpl
    pystepA []
    have g1 : ∀ y, y ≠ "context" → y ≠ "formula" → y ≠ "premises" → y ≠ "source" → y ≠ "candidate" →
        y ≠ "difference" → (((env1.set "source" V.none).set "candidate" V.none).set "difference" V.none).get y =
          env.get y := fun y a b c d e f => by
      simp only [Env.get_set, Ne.symm d, Ne.symm e, Ne.symm f, if_false]
      rw [hy1 y a b]; simp [Env.get_set, Ne.symm a, Ne.symm c]
    generalize hE2 : ((env1.set "source" V.none).set "candidate" V.none).set "difference" V.none = env2 at g1
    have hctx2 : env2.get "context" = some (iv ctx) := by rw [← hE2]; simp [Env.get_set, hctx1]
    have hmg2 : env2.get "manager" = some (.ref D.self) := by
      rw [g1 _ (by decide) (by decide) (by decide) (by decide) (by decide) (by decide)]; exact hmg
    have hres2 : env2.get "result" = some (.ref R) := by
      rw [g1 _ (by decide) (by decide) (by decide) (by decide) (by decide) (by decide)]; exact hres
    have hval2 : env2.get "value" = some (.ref A) := by
      rw [g1 _ (by decide) (by decide) (by decide) (by decide) (by decide) (by decide)]; exact hval
    have hprem2 : env2.get "premises" = some (.ref P) := by
      rw [← hE2]; simp only [Env.get_set]; simp
      rw [hy1 _ (by decide) (by decide)]; simp [Env.get_set]
    have hsrc2 : env2.get "source" = some V.none := by rw [← hE2]; simp [Env.get_set]
    have hcand2 : env2.get "candidate" = some V.none := by rw [← hE2]; simp [Env.get_set]
    have hdif2 : env2.get "difference" = some V.none := by rw [← hE2]; simp [Env.get_set]
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
    simp [evalE, bindS, hctx2, binOp, eqD, eqPy, iv, truthy, num]
    by_cases hc0 : ctx = 0
    · subst hc0
      simp only [if_true]
      have hinc := incons_sim ext (D := D.addOwn P) hnd prs k env2 h1 m1 P R kvs kts (by omega) hprem2
        (by simpa using hmg2) hres2 hP1 hmPb R1 i1 ro1 (by simp [hRo]) (by simpa using r1) (by simpa using r2)
        (by simpa using r3) (by simpa using r4) hR1 hkv1
      have keep := fun y (hy : y ∉ bindsB incBody) => execB_keeps_interp (pyCtx ext) (k + 1) y incBody env2 h1 hy
      simp only [incCompute] at hinc
      cases hs : shrink names.length lim prs (List.range prs.length) (List.range prs.length) m1 with
      | error q =>
        obtain ⟨e, m2⟩ := q
        simp only [hs] at hinc
        obtain ⟨env3, h3, a3, e3, ha3, hR3, W3, F3⟩ := hinc
        rw [e3]
        simp only [seqF_raise, TryOut]
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
          simp only [seqF_raise, TryOut]
          exact ⟨env3, h3, a3, rfl, ha3, hR3, W3.of_addOwn, FB1.trans (hBig' F3)⟩
        | ok q =>
          obtain ⟨ws, m3⟩ := q
          simp only [hcw] at hinc
          obtain ⟨env3, h3, kvs3, N, e3, hN, hR3, hkv3, R3, F3⟩ := hinc
          have k1 := keep "manager" (by decide)
          have k2 := keep "result" (by decide)
          have k3 := keep "source" (by decide)
          have k4 := keep "candidate" (by decide)
          have k5 := keep "context" (by decide)
          have k6 := keep "difference" (by decide)
          rw [e3] at k1 k2 k3 k4 k5 k6
          simp only [FK] at k1 k2 k3 k4 k5 k6
          rw [e3]
          simp only [seqF_normal]
          obtain ⟨d1, dR, dF, dRd⟩ := diag_sim ext (D := (D.addOwn P).addOwn N) k env3 h3 m3 R kvs3 none none none 0
            (by rw [k1]; simpa using hmg2) (by rw [k2]; exact hres2) (by rw [k3]; exact hsrc2)
            (by rw [k4]; exact hcand2) (by rw [k5]; exact hctx2) (by rw [k6]; exact hdif2) R3
            (by simp [hRo]) (by simpa using r1) (by simpa using r2) (by simpa using r3) (by simpa using r4) hR3
          rw [execB_cons', d1]
          simp only [seqF_normal, execB_nil_eq, TryOut, bodyT]
          refine ⟨_, _, _, rfl, hget_hset_same _ (by simp; have := hget_lt hR3; omega), ?_,
            (WorkOK.of_mrel dR).of_addOwn.of_addOwn, (FB1.trans (hBig' F3)).trans (dF.mono (fun x e => by
              subst e; exact Or.inl (Or.inr (Or.inr (Or.inr (Or.inr hRo))))))⟩
          exact ReadsKV.dictSet _ dRd _ _ ((hkv3.anti hRm').frame dF)
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
      have hF1 : ∀ {f : BForm names.length} {v : V}, FRel D h names v f → FRel (D.addOwn P) h1 names v f :=
        fun hf => FRel.frame Fr1 _ _ (hFP hf)
      have hdc := dec_compute ext (D := D.addOwn P) hnd t.source t.candidate k env2 h1 m1 ctx A vkvs vs vc
        (by omega) (by simpa using hmg2) hval2 hctx2 hA1 hmA' hs hc (hF1 hfs) (hF1 hfc) R1 i1 d1.1
      have hRbase : ¬ (D.addOwn P).base.mut R := by simpa using hRb
      have hR1lt := hget_lt hR1
      have FbB : ∀ {X Y : Heap}, Frame (D.addOwn P).base X Y → FrameS (Big D h.length) X Y :=
        fun F => (FrameS.of_frame F).mono (fun x e => Or.inl (Addrs.base_mut (by simpa using e)))
      have herr : ∀ e m', decCompute names.length lim t.source t.candidate ctx m1 = .error (e, m') →
          TryOut names t D R h kvs kts (.error (e, m'))
            (seqF (seqF (execB (pyCtx ext) (interp (pyCtx ext) (k + 1)) env2 h1 decBodyA) fun env' h' =>
              execB (pyCtx ext) (interp (pyCtx ext) (k + 1)) env' h' repBody) fun env' h' =>
              execB (pyCtx ext) (interp (pyCtx ext) (k + 1)) env' h' [diagS]) := by
        intro e m' H
        rw [H] at hdc
        obtain ⟨env', h', a, e3, ha, R5, F5⟩ := hdc
        rw [e3]
        simp only [seqF_raise, TryOut]
        refine ⟨env', h', a, rfl, ha, ?_, (WorkOK.of_mrel R5).of_addOwn, FB1.trans (FbB F5)⟩
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
      have hF3 : ∀ {f : BForm names.length} {v : V}, FRel D h names v f → FRel (D.addOwn P) h3 names v f :=
        fun hf => FRel.frame (Frame.ofBase F5) _ _ (hF1 hf)
      have rp := report_sim ext (D := D.addOwn P) hnd t k env3 h3 m5 ctx d A AS R vkvs as vs vc kvs kts
        (by omega)
        (by rw [hy3 _ (by decide) (by decide) (by decide)]; simpa using hmg2) (by rw [hy3 _ (by decide) (by decide) (by decide)]; exact hctx2)
        (by rw [hd3])
        (by rw [hy3 _ (by decide) (by decide) (by decide)]; exact hval2)
        (by rw [hy3 _ (by decide) (by decide) (by decide)]; exact hres2)
        hA3 hmA' has hAS3 hmAS' hl (fun p hp => hF3 (hz p hp)) hs hc (hF3 hfs) (hF3 hfc) R5 i5
        (by simp [hRo]) (by simpa using r1) (by simpa using r2) (by simpa using r3) (by simpa using r4)
        hR3 (hkv1.frame (FrameS.of_frame (Frame.ofBase F5))) dctx hc0 dd
      obtain ⟨env4, h4, kvs4, e4, hy4, hR4, hkv4, R6, F6⟩ := rp
      rw [e4]
      simp only [seqF_normal]
      have g4 : ∀ y, y ≠ "world" → y ≠ "truths" → y ≠ "a" → y ≠ "b" → y ≠ "source" → y ≠ "candidate" →
          y ≠ "difference" → env4.get y = env2.get y := fun y a b c' d' e f g => by
        rw [hy4 y a b c' d', hy3 y e f g]
      obtain ⟨dd1, dR, dF, dRd⟩ := diag_sim ext (D := D.addOwn P) k env4 h4 (finM names.length m5 ctx d) R kvs4
        (some s) (some c) (some d) ctx
        (by rw [g4 _ (by decide) (by decide) (by decide) (by decide) (by decide) (by decide) (by decide)]; simpa using hmg2)
        (by rw [g4 _ (by decide) (by decide) (by decide) (by decide) (by decide) (by decide) (by decide)]; exact hres2)
        (by rw [hy4 _ (by decide) (by decide) (by decide) (by decide)]; exact hs3)
        (by rw [hy4 _ (by decide) (by decide) (by decide) (by decide)]; exact hc3')
        (by rw [hy4 _ (by decide) (by decide) (by decide) (by decide), hy3 _ (by decide) (by decide) (by decide)]; exact hctx2)
        (by rw [hy4 _ (by decide) (by decide) (by decide) (by decide)]; exact hd3)
        R6 (by simp [hRo]) (by simpa using r1) (by simpa using r2) (by simpa using r3) (by simpa using r4) hR4
      rw [execB_cons', dd1]
      simp only [seqF_normal, execB_nil_eq, TryOut, bodyT]
      have F6B : FrameS (Big D h.length) h3 h4 := F6.mono (fun x e => by
        rcases Addrs.addOwn_mut e with e | e
        · exact Or.inl e
        · exact Or.inr (by omega))
      refine ⟨_, _, _, rfl, hget_hset_same _ (by simp; have := hget_lt hR4; omega), ?_,
        (WorkOK.of_mrel dR).of_addOwn, ((FB1.trans (FbB F5)).trans F6B).trans (dF.mono (fun x e => by
          subst e; exact Or.inl (Or.inr (Or.inr (Or.inr (Or.inr hRo))))))⟩
      exact ReadsKV.dictSet _ dRd _ _ ((hkv4.anti hRm').frame dF)

end PCSCR.Py
