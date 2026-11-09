import AttestedProduct

/-!
Writ/16: fresh, independently receiver-signed readback evidence.

Historical delivery receipts alone do not establish current data retention.
A live verifier chooses a challenge nonce and pins the expected acknowledgment,
receiver and payload. The executable checker only accepts when the separate
cryptographic verifier has marked an exactly bound readback assertion valid.

These theorems do NOT prove receiver honesty, filesystem persistence after
the challenge, Ed25519, nonce randomness, or Python/SQLite-to-Lean refinement.
-/
namespace Writ16

structure RetainedBinding where
  policy : Nat
  receiver : Nat
  effect : Nat
  route : Nat
  payload : Nat
  size : Nat
  lease : Nat
  acknowledgment : Nat
  deriving DecidableEq, Repr

structure Readback where
  binding : RetainedBinding
  challenge : Nat
  bytesPresent : Bool
  signatureVerified : Bool
  deriving DecidableEq, Repr

/-- Trusted cryptographic verification and exact policy/byte/nonce binding. -/
def Verified (expected : RetainedBinding) (freshNonce : Nat)
    (response : Readback) : Prop :=
  response.binding = expected ∧
  response.challenge = freshNonce ∧
  response.bytesPresent = true ∧
  response.signatureVerified = true

def CheckFresh (expected : RetainedBinding) (freshNonce : Nat)
    (response : Readback) : Bool :=
  decide (response.binding = expected) &&
  decide (response.challenge = freshNonce) &&
  response.bytesPresent && response.signatureVerified

theorem checkFresh_iff (expected : RetainedBinding) (freshNonce : Nat)
    (response : Readback) :
    CheckFresh expected freshNonce response = true ↔
    Verified expected freshNonce response := by
  simp [CheckFresh, Verified, Bool.and_eq_true]

theorem cannot_replay_different_nonce (expected : RetainedBinding)
    (original fresh : Nat) (response : Readback)
    (old : response.challenge = original) (different : original ≠ fresh) :
    CheckFresh expected fresh response = false := by
  by_cases h : CheckFresh expected fresh response = true
  · have valid := (checkFresh_iff expected fresh response).mp h
    have eq : original = fresh := by rw [← old]; exact valid.2.1
    exact False.elim (different eq)
  · cases b : CheckFresh expected fresh response <;> simp_all

theorem cannot_substitute_payload (expected : RetainedBinding)
    (nonce : Nat) (response : Readback)
    (different : response.binding.payload ≠ expected.payload) :
    CheckFresh expected nonce response = false := by
  by_cases h : CheckFresh expected nonce response = true
  · have valid := (checkFresh_iff expected nonce response).mp h
    exact False.elim (different (congrArg RetainedBinding.payload valid.1))
  · cases b : CheckFresh expected nonce response <;> simp_all

/-- An old receipt is compatible with two different live file states:
    historical signature validity alone cannot distinguish their retention. -/
structure World where
  historicalAck : Nat
  presentNow : Bool

def HistoricalObservation (w : World) : Nat := w.historicalAck

theorem historical_ack_cannot_distinguish_missing_file (ack : Nat) :
    HistoricalObservation ⟨ack, true⟩ =
      HistoricalObservation ⟨ack, false⟩ := by rfl

/-- The product checker accepts only if the *existing* source/provenance/
    weighted-authority/receiver-admission certificate passes AND an
    independently fresh receiver readback matches the verifier's challenge. -/
def CheckRetained {n m : Nat}
    (committed current : Nat)
    (parents : Fin n → List (Fin n)) (label : Fin n → Nat)
    (budget : Fin m → Nat) (charges : List (Fin m → Nat))
    (expectedDelivery : Writ15.Binding)
    (deliveryTrace : List Writ15.Event) (ack : Writ15.Attestation)
    (expectedReadback : RetainedBinding)
    (challenge : Nat) (response : Readback) : Option (Fin m → Nat) :=
  if CheckFresh expectedReadback challenge response then
    Writ15.CheckAttested committed current parents label budget charges
      expectedDelivery deliveryTrace ack
  else none

theorem retained_sound {n m : Nat}
    {committed current : Nat}
    {parents : Fin n → List (Fin n)} {label : Fin n → Nat}
    {budget final : Fin m → Nat} {charges : List (Fin m → Nat)}
    {expectedDelivery : Writ15.Binding} {deliveryTrace : List Writ15.Event}
    {ack : Writ15.Attestation}
    {expectedReadback : RetainedBinding} {challenge : Nat}
    {response : Readback}
    (accepted : CheckRetained committed current parents label budget charges
      expectedDelivery deliveryTrace ack
      expectedReadback challenge response = some final) :
    committed = current ∧ Writ12.FlowSound parents label ∧
    Writ9.WeightedRuns budget charges final ∧
    Writ15.Valid expectedDelivery ack ∧
    Verified expectedReadback challenge response := by
  have h : CheckFresh expectedReadback challenge response = true ∧
    Writ15.CheckAttested committed current parents label budget charges
       expectedDelivery deliveryTrace ack = some final := by
    simpa [CheckRetained] using accepted
  have hs := Writ15.attested_sound h.2
  exact ⟨hs.1,hs.2.1,hs.2.2.1,hs.2.2.2,
         (checkFresh_iff expectedReadback challenge response).mp h.1⟩

theorem retained_complete {n m : Nat}
    {committed current : Nat}
    {parents : Fin n → List (Fin n)} {label : Fin n → Nat}
    {budget final : Fin m → Nat} {charges : List (Fin m → Nat)}
    {expectedDelivery : Writ15.Binding} {deliveryTrace : List Writ15.Event}
    {ack : Writ15.Attestation}
    {expectedReadback : RetainedBinding} {challenge : Nat}
    {response : Readback}
    (admitted : Writ15.CheckAttested committed current parents label
      budget charges expectedDelivery deliveryTrace ack = some final)
    (live : Verified expectedReadback challenge response) :
    CheckRetained committed current parents label budget charges
      expectedDelivery deliveryTrace ack
      expectedReadback challenge response = some final := by
  have checked := (checkFresh_iff expectedReadback challenge response).mpr live
  simpa [CheckRetained,checked] using admitted

theorem retained_no_overspend {n m : Nat}
    {committed current : Nat}
    {parents : Fin n → List (Fin n)} {label : Fin n → Nat}
    {budget final : Fin m → Nat} {charges : List (Fin m → Nat)}
    {expectedDelivery : Writ15.Binding} {deliveryTrace : List Writ15.Event}
    {ack : Writ15.Attestation}
    {expectedReadback : RetainedBinding} {challenge : Nat}
    {response : Readback}
    (accepted : CheckRetained committed current parents label budget charges
      expectedDelivery deliveryTrace ack
      expectedReadback challenge response = some final)
    (i : Fin m) : Writ9.WeightedUsed i charges ≤ budget i := by
  have h := (retained_sound accepted).2.2.1
  have exact := Writ9.weighted_quota_conservation h i
  omega

end Writ16
