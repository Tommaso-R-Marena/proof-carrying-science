import PCS.V2.Archive

/-!
# Canonical PCS ZIP (`ZIP_STORED`) — verified Lean decoder

The v0.6 bundle writer (`pcs/bundle_v06.py`) emits a single deterministic ZIP subset:
members in strictly increasing name order, method 0 (`STORED`), DOS time 1980-01-01
00:00:00, `create_system = 3`, version 2.0, external attributes `0o100644 << 16`, no extra
fields, no comments, no directory entries, no data descriptors, no ZIP64, general-purpose
flags `0` (or `0x0800` — UTF-8 name — exactly when the name is non-ASCII), followed by the
central directory and an end-of-central-directory record without comment.

`encodeZip` writes that format field by field from the ZIP application note: for each
member a local file header (signature `PK\x03\x04`, versions, flags, method, time, date,
CRC-32, compressed and uncompressed size, name length, extra length, name) followed by the
member bytes; then one central-directory header per member (signature `PK\x01\x02`,
…, local-header offset, name); then the end-of-central-directory record (`PK\x05\x06`,
entry counts, directory size and offset).

`CanonicalZip raw entries` — the **declarative semantics** — says that `raw` is *exactly*
that encoding of `entries`, names strictly sorted (hence unique) and every field in range.
This pins down signatures, local/central agreement, member byte boundaries (no overlap, no
gaps), unique names and the absence of trailing bytes, without trusting any ZIP library.

`decodeZip` parses the central directory and then *re-encodes* and compares, so
`decodeZip_sound : decodeZip raw = some entries → CanonicalZip raw entries`, i.e.
`ZipDecoderFaithful decodeZip CanonicalZip` is a theorem (`leanZip_faithful`).  Archives
outside the canonical subset (DEFLATE, extra fields, other orders, …) are rejected by this
decoder; they are handled by the legacy, explicitly less-assured materialisation path.
-/

namespace PCS.V2.Zip

open PCS.V2.EndToEnd PCS.V2.TCB

abbrev Bytes := List UInt8

def le16 (n : Nat) : Bytes := [UInt8.ofNat (n % 256), UInt8.ofNat (n / 256 % 256)]
def le32 (n : Nat) : Bytes :=
  [UInt8.ofNat (n % 256), UInt8.ofNat (n / 256 % 256), UInt8.ofNat (n / 65536 % 256),
   UInt8.ofNat (n / 16777216 % 256)]

/-! ## CRC-32 (ISO-HDLC / ZIP: reflected polynomial `0xEDB88320`, init and xor-out all ones) -/

def crcStep (c : UInt32) : UInt32 := if c &&& 1 = 1 then (c >>> 1) ^^^ 0xEDB88320 else c >>> 1

def crcByte (c : UInt32) (b : UInt8) : UInt32 :=
  let c := c ^^^ b.toUInt32
  crcStep (crcStep (crcStep (crcStep (crcStep (crcStep (crcStep (crcStep c)))))))

def crc32 (bs : Bytes) : UInt32 := bs.foldl crcByte 0xFFFFFFFF ^^^ 0xFFFFFFFF

/-! ## The canonical encoding -/

def nameBytes (n : String) : Bytes := n.toUTF8.data.toList

def nameFlags (n : String) : Nat := if n.toList.all (·.toNat < 128) then 0 else 0x0800

def dosTime : Nat := 0
def dosDate : Nat := 0x21  -- 1980-01-01

def localHeader (n : String) (d : Bytes) : Bytes :=
  le32 0x04034b50 ++ le16 20 ++ le16 (nameFlags n) ++ le16 0 ++ le16 dosTime ++ le16 dosDate ++
  le32 (crc32 d).toNat ++ le32 d.length ++ le32 d.length ++ le16 (nameBytes n).length ++ le16 0 ++
  nameBytes n

def localRecord (n : String) (d : Bytes) : Bytes := localHeader n d ++ d

def centralRecord (n : String) (d : Bytes) (off : Nat) : Bytes :=
  le32 0x02014b50 ++ le16 0x0314 ++ le16 20 ++ le16 (nameFlags n) ++ le16 0 ++ le16 dosTime ++
  le16 dosDate ++ le32 (crc32 d).toNat ++ le32 d.length ++ le32 d.length ++
  le16 (nameBytes n).length ++ le16 0 ++ le16 0 ++ le16 0 ++ le16 0 ++ le32 0x81A40000 ++
  le32 off ++ nameBytes n

def locals : List (String × Bytes) → Bytes
  | [] => []
  | (n, d) :: es => localRecord n d ++ locals es

def centrals : Nat → List (String × Bytes) → Bytes
  | _, [] => []
  | off, (n, d) :: es => centralRecord n d off ++ centrals (off + (localRecord n d).length) es

def eocd (count cdSize cdOff : Nat) : Bytes :=
  le32 0x06054b50 ++ le16 0 ++ le16 0 ++ le16 count ++ le16 count ++ le32 cdSize ++ le32 cdOff ++
  le16 0

def entryBytes (es : List (String × ByteArray)) : List (String × Bytes) :=
  es.map fun e => (e.1, e.2.data.toList)

/-- The canonical PCS `STORED` ZIP encoding of a member list. -/
def encodeZip (es : List (String × ByteArray)) : Bytes :=
  let xs := entryBytes es
  let l := locals xs
  let c := centrals 0 xs
  l ++ c ++ eocd xs.length c.length l.length

/-! ## Declarative semantics -/

def strictSorted : List String → Bool
  | a :: b :: rest => decide (a < b) && strictSorted (b :: rest)
  | _ => true

