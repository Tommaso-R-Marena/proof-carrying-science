import Lean

/-!
# A fully verified canonical integer / field codec (versioned wire format `PGSI2`)

The earlier `PGSI1` artifact format (`ProofGatedArtifacts`) is built from Lean core's
`toString : Int → String`, `String.splitOn` and `String.toInt?`. In Lean 4.28 the
rendering of a **negative** integer is

  `toString (Int.negSucc n) = String.Internal.append "-" (toString (n+1))`

and `String.Internal.append` is an `opaque` constant (implemented natively by
`lean_string_append`), about which the logic knows nothing. See
`ProofGatedV1Analysis` for the consequences. This module therefore defines a
transparent codec on `List Char`, proves it correct for **all** integers, and
bridges it to core `toString` where that is possible.

Main results:
* `parseNat_renderNat`, `parseInt_renderInt`: decode-after-encode, for every `Nat`/`Int`;
* `parseInt_eq_some_iff`: the decoder accepts **exactly** the canonical renderings
  (so `"-0"`, `"007"`, `"+5"`, `""`, `"1_000"` are all rejected — `noncanonical_rejected`);
* `renderInt_injective`;
* `splitFields_joinFields`, `joinFields_splitFields`: the `|`-delimited field protocol is
  a bijection between `|`-free field lists and character lists;
* `decodeInts_encodeInts`, `decodeInts_canonical`: tagged integer-vector records;
* `toString_ofNat_toList`: for nonnegative integers the renderer agrees with core
  `toString` (unconditionally); `toString_toList_of_append_spec`: for all integers,
  under the explicit hypothesis that the opaque runtime append behaves as `++`.
-/

namespace PCS.V2.ProofGatedCodec

/-! ## Natural numbers -/

def digitVal? (c : Char) : Option Nat :=
  if c = '0' then some 0 else if c = '1' then some 1 else if c = '2' then some 2
  else if c = '3' then some 3 else if c = '4' then some 4 else if c = '5' then some 5
  else if c = '6' then some 6 else if c = '7' then some 7 else if c = '8' then some 8
  else if c = '9' then some 9 else none

def parseNatAux : Nat → List Char → Option Nat
  | acc, [] => some acc
  | acc, c :: cs =>
      match digitVal? c with
      | some d => parseNatAux (acc * 10 + d) cs
      | none => none

/-- Digit-string parser; the empty string is rejected. -/
def parseNat : List Char → Option Nat
  | [] => none
  | c :: cs => parseNatAux 0 (c :: cs)

/-- The renderer is literally Lean core's `Nat.toDigits 10`. -/
def renderNat (n : Nat) : List Char := Nat.toDigits 10 n

theorem toDigitsCore_acc (f n : Nat) (ds : List Char) (h : n < f) :
    Nat.toDigitsCore 10 f n ds = Nat.toDigitsCore 10 f n [] ++ ds := by
  induction f generalizing n ds with
  | zero => omega
  | succ f ih =>
      simp only [Nat.toDigitsCore]
      by_cases h0 : n / 10 = 0
      · simp [h0]
      · simp only [h0, if_false]
        have hlt : n / 10 < f := by omega
        rw [ih (n / 10) _ hlt, ih (n / 10) [_] hlt]
        simp

theorem toDigitsCore_fuel (f₁ f₂ n : Nat) (ds : List Char) (h₁ : n < f₁) (h₂ : n < f₂) :
    Nat.toDigitsCore 10 f₁ n ds = Nat.toDigitsCore 10 f₂ n ds := by
  induction f₁ generalizing f₂ n ds with
  | zero => omega
  | succ f ih =>
      cases f₂ with
      | zero => omega
      | succ g =>
          simp only [Nat.toDigitsCore]
          by_cases h0 : n / 10 = 0
          · simp [h0]
          · simp only [h0, if_false]
            exact ih g (n / 10) _ (by omega) (by omega)

