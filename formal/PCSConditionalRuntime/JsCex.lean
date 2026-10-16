import PCSConditionalRuntime.JsWits
import PCSConditionalRuntime.PyFields

/-!
# `checkConditional`: the disagreement report

```
const truths=t.assumptions.map(f=>evaluateConditional(f,world)),
      a=evaluateConditional(t.source,world),b=evaluateConditional(t.candidate,world);
if(!truths.every(Boolean)||a===b)throw Error('Invalid counterexample');
Object.assign(r,{decision:'counterexample',counterexample:{assignment:world,source_true:a,
  candidate_true:b,assumptions_true:truths}});
```
`evaluateConditional` is heap-pure; the check never throws because the witness satisfies the
difference diagram (`pipeline_decided`).  Also: the JavaScript (`Map`/object) versions of the
field-level read-back lemmas of `PyFields`.
-/

namespace PCSCR.Js

open PCSCR PCSDD PCSOmega PCSCR.Py

/-! ## Field-level read-back with ECMAScript keys -/

theorem ReadsKV.jdictSet {M : Nat → Prop} {h : Heap} {v : V} {t : T} (k : String) (hv : ReadsM M h v t) :
    ∀ (kvs : List (V × V)) (kts : List (String × T)), ReadsKV M h kvs kts →
      ReadsKV M h (PCSCR.dictSet .js kvs (.str k) v) (tset kts k t)
  | [], kts, r => by
    obtain ⟨fu, e⟩ := r
    simp at e; subst e
    exact ReadsKV.cons hv (ReadsKV.nil M h)
  | p :: kvs, kts, r => by
    obtain ⟨k', v', t', kts', rfl, rfl, h1, h2⟩ := r.uncons
    simp only [PCSCR.dictSet, tset, jkeyEq_str]
    by_cases hk : k' = k
    · subst hk; simp only [decide_true, if_true]; exact ReadsKV.cons hv h2
    · simp only [hk, decide_false, if_false, Bool.false_eq_true]
      exact ReadsKV.cons h1 (ReadsKV.jdictSet k hv kvs kts' h2)

theorem jdictSet_absentKV {M : Nat → Prop} {h : Heap} (k : String) (v : V) :
    ∀ (kvs : List (V × V)) (kts : List (String × T)), ReadsKV M h kvs kts → k ∉ kts.map Prod.fst →
      PCSCR.dictSet .js kvs (.str k) v = kvs ++ [(.str k, v)]
  | [], _, _, _ => rfl
  | p :: kvs, kts, r, hk => by
    obtain ⟨k', v', t', kts', rfl, rfl, _, h2⟩ := r.uncons
    have hne : k' ≠ k := fun e => hk (by simp [e])
    simp only [PCSCR.dictSet, jkeyEq_str, hne, decide_false, Bool.false_eq_true, if_false, List.cons_append]
    rw [jdictSet_absentKV k v kvs kts' h2 (fun hm => hk (by simp [hm]))]

/-! ## `evaluateConditional` on the assumptions -/

/-- The value `evaluateConditional(y, world)` (determined by any formula tree that `y` denotes). -/
noncomputable def jevalG (D : Addrs) (h : Heap) (names : List String) (w : List Bool) (y : V) : V :=
  open Classical in
  if hy : ∃ f : BForm names.length, JFRel D h names y f then .bool ((Classical.choose hy).eval (envOf w))
  else .none

theorem jevalG_eq (ext : Ext) {names : List String} {D : Addrs} {h : Heap} {A : Nat} {w : List Bool}
    (hnd : names.Nodup) (hw : w.length = names.length) (hA : hget h A = some (.dict (encVals names w)))
    {y : V} {f : BForm names.length} (hf : JFRel D h names y f) :
    jevalG D h names w y = .bool (f.eval (envOf w)) := by
  have hy : ∃ f : BForm names.length, JFRel D h names y f := ⟨f, hf⟩
  simp only [jevalG, hy, dif_pos]
  have e1 := jeval_sim ext hnd hw hA f (fdepth f + fdepth (Classical.choose hy) + 1) (by omega) y hf
  have e2 := jeval_sim ext hnd hw hA (Classical.choose hy) (fdepth f + fdepth (Classical.choose hy) + 1)
    (by omega) y (Classical.choose_spec hy)
  rw [e1] at e2
  simp only [Out.ok.injEq, V.bool.injEq, and_true] at e2
  rw [e2]

theorem map_jevalG (ext : Ext) {names : List String} {D : Addrs} {h : Heap} {A : Nat} {w : List Bool}
    (hnd : names.Nodup) (hw : w.length = names.length) (hA : hget h A = some (.dict (encVals names w))) :
    ∀ (as : List V) (fs : List (BForm names.length)), as.length = fs.length →
      (∀ p ∈ as.zip fs, JFRel D h names p.1 p.2) →
      as.map (jevalG D h names w) = fs.map (fun f => V.bool (f.eval (envOf w)))
  | [], [], _, _ => rfl
  | [], _ :: _, hl, _ => by simp at hl
  | _ :: _, [], hl, _ => by simp at hl
  | a :: as, f :: fs, hl, hz => by
      simp only [List.map_cons]
      rw [jevalG_eq ext hnd hw hA (hz (a, f) (by simp)),
        map_jevalG ext hnd hw hA as fs (by simpa using hl) (fun p hp => hz p (by simp [hp]))]

theorem jlookup_evaluate_some : (lookupFn jsProg "evaluateConditional").isSome = true := rfl

/-- `t.assumptions.map(f => evaluateConditional(f, world))`. -/
theorem jcomp_truths (ext : Ext) {names : List String} {D : Addrs} (hnd : names.Nodup) (k : Nat) (env : Env)
    (h : Heap) (A AS W : Nat) (vkvs : List (V × V)) (as : List V) (fs : List (BForm names.length))
    (w : List Bool) (hw : w.length = names.length)
    (hval : env.get "t" = some (.ref A)) (hwd : env.get "world" = some (.ref W))
    (hA : hget h A = some (.dict vkvs)) (has : dictFind .js vkvs (.str "assumptions") = some (.ref AS))
    (hAS : hget h AS = some (.list as)) (hl : as.length = fs.length)
    (hz : ∀ p ∈ as.zip fs, JFRel D h names p.1 p.2)
    (hW : hget h W = some (.dict (encVals names w)))
    (hk : fdepthL fs + 2 + as.length + 1 ≤ k) :
    evalE (jsCtx ext) (interp (jsCtx ext) k) env h
        (E.comp (E.call "evaluateConditional" [E.var "f#2", E.var "world"]) "f#2"
          (E.attr (E.var "t") "assumptions") none) =
      .ok (.ref h.length) (h ++ [.list (fs.map (fun f => V.bool (f.eval (envOf w))))]) := by
  have e := jcomp_eval ext k env h "f#2" (E.attr (E.var "t") "assumptions")
    (E.call "evaluateConditional" [E.var "f#2", E.var "world"]) none (.ref AS) as (jevalG D h names w)
    (fun _ => true) (fdepthL fs + 2) (by simp [evalE, hval, Out.bind, attrOp, hA, has]) (IterOK.ref hAS) hk
    (fun y hy k' hk' env' H hx hz' hag => by
      obtain ⟨f, hf, hyf⟩ := zip_mem_left hl y hy
      have hfr := hz (y, f) hyf
      have hwd' : env'.get "world" = some (.ref W) := by rw [hz' "world" (by decide)]; exact hwd
      have hAH : hget H W = some (.dict (encVals names w)) := by rw [hag.2 W (hget_lt hW)]; exact hW
      have hfH := JFRel.frame (HAgree.frame hag) f y hfr
      obtain ⟨k'', rfl⟩ : ∃ k'', k' = k'' + 1 := ⟨k' - 1, by omega⟩
      have hd := fdepthL_ge fs f (List.of_mem_zip hyf).2
      have ev := jeval_sim ext hnd hw hAH f k'' (by omega) y hfH
      rw [jevalG_eq ext hnd hw hW hfr]
      simp [evalE, evalL, hx, hwd', Out.bind, ev, jlookup_evaluate_some])
    (fun _ _ => rfl)
  rw [e, List.filter_eq_self.2 (fun _ _ => rfl), map_jevalG ext hnd hw hW as fs hl hz]

def jcexBody : List S :=
  [S.assign [Tgt.name "truths"]
     (E.comp (E.call "evaluateConditional" [E.var "f#2", E.var "world"]) "f#2"
       (E.attr (E.var "t") "assumptions") none),
   S.assign [Tgt.name "a"] (E.call "evaluateConditional" [E.attr (E.var "t") "source", E.var "world"]),
   S.assign [Tgt.name "b"] (E.call "evaluateConditional" [E.attr (E.var "t") "candidate", E.var "world"]),
   S.ifte (E.or (E.not (E.call "%every" [E.var "truths"])) (E.bin BinOp.eq (E.var "a") (E.var "b")))
     [S.raise (E.call "%newError" [E.lit (V.str "Error"), E.lit (V.str "Invalid counterexample")])] [],
   S.expr (E.kwcall (E.var "r") "update" ["decision", "counterexample"]
     [E.lit (V.str "counterexample"),
      E.dictD [E.lit (V.str "assignment"), E.var "world", E.lit (V.str "source_true"), E.var "a",
               E.lit (V.str "candidate_true"), E.var "b", E.lit (V.str "assumptions_true"), E.var "truths"]])]

theorem jcex_branch (ext : Ext) {names : List String} {D : Addrs} (hnd : names.Nodup)
    (t : CTask names.length) (k : Nat) (env : Env) (h : Heap) (A AS W R : Nat) (vkvs : List (V × V))
    (as : List V) (vs vc : V) (w : List Bool) (kvs : List (V × V)) (hw : w.length = names.length)
    (hval : env.get "t" = some (.ref A)) (hwd : env.get "world" = some (.ref W))
    (hres : env.get "r" = some (.ref R))
    (hA : hget h A = some (.dict vkvs)) (has : dictFind .js vkvs (.str "assumptions") = some (.ref AS))
    (hAS : hget h AS = some (.list as)) (hl : as.length = t.assumptions.length)
    (hz : ∀ p ∈ as.zip t.assumptions, JFRel D h names p.1 p.2)
    (hs : dictFind .js vkvs (.str "source") = some vs) (hc : dictFind .js vkvs (.str "candidate") = some vc)
    (hfs : JFRel D h names vs t.source) (hfc : JFRel D h names vc t.candidate)
    (hW : hget h W = some (.dict (encVals names w))) (hR : hget h R = some (.dict kvs))
    (hsat : allEval t.assumptions (envOf w) = true)
    (hne : t.source.eval (envOf w) ≠ t.candidate.eval (envOf w))
    (hk : fdepthL t.assumptions + fdepth t.source + fdepth t.candidate + as.length + 4 ≤ k) :
    execB (jsCtx ext) (interp (jsCtx ext) (k + 1)) env h jcexBody =
      .ok (.normal (((env.set "truths" (.ref h.length)).set "a" (.bool (t.source.eval (envOf w)))).set "b"
            (.bool (t.candidate.eval (envOf w)))))
        (hset (h ++ [.list (truthsV t.assumptions w),
            .dict (cexKV W h.length (t.source.eval (envOf w)) (t.candidate.eval (envOf w)))]) R
          (.dict (dictSet .js (dictSet .js kvs (.str "decision") (.str "counterexample")) (.str "counterexample")
            (.ref (h.length + 1))))) := by
  have hct := jcomp_truths ext (D := D) hnd (k + 1) env h A AS W vkvs as t.assumptions w hw hval hwd hA has
    hAS hl hz hW (by omega)
  have hWl := hget_lt hW
  have hW1 : hget (h ++ [Obj.list (truthsV t.assumptions w)]) W = some (.dict (encVals names w)) := by
    rw [hget_append_lt _ hWl]; exact hW
  have hA1 : hget (h ++ [Obj.list (truthsV t.assumptions w)]) A = some (.dict vkvs) := by
    rw [hget_append_lt _ (hget_lt hA)]; exact hA
  have hag : HAgree h (h ++ [Obj.list (truthsV t.assumptions w)]) := HAgree.of_prefix rfl
  have hfs1 := JFRel.frame (HAgree.frame hag) _ _ hfs
  have hfc1 := JFRel.frame (HAgree.frame hag) _ _ hfc
  have es := jeval_sim ext hnd hw hW1 t.source k (by omega) vs hfs1
  have ec := jeval_sim ext hnd hw hW1 t.candidate k (by omega) vc hfc1
  simp only [jcexBody]
  rw [execB_cons']
  simp only [execS, bindS, ↓hct, assignAll, assignT, bindE, Out.bind, seqF_normal]
  simp only [truthsV] at hW1 hA1 es ec
  jsstepA [hval, hwd, hA1, hs, es, jlookup_evaluate_some]
  jsstepA [hval, hwd, hA1, hc, ec, jlookup_evaluate_some]
  have hall : ∀ H, (List.map (fun f => V.bool (BForm.eval (envOf w) f)) t.assumptions).all (truthy .js H) = true := by
    intro H; simpa [allEval, List.all_map, truthy, Function.comp_def] using hsat
  have hlc : lookupClass jsProg "%every" = none := by rfl
  have hRl := hget_lt hR
  have hRl' : R < h.length + 1 := by omega
  have hne' : (BForm.eval (envOf w) t.source == BForm.eval (envOf w) t.candidate) = false := by
    revert hne; cases BForm.eval (envOf w) t.source <;> cases BForm.eval (envOf w) t.candidate <;> simp
  jsstepA [hall, hne', hlc, hget_append_lt_list]
  jsstepA [hres, hwd, hR, hRl, hRl', hget_append_lt_list, pairUp, updateKw]
  simp [execB_nil_eq, truthsV, cexKV, dictSet, keyEq, eqD, eqJs]

end PCSCR.Js
