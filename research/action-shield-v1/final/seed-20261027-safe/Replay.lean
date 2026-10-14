import PCSActionShield
set_option autoImplicit false
set_option maxRecDepth 8192
set_option maxHeartbeats 2000000
-- Exact model SHA256: 28899bdefcb12ca81776e2dc984c2b1ea7ce7924145a207ecf6f47848cfc8a41
-- Exact shield SHA256: 40891c3d60e4bfa956cc3a69bc8c44b5d1cb58da9a82481cd1d3e64421f30a87
namespace PCSActionShieldReplay
def model : PCSActionShield.Model := ⟨[0], [0, 1, 2, 3], [⟨0, 0, 0⟩, ⟨0, 1, 0⟩, ⟨0, 1, 1⟩, ⟨0, 1, 4⟩, ⟨0, 2, 1⟩, ⟨0, 3, 3⟩, ⟨1, 0, 1⟩, ⟨1, 1, 3⟩, ⟨1, 2, 2⟩, ⟨1, 2, 3⟩, ⟨2, 0, 2⟩, ⟨2, 2, 2⟩, ⟨2, 3, 1⟩, ⟨3, 0, 0⟩, ⟨3, 0, 3⟩, ⟨3, 1, 3⟩, ⟨4, 1, 2⟩, ⟨4, 1, 3⟩, ⟨4, 3, 2⟩], [(0, 0), (0, 2), (1, 0), (1, 1), (1, 2), (2, 0), (2, 2), (3, 0), (3, 1)], [3]⟩
theorem certificate_checked : PCSActionShield.check model = true := by decide
theorem all_finite_histories_safe {history : List PCSActionShield.Edge} {s : Nat}
    (h : PCSActionShield.History model history s) :
    s ∈ model.safe ∧ ∀ e ∈ history, e.action ∉ model.forbidden :=
  PCSActionShield.admitted_histories_safe certificate_checked h
#print axioms certificate_checked
#print axioms all_finite_histories_safe
end PCSActionShieldReplay
