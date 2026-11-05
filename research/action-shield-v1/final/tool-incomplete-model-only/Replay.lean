import PCSActionShield
set_option autoImplicit false
set_option maxRecDepth 8192
set_option maxHeartbeats 2000000
-- Exact model SHA256: 03393504a55b66cda65dfacce68feadbefec1fac24c9da8d473163f3c5a4f0d3
-- Exact shield SHA256: 93c9a7813ce4faeda78cc823f406769abb6c84fb6e944ceb2423c30a5e924b58
namespace PCSActionShieldReplay
def model : PCSActionShield.Model := ⟨[0], [0, 1, 2, 3, 4], [⟨0, 0, 0⟩, ⟨0, 0, 1⟩, ⟨0, 1, 5⟩, ⟨0, 5, 0⟩, ⟨1, 1, 2⟩, ⟨1, 5, 5⟩, ⟨2, 2, 3⟩, ⟨2, 3, 4⟩, ⟨2, 5, 5⟩, ⟨3, 3, 4⟩, ⟨3, 5, 5⟩, ⟨4, 4, 4⟩, ⟨4, 5, 5⟩, ⟨5, 4, 5⟩], [(0, 0), (1, 1), (2, 2), (2, 3), (3, 3), (4, 4)], [5]⟩
theorem certificate_checked : PCSActionShield.check model = true := by decide
theorem all_finite_histories_safe {history : List PCSActionShield.Edge} {s : Nat}
    (h : PCSActionShield.History model history s) :
    s ∈ model.safe ∧ ∀ e ∈ history, e.action ∉ model.forbidden :=
  PCSActionShield.admitted_histories_safe certificate_checked h
#print axioms certificate_checked
#print axioms all_finite_histories_safe
end PCSActionShieldReplay
