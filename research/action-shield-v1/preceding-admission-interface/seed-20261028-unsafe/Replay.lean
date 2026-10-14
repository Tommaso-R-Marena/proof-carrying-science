import PCSActionShield
set_option autoImplicit false
set_option maxRecDepth 8192
set_option maxHeartbeats 2000000
-- Exact model SHA256: 49319181fa1cf460324d9b37654f7021c3d759ef957dcb5ab716f62e2c42dcbc
-- Exact shield SHA256: 1633c64932f6b32d08906ee45f3eb7afa7cf2a8b0fd23cac2cbd359907ea6030
namespace PCSActionShieldReplay
def model : PCSActionShield.Model := ⟨[0], [0, 1, 2, 3, 4, 5, 6], [⟨0, 0, 0⟩, ⟨0, 0, 3⟩, ⟨0, 0, 4⟩, ⟨0, 1, 0⟩, ⟨0, 1, 7⟩, ⟨0, 2, 2⟩, ⟨0, 3, 3⟩, ⟨1, 0, 1⟩, ⟨1, 0, 7⟩, ⟨2, 0, 2⟩, ⟨2, 1, 2⟩, ⟨3, 0, 0⟩, ⟨3, 0, 3⟩, ⟨3, 2, 1⟩, ⟨3, 3, 6⟩, ⟨4, 0, 4⟩, ⟨4, 1, 0⟩, ⟨4, 2, 2⟩, ⟨4, 3, 6⟩, ⟨5, 0, 5⟩, ⟨5, 1, 0⟩, ⟨5, 1, 3⟩, ⟨5, 1, 4⟩, ⟨5, 3, 6⟩, ⟨6, 0, 6⟩, ⟨6, 1, 3⟩, ⟨6, 2, 3⟩, ⟨6, 3, 5⟩, ⟨7, 0, 3⟩, ⟨7, 0, 5⟩, ⟨7, 1, 3⟩, ⟨7, 1, 4⟩], [(0, 0), (0, 1), (0, 2), (2, 0), (2, 1), (3, 0), (3, 2), (4, 0), (4, 1), (4, 2), (5, 0), (5, 1), (6, 0), (6, 1), (6, 2)], [3]⟩
theorem certificate_checked : PCSActionShield.check model = true := by decide
theorem all_finite_histories_safe {history : List PCSActionShield.Edge} {s : Nat}
    (h : PCSActionShield.History model history s) :
    s ∈ model.safe ∧ ∀ e ∈ history, e.action ∉ model.forbidden :=
  PCSActionShield.admitted_histories_safe certificate_checked h
#print axioms certificate_checked
#print axioms all_finite_histories_safe
end PCSActionShieldReplay
