import PCSScientificReceiver.Codec
import PCSScientificReceiver.Semantics

namespace PCSScientificReceiver

/-- The pure authority consumes bytes, never submitted code or proof flags. -/
def receive (raw : List UInt8) : Option Result := do
  let c ← decode raw
  if checkContract c then some (resultOfContract c) else none

/-- Exact byte identity and the restricted mathematical conclusion. This does
not assert empirical adequacy, host integrity, or general chemical kinetics. -/
def ScopedScientificClaimHolds (raw : List UInt8) (r : Result) : Prop :=
  ∃ c, decode raw = some c ∧ encodeBytes c = raw ∧ ResultSound c r

/-- Every accepted byte sequence has a canonical decoded contract whose checked
state semantics imply the returned conservation and enclosure claims. -/
theorem verifiedWireSound (raw : List UInt8) (r : Result)
    (accepted : receive raw = some r) : ScopedScientificClaimHolds raw r := by
  unfold receive at accepted
  cases hd : decode raw with
  | none => simp [hd] at accepted
  | some c =>
    simp only [hd, bind, Option.bind] at accepted
    split at accepted
    next hc =>
      have hr : resultOfContract c = r := Option.some.inj accepted
      subst r
      exact ⟨c, hd, decode_canonical hd, resultOfContract_sound c hc⟩
    next => simp at accepted

theorem malformed_rejects (raw : List UInt8) (h : decode raw = none) :
    receive raw = none := by simp [receive, h]

theorem canonical_accepts (c : Contract) (supported : OperationallySupported c)
    (accepted : checkContract c = true) :
    receive (encodeBytes c) = some (resultOfContract c) := by
  simp [receive, decode_encodeBytes c supported, accepted]

#print axioms verifiedWireSound
#print axioms canonical_accepts

end PCSScientificReceiver
