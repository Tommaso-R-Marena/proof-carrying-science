import PCSConditionalRuntime.JsTry
import PCSConditionalRuntime.PyTail

/-!
# `checkConditional`: the `catch` handler, the `try` statement and the tail

```
}catch(e){if(!(e instanceof ResourceLimit))throw e;
  for(const k of ['context_example','counterexample','unsat_core','core_necessity_witnesses','diagram'])r[k]=null;
  Object.assign(r,{decision:'resource_limit',limit_reached:e.message});}
r.work=m.work();r.receipt_sha256=await digest(r);return r;
```
Only `ResourceLimit` instances are caught (every other exception propagates unchanged).
-/

namespace PCSCR.Js

open PCSCR PCSDD PCSOmega PCSCR.Py

def jhandlerB : List S :=
  [S.forIn (Tgt.name "k#2")
     (E.listD [E.lit (V.str "context_example"), E.lit (V.str "counterexample"), E.lit (V.str "unsat_core"),
       E.lit (V.str "core_necessity_witnesses"), E.lit (V.str "diagram")])
     [S.assign [Tgt.sub (E.var "r") (E.var "k#2")] (E.lit V.none)],
   S.expr (E.kwcall (E.var "r") "update" ["decision", "limit_reached"]
     [E.lit (V.str "resource_limit"), E.attr (E.var "e") "message"])]

def jnullBody : List S := [S.assign [Tgt.sub (E.var "r") (E.var "k#2")] (E.lit V.none)]

theorem jnull_step (ext : Ext) (j i : Nat) (env : Env) (H : Heap) (L R : Nat) (xs : List V) (kvs : List (V × V))
    (f : String) (hL : hget H L = some (.list xs)) (hx : xs[i]? = some (.str f))
    (hRk : hget H R = some (.dict kvs)) (hres : env.get "r" = some (.ref R)) :
    forIter (jsCtx ext) (interp (jsCtx ext) (j + 1)) env H (Tgt.name "k#2") (.ref L) i jnullBody =
      forIter (jsCtx ext) (interp (jsCtx ext) j) (env.set "k#2" (.str f))
        (hset H R (.dict (dictSet .js kvs (.str f) .none))) (Tgt.name "k#2") (.ref L) (i + 1) jnullBody := by
  have hRlt := hget_lt hRk
  conv =>
    lhs
    simp [forIter, elemAt, hL, hx, bindE, assignT, jnullBody, execB, execS, evalE, bindS, assignAll,
      Env.get_set, hres, storeOp, hRk, hashable, loopK]
  rfl

