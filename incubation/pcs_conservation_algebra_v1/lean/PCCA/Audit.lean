import PCCA.Stoich
import PCCA.Elemental
import PCCA.Controls

/-!
# Axiom audit surface for PCCA

Every named result below is intended to be checked with `#print axioms`
against the approved closure `{propext, Classical.choice, Quot.sound}`
(or a subset). No project axioms, `sorry`, `admit`, or `native_decide`.
-/

namespace PCCA.Audit

open PCCA.Stoich PCCA.Elemental PCCA.Controls

#print axioms conserved_step
#print axioms conserved_all_times
#print axioms conserved_uniform
#print axioms fire_zero
#print axioms conservation_zero
#print axioms conservation_add
#print axioms conservation_smul
#print axioms check_sound
#print axioms rational_certificate_real
#print axioms trajectory_preserves_pool
#print axioms checkTrajectory_sound
#print axioms checkTrajectory_preserves
#print axioms elementBalanced_iff_conservation
#print axioms elemental_is_conservation
#print axioms elemental_pool_invariant
#print axioms checkElemental_sound
#print axioms joint_elemental
#print axioms good_carbon
#print axioms good_hydrogen
#print axioms good_oxygen
#print axioms carbon_conserves
#print axioms carbon_all_times
#print axioms carbon_rejects_leak
#print axioms exchange_conserves_amount
#print axioms exchange_all_times
#print axioms one_step_carbon
#print axioms one_step_carbon_value
#print axioms one_step_carbon_after
#print axioms joint_CH_conserves

end PCCA.Audit
