import PCSActionShield
set_option autoImplicit false
set_option maxRecDepth 8192
set_option maxHeartbeats 2000000
-- Exact model SHA256: 8ffdf8e28fc9cc7b155b2eacb4122f440353bb5f66e22eb9e49a53b99e3f2074
-- Exact shield SHA256: c3c4aa5444fa34a76655827335ec027379b263f470802c6680573c54bd661b29
namespace PCSActionShieldReplay
def model : PCSActionShield.Model := ⟨[0], [0, 1, 2, 3, 4, 5, 6], [⟨0, 0, 0⟩, ⟨0, 1, 7⟩, ⟨0, 2, 2⟩, ⟨0, 2, 4⟩, ⟨0, 2, 7⟩, ⟨0, 3, 0⟩, ⟨1, 0, 1⟩, ⟨1, 3, 4⟩, ⟨2, 0, 2⟩, ⟨2, 0, 5⟩, ⟨2, 2, 1⟩, ⟨2, 2, 5⟩, ⟨2, 3, 5⟩, ⟨3, 0, 3⟩, ⟨3, 1, 6⟩, ⟨3, 3, 1⟩, ⟨4, 0, 2⟩, ⟨4, 0, 4⟩, ⟨4, 1, 5⟩, ⟨4, 2, 1⟩, ⟨4, 2, 5⟩, ⟨5, 0, 3⟩, ⟨5, 0, 5⟩, ⟨5, 0, 6⟩, ⟨5, 2, 7⟩, ⟨6, 0, 6⟩, ⟨6, 2, 1⟩, ⟨7, 0, 5⟩, ⟨7, 2, 4⟩, ⟨7, 3, 1⟩], [(0, 0), (1, 0), (2, 0), (2, 2), (3, 0), (3, 1), (4, 0), (4, 1), (4, 2), (5, 0), (6, 0), (6, 2)], [3]⟩
theorem certificate_checked : PCSActionShield.check model = true := by decide
theorem all_finite_histories_safe {history : List PCSActionShield.Edge} {s : Nat}
    (h : PCSActionShield.History model history s) :
    s ∈ model.safe ∧ ∀ e ∈ history, e.action ∉ model.forbidden :=
  PCSActionShield.admitted_histories_safe certificate_checked h
#print axioms certificate_checked
#print axioms all_finite_histories_safe
end PCSActionShieldReplay
