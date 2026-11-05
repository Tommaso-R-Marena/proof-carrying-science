import PCS.V2.Golden.ArchiveBytes

/-!
# Axiom audit of the kernel-checked golden-fixture acceptance

Printed on every build.  Expected: only `propext`, `Classical.choice`, `Quot.sound`
(no `Lean.ofReduceBool`, i.e. no `native_decide`; no project axioms).
-/

#print axioms PCS.V2.Golden.certSig_verifies
#print axioms PCS.V2.Golden.pkgSig_verifies
#print axioms PCS.V2.Golden.verifyPackage_golden
#print axioms PCS.V2.Golden.acceptPCSWithCheckers_golden
#print axioms PCS.V2.Golden.decodeZip_golden
#print axioms PCS.V2.Golden.certifiedAuthority_golden
#print axioms PCS.V2.Golden.aiSafetyGoldenArchive_accepts
#print axioms PCS.V2.Golden.aiSafetyGoldenArchive_entries_accepts
#print axioms PCS.V2.Golden.aiSafetyGoldenArchive_committed_safe
#print axioms PCS.V2.Golden.aiSafetyGoldenArchive_deployed_safe
#print axioms PCS.V2.Golden.archiveBytes_eq_goldenRaw
#print axioms PCS.V2.Golden.decodeAuthorityTranscriptBytes_golden
#print axioms PCS.V2.Golden.cliAnchor_golden
#print axioms PCS.V2.Golden.pcsLeanAuthority_golden_zip_output
#print axioms PCS.V2.Golden.pcsLeanAuthority_golden_dir_output
