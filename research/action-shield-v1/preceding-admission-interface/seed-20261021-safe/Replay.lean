import PCSActionShield
set_option autoImplicit false
set_option maxRecDepth 8192
set_option maxHeartbeats 2000000
-- Exact model SHA256: 0edfdef0784b2a6c573fe8bece1dd170419eafe07ae37331102f10bd04025c76
-- Exact shield SHA256: 1b2811cf31e5e837ae060931f4bfa779c54389c59bc0f49526db526e0e4f553b
namespace PCSActionShieldReplay
def model : PCSActionShield.Model := ⟨[0], [0, 1, 2, 3, 4, 5, 6], [⟨0, 0, 0⟩, ⟨0, 0, 1⟩, ⟨0, 0, 4⟩, ⟨0, 0, 7⟩, ⟨0, 1, 0⟩, ⟨0, 1, 7⟩, ⟨0, 2, 2⟩, ⟨1, 0, 1⟩, ⟨1, 0, 3⟩, ⟨1, 2, 4⟩, ⟨1, 2, 7⟩, ⟨2, 0, 2⟩, ⟨2, 1, 2⟩, ⟨2, 2, 4⟩, ⟨3, 0, 3⟩, ⟨3, 2, 4⟩, ⟨4, 0, 2⟩, ⟨4, 0, 4⟩, ⟨4, 1, 3⟩, ⟨4, 2, 1⟩, ⟨5, 0, 3⟩, ⟨5, 0, 5⟩, ⟨5, 1, 0⟩, ⟨6, 0, 6⟩, ⟨6, 1, 0⟩, ⟨6, 2, 3⟩, ⟨7, 3, 1⟩, ⟨7, 3, 6⟩], [(0, 2), (1, 0), (2, 0), (2, 1), (2, 2), (3, 0), (3, 2), (4, 0), (4, 1), (4, 2), (5, 0), (5, 1), (6, 0), (6, 1), (6, 2)], [3]⟩
theorem certificate_checked : PCSActionShield.check model = true := by decide
theorem all_finite_histories_safe {history : List PCSActionShield.Edge} {s : Nat}
    (h : PCSActionShield.History model history s) :
    s ∈ model.safe ∧ ∀ e ∈ history, e.action ∉ model.forbidden :=
  PCSActionShield.admitted_histories_safe certificate_checked h
#print axioms certificate_checked
#print axioms all_finite_histories_safe
end PCSActionShieldReplay
