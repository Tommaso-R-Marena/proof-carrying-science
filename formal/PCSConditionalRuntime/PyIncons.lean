import PCSConditionalRuntime.PyReport
import PCSConditionalRuntime.EnvKeep

/-!
# `check`: the inconsistent-assumptions branch

```
core = list(range(len(premises)))
for i in list(core):
    remaining = [j for j in core if j != i]
    if manager.conjunction([premises[j] for j in remaining]) == 0: core = remaining
necessities = []
for i in core:
    world = manager.world(manager.conjunction([premises[j] for j in core if j != i]))
    assert world is not None
    necessities.append({'removed_assumption': i, 'assignment': world})
result.update(decision='inconsistent_assumptions', unsat_core=core, core_necessity_witnesses=necessities)
```
-/

namespace PCSCR.Py

open PCSCR PCSDD PCSOmega

/-- Addresses that `check` may still overwrite, together with everything allocated after `B`. -/
def Big (D : Addrs) (B : Nat) (a : Nat) : Prop := D.mut a ∨ B ≤ a

/-- What `manager.work()` reads. -/
def WorkOK (D : Addrs) (h : Heap) (m : Mgr) : Prop :=
  hget h D.self = some (.inst "Diagram" (diagramFields D m)) ∧
    ∃ ptrs, hget h D.nodes = some (.list ptrs) ∧ ptrs.length = m.nodes.size

theorem WorkOK.of_mrel {names : List String} {lim : Limits} {D : Addrs} {h : Heap} {m : Mgr}
    (hR : MRel names lim D h m) : WorkOK D h m := by
  obtain ⟨ptrs, hp, hl, _⟩ := hR.nodes
  exact ⟨hR.self, ptrs, hp, hl⟩

theorem WorkOK.of_mrel_addOwn {names : List String} {lim : Limits} {D : Addrs} {N : Nat} {h : Heap} {m : Mgr}
    (hR : MRel names lim (D.addOwn N) h m) : WorkOK D h m := by
  obtain ⟨ptrs, hp, hl, _⟩ := hR.nodes
  exact ⟨by have := hR.self; rwa [diagramFields_addOwn] at this, ptrs, hp, hl⟩

theorem ReadsKV.frameBig {M : Nat → Prop} {h h' : Heap} (F : FrameS (fun a => M a ∨ h.length ≤ a) h h')
    {kvs : List (V × V)} {kts : List (String × T)} (r : ReadsKV M h kvs kts) : ReadsKV M h' kvs kts :=
  r.transport (fun a o hm hg => ⟨hm, by
    rw [F.2 a (hget_lt hg) (fun e => by rcases e with e | e; exact hm e; have := hget_lt hg; omega)]; exact hg⟩)

theorem ReadsM.frameBig {M : Nat → Prop} {h h' : Heap} (F : FrameS (fun a => M a ∨ h.length ≤ a) h h')
    {v : V} {t : T} (r : ReadsM M h v t) : ReadsM M h' v t :=
  r.transport (fun a o hm hg => ⟨hm, by
    rw [F.2 a (hget_lt hg) (fun e => by rcases e with e | e; exact hm e; have := hget_lt hg; omega)]; exact hg⟩)

theorem shrink_sublist {n : Nat} {lim : Limits} (prs : List (Nat × BForm n)) :
    ∀ (is core : List Nat) (m : Mgr) core' (m' : Mgr),
      shrink n lim prs core is m = .ok (core', m') → core'.Sublist core
  | [], core, m, core', m', h => by simp only [shrink] at h; cases h; exact List.Sublist.refl _
  | i :: is, core, m, core', m', h => by
      simp only [shrink] at h
      split at h
      · cases h
      split at h
      · exact (shrink_sublist prs is _ _ core' m' h).trans (List.filter_sublist)
      · exact shrink_sublist prs is core _ core' m' h

