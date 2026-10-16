import PCSConditionalRuntime.JsRun
import PCSConditionalRuntime.PyProofBase

/-!
# String keys of the JavaScript `Diagram`: `[v,lo,hi].join(',')` is injective

The JavaScript unique table and memo cache are `Map`s keyed by the comma-joined decimal strings
of their components.  Decimal numerals contain no comma and determine their value, so the keys
determine the tuples (`jukey_inj`, `jmkey_inj`).
-/

namespace PCSCR.Js

open PCSCR PCSDD PCSCR.Py

/-- Value of a list of decimal digit characters. -/
def digVal (cs : List Char) : Nat := cs.foldl (fun acc c => acc * 10 + (c.toNat - 48)) 0

theorem digVal_append_single (cs : List Char) (c : Char) :
    digVal (cs ++ [c]) = digVal cs * 10 + (c.toNat - 48) := by
  simp [digVal, List.foldl_append]

theorem char_ofNat_digit {d : Nat} (hd : d < 10) : (Char.ofNat (48 + d)).toNat = 48 + d := by
  have hv : Nat.isValidChar (48 + d) := Or.inl (by omega)
  simp [Char.ofNat, hv, Char.ofNatAux, Char.toNat]
  omega

theorem decDigits_val : ∀ (f n : Nat), n < 10 ^ f → digVal (decDigits f n) = n
  | 0, n, h => by simp at h; subst h; rfl
  | f + 1, n, h => by
      unfold decDigits
      by_cases hn : n < 10
      · simp only [hn, if_true, digVal, List.foldl]
        rw [char_ofNat_digit hn]; omega
      · simp only [hn, if_false]
        rw [digVal_append_single, decDigits_val f (n / 10) (by rw [Nat.pow_succ] at h; omega),
          char_ofNat_digit (Nat.mod_lt _ (by omega))]
        omega

theorem decDigits_noComma : ∀ (f n : Nat), ',' ∉ decDigits f n
  | 0, _ => by simp [decDigits]
  | f + 1, n => by
      unfold decDigits
      by_cases hn : n < 10
      · simp only [hn, if_true, List.mem_singleton]
        intro h
        have := congrArg Char.toNat h
        rw [char_ofNat_digit hn] at this
        simp at this
        omega
      · simp only [hn, if_false, List.mem_append, List.mem_singleton, not_or]
        refine ⟨decDigits_noComma f (n / 10), fun h => ?_⟩
        have := congrArg Char.toNat h
        rw [char_ofNat_digit (Nat.mod_lt _ (by omega))] at this
        simp at this
        omega

theorem lt_ten_pow (n : Nat) : n < 10 ^ (n + 1) := by
  induction n with
  | zero => decide
  | succ k ih => rw [Nat.pow_succ]; omega

theorem jsIntStr_nat (n : Nat) : jsIntStr (n : Int) = String.ofList (decDigits (n + 1) n) := by
  simp [jsIntStr]

theorem jsIntStr_nat_inj {a b : Nat} (h : jsIntStr (a : Int) = jsIntStr (b : Int)) : a = b := by
  rw [jsIntStr_nat, jsIntStr_nat] at h
  have h2 := congrArg (fun s => digVal s.toList) h
  simp only [String.toList_ofList] at h2
  rwa [decDigits_val _ _ (lt_ten_pow a), decDigits_val _ _ (lt_ten_pow b)] at h2

theorem jsIntStr_noComma (n : Nat) : ',' ∉ (jsIntStr (n : Int)).toList := by
  rw [jsIntStr_nat, String.toList_ofList]; exact decDigits_noComma _ _

/-- Splitting at the first comma. -/
theorem split_comma : ∀ {a a' b b' : List Char}, ',' ∉ a → ',' ∉ a' →
    a ++ ',' :: b = a' ++ ',' :: b' → a = a' ∧ b = b'
  | [], [], _, _, _, _, h => by simp at h; exact ⟨rfl, h⟩
  | [], c :: a', _, _, _, h2, h => by
      simp at h; exact absurd (h.1 ▸ List.mem_cons_self) h2
  | c :: a, [], _, _, h1, _, h => by
      simp at h; exact absurd (h.1 ▸ List.mem_cons_self) h1
  | c :: a, c' :: a', _, _, h1, h2, h => by
      simp only [List.cons_append, List.cons.injEq] at h
      obtain ⟨e, r⟩ := split_comma (fun hm => h1 (List.mem_cons_of_mem _ hm))
        (fun hm => h2 (List.mem_cons_of_mem _ hm)) h.2
      exact ⟨by rw [h.1, e], r⟩

theorem toList_join3 (a b c : String) :
    (a ++ "," ++ (b ++ "," ++ c)).toList = a.toList ++ ',' :: (b.toList ++ ',' :: c.toList) := by
  have hc : ",".toList = [','] := by decide
  simp [String.toList_append, hc]

