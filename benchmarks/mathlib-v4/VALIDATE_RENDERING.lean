import Mathlib.Data.Set.Function
import Mathlib.Algebra.Group.Basic
import Mathlib.Data.Nat.Factorial.Basic
import Mathlib.Data.List.Basic
import Mathlib.Data.Finset.Card
import Mathlib.Data.Real.Basic

universe u v w u_1 u_2 u_3 u_4 u_5
open Lean Elab Command Term Meta
syntax "#pcs_check_signature " ident " : " term : command
elab_rules : command
  | `(#pcs_check_signature $name:ident : $type) => do
    liftTermElabM do
      let expected ← getConstInfo name.getId
      let actual ← elabType type
      synthesizeSyntheticMVarsNoPostponing
      let actual ← instantiateMVars actual
      unless ← isDefEq expected.type actual do
        throwError "rendered proposition differs from exact declaration {name}"
      if actual.hasMVar then throwError "unresolved type metavariable"
      IO.println s!"PCS_SIGNATURE_ROUNDTRIP:{name.getId}"
#pcs_check_signature List.mem_pair : (∀ {α : Type u} {a b c : α}, a ∈ [b, c] ↔ a = b ∨ a = c)
#pcs_check_signature List.mem_map_of_injective : (∀ {α : Type u} {β : Type v} {f : α → β}, Function.Injective f → ∀ {a : α} {l : List α}, f a ∈ List.map f l ↔ a ∈ l)
#pcs_check_signature List.length_eq_two : (∀ {α : Type u} {l : List α}, l.length = 2 ↔ ∃ a b, l = [a, b])
#pcs_check_signature List.insert_neg : (∀ {α : Type u} [inst : DecidableEq α] {x : α} {l : List α}, x ∉ l → insert x l = x :: l)
#pcs_check_signature List.foldl_fixed : (∀ {α : Type u} {β : Type v} {a : α} (l : List β), List.foldl (fun a x => a) a l = a)
#pcs_check_signature Finset.card_le_card : (∀ {α : Type u_1} {s t : Finset α}, s ⊆ t → s.card ≤ t.card)
#pcs_check_signature Finset.card_insert_of_notMem : (∀ {α : Type u_1} {s : Finset α} {a : α} [inst : DecidableEq α], a ∉ s → (insert a s).card = s.card + 1)
#pcs_check_signature Finset.card_erase_add_one : (∀ {α : Type u_1} {s : Finset α} {a : α} [inst : DecidableEq α], a ∈ s → (s.erase a).card + 1 = s.card)
#pcs_check_signature Finset.card_image_of_injective : (∀ {α : Type u_1} {β : Type u_2} {f : α → β} [inst : DecidableEq β] (s : Finset α), Function.Injective f → (Finset.image f s).card = s.card)
#pcs_check_signature Finset.card_union_add_card_inter : (∀ {α : Type u_1} [inst : DecidableEq α] (s t : Finset α), (s ∪ t).card + (s ∩ t).card = s.card + t.card)
#pcs_check_signature Nat.factorial_dvd_factorial : (∀ {m n : ℕ}, m ≤ n → m.factorial ∣ n.factorial)
#pcs_check_signature Nat.dvd_factorial : (∀ {m n : ℕ}, 0 < m → m ≤ n → m ∣ n.factorial)
#pcs_check_signature Nat.factorial_eq_one : (∀ {n : ℕ}, n.factorial = 1 ↔ n ≤ 1)
#pcs_check_signature Nat.factorial_inj : (∀ {m n : ℕ}, 1 < n → (n.factorial = m.factorial ↔ n = m))
#pcs_check_signature inv_unique : (∀ {M : Type u_4} [inst : CommMonoid M] {x y z : M}, x * y = 1 → x * z = 1 → y = z)
#pcs_check_signature mul_eq_left : (∀ {M : Type u_4} [inst : Monoid M] [IsLeftCancelMul M] {a b : M}, a * b = a ↔ b = 1)
#pcs_check_signature inv_eq_iff_eq_inv : (∀ {G : Type u_3} [inst : InvolutiveInv G] {a b : G}, a⁻¹ = b ↔ a = b⁻¹)
#pcs_check_signature mul_div_assoc' : (∀ {G : Type u_3} [inst : DivInvMonoid G] (a b c : G), a * (b / c) = a * b / c)
#pcs_check_signature eq_of_inv_mul_eq_one : (∀ {α : Type u_1} [inst : DivisionMonoid α] {a b : α}, a⁻¹ * b = 1 → a = b)
#pcs_check_signature Real.ratCast_lt : (∀ {x y : ℚ}, (x : ℝ) < (y : ℝ) ↔ x < y)
#pcs_check_signature Real.mul_add_one_le_add_one_pow : (∀ {a : ℝ}, 0 ≤ a → ∀ (b : ℕ), a * ↑b + 1 ≤ (a + 1) ^ b)
#pcs_check_signature Real.mk_le_of_forall_le : (∀ {f : CauSeq ℚ abs} {x : ℝ}, (∃ i, ∀ j ≥ i, (f j : ℝ) ≤ x) → Real.mk f ≤ x)
