import PCS.V2.ProofGatedNetArtifacts

/-!
# Byte-level canonical PGSI2-WIDE artifacts

`ProofGatedNetArtifacts` fixes the canonical *text* of a width-`n` network. This module
lowers the format to **bytes** (`List UInt8`), which is what a file, a socket or a hash
function actually sees.

Byte format: the canonical text, one byte per character, all bytes ASCII (`< 128`):

  `PGSI2-WIDE|outBias|w₁|b₁|o₁|…`   as the bytes `0x50 0x47 0x53 0x49 0x32 …`

The byte decoder `decodeBytes` first rejects any byte `≥ 128` (so UTF-8 multi-byte
sequences, byte-order marks and Latin-1 look-alikes never reach the parser), then maps
bytes to characters and runs the verified canonical text decoder.

Main results (every architecture bound, every network of every width):
* `asciiChars_encodeChars`: the canonical text of every network is pure ASCII;
* `decodeBytes_encodeBytes`: byte roundtrip for every valid network;
* `decodeBytes_iff`: the byte decoder accepts `bs` with result `m` **iff** `m` is valid
  and `bs` is *exactly* `encodeBytes m`. Consequently every malformed byte string
  (non-ASCII bytes, wrong tag, missing or extra fields, non-canonical integers such as
  `007`, `-0`, `+1`, leading/trailing separators, out-of-range parameters, over-width
  networks) is rejected, with no case analysis on the kind of malformation;
* `encodeBytes_injective`: distinct networks have distinct byte artifacts;
* `inferBytes_encodeBytes` / `inferBytes_sound`: byte-level inference is exactly
  `predict` of the unique network that the bytes canonically encode;
* `decodeBytes_arch_mono`: an artifact accepted under an architecture bound is accepted,
  with the same network, under every larger bound (and `arch_mismatch_fixture` shows the
  converse fails).
-/

namespace PCS.V2.ProofGatedBytes

open PCS.V2.ProofGatedCodec
open PCS.V2.ProofGatedWide
open PCS.V2.ProofGatedNetArtifacts

/-- Raw artifact bytes. -/
abbrev Bytes := List UInt8

def byteToChar (b : UInt8) : Char := Char.ofNat b.toNat

def charToByte (c : Char) : UInt8 := c.toNat.toUInt8

def isAsciiByte (b : UInt8) : Bool := decide (b.toNat < 128)

theorem byteToChar_charToByte (c : Char) (h : c.toNat < 128) :
    byteToChar (charToByte c) = c := by
  unfold byteToChar charToByte
  rw [Nat.toUInt8, UInt8.toNat_ofNat', Nat.mod_eq_of_lt (by omega)]
  exact Char.ofNat_toNat c

theorem charToByte_byteToChar (b : UInt8) (h : b.toNat < 128) :
    charToByte (byteToChar b) = b := by
  unfold byteToChar charToByte
  have : (Char.ofNat b.toNat).toNat = b.toNat := by
    have hv : b.toNat.isValidChar := Or.inl (by omega)
    simp [Char.ofNat, hv, Char.ofNatAux, Char.toNat]
  rw [this]; exact UInt8.ofNat_toNat

/-! ## The canonical text is ASCII -/

/-- Every character of a list is ASCII. -/
def AsciiChars (l : List Char) : Prop := ∀ c ∈ l, c.toNat < 128

theorem digitChar_ascii (d : Nat) (h : d < 10) : (Nat.digitChar d).toNat < 128 := by
  match d, h with
  | 0, _ => decide
  | 1, _ => decide
  | 2, _ => decide
  | 3, _ => decide
  | 4, _ => decide
  | 5, _ => decide
  | 6, _ => decide
  | 7, _ => decide
  | 8, _ => decide
  | 9, _ => decide

theorem renderNat_ascii (n : Nat) : AsciiChars (renderNat n) := by
  induction n using Nat.strongRecOn with
  | _ n ih =>
      intro c hc
      rw [renderNat_step] at hc
      simp only [List.mem_append, List.mem_singleton] at hc
      rcases hc with hm | hm
      · by_cases h0 : n / 10 = 0
        · simp [h0] at hm
        · simp only [h0, if_false] at hm
          exact ih (n / 10) (by omega) c hm
      · subst hm; exact digitChar_ascii _ (Nat.mod_lt n (by decide))

theorem renderInt_ascii (z : Int) : AsciiChars (renderInt z) := by
  cases z with
  | ofNat n => exact renderNat_ascii n
  | negSucc n =>
      intro c hc
      simp only [renderInt, List.mem_cons] at hc
      rcases hc with rfl | hc
      · decide
      · exact renderNat_ascii _ c hc

theorem joinFields_ascii : ∀ fs : List (List Char), (∀ f ∈ fs, AsciiChars f) →
    AsciiChars (joinFields fs)
  | [], _ => fun _ h => by simp [joinFields] at h
  | [f], h => by simpa [joinFields] using h f (by simp)
  | f :: g :: fs, h => by
      intro c hc
      simp only [joinFields, List.mem_append, List.mem_cons] at hc
      rcases hc with hc | rfl | hc
      · exact h f (by simp) c hc
      · decide
      · exact joinFields_ascii (g :: fs) (fun f' hf' => h f' (List.mem_cons_of_mem _ hf')) c
          (by simpa [List.mem_cons] using hc)

