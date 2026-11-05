import PCSActionShield
set_option autoImplicit false
set_option maxRecDepth 8192
set_option maxHeartbeats 2000000
-- Exact model SHA256: e9169e3d7eb17dd94124b02e3295885a660c850e3fe5e96fd9a868abdddccea4
-- Exact shield SHA256: 55dde2febba720f4279b46ca7c362f71acbf800f273e7415693f9425c5689785
namespace PCSActionShieldReplay
def model : PCSActionShield.Model := ⟨[0], [0, 1, 2], [⟨0, 0, 0⟩, ⟨0, 1, 2⟩, ⟨0, 1, 3⟩, ⟨0, 2, 2⟩, ⟨1, 0, 1⟩, ⟨1, 1, 3⟩, ⟨1, 3, 2⟩, ⟨1, 3, 3⟩, ⟨2, 0, 2⟩, ⟨2, 1, 2⟩, ⟨2, 1, 3⟩, ⟨3, 0, 0⟩, ⟨3, 1, 3⟩, ⟨3, 2, 2⟩], [(0, 0), (0, 2), (1, 0), (2, 0)], [3]⟩
theorem certificate_checked : PCSActionShield.check model = true := by decide
theorem all_finite_histories_safe {history : List PCSActionShield.Edge} {s : Nat}
    (h : PCSActionShield.History model history s) :
    s ∈ model.safe ∧ ∀ e ∈ history, e.action ∉ model.forbidden :=
  PCSActionShield.admitted_histories_safe certificate_checked h
#print axioms certificate_checked
#print axioms all_finite_histories_safe
end PCSActionShieldReplay
