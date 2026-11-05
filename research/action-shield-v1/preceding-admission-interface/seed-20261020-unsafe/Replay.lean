import PCSActionShield
set_option autoImplicit false
set_option maxRecDepth 8192
set_option maxHeartbeats 2000000
-- Exact model SHA256: 942fcead5a9a306046622687d6d669ce090f4d8964a5e9ed837dbb780bbb7b2b
-- Exact shield SHA256: c7aa3ee65932f1d6ba6081d77a6e94c2e93eff1259efeaa340c8d8b7dbc5a9ee
namespace PCSActionShieldReplay
def model : PCSActionShield.Model := ⟨[0], [0, 1, 2, 3, 4, 5], [⟨0, 0, 0⟩, ⟨0, 0, 1⟩, ⟨0, 1, 6⟩, ⟨0, 2, 0⟩, ⟨0, 2, 3⟩, ⟨1, 0, 1⟩, ⟨1, 0, 2⟩, ⟨1, 0, 3⟩, ⟨1, 3, 0⟩, ⟨1, 3, 1⟩, ⟨2, 0, 2⟩, ⟨2, 1, 0⟩, ⟨3, 0, 3⟩, ⟨3, 0, 5⟩, ⟨3, 2, 1⟩, ⟨3, 2, 6⟩, ⟨4, 0, 4⟩, ⟨4, 1, 0⟩, ⟨4, 1, 5⟩, ⟨5, 0, 2⟩, ⟨5, 0, 4⟩, ⟨5, 0, 5⟩, ⟨5, 1, 1⟩, ⟨5, 2, 1⟩, ⟨5, 3, 5⟩, ⟨6, 1, 0⟩, ⟨6, 1, 6⟩, ⟨6, 3, 0⟩], [(0, 0), (0, 1), (0, 2), (1, 0), (2, 0), (2, 1), (3, 0), (4, 0), (4, 1), (5, 0), (5, 1), (5, 2)], [3]⟩
theorem certificate_checked : PCSActionShield.check model = true := by decide
theorem all_finite_histories_safe {history : List PCSActionShield.Edge} {s : Nat}
    (h : PCSActionShield.History model history s) :
    s ∈ model.safe ∧ ∀ e ∈ history, e.action ∉ model.forbidden :=
  PCSActionShield.admitted_histories_safe certificate_checked h
#print axioms certificate_checked
#print axioms all_finite_histories_safe
end PCSActionShieldReplay
