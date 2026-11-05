import PCS.V2.ProofGatedCertificate

/-!
# Canonical byte format for PGSC6 certificates

A certificate is serialised as the ASCII bytes of the tagged integer record

  `PGSC6|version|predicate|maxWidth|bound|generation|lo|hi|gainWitness|incLoss|candLoss|`
  `errWitness|errLevel|#corpus|corpus…|#target|target…|#inc|inc bytes…|#cand|cand bytes…`

where every integer uses the verified canonical decimal form of `ProofGatedCodec`,
`#…` are length prefixes, the target network is its `PGSI2-WIDE` integer vector and the
two artifacts are embedded **byte for byte** (each byte as an integer in `[0,255]`).

The decoder parses, then re-encodes and compares (`decodeCert`); so:
* `decodeCert_encodeCert`: roundtrip for every certificate;
* `decodeCert_iff`: `decodeCert bs = some c ↔ encodeCert c = bs`, so a certificate has
  exactly one byte representation, and every other byte string is rejected;
* `encodeCert_injective`;
* `checkCertBytes_sound` / `checkCertBytes_complete`: the byte-level checker inherits the
  guarantees of `checkCert`.
-/

namespace PCS.V2.ProofGatedCertCodec

open PCS.V2.ProofGatedCodec
open PCS.V2.ProofGatedWide
open PCS.V2.ProofGatedStrongGate
open PCS.V2.ProofGatedBytes
open PCS.V2.ProofGatedCertificate
open PCS.V2.ProofGatedNetArtifacts (toInts ofInts ofInts_toInts)

def certTag : List Char := "PGSC6".toList

theorem certTag_pipe_free : '|' ∉ certTag := by decide

theorem certTag_ascii : AsciiChars certTag := by
  intro c hc; revert c; decide

def block (zs : List Int) : List Int := (zs.length : Int) :: zs

def byteI (b : UInt8) : Int := b.toNat

def certToInts (c : Cert) : List Int :=
  [(c.version : Int), (c.predicate : Int), (c.maxWidth : Int), (c.bound : Int),
    (c.generation : Int), c.lo, c.hi, c.gainWitness, (c.incLoss : Int), (c.candLoss : Int),
    c.errWitness, (c.errLevel : Int)] ++
  block c.corpus ++ block (toInts c.target) ++ block (c.incumbent.map byteI) ++
    block (c.candidate.map byteI)

/-! ## Parser -/

def takeNat : List Int → Option (Nat × List Int)
  | z :: r => if 0 ≤ z then some (z.toNat, r) else none
  | [] => none

def takeInt : List Int → Option (Int × List Int)
  | z :: r => some (z, r)
  | [] => none

def takeBlock (zs : List Int) : Option (List Int × List Int) :=
  match takeNat zs with
  | some (n, r) => if n ≤ r.length then some (r.take n, r.drop n) else none
  | none => none

def byteOfInt (z : Int) : Option UInt8 :=
  if 0 ≤ z ∧ z < 256 then some z.toNat.toUInt8 else none

def bytesOfInts (zs : List Int) : Option Bytes := zs.mapM byteOfInt

def parseCert (zs : List Int) : Option Cert := do
  let (version, zs) ← takeNat zs
  let (predicate, zs) ← takeNat zs
  let (maxWidth, zs) ← takeNat zs
  let (bound, zs) ← takeNat zs
  let (generation, zs) ← takeNat zs
  let (lo, zs) ← takeInt zs
  let (hi, zs) ← takeInt zs
  let (gainWitness, zs) ← takeInt zs
  let (incLoss, zs) ← takeNat zs
  let (candLoss, zs) ← takeNat zs
  let (errWitness, zs) ← takeInt zs
  let (errLevel, zs) ← takeNat zs
  let (corpus, zs) ← takeBlock zs
  let (tInts, zs) ← takeBlock zs
  let target ← ofInts tInts
  let (incI, zs) ← takeBlock zs
  let incumbent ← bytesOfInts incI
  let (candI, zs) ← takeBlock zs
  let candidate ← bytesOfInts candI
  if zs = [] then
    some ⟨version, predicate, maxWidth, bound, target, corpus, lo, hi, generation, incumbent,
      candidate, gainWitness, incLoss, candLoss, errWitness, errLevel⟩
  else none

