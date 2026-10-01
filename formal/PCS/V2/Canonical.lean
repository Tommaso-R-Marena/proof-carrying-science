import PCS.V2.SHA256

/-!
# The v0.6 canonical-byte gate

`parseCanonicalBytes` is the Lean counterpart of the production
`_parse_canonical_json_bytes` / `parse_normalized_wire_bytes_v06` prefix:

```
len(raw) ≤ limit ; no BOM ; strict UTF-8 ; strict JSON (no duplicate keys,
no NaN/Infinity) ; canonicalize_jcs_bytes(value) == raw
```

Lean decides the same acceptance condition directly: the bytes must be the
canonical UTF-8 serialization of a value whose objects have strictly increasing
UTF-16 keys (hence no duplicates), whose strings contain no Unicode
noncharacters (surrogates are not Lean `Char`s), and whose numbers are safe
integers.

Soundness of this gate does **not** depend on the UTF-8 decoder or on the JSON
parser: acceptance re-checks `jcsBytes v = raw` byte-for-byte.
-/

namespace PCS.V2.Canonical

open PCS.V2.Json

/-- UTF-16 code units of a character (surrogate pair above the BMP). -/
def utf16Units (c : Char) : List Nat :=
  let n := c.toNat
  if n < 0x10000 then [n]
  else [0xD800 + (n - 0x10000) / 0x400, 0xDC00 + (n - 0x10000) % 0x400]

def keyUnits (s : String) : List Nat := s.toList.flatMap utf16Units

def lexLt : List Nat → List Nat → Bool
  | [], [] => false
  | [], _ :: _ => true
  | _ :: _, [] => false
  | a :: as, b :: bs => a < b || (a == b && lexLt as bs)

/-- Strictly increasing UTF-16 order (RFC 8785 §3.2.3); strictness excludes duplicates. -/
def keysSorted : List String → Bool
  | k₁ :: k₂ :: ks => lexLt (keyUnits k₁) (keyUnits k₂) && keysSorted (k₂ :: ks)
  | _ => true

/-- Characters admitted by the PCS I-JSON profile (`_validate_unicode_string`). -/
def validChar (c : Char) : Bool :=
  let n := c.toNat
  !(0xFDD0 ≤ n && n ≤ 0xFDEF) && !(n % 0x10000 == 0xFFFE) && !(n % 0x10000 == 0xFFFF)

def validString (s : String) : Bool := s.toList.all validChar

def maxSafeInt : Nat := 2 ^ 53

mutual
def canonical : JVal → Bool
  | .null => true
  | .bool _ => true
  | .num i => decide (i.natAbs ≤ maxSafeInt)
  | .str s => validString s
  | .arr xs => canonicalList xs
  | .obj ms => keysSorted (ms.map Prod.fst) && canonicalMembers ms
def canonicalList : List JVal → Bool
  | [] => true
  | x :: xs => canonical x && canonicalList xs
def canonicalMembers : List (String × JVal) → Bool
  | [] => true
  | (k, v) :: ms => validString k && canonical v && canonicalMembers ms
end

/-- The canonical-byte gate. -/
def parseCanonicalBytes (maxBytes : Nat) (raw : ByteArray) : Option JVal :=
  if raw.size ≤ maxBytes then
    match String.fromUTF8? raw with
    | none => none
    | some s =>
      match parse s.toList with
      | none => none
      | some v => if canonical v ∧ jcsBytes v = raw then some v else none
  else none

/-- Gate soundness: accepted bytes are exactly the canonical bytes of a canonical value. -/
theorem parseCanonicalBytes_sound {maxBytes : Nat} {raw : ByteArray} {v : JVal}
    (h : parseCanonicalBytes maxBytes raw = some v) :
    raw = jcsBytes v ∧ canonical v = true ∧ raw.size ≤ maxBytes := by
  unfold parseCanonicalBytes at h
  split at h
  · rename_i hsize
    split at h
    · cases h
    · split at h
      · cases h
      · split at h
        · rename_i hc
          cases h
          exact ⟨hc.2.symm, hc.1, hsize⟩
        · cases h
  · cases h

/-- No parser ambiguity: any JSON value whose canonical bytes are the accepted
    bytes is the value the gate returned. -/
theorem parseCanonicalBytes_unique {maxBytes : Nat} {raw : ByteArray} {v w : JVal}
    (h : parseCanonicalBytes maxBytes raw = some v) (hw : jcsBytes w = raw) : w = v := by
  obtain ⟨hraw, _, _⟩ := parseCanonicalBytes_sound h
  exact jcsBytes_injective (hw.trans hraw)

theorem fromUTF8?_utf8Encode (l : List Char) :
    String.fromUTF8? l.utf8Encode = some (String.ofList l) := by
  have hv : l.utf8Encode.IsValidUTF8 := ByteArray.isValidUTF8_utf8Encode
  simp only [String.fromUTF8?, hv, dite_true, Option.some.injEq]
  apply String.toByteArray_inj.mp
  rw [String.toByteArray_ofList]
  rfl

/-- Gate completeness: canonical bytes of a canonical value within the limit are accepted. -/
theorem parseCanonicalBytes_complete {maxBytes : Nat} {v : JVal}
    (hc : canonical v = true) (hs : (jcsBytes v).size ≤ maxBytes) :
    parseCanonicalBytes maxBytes (jcsBytes v) = some v := by
  unfold parseCanonicalBytes
  simp only [hs, ↓reduceIte]
  unfold jcsBytes
  rw [fromUTF8?_utf8Encode]
  simp only [String.toList_ofList, parse_ser, hc, true_and, ↓reduceIte]

end PCS.V2.Canonical
