import PCS.V2.Json

/-!
# Canonical JSON: parser/serializer roundtrip and injectivity

* `parseVal_ser`        : the canonical parser inverts `ser` (for enough fuel);
* `parse_ser`           : `parse (ser v) = some v` (completeness of the parser);
* `ser_injective`       : `ser v = ser w → v = w`;
* `jcsBytes_injective`  : `jcsBytes v = jcsBytes w → v = w`.

These are the formal content of "absence of parser ambiguity": the canonical byte
string determines the JSON value uniquely, independently of which JSON parser a
verifier uses, provided that parser's output re-serializes to the received bytes
(exactly the production `canonicalize_jcs_bytes(parse(raw)) == raw` gate).
-/

namespace PCS.V2.Json

/-! ## Digits -/

theorem digitVal_digitChar_all : ∀ d, d < 10 → digitVal (digitChar d) = d := by decide

theorem digitVal_digitChar {d : Nat} (h : d < 10) : digitVal (digitChar d) = d :=
  digitVal_digitChar_all d h

theorem digitChar_isDigit_all : ∀ d, d < 10 → (digitChar d).isDigit = true := by decide

theorem digitChar_isDigit {d : Nat} (h : d < 10) : (digitChar d).isDigit = true :=
  digitChar_isDigit_all d h

theorem ofDigits_decDigits (n : Nat) : ofDigits (decDigits n) = n := by
  rw [decDigits]
  split
  · simp [ofDigits, digitVal_digitChar (by assumption)]
  · have := ofDigits_decDigits (n / 10)
    simp only [ofDigits, List.foldl_append, List.foldl_cons, List.foldl_nil] at this ⊢
    rw [this, digitVal_digitChar (by omega)]
    omega
termination_by n
decreasing_by omega

theorem decDigits_all_digit (n : Nat) : ∀ c ∈ decDigits n, c.isDigit = true := by
  rw [decDigits]
  split
  · simp only [List.mem_singleton]; rintro c rfl; exact digitChar_isDigit (by assumption)
  · intro c hc
    simp only [List.mem_append, List.mem_singleton] at hc
    rcases hc with hc | rfl
    · exact decDigits_all_digit (n / 10) c hc
    · exact digitChar_isDigit (by omega)
termination_by n
decreasing_by omega

theorem decDigits_ne_nil (n : Nat) : decDigits n ≠ [] := by
  rw [decDigits]; split <;> simp

/-- The continuation after a value never starts with a digit. -/
def NoDigitHead (r : List Char) : Prop := ∀ c rest, r = c :: rest → c.isDigit = false

theorem noDigitHead_nil : NoDigitHead [] := by intro c rest h; cases h

theorem noDigitHead_cons {c : Char} {r : List Char} (h : c.isDigit = false) :
    NoDigitHead (c :: r) := by
  intro c' rest h'; cases h'; exact h

theorem spanDigits_append {ds r : List Char} (hd : ∀ c ∈ ds, c.isDigit = true)
    (hr : NoDigitHead r) : spanDigits (ds ++ r) = (ds, r) := by
  induction ds with
  | nil =>
    cases r with
    | nil => rfl
    | cons c rest => simp [spanDigits, hr c rest rfl]
  | cons c ds ih =>
    have hc := hd c (by simp)
    simp [spanDigits, hc, ih (fun x hx => hd x (by simp [hx]))]

theorem parseNat_decDigits (m : Nat) {r : List Char} (hr : NoDigitHead r) :
    parseNat (decDigits m ++ r) = some (m, r) := by
  unfold parseNat
  rw [spanDigits_append (decDigits_all_digit m) hr]
  have hne := decDigits_ne_nil m
  cases h : decDigits m with
  | nil => exact absurd h hne
  | cons d ds => simp only; rw [← h, ofDigits_decDigits]

/-! ## Strings -/

theorem hexVal_hexDigit : ∀ d, d < 16 → hexVal (hexDigit d) = some d := by
  decide

