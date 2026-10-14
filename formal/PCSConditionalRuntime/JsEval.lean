import PCSConditionalRuntime.JsWorld
import PCSConditionalRuntime.PyEval

/-!
# JavaScript `evaluateConditional` refines `BForm.eval`

`evaluateConditional(f, a)` on a heap formula tree (`JFRel`) and an assignment object
`{names[i]: w[i]}` returns `f.eval (envOf w)`; the heap is unchanged.  The `switch(f.op)` is
lowered to the `%sw` cascade; `&&`/`||` return one of their (Boolean) operands.
-/

namespace PCSCR.Js

open PCSCR PCSDD PCSOmega PCSCR.Py

theorem jdictFind_encVals : ∀ (names : List String) (w : List Bool), names.Nodup → w.length = names.length →
    ∀ (i : Nat) (hi : i < names.length),
    dictFind .js (encVals names w) (.str names[i]) = some (.bool (w.getD i false))
  | [], _, _, _, i, hi => by simp at hi
  | x :: xs, [], _, hl, _, _ => by simp at hl
  | x :: xs, b :: bs, hd, hl, 0, _ => by simp [encVals, dictFind, jkeyEq_str]
  | x :: xs, b :: bs, hd, hl, i + 1, hi => by
      have hx : x ∉ xs := (List.nodup_cons.1 hd).1
      have hi' : i < xs.length := by simp at hi; omega
      have hne : x ≠ xs[i] := fun e => hx (e ▸ List.getElem_mem _)
      have ih := jdictFind_encVals xs bs (List.nodup_cons.1 hd).2 (by simpa using hl) i hi'
      simp only [encVals] at ih
      simp [encVals, dictFind, jkeyEq_str, hne, ih]

/-- The simulation statement for `evaluateConditional` on one formula. -/
def JEvalOK (ext : Ext) (names : List String) (D : Addrs) (h : Heap) (A : Nat) (w : List Bool)
    (f : BForm names.length) : Prop :=
  ∀ (k : Nat), fdepth f + 1 ≤ k → ∀ (v : V), JFRel D h names v f →
    (interp (jsCtx ext) (k + 1)).call "evaluateConditional" [v, .ref A] h = .ok (.bool (f.eval (envOf w))) h

section
variable (ext : Ext) {names : List String} {D : Addrs} {h : Heap} {A : Nat} {w : List Bool}
  (hnd : names.Nodup) (hw : w.length = names.length) (hA : hget h A = some (.dict (encVals names w)))
include hnd hw hA

