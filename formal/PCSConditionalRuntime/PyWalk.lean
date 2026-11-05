import PCSConditionalRuntime.PyProofBase

/-!
# The witness walk of `Diagram.world` and the false-first reference witness

`pyWalk` is the loop `while root >= 2: … values[names[var]] = low == 0; root = high if low == 0
else low` written as a fuelled Lean function over the values dictionary.  `pyWalk_world`
proves that, on a valid diagram, starting from `dict.fromkeys(names, False)` it produces
exactly the reference witness `world n ns u = some (wit n ns 0 u)` as a name → bool dictionary,
counts exactly `witSteps n ns 0 u` iterations and stops at the terminal `1` (so the
`assert root == 1` holds).
-/

namespace PCSCR.Py

open PCSCR PCSDD PCSOmega

/-- The dictionary `{names[i]: vals[i]}` (insertion order = order of `names`). -/
def encVals (names : List String) (vals : List Bool) : List (V × V) :=
  (names.zip vals).map (fun p => (.str p.1, .bool p.2))

/-- Python's `while root >= 2` witness walk (fuel = maximal number of iterations). -/
def pyWalk (names : List String) (ns : Nodes) : Nat → Nat → List (V × V) → Nat → List (V × V) × Nat × Nat
  | 0, u, kvs, st => (kvs, st, u)
  | f + 1, u, kvs, st =>
    if 2 ≤ u then
      match getNode ns u with
      | some nd => pyWalk names ns f (if nd.low = 0 then nd.high else nd.low)
          (dictSet .py kvs (.str (names.getD nd.var "")) (.bool (nd.low == 0))) (st + 1)
      | none => (kvs, st, u)
    else (kvs, st, u)

theorem keyEq_str (a b : String) : keyEq .py (.str a) (.str b) = decide (a = b) := by
  by_cases h : a = b <;> simp [keyEq, eqD, eqPy, h]