theorem tag_ascii : AsciiChars tag := by
  intro c hc; revert c; decide

/-- Every tagged integer record with an ASCII tag is ASCII. -/
theorem asciiChars_encodeInts (tg : List Char) (htg : AsciiChars tg) (zs : List Int) :
    AsciiChars (encodeInts tg zs) := by
  unfold encodeInts
  apply joinFields_ascii
  intro f hf
  simp only [List.mem_cons, List.mem_map] at hf
  rcases hf with rfl | ⟨z, _, rfl⟩
  · exact htg
  · exact renderInt_ascii z

theorem asciiChars_encodeChars (m : WideNet) : AsciiChars (encodeChars m) :=
  asciiChars_encodeInts tag tag_ascii _

/-! ## Byte codec -/

/-- The canonical byte artifact of a network. -/
def encodeBytes (m : WideNet) : Bytes := (encodeChars m).map charToByte

/-- The authoritative byte decoder: ASCII check, then the canonical text decoder (which
also enforces the versioned architecture bound). -/
def decodeBytes (A : Arch) (bs : Bytes) : Option WideNet :=
  if bs.all isAsciiByte then decode A (String.ofList (bs.map byteToChar)) else none

theorem map_byteToChar_charToByte (l : List Char) (h : AsciiChars l) :
    (l.map charToByte).map byteToChar = l := by
  rw [List.map_map]
  conv => rhs; rw [← List.map_id l]
  apply List.map_congr_left
  intro c hc
  exact byteToChar_charToByte c (h c hc)