theorem renderNat_step (n : Nat) :
    renderNat n = (if n / 10 = 0 then [] else renderNat (n / 10)) ++
      [Nat.digitChar (n % 10)] := by
  have hl : ∀ k, renderNat k = Nat.toDigitsCore 10 (k + 1) k [] := fun _ => rfl
  rw [hl n]
  simp only [Nat.toDigitsCore]
  by_cases h0 : n / 10 = 0
  · simp [h0]
  · simp only [h0, if_false]
    rw [toDigitsCore_acc n (n / 10) _ (by omega), hl (n / 10),
      toDigitsCore_fuel n (n / 10 + 1) (n / 10) [] (by omega) (by omega)]

theorem renderNat_ne_nil (n : Nat) : renderNat n ≠ [] := by
  rw [renderNat_step]; simp

theorem digitVal_digitChar (d : Nat) (h : d < 10) : digitVal? (Nat.digitChar d) = some d := by
  match d, h with
  | 0, _ => rfl
  | 1, _ => rfl
  | 2, _ => rfl
  | 3, _ => rfl
  | 4, _ => rfl
  | 5, _ => rfl
  | 6, _ => rfl
  | 7, _ => rfl
  | 8, _ => rfl
  | 9, _ => rfl

theorem parseNatAux_append (acc : Nat) (l : List Char) (c : Char) :
    parseNatAux acc (l ++ [c]) =
      (parseNatAux acc l).bind fun k => (digitVal? c).map fun d => k * 10 + d := by
  induction l generalizing acc with
  | nil =>
      simp only [List.nil_append, parseNatAux, Option.bind_some]
      cases digitVal? c <;> rfl
  | cons a as ih =>
      simp only [List.cons_append, parseNatAux]
      cases digitVal? a with
      | none => rfl
      | some d => exact ih _

theorem parseNatAux_renderNat (n : Nat) : parseNatAux 0 (renderNat n) = some n := by
  induction n using Nat.strongRecOn with
  | _ n ih =>
      rw [renderNat_step, parseNatAux_append]
      by_cases h0 : n / 10 = 0
      · simp only [h0, if_true, parseNatAux, Option.bind_some,
          digitVal_digitChar _ (Nat.mod_lt n (by decide)), Option.map_some]
        congr 1; omega
      · simp only [h0, if_false]
        rw [ih (n / 10) (by omega)]
        simp only [Option.bind_some, digitVal_digitChar _ (Nat.mod_lt n (by decide)),
          Option.map_some]
        congr 1; omega

theorem parseNat_renderNat (n : Nat) : parseNat (renderNat n) = some n := by
  have h := parseNatAux_renderNat n
  cases hr : renderNat n with
  | nil => exact absurd hr (renderNat_ne_nil n)
  | cons c cs => rw [hr] at h; exact h

/-! ## Integers -/

def renderInt : Int → List Char
  | .ofNat n => renderNat n
  | .negSucc n => '-' :: renderNat (n + 1)

def parseIntRaw : List Char → Option Int
  | '-' :: ds => (parseNat ds).map fun n => -(n : Int)
  | ds => (parseNat ds).map fun n => (n : Int)

/-- Canonical integer decoder: parse, then insist that the text is the canonical
rendering of the parsed value. -/
def parseInt (l : List Char) : Option Int :=
  match parseIntRaw l with
  | some z => if renderInt z = l then some z else none
  | none => none

theorem renderNat_head_ne_minus (n : Nat) : ∃ c cs, renderNat n = c :: cs ∧ c ≠ '-' := by
  rw [renderNat_step]
  by_cases h0 : n / 10 = 0
  · refine ⟨Nat.digitChar (n % 10), [], by simp [h0], ?_⟩
    intro h
    have := digitVal_digitChar (n % 10) (Nat.mod_lt n (by decide))
    rw [h] at this
    simp [digitVal?] at this
  · obtain ⟨c, cs, hc, hne⟩ := renderNat_head_ne_minus (n / 10)
    exact ⟨c, cs ++ [Nat.digitChar (n % 10)], by simp [h0, hc], hne⟩