/-- Every field of the encoding is in range (no truncation by `le16`/`le32`). -/
def WellSized (es : List (String × ByteArray)) : Prop :=
  es.length < 65536 ∧ (encodeZip es).length < 2 ^ 32 ∧
  ∀ e ∈ es, 0 < (nameBytes e.1).length ∧ (nameBytes e.1).length < 65536 ∧ e.2.size < 2 ^ 32

/-- **Canonical PCS ZIP semantics**: `raw` is exactly the canonical encoding of `entries`,
    whose names are strictly increasing (so unique) and whose fields are in range. -/
structure CanonicalZip (raw : ByteArray) (entries : List (String × ByteArray)) : Prop where
  encoding : raw.data.toList = encodeZip entries
  sorted : strictSorted (entries.map (·.1)) = true
  sized : WellSized entries

theorem strictSorted_nodup : ∀ (ns : List String), strictSorted ns = true → ns.Nodup
  | [], _ => List.nodup_nil
  | [_], _ => by simp
  | a :: b :: rest, h => by
    simp only [strictSorted, Bool.and_eq_true, decide_eq_true_eq] at h
    have ih := strictSorted_nodup (b :: rest) h.2
    refine List.nodup_cons.2 ⟨?_, ih⟩
    intro hm
    have key : ∀ (c : String) (cs : List String), strictSorted (c :: cs) = true → a < c →
        a ∉ c :: cs := by
      intro c cs
      induction cs generalizing c with
      | nil =>
        intro _ hac hm
        rw [List.mem_singleton] at hm
        exact (String.lt_irrefl a) (hm ▸ hac)
      | cons d ds ih2 =>
        intro hs hac hm
        simp only [strictSorted, Bool.and_eq_true, decide_eq_true_eq] at hs
        rcases List.mem_cons.1 hm with hm | hm
        · exact (String.lt_irrefl a) (hm ▸ hac)
        · exact ih2 d hs.2 (String.lt_trans hac hs.1) hm
    exact key b rest h.2 h.1 hm

/-- Canonical archives have unique member names. -/
theorem canonicalZip_names_nodup {raw : ByteArray} {es : List (String × ByteArray)}
    (h : CanonicalZip raw es) : (es.map (·.1)).Nodup :=
  strictSorted_nodup _ h.sorted

/-! ## Decoder -/

def u8 (raw : ByteArray) (i : Nat) : Nat := (raw.data[i]?.getD 0).toNat
def u16 (raw : ByteArray) (i : Nat) : Nat := u8 raw i + 256 * u8 raw (i + 1)
def u32 (raw : ByteArray) (i : Nat) : Nat := u16 raw i + 65536 * u16 raw (i + 2)

/-- Read `count` central-directory entries starting at `pos` (tail-recursive; the
    accumulator is reversed). -/
def readCentral (raw : ByteArray) :
    Nat → Nat → List (String × ByteArray) → Option (List (String × ByteArray))
  | 0, _, acc => some acc.reverse
  | count + 1, pos, acc =>
    match String.fromUTF8? (raw.extract (pos + 46) (pos + 46 + u16 raw (pos + 28))) with
    | none => none
    | some name =>
      let nlen := u16 raw (pos + 28)
      let start := u32 raw (pos + 42) + 30 + nlen
      readCentral raw count (pos + 46 + nlen)
        ((name, raw.extract start (start + u32 raw (pos + 20))) :: acc)

def wellSizedB (es : List (String × ByteArray)) : Bool :=
  decide (es.length < 65536) && decide ((encodeZip es).length < 2 ^ 32) &&
  es.all fun e => decide (0 < (nameBytes e.1).length) && decide ((nameBytes e.1).length < 65536) &&
    decide (e.2.size < 2 ^ 32)

/-- The Lean canonical-ZIP decoder (fail-closed outside the canonical subset). -/
def decodeZip (raw : ByteArray) : Option (List (String × ByteArray)) :=
  if raw.size < 22 ∨ u32 raw (raw.size - 22) ≠ 0x06054b50 ∨
      46 * u16 raw (raw.size - 22 + 10) > raw.size then none else
  match readCentral raw (u16 raw (raw.size - 22 + 10)) (u32 raw (raw.size - 22 + 16)) [] with
  | none => none
  | some es =>
    if raw.data == (encodeZip es).toArray && strictSorted (es.map (·.1)) && wellSizedB es then
      some es
    else none

theorem wellSizedB_sound {es : List (String × ByteArray)} (h : wellSizedB es = true) :
    WellSized es := by
  simp only [wellSizedB, Bool.and_eq_true, decide_eq_true_eq, List.all_eq_true] at h
  exact ⟨h.1.1, h.1.2, fun e he => ⟨(h.2 e he).1.1, (h.2 e he).1.2, (h.2 e he).2⟩⟩

/-- **Soundness of the Lean ZIP decoder** against the canonical semantics. -/
theorem decodeZip_sound {raw : ByteArray} {es : List (String × ByteArray)}
    (h : decodeZip raw = some es) : CanonicalZip raw es := by
  unfold decodeZip at h
  split at h
  · cases h
  · split at h
    · cases h
    · rename_i es' _
      split at h
      · rename_i hc
        cases h
        simp only [Bool.and_eq_true, beq_iff_eq] at hc
        exact ⟨by simp [hc.1.1], hc.1.2, wellSizedB_sound hc.2⟩
      · cases h

/-- `ZipDecoderFaithful` is a **theorem** for the Lean decoder. -/
theorem leanZip_faithful : ZipDecoderFaithful decodeZip CanonicalZip :=
  fun _ _ h => decodeZip_sound h

end PCS.V2.Zip
