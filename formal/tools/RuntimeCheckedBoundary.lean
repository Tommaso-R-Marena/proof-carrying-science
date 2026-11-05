import PCSForgeRefinement.RustExtraction

/-! An isolated extension of the existing Rust fragment with a `values()` iterator,
an `if let` pattern, and early return. The body uses the existing expression
semantics. The iterator is represented by a finite snapshot, in arbitrary order;
no native compiler or HashMap implementation theorem is claimed. -/
namespace PCSRuntimeCheckedBoundary
open PCSForgeRefinement PCSForgeRefinement.Rust
set_option maxRecDepth 4096

structure CheckedIteratorFn where
  signature : List String
  receiver : RExpr
  binder : String
  pattern : RPat
  condition : RExpr
  rejection : RExpr
  rejectionTrailingComma : Bool
  tail : RExpr

def CheckedIteratorFn.toks (fn : CheckedIteratorFn) : List String :=
  fn.signature ++ ["{", "for", fn.binder, "in"] ++ fn.receiver.toks ++
  ["{", "if", "let"] ++ fn.pattern.toks ++ ["=", fn.binder, "{", "if"] ++
  fn.condition.toks ++ ["{", "return"] ++
  (if fn.rejectionTrailingComma then
    fn.rejection.toks.take (fn.rejection.toks.length - 2) ++ [","] ++
      fn.rejection.toks.drop (fn.rejection.toks.length - 2)
   else fn.rejection.toks) ++
  [";", "}", "}", "}"] ++ fn.tail.toks ++ ["}"]

def checkedFn : CheckedIteratorFn := {
  signature := ["pub", "fn", "eval_expr_checked", "(", "store", ":", "&", "HashMap",
    "<", "String", ",", "Value", ">", ",", "expr", ":", "&", "Expr", ")", "->",
    "Result", "<", "Value", ",", "EvalError", ">"]
  receiver := .mcall (v "store") "values" .nil
  binder := "value"
  pattern := .structS ["Value", "BitVec"] (fps [("width", .bind "width"), ("bits", .bind "bits")]) false false
  condition := .bin "!=" (.deref (v "bits"))
    (.paren (.bin "&" (.deref (v "bits")) (.mcall (v "width") "mask" .nil)))
  rejection := .call ["Err"] (es [ .call ["EvalError", "Runtime"]
    (es [.mcall (.str "noncanonical bitvector input; use Value::bitvec") "into" .nil]) ])
  rejectionTrailingComma := true
  tail := cl ["eval_expr"] [v "store", v "expr"] }

def currentWrapperSource : List String :=
  source_lines% "../source_reference/certiforge/checked-wrapper-v2.rs.txt"

theorem checked_wrapper_source_bound : lexLines currentWrapperSource = checkedFn.toks := by
  decide +kernel

theorem checked_expression_precedence :
    checkedFn.condition.wf = true ∧ checkedFn.rejection.wf = true ∧ checkedFn.tail.wf = true := by
  decide +kernel

/-- One iterator iteration. Failure to match `if let` skips its body. -/
def iteration (fn : CheckedIteratorFn) (callFuel : Nat) (value : RV) : Option Out :=
  match matchPat fn.pattern value with
  | none => none
  | some env =>
    match evalE (runFn certirFns callFuel) env fn.condition .val with
    | .val (.bool false) => none
    | .val (.bool true) => some (evalE (runFn certirFns callFuel) env fn.rejection .val)
    | other => some other

def rejection : Out := .val (encRes (.error (.runtime
  "noncanonical bitvector input; use Value::bitvec")))

def canonicalB : Value → Bool
  | .bool _ => true
  | .bitvec w bits => bits == (bits &&& w.mask)

theorem canonicalB_iff (value : Value) : canonicalB value = true ↔ value.WF := by
  cases value with
  | bool b => simp [canonicalB, Value.WF]
  | bitvec w bits =>
    simp only [canonicalB, beq_iff_eq, Value.WF]
    rw [mask_eq_mod]
    constructor
    · intro h
      have bound := Nat.mod_lt bits (by cases w <;> decide : 0 < 2 ^ w.bits)
      omega
    · intro h
      exact (Nat.mod_eq_of_lt h).symm

theorem condition_eval (w : Width) (bits extra : Nat) :
    evalE (runFn certirFns (extra + 2))
      [("width", encWidth w), ("bits", .int bits)] checkedFn.condition .val =
      .val (.bool (!(bits == (bits &&& w.mask)))) := by
  cases w <;> rfl

