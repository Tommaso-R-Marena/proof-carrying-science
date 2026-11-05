import PCSActionShield
set_option autoImplicit false
set_option maxRecDepth 8192
set_option maxHeartbeats 2000000
-- Exact model SHA256: 4f1a323f1e8b2ee93cf655b56e626315f2712e6b1c155ac1039c71451c770723
-- Exact shield SHA256: b5c1039c2c08081239f2f0a1d723511976b7ffea1873c1be8018532075fc2aa3
namespace PCSActionShieldReplay
def model : PCSActionShield.Model := ⟨[0], [0, 1, 2, 3], [⟨0, 0, 0⟩, ⟨0, 0, 1⟩, ⟨0, 1, 4⟩, ⟨0, 2, 1⟩, ⟨1, 0, 1⟩, ⟨1, 0, 2⟩, ⟨1, 0, 4⟩, ⟨1, 3, 3⟩, ⟨2, 0, 2⟩, ⟨2, 3, 1⟩, ⟨3, 0, 3⟩, ⟨3, 1, 3⟩, ⟨3, 3, 0⟩, ⟨3, 3, 4⟩, ⟨4, 0, 3⟩, ⟨4, 1, 4⟩, ⟨4, 3, 3⟩], [(0, 0), (0, 2), (2, 0), (3, 0), (3, 1)], [3]⟩
theorem certificate_checked : PCSActionShield.check model = true := by decide
theorem all_finite_histories_safe {history : List PCSActionShield.Edge} {s : Nat}
    (h : PCSActionShield.History model history s) :
    s ∈ model.safe ∧ ∀ e ∈ history, e.action ∉ model.forbidden :=
  PCSActionShield.admitted_histories_safe certificate_checked h
#print axioms certificate_checked
#print axioms all_finite_histories_safe
end PCSActionShieldReplay