theorem takeNat_nat (n : Nat) (r : List Int) : takeNat ((n : Int) :: r) = some (n, r) := by
  simp [takeNat]

theorem takeBlock_block (b r : List Int) : takeBlock (block b ++ r) = some (b, r) := by
  simp [takeBlock, block, takeNat_nat]

theorem takeBlock_block_nil (b : List Int) : takeBlock (block b) = some (b, []) := by
  have := takeBlock_block b []
  simpa using this

theorem byteOfInt_byteI (b : UInt8) : byteOfInt (byteI b) = some b := by
  have h := b.toNat_lt
  simp only [byteOfInt, byteI]
  rw [if_pos (by omega)]
  simp only [Int.toNat_natCast, Option.some.injEq]
  exact UInt8.ofNat_toNat

theorem bytesOfInts_map (bs : Bytes) : bytesOfInts (bs.map byteI) = some bs := by
  induction bs with
  | nil => rfl
  | cons b bs ih =>
    simp only [bytesOfInts, List.map_cons, List.mapM_cons, byteOfInt_byteI] at ih ⊢
    simp [ih]

theorem parseCert_certToInts (c : Cert) : parseCert (certToInts c) = some c := by
  simp only [certToInts, parseCert, List.cons_append, List.nil_append, List.append_assoc,
    takeNat_nat, takeInt, takeBlock_block, takeBlock_block_nil, ofInts_toInts, bytesOfInts_map,
    Option.bind_eq_bind, Option.bind_some]
  simp

/-! ## Byte codec -/

def encodeCertChars (c : Cert) : List Char := encodeInts certTag (certToInts c)

/-- The canonical byte encoding of a certificate. -/
def encodeCert (c : Cert) : Bytes := (encodeCertChars c).map charToByte

/-- Parse without the canonicity check. -/
def parseCertBytes (bs : Bytes) : Option Cert :=
  if bs.all isAsciiByte then (decodeInts certTag (bs.map byteToChar)).bind parseCert else none

/-- **The certificate decoder**: parse, then require that the bytes are exactly the
canonical encoding of the parsed certificate. -/
def decodeCert (bs : Bytes) : Option Cert :=
  match parseCertBytes bs with
  | some c => if encodeCert c = bs then some c else none
  | none => none

theorem parseCertBytes_encodeCert (c : Cert) : parseCertBytes (encodeCert c) = some c := by
  have ha := asciiChars_encodeInts certTag certTag_ascii (certToInts c)
  unfold parseCertBytes encodeCert encodeCertChars
  rw [if_pos (all_ascii_map_charToByte _ ha), map_byteToChar_charToByte _ ha,
    decodeInts_encodeInts certTag certTag_pipe_free, Option.bind_some, parseCert_certToInts]

/-- **Certificate roundtrip.** -/
theorem decodeCert_encodeCert (c : Cert) : decodeCert (encodeCert c) = some c := by
  simp [decodeCert, parseCertBytes_encodeCert]

/-- **Exact acceptance characterisation** of the certificate decoder. -/
theorem decodeCert_iff (bs : Bytes) (c : Cert) : decodeCert bs = some c ↔ encodeCert c = bs := by
  constructor
  · intro h
    unfold decodeCert at h
    cases hp : parseCertBytes bs with
    | none => simp [hp] at h
    | some c' =>
      by_cases he : encodeCert c' = bs
      · simp [hp, he] at h; subst h; exact he
      · simp [hp, he] at h
  · rintro rfl; exact decodeCert_encodeCert c

theorem encodeCert_injective {c₁ c₂ : Cert} (h : encodeCert c₁ = encodeCert c₂) : c₁ = c₂ := by
  have := decodeCert_encodeCert c₁
  rw [h, decodeCert_encodeCert] at this
  exact (Option.some.inj this).symm

/-! ## The byte-level certificate checker -/

/-- **Byte-level checker**: decode the certificate bytes, then run `checkCert`. -/
def checkCertBytes (S : StrongSpec) (g : Nat) (active : Bytes) (cb : Bytes) : Bool :=
  match decodeCert cb with
  | some c => checkCert S g active c
  | none => false

