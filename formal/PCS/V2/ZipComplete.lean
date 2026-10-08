import PCS.V2.Zip
import PCS.V2.KernelRfl

/-!
# Completeness of the Lean canonical-ZIP decoder

`PCS.V2.Zip.decodeZip_sound` shows that the decoder only accepts canonical encodings.  This
file proves the converse: **every canonical archive is decoded to exactly its entries**,

* `decodeZip_encodeZip : strictSorted names → wellSizedB es → decodeZip (encodeZip es) = some es`
* `decodeZip_iff_canonicalZip : decodeZip raw = some es ↔ CanonicalZip raw es`.

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
abbrev BA (l : List UInt8) : ByteArray := ⟨l.toArray⟩

theorem BA_size (l : List UInt8) : (BA l).size = l.length := by
  simp [ByteArray.size]

theorem u8_BA (l : List UInt8) (i : Nat) : u8 (BA l) i = (l[i]?.getD 0).toNat := by
  simp [u8]

theorem le16_length (v : Nat) : (le16 v).length = 2 := rfl
theorem le32_length (v : Nat) : (le32 v).length = 4 := rfl

theorem get_app (a l : List UInt8) (k : Nat) : (a ++ l)[a.length + k]? = l[k]? := by
  rw [List.getElem?_append_right (by omega)]; simp

theorem get_app0 (a l : List UInt8) : (a ++ l)[a.length]? = l[0]? := by
  simpa using get_app a l 0

theorem u16_of_eq {bs a b : List UInt8} {v i : Nat} (hbs : bs = a ++ (le16 v ++ b))
    (hi : i = a.length) : u16 (BA bs) i = v % 65536 := by
  subst hbs hi
  simp only [u16, u8_BA, get_app0, get_app]
  simp [le16]
  omega

theorem u32_of_eq {bs a b : List UInt8} {v i : Nat} (hbs : bs = a ++ (le32 v ++ b))
    (hi : i = a.length) : u32 (BA bs) i = v % 4294967296 := by
  subst hbs hi
  simp only [u32, u16, u8_BA, get_app0, get_app, Nat.add_assoc]
  simp [le32]
  omega

theorem extract_of_eq {bs a b c : List UInt8} {i j : Nat} (hbs : bs = a ++ (b ++ c))
    (hi : i = a.length) (hj : j = a.length + b.length) : (BA bs).extract i j = BA b := by
  subst hbs hi hj
  apply ByteArray.ext
  apply Array.ext'
  simp [ByteArray.data_extract, List.extract_eq_drop_take]

theorem BA_toList (x : ByteArray) : BA x.data.toList = x := by
  cases x; simp [BA]

theorem fromUTF8_toUTF8 (s : String) : String.fromUTF8? s.toUTF8 = some s := by
  simp only [String.fromUTF8?, String.toUTF8_eq_toByteArray, dif_pos s.isValidUTF8]
  rfl

/-! ## Structure of the encoding -/

theorem locals_append : ∀ (p q : List (String × Bytes)), locals (p ++ q) = locals p ++ locals q
  | [], _ => rfl
  | (n, d) :: p, q => by simp [locals, locals_append p q]

theorem centrals_append : ∀ (off : Nat) (p q : List (String × Bytes)),
    centrals off (p ++ q) = centrals off p ++ centrals (off + (locals p).length) q
  | _, [], _ => rfl
  | off, (n, d) :: p, q => by
    simp only [List.cons_append, centrals, centrals_append _ p q, locals, List.length_append,
      List.append_assoc, Nat.add_assoc]

theorem localHeader_length (n : String) (d : Bytes) :
    (localHeader n d).length = 30 + (nameBytes n).length := by
  simp [localHeader, le16_length, le32_length]; omega

theorem centralRecord_length (n : String) (d : Bytes) (off : Nat) :
    (centralRecord n d off).length = 46 + (nameBytes n).length := by
  simp [centralRecord, le16_length, le32_length]; omega

