import PCS.V2.ExecutableAuthority
import PCS.V2.ExternalWorld
import PCS.V2.DistributedContributors
import PCS.V2.ClaimGraphMemo
import PCS.V2.Witnesses.AISafetyCampaign
import PCS.V2.Witnesses.AISafetyDeployment

/-!
Audit surface for the executable AI-safety assurance layer: a successful build prints the
axiom dependencies of every major result added for the executable authority, the golden
AI-safety archive, distributed contributors, the external-world bridge and the memoized
graph checker.
-/

-- Priority 1: executable certified authority
#print axioms PCS.V2.DomainAuthority.executableAuthority_eq
#print axioms PCS.V2.DomainAuthority.executableAuthority_refines_certifiedAuthority
#print axioms PCS.V2.DomainAuthority.executableAuthorityEntries_refines_certifiedAuthority
#print axioms PCS.V2.DomainAuthority.executableAuthorityWith_dup
#print axioms PCS.V2.DomainAuthority.executableAuthorityWith_builtin
#print axioms PCS.V2.DomainAuthority.executableAuthorityWith_nil
#print axioms PCS.V2.DomainAuthority.buildRegistry_dup_none
#print axioms PCS.V2.DomainAuthority.buildRegistry_builtin_none
#print axioms PCS.V2.DomainAuthority.executor_builtin_unchanged
#print axioms PCS.V2.DomainAuthority.executor_unhandled_unchanged
#print axioms PCS.V2.DomainAuthority.executor_unknown_fail_closed
#print axioms PCS.V2.DomainAuthority.executableAuthority_sound
#print axioms PCS.V2.DomainAuthority.executableAuthority_domain_sound
-- Priority 2/3: golden AI-safety archive and adversarial campaign
#print axioms PCS.V2.Witnesses.AISafetyCampaign.golden_claim_decodes
#print axioms PCS.V2.Witnesses.AISafetyCampaign.golden_trace_safe
#print axioms PCS.V2.Witnesses.AISafetyCampaign.golden_checker_passes
#print axioms PCS.V2.Witnesses.AISafetyCampaign.golden_graph_accepted
#print axioms PCS.V2.Witnesses.AISafetyCampaign.aiSafetyGoldenArchive_domain_sound
#print axioms PCS.V2.Witnesses.AISafetyCampaigSECB1çÎ8r«