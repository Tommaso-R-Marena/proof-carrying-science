import ClaimCheck
import ClaimCheckAssurance.SourceBinding

/-!
# The source header of a proof file: canonical encoding and a strict decoder

A ClaimCheck proof file is `CHECKER ++ MARKER ++ TAIL`.  `TAIL` begins with the header that binds
the data file into the Lean text:

    open PCS.ClaimCheck⏎⏎def pcs_src : Source := ⟨0x<HEX>, <DEC>⟩⏎⏎

This module states the canonical header `canon d` of a byte string `d` and a strict decoder
`decode`, written step by step after `c/pcs_srcbind.c::pcs_header_decode` (same checks, same
order; the C function is compared with it by test, `runner/test_header_refinement.py`).  Proved:

* `decode_canon`        every canonical header is accepted, whatever follows it, and decodes to its data;
* `decode_sound`        whatever the decoder accepts begins with the canonical header of what it returns;
* `canon_prefix_free`   no canonical header is a prefix of another (so also injective);
* `hexValue_hexOf`      the hexadecimal numeral in the header has the value `ofBytes d`;
* `accepted_header_denotes_data`, `accepted_header_run`
                        the accepted header, read with the standard meaning of hexadecimal and decimal
                        literals, names a well-formed `Source` whose bytes are exactly the decoded
                        data, and `run` on it is `runTable` on the parse of those bytes.

With `SourceBinding` this gives the chain: header text → decoded bytes → numeral → the bytes the
reviewed checker computes on, every link proved except one: that Lean's elaborator reads the text
`0x…` and `…` as the numbers `hexValue` and `decVal` give.  That is the documented meaning of numeric
literals and is trusted, not proved.

Not covered here: everything after the header (the claims and theorem statements; see
`runner/strict_tail.py`, tested), the C function's memory behaviour (tested under sanitizers;
Aristotle's partial results in `c/ARISTOTLE_RESULTS.md`), and whether the data file is the one the
authors analysed.
-/

namespace PCS.ClaimCheck.Assurance

open PCS.ClaimCheck

/-! ## 1. Fixed parts, digits -/

/-- `open PCS.ClaimCheck⏎⏎def pcs_src : Source := ` (45 bytes), `⟨` (E2 9F A8) and the `0` of
`0x`: the 49 bytes `PRE` of `pcs_srcbind.c`. -/
def PRE : List Nat :=
  [111, 112, 101, 110, 32, 80, 67, 83, 46, 67, 108, 97, 105, 109, 67, 104, 101, 99, 107, 10, 10,
   100, 101, 102, 32, 112, 99, 115, 95, 115, 114, 99, 32, 58, 32, 83, 111, 117, 114, 99, 101, 32, 58,
   61, 32, 0xE2, 0x9F, 0xA8, 48]

/-- `⟩` (E2 9F A9), newline, newline. -/
def SUF : List Nat := [0xE2, 0x9F, 0xA9, 10, 10]

/-- The largest data file the generator accepts (`MAX_DATA_BYTES`, `PCS_MAX_DATA`). -/
def MAXD : Nat := 65536

/-- The fixed parts are the UTF-8 bytes of the intended text. -/
theorem PRE_text : PRE = b "open PCS.ClaimCheck\n\ndef pcs_src : Source := ⟨0" := by decide +kernel
theorem SUF_text : SUF = b "⟩\n\n" := by decide +kernel

/-- A lowercase hexadecimal digit (uppercase is not canonical). -/
def isHex (c : Nat) : Bool := (decide (48 ≤ c) && decide (c ≤ 57)) || (decide (97 ≤ c) && decide (c ≤ 102))
def isDig (c : Nat) : Bool := decide (48 ≤ c) && decide (c ≤ 57)
def hexDigit (v : Nat) : Nat := if v < 10 then 48 + v else 87 + v
def hexVal (c : Nat) : Nat := if c ≤ 57 then c - 48 else c - 87

theorem isHex_iff (c : Nat) : isHex c = true ↔ (48 ≤ c ∧ c ≤ 57) ∨ (97 ≤ c ∧ c ≤ 102) := by
  simp [isHex]

theorem isDig_iff (c : Nat) : isDig c = true ↔ 48 ≤ c ∧ c ≤ 57 := by
  simp [isDig]

theorem hexDigit_isHex {v : Nat} (h : v < 16) : isHex (hexDigit v) = true := by
  rw [isHex_iff]; unfold hexDigit; split <;> omega

