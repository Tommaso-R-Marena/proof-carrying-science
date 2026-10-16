import PCSActionShield
set_option autoImplicit false
set_option maxRecDepth 8192
set_option maxHeartbeats 2000000
-- Exact model SHA256: 852cd7c4708e8fac37aa3d79bc0fae81dccc9873e6c24c7d0488ba3d94436075
-- Exact shield SHA256: 59c78bfd201edaaf077c9868dad776f2cf9ead5d216e476118fe7a1e5bc5dfa1
namespace PCSActionShieldReplay
def model : PCSActionShield.Model := ⟨[0], [0, 1, 2, 3, 4, 5, 6], [⟨0, 0, 0⟩, ⟨0, 0, 4⟩, ⟨0, 1, 3⟩, ⟨0, 1, 7⟩, ⟨1, 0, 0⟩, ⟨1, 0, 1⟩, ⟨1, 1, 2⟩, ⟨1, 2, 0⟩, ⟨1, 2, 7⟩, ⟨1, 3, 6⟩, ⟨2, 0, 2⟩, ⟨2, 1, 7⟩, ⟨3, 0, 3⟩, ⟨3, 0, 4⟩, ⟨3, 0, 5⟩, ⟨3, 0, 6⟩, ⟨4, 0, 1⟩, ⟨4, 0, 3⟩, ⟨4, 0, 4⟩, ⟨4, 1, 0⟩, ⟨4, 2, 0⟩, ⟨4, 3, 6⟩, ⟨5, 0, 5⟩, ⟨5, 1, 0⟩, ⟨5, 1, 5⟩, ⟨5, 1, 6⟩, ⟨5, 2, 5⟩, ⟨5, 2, 6⟩, ⟨6, 0, 6⟩, ⟨7, 0, 3⟩, ⟨7, 2, 6⟩], [(0, 0), (1, 0), (1, 1), (2, 0), (3, 0), (4, 0), (4, 1), (4, 2), (5, 0), (5, 1), (5, 2), (6, 0)], [3]⟩
theorem certificate_checked : PCSActionShield.check model = true := by decide
theorem all_finite_histories_safe {history : List PCSActionShield.Edge} {s : Nat}
    (h : PCSActionShield.History model history s) :
    s ∈ model.safe ∧ ∀ e ∈ history, e.action ∉ model.forbidden :=
  PCSActionShield.admitted_histories_safe certificate_checked h
#print axioms certificate_checked
#print axioms all_finite_histories_safe
end PCSActionShieldReplay
