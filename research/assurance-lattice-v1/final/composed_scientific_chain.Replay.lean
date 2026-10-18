import PCSAssuranceLattice
set_option autoImplicit false
set_option maxRecDepth 8192
set_option maxHeartbeats 2000000
-- Exact package SHA256: b93d2dbf07151067d8a408e522e8837348d7a056a1bfb8e6e320bbd0d0881580
namespace PCSAssuranceLatticeReplay
open PCSAssuranceLattice
def package : Package := ⟨[⟨0, PCSAssuranceLattice.Stratum.provenance, [100], []⟩, ⟨1, PCSAssuranceLattice.Stratum.computational, [101], [0]⟩, ⟨2, PCSAssuranceLattice.Stratum.formal, [102], [1]⟩], [⟨0, PCSAssuranceLattice.Stratum.provenance, true⟩, ⟨1, PCSAssuranceLattice.Stratum.computational, true⟩, ⟨2, PCSAssuranceLattice.Stratum.formal, true⟩], [], []⟩
theorem certificate_checked : check package = true := by decide
theorem certificate_certified : Certified package :=
  (check_iff_certified package).mp certificate_checked
#print axioms certificate_checked
#print axioms certificate_certified
end PCSAssuranceLatticeReplay