theorem centrals_length_ge : ∀ (off : Nat) (xs : List (String × Bytes)),
    46 * xs.length ≤ (centrals off xs).length
  | _, [] => by simp [centrals]
  | off, (n, d) :: xs => by
    have := centrals_length_ge (off + (localRecord n d).length) xs
    simp only [centrals, List.length_append, centralRecord_length, List.length_cons]
    omega

theorem locals_length_le (xs : List (String × Bytes)) (pre : List (String × Bytes))
    (post : List (String × Bytes)) (h : xs = pre ++ post) :
    (locals pre).length ≤ (locals xs).length := by
  subst h; simp [locals_append]

/-- Splittings of a central-directory record at the fields the decoder reads. -/
theorem centralRecord_at20 (n : String) (d : Bytes) (off : Nat) :
    ∃ P R, centralRecord n d off = P ++ (le32 d.length ++ R) ∧ P.length = 20 :=
  ⟨le32 0x02014b50 ++ le16 0x0314 ++ le16 20 ++ le16 (nameFlags n) ++ le16 0 ++ le16 dosTime ++
    le16 dosDate ++ le32 (crc32 d).toNat,
    le32 d.length ++ le16 (nameBytes n).length ++ le16 0 ++ le16 0 ++ le16 0 ++ le16 0 ++
    le32 0x81A40000 ++ le32 off ++ nameBytes n,
    by simp only [centralRecord, List.append_assoc], rfl⟩

theorem centralRecord_at28 (n : String) (d : Bytes) (off : Nat) :
    ∃ P R, centralRecord n d off = P ++ (le16 (nameBytes n).length ++ R) ∧ P.length = 28 :=
  ⟨le32 0x02014b50 ++ le16 0x0314 ++ le16 20 ++ le16 (nameFlags n) ++ le16 0 ++ le16 dosTime ++
    le16 dosDate ++ le32 (crc32 d).toNat ++ le32 d.length ++ le32 d.length,
    le16 0 ++ le16 0 ++ le16 0 ++ le16 0 ++ le32 0x81A40000 ++ le32 off ++ nameBytes n,
    by simp only [centralRecord, List.append_assoc], rfl⟩

theorem centralRecord_at42 (n : String) (d : Bytes) (off : Nat) :
    ∃ P, centralRecord n d off = P ++ (le32 off ++ nameBytes n) ∧ P.length = 42 :=
  ⟨le32 0x02014b50 ++ le16 0x0314 ++ le16 20 ++ le16 (nameFlags n) ++ le16 0 ++ le16 dosTime ++
    le16 dosDate ++ le32 (crc32 d).toNat ++ le32 d.length ++ le32 d.length ++
    le16 (nameBytes n).length ++ le16 0 ++ le16 0 ++ le16 0 ++ le16 0 ++ le32 0x81A40000,
    by simp only [centralRecord, List.append_assoc], rfl⟩

theorem centralRecord_at46 (n : String) (d : Bytes) (off : Nat) :
    ∃ P, centralRecord n d off = P ++ nameBytes n ∧ P.length = 46 :=
  ⟨le32 0x02014b50 ++ le16 0x0314 ++ le16 20 ++ le16 (nameFlags n) ++ le16 0 ++ le16 dosTime ++
    le16 dosDate ++ le32 (crc32 d).toNat ++ le32 d.length ++ le32 d.length ++
    le16 (nameBytes n).length ++ le16 0 ++ le16 0 ++ le16 0 ++ le16 0 ++ le32 0x81A40000 ++
    le32 off, by simp only [centralRecord, List.append_assoc],
    by simp only [List.length_append, le16_length, le32_length]⟩

theorem encodeZip_eq (es : List (String × ByteArray)) :
    encodeZip es = locals (entryBytes es) ++ centrals 0 (entryBytes es) ++
      eocd (entryBytes es).length (centrals 0 (entryBytes es)).length
        (locals (entryBytes es)).length := by
  simp only [encodeZip]

theorem entryBytes_append (p q : List (String × ByteArray)) :
    entryBytes (p ++ q) = entryBytes p ++ entryBytes q := by
  simp [entryBytes]

theorem entryBytes_length (es : List (String × ByteArray)) :
    (entryBytes es).length = es.length := by
  simp [entryBytes]