theorem parseStrBody_escChar (c : Char) (rest : List Char) :
    parseStrBody (escChar c ++ rest) =
      (parseStrBody rest).map fun p => (c :: p.1, p.2) := by
  unfold escChar
  split
  · subst_vars; simp [parseStrBody]
  split
  · subst_vars; simp [parseStrBody]
  split
  · subst_vars; simp [parseStrBody]
  split
  · subst_vars; simp [parseStrBody]
  split
  · subst_vars; simp [parseStrBody]
  split
  · subst_vars; simp [parseStrBody]
  split
  · subst_vars; simp [parseStrBody]
  split
  · rename_i h
    have h1 := hexVal_hexDigit (c.toNat / 16) (by omega)
    have h2 := hexVal_hexDigit (c.toNat % 16) (by omega)
    have hc : Char.ofNat (16 * (c.toNat / 16) + c.toNat % 16) = c := by
      rw [show 16 * (c.toNat / 16) + c.toNat % 16 = c.toNat by omega]
      exact Char.ofNat_toNat c
    simp only [List.cons_append]
    rw [parseStrBody]
    simp only [h1, h2, hc, List.nil_append]
  · rename_i h1 h2 h3 h4 h5 h6 h7 h8
    simp only [List.cons_append, List.nil_append]
    rw [parseStrBody.eq_def]
    split <;> simp_all

theorem parseStrBody_escStr (cs : List Char) (r : List Char) :
    parseStrBody (escStr cs ++ '"' :: r) = some (cs, r) := by
  induction cs with
  | nil => simp [escStr, parseStrBody]
  | cons c cs ih =>
    simp only [escStr, List.append_assoc]
    rw [parseStrBody_escChar, ih]
    rfl

theorem parseStrBody_serStr (s : String) (r : List Char) :
    parseStrBody (escStr s.toList ++ '"' :: r) = some (s.toList, r) :=
  parseStrBody_escStr _ _

/-! ## Sizes (fuel bound) -/

mutual
def size : JVal → Nat
  | .arr [] => 1
  | .arr (x :: xs) => 1 + size x + sizeElemsTail xs
  | .obj [] => 1
  | .obj ((_, v) :: ms) => 1 + size v + sizeMembersTail ms
  | _ => 1
def sizeElemsTail : List JVal → Nat
  | [] => 1
  | x :: xs => 1 + size x + sizeElemsTail xs
def sizeMembersTail : List (String × JVal) → Nat
  | [] => 1
  | (_, v) :: ms => 1 + size v + sizeMembersTail ms
end

/-! ## Value roundtrip -/

private theorem digit_ne {d : Char} (hd : d.isDigit = true) :
    d ≠ 'n' ∧ d ≠ 't' ∧ d ≠ 'f' ∧ d ≠ '"' ∧ d ≠ '[' ∧ d ≠ '{' ∧ d ≠ '-' := by
  refine ⟨?_, ?_, ?_, ?_, ?_, ?_, ?_⟩ <;> (rintro rfl; revert hd; decide)

