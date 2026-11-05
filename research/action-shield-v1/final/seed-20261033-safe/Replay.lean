import PCSActionShield
set_option autoImplicit false
set_option maxRecDepth 8192
set_option maxHeartbeats 2000000
-- Exact model SHA256: 1ea94a6527eb9ba26394019f496c23c3c4ee618565c92e913314b4f937e999c0
-- Exact shield SHA256: 2ee3f1d02539a4a0a59c3de8eaf2a363e100ab6eb0f2c4c5305724e9657de4b2
namespace PCSActionShieldReplay
def model : PCSActionShield.Model := ⟨[0], [0, 1, 2, 3, 4, 5, 6], [⟨0, 0, 0⟩, ⟨0, 1, 7⟩, ⟨0, 2, 5⟩, ⟨0, 3, 3⟩, ⟨1, 0, 0⟩, ⟨1, 0, 1⟩, ⟨1, 2, 5⟩, ⟨1, 3, 3⟩, ⟨2, 0, 2⟩, ⟨2, 2, 1⟩, ⟨2, 2, 4⟩, ⟨3, 0, 0⟩, ⟨3, 0, 3⟩, ⟨3, 2, 0⟩, ⟨3, 2, 4⟩, ⟨4, 0, 4⟩, ⟨4, 0, 6⟩, ⟨5, 0, 3⟩, ⟨5, 0, 5⟩, ⟨5, 0, 6⟩, ⟨5, 1, 4⟩, ⟨5, 2, 2⟩, ⟨6, 0, 2⟩, ⟨6, 0, 5⟩, ⟨6, 0, 6⟩, ⟨6, 0, 7⟩, ⟨6, 2, 0⟩, ⟨6, 3, 2⟩, ⟨6, 3, 6⟩, ⟨7, 0, 4⟩, ⟨7, 0, 7⟩, ⟨7, 1, 5⟩], [(0, 0), (0, 2), (1, 0), (1, 2), (2, 0), (2, 2), (3, 0), (3, 2), (4, 0), (5, 0), (5, 1), (5, 2), (6, 2)], [3]⟩
theorem certificate_checked : PCSActionShield.check model = true := by decide
theorem all_finite_histories_safe {history : List PCSActionShield.Edge} {s : Nat}
    (h : PCSActionShield.History model history s) :
    s ∈ model.safe ∧ ∀ e ∈ history, e.action ∉ model.forbidden :=
  PCSActionShield.admitted_histories_safe certificate_checked h
#print axioms certificate_checked
#print axioms all_finite_histories_safe
end PCSActionShieldReplay
