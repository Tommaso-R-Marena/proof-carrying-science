import PCSForgeRefinement.Episode

/-!
# Executed CertIR controls (ordinary kernel evaluation)
-/

namespace PCSForgeRefinement.Controls

open PCSForgeRefinement

def xy (w : Width) : List Param := [⟨"x", .bv w⟩, ⟨"y", .bv w⟩]
def X : Expr := .var "x"
def Y : Expr := .var "y"

/-- `add(and(x, y), xor(x, y))` (the Rust `and_xor_eq_or` test). -/
def andXor (w : Width) : Program := ⟨"p", xy w, .binop .add (.binop .and X Y) (.binop .xor X Y), .bv w⟩
def orXY (w : Width) : Program := ⟨"p_opt", xy w, .binop .or X Y, .bv w⟩

def certAndXor (w : Width) : Cert := ⟨andXor w, orXY w, [⟨.andXorAddToOr, []⟩], SEMANTICS, LIBRARY⟩

example : checkCertImproving (certAndXor .u8) = true := by decide
example : checkCertImproving (certAndXor .u16) = true := by decide
example : checkCertImproving (certAndXor .u32) = true := by decide
example : checkCertImproving (certAndXor .u64) = true := by decide

/-- Universal `u64` equivalence of the actual interpreter, for every canonical input. -/
theorem andXor_u64_universal (inputs : List Value) (hw : ∀ v ∈ inputs, v.WF) :
    eval (orXY .u64) inputs = eval (andXor .u64) inputs :=
  optimization_sequence_preserves_program (c := certAndXor .u64) (by decide) inputs hw

/-- `x + x ⇒ x << 1` under a `select` context, then commuted addition elsewhere. -/
def ctxProg : Program :=
  ⟨"c", [⟨"x", .bv .u16⟩, ⟨"y", .bv .u16⟩, ⟨"b", .bool⟩],
    .select (.var "b") (.binop .add X X) (.binop .add X Y), .bv .u16⟩
def ctxCand : Program :=
  ⟨"c_opt", ctxProg.params, .select (.var "b") (.binop .shl X (.constBv .u16 1)) (.binop .add Y X), .bv .u16⟩
def ctxCert : Cert := ⟨ctxProg, ctxCand, [⟨.addSelfShl1, [.thn]⟩, ⟨.addComm, [.els]⟩], SEMANTICS, LIBRARY⟩

example : checkCert ctxCert = true := by decide
example : checkCertImproving ctxCert = true := by decide

/-! ### Oversized shifts (the Rust test `large_u64_shift_does_not_truncate_to_u32`) -/

def shlBig : Program := ⟨"p", [⟨"x", .bv .u64⟩], .binop .shl X (.constBv .u64 4294967296), .bv .u64⟩
def lshrBig : Program := ⟨"p", [⟨"x", .bv .u64⟩], .binop .lshr X (.constBv .u64 4294967296), .bv .u64⟩

example : eval shlBig [.bitvec .u64 7] = .ok (.bitvec .u64 0) := by decide
example : eval lshrBig [.bitvec .u64 7] = .ok (.bitvec .u64 0) := by decide
/-- `u8` shift by 8 or more is `0`; by 7 is the masked product. -/
example : evalBinop .shl .u8 255 8 = 0 ∧ evalBinop .shl .u8 255 7 = 128 ∧ evalBinop .lshr .u8 255 9 = 0 := by
  decide

/-! ### Wrapping arithmetic at every width -/

example : eval ⟨"p", [⟨"x", .bv .u8⟩], .binop .add X (.constBv .u8 1), .bv .u8⟩ [.bitvec .u8 255] =
    .ok (.bitvec .u8 0) := by decide
example : eval ⟨"p", [⟨"x", .bv .u16⟩], .unop .neg X, .bv .u16⟩ [.bitvec .u16 1] =
    .ok (.bitvec .u16 65535) := by decide
example : eval ⟨"p", [⟨"x", .bv .u32⟩], .binop .sub (.constBv .u32 0) X, .bv .u32⟩ [.bitvec .u32 1] =
    .ok (.bitvec .u32 4294967295) := by decide
example : eval ⟨"p", [⟨"x", .bv .u64⟩], .unop .not X, .bv .u64⟩ [.bitvec .u64 0] =
    .ok (.bitvec .u64 18446744073709551615) := by decide

/-! ### False rewrite certificates are rejected -/

/-- The intentionally unsound `UNSOUND_add_to_lhs` (`x + y ⇒ x`) cannot be certified. -/
def addP : Program := ⟨"p", xy .u32, .binop .add X Y, .bv .u32⟩
def addBad : Program := ⟨"p_opt", xy .u32, X, .bv .u32⟩

example : checkCert ⟨addP, addBad, [⟨.addComm, []⟩], SEMANTICS, LIBRARY⟩ = false := by decide
example : checkCert ⟨addP, addBad, [⟨.andIdem, []⟩], SEMANTICS, LIBRARY⟩ = false := by decide
example : checkCert ⟨addP, addBad, [], SEMANTICS, LIBRARY⟩ = false := by decide
/-- Wrong semantic version or library identifier. -/
example : checkCert ⟨andXor .u8, orXY .u8, [⟨.andXorAddToOr, []⟩], "other", LIBRARY⟩ = false := by decide
example : checkCert ⟨andXor .u8, orXY .u8, [⟨.andXorAddToOr, []⟩], SEMANTICS, "other"⟩ = false := by decide

/-- A genuine counterexample certificate for the unsound proposal. -/
def addCex : CexCert := ⟨addP, addBad, [.bitvec .u32 1, .bitvec .u32 2]⟩
example : checkCex addCex = true := by decide
theorem addBad_not_equivalent : ¬ ∀ inputs, eval addP inputs = eval addBad inputs :=
  (counterexample_certificate_sound (c := addCex) (by decide)).2

/-- A ranking that tries the bad proposal first still accepts only the checked one. -/
example : optimize [1, 0] [certAndXor .u8, ⟨addP, addBad, [], SEMANTICS, LIBRARY⟩] =
    some (certAndXor .u8) := by decide
example : optReward (certAndXor .u8) = 3 := by decide
example : optReward ⟨addP, addBad, [], SEMANTICS, LIBRARY⟩ = -1 := by decide

end PCSForgeRefinement.Controls