mutual
theorem parseVal_ser : ∀ (v : JVal) (n : Nat) (r : List Char),
    size v ≤ n → NoDigitHead r → parseVal n (ser v ++ r) = some (v, r)
  | .null, n + 1, r, _, _ => by simp [ser, parseVal]
  | .null, 0, r, h, _ => by simp [size] at h
  | .bool true, n + 1, r, _, _ => by simp [ser, parseVal]
  | .bool false, n + 1, r, _, _ => by simp [ser, parseVal]
  | .bool _, 0, r, h, _ => by simp [size] at h
  | .num i, n + 1, r, _, hr => by
    simp only [ser, serNum]
    split
    · rename_i hi
      simp only [List.cons_append, parseVal]
      simp only [Char.reduceEq, ↓reduceIte, parseNat_decDigits _ hr, Option.map_some]
      congr; omega
    · rename_i hi
      have hne := decDigits_ne_nil i.natAbs
      have hall := decDigits_all_digit i.natAbs
      cases hds : decDigits i.natAbs with
      | nil => exact absurd hds hne
      | cons d ds =>
        have hd : d.isDigit = true := hall d (by rw [hds]; simp)
        obtain ⟨h1, h2, h3, h4, h5, h6, h7⟩ := digit_ne hd
        simp only [List.cons_append, parseVal, h1, h2, h3, h4, h5, h6, h7, hd, ↓reduceIte]
        rw [← List.cons_append, ← hds, parseNat_decDigits _ hr]
        simp only [Option.map_some]
        congr; omega
  | .num _, 0, r, h, _ => by simp [size] at h
  | .str s, n + 1, r, _, _ => by
    simp only [ser, serStr, List.cons_append, List.append_assoc,
      parseVal]
    simp [parseStrBody_serStr]
  | .str _, 0, r, h, _ => by simp [size] at h
  | .arr [], n + 1, r, _, _ => by simp [ser, parseVal]
  | .arr [], 0, r, h, _ => by simp [size] at h
  | .arr (x :: xs), n + 1, r, h, hr => by
    simp only [size] at h
    have hx := parseVal_ser x n (serElemsTail xs ++ r) (by omega) (by
      cases xs <;> simp only [serElemsTail, List.cons_append] <;>
        exact noDigitHead_cons (by decide))
    have hxs := parseElemsTail_ser xs n r (by omega)
    have hne : ∀ r', ser x ++ (serElemsTail xs ++ r) ≠ ']' :: r' := by
      intro r' heq
      rw [heq] at hx
      cases n with
      | zero => simp [parseVal] at hx
      | succ n => simp [parseVal] at hx
    simp only [ser, List.cons_append, parseVal, Char.reduceEq, ↓reduceIte]
    rw [List.append_assoc, hx]
    simp only
    rw [hxs]
  | .arr (_ :: _), 0, r, h, _ => by simp [size] at h
  | .obj [], n + 1, r, _, _ => by simp [ser, parseVal]
  | .obj [], 0, r, h, _ => by simp [size] at h
  | .obj ((k, v) :: ms), n + 1, r, h, hr => by
    simp only [size] at h
    have hv := parseVal_ser v n (serMembersTail ms ++ r) (by omega) (by
      cases ms <;> simp only [serMembersTail, List.cons_append] <;>
        exact noDigitHead_cons (by decide))
    have hms := parseMembersTail_ser ms n r (by omega)
    simp only [ser, serStr, List.cons_append, List.append_assoc,
      parseVal, Char.reduceEq, ↓reduceIte]
    rw [parseStrBody_serStr]
    simp only [List.nil_append]
    rw [hv]
    simp only
    rw [hms]
    simp
  | .obj (_ :: _), 0, r, h, _ => by simp [size] at h

theorem parseElemsTail_ser : ∀ (xs : List JVal) (n : Nat) (r : List Char),
    sizeElemsTail xs ≤ n → parseElemsTail n (serElemsTail xs ++ r) = some (xs, r)
  | [], n + 1, r, _ => by simp [serElemsTail, parseElemsTail]
  | [], 0, r, h => by simp [sizeElemsTail] at h
  | x :: xs, n + 1, r, h => by
    simp only [sizeElemsTail] at h
    have hx := parseVal_ser x n (serElemsTail xs ++ r) (by omega) (by
      cases xs <;> simp only [serElemsTail, List.cons_append] <;>
        exact noDigitHead_cons (by decide))
    have hxs := parseElemsTail_ser xs n r (by omega)
    simp only [serElemsTail, List.cons_append, List.append_assoc, parseElemsTail]
    rw [hx]
    simp only
    rw [hxs]
  | _ :: _, 0, r, h => by simp [sizeElemsTail] at h

theorem parseMembersTail_ser : ∀ (ms : List (String × JVal)) (n : Nat) (r : List Char),
    sizeMembersTail ms ≤ n → parseMembersTail n (serMembersTail ms ++ r) = some (ms, r)
  | [], n + 1, r, _ => by simp [serMembersTail, parseMembersTail]
  | [], 0, r, h => by simp [sizeMembersTail] at h
  | (k, v) :: ms, n + 1, r, h => by
    simp only [sizeMembersTail] at h
    have hv := parseVal_ser v n (serMembersTail ms ++ r) (by omega) (by
      cases ms <;> simp only [serMembersTail, List.cons_append] <;>
        exact noDigitHead_cons (by decide))
    have hms := parseMembersTail_ser ms n r (by omega)
    simp only [serMembersTail, serStr, List.cons_append, List.append_assoc,
      parseMembersTail]
    rw [parseStrBody_serStr]
    simp only [List.nil_append]
    rw [hv]
    simp only
    rw [hms]
    simp
  | _ :: _, 0, r, h => by simp [sizeMembersTail] at h
