import PCSActionShield
set_option autoImplicit false
set_option maxRecDepth 8192
set_option maxHeartbeats 2000000
-- Exact model SHA256: 660df95bb50fbfaabe951e373f2cc856b59918df521232c5e5fcee4c789a07f8
-- Exact shield SHA256: c1a8b8b1fcf3a4acaf732477e1dc837fee7604dd6c99e296ca7615687359a56f
namespace PCSActionShieldReplay
def model : PCSActionShield.Model := ⟨[0], [0, 1, 2, 3, 4], [⟨0, 0, 0⟩, ⟨0, 0, 2⟩, ⟨0, 1, 5⟩, ⟨0, 2, 1⟩, ⟨0, 3, 1⟩, ⟨1, 0, 1⟩, ⟨1, 1, 2⟩, ⟨1, 3, 4⟩, ⟨2, 0, 1⟩, ⟨2, 0, 2⟩, ⟨2, 2, 3⟩, ⟨2, 3, 2⟩, ⟨2, 3, 3⟩, ⟨2, 3, 4⟩, ⟨3, 0, 1⟩, ⟨3, 0, 3⟩, ⟨4, 0, 4⟩, ⟨4, 1, 4⟩, ⟨4, 1, 5⟩, ⟨4, 2, 4⟩, ⟨5, 0, 3⟩, ⟨5, 1, 1⟩, ⟨5, 2, 3⟩], [(0, 0), (0, 2), (1, 0), (1, 1), (2, 0), (2, 2), (3, 0), (4, 0), (4, 2)], [3]⟩
theorem certificate_checked : PCSActionShield.check model = true := by decide
theorem all_finite_histories_safe {history : List PCSActionShield.Edge} {s : Nat}
    (h : PCSActionShield.History model history s) :
    s ∈ model.safe ∧ ∀ e ∈ history, e.action ∉ model.forbidden :=
  PCSActionShield.admitted_histories_safe certificate_checked h
#print axioms certificate_checked
#print axioms all_finite_histories_safe
end PCSActionShieldReplay