theorem Addrs.mut_addOwn {D : Addrs} {N a : Nat} (e : D.mut a) : (D.addOwn N).mut a := by
  rcases e with e | e | e | e | e
  · exact Or.inl e
  · exact Or.inr (Or.inl e)
  · exact Or.inr (Or.inr (Or.inl e))
  · exact Or.inr (Or.inr (Or.inr (Or.inl e)))
  · exact Or.inr (Or.inr (Or.inr (Or.inr (List.mem_cons_of_mem _ e))))

theorem FrameS.big_of_base {D : Addrs} {B : Nat} {X Y : Heap} (F : Frame D.base X Y) : FrameS (Big D B) X Y :=
  (FrameS.of_frame F).mono (fun _ e => Or.inl (Addrs.base_mut e))

theorem FrameS.append2 (Sm : Nat → Prop) (h : Heap) (o1 o2 : Obj) : FrameS Sm h (h ++ [o1, o2]) := by
  have := (FrameS.append Sm h o1).trans (FrameS.append Sm _ o2); simpa using this

theorem readsL_ints (M : Nat → Prop) (h : Heap) :
    ∀ cs : List Nat, ReadsL M h (cs.map iv) (cs.map natT)
  | [] => ReadsL.nil _ _
  | _ :: cs => ReadsL.cons (ReadsM.int _ _ _) (readsL_ints M h cs)

def incBody : List S :=
  [S.assign [Tgt.name "core"] (E.call "list" [E.call "range" [E.call "len" [E.var "premises"]]]),
   S.forIn (Tgt.name "i") (E.call "list" [E.var "core"]) shrinkBody,
   S.assign [Tgt.name "necessities"] (E.listD []),
   S.forIn (Tgt.name "i") (E.var "core") witsBody,
   S.expr (E.kwcall (E.var "result") "update" ["decision", "unsat_core", "core_necessity_witnesses"]
     [E.lit (V.str "inconsistent_assumptions"), E.var "core", E.var "necessities"])]

/-- The two manager phases of the inconsistent branch of `PCSDD.pipeline`. -/
def incCompute (n : Nat) (lim : Limits) (prs : List (Nat × BForm n)) (m1 : Mgr) :
    Except (LimitReached × Mgr) (List Nat × List (Nat × List Bool) × Mgr) :=
  match shrink n lim prs (List.range prs.length) (List.range prs.length) m1 with
  | .error e => .error e
  | .ok (core, m2) => match coreWits n lim prs core core m2 with
    | .error e => .error e
    | .ok (ws, m3) => .ok (core, ws, m3)

/-- The JSON fields after the branch. -/
def incT (names : List String) (core : List Nat) (ws : List (Nat × List Bool)) (kts : List (String × T)) :
    List (String × T) :=
  tset (tset (tset kts "decision" (decisionT .inconsistentAssumptions)) "unsat_core" (.arr (core.map natT)))
    "core_necessity_witnesses" (witsT names ws)

def IncOut (names : List String) (lim : Limits) (D : Addrs) (R : Nat) (h : Heap) (kvs : List (V × V))
    (kts : List (String × T)) :
    Except (LimitReached × Mgr) (List Nat × List (Nat × List Bool) × Mgr) → Out Flow → Prop
  | .ok (core, ws, m3), o => ∃ env' h' kvs' N, o = .ok (.normal env') h' ∧ h.length ≤ N ∧
      hget h' R = some (.dict kvs') ∧ ReadsKV D.mut h' kvs' (incT names core ws kts) ∧
      MRel names lim (D.addOwn N) h' m3 ∧ FrameS (Big D h.length) h h'
  | .error (e, m'), o => ∃ env' h' a, o = .ok (.raise (.obj (.ref a)) env') h' ∧
      hget h' a = some (.inst "ResourceLimit" [("args", .tup [.str e.name])]) ∧
      hget h' R = some (.dict kvs) ∧ WorkOK D h' m' ∧ FrameS (Big D h.length) h h'