theorem jeval_atom (i : Fin names.length) : JEvalOK ext names D h A w (.atom i) := by
  intro k hk v hv
  obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by omega⟩
  match v, hv with
  | .ref a, ⟨hma, kvs, hg, hop, hsym⟩ =>
  rw [interp_succ_call]
  simp only [callBody, lookup_evaluate, js_evaluateConditional, jsCtx_prog]
  simp only [List.length, List.zip, List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append,
    List.cons_append, ne_eq, not_true, if_false]
  have hin : i.val < names.length := i.isLt
  have hf := jdictFind_encVals names w hnd hw i.val hin
  have hsym' : dictFind .js kvs (.str "symbol") = some (.str names[i.val]) := by
    rw [hsym]; simp [hin]
  jsstep [hg, hop]
  jsrun [hg, hsym', hA, hf, finishCall]
  simp [BForm.eval, envOf]

theorem jeval_tt : JEvalOK ext names D h A w .tt := by
  intro k hk v hv
  obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by omega⟩
  match v, hv with
  | .ref a, ⟨hma, kvs, hg, hop⟩ =>
  rw [interp_succ_call]
  simp only [callBody, lookup_evaluate, js_evaluateConditional, jsCtx_prog]
  simp only [List.length, List.zip, List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append,
    List.cons_append, ne_eq, not_true, if_false]
  jsstep [hg, hop]
  jsrun [finishCall, BForm.eval]

theorem jeval_ff : JEvalOK ext names D h A w .ff := by
  intro k hk v hv
  obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by omega⟩
  match v, hv with
  | .ref a, ⟨hma, kvs, hg, hop⟩ =>
  rw [interp_succ_call]
  simp only [callBody, lookup_evaluate, js_evaluateConditional, jsCtx_prog]
  simp only [List.length, List.zip, List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append,
    List.cons_append, ne_eq, not_true, if_false]
  jsstep [hg, hop]
  jsrun [finishCall, BForm.eval]

theorem jeval_not (f : BForm names.length) (ih : JEvalOK ext names D h A w f) :
    JEvalOK ext names D h A w (.not f) := by
  intro k hk v hv
  obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by omega⟩
  match v, hv with
  | .ref a, ⟨hma, kvs, c, hg, hop, hbody, hc⟩ =>
  rw [interp_succ_call]
  simp only [callBody, lookup_evaluate, js_evaluateConditional, jsCtx_prog]
  simp only [List.length, List.zip, List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append,
    List.cons_append, ne_eq, not_true, if_false]
  jsstep [hg, hop]
  have e1 := ih k' (by simp only [fdepth] at hk; omega) c hc
  jsrun [hg, hbody, e1, finishCall, BForm.eval]

theorem jeval_and (f g : BForm names.length) (ih1 : JEvalOK ext names D h A w f)
    (ih2 : JEvalOK ext names D h A w g) : JEvalOK ext names D h A w (.and f g) := by
  intro k hk v hv
  obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by omega⟩
  match v, hv with
  | .ref a, ⟨hma, kvs, c1, c2, hg, hop, hleft, hright, hc1, hc2⟩ =>
  rw [interp_succ_call]
  simp only [callBody, lookup_evaluate, js_evaluateConditional, jsCtx_prog]
  simp only [List.length, List.zip, List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append,
    List.cons_append, ne_eq, not_true, if_false]
  jsstep [hg, hop]
  have e1 := ih1 k' (by simp only [fdepth] at hk; omega) c1 hc1
  have e2 := ih2 k' (by simp only [fdepth] at hk; omega) c2 hc2
  cases hf : f.eval (envOf w) <;> cases hg' : g.eval (envOf w) <;>
    jsrun [hg, hleft, hright, e1, e2, finishCall, BForm.eval, hf, hg']

theorem jeval_or (f g : BForm names.length) (ih1 : JEvalOK ext names D h A w f)
    (ih2 : JEvalOK ext names D h A w g) : JEvalOK ext names D h A w (.or f g) := by
  intro k hk v hv
  obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by omega⟩
  match v, hv with
  | .ref a, ⟨hma, kvs, c1, c2, hg, hop, hleft, hright, hc1, hc2⟩ =>
  rw [interp_succ_call]
  simp only [callBody, lookup_evaluate, js_evaluateConditional, jsCtx_prog]
  simp only [List.length, List.zip, List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append,
    List.cons_append, ne_eq, not_true, if_false]
  jsstep [hg, hop]
  have e1 := ih1 k' (by simp only [fdepth] at hk; omega) c1 hc1
  have e2 := ih2 k' (by simp only [fdepth] at hk; omega) c2 hc2
  cases hf : f.eval (envOf w) <;> cases hg' : g.eval (envOf w) <;>
    jsrun [hg, hleft, hright, e1, e2, finishCall, BForm.eval, hf, hg']

theorem jeval_imp (f g : BForm names.length) (ih1 : JEvalOK ext names D h A w f)
    (ih2 : JEvalOK ext names D h A w g) : JEvalOK ext names D h A w (.imp f g) := by
  intro k hk v hv
  obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by omega⟩
  match v, hv with
  | .ref a, ⟨hma, kvs, c1, c2, hg, hop, hleft, hright, hc1, hc2⟩ =>
  rw [interp_succ_call]
  simp only [callBody, lookup_evaluate, js_evaluateConditional, jsCtx_prog]
  simp only [List.length, List.zip, List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append,
    List.cons_append, ne_eq, not_true, if_false]
  jsstep [hg, hop]
  have e1 := ih1 k' (by simp only [fdepth] at hk; omega) c1 hc1
  have e2 := ih2 k' (by simp only [fdepth] at hk; omega) c2 hc2
  cases hf : f.eval (envOf w) <;> cases hg' : g.eval (envOf w) <;>
    jsrun [hg, hleft, hright, e1, e2, finishCall, BForm.eval, hf, hg']

end

/-- **`evaluateConditional` refines `BForm.eval`** on every typed formula tree. -/
theorem jeval_sim (ext : Ext) {names : List String} {D : Addrs} {h : Heap} {A : Nat} {w : List Bool}
    (hnd : names.Nodup) (hw : w.length = names.length) (hA : hget h A = some (.dict (encVals names w))) :
    ∀ f : BForm names.length, JEvalOK ext names D h A w f
  | .atom i => jeval_atom ext hnd hw hA i
  | .tt => jeval_tt ext hnd hw hA
  | .ff => jeval_ff ext hnd hw hA
  | .not f => jeval_not ext hnd hw hA f (jeval_sim ext hnd hw hA f)
  | .and f g => jeval_and ext hnd hw hA f g (jeval_sim ext hnd hw hA f) (jeval_sim ext hnd hw hA g)
  | .or f g => jeval_or ext hnd hw hA f g (jeval_sim ext hnd hw hA f) (jeval_sim ext hnd hw hA g)
  | .imp f g => jeval_imp ext hnd hw hA f g (jeval_sim ext hnd hw hA f) (jeval_sim ext hnd hw hA g)

end PCSCR.Js
