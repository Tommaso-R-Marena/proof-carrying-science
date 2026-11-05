import PCSConditionalRuntime.PyPrem

/-!
# List comprehensions

`[elt for x in it if filt]` allocates a fresh accumulator list and runs a `for` loop that
appends.  `comp_eval` computes the result for *pure* element and filter expressions (their value
may depend on the heap, which only grows by the accumulator, but they do not change it).
-/

namespace PCSCR.Py

open PCSCR PCSDD PCSOmega

/-- `e` evaluates to `w` (without heap effects) whenever `x` is bound to `y`, the other local
names are as in `env`, and the heap extends `h`. -/
def EvalPure (ext : Ext) (K0 : Nat) (h : Heap) (env : Env) (x : String) (y : V) (e : E) (w : V) : Prop :=
  ∀ k', K0 ≤ k' → ∀ (env' : Env) (H : Heap), env'.get x = some y → (∀ z, z ≠ x → env'.get z = env.get z) →
    HAgree h H → evalE (pyCtx ext) (interp (pyCtx ext) k') env' H e = .ok w H

/-- The (optional) filter selects `b`. -/
def FiltOK (ext : Ext) (K0 : Nat) (h : Heap) (env : Env) (x : String) (y : V) : Option E → Bool → Prop
  | none, b => b = true
  | some fe, b => EvalPure ext K0 h env x y fe (.bool b)

theorem comp_loop (ext : Ext) (h : Heap) (env : Env) (x : String) (L : Nat) (xs : List V) (elt : E)
    (filt : Option E) (g : V → V) (p : V → Bool) (K0 : Nat) (hL : hget h L = some (.list xs))
    (helt : ∀ y ∈ xs, EvalPure ext K0 h env x y elt (g y))
    (hfilt : ∀ y ∈ xs, FiltOK ext K0 h env x y filt (p y)) :
    ∀ (ys acc : List V) (j k : Nat) (env' : Env), xs.drop j = ys → K0 + ys.length + 1 ≤ k →
      (∀ z, z ≠ x → env'.get z = env.get z) →
      ∃ env'', (interp (pyCtx ext) k).forLoop env' (h ++ [.list acc]) (.name x) (.ref L) j
          (compBody h.length elt filt) =
        .ok (.normal env'') (h ++ [.list (acc ++ (ys.filter p).map g)])
  | [], acc, j, k, env', hys, hk, henv => by
      obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by simp at hk; omega⟩
      rw [interp_succ_forLoop]
      have hj : xs[j]? = none := by
        have := congrArg List.length hys; simp at this
        exact List.getElem?_eq_none (by omega)
      have hLt := hget_lt hL
      exact ⟨env', by simp [forIter, elemAt, hget_append_lt _ hLt, hL, hj]⟩
  | y :: ys, acc, j, k, env', hys, hk, henv => by
      obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by simp at hk; omega⟩
      rw [interp_succ_forLoop]
      have hj : xs[j]? = some y := by
        have := congrArg (fun l => l[0]?) hys; simpa using this
      have hy : y ∈ xs := List.mem_of_getElem? hj
      have hLt := hget_lt hL
      have hK : K0 ≤ k' := by simp at hk; omega
      have hag : HAgree h (h ++ [.list acc]) := HAgree.of_prefix rfl
      have hx1 : (env'.set x y).get x = some y := by simp
      have hx2 : ∀ z, z ≠ x → (env'.set x y).get z = env.get z := fun z hz => by
        simp [Ne.symm hz, henv z hz]
      have he := helt y hy k' hK (env'.set x y) _ hx1 hx2 hag
      have hys' : xs.drop (j + 1) = ys := by rw [← List.drop_drop, hys]; simp
      have hacc : hget (h ++ [.list acc]) h.length = some (.list acc) := by simp [hget]
      have hset_eq : ∀ l, hset (h ++ [.list acc]) h.length (.list l) = h ++ [.list l] := by
        intro l; simp [hset]
      cases filt with
      | none =>
        have hp : p y = true := hfilt y hy
        obtain ⟨env'', ih⟩ := comp_loop ext h env x L xs elt none g p K0 hL helt hfilt ys (acc ++ [g y])
          (j + 1) k' (env'.set x y) hys' (by simp at hk; omega) hx2
        refine ⟨env'', ?_⟩
        simp only [forIter, elemAt, hget_append_lt _ hLt, hL, hj, bindE, assignT, compBody, execB, execS,
          evalE, evalL, he, Out.bind, bindS, hacc, builtinMethod, hset_eq, seqF, loopK]
        simp only [compBody] at ih
        rw [ih]; simp [hp]
      | some fe =>
        have hf := hfilt y hy k' hK (env'.set x y) _ hx1 hx2 hag
        obtain ⟨env'', ih⟩ := comp_loop ext h env x L xs elt (some fe) g p K0 hL helt hfilt ys
          (if p y then acc ++ [g y] else acc) (j + 1) k' (env'.set x y) hys' (by simp at hk; omega) hx2
        refine ⟨env'', ?_⟩
        cases hpy : p y with
        | true =>
          simp only [hpy, if_true, compBody] at ih
          simp only [forIter, elemAt, hget_append_lt _ hLt, hL, hj, bindE, assignT, compBody, execB, execS,
            evalE, evalL, he, hf, Out.bind, bindS, hacc, builtinMethod, hset_eq, seqF, loopK, truthy, hpy,
            if_true]
          rw [ih]; simp [hpy]
        | false =>
          simp only [hpy, Bool.false_eq_true, if_false, compBody] at ih
          simp only [forIter, elemAt, hget_append_lt _ hLt, hL, hj, bindE, assignT, compBody, execB, execS,
            evalE, evalL, hf, Out.bind, bindS, seqF, loopK, truthy, hpy, Bool.false_eq_true, if_false]
          rw [ih]; simp [hpy]

/-- **Comprehension over a list.** -/
theorem comp_eval (ext : Ext) (k : Nat) (env : Env) (h : Heap) (x : String) (it elt : E) (filt : Option E)
    (L : Nat) (xs : List V) (g : V → V) (p : V → Bool) (K0 : Nat)
    (hit : evalE (pyCtx ext) (interp (pyCtx ext) k) env h it = .ok (.ref L) h)
    (hL : hget h L = some (.list xs)) (hk : K0 + xs.length + 1 ≤ k)
    (helt : ∀ y ∈ xs, EvalPure ext K0 h env x y elt (g y))
    (hfilt : ∀ y ∈ xs, FiltOK ext K0 h env x y filt (p y)) :
    evalE (pyCtx ext) (interp (pyCtx ext) k) env h (.comp elt x it filt) =
      .ok (.ref h.length) (h ++ [.list ((xs.filter p).map g)]) := by
  obtain ⟨env'', e⟩ := comp_loop ext h env x L xs elt filt g p K0 hL helt hfilt xs [] 0 k env rfl hk
    (fun _ _ => rfl)
  simp only [evalE, hit, Out.bind, e, compResult, List.nil_append]

end PCSCR.Py
