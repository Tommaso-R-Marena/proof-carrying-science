import PCS.V2.Domains
import PCS.WireCheck
import PCS.WireCodec

/-!
# Shared typed-decoding helpers for the v0.6/v2 JSON objects

Generic, reusable pieces used by the normalized-decision wire, the normalized
index and the signature/package layers:

* `mapOpt` / `mapOpt_inv` : list decoding and its soundness;
* string-form predicates mirroring the production JSON-Schema patterns
  (`safeId`, `checker_version`), with Python's `$` already strengthened to `\Z`
  by `pcs/schema_validation.py::_anchor_patterns`;
* digest / predicate-commitment decoders and their soundness;
* enum name tables and their decoders.
-/

namespace PCS.V2.Common

open PCS PCS.Decision PCS.V2.Json PCS.V2.Hex

/-! ## Lists -/

def mapOpt {α β : Type} (f : α → Option β) : List α → Option (List β)
  | [] => some []
  | x :: xs =>
    match f x, mapOpt f xs with
    | some y, some ys => some (y :: ys)
    | _, _ => none

theorem mapOpt_inv {α β : Type} {f : α → Option β} {g : β → α}
    (hfg : ∀ x y, f x = some y → g y = x) :
    ∀ {xs : List α} {ys : List β}, mapOpt f xs = some ys → ys.map g = xs
  | [], ys, h => by simp [mapOpt] at h; subst h; rfl
  | x :: xs, ys, h => by
    simp only [mapOpt] at h
    split at h
    · rename_i y ys' hy hys
      cases h
      simp [hfg x y hy, mapOpt_inv hfg hys]
    · cases h

theorem map_injective_of {α β : Type} {f : α → β} (hf : ∀ a b, f a = f b → a = b) :
    ∀ {xs ys : List α}, xs.map f = ys.map f → xs = ys
  | [], [], _ => rfl
  | [], _ :: _, h => by simp at h
  | _ :: _, [], h => by simp at h
  | x :: xs, y :: ys, h => by
    simp only [List.map_cons, List.cons.injEq] at h
    rw [hf x y h.1, map_injective_of hf h.2]

theorem nodup_map_of_injective {α β : Type} {f : α → β} (hf : ∀ a b, f a = f b → a = b) :
    ∀ {xs : List α}, xs.Nodup → (xs.map f).Nodup
  | [], _ => List.nodup_nil
  | x :: xs, h => by
    simp only [List.nodup_cons, List.map_cons, List.mem_map] at h ⊢
    refine ⟨?_, nodup_map_of_injective hf h.2⟩
    rintro ⟨y, hy, hfy⟩
    exact h.1 (hf y x hfy ▸ hy)

/-! ## String forms (JSON-Schema patterns) -/

def isAsciiAlnum (c : Char) : Bool :=
  ('A' ≤ c && c ≤ 'Z') || ('a' ≤ c && c ≤ 'z') || ('0' ≤ c && c ≤ '9')

def isSafeIdTail (c : Char) : Bool :=
  isAsciiAlnum c || c == '_' || c == '.' || c == ':' || c == '-'

/-- `^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z` -/
def isSafeId (s : String) : Bool :=
  match s.toList with
  | [] => false
  | c :: cs => isAsciiAlnum c && cs.all isSafeIdTail && decide (cs.length ≤ 127)

def isSuffixChar (c : Char) : Bool := isAsciiAlnum c || c == '.' || c == '_' || c == '-'

/-- `^pcs-python-kernel/0\.6\.[0-9]+(?:-[A-Za-z0-9._-]+)?\Z` -/
def isCheckerVersion (s : String) : Bool :=
  let pre := "pcs-python-kernel/0.6.".toList
  let cs := s.toList
  let rest := cs.drop pre.length
  let ds := rest.takeWhile Char.isDigit
  let tl := rest.dropWhile Char.isDigit
  cs.take pre.length == pre && !ds.isEmpty &&
    (match tl with
     | [] => true
     | '-' :: sfx => !sfx.isEmpty && sfx.all isSuffixChar
     | _ => false)

def maxItems : Nat := 10000

def idArrayOK (ids : List String) : Bool :=
  decide (ids.length ≤ maxItems) && ids.all isSafeId && decide ids.Nodup

/-! ## Digests -/

/-- A 32-byte SHA-256 digest written as exactly 64 lower-case hex characters. -/
def decDigest (s : String) : Option (List UInt8) :=
  match hexDecode s with
  | some d => if d.length = 32 then some d else none
  | none => none

theorem decDigest_sound {s : String} {d : List UInt8} (h : decDigest s = some d) :
    hexEncode d = s ∧ d.length = 32 := by
  unfold decDigest at h
  split at h
  · rename_i d' hd
    split at h
    · cases h; exact ⟨hexEncode_of_hexDecode hd, by assumption⟩
    · cases h
  · cases h

def predicatePrefix : String := "pcs-predicate-sha256-v2:"

/-- `pcs-predicate-sha256-v2:<64 hex>` -/
def commitmentStr (d : List UInt8) : String := String.ofList (predicatePrefix.toList ++ hexChars d)

def decCommitment (s : String) : Option (List UInt8) :=
  if s.toList.take predicatePrefix.length = predicatePrefix.toList then
    decDigest (String.ofList (s.toList.drop predicatePrefix.length))
  else none

