import PCSActionShield
set_option autoImplicit false
set_option maxRecDepth 8192
set_option maxHeartbeats 2000000
-- Exact model SHA256: 616fdcfefdb44e187d336eb923df590a76a98848a409070cb61a86043f12ee42
-- Exact shield SHA256: ff18a3bd9ca25812380b57ff769d6f385ad57cf99236ca0f0a5b76230b0d1786
namespace PCSActionShieldReplay
def model : PCSActionShield.Model := ⟨[0], [0, 1, 2, 3, 4, 5, 6], [⟨0, 0, 0⟩, ⟨0, 0, 6⟩, ⟨0, 1, 0⟩, ⟨0, 1, 7⟩, ⟨0, 3, 0⟩, ⟨0, 3, 1⟩, ⟨0, 3, 2⟩, ⟨1, 0, 1⟩, ⟨1, 2, 5⟩, ⟨2, 0, 2⟩, ⟨2, 0, 4⟩, ⟨2, 2, 1⟩, ⟨2, 2, 2⟩, ⟨3, 0, 0⟩, ⟨3, 0, 2⟩, ⟨3, 0, 3⟩, ⟨3, 0, 7⟩, ⟨3, 2, 2⟩, ⟨4, 0, 4⟩, ⟨4, 1, 2⟩, ⟨4, 2, 5⟩, ⟨4, 2, 7⟩, ⟨4, 3, 1⟩, ⟨5, 0, 5⟩, ⟨5, 1, 0⟩, ⟨5, 2, 1⟩, ⟨6, 0, 6⟩, ⟨6, 1, 2⟩, ⟨7, 0, 0⟩, ⟨7, 1, 5⟩, ⟨7, 3, 4⟩, ⟨7, 3, 7⟩], [(0, 0), (1, 0), (1, 2), (2, 0), (2, 2), (3, 2), (4, 0), (4, 1), (5, 0), (5, 1), (5, 2), (6, 0), (6, 1)], [3]⟩
theorem certificate_checked : PCSActionShield.check model = true := by decide
theorem all_finite_histories_safe {history : List PCSActionShield.Edge} {s : Nat}
    (h : PCSActionShield.History model history s) :
    s ∈ model.safe ∧ ∀ e ∈ history, e.action ∉ model.forbidden :=
  PCSActionShield.admitted_histories_safe certificate_checked h
#print axioms certificate_checked
#print axioms all_finite_histories_safe
end PCSActionShieldReplay
