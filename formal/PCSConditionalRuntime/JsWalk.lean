import PCSConditionalRuntime.JsConj
import PCSConditionalRuntime.PyWalk

/-!
# The witness walk of the JavaScript `Diagram.world`

`jsWalk` is `while(root>=2){…values[this.names[v]]=lo===0;root=lo===0?hi:lo;}` over the values
object (an insertion-ordered string-keyed dictionary).  As for Python (`PCSCR.Py.pyWalk_world`),
on a valid diagram starting from the all-`false` object it produces exactly the reference
witness and counts exactly `witSteps` iterations, stopping at the terminal `1`.
-/

namespace PCSCR.Js

open PCSCR PCSDD PCSOmega PCSCR.Py


/-- JavaScript's `while(root>=2)` witness walk (fuel = maximal number of iterations). -/
def jsWalk (names : List String) (ns : Nodes) : Nat → Nat → List (V × V) → Nat → List (V × V) × Nat × Nat
  | 0, u, kvs, st => (kvs, st, u)
  | f + 1, u, kvs, st =>
    if 2 ≤ u then
      match getNode ns u with
      | some nd => jsWalk names ns f (if nd.low = 0 then nd.high else nd.low)
          (dictSet .js kvs (.str (names.getD nd.var "")) (.bool (nd.low == 0))) (st + 1)
      | none => (kvs, st, u)
    else (kvs, st, u)

/-- The walk never decreases the step counter. -/
theorem jsWalk_st_le (names : List String) (ns : Nodes) :
    ∀ (f u : Nat) (kvs : List (V × V)) (st : Nat), st ≤ (jsWalk names ns f u kvs st).2.1
  | 0, _, _, _ => by simp [jsWalk]
  | f + 1, u, kvs, st => by
    simp only [jsWalk]
    split
    · split
      · rename_i nd _
        have := jsWalk_st_le names ns f (if nd.low = 0 then nd.high else nd.low)
          (dictSet .js kvs (.str (names.getD nd.var "")) (.bool (nd.low == 0))) (st + 1)
        omega
      · exact Nat.le_refl _
    · exact Nat.le_refl _

theorem jkeyEq_str (a b : String) : keyEq .js (.str a) (.str b) = decide (a = b) := by
  by_cases h : a = b <;> simp [keyEq, eqD, eqJs, h]

