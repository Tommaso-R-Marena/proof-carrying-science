import PCSActionShield
set_option autoImplicit false
set_option maxRecDepth 8192
set_option maxHeartbeats 2000000
-- Exact model SHA256: 3c25aa6a92660edcd06647929102b1ec677535c8f35047fc689c28a9ecd3a2ec
-- Exact shield SHA256: 8b942db4a3dd6b3965d97ab3abd40cbc1eb2bd6eda49f429566dd78688045032
namespace PCSActionShieldReplay
def model : PCSActionShield.Model := ⟨[0], [0, 1, 2, 3], [⟨0, 0, 0⟩, ⟨0, 0, 3⟩, ⟨0, 0, 4⟩, ⟨0, 1, 4⟩, ⟨1, 0, 1⟩, ⟨1, 0, 3⟩, ⟨1, 1, 2⟩, ⟨1, 2, 2⟩, ⟨1, 2, 3⟩, ⟨1, 3, 0⟩, ⟨2, 0, 2⟩, ⟨2, 2, 1⟩, ⟨2, 3, 3⟩, ⟨2, 3, 4⟩, ⟨3, 0, 3⟩, ⟨3, 1, 2⟩, ⟨3, 1, 4⟩, ⟨3, 2, 0⟩, ⟨4, 3, 3⟩], [(1, 0), (1, 1), (1, 2), (2, 0), (2, 2), (3, 0), (3, 2)], [3]⟩
theorem certificate_checked : PCSActionShield.check model = true := by decide
theorem all_finite_histories_safe {history : List PCSActionShield.Edge} {s : Nat}
    (h : PCSActionShield.History model history s) :
    s ∈ model.safe ∧ ∀ e ∈ history, e.action ∉ model.forbidden :=
  PCSActionShield.admitted_histories_safe certificate_checked h
#print axioms certificate_checked
#print axioms all_finite_histories_safe
end PCSActionShieldReplay