theorem jhandler_sim (ext : Ext) (k : Nat) (env : Env) (h : Heap) (R a : Nat) (kvs : List (V × V))
    (kts : List (String × T)) (e : LimitReached) (M : Nat → Prop) (hk : 6 ≤ k)
    (hres : env.get "r" = some (.ref R)) (herr : env.get "e" = some (.ref a))
    (ha : hget h a = some (.inst "ResourceLimit" [("message", .str e.name)]))
    (hRk : hget h R = some (.dict kvs)) (hkv : ReadsKV M h kvs kts) (hMR : M R) :
    ∃ env' h' kvs', execB (jsCtx ext) (interp (jsCtx ext) (k + 1)) env h jhandlerB = .ok (.normal env') h' ∧
      (∀ y, y ≠ "k#2" → env'.get y = env.get y) ∧
      hget h' R = some (.dict kvs') ∧ ReadsKV M h' kvs' (limKT kts e) ∧ FrameS (fun x => x = R) h h' := by
  obtain ⟨k, rfl⟩ : ∃ k', k = k' + 6 := ⟨k - 6, by omega⟩
  have hRlt := hget_lt hRk
  have hal := hget_lt ha
  generalize hL5 : [V.str "context_example", V.str "counterexample", V.str "unsat_core",
    V.str "core_necessity_witnesses", V.str "diagram"] = L5
  have e1 : execS (jsCtx ext) (interp (jsCtx ext) (k + 6 + 1)) env h (jhandlerB.head!) =
      forIter (jsCtx ext) (interp (jsCtx ext) (k + 6)) env (h ++ [Obj.list L5]) (Tgt.name "k#2")
        (.ref h.length) 0 jnullBody := by
    rw [← hL5]; rfl
  simp only [jhandlerB]
  rw [execB_cons']
  simp only [jhandlerB, List.head!] at e1
  rw [e1]
  have hL0 : hget (h ++ [Obj.list L5]) h.length = some (.list L5) := by simp [hget]
  have hRL : R ≠ h.length := by omega
  have hR0 : hget (h ++ [Obj.list L5]) R = some (.dict kvs) := by rw [hget_append_lt_list _ hRlt]; exact hRk
  rw [show k + 6 = (k + 5) + 1 from rfl]
  rw [jnull_step ext (k + 5) 0 env _ h.length R L5 kvs "context_example" hL0 (by rw [← hL5]; rfl) hR0 hres]
  rw [jnull_step ext (k + 4) 1 _ _ h.length R L5 _ "counterexample" (by rw [hget_hset_ne _ hRL]; exact hL0)
    (by rw [← hL5]; rfl) (hget_hset_same _ (by simp; omega)) (by simp [Env.get_set, hres])]
  rw [jnull_step ext (k + 3) 2 _ _ h.length R L5 _ "unsat_core"
    (by rw [hget_hset_ne _ hRL, hget_hset_ne _ hRL]; exact hL0)
    (by rw [← hL5]; rfl) (hget_hset_same _ (by simp; omega)) (by simp [Env.get_set, hres])]
  rw [jnull_step ext (k + 2) 3 _ _ h.length R L5 _ "core_necessity_witnesses"
    (by rw [hget_hset_ne _ hRL, hget_hset_ne _ hRL, hget_hset_ne _ hRL]; exact hL0)
    (by rw [← hL5]; rfl) (hget_hset_same _ (by simp; omega)) (by simp [Env.get_set, hres])]
  rw [jnull_step ext (k + 1) 4 _ _ h.length R L5 _ "diagram"
    (by rw [hget_hset_ne _ hRL, hget_hset_ne _ hRL, hget_hset_ne _ hRL, hget_hset_ne _ hRL]; exact hL0)
    (by rw [← hL5]; rfl) (hget_hset_same _ (by simp; omega)) (by simp [Env.get_set, hres])]
  simp only [hset_hset_same]
  subst hL5
  have hel : forIter (jsCtx ext) (interp (jsCtx ext) (k + 1))
      (((((env.set "k#2" (V.str "context_example")).set "k#2" (V.str "counterexample")).set "k#2"
        (V.str "unsat_core")).set "k#2" (V.str "core_necessity_witnesses")).set "k#2" (V.str "diagram"))
      (hset (h ++ [Obj.list [V.str "context_example", V.str "counterexample", V.str "unsat_core",
        V.str "core_necessity_witnesses", V.str "diagram"]]) R (Obj.dict
          (dictSet Dialect.js (dictSet Dialect.js (dictSet Dialect.js (dictSet Dialect.js
            (dictSet Dialect.js kvs (V.str "context_example") V.none) (V.str "counterexample") V.none)
            (V.str "unsat_core") V.none) (V.str "core_necessity_witnesses") V.none) (V.str "diagram") V.none)))
      (Tgt.name "k#2") (V.ref (List.length h)) (4 + 1) jnullBody =
      .ok (.normal (((((env.set "k#2" (V.str "context_example")).set "k#2" (V.str "counterexample")).set "k#2"
        (V.str "unsat_core")).set "k#2" (V.str "core_necessity_witnesses")).set "k#2" (V.str "diagram")))
      (hset (h ++ [Obj.list [V.str "context_example", V.str "counterexample", V.str "unsat_core",
        V.str "core_necessity_witnesses", V.str "diagram"]]) R (Obj.dict
          (dictSet Dialect.js (dictSet Dialect.js (dictSet Dialect.js (dictSet Dialect.js
            (dictSet Dialect.js kvs (V.str "context_example") V.none) (V.str "counterexample") V.none)
            (V.str "unsat_core") V.none) (V.str "core_necessity_witnesses") V.none) (V.str "diagram") V.none))) := by
    simp only [forIter, elemAt, hget_hset_ne _ hRL]
    simp [hget]
  rw [hel]
  simp only [seqF_normal]
  have haR : a ≠ R := fun e => by rw [e, hRk] at ha; cases ha
  have hal' : hget (hset (h ++ [Obj.list [V.str "context_example", V.str "counterexample", V.str "unsat_core",
        V.str "core_necessity_witnesses", V.str "diagram"]]) R (Obj.dict
          (dictSet Dialect.js (dictSet Dialect.js (dictSet Dialect.js (dictSet Dialect.js
            (dictSet Dialect.js kvs (V.str "context_example") V.none) (V.str "counterexample") V.none)
            (V.str "unsat_core") V.none) (V.str "core_necessity_witnesses") V.none) (V.str "diagram") V.none))) a =
      some (.inst "ResourceLimit" [("message", .str e.name)]) := by
    rw [hget_hset_ne _ (Ne.symm haR), hget_append_lt_list _ hal]; exact ha
  have hRl1 : R < (h ++ [Obj.list [V.str "context_example", V.str "counterexample", V.str "unsat_core",
        V.str "core_necessity_witnesses", V.str "diagram"]]).length := by simp; omega
  rw [execB_cons']
  simp [execS, evalE, evalL, bindS, Env.get_set, hres, herr, updateKw, builtin, attrOp, hal', fieldGet,
    hget_hset_same _ hRl1]
  simp only [hset_hset_same, execB_nil_eq]
  have FF : FrameS (fun x => x = R) h (hset (h ++ [Obj.list [V.str "context_example", V.str "counterexample",
      V.str "unsat_core", V.str "core_necessity_witnesses", V.str "diagram"]]) R (Obj.dict
        (dictSet Dialect.js (dictSet Dialect.js (dictSet Dialect.js (dictSet Dialect.js (dictSet Dialect.js
          (dictSet Dialect.js (dictSet Dialect.js kvs (V.str "context_example") V.none) (V.str "counterexample")
          V.none) (V.str "unsat_core") V.none) (V.str "core_necessity_witnesses") V.none) (V.str "diagram") V.none)
          (V.str "decision") (V.str "resource_limit")) (V.str "limit_reached") (V.str e.name)))) :=
    (FrameS.append _ _ _).trans (FrameS.hset _ _ rfl)
  refine ⟨_, _, rfl, fun y hy => by simp [Env.get_set, Ne.symm hy], _, hget_hset_same _ hRl1, ?_, FF⟩
  have hk0 := hkv.frame (FF.mono (fun x e => e ▸ hMR))
  simp only [limKT]
  exact ReadsKV.jdictSet _ (ReadsM.str _ _ _) _ _ (ReadsKV.jdictSet _ (ReadsM.str _ _ _) _ _
    (ReadsKV.jdictSet _ (ReadsM.none _ _) _ _ (ReadsKV.jdictSet _ (ReadsM.none _ _) _ _
    (ReadsKV.jdictSet _ (ReadsM.none _ _) _ _ (ReadsKV.jdictSet _ (ReadsM.none _ _) _ _
    (ReadsKV.jdictSet _ (ReadsM.none _ _) _ _ hk0))))))

theorem jwork_call (ext : Ext) (k : Nat) (h : Heap) (D : Addrs) (m : Mgr) (W : JWorkOK D h m) :
    (interp (jsCtx ext) (k + 1)).call "Diagram.work" [.ref D.self] h = .ok (.ref h.length) (h ++ [.dict (workKV m)]) := by
  obtain ⟨hs, ptrs, hp, hl⟩ := W
  rw [interp_succ_call]
  simp only [callBody, show lookupFn (jsCtx ext).prog "Diagram.work" = some js_Diagram_work from rfl,
    js_Diagram_work]
  simp only [List.length, List.zip, List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append,
    List.cons_append, ne_eq, not_true, if_false]
  jsstep [hs, hp, jdiagramFields, pairUp]
  simp [finishCall, workKV, hl, iv, dictSet, keyEq, eqD, eqJs]

theorem JWorkOK.frameR {D : Addrs} {R : Nat} {h h' : Heap} {m : Mgr} (F : FrameS (fun x => x = R) h h')
    (r1 : R ≠ D.self) (r2 : R ≠ D.nodes) (W : JWorkOK D h m) : JWorkOK D h' m := by
  obtain ⟨hs, ptrs, hp, hl⟩ := W
  refine ⟨?_, ptrs, ?_, hl⟩
  · rw [F.2 _ (hget_lt hs) (fun e => r1 e.symm)]; exact hs
  · rw [F.2 _ (hget_lt hp) (fun e => r2 e.symm)]; exact hp

/-- The `try` statement of `check`. -/
def jtryS : S := S.try jtryBody "ResourceLimit" "e" jhandlerB

theorem jtrystmt_sim (ext : Ext) {names : List String} {lim : Limits} {D : Addrs} (hnd : names.Nodup)
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
    ∃ env' h' kvs', execS (jsCtx ext) (interp (jsCtx ext) (k + 1)) env h jtryS = .ok (.normal env') h' ∧
      env'.get "m" = some (.ref D.self) ∧ env'.get "r" = some (.ref R) ∧
      hget h' R = some (.dict kvs') ∧ ReadsKV (fun a => a = R) h' kvs' (finKT names t lim kts) ∧
      JWorkOK D h' (finMgr t lim) ∧ FrameS (Big D h.length) h h' := by
  have ts := jtry_sim ext hnd t k env h A AS R vkvs as vs vc kvs kts hk hmg hval hres hA hmA has hAS hmAS hl hz
    hs hc hfs hfc hR hRo r1 r2 r3 r4 hRk hkv hvisB hwsB
  have kr := execB_keeps_interp (jsCtx ext) (k + 1) "r" jtryBody env h (by decide)
  have km := execB_keeps_interp (jsCtx ext) (k + 1) "m" jtryBody env h (by decide)
  have hRB : ∀ a, a = R → Big D h.length a := fun a e => e ▸ Or.inl (Or.inr (Or.inr (Or.inr (Or.inr hRo))))
  simp only [jtryS, execS]
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
    obtain ⟨env'', h'', kvs'', eh, hy, hR'', hkv'', F''⟩ := jhandler_sim ext k (env'.set "e" (.ref a)) h' R a
      kvs kts e (fun x => x = R) (by omega) (by simp [Env.get_set, kr, hres]) (by simp [Env.get_set]) ha hR'
      ((hkv.frame F').anti hRB) rfl
    rw [eh]
    simp only [eraseAfter]
    refine ⟨_, h'', kvs'', rfl, ?_, ?_, hR'', hkv'', W'.frameR F'' r1 r2, F'.trans (F''.mono hRB)⟩
    · rw [Env.get_erase _ _ _ (by decide), hy _ (by decide)]; simp [Env.get_set, km, hmg]
    · rw [Env.get_erase _ _ _ (by decide), hy _ (by decide)]; simp [Env.get_set, kr, hres]

def jworkS : S :=
  S.assign [Tgt.attr (E.var "r") "work"] (E.mcall (E.var "m") "work" [])
def jdigS : S :=
  S.assign [Tgt.attr (E.var "r") "receipt_sha256"] (E.call "digest" [E.var "r"])
def jretS : S := S.ret (E.var "r")

theorem check_body_drop9 : js_checkConditional.body.drop 9 = [jtryS, jworkS, jdigS, jretS] := rfl

theorem jtail_sim (ext : Ext) (dg : T → String) (hdg : DigestOK ext dg) (k : Nat) (env : Env) (h : Heap)
    (D : Addrs) (m : Mgr) (R : Nat) (kvs : List (V × V)) (kts : List (String × T))
    (hmg : env.get "m" = some (.ref D.self)) (hres : env.get "r" = some (.ref R))
    (hRk : hget h R = some (.dict kvs)) (hkv : ReadsKV (fun a => a = R) h kvs kts) (W : JWorkOK D h m) :
    ∃ h', execB (jsCtx ext) (interp (jsCtx ext) (k + 2)) env h [jworkS, jdigS, jretS] = .ok (.ret (.ref R)) h' ∧
      ∃ fu, readback fu h' (.ref R) = some (.obj (tailKT dg kts m)) := by
  have hRlt := hget_lt hRk
  have hcl : classHasMethod jsProg "Diagram" "work" = true := by decide
  have hself := W.1
  have ew := jwork_call ext (k + 1) h D m W
  rw [execB_cons']
  simp [jworkS, execS, evalE, evalL, bindS, bindE, hmg, Out.bind, hself, hcl, ew, assignAll, assignT, hres,
    setAttrOp, hget_append_lt_list _ hRlt, hRk]
  generalize hH1 : hset (h ++ [Obj.dict (workKV m)]) R (Obj.dict (dictSet Dialect.js kvs (V.str "work")
    (V.ref h.length))) = H1
  have hR1 : hget H1 R = some (.dict (dictSet Dialect.js kvs (V.str "work") (V.ref h.length))) := by
    rw [← hH1]; exact hget_hset_same _ (by simp; omega)
  have F1 : FrameS (fun a => a = R) h H1 := by rw [← hH1]; exact (FrameS.append _ _ _).trans (FrameS.hset _ _ rfl)
  have hW1 : hget H1 h.length = some (.dict (workKV m)) := by
    rw [← hH1, hget_hset_ne _ (by omega)]; simp [hget]
  have hkv1 : ReadsKV (fun a => a = R) H1 (dictSet Dialect.js kvs (V.str "work") (V.ref h.length))
      (tset kts "work" (workT m.work)) :=
    ReadsKV.jdictSet _ (reads_workKV _ _ _ m hW1 (by omega)) _ _ (hkv.frame F1)
  obtain ⟨fu1, rb1⟩ := readback_dict hR1 hkv1
  have ed := hdg H1 (.ref R) fu1 _ rb1
  have hR1lt := hget_lt hR1
  rw [execB_cons']
  have hdx : "digest" ∈ jsProg.externs := by decide
  simp [jdigS, execS, evalE, evalL, bindS, bindE, hres, Out.bind, ed, assignAll, assignT, setAttrOp, hR1, hdx]
  generalize hH2 : hset H1 R (Obj.dict (dictSet Dialect.js (dictSet Dialect.js kvs (V.str "work") (V.ref h.length))
    (V.str "receipt_sha256") (V.str (dg (T.obj (tset kts "work" (workT m.work))))))) = H2
  have hR2 : hget H2 R = some (.dict (dictSet Dialect.js (dictSet Dialect.js kvs (V.str "work") (V.ref h.length))
      (V.str "receipt_sha256") (V.str (dg (T.obj (tset kts "work" (workT m.work))))))) := by
    rw [← hH2]; exact hget_hset_same _ hR1lt
  have F2 : FrameS (fun a => a = R) H1 H2 := by rw [← hH2]; exact FrameS.hset _ _ rfl
  rw [execB_cons']
  simp [jretS, execS, evalE, bindS, hres, execB_nil_eq]
  exact readback_dict hR2 (ReadsKV.jdictSet _ (ReadsM.str _ _ _) _ _ (hkv1.frame F2))

end PCSCR.Js