termination_by n
decreasing_by omega

theorem parseIntRaw_renderInt (z : Int) : parseIntRaw (renderInt z) = some z := by
  cases z with
  | ofNat n =>
      obtain ⟨c, cs, hc, hne⟩ := renderNat_head_ne_minus n
      simp only [renderInt]
      rw [hc]
      have : parseIntRaw (c :: cs) = (parseNat (c :: cs)).map fun n => (n : Int) := by
        unfold parseIntRaw
        split
        · rename_i h; simp at h; exact absurd h.1 hne
        · rfl
      rw [this, ← hc, parseNat_renderNat]
      rfl
  | negSucc n =>
      simp only [renderInt, parseIntRaw, parseNat_renderNat]
      rfl

/-- **Integer roundtrip, for every integer.** -/
theorem parseInt_renderInt (z : Int) : parseInt (renderInt z) = some z := by
  simp [parseInt, parseIntRaw_renderInt]

/-- **Exact acceptance characterisation**: the decoder accepts a character list iff it
is the canonical rendering of the returned integer. -/
theorem parseInt_eq_some_iff (l : List Char) (z : Int) :
    parseInt l = some z ↔ renderInt z = l := by
  constructor
  · intro h
    unfold parseInt at h
    split at h
    · rename_i w _
      by_cases hr : renderInt w = l
      · simp [hr] at h; subst h; exact hr
      · simp [hr] at h
    · simp at h
  · intro h; subst h; exact parseInt_renderInt z

theorem parseInt_canonical {l : List Char} {z : Int} (h : parseInt l = some z) :
    renderInt z = l := (parseInt_eq_some_iff l z).mp h

theorem renderInt_injective {a b : Int} (h : renderInt a = renderInt b) : a = b := by
  have h1 := parseInt_renderInt a
  rw [h, parseInt_renderInt] at h1
  exact (Option.some.inj h1).symm

/-- Rejection of non-canonical spellings (examples of the general
`parseInt_eq_some_iff`). -/
theorem noncanonical_rejected :
    parseInt "-0".toList = none ∧ parseInt "007".toList = none ∧
    parseInt "+5".toList = none ∧ parseInt "".toList = none ∧
    parseInt "1_000".toList = none ∧ parseInt "-".toList = none ∧
    parseInt " 5".toList = none ∧ parseInt "--5".toList = none := by
  decide +kernel

theorem canonical_examples :
    parseInt "0".toList = some 0 ∧ parseInt "-32".toList = some (-32) ∧
    parseInt "32".toList = some 32 ∧ parseInt "1000".toList = some 1000 := by
  decide +kernel

theorem digitVal_ne_pipe : ∀ c, digitVal? c ≠ none → c ≠ '|' := by
  intro c h hc; subst hc; exact h rfl

theorem pipe_not_mem_renderNat (n : Nat) : '|' ∉ renderNat n := by
  intro hmem
  have hd : ∀ d, d < 10 → Nat.digitChar d ≠ '|' := by
    intro d hd heq
    have := digitVal_digitChar d hd
    rw [heq] at this
    simp [digitVal?] at this
  induction n using Nat.strongRecOn with
  | _ n ih =>
      rw [renderNat_step] at hmem
      simp only [List.mem_append, List.mem_singleton] at hmem
      rcases hmem with hm | hm
      · by_cases h0 : n / 10 = 0
        · simp [h0] at hm
        · simp only [h0, if_false] at hm
          exact ih (n / 10) (by omega) hm
      · exact hd _ (Nat.mod_lt n (by decide)) hm.symm

theorem pipe_not_mem_renderInt (z : Int) : '|' ∉ renderInt z := by
  cases z with
  | ofNat n => exact pipe_not_mem_renderNat n
  | negSucc n =>
      simp only [renderInt, List.mem_cons]
      rintro (h | h)
      · exact absurd h (by decide)
      · exact pipe_not_mem_renderNat _ h

