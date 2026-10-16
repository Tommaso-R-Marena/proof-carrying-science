import PCSActionShield
set_option autoImplicit false
set_option maxRecDepth 8192
set_option maxHeartbeats 2000000
-- Exact model SHA256: 58ed24d8a71cec93b873276c8fe1359ea15ad5535e94054bc159049cef65f7cf
-- Exact shield SHA256: 36e4e424002be20d3e0f48486601d87eee5c84815bb43396f683074eb97db823
namespace PCSActionShieldReplay
def model : PCSActionShield.Model := ⟨[0], [0, 1, 2, 3, 4], [⟨0, 0, 0⟩, ⟨0, 0, 1⟩, ⟨0, 1, 5⟩, ⟨0, 5, 0⟩, ⟨1, 1, 2⟩, ⟨1, 5, 5⟩, ⟨2, 2, 3⟩, ⟨2, 3, 4⟩, ⟨2, 3, 5⟩, ⟨2, 5, 5⟩, ⟨3, 3, 4⟩, ⟨3, 5, 5⟩, ⟨4, 4, 4⟩, ⟨4, 5, 5⟩, ⟨5, 4, 5⟩], [], [5]⟩
theorem certificate_checked : PCSActionShield.check model = true := by decide
theorem all_finite_histories_safe {history : List PCSActionShield.Edge} {s : Nat}
    (h : PCSActionShield.History model history s) :
    s ∈ model.safe ∧ ∀ e ∈ history, e.action ∉ model.forbidden :=
  PCSActionShield.admitted_histories_safe certificate_checked h
#print axioms certificate_checked
#print axioms all_finite_histories_safe
end PCSActionShieldReplay