theorem dictSet_encVals : ∀ (names : List String) (vals : List Bool), names.Nodup →
    vals.length = names.length → ∀ (k : Nat), k < names.length → ∀ (b : Bool),
    dictSet .py (encVals names vals) (.str (names.getD k "")) (.bool b) = encVals names (vals.set k b)
  | [], _, _, _, k, hk, _ => by simp at hk
  | x :: xs, [], _, hl, _, _, _ => by simp at hl
  | x :: xs, v :: vs, hd, hl, 0, _, b => by
      simp [encVals, dictSet, keyEq_str]
  | x :: xs, v :: vs, hd, hl, k + 1, hk, b => by
      have hx : x ∉ xs := (List.nodup_cons.1 hd).1
      have hk' : k < xs.length := by simp at hk; omega
      have hne : x ≠ xs.getD k "" := by
        rw [List.getD_eq_getElem?_getD, List.getElem?_eq_getElem hk', Option.getD_some]
        exact fun e => hx (e ▸ List.getElem_mem _)
      have ih := dictSet_encVals xs vs (List.nodup_cons.1 hd).2 (by simpa using hl) k hk' b
      simp only [encVals, List.zip_cons_cons, List.map_cons, dictSet, keyEq_str, hne,
        decide_false, Bool.false_eq_true, if_false, List.getD_cons_succ, List.set_cons_succ]
      simp only [encVals] at ih
      rw [ih]

theorem dictSet_absent {k : V} (v : V) : ∀ (kvs : List (V × V)), (∀ p ∈ kvs, keyEq .py p.1 k = false) →
    dictSet .py kvs k v = kvs ++ [(k, v)]
  | [], _ => rfl
  | (k', v') :: rest, h => by
      simp only [dictSet, h (k', v') (by simp), Bool.false_eq_true, if_false, List.cons_append]
      rw [dictSet_absent v rest (fun p hp => h p (by simp [hp]))]

theorem encVals_append (a b : List String) (va vb : List Bool) (h : va.length = a.length) :
    encVals (a ++ b) (va ++ vb) = encVals a va ++ encVals b vb := by
  simp [encVals, List.zip_append h.symm]

/-- `dict.fromkeys(names, False)`. -/
theorem fromkeys_encVals : ∀ (pre names : List String), (pre ++ names).Nodup →
    (names.map V.str).foldl (fun kvs k => dictSet .py kvs k (.bool false))
      (encVals pre (List.replicate pre.length false)) =
    encVals (pre ++ names) (List.replicate (pre ++ names).length false)
  | pre, [], _ => by simp
  | pre, x :: xs, hd => by
      simp only [List.map_cons, List.foldl_cons]
      have hx : x ∉ pre := by
        intro hm; have := (List.nodup_append.1 hd).2.2 x hm x (by simp); exact this rfl
      have e : dictSet .py (encVals pre (List.replicate pre.length false)) (.str x) (.bool false) =
          encVals (pre ++ [x]) (List.replicate (pre ++ [x]).length false) := by
        rw [dictSet_absent]
        · rw [show (pre ++ [x]).length = pre.length + 1 by simp, List.replicate_succ',
            encVals_append _ _ _ _ (by simp)]
          simp [encVals]
        · intro p hp
          simp only [encVals, List.mem_map] at hp
          obtain ⟨q, hq, rfl⟩ := hp
          have := List.of_mem_zip hq
          rw [keyEq_str]; simp only [decide_eq_false_iff_not]
          exact fun e => hx (e ▸ this.1)
      rw [e]
      have := fromkeys_encVals (pre ++ [x]) xs (by simpa using hd)
      simpa using this

theorem take_succ_of_getElem {vals : List Bool} {k : Nat} {b : Bool} (h : vals[k]? = some b) :
    vals.take (k + 1) = vals.take k ++ [b] := by
  rw [List.take_add_one, h]; rfl

theorem take_set_succ : ∀ (l : List Bool) (k : Nat) (b : Bool), k < l.length →
    (l.set k b).take (k + 1) = l.take k ++ [b]
  | [], k, b, h => by simp at h
  | x :: xs, 0, b, _ => by simp
  | x :: xs, k + 1, b, h => by
      have := take_set_succ xs k b (by simp at h; omega)
      simp [this]

/-- **The Python walk computes the false-first witness and its step count.** -/
theorem pyWalk_wit {names : List String} {ns : Nodes} (hv : Valid names.length ns) (hnd : names.Nodup) :
    ∀ d k u (vals : List Bool) st f, names.length - k = d → u < ns.size + 2 → u ≠ 0 →
      k ≤ topVar names.length ns u → vals.length = names.length →
      vals.drop k = List.replicate (names.length - k) false → d ≤ f →
      pyWalk names ns f u (encVals names vals) st =
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
    cases f <;> simp [pyWalk, ht]
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
        have hb := dictSet_encVals names vals hnd hl nd.var hkn (nd.low == 0)
        have hset1 : (vals.set nd.var (nd.low == 0)).drop (nd.var + 1) =
            List.replicate (names.length - (nd.var + 1)) false := by
          rw [List.drop_set_of_lt (by omega)]; exact hdrop1
        have htake : (vals.set nd.var (nd.low == 0)).take (nd.var + 1) = vals.take nd.var ++ [nd.low == 0] :=
          take_set_succ vals nd.var _ (by omega)
        simp only [pyWalk, h2, if_true, hg, hb]
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

/-- **`Diagram.world`'s walk from `dict.fromkeys(names, False)`.** -/
theorem pyWalk_world {names : List String} {ns : Nodes} (hv : Valid names.length ns) (hnd : names.Nodup)
    {u : Nat} (hu : u < ns.size + 2) (h0 : u ≠ 0) (st f : Nat) (hf : names.length ≤ f) :
    pyWalk names ns f u (encVals names (List.replicate names.length false)) st =
      (encVals names (wit names.length ns 0 u), st + witSteps names.length ns 0 u, 1) := by
  have := pyWalk_wit hv hnd names.length 0 u (List.replicate names.length false) st f (by omega) hu h0
    (Nat.zero_le _) (by simp) (by simp) hf
  simpa using this

end PCSCR.Py
