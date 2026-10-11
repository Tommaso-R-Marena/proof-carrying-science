import PCSMathLanguage.LanguageExact

/-!
# Executed controls for the controlled language (kernel-checked)

Unicode/whitespace behaviour, precedence, the `∧`/`∨` ambiguity rule, quantifier order,
shadowing, Bool-free numerals and the patched recursion bound.  The same statements were run
through the actual `language.py` by `tools/difftest/language_diff.py` (1523 cases, identical
output; log in `tools/difftest/language_diff.log`).
-/

namespace PCSMathLanguage.Language

def leanOf (names : List String) (d : Ty) (body : String) : Option (List String) :=
  (formalizeCore names d body none).map (·.map (·.lean))

/-- Unparenthesised `∧`/`∨` mixing yields two distinct candidates (status `ambiguous`). -/
example : leanOf ["p", "q"] .prop "p ∧ q ∨ p" =
    some ["∀ (p : Prop) (q : Prop), ((p ∧ q) ∨ p)", "∀ (p : Prop) (q : Prop), (p ∧ (q ∨ p))"] := by
  decide +kernel

/-- Parenthesised: one candidate. -/
example : leanOf ["p", "q"] .prop "(p ∧ q) ∨ p" = some ["∀ (p : Prop) (q : Prop), ((p ∧ q) ∨ p)"] := by
  decide +kernel

/-- Unicode whitespace (U+3000, U+00A0) separates tokens like ASCII space. -/
example : leanOf ["p", "q"] .prop "p\u3000∧\u00a0q" = some ["∀ (p : Prop) (q : Prop), (p ∧ q)"] := by
  decide +kernel

/-- A zero-width space is not Unicode whitespace: rejected. -/
example : leanOf ["p", "q"] .prop "p ∧\u200bq" = none := by decide +kernel

/-- Non-ASCII letters are not identifier characters: rejected. -/
example : leanOf ["p", "q"] .prop "pé ∧ q" = none := by decide +kernel

/-- Arithmetic precedence and the default numeral domain. -/
example : leanOf ["x"] .nat "x + 1 * 2 = 3" =
    some ["∀ (x : Nat), ((x + ((1 : Nat) * (2 : Nat))) = (3 : Nat))"] := by decide +kernel

/-- `→` is right associative. -/
example : leanOf ["p"] .prop "p → p → p" = some ["∀ (p : Prop), (p → (p → p))"] := by decide +kernel

/-- Shadowing a bound name is rejected; duplicate catalog names are rejected. -/
example : leanOf ["x"] .nat "∀ (x : Nat), x = x" = none := by decide +kernel
example : leanOf ["p", "p"] .prop "p" = none := by decide +kernel

/-- Quantifier order is preserved (`∀ ∃` and `∃ ∀` give different statements). -/
example : leanOf ["p"] .prop "∀ (n : Nat), ∃ (m : Nat), n ≤ m" =
    some ["∀ (p : Prop), (∀ (n : Nat), (∃ (m : Nat), (n ≤ m)))"] := by decide +kernel
example : leanOf ["p"] .prop "∃ (m : Nat), ∀ (n : Nat), n ≤ m" =
    some ["∀ (p : Prop), (∃ (m : Nat), (∀ (n : Nat), (n ≤ m)))"] := by decide +kernel

/-- Numerals above 1000 are rejected. -/
example : leanOf ["x"] .nat "1001 = 1001" = none := by decide +kernel

/-- The `Nat → Nat` binder expansion and application. -/
example : leanOf ["f"] .natFn "∀ (n : Nat), f n = f n" =
    some ["∀ (f : Nat → Nat), (∀ (n : Nat), ((f n) = (f n)))"] := by decide +kernel

end PCSMathLanguage.Language