theorem jdictSet_encVals : ∀ (names : List String) (vals : List Bool), names.Nodup →
    vals.length = names.length → ∀ (k : Nat), k < names.length → ∀ (b : Bool),
    dictSet .js (encVals names vals) (.str (names.getD k "")) (.bool b) = encVals names (vals.set k b)
  | [], _, _, _, k, hk, _ => by simp at hk
  | x :: xs, [], _, hl, _, _, _ => by simp at hl
  | x :: xs, v :: vs, hd, hl, 0, _, b => by
      simp [encVals, dictSet, jkeyEq_str]
  | x :: xs, v :: vs, hd, hl, k + 1, hk, b => by
      have hx : x ∉ xs := (List.nodup_cons.1 hd).1
      have hk' : k < xs.length := by simp at hk; omega
      have hne : x ≠ xs.getD k "" := by
        rw [List.getD_eq_getElem?_getD, List.getElem?_eq_getElem hk', Option.getD_some]
        exact fun e => hx (e ▸ List.getElem_mem _)
      have ih := jdictSet_encVals xs vs (List.nodup_cons.1 hd).2 (by simpa using hl) k hk' b
      simp only [encVals, List.zip_cons_cons, List.map_cons, dictSet, jkeyEq_str, hne,
        decide_false, Bool.false_eq_true, if_false, List.getD_cons_succ, List.set_cons_succ]
      simp only [encVals] at ih
      rw [ih]

theorem jdictSet_absent {k : V} (v : V) : ∀ (kvs : List (V × V)), (∀ p ∈ kvs, keyEq .js p.1 k = false) →
    dictSet .js kvs k v = kvs ++ [(k, v)]
  | [], _ => rfl
  | (k', v') :: rest, h => by
      simp only [dictSet, h (k', v') (by simp), Bool.false_eq_true, if_false, List.cons_append]
      rw [jdictSet_absent v rest (fun p hp => h p (by simp [hp]))]

/-- `Object.fromEntries(names.map(n=>[n,false]))` as a left fold of `Map` updates. -/
theorem jfromkeys_encVals : ∀ (pre names : List String), (pre ++ names).Nodup →
    (names.map V.str).foldl (fun kvs k => dictSet .js kvs k (.bool false))
      (encVals pre (List.replicate pre.length false)) =
    encVals (pre ++ names) (List.replicate (pre ++ names).length false)
  | pre, [], _ => by simp
  | pre, x :: xs, hd => by
      simp only [List.map_cons, List.foldl_cons]
      have hx : x ∉ pre := by
        intro hm; have := (List.nodup_append.1 hd).2.2 x hm x (by simp); exact this rfl
      have e : dictSet .js (encVals pre (List.replicate pre.length false)) (.str x) (.bool false) =
          encVals (pre ++ [x]) (List.replicate (pre ++ [x]).length false) := by
        rw [jdictSet_absent]
        · rw [show (pre ++ [x]).length = pre.length + 1 by simp, List.replicate_succ',
            encVals_append _ _ _ _ (by simp)]
          simp [encVals]
        · intro p hp
          simp only [encVals, List.mem_map] at hp
          obtain ⟨q, hq, rfl⟩ := hp
          have := List.of_mem_zip hq
          rw [jkeyEq_str]; simp only [decide_eq_false_iff_not]
          exact fun e => hx (e ▸ this.1)
      rw [e]
      have := jfromkeys_encVals (pre ++ [x]) xs (by simpa using hd)
      simpa using this

/-- **The JavaScript walk computes the false-first witness and its step count.** -/
theorem jsWalk_wit {names : List String} {ns : Nodes} (hv : Valid names.length ns) (hnd : names.Nodup) :
    ∀ d k u (vals : List Bool) st f, names.length - k = d → u < ns.size + 2 → u ≠ 0 →
      k ≤ topVar names.length ns u → vals.length = names.length →
      vals.drop k = List.replicate (names.length - k) false → d ≤ f →
      jsWalk names ns f u (encVals names vals) st =
        (encVals names (vals.take k ++ wit names.length ns k u), st + witSteps names.length ns k u, 1) := by
  intro d
  induction d with
  | zero =>
    intro k u vals st f hd hu h0 hk hl hdrop _
    have htv := topVar_le hv u
    have hu1 : u = 1 := by
      by_cases h2 : 2 ≤ u
      · obtain ⟨nd, hg⟩ := getNode_some_of_ge2 h2 hu
        have := (hv.node hg).1; rw [topVar_node hg] at hk; omega
      · omega
    subst hu1
    rw [wit_eq, if_neg (by omega), witSteps_eq, if_neg (by omega)]
    have ht : vals.take k = vals := List.take_of_length_le (by omega)
    cases f <;> simp [jsWalk, ht]
  | succ d ih =>
    intro k u vals st f hd hu h0 hk hl hdrop hf
    have hkn : k < names.length := by omega
    have hvk : vals[k]? = some false := by
      have : (vals.drop k)[0]? = some false := by
        rw [hdrop, List.getElem?_replicate]; simp; omega
      simpa using this
    have hdrop1 : vals.drop (k + 1) = List.replicate (names.length - (k + 1)) false := by
      rw [← List.drop_drop, hdrop, List.drop_replicate]; congr 1
    by_cases h2 : 2 ≤ u
    · obtain ⟨nd, hg⟩ := getNode_some_of_ge2 h2 hu
      obtain ⟨hvn, hlo, hhi, hne, htl, hth⟩ := hv.node hg
      have htv : topVar names.length ns u = nd.var := topVar_node hg
      rw [htv] at hk
      by_cases hvar : nd.var = k
      · subst hvar
        obtain ⟨f', rfl⟩ : ∃ f', f = f' + 1 := ⟨f - 1, by omega⟩
        have hb := jdictSet_encVals names vals hnd hl nd.var hkn (nd.low == 0)
        have hset1 : (vals.set nd.var (nd.low == 0)).drop (nd.var + 1) =
            List.replicate (names.length - (nd.var + 1)) false := by
          rw [List.drop_set_of_lt (by omega)]; exact hdrop1
        have htake : (vals.set nd.var (nd.low == 0)).take (nd.var + 1) = vals.take nd.var ++ [nd.low == 0] :=
          take_set_succ vals nd.var _ (by omega)
        simp only [jsWalk, h2, if_true, hg, hb]
        rw [wit_eq names.length ns nd.var u, if_pos hkn, hg, witSteps_eq names.length ns nd.var u, if_pos hkn, hg]
        simp only [if_true]
        by_cases hl0 : nd.low = 0
        · have := ih (nd.var + 1) nd.high _ (st + 1) f' (by omega) (by omega) (by omega) (by omega)
            (by simp [hl]) hset1 (by omega)
          rw [if_pos hl0, this, htake]
          simp [hl0, Nat.add_assoc]
        · have := ih (nd.var + 1) nd.low _ (st + 1) f' (by omega) (by omega) hl0 (by omega)
            (by simp [hl]) hset1 (by omega)
          rw [if_neg hl0, this, htake, show (nd.low == 0) = false from by simp [hl0]]
          simp [hl0, Nat.add_assoc]
      · have hk' : k + 1 ≤ topVar names.length ns u := by rw [htv]; omega
        have := ih (k + 1) u vals st f (by omega) hu h0 hk' hl hdrop1 (by omega)
        rw [this, wit_eq names.length ns k u, if_pos hkn, hg, witSteps_eq names.length ns k u, if_pos hkn, hg]
        simp only [hvar, if_false, take_succ_of_getElem hvk, List.append_assoc, List.singleton_append]
    · have hu1 : u = 1 := by omega
      subst hu1
      have hg : getNode ns 1 = none := by simp [getNode]
      have hk' : k + 1 ≤ topVar names.length ns 1 := by rw [topVar_terminal _ _ (by omega)]; omega
      have := ih (k + 1) 1 vals st f (by omega) hu h0 hk' hl hdrop1 (by omega)
      rw [this, wit_eq names.length ns k 1, if_pos hkn, hg, witSteps_eq names.length ns k 1, if_pos hkn, hg]
      simp only [take_succ_of_getElem hvk, List.append_assoc, List.singleton_append]

/-- **`Diagram.world`'s walk from the all-`false` values object.** -/
theorem jsWalk_world {names : List String} {ns : Nodes} (hv : Valid names.length ns) (hnd : names.Nodup)
    {u : Nat} (hu : u < ns.size + 2) (h0 : u ≠ 0) (st f : Nat) (hf : names.length ≤ f) :
    jsWalk names ns f u (encVals names (List.replicate names.length false)) st =
      (encVals names (wit names.length ns 0 u), st + witSteps names.length ns 0 u, 1) := by
  have := jsWalk_wit hv hnd names.length 0 u (List.replicate names.length false) st f (by omega) hu h0
    (Nat.zero_le _) (by simp) (by simp) hf
  simpa using this

end PCSCR.Js
