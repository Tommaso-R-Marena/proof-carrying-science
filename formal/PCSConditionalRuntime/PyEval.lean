import PCSConditionalRuntime.PyWalk
import PCSConditionalRuntime.PyCompile

/-!
# `evaluate` refines `BForm.eval`

`evaluate(formula, assignment)` on a heap formula tree (`FRel`) and an assignment dictionary
`{names[i]: w[i]}` returns `f.eval (envOf w)`; the heap is unchanged.
-/

namespace PCSCR.Py

open PCSCR PCSDD PCSOmega

theorem dictFind_encVals : ∀ (names : List String) (w : List Bool), names.Nodup → w.length = names.length →
    ∀ (i : Nat) (hi : i < names.length),
    dictFind .py (encVals names w) (.str names[i]) = some (.bool (w.getD i false))
  | [], _, _, _, i, hi => by simp at hi
  | x :: xs, [], _, hl, _, _ => by simp at hl
  | x :: xs, b :: bs, hd, hl, 0, _ => by simp [encVals, dictFind, keyEq_str]
  | x :: xs, b :: bs, hd, hl, i + 1, hi => by
      have hx : x ∉ xs := (List.nodup_cons.1 hd).1
      have hi' : i < xs.length := by simp at hi; omega
      have hne : x ≠ xs[i] := fun e => hx (e ▸ List.getElem_mem _)
      have ih := dictFind_encVals xs bs (List.nodup_cons.1 hd).2 (by simpa using hl) i hi'
      simp only [encVals] at ih
      simp [encVals, dictFind, keyEq_str, hne, ih]

theorem lookup_evaluate' (ext : Ext) : lookupFn (pyCtx ext).prog "evaluate" = some py_evaluate := by rfl

/-- The simulation statement for `evaluate` on one formula. -/
def EvalOK (ext : Ext) (names : List String) (D : Addrs) (h : Heap) (A : Nat) (w : List Bool)
    (f : BForm names.length) : Prop :=
  ∀ (k : Nat), fdepth f + 1 ≤ k → ∀ (v : V), FRel D h names v f →
    (interp (pyCtx ext) (k + 1)).call "evaluate" [v, .ref A] h = .ok (.bool (f.eval (envOf w))) h

section
variable (ext : Ext) {names : List String} {D : Addrs} {h : Heap} {A : Nat} {w : List Bool}
  (hnd : names.Nodup) (hw : w.length = names.length) (hA : hget h A = some (.dict (encVals names w)))
include hnd hw hA

