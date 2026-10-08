import PCS.V2.Zip
import PCS.V2.KernelRfl

/-!
# Completeness of the Lean canonical-ZIP decoder

`PCS.V2.Zip.decodeZip_sound` shows that the decoder only accepts canonical encodings.  This
file proves the converse: **every canonical archive is decoded to exactly its entries**,

* `decodeZip_encodeZip : strictSorted names â†’ wellSizedB es â†’ decodeZip (encodeZip es) = some es`
* `decodeZip_iff_canonicalZip : decodeZip raw = some es â†” CanonicalZip raw es`.

The proof reads every field the decoder consults (end-of-central-directory signature, entry
count and directory offset; per central-directory record the compressed size, name length,
local-header offset and name; per local record the member bytes) off the canonical encoding,
using only the lengths of the encoding's components.  In particular no CRC-32 value is ever
evaluated: the decoder's final re-encoding check compares `encodeZip es` with itself.

This is what makes the raw golden archive (`goldenRaw`, 7.7 KB) tractable: its decoding is
obtained from this general theorem and two small kernel-checked side conditions
(`strictSorted`, `wellSizedB`), rather than by kernel evaluation of the decoder.
-/

set_option autoImplicit false

namespace PCS.V2.Zip

/-! ## Reading fields from byte lists -/

/-- A byte list as a byte array. -/
abbrev BA (l : List UInt8) : ByteArray := âŸ¨l.toArrayâŸ©

theorem BA_size (l : List UInt8) : (BA l).size = l.length := by
  simp [ByteArray.size]

theorem u8_BA (l : List UInt8) (i : Nat) : u8 (BA l) i = (l[i]?.getD 0).toNat := by
  simp [u8]

theorem le16_length (v : Nat) : (le16 v).length = 2 := rfl
theorem le32_length (v : Nat) : (le32 v).length = 4 := rfl

theorem get_app (a l : List UInt8) (k : Nat) : (a ++ l)[a.length + k]? = l[k]? := by
  rw [List.getElem?_append_right (by omega)]; simp

theorem get_app0 (a l : List UInt8) : (a ++ l)[a.length]? = l[0]? := by
  simpa using get_app a l 0ÑPÐ€L@ö×Ý<r«