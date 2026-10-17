import Pointwise
import FamilyTail

/-! Post-hoc closure of the previously proved infinite counterexample family.
Reuse its retained proof byte-for-byte. For k > 31 this is a statement about
mathematical neurons, not a claim that the bounded PGSI1 codec accepts them. -/
namespace PCS.Research.PointwiseFamilyBlock
open IntegerAffine Pointwise
open SupportedCounterexampleFamily

theorem no_positive_certificate (k : Int) (hk : 18 ≤ k) (rows : List Row) :
    ¬ (accept (PGSI1Bridge.embed (old k)) (PGSI1Bridge.embed (candidate k))
      PGSI1Bridge.targetNet rows = true) := by
  intro h
  have hn := accept_sound _ _ _ _ h (k+3)
  have hw := every_tail_input_worsens k (k+3) hk (by omega)
  simp only [error, PGSI1Bridge.embed_predict, PGSI1Bridge.target_predict] at hn
  omega

theorem no_guard_authorization (k : Int) (hk : 18 ≤ k) (rows : List Row) :
    ¬ (guard (old k) (candidate k) rows = true) := by
  intro h
  have hn := (guard_sound _ _ _ h).2 (k+3)
  have hw := every_tail_input_worsens k (k+3) hk (by omega)
  omega

#print axioms no_positive_certificate
#print axioms no_guard_authorization
end PCS.Research.PointwiseFamilyBlock
