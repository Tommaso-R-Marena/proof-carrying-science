import PCSActionShield
set_option autoImplicit false
set_option maxRecDepth 8192
set_option maxHeartbeats 2000000
-- Exact model SHA256: 1bcd9ebeda810b467e94e2921f0877477d3ff78639d5de3917f193ee917b0717
-- Exact shield SHA256: e84dc5684e264073825247590848b938e5440ce4df1c5c0eabe851ff23566c6b
namespace PCSActionShieldReplay
def model : PCSActionShield.Model := ⟨[0], [0, 1, 2, 3, 4, 5], [⟨0, 0, 0⟩, ⟨0, 0, 5⟩, ⟨0, 1, 6⟩, ⟨0, 2, 3⟩, ⟨1, 0, 1⟩, ⟨1, 1, 0⟩, ⟨1, 2, 6⟩, ⟨1, 3, 3⟩, ⟨2, 0, 2⟩, ⟨2, 1, 3⟩, ⟨2, 1, 4⟩, ⟨2, 3, 3⟩, ⟨3, 0, 3⟩, ⟨3, 0, 4⟩, ⟨3, 1, 1⟩, ⟨3, 1, 3⟩, ⟨4, 0, 4⟩, ⟨4, 0, 5⟩, ⟨4, 2, 1⟩, ⟨4, 2, 3⟩, ⟨4, 3, 2⟩, ⟨5, 0, 0⟩, ⟨5, 0, 2⟩, ⟨5, 0, 5⟩, ⟨5, 3, 0⟩, ⟨6, 3, 2⟩], [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (2, 0), (2, 1), (3, 0), (3, 1), (4, 0), (4, 2), (5, 0)], [3]⟩
theorem certificate_checked : PCSActionShield.check model = true := by decide
theorem all_finite_histories_safe {history : List PCSActionShield.Edge} {s : Nat}
    (h : PCSActionShield.History model history s) :
    s ∈ model.safe ∧ ∀ e ∈ history, e.action ∉ model.forbidden :=
  PCSActionShield.admitted_histories_safe certificate_checked h
#print axioms certificate_checked
#print axioms all_finite_histories_safe
end PCSActionShieldReplay
