import PCS.V2.ProofGatedNoForget

/-! Axiom audit for the all-integer no-forgetting checker (`ProofGatedNoForget`).
Expected: only `propext`, `Classical.choice`, `Quot.sound`; no `sorryAx`, no
`Lean.ofReduceBool`. -/

#print axioms PCS.V2.ProofGatedNoForget.affine_of_secondDiff
#print axioms PCS.V2.ProofGatedNoForget.relu_secondDiff_of_not_kink
#print axioms PCS.V2.ProofGatedNoForget.predict_secondDiff
#print axioms PCS.V2.ProofGatedNoForget.forget_on_piece
#print axioms PCS.V2.ProofGatedNoForget.exists_candidate_of_forgets
#print axioms PCS.V2.ProofGatedNoForget.findForgetting_sound
#print axioms PCS.V2.ProofGatedNoForget.noForgetting_sound
#print axioms PCS.V2.ProofGatedNoForget.noForgetting_iff
#print axioms PCS.V2.ProofGatedNoForget.findForgetting_complete
#print axioms PCS.V2.ProofGatedNoForget.acceptNF_sound
#print axioms PCS.V2.ProofGatedNoForget.nfTrace_preserves
#print axioms PCS.V2.ProofGatedNoForget.nfTrace_loss
#print axioms PCS.V2.ProofGatedNoForget.blindForget_corpus_accepted
#print axioms PCS.V2.ProofGatedNoForget.blindForget_caught
#print axioms PCS.V2.ProofGatedNoForget.blindForget_forgets_at_minus_12
#print axioms PCS.V2.ProofGatedNoForget.blindForget_rejected
#print axioms PCS.V2.ProofGatedNoForget.gen3_acceptNF
#print axioms PCS.V2.ProofGatedNoForget.growth_chain
#print axioms PCS.V2.ProofGatedNoForget.ood_not_forgetting
