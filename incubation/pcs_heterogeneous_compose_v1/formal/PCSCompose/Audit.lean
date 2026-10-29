import PCSCompose.Levels
import PCSCompose.Compose
import PCSCompose.Predictive
import PCSCompose.Controls

/-!
# Axiom audit targets for HECK

Every named theorem below is an audit target. The release gate prints axioms
for each and requires only `propext`, `Classical.choice`, `Quot.sound`, or fewer.
-/

namespace PCSCompose.Audit

/-- Audit surface: list of declaration names for external axiom inventory. -/
def auditTargets : List String :=
  [ "PCSCompose.Levels.Level.le_refl"
  , "PCSCompose.Levels.Level.le_trans"
  , "PCSCompose.Levels.Level.le_antisymm"
  , "PCSCompose.Levels.Level.meet_comm"
  , "PCSCompose.Levels.Level.meet_idempotent"
  , "PCSCompose.Levels.Level.meet_assoc"
  , "PCSCompose.Levels.Level.meet_le_left"
  , "PCSCompose.Levels.Level.meet_le_right"
  , "PCSCompose.Levels.empirical_meet_formal"
  , "PCSCompose.Levels.empirical_ne_formal"
  , "PCSCompose.Levels.computational_meet_empirical"
  , "PCSCompose.Levels.provenance_meet_formal"
  , "PCSCompose.Levels.meetList_singleton"
  , "PCSCompose.Levels.meetList_cons_le"
  , "PCSCompose.Levels.meet_of_atMostEmpirical_ne_formal"
  , "PCSCompose.Compose.leavesOk_member"
  , "PCSCompose.Compose.empty_rejects"
  , "PCSCompose.Compose.achieved_singleton_formal"
  , "PCSCompose.Compose.heterogeneous_level_law"
  , "PCSCompose.Compose.formal_required_empirical_achieved_rejects"
  , "PCSCompose.Compose.computational_atom_not_formal_accept"
  , "PCSCompose.Compose.unsupported_formal_rejects"
  , "PCSCompose.Compose.underleveled_empirical_rejects"
  , "PCSCompose.Compose.heterogeneous_pair_law"
  , "PCSCompose.Predictive.match_is_empirical"
  , "PCSCompose.Predictive.contradict_falsifies"
  , "PCSCompose.Predictive.unrelated_preserves"
  , "PCSCompose.Predictive.wrong_key_match_preserves"
  , "PCSCompose.Predictive.wrong_key_contradict_preserves"
  , "PCSCompose.Predictive.falsified_not_support"
  , "PCSCompose.Predictive.open_not_support"
  , "PCSCompose.Predictive.empirical_is_support"
  , "PCSCompose.Predictive.sticky_preserves_falsified"
  , "PCSCompose.Predictive.discharged_match_level_empirical"
  , "PCSCompose.Predictive.empirical_level_ne_formal"
  , "PCSCompose.Controls.good_formal_singleton"
  , "PCSCompose.Controls.good_empirical_singleton"
  , "PCSCompose.Controls.good_heterogeneous_empirical_req"
  , "PCSCompose.Controls.reject_heterogeneous_formal_req"
  , "PCSCompose.Controls.reject_unsupported"
  , "PCSCompose.Controls.reject_missing"
  , "PCSCompose.Controls.reject_empty"
  , "PCSCompose.Controls.reject_empirical_as_formal"
  , "PCSCompose.Controls.achieved_heterogeneous_is_empirical"
  , "PCSCompose.Controls.predictive_match_supports"
  , "PCSCompose.Controls.predictive_contradict_falsifies"
  , "PCSCompose.Controls.predictive_match_not_formal"
  , "PCSCompose.Controls.predictive_sticky_falsified"
  , "PCSCompose.Controls.level_meet_laws"
  ]

theorem audit_target_count : auditTargets.length = 49 := by rfl

end PCSCompose.Audit
