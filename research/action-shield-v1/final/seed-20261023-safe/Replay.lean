import PCSActionShield
set_option autoImplicit false
set_option maxRecDepth 8192
set_option maxHeartbeats 2000000
-- Exact model SHA256: c4c8271817e7f3d8ccbd40f3ae3b50b88d51a6dd56511f359217f1387213b997
-- Exact shield SHA256: d06d27d0f3f67ade2fb8b9c566c43e2d636d509b32a420b8dbea34a9e1e8b40f
namespace PCSActionShieldReplay
def model : PCSActionShield.Model := ⟨[0], [0, 1, 2, 3, 4], [⟨0, 0, 0⟩, ⟨0, 1, 5⟩, ⟨0, 3, 1⟩, ⟨1, 0, 1⟩, ⟨1, 1, 2⟩, ⟨1, 3, 2⟩, ⟨2, 0, 2⟩, ⟨2, 0, 3⟩, ⟨2, 0, 4⟩, ⟨2, 1, 2⟩, ⟨2, 1, 4⟩, ⟨2, 2, 0⟩, ⟨2, 2, 2⟩, ⟨2, 2, 5⟩, ⟨3, 0, 1⟩, ⟨3, 0, 3⟩, ⟨3, 3, 1⟩, ⟨4, 0, 4⟩, ⟨4, 0, 5⟩, ⟨4, 2, 2⟩, ⟨4, 2, 4⟩, ⟨5, 2, 0⟩], [(0, 0), (1, 0), (1, 1), (2, 0), (2, 1), (3, 0), (4, 2)], [3]⟩
theorem certificate_checked : PCSActionShield.check model = true := by decide
theorem all_finite_histories_safe {history : List PCSActionShield.Edge} {s : Nat}
    (h : PCSActionShield.History model history s) :
    s ∈ model.safe ∧ ∀ e ∈ history, e.action ∉ model.forbidden :=
  PCSActionShield.admitted_histories_safe certificate_checked h
#print axioms certificate_checked
#print axioms all_finite_histories_safe
end PCSActionShieldReplay
