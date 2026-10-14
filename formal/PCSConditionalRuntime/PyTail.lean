import PCSConditionalRuntime.PyHandler

/-!
# `check`: the `try` statement and the tail

```
try: ...  except ResourceLimit as error: ...
result['work'] = manager.work()
result['receipt_sha256'] = digest(result)
return result
```
-/

namespace PCSCR.Py

open PCSCR PCSDD PCSOmega

/-- The dictionary built by `Diagram.work`. -/
def workKV (m : Mgr) : List (V × V) :=
  [(.str "bdd_nodes", iv m.nodes.size), (.str "apply_calls", iv m.ops), (.str "ast_visits", iv m.visits),
   (.str "witness_steps", iv m.wsteps)]

theorem work_call (ext : Ext) (k : Nat) (h : Heap) (D : Addrs) (m : Mgr) (W : WorkOK D h m) :
    (interp (pyCtx ext) (k + 1)).call "Diagram.work" [.ref D.self] h = .ok (.ref h.length) (h ++ [.dict (workKV m)]) := by
  obtain ⟨hs, ptrs, hp, hl⟩ := W
  rw [interp_succ_call]
  simp only [callBody, show lookupFn (pyCtx ext).prog "Diagram.work" = some py_Diagram_work from rfl,
    py_Diagram_work]
  simp only [List.length, List.zip, List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append,
    List.cons_append, ne_eq, not_true, if_false]
  pystep [hs, hp, diagramFields, pairUp]
  simp [finishCall, workKV, hl, iv, dictSet, keyEq, eqD, eqPy]

theorem WorkOK.frameR {D : Addrs} {R : Nat} {h h' : Heap} {m : Mgr} (F : FrameS (fun x => x = R) h h')
    (r1 : R ≠ D.self) (r2 : R ≠ D.nodes) (W : WorkOK D h m) : WorkOK D h' m := by
  obtain ⟨hs, ptrs, hp, hl⟩ := W
  refine ⟨?_, ptrs, ?_, hl⟩
  · rw [F.2 _ (hget_lt hs) (fun e => r1 e.symm)]; exact hs
  · rw [F.2 _ (hget_lt hp) (fun e => r2 e.symm)]; exact hp

/-- The `try` statement of `check`. -/
def tryS : S := S.try tryBody "ResourceLimit" "error" handlerB

/-- The JSON fields of the result dictionary after the `try` statement. -/
def finKT (names : List String) (t : CTask names.length) (lim : Limits) (kts : List (String × T)) :
    List (String × T) :=
  match pipeline t lim with
  | .ok (b, m) => bodyT names t kts b m
  | .error (e, _) => limKT kts e

/-- The manager state after the `try` statement. -/
def finMgr {n : Nat} (t : CTask n) (lim : Limits) : Mgr :=
  match pipeline t lim with
  | .ok (_, m) => m
  | .error (_, m) => m

