import PCSForgeRefinement.RustExtraction

/-! Additional source extraction for the real CertiForge `Value::ty` helper.
The source snapshot is independently compared with a receiver-selected native checkout.
This covers the helper only: the top-level `eval` loop is not extracted here. -/
namespace PCSForgeRefinement.Rust

def valueTyFn : RFn where
  isPub := true
  path := ["Value", "ty"]
  params := [("self", [])]
  ret := ["Ty"]
  body := blk (.mtch (v "self") (arms [
    (.tupleS ["Value", "Bool"] (ps [.wild]), none, .path ["Ty", "Bool"], true),
    (.structS ["Value", "BitVec"] (fps [("width", .bind "width")]) true false,
      none, cl ["Ty", "BitVec"] [v "width"], true)]))

def encTy : Ty → RV
  | .bool => .ctor "Ty" "Bool" []
  | .bv w => .ctor "Ty" "BitVec" [encWidth w]

/-- Read the committed snapshot again during this module's fresh elaboration;
a previously cached `interpLib` literal cannot stand in for today's source bytes. -/
def valueTySource : List String :=
  source_lines% "../source_reference/certiforge/crates/certir-interpreter/src/lib.rs.txt"

/-- Exact Rust tokens in production helper lines 21–26. -/
theorem value_ty_source_bound :
    lexLines (window valueTySource 21 26) = valueTyFn.toks := by decide +kernel

theorem value_ty_precedence_checked : valueTyFn.wf = true := by decide +kernel

/-- All values, including unmasked payloads: source-extracted execution returns
exactly the reference type for every positive call-depth fuel. -/
theorem rust_value_ty (val : Value) (fuel : Nat) :
    runFn [valueTyFn] (fuel + 1) ["Value", "ty"] [encVal val] =
      some (.val (encTy val.ty)) := by
  cases val with
  | bool b => rfl
  | bitvec w bits => cases fuel <;> cases w <;> rfl

/-- Resource exhaustion remains a non-value outcome. -/
theorem rust_value_ty_zero_fuel (val : Value) :
    runFn [valueTyFn] 0 ["Value", "ty"] [encVal val] = some (.stuck "fuel") := rfl

end PCSForgeRefinement.Rust

#print axioms PCSForgeRefinement.Rust.value_ty_source_bound
#print axioms PCSForgeRefinement.Rust.value_ty_precedence_checked
#print axioms PCSForgeRefinement.Rust.rust_value_ty
#print axioms PCSForgeRefinement.Rust.rust_value_ty_zero_fuel