theorem iteration_exact (value : Value) (extra : Nat) :
    iteration checkedFn (extra + 2) (encVal value) =
      if canonicalB value then none else some rejection := by
  cases value with
  | bool b => rfl
  | bitvec w bits =>
    change (match evalE (runFn certirFns (extra + 2))
      [("width", encWidth w), ("bits", .int bits)] checkedFn.condition .val with
      | .val (.bool false) => none
      | .val (.bool true) => some rejection
      | other => some other) = _
    rw [condition_eval]
    by_cases h : (bits == (bits &&& w.mask)) = true
    · simp [canonicalB, h]
    · have hf : (bits == (bits &&& w.mask)) = false := Bool.eq_false_iff.mpr h
      simp [canonicalB, hf]

/-- Early return is propagated; exhausting the iterator budget is never a value. -/
def loop (fn : CheckedIteratorFn) (callFuel : Nat) : Nat → List RV → Out → Out
  | _, [], tail => tail
  | 0, _ :: _, _ => .stuck "iterator fuel"
  | fuel + 1, value :: rest, tail =>
    match iteration fn callFuel value with
    | none => loop fn callFuel fuel rest tail
    | some out => out

theorem loop_exact (values : List Value) (extra fuel : Nat) (tail : Out)
    (enough : values.length ≤ fuel) :
    loop checkedFn (extra + 2) fuel (values.map encVal) tail =
      if values.all canonicalB then tail else rejection := by
  induction values generalizing fuel with
  | nil => simp [loop]
  | cons value rest ih =>
    cases fuel with
    | zero => simp at enough
    | succ fuel =>
      simp only [List.map_cons, loop, iteration_exact, List.all_cons]
      by_cases h : canonicalB value = true
      · simp only [h, ↓reduceIte, Bool.true_and]
        exact ih fuel (by simpa using enough)
      · have hf : canonicalB value = false := Bool.eq_false_iff.mpr h
        simp [hf]

def runChecked (σ : Store) (e : Expr) (callFuel iteratorFuel : Nat) : Out :=
  loop checkedFn callFuel iteratorFuel (σ.map fun entry => encVal entry.2)
    (evalE (runFn certirFns callFuel) [("store", encStore σ), ("expr", encExpr e)] checkedFn.tail .val)

def checkedReference (σ : Store) (e : Expr) : Except EvalError Value :=
  if (σ.map (·.2)).all canonicalB then evalExpr σ e
  else .error (.runtime "noncanonical bitvector input; use Value::bitvec")

/-- All expressions and error paths, all four widths: the bound wrapper runs the
existing source-extracted expression evaluator only after every value is canonical. -/
theorem checked_wrapper_refines (σ : Store) (e : Expr) (extra iteratorFuel : Nat)
    (callBudget : depth e + 4 ≤ extra + 2) (iteratorBudget : σ.length ≤ iteratorFuel) :
    runChecked σ e (extra + 2) iteratorFuel = .val (encRes (checkedReference σ e)) := by
  unfold runChecked
  have step := loop_exact (σ.map (·.2)) extra iteratorFuel
    (evalE (runFn certirFns (extra + 2)) [("store", encStore σ), ("expr", encExpr e)] checkedFn.tail .val)
    (by simpa using iteratorBudget)
  simp only [List.map_map, Function.comp_def] at step
  rw [step]
  unfold checkedReference
  split
  · change callK (runFn certirFns (extra + 2)) ["eval_expr"] [encStore σ, encExpr e] Out.val = _
    exact callK_val _ (rust_certir_extraction_sound σ e (extra + 2) callBudget)
  · rfl

theorem checked_reference_rejects_noncanonical (σ : Store) (e : Expr)
    (bad : ∃ value ∈ σ.map (·.2), ¬ value.WF) :
    checkedReference σ e = .error (.runtime "noncanonical bitvector input; use Value::bitvec") := by
  unfold checkedReference
  have h : (σ.map (·.2)).all canonicalB ≠ true := by
    intro accepted
    rcases bad with ⟨value, member, notWF⟩
    exact notWF ((canonicalB_iff value).mp ((List.all_eq_true.mp accepted) value member))
  simp [h]

theorem checked_reference_accepts_canonical (σ : Store) (e : Expr)
    (wf : ∀ value ∈ σ.map (·.2), value.WF) : checkedReference σ e = evalExpr σ e := by
  have h : (σ.map (·.2)).all canonicalB = true :=
    List.all_eq_true.mpr (fun value member => (canonicalB_iff value).mpr (wf value member))
  simp [checkedReference, h]

theorem guard_order_independent (a b : List Value) (sameValues : a.Perm b) :
    a.all canonicalB = b.all canonicalB := by
  exact sameValues.all_eq

