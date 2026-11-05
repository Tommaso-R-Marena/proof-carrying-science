import PCSActionShield
set_option autoImplicit false
set_option maxRecDepth 8192
set_option maxHeartbeats 2000000
-- Exact model SHA256: 2d76a70d696d4df38ba7590db84dddc83103efb819b6941c18dbfea05375e0a2
-- Exact shield SHA256: 991f2fdae482b0468fcd7b046793fdb6486775889f54c3bfa515b03f1c4c6822
namespace PCSActionShieldReplay
def model : PCSActionShield.Model := ⟨[0], [0, 1, 2, 3, 4], [⟨0, 0, 0⟩, ⟨0, 0, 1⟩, ⟨0, 1, 1⟩, ⟨0, 1, 4⟩, ⟨0, 1, 5⟩, ⟨0, 2, 1⟩, ⟨1, 0, 1⟩, ⟨1, 0, 5⟩, ⟨1, 1, 2⟩, ⟨1, 1, 4⟩, ⟨1, 3, 0⟩, ⟨1, 3, 4⟩, ⟨2, 0, 2⟩, ⟨3, 0, 1⟩, ⟨3, 0, 3⟩, ⟨3, 0, 4⟩, ⟨4, 0, 4⟩, ⟨4, 1, 0⟩, ⟨4, 2, 0⟩, ⟨4, 2, 1⟩, ⟨4, 2, 3⟩, ⟨5, 0, 5⟩], [(0, 0), (0, 2), (1, 1), (2, 0), (3, 0), (4, 0), (4, 1), (4, 2)], [3]⟩
theorem certificate_checked : PCSActionShield.check model = true := by decide
theorem all_finite_histories_safe {history : List PCSActionShield.Edge} {s : Nat}
    (h : PCSActionShield.History model history s) :
    s ∈ model.safe ∧ ∀ e ∈ history, e.action ∉ model.forbidden :=
  PCSActionShield.admitted_histories_safe certificate_checked h
#print axioms certificate_checked
#print axioms all_finite_histories_safe
end PCSActionShieldReplay
