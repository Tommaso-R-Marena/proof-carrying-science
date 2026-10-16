import PCSActionShield
set_option autoImplicit false
set_option maxRecDepth 8192
set_option maxHeartbeats 2000000
-- Exact model SHA256: c1356bba04d9d958919096fce4a26f0c312a745b8955868982ac8ab20d5f21f6
-- Exact shield SHA256: d8b6e8c4d7e5841f5c4777d545d1cccb32b5497072c91c3d1f819aaaa1e9e4f0
namespace PCSActionShieldReplay
def model : PCSActionShield.Model := ⟨[0], [0, 1, 2, 3], [⟨0, 0, 0⟩, ⟨0, 0, 4⟩, ⟨0, 1, 4⟩, ⟨0, 2, 0⟩, ⟨0, 2, 2⟩, ⟨0, 2, 4⟩, ⟨1, 0, 0⟩, ⟨1, 0, 1⟩, ⟨2, 0, 2⟩, ⟨2, 0, 3⟩, ⟨3, 0, 0⟩, ⟨3, 0, 3⟩, ⟨3, 1, 3⟩, ⟨4, 0, 0⟩, ⟨4, 0, 1⟩, ⟨4, 1, 4⟩], [(1, 0), (2, 0), (3, 0), (3, 1)], [3]⟩
theorem certificate_checked : PCSActionShield.check model = true := by decide
theorem all_finite_histories_safe {history : List PCSActionShield.Edge} {s : Nat}
    (h : PCSActionShield.History model history s) :
    s ∈ model.safe ∧ ∀ e ∈ history, e.action ∉ model.forbidden :=
  PCSActionShield.admitted_histories_safe certificate_checked h
#print axioms certificate_checked
#print axioms all_finite_histories_safe
end PCSActionShieldReplay