theorem encoded_store_canonical (δ : DStore) :
    ∀ value ∈ (PCSForgeRefinement.encStore δ).map (·.2), value.WF := by
  intro value member
  simp only [PCSForgeRefinement.encStore, List.map_map, Function.comp_def] at member
  rcases List.mem_map.mp member with ⟨⟨name, val⟩, _, rfl⟩
  cases val with
  | bool b => trivial
  | bv w bits => exact bits.isLt

/-- Acceptance is still determined by the existing certificate checker, not the
wrapper. The wrapper establishes the missing canonical-input boundary. -/
theorem checked_certificate_preserves {c : Cert} (accepted : checkCert c = true)
    (δ : DStore) (typed : WTStore c.original.env δ) (f1 f2 iteratorFuel : Nat)
    (candidateBudget : depth c.candidate.body + 4 ≤ f1 + 2)
    (originalBudget : depth c.original.body + 4 ≤ f2 + 2)
    (iteratorBudget : (PCSForgeRefinement.encStore δ).length ≤ iteratorFuel) :
    runChecked (PCSForgeRefinement.encStore δ) c.candidate.body (f1 + 2) iteratorFuel =
      runChecked (PCSForgeRefinement.encStore δ) c.original.body (f2 + 2) iteratorFuel := by
  rw [checked_wrapper_refines _ _ _ _ candidateBudget iteratorBudget,
      checked_wrapper_refines _ _ _ _ originalBudget iteratorBudget,
      checked_reference_accepts_canonical _ _ (encoded_store_canonical δ),
      checked_reference_accepts_canonical _ _ (encoded_store_canonical δ),
      certir_eval_correspondence, certir_eval_correspondence,
      (rewrite_certificate_universally_sound accepted).2 δ typed]

theorem iterator_exhaustion :
    loop checkedFn 8 0 [encVal (.bool true)] rejection = .stuck "iterator fuel" := rfl

theorem bad_payload_rejected_all_widths (w : Width) :
    checkedReference [("x", .bitvec w (2 ^ w.bits))] (.var "x") =
      .error (.runtime "noncanonical bitvector input; use Value::bitvec") := by
  apply checked_reference_rejects_noncanonical
  exact ⟨.bitvec w (2 ^ w.bits), by simp, by simp [Value.WF]⟩

theorem checked_error_controls :
    checkedReference [] (.var "missing") = .error (.undefinedVar "missing") ∧
    checkedReference [] (.unop .neg (.constBool true)) = .error (.runtime "bad unop") ∧
    checkedReference [] (.select (.constBv .u8 1) (.constBool true) (.constBool false)) =
      .error (.runtime "select cond not bool") ∧
    checkedReference [("unused", .bitvec .u8 256)] (.constBool true) =
      .error (.runtime "noncanonical bitvector input; use Value::bitvec") := by
  decide +kernel

theorem checked_native_u64_max_and_zero :
    checkedReference [("x", .bitvec .u64 (2 ^ 64 - 1))] (.var "x") =
      .ok (.bitvec .u64 (2 ^ 64 - 1)) ∧
    checkedReference [("x", .bitvec .u64 0)] (.var "x") = .ok (.bitvec .u64 0) := by
  decide +kernel

theorem checked_call_exhaustion :
    runChecked [] (.constBool true) 0 0 = .stuck "fuel" := by rfl

end PCSRuntimeCheckedBoundary

#print axioms PCSRuntimeCheckedBoundary.checked_wrapper_source_bound
#print axioms PCSRuntimeCheckedBoundary.checked_expression_precedence
#print axioms PCSRuntimeCheckedBoundary.canonicalB_iff
#print axioms PCSRuntimeCheckedBoundary.iteration_exact
#print axioms PCSRuntimeCheckedBoundary.condition_eval
#print axioms PCSRuntimeCheckedBoundary.loop_exact
#print axioms PCSRuntimeCheckedBoundary.checked_wrapper_refines
#print axioms PCSRuntimeCheckedBoundary.checked_reference_rejects_noncanonical
#print axioms PCSRuntimeCheckedBoundary.checked_reference_accepts_canonical
#print axioms PCSRuntimeCheckedBoundary.guard_order_independent
#print axioms PCSRuntimeCheckedBoundary.encoded_store_canonical
#print axioms PCSRuntimeCheckedBoundary.checked_certificate_preserves
#print axioms PCSRuntimeCheckedBoundary.iterator_exhaustion
#print axioms PCSRuntimeCheckedBoundary.bad_payload_rejected_all_widths
#print axioms PCSRuntimeCheckedBoundary.checked_error_controls
#print axioms PCSRuntimeCheckedBoundary.checked_native_u64_max_and_zero
#print axioms PCSRuntimeCheckedBoundary.checked_call_exhaustion
