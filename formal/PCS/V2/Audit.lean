import PCS.V2.TCB
import PCS.V2.Vectors
import PCS.V2.Archive
import PCS.V2.SHA256Padding
import PCS.V2.Chemistry
import PCS.V2.ChemistryVectors

/-!
Audit surface for the v0.6/v2 refinement layer: a successful build prints the axiom
dependencies of the flagship theorem and of the main intermediate theorems.
-/

-- canonical JSON / bytes
#print axioms PCS.V2.Json.parse_ser
#print axioms PCS.V2.Json.jcsBytes_injective
#print axioms PCS.V2.Canonical.parseCanonicalBytes_sound
#print axioms PCS.V2.Canonical.parseCanonicalBytes_unique
#print axioms PCS.V2.Canonical.parseCanonicalBytes_complete
-- domains / hash binding
#print axioms PCS.V2.Domains.hash_domain_separation
#print axioms PCS.V2.Domains.hash_sig_separation
#print axioms PCS.V2.Domains.digest_binding
#print axioms PCS.V2.Domains.cross_domain_digest_collision
-- normalized decision wire
#print axioms PCS.V2.NormalizedWire.verifyWireBytes_accepted
#print axioms PCS.V2.NormalizedWire.verifyWireBytes_assures
#print axioms PCS.V2.NormalizedWire.verifyWireBytes_computational_sound
#print axioms PCS.V2.NormalizedWire.verifyWireBytes_formal_sound
#print axioms PCS.V2.NormalizedWire.verifyWireBytes_empirical_sound
#print axioms PCS.V2.NormalizedWire.verifyWireBytes_mixed_sound
#print axioms PCS.V2.Binding.wire_hash_binding
#print axioms PCS.V2.Binding.predicate_commitment_binding
#print axioms PCS.V2.Binding.evidence_bound_to_claim_predicate
-- index / normalized set
#print axioms PCS.V2.Index.verifyNormalizedSet_sound
#print axioms PCS.V2.Index.verifyNormalizedSet_assures
-- signatures
#print axioms PCS.V2.Base64.decodeCanonical_unique
#print axioms PCS.V2.Signature.verifySigRecordBytes_sound
#print axioms PCS.V2.Signature.verifySigRecordBytes_nonmalleable
#print axioms PCS.V2.Signature.verifySigRecordBytes_domain_unique
#print axioms PCS.V2.Signature.verifySigRecordBytes_authentic
#print axioms PCS.V2.Signature.verifySigRecordBytes_intended
#print axioms PCS.V2.Ed25519.ed25519ImplCorrect_self
-- package
#print axioms PCS.V2.Package.namespace_no_traversal
#print axioms PCS.V2.Package.namespace_no_alias
#print axioms PCS.V2.Package.namespace_no_parent
#print axioms PCS.V2.Package.verifyPackage_sound
#print axioms PCS.V2.Package.fileMap_exact_names
#print axioms PCS.V2.Package.member_bytes_binding
#print axioms PCS.V2.Package.package_authentic
-- end to end
#print axioms PCS.V2.EndToEnd.acceptPCS_sound
#print axioms PCS.V2.Flagship.pcs_claims_assured
#print axioms PCS.V2.Flagship.pcs_authentic
#print axioms PCS.V2.Flagship.pcs_environment_bound
#print axioms PCS.V2.Flagship.pcs_evidence_holds
#print axioms PCS.V2.Flagship.pcs_accept_implies_scientific_assurance
#print axioms PCS.V2.Flagship.pcs_archive_accept_implies_scientific_assurance
#print axioms PCS.V2.Reproducibility.same_commitment_same_requests
#print axioms PCS.V2.Reproducibility.acceptance_reproducible
#print axioms PCS.V2.Reproducibility.wire_reuse_same_certificate
#print axioms PCS.V2.TCB.production_accept_implies_scientific_assurance
-- SHA-256 implementation structure
#print axioms PCS.V2.SHA256.be64_injective
#print axioms PCS.V2.SHA256.pad_injective
#print axioms PCS.V2.SHA256.chunks_pad_injective
#print axioms PCS.V2.SHA256.schedule_size
#print axioms PCS.V2.SHA256.pad_schedule_size
-- archive layer
#print axioms PCS.V2.Archive.fromArchiveEntries_sound
#print axioms PCS.V2.Archive.archive_no_duplicate_members
#print axioms PCS.V2.Archive.archive_members_signed
#print axioms PCS.V2.Archive.archive_manifest_members_present
#print axioms PCS.V2.Archive.archive_certificate_member
#print axioms PCS.V2.Archive.pcs_archive_scientific_assurance_exact
#print axioms PCS.V2.Archive.pcs_raw_archive_assurance
#print axioms PCS.V2.Archive.production_raw_archive_assurance
-- verified replay executor for `reaction_balance`
#print axioms PCS.V2.Chemistry.tokenize_sound
#print axioms PCS.V2.Chemistry.tokenize_complete
#print axioms PCS.V2.Chemistry.tokens_functional
#print axioms PCS.V2.Chemistry.balancedB_iff
#print axioms PCS.V2.Chemistry.chemExecWith_faithful
#print axioms PCS.V2.Chemistry.chemExec_faithful
#print axioms PCS.V2.Chemistry.pcs_reaction_evidence_balanced
