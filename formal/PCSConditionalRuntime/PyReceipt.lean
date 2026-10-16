import PCSConditionalRuntime.PyTail

/-!
# The returned dictionary is the reference receipt

`receipt_fields_eq`: starting from the initial result dictionary of `check`, the fields written
by the `try` statement, `result['work']` and `result['receipt_sha256']` are exactly the fields
(in insertion order) of `receiptT` for the reference receipt `PCSDD.check t lim`.  The proof is
a case analysis on the reference pipeline (resource limit / inconsistent / equivalent /
counterexample).
-/

namespace PCSCR.Py

open PCSCR PCSDD PCSOmega

/-- The fields of the result dictionary right after its construction. -/
def initKT (tj : T) (d : String) (lim : Limits) : List (String × T) :=
  [("format", .str "pcs-conditional-boolean-receipt-v1"), ("checker", .str "pcs-conditional-bdd/1"),
   ("original_task", tj), ("task_sha256", .str d), ("limits", limT lim), ("decision", .null),
   ("context_example", .null), ("counterexample", .null), ("unsat_core", .null),
   ("core_necessity_witnesses", .null), ("diagram", .null), ("limit_reached", .null),
   ("scope", .str "Declared Boolean interpretations and explicit assumptions only"),
   ("pcs_authority", .bool false), ("lean_kernel_checked", .bool false)]

theorem work_fields_eq (names : List String) (t : CTask names.length) (lim : Limits) (tj : T) (d : String) :
    tset (finKT names t lim (initKT tj d lim)) "work" (workT (finMgr t lim).work) =
      receiptFields names tj d (check t lim) := by
  unfold finKT finMgr check
  cases hp : pipeline t lim with
  | error q =>
    obtain ⟨e, m⟩ := q
    simp [limKT, initKT, tset, receiptFields, decisionT, optT]
  | ok q =>
    obtain ⟨b, m⟩ := q
    cases b with
    | inconsistent prs core ws =>
      simp [bodyT, incT, initKT, tset, receiptFields, decisionT, optT]
    | decided ctx s c dd =>
      by_cases hd : dd = 0
      · subst hd
        simp [bodyT, repT, initKT, tset, receiptFields, decisionT, optT, world]
      · simp [bodyT, repT, initKT, tset, receiptFields, decisionT, optT, hd, cexOf]

theorem tset_receipt (names : List String) (tj : T) (d : String) (r : CReceipt names.length) (x : T) :
    tset (receiptFields names tj d r) "receipt_sha256" x = receiptFields names tj d r ++ [("receipt_sha256", x)] := by
  simp [receiptFields, tset]

theorem receipt_fields_eq (names : List String) (t : CTask names.length) (lim : Limits) (tj : T)
    (dg : T → String) :
    T.obj (tailKT dg (finKT names t lim (initKT tj (dg tj) lim)) (finMgr t lim)) =
      receiptT names tj dg (check t lim) := by
  simp only [tailKT, work_fields_eq, tset_receipt, receiptT]

end PCSCR.Py