theorem checkCertBytes_sound {S : StrongSpec} {g : Nat} {active cb : Bytes}
    (h : checkCertBytes S g active cb = true) :
    ∃ c, encodeCert c = cb ∧ HeaderOK S g active c ∧
      ∃ o n, decodeBytes S.arch active = some o ∧ decodeBytes S.arch c.candidate = some n ∧
        encodeBytes o = active ∧ encodeBytes n = c.candidate ∧ StrongAdmissible S o n := by
  unfold checkCertBytes at h
  cases hd : decodeCert cb with
  | none => simp [hd] at h
  | some c =>
    rw [hd] at h
    obtain ⟨hH, o, n, ho, hn, heo, hen, hadm⟩ := checkCert_sound h
    exact ⟨c, (decodeCert_iff cb c).mp hd, hH, o, n, hH.2.2.2.2 ▸ ho, hn, heo, hen, hadm⟩

theorem checkCertBytes_complete (S : StrongSpec) (g : Nat) (o n : WideNet)
    (h : StrongAdmissible S o n) :
    checkCertBytes S g (encodeBytes o) (encodeCert (genCert S g o n)) = true := by
  simp only [checkCertBytes, decodeCert_encodeCert]
  exact checkCert_complete S g o n h

theorem checkCertBytes_malformed (S : StrongSpec) (g : Nat) (active cb : Bytes)
    (h : ∀ c, encodeCert c ≠ cb) : checkCertBytes S g active cb = false := by
  unfold checkCertBytes
  cases hd : decodeCert cb with
  | none => rfl
  | some c => exact absurd ((decodeCert_iff cb c).mp hd) (h c)

/-! ## Fixtures -/

/-- The generated certificate for the first step of the robust chain on `[-10^9,10^9]`. -/
def cert1 : Cert := genCert specWide 0 gen0 r1

theorem cert1_accepted : checkCert specWide 0 (encodeBytes gen0) cert1 = true := by
  decide +kernel

theorem cert1_bytes_accepted :
    checkCertBytes specWide 0 (encodeBytes gen0) (encodeCert cert1) = true := by
  simp only [checkCertBytes, decodeCert_encodeCert]; exact cert1_accepted

/-- The concrete witness values chosen by the generator. -/
theorem cert1_witness :
    cert1.gainWitness = -1 ∧ cert1.incLoss = 34 ∧ cert1.candLoss = 26 ∧
    cert1.errWitness = -1000000000 ∧ cert1.errLevel = 1000000001 := by
  decide +kernel

/-- The complete certificate bytes for this step (225 ASCII bytes; both artifacts are
embedded verbatim as byte values, e.g. `80|71|83|73|50|45|87|73|68|69` is `PGSI2-WIDE`). -/
theorem cert1_text : encodeCert cert1 = ascii ("PGSC6|6|1|8|32|0|-1000000000|1000000000|-1|34|26|" ++
    "-1000000000|1000000001|9|-4|-3|-2|-1|0|1|2|3|4|10|0|2|1|1|-1|1|1|1|-2|-2|12|80|71|83|73|50|" ++
    "45|87|73|68|69|124|48|19|80|71|83|73|50|45|87|73|68|69|124|48|124|45|50|124|48|124|49") := by
  decide +kernel

theorem cert1_size : (encodeCert cert1).length = 225 := by rw [cert1_text]; decide +kernel

/-- Tampering: the same certificate replayed at the next generation is rejected. -/
theorem cert1_replay_rejected :
    checkCert specWide 1 (encodeBytes gen0) cert1 = false :=
  checkCert_stale_rejected _ _ _ _ (by decide)

/-- Tampering: a forged error level that the incumbent does not reach is rejected. -/
theorem cert1_forged_level_rejected :
    checkCert specWide 0 (encodeBytes gen0) { cert1 with errLevel := 2000000000 } = false := by
  decide +kernel

/-- Tampering: a gain witness outside the corpus is rejected. -/
theorem cert1_forged_gain_rejected :
    checkCert specWide 0 (encodeBytes gen0) { cert1 with gainWitness := 7 } = false := by
  decide +kernel

/-- Tampering: claiming a different interval than the deployment configuration. -/
theorem cert1_config_rejected :
    checkCert specWide 0 (encodeBytes gen0) { cert1 with lo := -4, hi := 4 } = false :=
  checkCert_config_rejected _ _ _ _ (by decide)

end PCS.V2.ProofGatedCertCodec
