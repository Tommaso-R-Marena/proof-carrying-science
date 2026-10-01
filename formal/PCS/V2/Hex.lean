import PCS.V2.JsonRoundtrip

/-!
# Lower-case hexadecimal digests

Production renders every SHA-256 digest with Python `hashlib...hexdigest()`:
exactly 64 lower-case hex characters.  This module proves that

* `hexDecode` accepts only lower-case hex of even length and that it is a left
  inverse of `hexEncode` (`hexDecode_hexEncode`), hence `hexEncode` is injective;
* a successfully decoded string *is* the lower-case hex encoding of the decoded
  bytes (`hexEncode_of_hexDecode`): a 64-hex field denotes exactly one 32-byte
  value, with no alternative (upper-case, truncated, padded) spelling.
-/

namespace PCS.V2.Hex

open PCS.V2.Json

def byteChars (b : UInt8) : List Char := [hexDigit (b.toNat / 16), hexDigit (b.toNat % 16)]

def hexChars : List UInt8 → List Char
  | [] => []
  | b :: bs => byteChars b ++ hexChars bs

def hexEncode (bs : List UInt8) : String := String.ofList (hexChars bs)

def decodeChars : List Char → Option (List UInt8)
  | [] => some []
  | a :: b :: rest =>
    match hexVal a, hexVal b with
    | some x, some y => (decodeChars rest).map fun t => UInt8.ofNat (16 * x + y) :: t
    | _, _ => none
  | [_] => none

def hexDecode (s : String) : Option (List UInt8) := decodeChars s.toList

theorem hexVal_hexDigit' {d : Nat} (h : d < 16) : hexVal (hexDigit d) = some d :=
  hexVal_hexDigit d h

theorem decodeChars_hexChars (bs : List UInt8) : decodeChars (hexChars bs) = some bs := by
  induction bs with
  | nil => rfl
  | cons b bs ih =>
    have hb := b.toNat_lt
    simp only [hexChars, byteChars, List.cons_append, List.nil_append, decodeChars,
      hexVal_hexDigit' (show b.toNat / 16 < 16 by omega),
      hexVal_hexDigit' (show b.toNat % 16 < 16 by omega), ih, Option.map_some]
    congr
    rw [show 16 * (b.toNat / 16) + b.toNat % 16 = b.toNat by omega]
    simp

theorem hexDecode_hexEncode (bs : List UInt8) : hexDecode (hexEncode bs) = some bs := by
  simp [hexDecode, hexEncode, decodeChars_hexChars]

theorem hexEncode_injective {a b : List UInt8} (h : hexEncode a = hexEncode b) : a = b := by
  have ha := hexDecode_hexEncode a
  rw [h, hexDecode_hexEncode] at ha
  exact (Option.some.inj ha).symm

/-- `hexVal` only accepts characters it could have produced. -/
theorem hexDigit_of_hexVal {c : Char} {d : Nat} (h : hexVal c = some d) :
    d < 16 ∧ hexDigit d = c := by
  unfold hexVal at h
  split at h
  · rename_i hc
    cases h
    obtain ⟨h1, h2⟩ := hc
    have h1' : 48 ≤ c.toNat := by
      have := (Char.le_def).mp h1; simpa [Char.toNat] using this
    have h2' : c.toNat ≤ 57 := by
      have := (Char.le_def).mp h2; simpa [Char.toNat] using this
    refine ⟨by omega, ?_⟩
    simp only [hexDigit, show c.toNat - 48 < 10 by omega, ↓reduceIte]
    rw [show 48 + (c.toNat - 48) = c.toNat by omega]
    exact Char.ofNat_toNat c
  · split at h
    · rename_i _ hc
      cases h
      obtain ⟨h1, h2⟩ := hc
      have h1' : 97 ≤ c.toNat := by
        have := (Char.le_def).mp h1; simpa [Char.toNat] using this
      have h2' : c.toNat ≤ 102 := by
        have := (Char.le_def).mp h2; simpa [Char.toNat] using this
      refine ⟨by omega, ?_⟩
      simp only [hexDigit, show ¬ (c.toNat - 87 < 10) by omega, ↓reduceIte]
      rw [show 87 + (c.toNat - 87) = c.toNat by omega]
      exact Char.ofNat_toNat c
    · cases h

theorem hexChars_of_decodeChars : ∀ {cs : List Char} {bs : List UInt8},
    decodeChars cs = some bs → hexChars bs = cs
  | [], bs, h => by simp [decodeChars] at h; subst h; rfl
  | [_], _, h => by simp [decodeChars] at h
  | a :: b :: rest, bs, h => by
    simp only [decodeChars] at h
    split at h
    · rename_i x y hx hy
      obtain ⟨hx16, hxa⟩ := hexDigit_of_hexVal hx
      obtain ⟨hy16, hyb⟩ := hexDigit_of_hexVal hy
      cases ht : decodeChars rest with
      | none => rw [ht] at h; cases h
      | some t =>
        rw [ht] at h
        simp only [Option.map_some, Option.some.injEq] at h
        subst h
        have := hexChars_of_decodeChars ht
        have hn : (UInt8.ofNat (16 * x + y)).toNat = 16 * x + y := by
          simp [UInt8.toNat_ofNat]; omega
        simp only [hexChars, byteChars, hn, List.cons_append, List.nil_append, this]
        rw [show (16 * x + y) / 16 = x by omega, show (16 * x + y) % 16 = y by omega, hxa, hyb]
    · cases h

/-- A decoded hex string is exactly the lower-case encoding of its bytes. -/
theorem hexEncode_of_hexDecode {s : String} {bs : List UInt8} (h : hexDecode s = some bs) :
    hexEncode bs = s := by
  unfold hexEncode
  rw [hexChars_of_decodeChars h]
  simp

theorem length_hexChars (bs : List UInt8) : (hexChars bs).length = 2 * bs.length := by
  induction bs with
  | nil => rfl
  | cons b bs ih => simp [hexChars, byteChars, ih]; omega

end PCS.V2.Hex
