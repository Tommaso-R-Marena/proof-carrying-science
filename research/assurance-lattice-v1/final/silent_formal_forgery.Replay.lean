import PCSAssuranceLattice
set_option autoImplicit false
set_option maxRecDepth 8192
set_option maxHeartbeats 2000000
-- Exact package SHA256: 08b7be91a4e0e84cd53394c5d1014d6e07c4a2a77515eab4bf609765842dcbb2
namespace PCSAssuranceLatticeReplay
open PCSAssuranceLattice
def package : Package := ⟨[⟨0, PCSAssuranceLattice.Stratum.formal, [1], []⟩], [⟨0, PCSAssuranceLattice.Stratum.computational, true⟩], [], []⟩
theorem certificate_checked : check package = true := by decide
theorem certificate_certified : Certified package :=
  (check_iff_certified package).mp certificate_checked
#print axioms certificate_checked
#print axioms certificate_certified
end PCSAssuranceLatticeReplay
