import PCSForgeRefinement.RustExtraction

/-! The canonical-value precondition of optimization soundness is necessary.
The public Rust enum permits an unmasked u8 payload 256 even though `Value::bitvec`
would mask it to zero. This is a boundary regression, not a counterexample to the
existing theorem, whose `Value.WF` hypothesis explicitly excludes this input.
The extracted expression-level executions are source-bound; top-level `eval`
below remains the existing transcription and is independently tested natively. -/
namespace PCSRuntimeCanonicalInputs
open PCSForgeRefinement
open PCSForgeRefinement.Rust

def original : Program := ⟨"canonical_boundary", [⟨"x", .bv .u8⟩],
  .binop .or (.var "x") (.var "x"), .bv .u8⟩

def candidate : Program := { original with body := .var "x" }

def certificate : Cert := ⟨original, candidate, [⟨.orIdem, []⟩], SEMANTICS, LIBRARY⟩

def unmasked : Value := .bitvec .u8 256

theorem checked_certificate_and_types :
    checkCert certificate = true ∧ original.checkG true = .ok () ∧
      candidate.checkG true = .ok () := by decide +kernel

theorem matching_type_tag_is_insufficient : unmasked.ty = .bv .u8 ∧ ¬ unmasked.WF := by
  decide +kernel

theorem transcribed_top_level_disagrees :
    eval original [unmasked] = .ok (.bitvec .u8 0) ∧
      eval candidate [unmasked] = .ok unmasked := by decide +kernel

/-- These are executions of the source-extracted Rust expression evaluator. -/
theorem source_extracted_expression_disagrees :
    runFn certirFns 8 ["eval_expr"] [encStore [("x", unmasked)], encExpr original.body] =
      some (.val (encRes (.ok (.bitvec .u8 0)))) ∧
    runFn certirFns 8 ["eval_expr"] [encStore [("x", unmasked)], encExpr candidate.body] =
      some (.val (encRes (.ok unmasked))) := by
  constructor
  · rw [rust_certir_extraction_sound _ _ _ (by decide)]
    rfl
  · rw [rust_certir_extraction_sound _ _ _ (by decide)]
    rfl

/-- The original soundness theorem continues to cover every canonical input. -/
theorem canonical_input_preserves_rewrite (input : Value) (wf : input.WF) :
    eval candidate [input] = eval original [input] := by
  exact optimization_sequence_preserves_program checked_certificate_and_types.1 [input]
    (by simpa using wf)

end PCSRuntimeCanonicalInputs

#print axioms PCSRuntimeCanonicalInputs.checked_certificate_and_types
#print axioms PCSRuntimeCanonicalInputs.matching_type_tag_is_insufficient
#print axioms PCSRuntimeCanonicalInputs.transcribed_top_level_disagrees
#print axioms PCSRuntimeCanonicalInputs.source_extracted_expression_disagrees
#print axioms PCSRuntimeCanonicalInputs.canonical_input_preserves_rewrite
