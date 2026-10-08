import PCS.V2.ExecutableGeneral
import PCS.V2.ExecutableLimits
import PCS.V2.Golden.Rejection
import PCS.V2.Golden.Insider
import PCS.V2.GoldenCx.Counterexample

/-!
# Axiom audit of the general executable bridge, rejections and counterexample

Printed on every build.  Expected: only `propext`, `Classical.choice`, `Quot.sound`
(no `Lean.ofReduceBool`, i.e. no `native_decide`; no project axioms).
-/

-- general bridge (arbitrary archives, transcripts, trust anchors)
#print axioms PCS.V2.ExecutableGeneral.executableAuthority_registered_evidence_sound
#print axioms PCS.V2.ExecutableGeneral.executableAuthority_trace_evidence_sound
#print axioms PCS.V2.ExecutableGeneral.executableAuthorityEntries_trace_evidence_sound
#print axioms PCS.V2.ExecutableGeneral.zipModeOutput_trace_evidence_sound
#print axioms PCS.V2.ExecutableGeneral.executableAuthority_trace_claim_sound
#print axioms PCS.V2.ExecutableGeneral.executableAuthority_deployed_trace_safe
#print axioms PCS.V2.ExecutableGeneral.executableAuthority_rejects_unsafe_trace_evidence
#print axioms PCS.V2.ExecutableGeneral.executableAuthorityEntries_rejects_unsafe_trace_evidence
-- concrete kernel-checked rejections
#print axioms PCS.V2.Golden.tamperedRaw_rejected
#print axioms PCS.V2.Golden.tamperedEntries_rejected
#print axioms PCS.V2.Golden.golden_vs_tampered
#print axioms PCS.V2.Golden.Insider.insider_rejected_entries
#print axioms PCS.V2.Golden.Insider.insider_rejdÑPÐ€L@öëŽ…ªì