/-! ## The central-directory loop -/

theorem readCentral_zero (raw : ByteArray) (k : Nat) (acc : List (String × ByteArray)) :
    readCentral raw 0 k acc = some acc.reverse := rfl

/-- One unfolding of the loop.  (Lean cannot generate this equation lemma automatically
    within its heartbeat budget; the definitional unfolding is checked by the kernel.) -/
theorem readCentral_succ : ∀ (raw : ByteArray) (c k : Nat) (acc : List (String × ByteArray)),
    readCentral raw (c + 1) k acc =
      (match String.fromUTF8? (raw.extract (k + 46) (k + 46 + u16 raw (k + 28))) with
       | none => none
       | some name =>
         readCentral raw c (k + 46 + u16 raw (k + 28))
           ((name, raw.extract (u32 raw (k + 42) + 30 + u16 raw (k + 28))
              (u32 raw (k + 42) + 30 + u16 raw (k + 28) + u32 raw (k + 20))) :: acc)) := by
  kernel_rfl

theorem entryBytes_cons (e : String × ByteArray) (es : List (String × ByteArray)) :
    entryBytes (e :: es) = (e.1, e.2.data.toList) :: entryBytes es := rfl

/-- The decoder's central-directory loop on a canonical encoding.  `pre` are the (already
    read) entries before the cursor, `post` the entries still to be read; `bs` is any byte
    string laid out as `locals ++ centrals ++ Ys`. -/