theorem all_ascii_map_charToByte (l : List Char) (h : AsciiChars l) :
    (l.map charToByte).all isAsciiByte = true := by
  simp only [List.all_map, List.all_eq_true]
  intro c hc
  simp only [Function.comp, isAsciiByte, decide_eq_true_eq]
  have h := h c hc
  unfold charToByte
  rw [Nat.toUInt8, UInt8.toNat_ofNat', Nat.mod_eq_of_lt (by omega)]
  exact h

theorem encodeBytes_map_byteToChar (m : WideNet) :
    (encodeBytes m).map byteToChar = encodeChars m :=
  map_byteToChar_charToByte _ (asciiChars_encodeChars m)

theorem encodeBytes_ascii (m : WideNet) : (encodeBytes m).all isAsciiByte = true :=
  all_ascii_map_charToByte _ (asciiChars_encodeChars m)

/-- **Byte roundtrip** for every valid network of every admissible width. -/
theorem decodeBytes_encodeBytes (A : Arch) (m : WideNet) (h : valid A m = true) :
    decodeBytes A (encodeBytes m) = some m := by
  unfold decodeBytes
  rw [if_pos (encodeBytes_ascii m), encodeBytes_map_byteToChar]
  exact decode_encode A m h

theorem bytes_of_ascii (bs : Bytes) (h : bs.all isAsciiByte = true) :
    (bs.map byteToChar).map charToByte = bs := by
  rw [List.map_map]
  conv => rhs; rw [← List.map_id bs]
  apply List.map_congr_left
  intro b hb
  simp only [List.all_eq_true, isAsciiByte, decide_eq_true_eq] at h
  exact charToByte_byteToChar b (h b hb)

/-- **Exact acceptance characterisation of the byte decoder.** -/
theorem decodeBytes_iff (A : Arch) (bs : Bytes) (m : WideNet) :
    decodeBytes A bs = some m ↔ valid A m = true ∧ encodeBytes m = bs := by
  constructor
  · intro h
    unfold decodeBytes at h
    by_cases ha : bs.all isAsciiByte = true
    · rw [if_pos ha] at h
      obtain ⟨hv, he⟩ := (decode_iff A _ m).mp h
      refine ⟨hv, ?_⟩
      have : encodeChars m = bs.map byteToChar := by
        have := congrArg String.toList he
        simpa [encode, String.toList_ofList] using this
      rw [encodeBytes, this, bytes_of_ascii bs ha]
    · rw [if_neg ha] at h; cases h
  · rintro ⟨hv, rfl⟩
    exact decodeBytes_encodeBytes A m hv

theorem decodeBytes_canonical {A : Arch} {bs : Bytes} {m : WideNet}
    (h : decodeBytes A bs = some m) : encodeBytes m = bs := ((decodeBytes_iff A bs m).mp h).2

theorem decodeBytes_valid {A : Arch} {bs : Bytes} {m : WideNet}
    (h : decodeBytes A bs = some m) : valid A m = true := ((decodeBytes_iff A bs m).mp h).1

/-- `encodeBytes` is injective on **all** networks. -/
theorem encodeBytes_injective {m₁ m₂ : WideNet} (h : encodeBytes m₁ = encodeBytes m₂) :
    m₁ = m₂ := by
  have h1 := congrArg (List.map byteToChar) h
  rw [encodeBytes_map_byteToChar, encodeBytes_map_byteToChar] at h1
  apply encode_injective
  simp [encode, h1]

/-- **Malformed bytes are rejected.** Any byte string that is not exactly the canonical
encoding of a valid network decodes to `none`. -/
theorem decodeBytes_rejects (A : Arch) (bs : Bytes)
    (h : ∀ m, valid A m = true → encodeBytes m ≠ bs) : decodeBytes A bs = none := by
  cases hd : decodeBytes A bs with
  | none => rfl
  | some m =>
      obtain ⟨hv, he⟩ := (decodeBytes_iff A bs m).mp hd
      exact absurd he (h m hv)

/-- Any byte `≥ 128` anywhere is rejected. -/
theorem decodeBytes_nonascii (A : Arch) (bs : Bytes) (b : UInt8) (hb : b ∈ bs)
    (h : 128 ≤ b.toNat) : decodeBytes A bs = none := by
  unfold decodeBytes
  rw [if_neg]
  intro ha
  simp only [List.all_eq_true, isAsciiByte, decide_eq_true_eq] at ha
  have := ha b hb
  omega

/-- Two byte strings accepted for the same network are identical (no alternative
spellings exist at the byte level). -/
theorem decodeBytes_unique {A A' : Arch} {bs bs' : Bytes} {m : WideNet}
    (h : decodeBytes A bs = some m) (h' : decodeBytes A' bs' = some m) : bs = bs' := by
  rw [← decodeBytes_canonical h, ← decodeBytes_canonical h']

theorem valid_mono {A A' : Arch} (hw : A.maxWidth ≤ A'.maxWidth) (hb : A.bound ≤ A'.bound)
    {m : WideNet} (h : valid A m = true) : valid A' m = true := by
  have hr : ∀ z : Int, inRange A.bound z = true → inRange A'.bound z = true := by
    intro z hz
    simp only [inRange, decide_eq_true_eq] at hz ⊢
    omega
  have hu : ∀ l : List HiddenUnit, unitsOK A.bound l = true → unitsOK A'.bound l = true := by
    intro l
    induction l with
    | nil => intro _; rfl
    | cons u us ih =>
        intro hl
        simp only [unitsOK, unitOK, Bool.and_eq_true] at hl ⊢
        exact ⟨⟨⟨hr _ hl.1.1.1, hr _ hl.1.1.2⟩, hr _ hl.1.2⟩, ih hl.2⟩
  simp only [valid, Bool.and_eq_true, decide_eq_true_eq] at h ⊢
  exact ⟨⟨by omega, hr _ h.1.2⟩, hu _ h.2⟩

/-- Accepted artifacts stay accepted, with the same network, under larger bounds. -/
theorem decodeBytes_arch_mono {A A' : Arch} (hw : A.maxWidth ≤ A'.maxWidth)
    (hb : A.bound ≤ A'.bound) {bs : Bytes} {m : WideNet} (h : decodeBytes A bs = some m) :
    decodeBytes A' bs = some m := by
  obtain ⟨hv, he⟩ := (decodeBytes_iff A bs m).mp h
  exact (decodeBytes_iff A' bs m).mpr ⟨valid_mono hw hb hv, he⟩

/-! ## Byte-level inference -/

/-- Inference from raw bytes. -/
def inferBytes (A : Arch) (bs : Bytes) (x : Int) : Option Int :=
  (decodeBytes A bs).map fun m => predict m x

theorem inferBytes_encodeBytes (A : Arch) (m : WideNet) (h : valid A m = true) (x : Int) :
    inferBytes A (encodeBytes m) x = some (predict m x) := by
  simp [inferBytes, decodeBytes_encodeBytes A m h]

theorem inferBytes_sound {A : Arch} {bs : Bytes} {x y : Int} (h : inferBytes A bs x = some y) :
    ∃ m, valid A m = true ∧ encodeBytes m = bs ∧ predict m x = y := by
  unfold inferBytes at h
  cases hd : decodeBytes A bs with
  | none => simp [hd] at h
  | some m =>
      simp [hd] at h
      exact ⟨m, decodeBytes_valid hd, decodeBytes_canonical hd, h⟩

/-- Bytes that do not decode serve nothing (fail closed). -/
theorem inferBytes_none {A : Arch} {bs : Bytes} (h : decodeBytes A bs = none) (x : Int) :
    inferBytes A bs x = none := by
  simp [inferBytes, h]

/-- Text and bytes agree: the byte artifact is the text artifact, byte for character. -/
theorem decodeBytes_text (m : WideNet) :
    (encodeBytes m).map byteToChar = (encode m).toList := by
  rw [encodeBytes_map_byteToChar]; simp [encode, String.toList_ofList]

/-! ## Literal byte fixtures -/

/-- ASCII bytes of a string literal (fixtures only). -/
def ascii (s : String) : Bytes := s.toList.map charToByte

theorem gen3_bytes : encodeBytes gen3 = ascii "PGSI2-WIDE|0|2|1|1|-1|1|1|1|-2|-2" := by
  decide +kernel

theorem gen3_bytes_decode : decodeBytes arch3 (ascii "PGSI2-WIDE|0|2|1|1|-1|1|1|1|-2|-2") =
    some gen3 := by
  rw [← gen3_bytes]; exact decodeBytes_encodeBytes arch3 gen3 (by decide)

/-- Malformed byte strings, each rejected by the byte decoder. -/
theorem malformed_fixtures :
    decodeBytes arch3 [] = none ∧
    decodeBytes arch3 (ascii "PGSI2-WIDE") = none ∧
    decodeBytes arch3 (ascii "PGSI2-WIDE|0|2|1") = none ∧
    decodeBytes arch3 (ascii "PGSI2-WIDE|0|2|1|1|") = none ∧
    decodeBytes arch3 (ascii "PGSI2-WIDE|0|2|1|1|7") = none ∧
    decodeBytes arch3 (ascii "PGSI2-WIDE|00") = none ∧
    decodeBytes arch3 (ascii "PGSI2-WIDE|+1") = none ∧
    decodeBytes arch3 (ascii "PGSI2-WIDE|-0") = none ∧
    decodeBytes arch3 (ascii "PGSI2-WIDE| 1") = none ∧
    decodeBytes arch3 (ascii "pgsi2-wide|0") = none ∧
    decodeBytes arch3 (ascii "PGSI2-WIDE|0\n") = none ∧
    decodeBytes arch3 (ascii "|PGSI2-WIDE|0") = none ∧
    decodeBytes arch3 (ascii "PGSI2-WIDE||0") = none := by
  decide +kernel

/-- A UTF-8 byte-order mark in front of a valid artifact is rejected (non-ASCII). -/
theorem bom_rejected :
    decodeBytes arch3 ([0xEF, 0xBB, 0xBF] ++ ascii "PGSI2-WIDE|0") = none :=
  decodeBytes_nonascii _ _ 0xEF (by simp) (by decide)

/-- A byte `0xC0` (overlong-encoding lead byte) is rejected wherever it occurs. -/
theorem high_byte_rejected (pre post : Bytes) :
    decodeBytes arch3 (pre ++ 0xC0 :: post) = none :=
  decodeBytes_nonascii _ _ 0xC0 (by simp) (by decide)

/-- Architecture mismatch: accepted under `arch3` (bound 32), rejected under bound 16. -/
theorem arch_mismatch_fixture :
    (decodeBytes arch3 (ascii "PGSI2-WIDE|32")).isSome = true ∧
    decodeBytes ⟨8, 16⟩ (ascii "PGSI2-WIDE|32") = none := by
  decide +kernel

end PCS.V2.ProofGatedBytes
