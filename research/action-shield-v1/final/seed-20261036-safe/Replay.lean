import PCSActionShield
set_option autoImplicit false
set_option maxRecDepth 8192
set_option maxHeartbeats 2000000
-- Exact model SHA256: c61e3f5f4552cadfe7676fce69f6269a721df6162b4fe8ace8d3f6c67d40736e
-- Exact shield SHA256: 1f805749bf81903c4a4f9c200b2ace18846ae3a718f44f63166e82e04a7a1897
namespace PCSActionShieldReplay
def model : PCSActionShield.Model := ⟨[0], [0, 1, 2, 3], [⟨0, 0, 0⟩, ⟨0, 0, 3⟩, ⟨0, 1, 0⟩, ⟨0, 1, 3⟩, ⟨0, 1, 4⟩, ⟨0, 2, 4⟩, ⟨1, 0, 1⟩, ⟨1, 3, 3⟩, ⟨2, 0, 2⟩, ⟨2, 1, 0⟩, ⟨2, 1, 4⟩, ⟨2, 3, 3⟩, ⟨3, 0, 0⟩, ⟨3, 0, 1⟩, ⟨3, 0, 3⟩, ⟨3, 0, 4⟩, ⟨3, 2, 2⟩, ⟨4, 1, 0⟩, ⟨4, 2, 1⟩], [(0, 0), (1, 0), (2, 0), (3, 2)], [3]⟩
theorem certificate_checked : PCSActionShield.check model = true := by decide
theorem all_finite_histories_safe {history : List PCSActionShield.Edge} {s : Nat}
    (h : PCSActionShield.History model history s) :
    s ∈ model.safe ∧ ∀ e ∈ history, e.action ∉ model.forbidden :=
  PCSActionShield.admitted_histories_safe certificate_checked h
#print axioms certificate_checked
#print axioms all_finite_histories_safe
end PCSActionShieldReplay
