import PCSActionShield
set_option autoImplicit false
set_option maxRecDepth 8192
set_option maxHeartbeats 2000000
-- Exact model SHA256: 3982fe0307873890443a2164049eb2bd17507ebc06ce327b58cd21b37c1873f1
-- Exact shield SHA256: dcbb16356f44fad580b1174fab84f7dd1580a62cc7bd831121cbdd573e2c944e
namespace PCSActionShieldReplay
def model : PCSActionShield.Model := ⟨[0], [0, 1, 2, 3, 4], [⟨0, 0, 0⟩, ⟨0, 0, 1⟩, ⟨0, 0, 3⟩, ⟨0, 1, 0⟩, ⟨0, 1, 2⟩, ⟨0, 1, 5⟩, ⟨0, 2, 0⟩, ⟨0, 3, 2⟩, ⟨1, 0, 1⟩, ⟨1, 0, 4⟩, ⟨2, 0, 2⟩, ⟨3, 0, 3⟩, ⟨3, 1, 1⟩, ⟨4, 0, 4⟩, ⟨4, 0, 5⟩, ⟨4, 1, 5⟩, ⟨4, 3, 1⟩, ⟨4, 3, 5⟩, ⟨5, 1, 5⟩, ⟨5, 2, 4⟩], [(0, 0), (0, 2), (1, 0), (2, 0), (3, 0), (3, 1)], [3]⟩
theorem certificate_checked : PCSActionShield.check model = true := by decide
theorem all_finite_histories_safe {history : List PCSActionShield.Edge} {s : Nat}
    (h : PCSActionShield.History model history s) :
    s ∈ model.safe ∧ ∀ e ∈ history, e.action ∉ model.forbidden :=
  PCSActionShield.admitted_histories_safe certificate_checked h
#print axioms certificate_checked
#print axioms all_finite_histories_safe
end PCSActionShieldReplay