theorem trystmt_sim (ext : Ext) {names : List String} {lim : Limits} {D : Addrs} (hnd : names.Nodup)
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
    ∃ env' h' kvs', execS (pyCtx ext) (interp (pyCtx ext) (k + 1)) env h tryS = .ok (.normal env') h' ∧
      env'.get "manager" = some (.ref D.self) ∧ env'.get "result" = some (.ref R) ∧
      hget h' R = some (.dict kvs') ∧ ReadsKV (fun a => a = R) h' kvs' (finKT names t lim kts) ∧
      WorkOK D h' (finMgr t lim) ∧ FrameS (Big D h.length) h h' := by
  have ts := try_sim ext hnd t k env h A AS R vkvs as vs vc kvs kts hk hmg hval hres hA hmA has hAS hmAS hl hz
    hs hc hfs hfc hR hRo r1 r2 r3 r4 hRk hkv
  have kr := execB_keeps_interp (pyCtx ext) (k + 1) "result" tryBody env h (by decide)
  have km := execB_keeps_interp (pyCtx ext) (k + 1) "manager" tryBody env h (by decide)
  have hRB : ∀ a, a = R → Big D h.length a := fun a e => e ▸ Or.inl (Or.inr (Or.inr (Or.inr (Or.inr hRo))))
  simp only [tryS, execS]
  unfold finKT finMgr
  cases hp : pipeline t lim with
  | ok q =>
    obtain ⟨b, m⟩ := q
    rw [hp] at ts
    obtain ⟨env', h', kvs', e', hR', hkv', W', F'⟩ := ts
    rw [e'] at kr km ⊢
    simp only [FK] at kr km
    simp only [onRaise]
    exact ⟨env', h', kvs', rfl, km.trans hmg, kr.trans hres, hR', hkv', W', F'⟩
  | error q =>
    obtain ⟨e, m⟩ := q
    rw [hp] at ts
    obtain ⟨env', h', a, e', ha, hR', W', F'⟩ := ts
    rw [e'] at kr km ⊢
    simp only [FK] at kr km
    simp only [onRaise, excClassIs, ha, excVal]
    simp only [beq_self_eq_true, if_true]
    obtain ⟨env'', h'', kvs'', eh, hy, hR'', hkv'', F''⟩ := handler_sim ext k (env'.set "error" (.ref a)) h' R a
      kvs kts e (fun x => x = R) (by omega) (by simp [Env.get_set, kr, hres]) (by simp [Env.get_set]) ha hR'
      ((hkv.frame F').anti hRB) rfl
    rw [eh]
    simp only [eraseAfter]
    refine ⟨_, h'', kvs'', rfl, ?_, ?_, hR'', hkv'', W'.frameR F'' r1 r2, F'.trans (F''.mono hRB)⟩
    · rw [Env.get_erase _ _ _ (by decide), hy _ (by decide)]; simp [Env.get_set, km, hmg]
    · rw [Env.get_erase _ _ _ (by decide), hy _ (by decide)]; simp [Env.get_set, kr, hres]

def workS : S :=
  S.assign [Tgt.sub (E.var "result") (E.lit (V.str "work"))] (E.mcall (E.var "manager") "work" [])
def digS : S :=
  S.assign [Tgt.sub (E.var "result") (E.lit (V.str "receipt_sha256"))] (E.call "digest" [E.var "result"])
def retS : S := S.ret (E.var "result")

theorem check_body_drop6 : py_check.body.drop 6 = [tryS, workS, digS, retS] := rfl

theorem reads_workKV (M : Nat → Prop) (h : Heap) (a : Nat) (m : Mgr) (hg : hget h a = some (.dict (workKV m)))
    (hm : ¬ M a) : ReadsM M h (.ref a) (workT m.work) := by
  refine ReadsM.dict hg hm ?_
  exact ReadsKV.cons (ReadsM.int _ _ _) (ReadsKV.cons (ReadsM.int _ _ _) (ReadsKV.cons (ReadsM.int _ _ _)
    (ReadsKV.cons (ReadsM.int _ _ _) (ReadsKV.nil _ _))))

/-- A dictionary whose fields read back (avoiding only itself) reads back as an object. -/
theorem readback_dict {R : Nat} {h : Heap} {kvs : List (V × V)} {kts : List (String × T)}
    (hg : hget h R = some (.dict kvs)) (hkv : ReadsKV (fun a => a = R) h kvs kts) :
    ∃ fu, readback fu h (.ref R) = some (.obj kts) :=
  (ReadsM.dict (M := fun _ => False) hg (fun e => e) (hkv.anti (fun _ e => e.elim))).readback

/-- The JSON fields after `result['work'] = manager.work()` and the digest. -/
def tailKT (dg : T → String) (kts : List (String × T)) (m : Mgr) : List (String × T) :=
  tset (tset kts "work" (workT m.work)) "receipt_sha256" (.str (dg (.obj (tset kts "work" (workT m.work)))))

theorem tail_sim (ext : Ext) (dg : T → String) (hdg : DigestOK ext dg) (k : Nat) (env : Env) (h : Heap)
    (D : Addrs) (m : Mgr) (R : Nat) (kvs : List (V × V)) (kts : List (String × T))
    (hmg : env.get "manager" = some (.ref D.self)) (hres : env.get "result" = some (.ref R))
    (hRk : hget h R = some (.dict kvs)) (hkv : ReadsKV (fun a => a = R) h kvs kts) (W : WorkOK D h m) :
    ∃ h', execB (pyCtx ext) (interp (pyCtx ext) (k + 2)) env h [workS, digS, retS] = .ok (.ret (.ref R)) h' ∧
      ∃ fu, readback fu h' (.ref R) = some (.obj (tailKT dg kts m)) := by
  have hRlt := hget_lt hRk
  have hcl : classHasMethod pyProg "Diagram" "work" = true := by decide
  have hself := W.1
  have ew := work_call ext (k + 1) h D m W
  rw [execB_cons']
  simp [workS, execS, evalE, evalL, bindS, bindE, hmg, Out.bind, hself, hcl, ew, assignAll, assignT, hres,
    storeOp, hget_append_lt_list _ hRlt, hRk, hashable]
  generalize hH1 : hset (h ++ [Obj.dict (workKV m)]) R (Obj.dict (dictSet Dialect.py kvs (V.str "work")
    (V.ref h.length))) = H1
  have hR1 : hget H1 R = some (.dict (dictSet Dialect.py kvs (V.str "work") (V.ref h.length))) := by
    rw [← hH1]; exact hget_hset_same _ (by simp; omega)
  have F1 : FrameS (fun a => a = R) h H1 := by rw [← hH1]; exact (FrameS.append _ _ _).trans (FrameS.hset _ _ rfl)
  have hW1 : hget H1 h.length = some (.dict (workKV m)) := by
    rw [← hH1, hget_hset_ne _ (by omega)]; simp [hget]
  have hkv1 : ReadsKV (fun a => a = R) H1 (dictSet Dialect.py kvs (V.str "work") (V.ref h.length))
      (tset kts "work" (workT m.work)) :=
    ReadsKV.dictSet _ (reads_workKV _ _ _ m hW1 (by omega)) _ _ (hkv.frame F1)
  obtain ⟨fu1, rb1⟩ := readback_dict hR1 hkv1
  have ed := hdg H1 (.ref R) fu1 _ rb1
  have hR1lt := hget_lt hR1
  rw [execB_cons']
  simp [digS, execS, evalE, evalL, bindS, bindE, hres, Out.bind, ed, assignAll, assignT, storeOp, hR1, hashable]
  generalize hH2 : hset H1 R (Obj.dict (dictSet Dialect.py (dictSet Dialect.py kvs (V.str "work") (V.ref h.length))
    (V.str "receipt_sha256") (V.str (dg (T.obj (tset kts "work" (workT m.work))))))) = H2
  have hR2 : hget H2 R = some (.dict (dictSet Dialect.py (dictSet Dialect.py kvs (V.str "work") (V.ref h.length))
      (V.str "receipt_sha256") (V.str (dg (T.obj (tset kts "work" (workT m.work))))))) := by
    rw [← hH2]; exact hget_hset_same _ hR1lt
  have F2 : FrameS (fun a => a = R) H1 H2 := by rw [← hH2]; exact FrameS.hset _ _ rfl
  rw [execB_cons']
  simp [retS, execS, evalE, bindS, hres, execB_nil_eq]
  exact readback_dict hR2 (ReadsKV.dictSet _ (ReadsM.str _ _ _) _ _ (hkv1.frame F2))

end PCSCR.Py