theorem hexVal_hexDigit {v : Nat} (h : v < 16) : hexVal (hexDigit v) = v := by
  unfold hexVal hexDigit; split <;> split <;> omega

theorem hexDigit_hexVal {c : Nat} (h : isHex c = true) : hexDigit (hexVal c) = c := by
  rw [isHex_iff] at h; unfold hexDigit hexVal; split <;> split <;> omega

theorem hexVal_lt {c : Nat} (h : isHex c = true) : hexVal c < 16 := by
  rw [isHex_iff] at h; unfold hexVal; split <;> omega

/-! ## 2. The canonical header -/

/-- Two lowercase hexadecimal digits per byte, first byte first. -/
def hexBytes : List Nat → List Nat
  | [] => []
  | x :: d => hexDigit (x / 16) :: hexDigit (x % 16) :: hexBytes d

/-- The digits after `0x`: `0` for the empty file. -/
def hexOf : List Nat → List Nat
  | [] => [48]
  | x :: d => hexBytes (x :: d)

/-- Decimal digits of `n`, given at least `n` steps of fuel.  Structural recursion, so that the
kernel can evaluate it (well-founded recursion does not reduce in the kernel). -/
def decStrAux : Nat → Nat → List Nat
  | 0, n => [48 + n]
  | fuel + 1, n => if n < 10 then [48 + n] else decStrAux fuel (n / 10) ++ [48 + n % 10]

/-- Decimal digits without a leading zero. -/
def decStr (n : Nat) : List Nat := decStrAux n n