theorem readCentral_complete (bs L Ys : List UInt8) (hbig : bs.length < 4294967296) :
    ∀ (post : List (String × ByteArray)) (pre : List (String × Bytes))
      (acc : List (String × ByteArray)),
      (∀ e ∈ post, (nameBytes e.1).length < 65536) →
      L = locals (pre ++ entryBytes post) →
      bs = L ++ centrals 0 (pre ++ entryBytes post) ++ Ys →
      readCentral (BA bs) post.length (L.length + (centrals 0 pre).length) acc =
        some (acc.reverse ++ post) := by
  intro post
  induction post with
  | nil => intro pre acc _ _ _; rw [List.length_nil, readCentral_zero, List.append_nil]
  | cons e post ihp =>
    intro pre acc hnm hL hbs
    obtain ⟨n, d0⟩ := e
    have hnl : (nameBytes n).length < 65536 := hnm _ (List.mem_cons_self ..)
    obtain ⟨d, hd⟩ : ∃ d, d = d0.data.toList := ⟨_, rfl⟩
    have hdlen : d.length = d0.size := by rw [hd, Array.length_toList]; rfl
    obtain ⟨off, hoff⟩ : ∃ off, off = (locals pre).length := ⟨_, rfl⟩
    obtain ⟨Cpost, hCpost⟩ : ∃ C, C = centrals (off + (localRecord n d).length) (entryBytes post) :=
      ⟨_, rfl⟩
    obtain ⟨C0, hC0⟩ : ∃ C, C = centrals 0 pre := ⟨_, rfl⟩
    have hsplit : pre ++ entryBytes ((n, d0) :: post) = pre ++ (n, d) :: entryBytes post := by
      rw [entryBytes_cons, hd]
    have hC : centrals 0 (pre ++ entryBytes ((n, d0) :: post)) =
        C0 ++ (centralRecord n d off ++ Cpost) := by
      rw [hsplit, centrals_append, hC0, hCpost, hoff]; simp only [centrals, Nat.zero_add]
    have hbs' : bs = (L ++ C0) ++ (centralRecord n d off ++ (Cpost ++ Ys)) := by
      rw [hbs, hC]; simp only [List.append_assoc]
    have hL' : L = locals pre ++ (localHeader n d ++ (d ++ locals (entryBytes post))) := by
      rw [hL, hsplit, locals_append]; simp [locals, localRecord]
    have hoffL : off + 30 + (nameBytes n).length + d0.size ≤ L.length := by
      rw [hL', hoff]; simp [localHeader_length, hdlen]; omega
    have hLbs : L.length ≤ bs.length := by rw [hbs]; simp
    obtain ⟨pos, hpos⟩ : ∃ p, p = L.length + C0.length := ⟨_, rfl⟩
    obtain ⟨P20, R20, h20, hP20⟩ := centralRecord_at20 n d off
    obtain ⟨P28, R28, h28, hP28⟩ := centralRecord_at28 n d off
    obtain ⟨P42, h42, hP42⟩ := centralRecord_at42 n d off
    obtain ⟨P46, h46, hP46⟩ := centralRecord_at46 n d off
    have r28 : u16 (BA bs) (pos + 28) = (nameBytes n).length := by
      rw [u16_of_eq (v := (nameBytes n).length) (a := L ++ C0 ++ P28) (b := R28 ++ (Cpost ++ Ys))
        (by rw [hbs', h28]; simp only [List.append_assoc]) (by rw [hpos]; simp only [List.length_append, hP28])]
      omega
    have r20 : u32 (BA bs) (pos + 20) = d0.size := by
      rw [u32_of_eq (v := d.length) (a := L ++ C0 ++ P20) (b := R20 ++ (Cpost ++ Ys))
        (by rw [hbs', h20]; simp only [List.append_assoc]) (by rw [hpos]; simp only [List.length_append, hP20])]
      omega
    have r42 : u32 (BA bs) (pos + 42) = off := by
      rw [u32_of_eq (v := off) (a := L ++ C0 ++ P42) (b := nameBytes n ++ (Cpost ++ Ys))
        (by rw [hbs', h42]; simp only [List.append_assoc]) (by rw [hpos]; simp only [List.length_append, hP42])]
      omega
    have rname : (BA bs).extract (pos + 46) (pos + 46 + (nameBytes n).length) = n.toUTF8 := by
      rw [extract_of_eq (b := nameBytes n) (a := L ++ C0 ++ P46) (c := Cpost ++ Ys)
        (by rw [hbs', h46]; simp only [List.append_assoc]) (by rw [hpos]; simp only [List.length_append, hP46])
        (by rw [hpos]; simp only [List.length_append, hP46])]
      exact BA_toList _
    have rdata : (BA bs).extract (off + 30 + (nameBytes n).length)
        (off + 30 + (nameBytes n).length + d0.size) = d0 := by
      rw [extract_of_eq (b := d) (a := locals pre ++ localHeader n d)
        (c := locals (entryBytes post) ++ (centrals 0 (pre ++ entryBytes ((n, d0) :: post)) ++ Ys))
        (by rw [hbs, hL']; simp only [List.append_assoc])
        (by simp [hoff, localHeader_length]; omega) (by simp [hoff, localHeader_length, hdlen]; omega)]
      rw [hd]
    have ih := ihp (pre ++ [(n, d)]) ((n, d0) :: acc)
      (fun e he => hnm e (List.mem_cons_of_mem _ he))
      (by rw [hL, hsplit]; simp)
      (by rw [hbs, hsplit]; simp)
    have hpos' : L.length + (centrals 0 (pre ++ [(n, d)])).length =
        pos + 46 + (nameBytes n).length := by
      rw [centrals_append, hpos, hC0]
      simp [centrals, centralRecord_length]
      omega
    rw [hpos'] at ih
    rw [← hC0, ← hpos]
    rw [List.length_cons, readCentral_succ, r28, rname, fromUTF8_toUTF8]
    dsimp only
    rw [r42, r20, rdata, ih]
    simp

/-! ## The decoder on canonical encodings -/

theorem wellSizedB_complete {es : List (String × ByteArray)} (h : WellSized es) :
    wellSizedB es = true := by
  simp only [wellSizedB, Bool.and_eq_true, decide_eq_true_eq, List.all_eq_true]
  exact ⟨⟨h.1, h.2.1⟩, fun e he => ⟨⟨(h.2.2 e he).1, (h.2.2 e he).2.1⟩, (h.2.2 e he).2.2⟩⟩

/-- **Decoder completeness**: the Lean decoder decodes every canonical encoding to exactly
    its entries.  No CRC-32 value is evaluated in this proof. -/
theorem decodeZip_encodeZip (es : List (String × ByteArray))
    (hs : strictSorted (es.map (·.1)) = true) (hw : wellSizedB es = true) :
    decodeZip (BA (encodeZip es)) = some es := by
  obtain ⟨hcount, htot, hsz⟩ := wellSizedB_sound hw
  obtain ⟨L, hL⟩ : ∃ L, L = locals (entryBytes es) := ⟨_, rfl⟩
  obtain ⟨C, hC⟩ : ∃ C, C = centrals 0 (entryBytes es) := ⟨_, rfl⟩
  have heocd : encodeZip es = (L ++ C) ++ (le32 0x06054b50 ++ (le16 0 ++ le16 0 ++
      le16 es.length ++ le16 es.length ++ le32 C.length ++ le32 L.length ++ le16 0)) := by
    rw [encodeZip_eq, hL, hC]; simp only [eocd, entryBytes_length, List.append_assoc]
  have hsize : (BA (encodeZip es)).size = L.length + C.length + 22 := by
    rw [BA_size, heocd]; simp only [List.length_append, le16_length, le32_length]
  have hpos : (BA (encodeZip es)).size - 22 = (L ++ C).length := by
    rw [hsize, List.length_append]; omega
  have hLtot : L.length ≤ (encodeZip es).length := by rw [heocd]; simp
  have hsig : u32 (BA (encodeZip es)) ((BA (encodeZip es)).size - 22) = 0x06054b50 := by
    rw [u32_of_eq heocd hpos]
  have hcnt : u16 (BA (encodeZip es)) ((BA (encodeZip es)).size - 22 + 10) = es.length := by
    rw [u16_of_eq (v := es.length)
      (a := (L ++ C) ++ (le32 0x06054b50 ++ le16 0 ++ le16 0 ++ le16 es.length))
      (b := le32 C.length ++ le32 L.length ++ le16 0)
      (by rw [heocd]; simp only [List.append_assoc])
      (by rw [hpos]; simp only [List.length_append, le16_length, le32_length])]
    omega
  have hoff : u32 (BA (encodeZip es)) ((BA (encodeZip es)).size - 22 + 16) = L.length := by
    rw [u32_of_eq (v := L.length)
      (a := (L ++ C) ++ (le32 0x06054b50 ++ le16 0 ++ le16 0 ++ le16 es.length ++
        le16 es.length ++ le32 C.length)) (b := le16 0)
      (by rw [heocd]; simp only [List.append_assoc])
      (by rw [hpos]; simp only [List.length_append, le16_length, le32_length])]
    omega
  have hC46 : 46 * es.length ≤ C.length := by
    have := centrals_length_ge 0 (entryBytes es)
    rw [entryBytes_length, ← hC] at this
    exact this
  have hread := readCentral_complete (encodeZip es) L
    (eocd (entryBytes es).length C.length L.length) htot es [] []
    (fun e he => (hsz e he).2.1) (by rw [hL]; rfl)
    (by rw [encodeZip_eq, hL, hC]; rfl)
  rw [List.reverse_nil, List.nil_append, show (centrals 0 ([] : List (String × Bytes))) = [] from rfl,
    List.length_nil, Nat.add_zero] at hread
  unfold decodeZip
  rw [if_neg (by rw [hsig, hcnt, hsize]; omega), hcnt, hoff, hread]
  dsimp only
  rw [if_pos]
  simp only [hs, hw, Bool.and_true, beq_self_eq_true]

/-- **The Lean ZIP decoder is exactly the canonical semantics.** -/
theorem decodeZip_iff_canonicalZip (raw : ByteArray) (es : List (String × ByteArray)) :
    decodeZip raw = some es ↔ CanonicalZip raw es := by
  refine ⟨decodeZip_sound, fun h => ?_⟩
  have hraw : raw = BA (encodeZip es) := by
    rw [← h.encoding, BA_toList]
  rw [hraw]
  exact decodeZip_encodeZip es h.sorted (wellSizedB_complete h.sized)

end PCS.V2.Zip
