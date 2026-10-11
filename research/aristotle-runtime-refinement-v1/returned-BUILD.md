# Building and checking the PCS verified-reasoning package

Toolchain: `leanprover/lean4:v4.28.0` (see `lean-toolchain`).  The root project is Std-only:
`lakefile.toml` has zero `require` declarations and `lake-manifest.json` lists zero packages.

## Std proof core (root project)

```sh
# original production libraries and executables (default targets, unchanged)
lake build

# new proof libraries, executable checkers and kernel-checked controls
lake build PCSRuntimeRefinement PCSMathLanguage PCSReasoningLibrary PCSAssumptionDiscovery \
           PCSVerifiedLearning PCSForgeRefinement PCSStatisticsCore PCSEndToEnd PCSNewControls

# transitive axiom inventory of every principal theorem
lake env lean tools/PrintPrincipalAxioms.lean
```

Logs from these commands are in `logs/`:

* `logs/build_new_libraries.log`: build of the nine new libraries (exit 0).
* `logs/rust_extraction_compile.log`: from-scratch elaboration of the three Rust extraction
  modules (exit 0, no messages).
* `logs/principal_axioms.log`: `#print axioms` for 54 principal and supporting theorems.  Each depends on
  a subset of `propext`, `Classical.choice` and `Quot.sound`, or on no axioms at all.  None
  uses `sorryAx`, `Lean.ofReduceBool` or `Lean.trustCompiler`.

The new libraries contain no `sorry`, `admit`, `axiom`, `native_decide`, `implemented_by` or
`unsafe`.  You can check this with:

```sh
rg -nw "sorry|admit|native_decide|implemented_by|unsafe|axiom" PCSRuntimeRefinement PCSMathLanguage \
   PCSReasoningLibrary PCSAssumptionDiscovery PCSVerifiedLearning PCSForgeRefinement \
   PCSStatisticsCore PCSEndToEnd statistics
```

The only hits are docstrings, the receiver's forbidden-token lists (`FORBIDDEN`, the reserved
name list) and a control that checks a `sorry` action is rejected.

Large finite checks use `decide +kernel`, which is checked by the ordinary kernel.  This
covers the source-binding certificates, the controls and the language-table certificates.

## Mathlib statistical gates (separate library)

`statistics/` is a separate Lake project.  Its `lakefile.toml` pins Mathlib through an exact Git
dependency: `https://github.com/leanprover-community/mathlib4.git`, rev
`8f9d9cff6bd728b17a24e163c9402775d9e6a365`.  It never uses a local `path` dependency.  It
was checked against a Mathlib checkout at exactly that revision:

```sh
cd <mathlib checkout at 8f9d9cff6bd728b17a24e163c9402775d9e6a365>
lake env lean <this package>/statistics/PCSStatistics/Gates.lean
```

The log is `logs/statistics_mathlib_gates.log`.  It ends with exit 0 and the Mathlib revision
actually used, and its only messages are unused-variable linter warnings.  To check it as its
own project, run `cd statistics && lake update && lake build`, which downloads that Mathlib
revision.

## Differential tests (not proofs)

* `tools/difftest/language_diff.py`: runs the actual `language.py` and the Lean transcription
  on 1523 cases and compares the results (all identical; see `tools/difftest/language_diff.log`).
* `counterexamples/language_recursion/`: `reproduce.py`, the original failing log, the proposed
  patch and the patched log.
