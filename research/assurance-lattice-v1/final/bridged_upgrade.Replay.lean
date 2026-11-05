import PCSAssuranceLattice
set_option autoImplicit false
set_option maxRecDepth 8192
set_option maxHeartbeats 2000000
-- Exact package SHA256: 835f455324151181242ec4c11f0f022b1a6f1a516cdb0ecf2abfdc976549f53d
namespace PCSAssuranceLatticeReplay
open PCSAssuranceLattice
def package : Package := ⟨[⟨0, PCSAssuranceLattice.Stratum.formal, [7], []⟩], [⟨0, PCSAssuranceLattice.Stratum.computational, true⟩], [⟨0, PCSAssuranceLattice.Stratum.computational, PCSAssuranceLattice.Stratum.formal, true⟩], []⟩
theorem certificate_checked : check package = true := by decide
theorem certificate_certified : Certified package :=
  (check_iff_certified package).mp certificate_checked
#print axioms certificate_checked
#print axioms certificate_certified
end PCSAssuranceLatticeReplay