/-! ## Bridge to Lean core `toString` -/

/-- For nonnegative integers the transparent renderer is exactly core `toString`. -/
theorem toString_ofNat_toList (n : Nat) :
    (toString (Int.ofNat n)).toList = renderInt (Int.ofNat n) := by
  show (Nat.repr n).toList = renderNat n
  simp [Nat.repr, renderNat, String.toList_ofList]

/-- Core `toString` of a negative integer is defined through the opaque primitive
`String.Internal.append` (definitional unfolding, no assumption). -/
theorem toString_negSucc_def (n : Nat) :
    toString (Int.negSucc n) = String.Internal.append "-" (toString (n + 1)) := rfl

/-- Under the explicit (runtime-implementation) hypothesis that the opaque append
behaves as string concatenation on the `"-"` prefix, core `toString` agrees with the
transparent renderer on **all** integers. -/
theorem toString_toList_of_append_spec
    (happ : ∀ s : String, String.Internal.append "-" s = "-" ++ s) (z : Int) :
    (toString z).toList = renderInt z := by
  cases z with
  | ofNat n => exact toString_ofNat_toList n
  | negSucc n =>
      rw [toString_negSucc_def, happ, String.toList_append]
      show ['-'] ++ (Nat.repr (n + 1)).toList = '-' :: renderNat (n + 1)
      simp [Nat.repr, renderNat, String.toList_ofList]

/-! ## `|`-delimited fields -/

def joinFields : List (List Char) → List Char
  | [] => []
  | [f] => f
  | f :: g :: fs => f ++ '|' :: joinFields (g :: fs)

def splitFields : List Char → List (List Char)
  | [] => [[]]
  | c :: cs =>
      if c = '|' then [] :: splitFields cs
      else
        match splitFields cs with
        | f :: fs => (c :: f) :: fs
        | [] => [[c]]

theorem splitFields_ne_nil (l : List Char) : splitFields l ≠ [] := by
  cases l with
  | nil => simp [splitFields]
  | cons c cs =>
      simp only [splitFields]
      split
      · simp
      · split <;> simp

theorem splitFields_pipe_free_append (f rest : List Char) (hf : '|' ∉ f) :
    splitFields (f ++ rest) =
      match splitFields rest with
      | g :: gs => (f ++ g) :: gs
      | [] => [f] := by
  induction f with
  | nil =>
      simp only [List.nil_append]
      cases h : splitFields rest with
      | nil => exact absurd h (splitFields_ne_nil rest)
      | cons g gs => rfl
  | cons c cs ih =>
      have hc : c ≠ '|' := fun h => hf (h ▸ List.mem_cons_self)
      have hcs : '|' ∉ cs := fun h => hf (List.mem_cons_of_mem c h)
      simp only [List.cons_append, splitFields, hc, if_false, ih hcs]
      cases h : splitFields rest with
      | nil => exact absurd h (splitFields_ne_nil rest)
      | cons g gs => rfl

/-- **Delimiter-protocol roundtrip**. -/
theorem splitFields_joinFields (fs : List (List Char)) (hne : fs ≠ [])
    (hfree : ∀ f ∈ fs, '|' ∉ f) : splitFields (joinFields fs) = fs := by
  induction fs with
  | nil => exact absurd rfl hne
  | cons f fs ih =>
      cases fs with
      | nil =>
          have := splitFields_pipe_free_append f [] (hfree f List.mem_cons_self)
          simp only [List.append_nil] at this
          simp [joinFields, this, splitFields]
      | cons g gs =>
          simp only [joinFields]
          rw [splitFields_pipe_free_append f _ (hfree f List.mem_cons_self)]
          have hrest := ih (by simp) (fun h hm => hfree h (List.mem_cons_of_mem f hm))
          simp [splitFields, hrest]

