import PCSScientificHistoryV1

namespace ScientificHistoryIndependentReview
open PCSAuthorizationHistoryV1
open PCSScientificHistoryV1

-- Negative bytes cannot enter through the empty auxiliary-certificate route.
theorem empty_candidate_rejected (root : Root) (verify : VerifySignature)
    (s : State) (e : Envelope) (empty : e.payload.candidate = []) :
    scientificTransition root verify s e = (s, none) := by
  apply PCSScientificHistoryV1.malformed_rejects
  rw [empty]
  decide +kernel

theorem empty_not_checked : ¬ Checked [] := by
  rintro ⟨r, hr⟩
  have hn : PCSScientificReceiver.receive [] = none :=
    PCSScientificReceiver.malformed_rejects [] (by decide +kernel)
  rw [hn] at hr
  cases hr

-- Deliberately bad pre-existing history. A new good request does not erase it.
def badOld : Envelope :=
  { sampleEnvelope with payload := { sampleEnvelope.payload with eventId := [99], candidate := [] } }

def tainted : State := { initial sampleRoot with history := [badOld] }

theorem tainted_old_history_not_scientific : ¬ ScientificHistory tainted := by
  intro hs
  have bad := hs badOld (by simp [tainted])
  exact empty_not_checked bad.2

theorem good_new_event_accepts_without_old_science :
    scientificTransition sampleRoot sampleVerify tainted sampleEnvelope =
      (commit tainted sampleEnvelope, some (PCSScientificReceiver.resultOfContract PCSScientificReceiver.codecSample)) := by
  have hp : sampleRoot.policy = policyBytes := rfl
  have hc : sampleEnvelope.payload.certificate = [] := rfl
  have hh : (transition sampleRoot sampleVerify tainted sampleEnvelope).2 = true := by
    decide +kernel
  simp [scientificTransition, hp, hc, sample_science_accepts,
    accepted_state sampleRoot sampleVerify tainted sampleEnvelope hh]

theorem accepting_new_science_does_not_upgrade_old_history :
    ¬ ScientificHistory (scientificTransition sampleRoot sampleVerify tainted sampleEnvelope).1 := by
  rw [good_new_event_accepts_without_old_science]
  intro hs
  have bad := hs badOld (by simp [commit, tainted])
  exact empty_not_checked bad.2

def invalidGenesis : Root := { sampleRoot with genesisIncumbent := [] }

theorem empty_trace_does_not_repair_genesis :
    ¬ Checked (PCSScientificHistoryV1.run invalidGenesis sampleVerify (initial invalidGenesis) []).incumbent := by
  change ¬ Checked []
  exact empty_not_checked

-- Existing pure-root abstraction does not assert a 32-byte checker/key type.
-- This is a scope control, not a cryptographic authority or a runtime fixture.
def emptyScopesRoot : Root :=
  { sampleRoot with authority := [], witness := [], checker := [] }

def emptyScopesEnvelope : Envelope :=
  { sampleEnvelope with payload := { sampleEnvelope.payload with authority := [], witness := [], checker := [] } }

def permissiveSymbolicVerifier : VerifySignature := fun _ _ _ => true

theorem pure_root_can_have_empty_opaque_scopes :
    (scientificTransition emptyScopesRoot permissiveSymbolicVerifier
      (initial emptyScopesRoot) emptyScopesEnvelope).2 =
        some (PCSScientificReceiver.resultOfContract PCSScientificReceiver.codecSample) := by
  have hs : PCSScientificReceiver.receive emptyScopesEnvelope.payload.candidate =
      some (PCSScientificReceiver.resultOfContract PCSScientificReceiver.codecSample) := sample_science_accepts
  have hh : (transition emptyScopesRoot permissiveSymbolicVerifier
      (initial emptyScopesRoot) emptyScopesEnvelope).2 = true := by decide +kernel
  have hp : emptyScopesRoot.policy = policyBytes := rfl
  have hc : emptyScopesEnvelope.payload.certificate = [] := rfl
  simp [scientificTransition, hp, hc, hs, hh]

#print axioms empty_candidate_rejected
#print axioms accepting_new_science_does_not_upgrade_old_history
#print axioms empty_trace_does_not_repair_genesis
#print axioms pure_root_can_have_empty_opaque_scopes
end ScientificHistoryIndependentReview
