import PCSConditionalRuntime.PyDecided

/-!
# `check`: the disagreement report

```
truths = [evaluate(f, world) for f in value['assumptions']]
a, b = evaluate(value['source'], world), evaluate(value['candidate'], world)
assert all(truths) and a != b
result.update(decision='counterexample', counterexample={'assignment': world,
              'source_true': a, 'candidate_true': b, 'assumptions_true': truths})
```
`evaluate` is heap-pure; the assertion holds because the witness satisfies the difference
diagram (`pipeline_decided`).
-/

namespace PCSCR.Py

open PCSCR PCSDD PCSOmega

theorem HAgree.frame {D : Addrs} {h H : Heap} (a : HAgree h H) : Frame D h H :=
  ⟨a.1, fun x hx _ => a.2 x hx⟩

/-- The value `evaluate(y, world)` (determined by any formula tree that `y` denotes). -/
noncomputable def evalG (D : Addrs) (h : Heap) (names : List String) (w : List Bool) (y : V) : V :=
  open Classical in
  if hy : ∃ f : BForm names.length, FRel D h names y f then .bool ((Classical.choose hy).eval (envOf w))
  else .none

theorem evalG_eq (ext : Ext) {names : List String} {D : Addrs} {h : Heap} {A : Nat} {w : List Bool}
    (hnd : names.Nodup) (hw : w.length = names.length) (hA : hget h A = some (.dict (encVals names w)))
    {y : V} {f : BForm names.length} (hf : FRel D h names y f) :
    evalG D h names w y = .bool (f.eval (envOf w)) := by
  have hy : ∃ f : BForm names.length, FRel D h names y f := ⟨f, hf⟩
  simp only [evalG, hy, dif_pos]
  have e1 := eval_sim ext hnd hw hA f (fdepth f + fdepth (Classical.choose hy) + 1) (by omega) y hf
  have e2 := eval_sim ext hnd hw hA (Classical.choose hy) (fdepth f + fdepth (Classical.choose hy) + 1)
    (by omega) y (Classical.choose_spec hy)
  rw [e1] at e2
  simp only [Out.ok.injEq, V.bool.injEq, and_true] at e2
  rw [e2]

theorem fdepthL_ge {n : Nat} : ∀ (fs : List (BForm n)) (f : BForm n), f ∈ fs → fdepth f ≤ fdepthL fs
  | [], _, h => by simp at h
  | g :: gs, f, h => by
      simp only [List.mem_cons] at h
      rcases h with rfl | h
      · simp [fdepthL]; omega
      · have := fdepthL_ge gs f h; simp [fdepthL]; omega

theorem zip_mem_left {α β : Type} {xs : List α} {ys : List β} (hl : xs.length = ys.length) :
    ∀ x ∈ xs, ∃ y ∈ ys, (x, y) ∈ xs.zip ys := by
  induction xs generalizing ys with
  | nil => intro x hx; simp at hx
  | cons a as ih =>
    cases ys with
    | nil => simp at hl
    | cons b bs =>
      intro x hx
      simp only [List.mem_cons] at hx
      rcases hx with rfl | hx
      · exact ⟨b, by simp, by simp⟩
      · obtain ⟨y, hy, hxy⟩ := ih (by simpa using hl) x hx
        exact ⟨y, by simp [hy], by simp [hxy]⟩

theorem map_evalG (ext : Ext) {names : List String} {D : Addrs} {h : Heap} {A : Nat} {w : List Bool}
    (hnd : names.Nodup) (hw : w.length = names.length) (hA : hget h A = some (.dict (encVals names w))) :
    ∀ (as : List V) (fs : List (BForm names.length)), as.length = fs.length →
      (∀ p ∈ as.zip fs, FRel D h names p.1 p.2) →
      as.map (evalG D h names w) = fs.map (fun f => V.bool (f.eval (envOf w)))
  | [], [], _, _ => rfl
  | [], _ :: _, hl, _ => by simp at hl
  | _ :: _, [], hl, _ => by simp at hl
  | a :: as, f :: fs, hl, hz => by
      simp only [List.map_cons]
      rw [evalG_eq ext hnd hw hA (hz (a, f) (by simp)),
        map_evalG ext hnd hw hA as fs (by simpa using hl) (fun p hp => hz p (by simp [hp]))]

