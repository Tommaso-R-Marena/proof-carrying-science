import PCSActionShield
set_option autoImplicit false
set_option maxRecDepth 8192
set_option maxHeartbeats 2000000
-- Exact model SHA256: 1d1ed236664376ee24274105f4407941b71be860a232ecbc1ac82bf973156fea
-- Exact shield SHA256: 110aea8ec59e3fbf04656f0d1dc147d8d2825e0c475a317d7a98c92429275f3a
namespace PCSActionShieldReplay
def model : PCSActionShield.Model := ⟨[0], [0, 1, 2, 3, 4, 5, 6], [⟨0, 0, 0⟩, ⟨0, 1, 7⟩, ⟨0, 2, 6⟩, ⟨1, 0, 1⟩, ⟨1, 0, 2⟩, ⟨2, 0, 2⟩, ⟨2, 1, 6⟩, ⟨2, 2, 1⟩, ⟨3, 0, 3⟩, ⟨3, 0, 5⟩, ⟨4, 0, 3⟩, ⟨4, 0, 4⟩, ⟨4, 1, 0⟩, ⟨4, 1, 7⟩, ⟨4, 2, 1⟩, ⟨4, 2, 2⟩, ⟨5, 0, 5⟩, ⟨5, 2, 4⟩, ⟨6, 0, 6⟩, ⟨6, 0, 7⟩, ⟨6, 1, 2⟩, ⟨6, 1, 3⟩, ⟨6, 1, 7⟩, ⟨6, 2, 7⟩, ⟨7, 1, 5⟩, ⟨7, 2, 2⟩, ⟨7, 2, 6⟩, ⟨7, 3, 1⟩, ⟨7, 3, 4⟩, ⟨7, 3, 6⟩], [(0, 0), (0, 1), (0, 2), (1, 0), (2, 0), (2, 1), (2, 2), (3, 0), (4, 0), (4, 2), (5, 0), (5, 2)], [3]⟩
theorem certificate_checked : PCSActionShield.check model = true := by decide
theorem all_finite_histories_safe {history : List PCSActionShield.Edge} {s : Nat}
    (h : PCSActionShield.History model history s) :
    s ∈ model.safe ∧ ∀ e ∈ history, e.action ∉ model.forbidden :=
  PCSActionShield.admitted_histories_safe certificate_checked h
#print axioms certificate_checked
#print axioms all_finite_histories_safe
end PCSActionShieldReplay
