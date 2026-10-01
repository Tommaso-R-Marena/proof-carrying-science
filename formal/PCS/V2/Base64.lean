import PCS.V2.Common

/-!
# Canonical base64 (RFC 4648, standard alphabet, with padding)

Production (`pcs/signing_v06.py::decode_canonical_signature_b64`, added by this
refinement after the malleability counterexample) accepts a signature string `s`
only when `base64.b64encode(base64.b64decode(s, validate=True)) == s`.

The Lean checker does the same: `decodeCanonical s = some bs` only when the
Lean encoder maps `bs` back to exactly `s`.  Consequently the accepted spelling
of a byte string is unique (`decodeCanonical_sound`, `decodeCanonical_unique`).
-/

namespace PCS.V2.Base64

def alphabet : List Char :=
  "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/".toList

def sym (n : Nat) : Char := alphabet.getD n 'A'

def symVal (c : Char) : Option Nat := alphabet.idxOf? c

/-- `base64.b64encode`. -/
def encode : List UInt8 → List Char
  | a :: b :: c :: rest =>
    let n := a.toNat * 65536 + b.toNat * 256 + c.toNat
    [sym (n / 262144), sym (n / 4096 % 64), sym (n / 64 % 64), sym (n % 64)] ++ encode rest
  | [a, b] =>
    let n := a.toNat * 65536 + b.toNat * 256
    [sym (n / 262144), sym (n / 4096 % 64), sym (n / 64 % 64), '=']
  | [a] =>
    let n := a.toNat * 65536
    [sym (n / 262144), sym (n / 4096 % 64), '=', '=']
  | [] => []

def encodeStr (bs : List UInt8) : String := String.ofList (encode bs)

/-- A permissive decoder (low bits of the last symbol are ignored, exactly like
    `b64decode`); canonicity is enforced separately. -/
def decode : List Char → Option (List UInt8)
  | [] => some []
  | [c₁, c₂, '=', '='] =>
    match symVal c₁, symVal c₂ with
    | some a, some b => some [UInt8.ofNat ((a * 64 + b) / 16)]
    | _, _ => none
  | [c₁, c₂, c₃, '='] =>
    match symVal c₁, symVal c₂, symVal c₃ with
    | some a, some b, some c =>
      let n := (a * 4096 + b * 64 + c) / 4
      some [UInt8.ofNat (n / 256), UInt8.ofNat (n % 256)]
    | _, _, _ => none
  | c₁ :: c₂ :: c₃ :: c₄ :: rest =>
    match symVal c₁, symVal c₂, symVal c₃, symVal c₄, decode rest with
    | some a, some b, some c, some d, some tl =>
      let n := a * 262144 + b * 4096 + c * 64 + d
      some (UInt8.ofNat (n / 65536) :: UInt8.ofNat (n / 256 % 256) :: UInt8.ofNat (n % 256) :: tl)
    | _, _, _, _, _ => none
  | _ => none

/-- The canonical decoder: only the spelling produced by `encode` is accepted. -/
def decodeCanonical (s : String) : Option (List UInt8) :=
  match decode s.toList with
  | some bs => if encodeStr bs = s then some bs else none
  | none => none

theorem decodeCanonical_sound {s : String} {bs : List UInt8} (h : decodeCanonical s = some bs) :
    encodeStr bs = s := by
  unfold decodeCanonical at h
  split at h
  · split at h
    · cases h; assumption
    · cases h
  · cases h

/-- Non-malleability: two accepted spellings of the same bytes are identical. -/
theorem decodeCanonical_unique {s₁ s₂ : String} {bs : List UInt8}
    (h₁ : decodeCanonical s₁ = some bs) (h₂ : decodeCanonical s₂ = some bs) : s₁ = s₂ :=
  (decodeCanonical_sound h₁).symm.trans (decodeCanonical_sound h₂)

/-- The two spellings of the production counterexample: only the canonical one
    is accepted. -/
example : (decode "AQ==".toList, decode "AR==".toList) = (some [1], some [1]) := by decide
example : decodeCanonical "AQ==" = some [1] := by decide
example : decodeCanonical "AR==" = none := by decide

end PCS.V2.Base64
