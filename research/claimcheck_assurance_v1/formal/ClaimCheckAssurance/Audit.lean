import ClaimCheckAssurance.SourceBinding
import ClaimCheckAssurance.Authority
import ClaimCheckAssurance.Selection
import ClaimCheckAssurance.Header
import ClaimCheckAssurance.Claims

/-!
# Axiom audit

Prints, for every main theorem, the axioms its proof depends on.  `build.sh` compares the output
with `AXIOMS.expected`: only `propext`, `Classical.choice` and `Quot.sound` may appear, and never
`sorryAx` or `Lean.ofReduceBool`.
-/

open PCS.ClaimCheck PCS.ClaimCheck.Assurance

#print axioms Source.bytes_eq
#print axioms Source.bytes_ofBytes
#print axioms Source.ofBytes_bytes
#print axioms Source.eq_of_bytes_eq
#print axioms run_ofBytes_some
#print axioms run_ofBytes_none
#print axioms run_not_wellFormed
#print axioms matchProved_sound
#print axioms mismatchProved_sound
#print axioms conditional_sound
#print axioms mathStatus_of_unaccepted
#print axioms outward_unknown
#print axioms verdict_unknown_of_unaccepted
#print axioms conditional_never_decided
#print axioms confirmation_sound
#print axioms discrepancy_corroborated
#print axioms discrepancy_sound
#print axioms verdict_ignores_notes
#print axioms core_mono
#print axioms verdict_mono
#print axioms decided_of_withdrawn
#print axioms no_conflict
#print axioms faithfulness_not_decidable_from_observables
#print axioms evidence_does_not_transfer
#print axioms confirmable_block_le
#print axioms confirmable_count_le
#print axioms confirmable_count_le_general
#print axioms implemented_rule_three_digits
#print axioms sliding_window_exceeds_nominal_rate
#print axioms strict_rule_within_two_percent
#print axioms blockConfirmable_count_le
#print axioms routes_block_le
#print axioms routes_count_le
#print axioms PRE_text
#print axioms SUF_text
#print axioms decStr_eq
#print axioms decVal_decStr
#print axioms decStr_decVal
#print axioms unhex_hexBytes
#print axioms hexBytes_unhex
#print axioms hexValue_hexOf
#print axioms decode_canon
#print axioms decode_sound
#print axioms canon_prefix_free
#print axioms accepted_header_denotes_data
#print axioms accepted_header_run
#print axioms texts_are_utf8
#print axioms bytesP_bytesR
#print axioms qP_qR
#print axioms condP_condR
#print axioms statP_statR
#print axioms claimP_claimR
#print axioms outP_outR
#print axioms defsP_defsR
#print axioms batchP_batchR
#print axioms readTail_renderTail
#print axioms parseTail_renderTail
#print axioms parseTail_sound
#print axioms parseTail_iff
#print axioms renderTail_injective
#print axioms parseTail_header
#print axioms parseTail_source
#print axioms QLit.val_inj
#print axioms ClaimA.den_inj
#print axioms OutcomeA.den_inj
#print axioms same_meaning_same_text
#print axioms batch_iff_claims