theorem predicatePrefix_toList_length : predicatePrefix.toList.length = predicatePrefix.length := by
  decide

theorem decCommitment_sound {s : String} {d : List UInt8} (h : decCommitment s = some d) :
    commitmentStr d = s ∧ d.length = 32 := by
  unfold decCommitment at h
  split at h
  · rename_i hp
    obtain ⟨he, hl⟩ := decDigest_sound h
    refine ⟨?_, hl⟩
    unfold commitmentStr
    have : hexChars d = s.toList.drop predicatePrefix.length := by
      have := congrArg String.toList he
      simpa [hexEncode] using this
    rw [this, ← hp, List.take_append_drop]
    simp
  · cases h

theorem hexChars_injective {a b : List UInt8} (h : hexChars a = hexChars b) : a = b := by
  have ha := decodeChars_hexChars a
  rw [h, decodeChars_hexChars] at ha
  exact (Option.some.inj ha).symm

theorem commitmentStr_injective {a b : List UInt8} (h : commitmentStr a = commitmentStr b) :
    a = b := by
  unfold commitmentStr at h
  have := congrArg String.toList h
  simp only [String.toList_ofList, List.append_cancel_left_eq] at this
  exact hexChars_injective this

/-! ## Enumerations (exact production spellings) -/

def claimKindName : ClaimKind → String
  | .formal => "formal"
  | .computational => "computational"
  | .empirical => "empirical"
  | .mixed => "mixed"

def evidenceKindName : EvidenceKind → String
  | .formalProof => "formal_proof"
  | .computationalTest => "computational_test"
  | .statisticalValidation => "statistical_validation"
  | .empiricalValidation => "empirical_validation"
  | .provenance => "provenance"

def outcomeName : Outcome → String
  | .pass => "PASS"
  | .fail => "FAIL"
  | .unverified => "UNVERIFIED"

def decisionName : DecisionStatus → String
  | .formal => "FORMALLY_VERIFIED_UNDER_ASSUMPTIONS"
  | .computational => "COMPUTATIONALLY_SUPPORTED"
  | .empirical => "EMPIRICALLY_VALIDATED_WITHIN_SCOPE"
  | .mixed => "MIXED_SUPPORT_UNDER_ASSUMPTIONS"
  | .open_ => "OPEN"
  | .failed => "FALSIFIED_OR_CHECK_FAILED"

def allClaimKinds : List ClaimKind := [.formal, .computational, .empirical, .mixed]
def allEvidenceKinds : List EvidenceKind :=
  [.formalProof, .computationalTest, .statisticalValidation, .empiricalValidation, .provenance]
def allOutcomes : List Outcome := [.pass, .fail, .unverified]
def allDecisions : List DecisionStatus := [.formal, .computational, .empirical, .mixed, .open_, .failed]

def decodeEnum {α : Type} (all : List α) (name : α → String) (s : String) : Option α :=
  all.find? fun a => name a == s

theorem decodeEnum_sound {α : Type} {all : List α} {name : α → String} {s : String} {a : α}
    (h : decodeEnum all name s = some a) : name a = s := by
  unfold decodeEnum at h
  have := List.find?_some h
  simpa using this

theorem claimKindName_injective : ∀ a b, claimKindName a = claimKindName b → a = b := by
  intro a b; cases a <;> cases b <;> decide
theorem evidenceKindName_injective : ∀ a b, evidenceKindName a = evidenceKindName b → a = b := by
  intro a b; cases a <;> cases b <;> decide
theorem outcomeName_injective : ∀ a b, outcomeName a = outcomeName b → a = b := by
  intro a b; cases a <;> cases b <;> decide
theorem decisionName_injective : ∀ a b, decisionName a = decisionName b → a = b := by
  intro a b; cases a <;> cases b <;> decide

/-- The v2 enum decoders agree with the existing v1 `WireCodec` decoders on every
    production spelling. -/
theorem claimKind_names_agree_v1 :
    ∀ k ∈ allClaimKinds, PCS.WireCodec.decodeClaimKind (claimKindName k) = some k := by decide
theorem evidenceKind_names_agree_v1 :
    ∀ k ∈ allEvidenceKinds, PCS.WireCodec.decodeEvidenceKind (evidenceKindName k) = some k := by
  decide
theorem outcome_names_agree_v1 :
    ∀ k ∈ allOutcomes, PCS.WireCodec.decodeOutcome (outcomeName k) = some k := by decide
theorem decision_names_agree_v1 :
    ∀ k ∈ allDecisions, PCS.WireCodec.decodeDecisionStatus (decisionName k) = some k := by decide

/-! ## JSON accessors -/

def strOf : JVal → Option String
  | .str s => some s
  | _ => none

theorem strOf_sound {v : JVal} {s : String} (h : strOf v = some s) : JVal.str s = v := by
  cases v <;> simp [strOf] at h; subst h; rfl

def strArray : JVal → Option (List String)
  | .arr xs => mapOpt strOf xs
  | _ => none

theorem strArray_sound {v : JVal} {ss : List String} (h : strArray v = some ss) :
    JVal.arr (ss.map JVal.str) = v := by
  cases v <;> simp [strArray] at h
  rw [mapOpt_inv (fun x y hxy => strOf_sound hxy) h]

end PCS.V2.Common
