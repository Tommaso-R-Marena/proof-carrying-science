import PCSActionShield
set_option autoImplicit false
set_option maxRecDepth 8192
set_option maxHeartbeats 2000000
-- Exact model SHA256: c60e24ff390188ba2e3abbe1d677a9e27aef5a73c3e317504ee9f54841923b4f
-- Exact shield SHA256: 3da20d15ad9ad37cada594d7d45f6e5b49367866eb3e74256df8e396c61097f7
namespace PCSActionShieldReplay
def model : PCSActionShield.Model := ⟨[0], [0, 1, 2, 3, 4, 5, 6], [⟨0, 0, 0⟩, ⟨0, 1, 7⟩, ⟨0, 2, 4⟩, ⟨0, 3, 1⟩, ⟨1, 0, 1⟩, ⟨1, 0, 7⟩, ⟨1, 1, 6⟩, ⟨1, 2, 4⟩, ⟨1, 3, 3⟩, ⟨1, 3, 6⟩, ⟨2, 0, 0⟩, ⟨2, 0, 2⟩, ⟨2, 1, 4⟩, ⟨2, 2, 7⟩, ⟨3, 0, 1⟩, ⟨3, 0, 3⟩, ⟨3, 1, 1⟩, ⟨3, 2, 6⟩, ⟨4, 0, 4⟩, ⟨4, 1, 0⟩, ⟨4, 1, 5⟩, ⟨4, 2, 2⟩, ⟨5, 0, 5⟩, ⟨5, 3, 7⟩, ⟨6, 0, 6⟩, ⟨6, 1, 2⟩, ⟨6, 2, 1⟩, ⟨7, 0, 2⟩, ⟨7, 3, 5⟩], [(0, 0), (0, 1), (0, 2), (1, 1), (1, 2), (2, 0), (2, 1), (3, 0), (3, 1), (3, 2), (4, 0), (4, 1), (4, 2), (5, 0), (6, 0), (6, 1), (6, 2)], [3]⟩
theorem certificate_checked : PCSActionShield.check model = true := by decide
theorem all_finite_histories_safe {history : List PCSActionShield.Edge} {s : Nat}
    (h : PCSActionShield.History model history s) :
    s ∈ model.safe ∧ ∀ e ∈ history, e.action ∉ model.forbidden :=
  PCSActionShield.admitted_histories_safe certificate_checked h
#print axioms certificate_checked
#print axioms all_finite_histories_safe
end PCSActionShieldReplay
