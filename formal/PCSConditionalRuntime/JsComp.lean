import PCSConditionalRuntime.JsPrem

/-!
# Array comprehensions (JavaScript `map` / `filter` callbacks)

The JavaScript lowering turns `xs.map(x => e)` and `xs.filter(x => p)` into comprehensions.
As for Python (`PCSCR.Py.comp_eval`), `jcomp_eval` computes the result for *pure* element and
filter expressions; the iterable may be an array on the heap or an immutable tuple value (the
index list `%indices` of `premises.map((_, i) => i)`).
-/

namespace PCSCR.Js

open PCSCR PCSDD PCSOmega PCSCR.Py

/-- `e` evaluates to `w` (without heap effects) whenever `x` is bound to `y`, the other local
names are as in `env`, and the heap extends `h`. -/
def JEvalPure (ext : Ext) (K0 : Nat) (h : Heap) (env : Env) (x : String) (y : V) (e : E) (w : V) : Prop :=
  ∀ k', K0 ≤ k' → ∀ (env' : Env) (H : Heap), env'.get x = some y → (∀ z, z ≠ x → env'.get z = env.get z) →
    HAgree h H → evalE (jsCtx ext) (interp (jsCtx ext) k') env' H e = .ok w H

/-- The (optional) filter selects `b`. -/
def JFiltOK (ext : Ext) (K0 : Nat) (h : Heap) (env : Env) (x : String) (y : V) : Option E → Bool → Prop
  | none, b => b = true
  | some fe, b => JEvalPure ext K0 h env x y fe (.bool b)

/-- The iterable `vi` enumerates `xs` on every heap extending `h`. -/
def IterOK (h : Heap) (vi : V) (xs : List V) : Prop :=
  ∀ (H : Heap), HAgree h H → ∀ j, elemAt H vi j = .ok xs[j]?

theorem IterOK.ref {h : Heap} {L : Nat} {xs : List V} (hL : hget h L = some (.list xs)) :
    IterOK h (.ref L) xs := fun H hag j => by
  simp [elemAt, hag.2 L (hget_lt hL), hL]

theorem IterOK.tup (h : Heap) (xs : List V) : IterOK h (.tup xs) xs := fun _ _ _ => rfl

theorem jcomp_loop (ext : Ext) (h : Heap) (env : Env) (x : String) (vi : V) (xs : List V) (elt : E)
    (filt : Option E) (g : V → V) (p : V → Bool) (K0 : Nat) (hit : IterOK h vi xs)
    (helt : ∀ y ∈ xs, JEvalPure ext K0 h env x y elt (g y))
    (hfilt : ∀ y ∈ xs, JFiltOK ext K0 h env x y filt (p y)) :
    ∀ (ys acc : List V) (j k : Nat) (env' : Env), xs.drop j = ys → K0 + ys.length + 1 ≤ k →
      (∀ z, z ≠ x → env'.get z = env.get z) →
      ∃ env'', (interp (jsCtx ext) k).forLoop env' (h ++ [.list acc]) (.name x) vi j
          (compBody h.length elt filt) =
        .ok (.normal env'') (h ++ [.list (acc ++ (ys.filter p).map g)])
  | [], acc, j, k, env', hys, hk, henv => by
      obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by simp at hk; omega⟩
      rw [interp_succ_forLoop]
      have hj : xs[j]? = none := by
        have := congrArg List.length hys; simp at this
        exact List.getElem?_eq_none (by omega)
      have he := hit (h ++ [.list acc]) (HAgree.of_prefix rfl) j
      exact ⟨env', by simp [forIter, he, hj]⟩
  | y :: ys, acc, j, k, env', hys, hk, henv => by
      obtain ⟨k', rfl⟩ : ∃ k', k = k' + 1 := ⟨k - 1, by simp at hk; omega⟩
      rw [interp_succ_forLoop]
      have hj : xs[j]? = some y := by
        have := congrArg (fun l => l[0]?) hys; simpa using this
      have hy : y ∈ xs := List.mem_of_getElem? hj
      have hK : K0 ≤ k' := by simp at hk; omega
      have hag : HAgree h (h ++ [.list acc]) := HAgree.of_prefix rfl
      have hel := hit (h ++ [.list acc]) hag j
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
        obtain ⟨env'', ih⟩ := jcomp_loop ext h env x vi xs elt none g p K0 hit helt hfilt ys (acc ++ [g y])
          (j + 1) k' (env'.set x y) hys' (by simp at hk; omega) hx2
        refine ⟨env'', ?_⟩
        simp only [forIter, hel, hj, bindE, assignT, compBody, execB, execS,
          evalE, evalL, he, Out.bind, bindS, hacc, builtinMethod, hset_eq, seqF, loopK]
        simp only [compBody] at ih
        rw [ih]; simp [hp]
      | some fe =>
        have hf := hfilt y hy k' hK (env'.set x y) _ hx1 hx2 hag
        obtain ⟨env'', ih⟩ := jcomp_loop ext h env x vi xs elt (some fe) g p K0 hit helt hfilt ys
          (if p y then acc ++ [g y] else acc) (j + 1) k' (env'.set x y) hys' (by simp at hk; omega) hx2
        refine ⟨env'', ?_⟩
        cases hpy : p y with
        | true =>
          simp only [hpy, if_true, compBody] at ih
          simp only [forIter, hel, hj, bindE, assignT, compBody, execB, execS,
            evalE, evalL, he, hf, Out.bind, bindS, hacc, builtinMethod, hset_eq, seqF, loopK, truthy, hpy,
            if_true]
          rw [ih]; simp [hpy]
        | false =>
          simp only [hpy, Bool.false_eq_true, if_false, compBody] at ih
          simp only [forIter, hel, hj, bindE, assignT, compBody, execB, execS,
            evalE, evalL, hf, Out.bind, bindS, seqF, loopK, truthy, hpy, Bool.false_eq_true, if_false]
          rw [ih]; simp [hpy]

/-- **Comprehension over an iterable.** -/
theorem jcomp_eval (ext : Ext) (k : Nat) (env : Env) (h : Heap) (x : String) (it elt : E) (filt : Option E)
    (vi : V) (xs : List V) (g : V → V) (p : V → Bool) (K0 : Nat)
    (hev : evalE (jsCtx ext) (interp (jsCtx ext) k) env h it = .ok vi h)
    (hit : IterOK h vi xs) (hk : K0 + xs.length + 1 ≤ k)
    (helt : ∀ y ∈ xs, JEvalPure ext K0 h env x y elt (g y))
    (hfilt : ∀ y ∈ xs, JFiltOK ext K0 h env x y filt (p y)) :
    evalE (jsCtx ext) (interp (jsCtx ext) k) env h (.comp elt x it filt) =
      .ok (.ref h.length) (h ++ [.list ((xs.filter p).map g)]) := by
  obtain ⟨env'', e⟩ := jcomp_loop ext h env x vi xs elt filt g p K0 hit helt hfilt xs [] 0 k env rfl hk
    (fun _ _ => rfl)
  simp only [evalE, hev, Out.bind, e, compResult, List.nil_append]

end PCSCR.Js
