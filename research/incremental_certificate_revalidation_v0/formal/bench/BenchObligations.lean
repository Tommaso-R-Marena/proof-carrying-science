/-!
# Bounded Lean proof obligations for kernel-timing benchmarks

Real Lean checks (not Python sleep). Standalone file; no Mathlib.
-/

namespace PCSIncrementalBench

def sumTo : Nat → Nat
  | 0 => 0
  | n + 1 => sumTo n + (n + 1)

theorem sumTo_100 : sumTo 100 = 5050 := by
  native_decide

theorem sumTo_200 : sumTo 200 = 20100 := by
  native_decide

theorem sumTo_400 : sumTo 400 = 80200 := by
  native_decide

theorem sumTo_800 : sumTo 800 = 320400 := by
  native_decide

theorem chain_add (a b c : Nat) : (a + b) + c = a + (b + c) :=
  Nat.add_assoc a b c

theorem chain_mul (a b c : Nat) : (a * b) * c = a * (b * c) :=
  Nat.mul_assoc a b c

theorem many_assoc :
    (((1 + 2) + 3) + 4) + 5 = 1 + (2 + (3 + (4 + 5))) := by
  native_decide

/-- Larger native_decide product — forces more kernel/native work. -/
theorem product_fold :
    (List.range 120).foldl (· * · + 1) 1 = (List.range 120).foldl (fun a b => a * b + 1) 1 := by
  native_decide

end PCSIncrementalBench

#print axioms PCSIncrementalBench.sumTo_800
#print axioms PCSIncrementalBench.chain_add
