import PCSConditionalRuntime.JsReport
import PCSConditionalRuntime.PyIncons

/-!
# `checkConditional`: the inconsistent-assumptions branch

```
let core=premises.map((_,i)=>i);for(const i of [...core]){ … }        (`jshrink_loop`)
const necessities=core.map(i=>{ … });                                 (`jwits_loop`)
Object.assign(r,{decision:'inconsistent_assumptions',unsat_core:core,core_necessity_witnesses:necessities});
```
-/

namespace PCSCR.Js

open PCSCR PCSDD PCSOmega PCSCR.Py

/-- What `m.work()` reads. -/
def JWorkOK (D : Addrs) (h : Heap) (m : Mgr) : Prop :=
  hget h D.self = some (.inst "Diagram" (jdiagramFields D m)) ∧
    ∃ ptrs, hget h D.nodes = some (.list ptrs) ∧ ptrs.length = m.nodes.size

theorem JWorkOK.of_mrel {names : List String} {lim : Limits} {D : Addrs} {h : Heap} {m : Mgr}
    (hR : JMRel names lim D h m) : JWorkOK D h m := by
  obtain ⟨ptrs, hp, hl, _⟩ := hR.nodes
  exact ⟨hR.self, ptrs, hp, hl⟩

theorem JWorkOK.of_mrel_addOwn {names : List String} {lim : Limits} {D : Addrs} {N : Nat} {h : Heap} {m : Mgr}
    (hR : JMRel names lim (D.addOwn N) h m) : JWorkOK D h m := by
  obtain ⟨ptrs, hp, hl, _⟩ := hR.nodes
  exact ⟨by have := hR.self; rwa [jdiagramFields_addOwn] at this, ptrs, hp, hl⟩

theorem shrink_wsteps {n : Nat} {lim : Limits} (prs : List (Nat × BForm n)) :
    ∀ (is core : List Nat) (m : Mgr) core' (m' : Mgr),
      shrink n lim prs core is m = .ok (core', m') → m'.wsteps = m.wsteps
  | [], core, m, core', m', h => by simp only [shrink] at h; cases h; rfl
  | i :: is, core, m, core', m', h => by
      simp only [shrink] at h
      split at h
      · cases h
      rename_i c m1 h1
      split at h
      · rw [shrink_wsteps prs is _ _ core' m' h, conjList_wsteps _ _ _ _ _ h1]
      · rw [shrink_wsteps prs is core _ core' m' h, conjList_wsteps _ _ _ _ _ h1]

def jincBody : List S :=
  [S.assign [Tgt.name "core"] (E.comp (E.var "i") "i" (E.call "%indices" [E.var "premises"]) none),
   S.forIn (Tgt.name "i#2") (E.call "%spread" [E.var "core"]) jshrinkBody,
   S.assign [Tgt.name "necessities"] (E.listD []),
   S.forIn (Tgt.name "i#3") (E.var "core") jwitsBody,
   S.expr (E.kwcall (E.var "r") "update" ["decision", "unsat_core", "core_necessity_witnesses"]
     [E.lit (V.str "inconsistent_assumptions"), E.var "core", E.var "necessities"])]

def JIncOut (names : List String) (lim : Limits) (D : Addrs) (R : Nat) (h : Heap) (kvs : List (V × V))
    (kts : List (String × T)) :
    Except (LimitReached × Mgr) (List Nat × List (Nat × List Bool) × Mgr) → Out Flow → Prop
  | .ok (core, ws, m3), o => ∃ env' h' kvs' N, o = .ok (.normal env') h' ∧ h.length ≤ N ∧
      hget h' R = some (.dict kvs') ∧ ReadsKV D.mut h' kvs' (incT names core ws kts) ∧
      JMRel names lim (D.addOwn N) h' m3 ∧ FrameS (Big D h.length) h h'
  | .error (e, m'), o => ∃ env' h' a, o = .ok (.raise (.obj (.ref a)) env') h' ∧
      hget h' a = some (.inst "ResourceLimit" [("message", .str e.name)]) ∧
      hget h' R = some (.dict kvs) ∧ JWorkOK D h' m' ∧ FrameS (Big D h.length) h h'