theorem incons_sim (ext : Ext) {names : List String} {lim : Limits} {D : Addrs} (hnd : names.Nodup)
    (prs : List (Nat × BForm names.length)) (k : Nat) (env : Env) (h : Heap) (m1 : Mgr) (P R : Nat)
    (kvs : List (V × V)) (kts : List (String × T))
    (hk : applyFuel lim + 2 * prs.length + names.length + 6 ≤ k)
    (hp : env.get "premises" = some (.ref P)) (hmg : env.get "manager" = some (.ref D.self))
    (hres : env.get "result" = some (.ref R))
    (hP : hget h P = some (.list (prs.map (fun p => iv p.1)))) (hmP : ¬ D.base.mut P)
    (hR : MRel names lim D h m1) (hinv : Inv names.length lim m1) (hroots : RootsOK m1 prs)
    (hRo : R ∈ D.own) (r1 : R ≠ D.self) (r2 : R ≠ D.nodes) (r3 : R ≠ D.uniq) (r4 : R ≠ D.memo)
    (hRk : hget h R = some (.dict kvs)) (hkv : ReadsKV D.mut h kvs kts) :
    IncOut names lim D R h kvs kts (incCompute names.length lim prs m1)
      (execB (pyCtx ext) (interp (pyCtx ext) (k + 1)) env h incBody) := by
  have hPlt := hget_lt hP
  have hRlt := hget_lt hRk
  have hRb : ¬ D.base.mut R := by
    simp only [Addrs.mut, Addrs.base_self, Addrs.base_nodes, Addrs.base_uniq, Addrs.base_memo,
      Addrs.base_own, List.not_mem_nil, or_false]; omega
  simp only [incBody]
  pystepA [hp, hP]
  rw [execB_cons']
  conv in execS _ _ _ _ _ => simp [execS, evalE, evalL, bindS, Env.get_set, builtin, elems, hget]
  generalize hL : List.map (fun i : Nat => V.int (i : Int)) (List.range prs.length) = L
  have hLiv : L = (List.range prs.length).map iv := by rw [← hL]; rfl
  have hR0 : MRel names lim D (h ++ [Obj.list L, Obj.list L]) m1 := by
    have := (hR.append (Obj.list L)).append (Obj.list L); simpa using this
  have hmC : ¬ D.mut h.length := fresh_not_mut hR (Nat.le_refl _)
  have hmI : ¬ D.mut (h.length + 1) := fresh_not_mut hR (by omega)
  have hprs : ∀ p ∈ prs, p.1 < m1.nodes.size + 2 := fun p hp => (hroots p hp).1
  have sh := shrink_loop ext (D := D) P (h.length + 1) prs L (List.range prs.length) k 0
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
    simp only [seqF_raise, IncOut]
    refine ⟨env1, h1, a1, rfl, ha1, ?_, WorkOK.of_mrel R1, ?_⟩
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
    pystepA [hy1, hmg]
    have hcore1 : env1.get "core" = some (.ref C1) := hc1
    rw [execB_cons']
    conv in execS _ _ _ _ _ => simp [execS, evalE, bindS, Env.get_set, hcore1]
    generalize hN : h1.length = N at *
    have hNl : N = h1.length := hN.symm
    have hlt := R1.addrs_lt
    have RN : MRel names lim (D.addOwn N) (h1 ++ [Obj.list []]) m2 := by
      have := R1.addOwn (Obj.list []); rw [hN] at this; exact this
    have hmCN : ¬ (D.addOwn N).mut C1 := fun e => by
      rcases Addrs.addOwn_mut e with e | e
      · exact hmC1 e
      · omega
    have hw := wits_loop ext hnd P N C1 prs core hmin hcl hcn (by simp) (by simp; omega) (by simp; omega)
      (by simp; omega) (by simp; omega) (by omega) core k 0 (env1.set "necessities" (.ref N))
      (h1 ++ [Obj.list []]) m2 [] (by omega)
      (by rw [hget_append_lt_list _ (by omega)]; exact hC1) hmCN (by simp) (fun _ h => h)
      (by simp [Env.get_set]; rw [hy1 _ (by decide) (by decide) (by decide)]; simp [Env.get_set, hp])
      (by simp [Env.get_set]; rw [hy1 _ (by decide) (by decide) (by decide)]; simp [Env.get_set, hmg])
      (by simp [Env.get_set, hcore1]) (by simp [Env.get_set])
      (by rw [hget_append_lt_list _ (hget_lt hP1)]; exact hP1) (by simpa using hmP)
      (by rw [hNl]; simp [hget]) RN i2 (hroots.extend hinv ex2)
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
      simp only [seqF_raise, IncOut]
      refine ⟨env3, h3, a3, rfl, ha3, ?_, WorkOK.of_mrel_addOwn R3, FB1.trans (FBN F3)⟩
      rw [F3.2 R (by simp; omega) hRMP]; exact hR2
    | ok q =>
      obtain ⟨ws, m3⟩ := q
      rw [hcw] at hw
      obtain ⟨env3, h3, ds, e3, hN3, hds, hy3, R3, F3⟩ := hw
      rw [e3]
      simp only [seqF_normal]
      have g : ∀ y, y ≠ "i" → y ≠ "world" → y ≠ "necessities" → y ≠ "core" → y ≠ "remaining" →
          env3.get y = env.get y := fun y a b c d e => by
        rw [hy3 y a b]; simp only [Env.get_set, Ne.symm c, if_false]
        rw [hy1 y d a e]; simp [Env.get_set, Ne.symm d]
      have hres3 : env3.get "result" = some (.ref R) := by
        rw [g "result" (by decide) (by decide) (by decide) (by decide) (by decide)]; exact hres
      have hcore3 : env3.get "core" = some (.ref C1) := by
        rw [hy3 "core" (by decide) (by decide)]; simp [Env.get_set, hcore1]
      have hnec3 : env3.get "necessities" = some (.ref N) := by
        rw [hy3 "necessities" (by decide) (by decide)]; simp [Env.get_set]
      have hR3 : hget h3 R = some (.dict kvs) := by rw [F3.2 R (by simp; omega) hRMP]; exact hR2
      have hR3l := hget_lt hR3
      pystepA [hres3, hcore3, hnec3, hR3, hR3l, updateKw, pairUp]
      simp only [IncOut]
      obtain ⟨RF, FF⟩ := R3.hsetOwn (a := R) (by simp [hRo]) r1 r2 r3 r4
        (Obj.dict (dictSet .py (dictSet .py (dictSet .py kvs (.str "decision") (.str "inconsistent_assumptions"))
          (.str "unsat_core") (.ref C1)) (.str "core_necessity_witnesses") (.ref N)))
      have FBall : FrameS (Big D h.length) h (hset h3 R
          (Obj.dict (dictSet .py (dictSet .py (dictSet .py kvs (.str "decision") (.str "inconsistent_assumptions"))
            (.str "unsat_core") (.ref C1)) (.str "core_necessity_witnesses") (.ref N)))) :=
        (FB1.trans (FBN F3)).trans (FrameS.hset _ _ (Or.inl (Or.inr (Or.inr (Or.inr (Or.inr hRo))))))
      refine ⟨_, _, _, N, rfl, by omega, hget_hset_same _ hR3l, ?_, RF, FBall⟩
      have hmN : ¬ D.mut N := fresh_not_mut R1 (by omega)
      have hNlt3 : N < h3.length := hget_lt hN3
      simp only [incT, witsT_eq]
      refine ReadsKV.dictSet _ ?_ _ _ (ReadsKV.dictSet _ ?_ _ _ (ReadsKV.dictSet _ (ReadsM.str _ _ _) _ _
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

end PCSCR.Py
