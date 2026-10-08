import PCS.V2.ExecutableFailClosed
import PCS.V2.Golden.FailClosedFixtures
import PCS.V2.GoldenCx.Counterexample
import PCS.V2.Golden.Acceptance

/-!
# Axiom audit of the fail-closed gates

Printed on every build.  Expected: only `propext`, `Classical.choice`, `Quot.sound`
(no `Lean.ofReduceBool`, i.e. no `native_decide`; no project axioms).
-/

-- generic gates
#print axioms PCS.V2.FailClosed.acceptPCSStrictWith_fallback_irrelevant
#print axioms PCS.V2.FailClosed.acceptArchiveStrictWith_fallback_irrelevant
#print axioms PCS.V2.FailClosed.diagnosePCSStrictWith_accept_iff
#print axioms PCS.V2.FailClosed.diagnoseArchiveStrictWith_accept_iff
#print axioms PCS.V2.FailClosed.strict_evidence_certified
#print axioms PCS.V2.FailClosed.strict_supported_claim_sound
#print axioms PCS.V2.FailClosed.strict_rejects_unregistered_type
-- the executed decision functions
#print axioms PCS.V2.DomainAuthority.executableAuthority_refines_certifiedAuthority
#print axioms PCS.V2.DomainAuthority.executableAuthorityEntries_refines_certifiedAuthority
#print axioms PCS.V2.DomainAuthority.executableAuthorityWith_nil
#print axioms PCS.V2.ExecutableFailClosed.executableAuthority_rejects_unregistered_type
#print axioms PCS.V2.ExecutableFailClosed.executableAuthorityEntries_rejects_unregistered_type
#print axioms PCS.V2.ExecutableFailClosed.zipModeOutput_rejects_unregistered_type
#print axioms PCS.V2.ExecutableFailClosed.dirModeOutput_rejects_unregistered_type
#print axioms PCS.V2.ExecutableFailClosed.executableAuthority_evidence_certified
#print axioms PCS.V2.ExecutableFailClosed.executableAuthority_supported_claims_sound
#print axioms PCS.V2.ExecutableFailClosed.executableAuthority_rejects_false_supported_ai_claim
#print axioms PCS.V2.ExecutableFailClosed.executableAuthorityEntries_rejects_false_supported_ai_claim
-- golden acceptance (re-proved for the strict authority)
#print axioms PCS.V2.Golden.supportedEvidence_golden
#print axioms PCS.V2.Golden.claimsBound_golden
#print axioms PCS.V2.Golden.certifdÑPÐ€L@÷ón…ªì