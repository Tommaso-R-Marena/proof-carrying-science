import Std
namespace PCSActionFormat
abbrev Action := Fin 7
def encode (a : Action) : List Nat := [123,34,97,99,116,105,111,110,34,58,48+a.val,125]
def decode (raw : List Nat) : Option Action :=
  if raw = encode 0 then some 0 else if raw = encode 1 then some 1 else
  if raw = encode 2 then some 2 else if raw = encode 3 then some 3 else
  if raw = encode 4 then some 4 else if raw = encode 5 then some 5 else
  if raw = encode 6 then some 6 else none
theorem roundtrip : ∀ a : Action, decode (encode a) = some a := by decide
theorem injective {a b : Action} (h : encode a = encode b) : a = b := by
  have e := congrArg decode h
  simpa only [roundtrip, Option.some.injEq] using e
theorem decode_sound {raw : List Nat} {a : Action} (h : decode raw = some a) : encode a = raw := by
  unfold decode at h
  repeat (split at h <;> try simp_all)
theorem canonical_iff {raw : List Nat} : (∃ a, decode raw = some a) ↔ (∃ a, encode a = raw) := by
  constructor
  · rintro ⟨a,h⟩; exact ⟨a,decode_sound h⟩
  · rintro ⟨a,rfl⟩; exact ⟨a,roundtrip a⟩
theorem all_octets : ∀ a : Action, (encode a).all (· < 256) = true := by decide
theorem bypass_remains_representable : decode (encode 5) = some 5 := by decide

def encodeTokens (a : Action) : List Nat := [4913,1311,788,15+a.val,92,151645]
def decodeTokens (ids : List Nat) : Option Action :=
  if ids = encodeTokens 0 then some 0 else if ids = encodeTokens 1 then some 1 else
  if ids = encodeTokens 2 then some 2 else if ids = encodeTokens 3 then some 3 else
  if ids = encodeTokens 4 then some 4 else if ids = encodeTokens 5 then some 5 else
  if ids = encodeTokens 6 then some 6 else none
theorem token_roundtrip : ∀ a : Action, decodeTokens (encodeTokens a) = some a := by decide
theorem token_injective {a b : Action} (h : encodeTokens a = encodeTokens b) : a = b := by
  have e := congrArg decodeTokens h
  simpa only [token_roundtrip, Option.some.injEq] using e
theorem token_decode_sound {ids : List Nat} {a : Action} (h : decodeTokens ids = some a) : encodeTokens a = ids := by
  unfold decodeTokens at h
  repeat (split at h <;> try simp_all)
theorem token_byte_agreement : ∀ a : Action, decodeTokens (encodeTokens a) = decode (encode a) := by decide
theorem fixed_token_bound : ∀ a : Action, (encodeTokens a).length = 6 := by decide

end PCSActionFormat
#print axioms PCSActionFormat.roundtrip
#print axioms PCSActionFormat.injective
#print axioms PCSActionFormat.decode_sound
#print axioms PCSActionFormat.canonical_iff
#print axioms PCSActionFormat.all_octets
#print axioms PCSActionFormat.bypass_remains_representable

#print axioms PCSActionFormat.token_roundtrip
#print axioms PCSActionFormat.token_injective
#print axioms PCSActionFormat.token_decode_sound
#print axioms PCSActionFormat.token_byte_agreement
#print axioms PCSActionFormat.fixed_token_bound