theorem join3_inj {a b c a' b' c' : String} (ha : ',' ∉ a.toList) (ha' : ',' ∉ a'.toList)
    (hb : ',' ∉ b.toList) (hb' : ',' ∉ b'.toList)
    (h : a ++ "," ++ (b ++ "," ++ c) = a' ++ "," ++ (b' ++ "," ++ c')) : a = a' ∧ b = b' ∧ c = c' := by
  have h2 := congrArg String.toList h
  rw [toList_join3, toList_join3] at h2
  obtain ⟨e1, r1⟩ := split_comma ha ha' h2
  obtain ⟨e2, r2⟩ := split_comma hb hb' r1
  refine ⟨?_, ?_, ?_⟩
  · rw [← String.ofList_toList (s := a), e1, String.ofList_toList]
  · rw [← String.ofList_toList (s := b), e2, String.ofList_toList]
  · rw [← String.ofList_toList (s := c), r2, String.ofList_toList]

/-- Unique-table key `[v,lo,hi].join(',')`. -/
def jukey (v lo hi : Nat) : V :=
  .str (jsIntStr (v : Int) ++ "," ++ (jsIntStr (lo : Int) ++ "," ++ jsIntStr (hi : Int)))

/-- Memo key `[op,a,b].join(',')`. -/
def jmkey (op : BOp) (a b : Nat) : V :=
  .str (op.name ++ "," ++ (jsIntStr (a : Int) ++ "," ++ jsIntStr (b : Int)))

theorem jukey_inj {v lo hi v' lo' hi' : Nat} (h : jukey v lo hi = jukey v' lo' hi') :
    v = v' ∧ lo = lo' ∧ hi = hi' := by
  simp only [jukey, V.str.injEq] at h
  obtain ⟨e1, e2, e3⟩ := join3_inj (jsIntStr_noComma v) (jsIntStr_noComma v') (jsIntStr_noComma lo)
    (jsIntStr_noComma lo') h
  exact ⟨jsIntStr_nat_inj e1, jsIntStr_nat_inj e2, jsIntStr_nat_inj e3⟩

theorem BOp.name_noComma (op : BOp) : ',' ∉ op.name.toList := by
  cases op <;> decide

theorem jmkey_inj {op op' : BOp} {a b a' b' : Nat} (h : jmkey op a b = jmkey op' a' b') :
    op = op' ∧ a = a' ∧ b = b' := by
  simp only [jmkey, V.str.injEq] at h
  obtain ⟨e1, e2, e3⟩ := join3_inj (BOp.name_noComma op) (BOp.name_noComma op') (jsIntStr_noComma a)
    (jsIntStr_noComma a') h
  exact ⟨BOp.name_inj e1, jsIntStr_nat_inj e2, jsIntStr_nat_inj e3⟩

theorem jsJoin_ukey (v lo hi : Nat) :
    jsJoin "," [iv v, iv lo, iv hi] = some (jsIntStr (v : Int) ++ "," ++ (jsIntStr (lo : Int) ++ "," ++ jsIntStr (hi : Int))) :=
  rfl

theorem jsJoin_mkey (op : BOp) (a b : Nat) :
    jsJoin "," [.str op.name, iv a, iv b] = some (op.name ++ "," ++ (jsIntStr (a : Int) ++ "," ++ jsIntStr (b : Int))) :=
  rfl

/-! ## `Map`s with string keys -/

theorem keyEq_js_str (k : V) (s : String) : keyEq .js k (.str s) = decide (k = .str s) := by
  cases k <;> simp [keyEq, eqD, eqJs]
  rename_i s'
  by_cases e : s' = s <;> simp [e]

theorem dictFind_js_set (kvs : List (V × V)) (s t : String) (v : V) :
    dictFind .js (dictSet .js kvs (.str s) v) (.str t) =
      if s = t then some v else dictFind .js kvs (.str t) := by
  induction kvs with
  | nil => by_cases e : s = t <;> simp [dictSet, dictFind, keyEq_js_str, e]
  | cons p rest ih =>
    obtain ⟨k, w⟩ := p
    simp only [dictSet, keyEq_js_str]
    by_cases e : k = .str s
    · subst e
      by_cases e2 : s = t
      · subst e2; simp [dictFind, keyEq_js_str]
      · simp [dictFind, keyEq_js_str, e2]
    · simp only [e, decide_false, Bool.false_eq_true, if_false, dictFind, keyEq_js_str]
      rw [ih]
      by_cases e2 : k = .str t
      · subst e2
        have : s ≠ t := fun h => e (h ▸ rfl)
        simp [this]
      · simp [e2]

end PCSCR.Js
