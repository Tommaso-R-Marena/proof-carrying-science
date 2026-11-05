import PCSActionShield
set_option autoImplicit false
set_option maxRecDepth 8192
set_option maxHeartbeats 2000000
-- Exact model SHA256: b451eb3669257f788b6b87e988eced7221db466839f91d3fb9f08530167d9307
-- Exact shield SHA256: 0668f4ebcfe84c9777dac19363cacbc4bef000c95e6ad0cf9aa6df987702a968
namespace PCSActionShieldReplay
def model : PCSActionShield.Model := ⟨[0], [0, 1, 2, 3, 4], [⟨0, 0, 0⟩, ⟨0, 1, 5⟩, ⟨0, 3, 0⟩, ⟨1, 0, 0⟩, ⟨1, 0, 1⟩, ⟨1, 3, 0⟩, ⟨1, 3, 1⟩, ⟨2, 0, 2⟩, ⟨2, 3, 0⟩, ⟨2, 3, 2⟩, ⟨3, 0, 3⟩, ⟨3, 1, 5⟩, ⟨3, 2, 0⟩, ⟨3, 2, 4⟩, ⟨3, 2, 5⟩, ⟨3, 3, 4⟩, ⟨4, 0, 1⟩, ⟨4, 0, 2⟩, ⟨4, 0, 4⟩, ⟨4, 1, 5⟩, ⟨4, 2, 1⟩, ⟨4, 3, 1⟩, ⟨5, 1, 0⟩], [(0, 0), (0, 1), (1, 0), (2, 0), (3, 0), (4, 0), (4, 2)], [3]⟩
theorem certificate_checked : PCSActionShield.check model = true := by decide
theorem all_finite_histories_safe {history : List PCSActionShield.Edge} {s : Nat}
    (h : PCSActionShield.History model history s) :
    s ∈ model.safe ∧ ∀ e ∈ history, e.action ∉ model.forbidden :=
  PCSActionShield.admitted_histories_safe certificate_checked h
#print axioms certificate_checked
#print axioms all_finite_histories_safe
end PCSActionShieldReplay