theorem decStrAux_fuel (f : Nat) : ∀ n f', n ≤ f → n ≤ f' → decStrAux f n = decStrAux f' n := by
  induction f with
  | zero =>
    intro n f' hn _
    have : n = 0 := by omega
    subst this
    cases f' <;> simp [decStrAux]
  | succ k ih =>
    intro n f' hn hn'
    cases f' with
    | zero => have : n = 0 := by omega
              subst this; simp [decStrAux]
    | succ k' =>
      simp only [decStrAux]
      split
      · rfl
      · rename_i h
        rw [ih (n / 10) k' (by omega) (by omega)]

/-- The defining equation of `decStr`. -/
theorem decStr_eq (n : Nat) : decStr n = if n < 10 then [48 + n] else decStr (n / 10) ++ [48 + n % 10] := by
  unfold decStr
  cases n with
  | zero => simp [decStrAux]
  | succ k =>
    simp only [decStrAux]
    split
    · rfl
    · rename_i h
      rw [decStrAux_fuel k ((k + 1) / 10) ((k + 1) / 10) (by omega) (by omega)]

/-- `canon d`: the header the generator writes for the data `d`. -/
def canon (d : List Nat) : List Nat :=
  PRE ++ 120 :: (hexOf d ++ 44 :: 32 :: (decStr d.length ++ SUF))

/-- The standard value of a decimal digit string. -/
def decVal (ds : List Nat) : Nat := ds.foldl (fun acc c => acc * 10 + (c - 48)) 0

/-- The standard value of a hexadecimal digit string (after `0x`). -/
def hexValue (ds : List Nat) : Nat := ds.foldl (fun acc c => acc * 16 + hexVal c) 0

/-! ## 3. The decoder (step by step as `pcs_header_decode`) -/

/-- Bytes from pairs of hexadecimal digits. -/
def unhex : List Nat → List Nat
  | a :: b :: r => (16 * hexVal a + hexVal b) :: unhex r
  | _ => []

/-- The hexadecimal run: one digit `0` is the empty file; otherwise an even number of digits, at
most `MAXD` and `cap` bytes. -/
def hexData (hs : List Nat) (cap : Nat) : Option (List Nat) :=
  if hs.length = 1 then (if hs = [48] then some [] else none)
  else if hs.length = 0 ∨ hs.length % 2 = 1 then none
  else if MAXD < hs.length / 2 ∨ cap < hs.length / 2 then none
  else some (unhex hs)

/-- The decimal run: at least one digit, no leading zero, value at most `MAXD`. -/
def decLen (ds : List Nat) : Option Nat :=
  if ds = [] then none
  else if 2 ≤ ds.length ∧ ds.head? = some 48 then none
  else if MAXD < decVal ds then none
  else some (decVal ds)

/-- The strict decoder.  Returns the data and the length of the header, or `none`. -/
def decode (buf : List Nat) (cap : Nat) : Option (List Nat × Nat) :=
  if buf.take (PRE.length + 1) = PRE ++ [120] then
    match hexData ((buf.drop (PRE.length + 1)).takeWhile isHex) cap with
    | none => none
    | some d =>
      if ((buf.drop (PRE.length + 1)).drop ((buf.drop (PRE.length + 1)).takeWhile isHex).length).take 2
          = [44, 32] then
        match decLen ((((buf.drop (PRE.length + 1)).drop
            ((buf.drop (PRE.length + 1)).takeWhile isHex).length).drop 2).takeWhile isDig) with
        | none => none
        | some len =>
          if len = d.length ∧
              ((((buf.drop (PRE.length + 1)).drop ((buf.drop (PRE.length + 1)).takeWhile isHex).length).drop 2).drop
                ((((buf.drop (PRE.length + 1)).drop
                  ((buf.drop (PRE.length + 1)).takeWhile isHex).length).drop 2).takeWhile isDig).length).take SUF.length
                = SUF then
            some (d, PRE.length + 1 + ((buf.drop (PRE.length + 1)).takeWhile isHex).length + 2 +
              ((((buf.drop (PRE.length + 1)).drop
                ((buf.drop (PRE.length + 1)).takeWhile isHex).length).drop 2).takeWhile isDig).length + SUF.length)
          else none
      else none
  else none

/-! ## 4. Lists -/

theorem take_cons_len (l X : List Nat) (a : Nat) : (l ++ a :: X).take (l.length + 1) = l ++ [a] := by
  induction l with
  | nil => simp
  | cons y l ih => simp [ih]

theorem drop_cons_len (l X : List Nat) (a : Nat) : (l ++ a :: X).drop (l.length + 1) = X := by
  induction l with
  | nil => simp
  | cons y l ih => simpa using ih

theorem takeWhile_append_stop {p : Nat → Bool} {l r : List Nat} {y : Nat}
    (hl : ∀ x ∈ l, p x = true) (hy : p y = false) : (l ++ y :: r).takeWhile p = l := by
  induction l with
  | nil => simp [hy]
  | cons x l ih =>
    have hx : p x = true := hl x (by simp)
    simp [List.takeWhile_cons, hx, ih (fun z hz => hl z (by simp [hz]))]

theorem takeWhile_all (p : Nat → Bool) (l : List Nat) : ∀ x ∈ l.takeWhile p, p x = true := by
  induction l with
  | nil => simp
  | cons y l ih =>
    intro x hx
    rw [List.takeWhile_cons] at hx
    split at hx
    · rcases List.mem_cons.mp hx with h | h
      · rw [h]; assumption
      · exact ih x h
    · simp at hx

theorem takeWhile_append_drop (p : Nat → Bool) (l : List Nat) :
    l.takeWhile p ++ l.drop (l.takeWhile p).length = l := by
  induction l with
  | nil => simp
  | cons y l ih =>
    rw [List.takeWhile_cons]
    split
    · simp [ih]
    · simp

theorem eq_append_of_take_eq {l pre : List Nat} (h : l.take pre.length = pre) :
    l = pre ++ l.drop pre.length := by
  have := List.take_append_drop pre.length l
  rw [h] at this
  exact this.symm

/-! ## 5. Decimal digits -/

theorem decVal_append (ds : List Nat) (c : Nat) : decVal (ds ++ [c]) = decVal ds * 10 + (c - 48) := by
  simp [decVal, List.foldl_append]

theorem decStr_ne_nil (n : Nat) : decStr n ≠ [] := by
  rw [decStr_eq]; split <;> simp

theorem decStr_digits (n : Nat) : ∀ c ∈ decStr n, isDig c = true := by
  intro c hc
  rw [decStr_eq] at hc
  split at hc
  · simp at hc; rw [isDig_iff]; omega
  · rcases List.mem_append.mp hc with h | h
    · exact decStr_digits (n / 10) c h
    · simp at h; rw [isDig_iff]; omega
termination_by n
decreasing_by omega

theorem decVal_decStr (n : Nat) : decVal (decStr n) = n := by
  rw [decStr_eq]
  split
  · simp [decVal]
  · rw [decVal_append, decVal_decStr (n / 10)]; omega
termination_by n
decreasing_by omega

theorem decStr_head_ne_zero (n : Nat) (c : Nat) (hc : (decStr n).head? = some c) (h48 : c = 48) :
    n = 0 := by
  rw [decStr_eq] at hc
  split at hc
  · simp at hc; omega
  · rename_i hn
    rw [List.head?_append] at hc
    have hne := decStr_ne_nil (n / 10)
    cases e : (decStr (n / 10)).head? with
    | none => exact absurd (List.head?_eq_none_iff.mp e) hne
    | some c' =>
      rw [e] at hc
      simp at hc
      have := decStr_head_ne_zero (n / 10) c' e (by omega)
      omega
termination_by n
decreasing_by omega

theorem foldl_dec_ge (ds : List Nat) (acc : Nat) :
    acc ≤ ds.foldl (fun a c => a * 10 + (c - 48)) acc := by
  induction ds generalizing acc with
  | nil => simp
  | cons c ds ih => simp only [List.foldl_cons]; exact Nat.le_trans (by omega) (ih _)

/-- A digit string with no leading zero is the decimal representation of its value. -/
theorem decStr_decVal_rev (rs : List Nat) (hne : rs ≠ []) (hd : ∀ c ∈ rs, isDig c = true)
    (hz : ¬ (2 ≤ rs.length ∧ rs.reverse.head? = some 48)) : decStr (decVal rs.reverse) = rs.reverse := by
  induction rs with
  | nil => exact absurd rfl hne
  | cons c rs ih =>
    have hc := (isDig_iff c).mp (hd c (by simp))
    rw [List.reverse_cons, decVal_append]
    cases rs with
    | nil =>
      simp [decVal]
      rw [decStr_eq]
      simp only [show c - 48 < 10 by omega, if_true]
      simp; omega
    | cons c' rs' =>
      have hne' : (c' :: rs').reverse ≠ [] := by simp
      have hhead : (c' :: rs').reverse.head? = ((c' :: rs').reverse ++ [c]).head? := by
        rw [List.head?_append]
        cases e : (c' :: rs').reverse.head? with
        | none => exact absurd (List.head?_eq_none_iff.mp e) hne'
        | some _ => rfl
      have hz' : ¬ (2 ≤ (c' :: rs').length ∧ (c' :: rs').reverse.head? = some 48) := by
        intro ⟨_, h48⟩
        apply hz
        refine ⟨by simp, ?_⟩
        rw [List.reverse_cons, ← hhead, h48]
      have ih' := ih (by simp) (fun x hx => hd x (by simp [hx])) hz'
      have hv : 1 ≤ decVal (c' :: rs').reverse := by
        -- the first digit is not 0
        cases e : (c' :: rs').reverse with
        | nil => exact absurd e hne'
        | cons h t =>
          have hh : h ≠ 48 := by
            intro h48; apply hz; refine ⟨by simp, ?_⟩
            rw [List.reverse_cons, e]; simp [h48]
          have hmem : h ∈ (c' :: rs') := by
            have : h ∈ (c' :: rs').reverse := by rw [e]; simp
            exact List.mem_reverse.mp this
          have hdig := (isDig_iff h).mp (hd h (by simp [hmem]))
          simp only [decVal, List.foldl_cons]
          exact Nat.le_trans (by omega) (foldl_dec_ge t _)
      rw [decStr_eq]
      simp only [show ¬ (decVal (c' :: rs').reverse * 10 + (c - 48) < 10) by omega, if_false]
      have e1 : (decVal (c' :: rs').reverse * 10 + (c - 48)) / 10 = decVal (c' :: rs').reverse := by omega
      have e2 : 48 + (decVal (c' :: rs').reverse * 10 + (c - 48)) % 10 = c := by omega
      rw [e1, e2, ih']

theorem decStr_decVal (ds : List Nat) (hne : ds ≠ []) (hd : ∀ c ∈ ds, isDig c = true)
    (hz : ¬ (2 ≤ ds.length ∧ ds.head? = some 48)) : decStr (decVal ds) = ds := by
  have := decStr_decVal_rev ds.reverse (by simpa using hne) (by simpa using hd) (by simpa using hz)
  simpa using this

/-! ## 6. Hexadecimal digits -/

theorem hexBytes_length (d : List Nat) : (hexBytes d).length = 2 * d.length := by
  induction d with
  | nil => rfl
  | cons x d ih => simp [hexBytes, ih]; try omega

theorem hexBytes_isHex (d : List Nat) (h : ∀ x ∈ d, x < 256) : ∀ c ∈ hexBytes d, isHex c = true := by
  induction d with
  | nil => simp [hexBytes]
  | cons x d ih =>
    have hx := h x (by simp)
    intro c hc
    simp only [hexBytes, List.mem_cons] at hc
    rcases hc with hc | hc | hc
    · rw [hc]; exact hexDigit_isHex (by omega)
    · rw [hc]; exact hexDigit_isHex (by omega)
    · exact ih (fun y hy => h y (by simp [hy])) c hc

theorem unhex_hexBytes (d : List Nat) (h : ∀ x ∈ d, x < 256) : unhex (hexBytes d) = d := by
  induction d with
  | nil => rfl
  | cons x d ih =>
    have hx := h x (by simp)
    simp only [hexBytes, unhex]
    rw [hexVal_hexDigit (by omega), hexVal_hexDigit (by omega), ih (fun y hy => h y (by simp [hy]))]
    congr 1; omega

theorem hexBytes_unhex (n : Nat) : ∀ hs : List Nat, hs.length = 2 * n → (∀ c ∈ hs, isHex c = true) →
    hexBytes (unhex hs) = hs := by
  induction n with
  | zero => intro hs hl _; simp at hl; rw [hl]; rfl
  | succ n ih =>
    intro hs hl hh
    match hs, hl with
    | a :: b :: r, hl =>
      have ha := hexVal_lt (hh a (by simp))
      have hb := hexVal_lt (hh b (by simp))
      simp only [unhex, hexBytes]
      have e1 : (16 * hexVal a + hexVal b) / 16 = hexVal a := by omega
      have e2 : (16 * hexVal a + hexVal b) % 16 = hexVal b := by omega
      rw [e1, e2, hexDigit_hexVal (hh a (by simp)), hexDigit_hexVal (hh b (by simp)),
        ih r (by simp at hl; omega) (fun c hc => hh c (by simp [hc]))]

theorem unhex_lt (hs : List Nat) (h : ∀ c ∈ hs, isHex c = true) : ∀ x ∈ unhex hs, x < 256 := by
  induction hs using unhex.induct with
  | case1 a b r ih =>
    intro x hx
    simp only [unhex, List.mem_cons] at hx
    have ha := hexVal_lt (h a (by simp))
    have hb := hexVal_lt (h b (by simp))
    rcases hx with hx | hx
    · omega
    · exact ih (fun c hc => h c (by simp [hc])) x hx
  | case2 l _ => intro x hx; simp [unhex] at hx

theorem unhex_length (n : Nat) : ∀ hs : List Nat, hs.length = 2 * n → (unhex hs).length = n := by
  induction n with
  | zero => intro hs hl; simp at hl; rw [hl]; rfl
  | succ n ih =>
    intro hs hl
    match hs, hl with
    | a :: b :: r, hl => simp only [unhex, List.length_cons]; rw [ih r (by simp at hl; omega)]

theorem hexOf_isHex (d : List Nat) (h : ∀ x ∈ d, x < 256) : ∀ c ∈ hexOf d, isHex c = true := by
  cases d with
  | nil => simp [hexOf, isHex]
  | cons x d => exact hexBytes_isHex (x :: d) h

/-- The hexadecimal numeral of the header has the value of the big-endian bytes. -/
theorem foldl_hexBytes (d : List Nat) (acc : Nat) (h : ∀ x ∈ d, x < 256) :
    (hexBytes d).foldl (fun a c => a * 16 + hexVal c) acc = d.foldl (fun a x => a * 256 + x) acc := by
  induction d generalizing acc with
  | nil => rfl
  | cons x d ih =>
    have hx := h x (by simp)
    simp only [hexBytes, List.foldl_cons]
    rw [hexVal_hexDigit (by omega), hexVal_hexDigit (by omega)]
    have : (acc * 16 + x / 16) * 16 + x % 16 = acc * 256 + x := by omega
    rw [this]
    exact ih _ (fun y hy => h y (by simp [hy]))

theorem hexValue_hexOf (d : List Nat) (h : ∀ x ∈ d, x < 256) : hexValue (hexOf d) = ofBytes d := by
  cases d with
  | nil => rfl
  | cons x d => exact foldl_hexBytes (x :: d) 0 h

/-! ## 7. The decoder accepts every canonical header -/

theorem hexData_hexOf (d : List Nat) (cap : Nat) (hb : ∀ x ∈ d, x < 256) (hm : d.length ≤ MAXD)
    (hc : d.length ≤ cap) : hexData (hexOf d) cap = some d := by
  cases d with
  | nil => rfl
  | cons x d =>
    have hl := hexBytes_length (x :: d)
    simp only [List.length_cons] at hl hm hc
    unfold hexData
    simp only [hexOf, hl]
    rw [if_neg (by omega), if_neg (by omega), if_neg (by omega), unhex_hexBytes (x :: d) hb]

theorem decLen_decStr (n : Nat) (h : n ≤ MAXD) : decLen (decStr n) = some n := by
  unfold decLen
  rw [if_neg (decStr_ne_nil n)]
  have hz : ¬ (2 ≤ (decStr n).length ∧ (decStr n).head? = some 48) := by
    intro ⟨h2, hh⟩
    have := decStr_head_ne_zero n 48 hh rfl
    subst this
    rw [decStr_eq] at h2
    simp at h2
  rw [if_neg hz, decVal_decStr, if_neg (by omega)]

theorem SUF_head_not_digit (r : List Nat) : SUF ++ r = 0xE2 :: (List.drop 1 SUF ++ r) := rfl

/-- **Every canonical header is accepted and decodes to its data**, whatever follows it. -/
theorem decode_canon (d rest : List Nat) (cap : Nat) (hb : ∀ x ∈ d, x < 256) (hm : d.length ≤ MAXD)
    (hc : d.length ≤ cap) : decode (canon d ++ rest) cap = some (d, (canon d).length) := by
  have e0 : canon d ++ rest = PRE ++ 120 :: (hexOf d ++ 44 :: 32 :: (decStr d.length ++ (SUF ++ rest))) := by
    simp [canon, List.append_assoc]
  have hhex : (hexOf d ++ 44 :: 32 :: (decStr d.length ++ (SUF ++ rest))).takeWhile isHex = hexOf d :=
    takeWhile_append_stop (hexOf_isHex d hb) (by decide)
  have hdig : (decStr d.length ++ (SUF ++ rest)).takeWhile isDig = decStr d.length := by
    rw [SUF_head_not_digit]
    exact takeWhile_append_stop (decStr_digits _) (by decide)
  have hdrop1 : (hexOf d ++ 44 :: 32 :: (decStr d.length ++ (SUF ++ rest))).drop (hexOf d).length =
      44 :: 32 :: (decStr d.length ++ (SUF ++ rest)) := List.drop_left
  have hdrop2 : (decStr d.length ++ (SUF ++ rest)).drop (decStr d.length).length = SUF ++ rest := List.drop_left
  rw [e0]
  unfold decode
  rw [take_cons_len, if_pos rfl, drop_cons_len, hhex, hexData_hexOf d cap hb hm hc]
  simp only []
  rw [hdrop1]
  simp only [List.take_succ_cons, List.take_zero, List.drop_succ_cons, List.drop_zero, if_true]
  rw [hdig, decLen_decStr _ hm]
  simp only []
  rw [hdrop2, List.take_left]
  simp only [true_and, if_true]
  congr 2
  simp [canon, hexBytes_length]
  omega

/-! ## 8. Whatever the decoder accepts is a canonical header -/

theorem hexData_sound {hs : List Nat} {cap : Nat} {d : List Nat} (hh : ∀ c ∈ hs, isHex c = true)
    (h : hexData hs cap = some d) :
    hexOf d = hs ∧ d.length ≤ cap ∧ d.length ≤ MAXD ∧ ∀ x ∈ d, x < 256 := by
  unfold hexData at h
  split at h
  · rename_i h1
    split at h
    · rename_i h2
      cases h
      exact ⟨by rw [h2]; rfl, by simp, by simp [MAXD], by simp⟩
    · cases h
  · rename_i h1
    split at h
    · cases h
    · rename_i h2
      split at h
      · cases h
      · rename_i h3
        cases h
        obtain ⟨n, hn⟩ : ∃ n, hs.length = 2 * n := ⟨hs.length / 2, by omega⟩
        have hlen := unhex_length n hs hn
        have hne : unhex hs ≠ [] := by
          intro e; rw [e] at hlen; simp at hlen; omega
        refine ⟨?_, by omega, by omega, unhex_lt hs hh⟩
        cases e : unhex hs with
        | nil => exact absurd e hne
        | cons x d' =>
          show hexBytes (x :: d') = hs
          rw [← e]; exact hexBytes_unhex n hs hn hh

theorem decLen_sound {ds : List Nat} {len : Nat} (hd : ∀ c ∈ ds, isDig c = true)
    (h : decLen ds = some len) : ds = decStr len ∧ len ≤ MAXD := by
  unfold decLen at h
  split at h
  · cases h
  · rename_i h1
    split at h
    · cases h
    · rename_i h2
      split at h
      · cases h
      · rename_i h3
        cases h
        exact ⟨(decStr_decVal ds h1 hd h2).symm, by omega⟩

/-- **Whatever the decoder accepts begins with the canonical header of what it returns.** -/
theorem decode_sound {buf : List Nat} {cap : Nat} {d : List Nat} {L : Nat}
    (h : decode buf cap = some (d, L)) :
    buf.take L = canon d ∧ L = (canon d).length ∧ L ≤ buf.length ∧
      d.length ≤ cap ∧ d.length ≤ MAXD ∧ ∀ x ∈ d, x < 256 := by
  unfold decode at h
  split at h
  case isFalse => cases h
  case isTrue h1 =>
  generalize hr1 : buf.drop (PRE.length + 1) = r1 at h
  have hbuf : buf = PRE ++ 120 :: r1 := by
    have := eq_append_of_take_eq (pre := PRE ++ [120]) (by simpa using h1)
    rw [this, ← hr1]; simp
  generalize hhs : r1.takeWhile isHex = hs at h
  split at h
  case h_1 => cases h
  case h_2 d' hd =>
  obtain ⟨hhex, hcap, hmax, hbytes⟩ := hexData_sound (hhs ▸ takeWhile_all isHex r1) hd
  have hr1' : r1 = hs ++ r1.drop hs.length := by
    have := takeWhile_append_drop isHex r1
    rw [hhs] at this; exact this.symm
  generalize hr2 : r1.drop hs.length = r2 at h hr1'
  split at h
  case isFalse => cases h
  case isTrue h2 =>
  have hr2' : r2 = [44, 32] ++ r2.drop 2 := eq_append_of_take_eq (pre := [44, 32]) h2
  generalize hr3 : r2.drop 2 = r3 at h hr2'
  generalize hds : r3.takeWhile isDig = ds at h
  split at h
  case h_1 => cases h
  case h_2 len hlen =>
  obtain ⟨hdsc, hlmax⟩ := decLen_sound (hds ▸ takeWhile_all isDig r3) hlen
  have hr3' : r3 = ds ++ r3.drop ds.length := by
    have := takeWhile_append_drop isDig r3
    rw [hds] at this; exact this.symm
  generalize hr4 : r3.drop ds.length = r4 at h hr3'
  split at h
  case isFalse => cases h
  case isTrue h3 =>
  obtain ⟨hlend, h4⟩ := h3
  have hr4' : r4 = SUF ++ r4.drop SUF.length := eq_append_of_take_eq h4
  cases h
  have hfull : buf = canon d ++ r4.drop SUF.length := by
    rw [hbuf, hr1', hr2', hr3', hr4', ← hhex, hdsc, hlend]
    simp [canon, List.append_assoc]
  have hL : PRE.length + 1 + hs.length + 2 + ds.length + SUF.length = (canon d).length := by
    rw [← hhex, hdsc, hlend]; simp [canon]; omega
  refine ⟨?_, hL, ?_, hcap, hmax, hbytes⟩
  · rw [hL, hfull]; exact List.take_left
  · rw [hL, hfull]; simp

/-! ## 9. Consequences -/

/-- **No canonical header is a prefix of another**; in particular `canon` is injective. -/
theorem canon_prefix_free {d₁ d₂ r : List Nat} (h₁ : ∀ x ∈ d₁, x < 256) (h₂ : ∀ x ∈ d₂, x < 256)
    (m₁ : d₁.length ≤ MAXD) (m₂ : d₂.length ≤ MAXD) (h : canon d₁ ++ r = canon d₂) : d₁ = d₂ := by
  have e₁ := decode_canon d₁ r MAXD h₁ m₁ m₁
  have e₂ := decode_canon d₂ [] MAXD h₂ m₂ m₂
  rw [h] at e₁
  rw [List.append_nil] at e₂
  rw [e₁] at e₂
  cases e₂
  rfl

/-- **What an accepted header denotes.**  If the decoder accepts `buf` and returns `d`, then `buf`
begins with the canonical header of `d`; its hexadecimal numeral has the value `ofBytes d` and its
decimal numeral the value `d.length`; and the `Source` with those two values is well formed and its
bytes, the bytes every ClaimCheck theorem computes on, are exactly `d`. -/
theorem accepted_header_denotes_data {buf : List Nat} {cap : Nat} {d : List Nat} {L : Nat}
    (h : decode buf cap = some (d, L)) :
    buf.take L = PRE ++ 120 :: (hexOf d ++ 44 :: 32 :: (decStr d.length ++ SUF)) ∧
      hexValue (hexOf d) = ofBytes d ∧ decVal (decStr d.length) = d.length ∧
      (Source.mk (hexValue (hexOf d)) (decVal (decStr d.length))).wellFormed = true ∧
      (Source.mk (hexValue (hexOf d)) (decVal (decStr d.length))).bytes = d := by
  obtain ⟨htake, _, _, _, _, hb⟩ := decode_sound h
  have hv := hexValue_hexOf d hb
  have hn := decVal_decStr d.length
  obtain ⟨hw, hbytes⟩ := Source.bytes_ofBytes d hb
  refine ⟨htake, hv, hn, ?_, ?_⟩ <;> rw [hv, hn]
  · exact hw
  · exact hbytes

/-- The checker run on the source an accepted header denotes is the checker run on the parse of
exactly the decoded bytes. -/
theorem accepted_header_run {buf : List Nat} {cap : Nat} {d : List Nat} {L : Nat}
    (h : decode buf cap = some (d, L)) (c : Claim) (t : Table) (ht : parseTable d = some t) :
    run (Source.mk (hexValue (hexOf d)) (decVal (decStr d.length))) c = runTable t c := by
  obtain ⟨_, hv, hn, _, _⟩ := accepted_header_denotes_data h
  obtain ⟨_, _, _, _, _, hb⟩ := decode_sound h
  rw [hv, hn]
  exact run_ofBytes_some d hb c t ht

/-! ## 10. Negative controls and examples (evaluated by the kernel) -/

/-- The four bytes `a,b⏎`, followed by unrelated bytes: accepted, header length 49 + 1 + 8 + 2 + 1 + 5. -/
example : decode (canon [97, 44, 98, 10] ++ [100, 101, 102]) 65536 = some ([97, 44, 98, 10], 66) := by
  decide +kernel

example : (canon [97, 44, 98, 10]).length = 66 := by decide +kernel
example : decode (canon [] ++ [1]) 0 = some ([], 59) := by decide +kernel

/-- Uppercase hexadecimal digits are not canonical. -/
example : decode (PRE ++ 120 :: (b "6A, 1" ++ SUF)) 65536 = none := by decide +kernel
/-- A leading zero in the length, a wrong length, a missing digit, an extra digit are rejected. -/
example : decode (PRE ++ 120 :: (b "6a, 01" ++ SUF)) 65536 = none := by decide +kernel
example : decode (PRE ++ 120 :: (b "6a, 2" ++ SUF)) 65536 = none := by decide +kernel
example : decode (PRE ++ 120 :: (b "6, 1" ++ SUF)) 65536 = none := by decide +kernel
example : decode (PRE ++ 120 :: (b "6a0, 1" ++ SUF)) 65536 = none := by decide +kernel
/-- The empty file has exactly one spelling. -/
example : decode (PRE ++ 120 :: (b "00, 0" ++ SUF)) 65536 = none := by decide +kernel
example : decode (PRE ++ 120 :: (b ", 0" ++ SUF)) 65536 = none := by decide +kernel
example : decode (PRE ++ 120 :: (b "0, 1" ++ SUF)) 65536 = none := by decide +kernel
/-- A different but canonical header is accepted, with its own data: the decoder is not a
comparison against one fixed string. -/
example : decode (PRE ++ 120 :: (b "6b, 1" ++ SUF)) 65536 = some ([107], 60) := by decide +kernel
/-- The byte bound is needed in `decode_canon`: `256` is written with the non-digit `g`. -/
example : decode (canon [256]) 65536 = none := by decide +kernel
/-- The capacity bound is needed in `decode_canon`. -/
example : decode (canon [1, 2, 3]) 2 = none := by decide +kernel
/-- The size bound is needed: the decoder refuses a length above `MAXD`. -/
example : decLen (decStr (MAXD + 1)) = none := by decide +kernel

end PCS.ClaimCheck.Assurance