theorem jincons_sim (ext : Ext) {names : List String} {lim : Limits} {D : Addrs} (hnd : names.Nodup)
    (prs : List (Nat × BForm names.length)) (k : Nat) (env : Env) (h : Heap) (m1 : Mgr) (P R : Nat)
    (kvs : List (V × V)) (kts : List (String × T))
    (hk : applyFuel lim + 2 * prs.length + names.length + 6 ≤ k)
    (hp : env.get "premises" = some (.ref P)) (hmg : env.get "m" = some (.ref D.self))
    (hres : env.get "r" = some (.ref R))
    (hP : hget h P = some (.list (prs.map (fun p => iv p.1)))) (hmP : ¬ D.base.mut P)
    (hR : JMRel names lim D h m1) (hinv : Inv names.length lim m1) (hroots : RootsOK m1 prs)
    (hRo : R ∈ D.own) (r1 : R ≠ D.self) (r2 : R ≠ D.nodes) (r3 : R ≠ D.uniq) (r4 : R ≠ D.memo)
    (hRk : hget h R = some (.dict kvs)) (hkv : ReadsKV D.mut h kvs kts)
    (hws : m1.wsteps + prs.length * names.length ≤ 9007199254740991) :
    JIncOut names lim D R h kvs kts (incCompute names.length lim prs m1)
      (execB (jsCtx ext) (interp (jsCtx ext) (k + 1)) env h jincBody) := by
  have hPlt := hget_lt hP
  have hRlt := hget_lt hRk
  have hRb : ¬ D.base.mut R := by
    simp only [Addrs.mut, Addrs.base_self, Addrs.base_nodes, Addrs.base_uniq, Addrs.base_memo,
      Addrs.base_own, List.not_mem_nil, or_false]; omega
  simp only [jincBody]
  have hci := jcomp_indices ext (k + 1) env h P _ hp hP (by simp; omega)
  rw [execB_cons']
  simp only [execS, bindS, hci, assignAll, assignT, bindE, Out.bind, seqF_normal]
  have hlcs : lookupClass jsProg "%spread" = none := by rfl
  rw [execB_cons']
  conv in execS _ _ _ _ _ => simp [execS, evalE, evalL, bindS, Env.get_set, builtin, builtinJs, elems, hget, hlcs]
  generalize hL : List.map iv (List.range prs.length) = L
  have hLiv : L = (List.range prs.length).map iv := by rw [← hL]
  have hR0 : JMRel names lim D (h ++ [Obj.list L, Obj.list L]) m1 := by
    have := (hR.append (Obj.list L)).append (Obj.list L); simpa using this
  have hmC : ¬ D.mut h.length := jfresh_not_mut hR (Nat.le_refl _)
  have hmI : ¬ D.mut (h.length + 1) := jfresh_not_mut hR (by omega)
  have hprs : ∀ p ∈ prs, p.1 < m1.nodes.size + 2 := fun p hp => (hroots p hp).1
  have sh := jshrink_loop ext (D := D) P (h.length + 1) prs L (List.range prs.length) k 0
    (env.set "core" (.ref h.length)) (h ++ [Obj.list L, Obj.list L]) m1 (List.range prs.length) h.length
    (by simp; omega) (by simp [hget]) (fun e => hmI (Addrs.base_mut e)) (by simp [hLiv])
    (by simp [Env.get_set, hp]) (by simp [Env.get_set, hmg]) (by simp [Env.get_set])
    (by simp [hget, hLiv]) hmC (by rw [hget_append_lt_list _ hPlt]; exact hP) hmP
    (fun c hc => by simpa using hc) (by simp) hR0 hinv hprs
  simp only [incCompute]
  cases hs : shrink names.length lim prs (List.range prs.length) (List.range prs.length) m1 with
  | error q =>
    obtain ⟨e, m2⟩ := q
    rw [hs] at sh
    obtain ⟨env1, h1, a1, e1, ha1, R1, F1⟩ := sh
    rw [e1]
    simp only [seqF_raise, JIncOut]
    refine ⟨env1, h1, a1, rfl, ha1, ?_, JWorkOK.of_mrel R1, ?_⟩
    · rw [F1.2 R (by simp; omega) hRb, hget_append_lt_list _ hRlt]; exact hRk
    · exact (FrameS.append2 _ _ _ _).trans (FrameS.big_of_base F1)
  | ok q =>
    obtain ⟨core, m2⟩ := q
    rw [hs] at sh
    obtain ⟨env1, h1, C1, e1, hc1, hC1, hmC1, hy1, R1, F1⟩ := sh
    rw [e1]
    simp only [seqF_normal]
    obtain ⟨i2, ex2, sub2, _, mins2⟩ := shrink_spec prs _ _ m1 core m2 hinv hroots hs
    have hsl := shrink_sublist prs _ _ m1 core m2 hs
    have hcl : ∀ c ∈ core, c < prs.length := fun c hc => by simpa using sub2 c hc
    have hcn : core.length ≤ prs.length := by have := hsl.length_le; simpa using this
    have hmin : ∀ i ∈ core, ∃ ρ, SatSet prs (core.filter (· != i)) ρ :=
      fun i hi => mins2 i (sub2 i hi) hi
    have hl1 : (h ++ [Obj.list L, Obj.list L]).length ≤ h1.length := F1.1
    simp only [List.length_append, List.length_cons, List.length_nil] at hl1
    have hC1l := hget_lt hC1
    have hP1 : hget h1 P = some (.list (prs.map (fun p => iv p.1))) := by
      rw [F1.2 P (by simp; omega) hmP, hget_append_lt_list _ hPlt]; exact hP
    have hR1R : hget h1 R = some (.dict kvs) := by
      rw [F1.2 R (by simp; omega) hRb, hget_append_lt_list _ hRlt]; exact hRk
    jsstepA [hy1, hmg]
    have hcore1 : env1.get "core" = some (.ref C1) := hc1
    rw [execB_cons']
    conv in execS _ _ _ _ _ => simp [execS, evalE, bindS, Env.get_set, hcore1]
    generalize hN : h1.length = N at *
    have hNl : N = h1.length := hN.symm
    have hlt := R1.addrs_lt
    have RN : JMRel names lim (D.addOwn N) (h1 ++ [Obj.list []]) m2 := by
      have := R1.addOwn (Obj.list []); rw [hN] at this; exact this
    have hmCN : ¬ (D.addOwn N).mut C1 := fun e => by
      rcases Addrs.addOwn_mut e with e | e
      · exact hmC1 e
      · omega
    have hw := jwits_loop ext hnd P N C1 prs core hmin hcl hcn (by simp) (by simp; omega) (by simp; omega)
      (by simp; omega) (by simp; omega) (by omega) core k 0 (env1.set "necessities" (.ref N))
      (h1 ++ [Obj.list []]) m2 [] (by omega)
      (by rw [hget_append_lt_list _ (by omega)]; exact hC1) hmCN (by simp) (fun _ h => h)
      (by simp [Env.get_set]; rw [hy1 _ (by decide) (by decide) (by decide)]; simp [Env.get_set, hp])
      (by simp [Env.get_set]; rw [hy1 _ (by decide) (by decide) (by decide)]; simp [Env.get_set, hmg])
      (by simp [Env.get_set, hcore1]) (by simp [Env.get_set])
      (by rw [hget_append_lt_list _ (hget_lt hP1)]; exact hP1) (by simpa using hmP)
      (by rw [hNl]; simp [hget]) RN i2 (hroots.extend hinv ex2)
      (by have e := shrink_wsteps prs _ _ m1 core m2 hs; have := Nat.mul_le_mul_right names.length hcn; omega)
    have hRN : R ≠ N := by omega
    have hRMP : ¬ MutP (D.addOwn N) N R := fun e => by
      rcases e with e | e
      · exact hRb (by simpa using e)
      · exact hRN e
    have FB1 : FrameS (Big D h.length) h (h1 ++ [Obj.list []]) :=
      ((FrameS.append2 _ _ _ _).trans (FrameS.big_of_base F1)).trans (FrameS.append _ _ _)
    have FBN : ∀ {X Y : Heap}, FrameS (MutP (D.addOwn N) N) X Y → FrameS (Big D h.length) X Y :=
      fun F => F.mono (fun x e => by
        rcases e with e | e
        · exact Or.inl (Addrs.base_mut (by simpa using e))
        · exact Or.inr (by omega))
    have hR2 : hget (h1 ++ [Obj.list []]) R = some (.dict kvs) := by
      rw [hget_append_lt_list _ (by omega)]; exact hR1R
    cases hcw : coreWits names.length lim prs core core m2 with
    | error q =>
      obtain ⟨e, m3⟩ := q
      rw [hcw] at hw
      obtain ⟨env3, h3, a3, e3, ha3, R3, F3⟩ := hw
      rw [e3]
      simp only [seqF_raise, JIncOut]
      refine ⟨env3, h3, a3, rfl, ha3, ?_, JWorkOK.of_mrel_addOwn R3, FB1.trans (FBN F3)⟩
      rw [F3.2 R (by simp; omega) hRMP]; exact hR2
    | ok q =>
      obtain ⟨ws, m3⟩ := q
      rw [hcw] at hw
      obtain ⟨env3, h3, ds, e3, hN3, hds, hy3, R3, F3⟩ := hw
      rw [e3]
      simp only [seqF_normal]
      have g : ∀ y, y ≠ "i#3" → y ≠ "assignment" → y ≠ "necessities" → y ≠ "core" → y ≠ "i#2" →
          y ≠ "remaining" → env3.get y = env.get y := fun y a b c d i e => by
        rw [hy3 y a b]; simp only [Env.get_set, Ne.symm c, if_false]
        rw [hy1 y d i e]; simp [Env.get_set, Ne.symm d]
      have hres3 : env3.get "r" = some (.ref R) := by
        rw [g "r" (by decide) (by decide) (by decide) (by decide) (by decide) (by decide)]; exact hres
      have hcore3 : env3.get "core" = some (.ref C1) := by
        rw [hy3 "core" (by decide) (by decide)]; simp [Env.get_set, hcore1]
      have hnec3 : env3.get "necessities" = some (.ref N) := by
        rw [hy3 "necessities" (by decide) (by decide)]; simp [Env.get_set]
      have hR3 : hget h3 R = some (.dict kvs) := by rw [F3.2 R (by simp; omega) hRMP]; exact hR2
      have hR3l := hget_lt hR3
      jsstepA [hres3, hcore3, hnec3, hR3, hR3l, updateKw, pairUp]
      simp only [JIncOut]
      obtain ⟨RF, FF⟩ := R3.hsetOwn (a := R) (by simp [hRo]) r1 r2 r3 r4
        (Obj.dict (dictSet .js (dictSet .js (dictSet .js kvs (.str "decision") (.str "inconsistent_assumptions"))
          (.str "unsat_core") (.ref C1)) (.str "core_necessity_witnesses") (.ref N)))
      have FBall : FrameS (Big D h.length) h (hset h3 R
          (Obj.dict (dictSet .js (dictSet .js (dictSet .js kvs (.str "decision") (.str "inconsistent_assumptions"))
            (.str "unsat_core") (.ref C1)) (.str "core_necessity_witnesses") (.ref N)))) :=
        (FB1.trans (FBN F3)).trans (FrameS.hset _ _ (Or.inl (Or.inr (Or.inr (Or.inr (Or.inr hRo))))))
      refine ⟨_, _, _, N, rfl, by omega, hget_hset_same _ hR3l, ?_, RF, FBall⟩
      have hmN : ¬ D.mut N := jfresh_not_mut R1 (by omega)
      have hNlt3 : N < h3.length := hget_lt hN3
      simp only [incT, witsT_eq]
      refine ReadsKV.jdictSet _ ?_ _ _ (ReadsKV.jdictSet _ ?_ _ _ (ReadsKV.jdictSet _ (ReadsM.str _ _ _) _ _
        (hkv.frameBig FBall)))
      · refine ReadsM.list (vs := ds) ?_ hmN ?_
        · rw [hget_hset_ne _ (by omega)]; simpa using hN3
        · exact (hds.anti (fun a e => Addrs.mut_addOwn e)).frame
            (FrameS.hset _ _ (Or.inr (Or.inr (Or.inr (Or.inr hRo)))))
      · refine ReadsM.list (vs := core.map iv) ?_ hmC1 (readsL_ints _ _ _)
        have hRC : R ≠ C1 := fun e => hmC1 (e ▸ Or.inr (Or.inr (Or.inr (Or.inr hRo))))
        rw [hget_hset_ne _ hRC, F3.2 C1 (by simp; omega) ?_, hget_append_lt_list _ (by omega)]
        · exact hC1
        · intro e; rcases e with e | e
          · exact hmC1 (Addrs.base_mut (by simpa using e))
          · omega

end PCSCR.Js
