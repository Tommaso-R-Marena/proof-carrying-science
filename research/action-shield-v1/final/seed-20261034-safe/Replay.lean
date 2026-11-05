import PCSActionShield
set_option autoImplicit false
set_option maxRecDepth 8192
set_option maxHeartbeats 2000000
-- Exact model SHA256: 1f5a3e599c485b96f81946a9c51e6cfb4b496322b2e669588e74162a03a34933
-- Exact shield SHA256: 034f749332327980a7b1a09c12af4eed040097239a459f541e2217b07232925c
namespace PCSActionShieldReplay
def model : PCSActionShield.Model := ⟨[0], [0, 1, 2], [⟨0, 0, 0⟩, ⟨0, 1, 3⟩, ⟨0, 3, 1⟩, ⟨1, 0, 1⟩, ⟨1, 1, 2⟩, ⟨1, 3, 3⟩, ⟨2, 0, 2⟩, ⟨2, 1, 0⟩, ⟨2, 1, 2⟩, ⟨2, 2, 1⟩, ⟨2, 3, 0⟩, ⟨3, 2, 2⟩, ⟨3, 2, 3⟩, ⟨3, 3, 3⟩], [(0, 0), (1, 0), (1, 1), (2, 0), (2, 1), (2, 2)], [3]⟩
theorem certificate_checked : PCSActionShield.check model = true := by decide
theorem all_finite_histories_safe {history : List PCSActionShield.Edge} {s : Nat}
    (h : PCSActionShield.History model history s) :
    s ∈ model.safe ∧ ∀ e ∈ history, e.action ∉ model.forbidden :=
  PCSActionShield.admitted_histories_safe certificate_checked h
#print axioms certificate_checked
#print axioms all_finite_histories_safe
end PCSActionShieldReplay