theorem joinFields_cons_cons (c : Char) (f : List Char) (fs : List (List Char)) :
    joinFields ((c :: f) :: fs) = c :: joinFields (f :: fs) := by
  cases fs <;> rfl

/-- Splitting loses no information: joining the fields recovers every input. -/
theorem joinFields_splitFields (l : List Char) : joinFields (splitFields l) = l := by
  induction l with
  | nil => rfl
  | cons c cs ih =>
      simp only [splitFields]
      by_cases hc : c = '|'
      · subst hc
        simp only [if_true]
        cases h : splitFields cs with
        | nil => exact absurd h (splitFields_ne_nil cs)
        | cons g gs => rw [h] at ih; simp [joinFields, ih]
      · simp only [hc, if_false]
        cases h : splitFields cs with
        | nil => exact absurd h (splitFields_ne_nil cs)
        | cons g gs => rw [h] at ih; rw [joinFields_cons_cons, ih]

/-! ## Tagged integer-vector records -/

def encodeInts (tag : List Char) (zs : List Int) : List Char :=
  joinFields (tag :: zs.map renderInt)

def decodeInts (tag : List Char) (l : List Char) : Option (List Int) :=
  match splitFields l with
  | t :: fs => if t = tag then fs.mapM parseInt else none
  | [] => none

theorem mapM_parseInt_render (zs : List Int) : (zs.map renderInt).mapM parseInt = some zs := by
  induction zs with
  | nil => rfl
  | cons z zs ih => simp [List.mapM_cons, parseInt_renderInt, ih]

theorem mapM_parseInt_canonical {fs : List (List Char)} {zs : List Int}
    (h : fs.mapM parseInt = some zs) : zs.map renderInt = fs := by
  induction fs generalizing zs with
  | nil => simp at h; subst h; rfl
  | cons f fs ih =>
      simp only [List.mapM_cons] at h
      cases hf : parseInt f with
      | none => simp [hf] at h
      | some z =>
          cases hfs : fs.mapM parseInt with
          | none => simp [hf, hfs] at h
          | some ws =>
              simp [hf, hfs] at h
              subst h
              simp [parseInt_canonical hf, ih hfs]

theorem decodeInts_encodeInts (tag : List Char) (htag : '|' ∉ tag) (zs : List Int) :
    decodeInts tag (encodeInts tag zs) = some zs := by
  unfold decodeInts encodeInts
  rw [splitFields_joinFields _ (by simp)]
  · show (if tag = tag then (zs.map renderInt).mapM parseInt else none) = some zs
    rw [if_pos rfl, mapM_parseInt_render]
  · intro f hf
    simp only [List.mem_cons, List.mem_map] at hf
    rcases hf with rfl | ⟨z, _, rfl⟩
    · exact htag
    · exact pipe_not_mem_renderInt z

/-- **Record canonicity**: anything the record decoder accepts is the canonical
encoding of what it returns. -/
theorem decodeInts_canonical {tag l : List Char} {zs : List Int}
    (h : decodeInts tag l = some zs) : encodeInts tag zs = l := by
  unfold decodeInts at h
  have hj := joinFields_splitFields l
  cases hs : splitFields l with
  | nil => rw [hs] at h; simp at h
  | cons t fs =>
      rw [hs] at h hj
      by_cases ht : t = tag
      · subst ht
        simp only [if_true] at h
        unfold encodeInts
        rw [mapM_parseInt_canonical h]
        exact hj
      · simp [ht] at h

theorem encodeInts_injective (tag : List Char) (htag : '|' ∉ tag) {a b : List Int}
    (h : encodeInts tag a = encodeInts tag b) : a = b := by
  have h1 := decodeInts_encodeInts tag htag a
  rw [h, decodeInts_encodeInts tag htag b] at h1
  exact (Option.some.inj h1).symm

end PCS.V2.ProofGatedCodec
