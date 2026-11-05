import PCSCountermodel.Fixtures

/-!
# Intentionally wrong target — this file MUST be rejected by `lean`

It claims that the two `implication-flip` statements are equivalent in the reference world
`{n:1, P:[true], Q:[false], R:[[false]]}`. The proposition is false, so `decide` evaluates
the (proved-correct) decision procedure to `false` and elaboration fails. There is no
syntax error, no missing import and no `sorry`.

This file is deliberately NOT part of the `PCSCountermodel` library.
-/

open PCSCountermodel PCSCountermodel.Fixtures

theorem wrong_implicationFlip_equivalent :
    Holds implicationFlipWorld emptyEnv implicationFlipLeft ↔
      Holds implicationFlipWorld emptyEnv implicationFlipRight := by
  decide