/-- `[evaluate(f, world) for f in value['assumptions']]`. -/
theorem comp_truths (ext : Ext) {names : List String} {D : Addrs} (hnd : names.Nodup) (k : Nat) (env : Env)
    (h : Heap) (A AS W : Nat) (vkvs : List (V × V)) (as : List V) (fs : List (BForm names.length))
    (w : List Bool) (hw : w.length = names.length)
    (hval : env.get "value" = some (.ref A)) (hwd : env.get "world" = some (.ref W))
    (hA : hget h A = some (.dict vkvs)) (has : dictFind .py vkvs (.str "assumptions") = some (.ref AS))
    (hAS : hget h AS = some (.list as)) (hl : as.length = fs.length)
    (hz : ∀ p ∈ as.zip fs, FRel D h names p.1 p.2)
    (hW : hget h W = some (.dict (encVals names w)))
    (hk : fdepthL fs + 2 + as.length + 1 ≤ k) :
    evalE (pyCtx ext) (interp (pyCtx ext) k) env h
        (E.comp (E.call "evaluate" [E.var "f", E.var "world"]) "f"
          (E.sub (E.var "value") (E.lit (V.str "assumptions"))) none) =
      .ok (.ref h.length) (h ++ [.list (fs.map (fun f => V.bool (f.eval (envOf w))))]) := by
  have e := comp_eval ext k env h "f" (E.sub (E.var "value") (E.lit (V.str "assumptions")))
    (E.call "evaluate" [E.var "f", E.var "world"]) none AS as (evalG D h names w) (fun _ => true)
    (fdepthL fs + 2) (by simp [evalE, hval, Out.bind, subOp, hA, hashable, has]) hAS hk
    (fun y hy k' hk' env' H hx hz' hag => by
      obtain ⟨f, hf, hyf⟩ := zip_mem_left hl y hy
      have hfr := hz (y, f) hyf
      have hwd' : env'.get "world" = some (.ref W) := by rw [hz' "world" (by decide)]; exact hwd
      have hAH : hget H W = some (.dict (encVals names w)) := by rw [hag.2 W (hget_lt hW)]; exact hW
      have hfH := FRel.frame (HAgree.frame hag) f y hfr
      obtain ⟨k'', rfl⟩ : ∃ k'', k' = k'' + 1 := ⟨k' - 1, by omega⟩
      have hd := fdepthL_ge fs f (List.of_mem_zip hyf).2
      have ev := eval_sim ext hnd hw hAH f k'' (by omega) y hfH
      rw [evalG_eq ext hnd hw hW hfr]
      simp [evalE, evalL, hx, hwd', Out.bind, ev, show (lookupFn pyProg "evaluate").isSome = true from rfl])
    (fun _ _ => rfl)
  rw [e, List.filter_eq_self.2 (fun _ _ => rfl), map_evalG ext hnd hw hW as fs hl hz]

def cexBody : List S :=
  [S.assign [Tgt.name "truths"]
     (E.comp (E.call "evaluate" [E.var "f", E.var "world"]) "f"
       (E.sub (E.var "value") (E.lit (V.str "assumptions"))) none),
   S.assign [Tgt.tup [Tgt.name "a", Tgt.name "b"]]
     (E.tup [E.call "evaluate" [E.sub (E.var "value") (E.lit (V.str "source")), E.var "world"],
             E.call "evaluate" [E.sub (E.var "value") (E.lit (V.str "candidate")), E.var "world"]]),
   S.assert (E.and (E.call "all" [E.var "truths"]) (E.bin BinOp.ne (E.var "a") (E.var "b"))),
   S.expr (E.kwcall (E.var "result") "update" ["decision", "counterexample"]
     [E.lit (V.str "counterexample"),
      E.dictD [E.lit (V.str "assignment"), E.var "world", E.lit (V.str "source_true"), E.var "a",
               E.lit (V.str "candidate_true"), E.var "b", E.lit (V.str "assumptions_true"), E.var "truths"]])]

def truthsV {n : Nat} (fs : List (BForm n)) (w : List Bool) : List V :=
  fs.map (fun f => V.bool (f.eval (envOf w)))

def cexKV (W T : Nat) (sa sb : Bool) : List (V × V) :=
  [(.str "assignment", .ref W), (.str "source_true", .bool sa), (.str "candidate_true", .bool sb),
   (.str "assumptions_true", .ref T)]

theorem cex_branch (ext : Ext) {names : List String} {D : Addrs} (hnd : names.Nodup)
    (t : CTask names.length) (k : Nat) (env : Env) (h : Heap) (A AS W R : Nat) (vkvs : List (V × V))
    (as : List V) (vs vc : V) (w : List Bool) (kvs : List (V × V)) (hw : w.length = names.length)
    (hval : env.get "value" = some (.ref A)) (hwd : env.get "world" = some (.ref W))
    (hres : env.get "result" = some (.ref R))
    (hA : hget h A = some (.dict vkvs)) (has : dictFind .py vkvs (.str "assumptions") = some (.ref AS))
    (hAS : hget h AS = some (.list as)) (hl : as.length = t.assumptions.length)
    (hz : ∀ p ∈ as.zip t.assumptions, FRel D h names p.1 p.2)
    (hs : dictFind .py vkvs (.str "source") = some vs) (hc : dictFind .py vkvs (.str "candidate") = some vc)
    (hfs : FRel D h names vs t.source) (hfc : FRel D h names vc t.candidate)
    (hW : hget h W = some (.dict (encVals names w))) (hR : hget h R = some (.dict kvs))
    (hsat : allEval t.assumptions (envOf w) = true)
    (hne : t.source.eval (envOf w) ≠ t.candidate.eval (envOf w))
    (hk : fdepthL t.assumptions + fdepth t.source + fdepth t.candidate + as.length + 4 ≤ k) :
    execB (pyCtx ext) (interp (pyCtx ext) (k + 1)) env h cexBody =
      .ok (.normal (((env.set "truths" (.ref h.length)).set "a" (.bool (t.source.eval (envOf w)))).set "b"
            (.bool (t.candidate.eval (envOf w)))))
        (hset (h ++ [.list (truthsV t.assumptions w),
            .dict (cexKV W h.length (t.source.eval (envOf w)) (t.candidate.eval (envOf w)))]) R
          (.dict (dictSet .py (dictSet .py kvs (.str "decision") (.str "counterexample")) (.str "counterexample")
            (.ref (h.length + 1))))) := by
  have hct := comp_truths ext (D := D) hnd (k + 1) env h A AS W vkvs as t.assumptions w hw hval hwd hA has hAS hl
    hz hW (by omega)
  have hWl := hget_lt hW
  have hW1 : hget (h ++ [Obj.list (truthsV t.assumptions w)]) W = some (.dict (encVals names w)) := by
    rw [hget_append_lt _ hWl]; exact hW
  have hA1 : hget (h ++ [Obj.list (truthsV t.assumptions w)]) A = some (.dict vkvs) := by
    rw [hget_append_lt _ (hget_lt hA)]; exact hA
  have hag : HAgree h (h ++ [Obj.list (truthsV t.assumptions w)]) := HAgree.of_prefix rfl
  have hfs1 := FRel.frame (HAgree.frame hag) _ _ hfs
  have hfc1 := FRel.frame (HAgree.frame hag) _ _ hfc
  have es := eval_sim ext hnd hw hW1 t.source k (by omega) vs hfs1
  have ec := eval_sim ext hnd hw hW1 t.candidate k (by omega) vc hfc1
  simp only [cexBody]
  rw [execB_cons']
  simp only [execS, bindS, ↓hct, assignAll, assignT, bindE, Out.bind, seqF_normal]
  simp only [truthsV] at hW1 hA1 es ec
  pystepA [hval, hwd, hA1, hs, hc, es, ec, show (lookupFn pyProg "evaluate").isSome = true from rfl]
  have hall : ∀ H, (List.map (fun f => V.bool (BForm.eval (envOf w) f)) t.assumptions).all (truthy .py H) = true := by
    intro H; simpa [allEval, List.all_map, truthy, Function.comp_def] using hsat
  have hRl := hget_lt hR
  have hRl' : R < h.length + 1 := by omega
  pystepA [hall, hne, hres, hR, hRl, hRl', hget_append_lt_list, pairUp, isNoneV, updateKw, dictSet, keyEq, eqD,
    eqPy, eqPrim]
  have hne' : ¬ ((if BForm.eval (envOf w) t.source = true then (1 : Int) else 0) =
      if BForm.eval (envOf w) t.candidate = true then 1 else 0) := by
    revert hne; cases BForm.eval (envOf w) t.source <;> cases BForm.eval (envOf w) t.candidate <;> simp
  simp only [hne', if_false, seqF_normal]
  pystepA [hres, hwd, hR, hRl, hRl', hget_append_lt_list, pairUp, updateKw]
  simp [execB_nil_eq, truthsV, cexKV, dictSet, keyEq, eqD, eqPy]

end PCSCR.Py
