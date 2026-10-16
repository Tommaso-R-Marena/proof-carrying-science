import PCSActionShield
set_option autoImplicit false
set_option maxRecDepth 8192
set_option maxHeartbeats 2000000
-- Exact model SHA256: 80dbb96f1ee33edbfc69d42693e93567c559c626e5bcf8135a706a269eabab9b
-- Exact shield SHA256: 5d9207cdecda7975a85409fe7feca2ee0f4eacb37414f896ee587dc3bc0d394f
namespace PCSActionShieldReplay
def model : PCSActionShield.Model := ⟨[0], [0, 1, 2, 3, 4, 5], [⟨0, 0, 0⟩, ⟨0, 1, 6⟩, ⟨0, 2, 0⟩, ⟨0, 2, 5⟩, ⟨0, 3, 1⟩, ⟨1, 0, 1⟩, ⟨1, 0, 3⟩, ⟨1, 0, 6⟩, ⟨1, 1, 5⟩, ⟨1, 2, 4⟩, ⟨2, 0, 2⟩, ⟨2, 0, 3⟩, ⟨2, 1, 2⟩, ⟨2, 1, 6⟩, ⟨2, 3, 0⟩, ⟨3, 0, 0⟩, ⟨3, 0, 3⟩, ⟨3, 1, 2⟩, ⟨3, 3, 5⟩, ⟨4, 0, 4⟩, ⟨4, 1, 4⟩, ⟨4, 2, 3⟩, ⟨4, 2, 4⟩, ⟨5, 0, 5⟩, ⟨5, 2, 0⟩, ⟨5, 2, 4⟩, ⟨6, 2, 5⟩], [(0, 0), (0, 1), (0, 2), (1, 1), (1, 2), (2, 0), (3, 0), (3, 1), (4, 0), (4, 1), (4, 2), (5, 0), (5, 2)], [3]⟩
theorem certificate_checked : PCSActionShield.check model = true := by decide
theorem all_finite_histories_safe {history : List PCSActionShield.Edge} {s : Nat}
    (h : PCSActionShield.History model history s) :
    s ∈ model.safe ∧ ∀ e ∈ history, e.action ∉ model.forbidden :=
  PCSActionShield.admitted_histories_safe certificate_checked h
#print axioms certificate_checked
#print axioms all_finite_histories_safe
end PCSActionShieldReplay