theorem eval_atom (i : Fin names.length) : EvalOK ext names D h A w (.atom i) := by
  intro k hk v hv
  obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by omega⟩
  match v, hv with
  | .ref a, ⟨hma, kvs, hg, hop, hsym⟩ =>
  rw [interp_succ_call]
  simp only [callBody, lookup_evaluate', py_evaluate]
  simp only [List.length, List.zip, List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append,
    List.cons_append, ne_eq, not_true, if_false]
  pystep [hg, hop]
  have hin : i.val < names.length := i.isLt
  have hf := dictFind_encVals names w hnd hw i.val hin
  pystep [hg, hsym, hA, hf]
  simp [finishCall, BForm.eval, envOf]

theorem eval_tt : EvalOK ext names D h A w .tt := by
  intro k hk v hv
  obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by omega⟩
  match v, hv with
  | .ref a, ⟨hma, kvs, hg, hop⟩ =>
  rw [interp_succ_call]
  simp only [callBody, lookup_evaluate', py_evaluate]
  simp only [List.length, List.zip, List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append,
    List.cons_append, ne_eq, not_true, if_false]
  pystep [hg, hop]
  pystep []
  pystep [mkSet, dedup, memPy]
  simp [finishCall, BForm.eval]

theorem eval_ff : EvalOK ext names D h A w .ff := by
  intro k hk v hv
  obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by omega⟩
  match v, hv with
  | .ref a, ⟨hma, kvs, hg, hop⟩ =>
  rw [interp_succ_call]
  simp only [callBody, lookup_evaluate', py_evaluate]
  simp only [List.length, List.zip, List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append,
    List.cons_append, ne_eq, not_true, if_false]
  pystep [hg, hop]
  pystep []
  pystep [mkSet, dedup, memPy]
  simp [finishCall, BForm.eval]

theorem eval_not (f : BForm names.length) (ih : EvalOK ext names D h A w f) :
    EvalOK ext names D h A w (.not f) := by
  intro k hk v hv
  obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by omega⟩
  match v, hv with
  | .ref a, ⟨hma, kvs, c, hg, hop, hbody, hc⟩ =>
  rw [interp_succ_call]
  simp only [callBody, lookup_evaluate', py_evaluate]
  simp only [List.length, List.zip, List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append,
    List.cons_append, ne_eq, not_true, if_false]
  pystep [hg, hop]
  pystep []
  pystep [mkSet, dedup, memPy]
  have e1 := ih k' (by simp only [fdepth] at hk; omega) c hc
  pystep [hg, hbody, e1]
  simp [finishCall, BForm.eval]

theorem eval_and (f g : BForm names.length) (ih1 : EvalOK ext names D h A w f)
    (ih2 : EvalOK ext names D h A w g) : EvalOK ext names D h A w (.and f g) := by
  intro k hk v hv
  obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by omega⟩
  match v, hv with
  | .ref a, ⟨hma, kvs, c1, c2, hg, hop, hleft, hright, hc1, hc2⟩ =>
  rw [interp_succ_call]
  simp only [callBody, lookup_evaluate', py_evaluate]
  simp only [List.length, List.zip, List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append,
    List.cons_append, ne_eq, not_true, if_false]
  pystep [hg, hop]
  pystep []
  pystep [mkSet, dedup, memPy]
  pystep []
  have e1 := ih1 k' (by simp only [fdepth] at hk; omega) c1 hc1
  have e2 := ih2 k' (by simp only [fdepth] at hk; omega) c2 hc2
  pystep [hg, hleft, hright, e1, e2]
  pystep []
  cases hf : f.eval (envOf w) <;> cases hg' : g.eval (envOf w) <;> simp [finishCall, BForm.eval, hf, hg']

theorem eval_or (f g : BForm names.length) (ih1 : EvalOK ext names D h A w f)
    (ih2 : EvalOK ext names D h A w g) : EvalOK ext names D h A w (.or f g) := by
  intro k hk v hv
  obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by omega⟩
  match v, hv with
  | .ref a, ⟨hma, kvs, c1, c2, hg, hop, hleft, hright, hc1, hc2⟩ =>
  rw [interp_succ_call]
  simp only [callBody, lookup_evaluate', py_evaluate]
  simp only [List.length, List.zip, List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append,
    List.cons_append, ne_eq, not_true, if_false]
  pystep [hg, hop]
  pystep []
  pystep [mkSet, dedup, memPy]
  pystep []
  have e1 := ih1 k' (by simp only [fdepth] at hk; omega) c1 hc1
  have e2 := ih2 k' (by simp only [fdepth] at hk; omega) c2 hc2
  pystep [hg, hleft, hright, e1, e2]
  pystep []
  cases hf : f.eval (envOf w) <;> cases hg' : g.eval (envOf w) <;> simp [finishCall, BForm.eval, hf, hg']

theorem eval_imp (f g : BForm names.length) (ih1 : EvalOK ext names D h A w f)
    (ih2 : EvalOK ext names D h A w g) : EvalOK ext names D h A w (.imp f g) := by
  intro k hk v hv
  obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by omega⟩
  match v, hv with
  | .ref a, ⟨hma, kvs, c1, c2, hg, hop, hleft, hright, hc1, hc2⟩ =>
  rw [interp_succ_call]
  simp only [callBody, lookup_evaluate', py_evaluate]
  simp only [List.length, List.zip, List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append,
    List.cons_append, ne_eq, not_true, if_false]
  pystep [hg, hop]
  pystep []
  pystep [mkSet, dedup, memPy]
  pystep []
  have e1 := ih1 k' (by simp only [fdepth] at hk; omega) c1 hc1
  have e2 := ih2 k' (by simp only [fdepth] at hk; omega) c2 hc2
  pystep [hg, hleft, hright, e1, e2]
  pystep []
  cases hf : f.eval (envOf w) <;> cases hg' : g.eval (envOf w) <;> simp [finishCall, BForm.eval, hf, hg']

end

/-- **`evaluate` refines `BForm.eval`** on every typed formula tree. -/
theorem eval_sim (ext : Ext) {names : List String} {D : Addrs} {h : Heap} {A : Nat} {w : List Bool}
    (hnd : names.Nodup) (hw : w.length = names.length) (hA : hget h A = some (.dict (encVals names w))) :
    ∀ f : BForm names.length, EvalOK ext names D h A w f
  | .atom i => eval_atom ext hnd hw hA i
  | .tt => eval_tt ext hnd hw hA
  | .ff => eval_ff ext hnd hw hA
  | .not f => eval_not ext hnd hw hA f (eval_sim ext hnd hw hA f)
  | .and f g => eval_and ext hnd hw hA f g (eval_sim ext hnd hw hA f) (eval_sim ext hnd hw hA g)
  | .or f g => eval_or ext hnd hw hA f g (eval_sim ext hnd hw hA f) (eval_sim ext hnd hw hA g)
  | .imp f g => eval_imp ext hnd hw hA f g (eval_sim ext hnd hw hA f) (eval_sim ext hnd hw hA g)

end PCSCR.Py
