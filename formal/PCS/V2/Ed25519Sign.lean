import PCS.V2.Ed25519

/-!
# Deterministic Ed25519 signing (RFC 8032 §5.1.5–§5.1.6) — test-fixture generator only

This module is **not** on any authoritative path and no theorem depends on it being
correct: it only *produces* signatures for test fixtures.  Every produced signature is
checked by the authoritative verifier `PCS.V2.Ed25519.verify` (and the RFC 8032 §7.1
TEST 1 vector is reproduced exactly, see `PCS.V2.Witnesses.AISafetyGolden`).

The only key ever used with it is the **public** RFC 8032 §7.1 TEST 1 secret seed, so the
resulting signatures carry no authority beyond "signed with a published test key".
-/

namespace PCS.V2.Ed25519Sign

open PCS.V2.Ed25519

/-- RFC 8032 §5.1.5 scalar clamping of the first half of `SHA-512(seed)`. -/
def clampScalar (h : List UInt8) : Nat :=
  let s := leNat (h.take 32)
  (s - s % 8) % 2 ^ 254 + 2 ^ 254

/-- RFC 8032 §5.1.5 public key of a 32-byte secret seed. -/
def publicKey (seed : List UInt8) : List UInt8 :=
  encode (scalarMul (clampScalar (PCS.V2.SHA512.sha512 seed)) B)

/-- RFC 8032 §5.1.6 deterministic signature. -/
def sign (seed msg : List UInt8) : List UInt8 :=
  let h := PCS.V2.SHA512.sha512 seed
  let a := clampScalar h
  let pk := encode (scalarMul a B)
  let r := leNat (PCS.V2.SHA512.sha512 (h.drop 32 ++ msg)) % L
  let rB := encode (scalarMul r B)
  let k := leNat (PCS.V2.SHA512.sha512 (rB ++ pk ++ msg)) % L
  rB ++ leBytes ((r + k * a) % L) 32

end PCS.V2.Ed25519Sign
