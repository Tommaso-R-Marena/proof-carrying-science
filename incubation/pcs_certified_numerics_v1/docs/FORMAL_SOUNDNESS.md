# Formal soundness

Lean library `CertNum` (Lean 4.28.0, Mathlib `v4.28.0`), **`lake build` OK**, **no `sorry`**.

## Interval layer

- `mem_neg`, `mem_add`, `mem_sub`, `mem_mul`
- `mem_abs`, `mem_square`
- `mem_recip`, `mem_div` (denominator excludes zero)
- hull / inter / width

## Expression layer

- `evalInterval_sound_arith` for the `IsChecked` fragment: `const`, `var`, `neg`, `abs`
- `powNat_mem` for integer powers on intervals
- Binary `add`/`sub`/`mul` lifting through `evalInterval` status tests: next formal step
  (interval-level `mem_add`/`mem_mul` already proved)

## Certificate checker

- `checkIntervalEnclosure` + `checkIntervalEnclosure_sound`:
  if the checker accepts an `IsChecked` certificate, every exact evaluation in the box
  lands in the claimed enclosure.

Axiom policy: Mathlib classical foundations only; no project axioms.
