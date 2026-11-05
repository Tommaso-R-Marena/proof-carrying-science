import PCSScientificHistoryV1.Join

namespace PCSScientificHistoryV1

open PCSAuthorizationHistoryV1
open PCSScientificReceiver

/-- Finite symbolic signature allowlist only; science uses the actual receiver. -/
def sampleRoot : Root :=
  { fixtureRoot with
    policy := policyBytes
    checker := List.replicate 32 0
    genesisIncumbent := encodeBytes codecSample }

def sampleEnvelope : Envelope :=
  { fixtureEnvelope with
    payload := { fixturePayload with
      policy := policyBytes
      checker := sampleRoot.checker
      candidate := encodeBytes codecSample
      expectedIncumbent := sampleRoot.genesisIncumbent
      certificate := [] } }

def sampleVerify (key : Bytes) (payload : Payload) (signature : Bytes) : Bool :=
  decide (payload = sampleEnvelope.payload ∧
    ((key = [1] ∧ signature = [21]) ∨ (key = [2] ∧ signature = [22])))

theorem sample_science_accepts :
    receive sampleEnvelope.payload.candidate = some (resultOfContract codecSample) := by
  apply canonical_accepts codecSample codecSample_supported
  exact sample_accepts

theorem sample_commits_checked_science :
    scientificTransition sampleRoot sampleVerify (initial sampleRoot) sampleEnvelope =
      (commit (initial sampleRoot) sampleEnvelope, some (resultOfContract codecSample)) := by
  have hp : sampleRoot.policy = policyBytes := rfl
  have hc : sampleEnvelope.payload.certificate = [] := rfl
  have hh : (transition sampleRoot sampleVerify (initial sampleRoot) sampleEnvelope).2 = true := by
    decide +kernel
  simp [scientificTransition, hp, hc, sample_science_accepts,
    accepted_state sampleRoot sampleVerify (initial sampleRoot) sampleEnvelope hh]

theorem sample_false_science_unchanged :
    scientificTransition sampleRoot sampleVerify (initial sampleRoot)
      { sampleEnvelope with payload := { sampleEnvelope.payload with candidate := [] } } =
      (initial sampleRoot, none) := by
  apply malformed_rejects
  decide +kernel

theorem sample_auxiliary_rejected :
    scientificTransition sampleRoot sampleVerify (initial sampleRoot)
      { sampleEnvelope with payload := { sampleEnvelope.payload with certificate := [1] } } =
      (initial sampleRoot, none) := by
  apply auxiliary_certificate_rejects
  decide +kernel

theorem sample_missing_witness_rejected :
    scientificTransition sampleRoot sampleVerify (initial sampleRoot)
      { sampleEnvelope with witnessSignature := [] } = (initial sampleRoot, none) := by
  apply signature_failure_rejects
  right
  decide +kernel

/-- A canonical, resource-bounded bundle can make a false conservation
statement. Its actual scientific receiving check rejects before history CAS. -/
theorem sample_false_total_unchanged :
    let bad := { codecSample with declaredTotal := 2 }
    scientificTransition sampleRoot sampleVerify (initial sampleRoot)
      { sampleEnvelope with payload := { sampleEnvelope.payload with candidate := encodeBytes bad } } =
      (initial sampleRoot, none) := by
  dsimp only
  apply false_science_rejects
  let bad := { codecSample with declaredTotal := 2 }
  have supported : OperationallySupported bad := by constructor <;> decide +kernel
  have decoded := decode_encodeBytes bad supported
  have rejected : checkContract bad = false := sample_false_total_rejects
  change receive (encodeBytes bad) = none
  simp [receive, decoded, rejected]

end PCSScientificHistoryV1