end

/-! ## Injectivity -/

/-- The canonical JSON serializer is injective. -/
theorem ser_injective {v w : JVal} (h : ser v = ser w) : v = w := by
  have hv := parseVal_ser v (size v + size w) [] (by omega) noDigitHead_nil
  have hw := parseVal_ser w (size v + size w) [] (by omega) noDigitHead_nil
  rw [h] at hv
  rw [hv] at hw
  simpa using hw

theorem utf8Encode_injective {l l' : List Char} (h : l.utf8Encode = l'.utf8Encode) :
    l = l' := by
  rw [← String.toByteArray_ofList, ← String.toByteArray_ofList] at h
  have := String.toByteArray_inj.mp h
  have := congrArg String.toList this
  simpa using this

/-- The canonical UTF-8 byte encoding is injective. -/
theorem jcsBytes_injective {v w : JVal} (h : jcsBytes v = jcsBytes w) : v = w :=
  ser_injective (utf8Encode_injective h)

/-! ## Parser completeness -/

private theorem decDigits_length_pos (n : Nat) : 1 ≤ (decDigits n).length := by
  have := decDigits_ne_nil n
  cases h : decDigits n with
  | nil => exact absurd h this
  | cons _ _ => simp

mutual
theorem size_le_length : ∀ v : JVal, size v ≤ (ser v).length
  | .null => by simp [size, ser]
  | .bool true => by simp [size, ser]
  | .bool false => by simp [size, ser]
  | .num i => by
    simp only [size, ser, serNum]
    have := decDigits_length_pos i.natAbs
    split <;> simp <;> omega
  | .str s => by simp [size, ser, serStr]
  | .arr [] => by simp [size, ser]
  | .arr (x :: xs) => by
    have := size_le_length x
    have := sizeElemsTail_le_length xs
    simp only [size, ser, List.length_cons, List.length_append]
    omega
  | .obj [] => by simp [size, ser]
  | .obj ((k, v) :: ms) => by
    have := size_le_length v
    have := sizeMembersTail_le_length ms
    simp only [size, ser, List.length_cons, List.length_append]
    omega
theorem sizeElemsTail_le_length : ∀ xs : List JVal, sizeElemsTail xs ≤ (serElemsTail xs).length
  | [] => by simp [sizeElemsTail, serElemsTail]
  | x :: xs => by
    have := size_le_length x
    have := sizeElemsTail_le_length xs
    simp only [sizeElemsTail, serElemsTail, List.length_cons, List.length_append]
    omega
theorem sizeMembersTail_le_length :
    ∀ ms : List (String × JVal), sizeMembersTail ms ≤ (serMembersTail ms).length
  | [] => by simp [sizeMembersTail, serMembersTail]
  | (k, v) :: ms => by
    have := size_le_length v
    have := sizeMembersTail_le_length ms
    simp only [sizeMembersTail, serMembersTail, List.length_cons, List.length_append]
    omega
end

/-- The canonical parser accepts every canonical serialization (completeness). -/
theorem parse_ser (v : JVal) : parse (ser v) = some v := by
  unfold parse
  have := parseVal_ser v ((ser v).length + 1) [] (by have := size_le_length v; omega)
    noDigitHead_nil
  simp only [List.append_nil] at this
  rw [this]

/-- Parser soundness, stated as uniqueness: if the parser returns `v` on the
    canonical text of `w`, then `v = w`. -/
theorem parse_ser_unique {v w : JVal} (h : parse (ser w) = some v) : v = w := by
  rw [parse_ser] at h; exact (Option.some.inj h).symm

end PCS.V2.Json
