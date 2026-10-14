import PCSActionShield
set_option autoImplicit false
set_option maxRecDepth 8192
set_option maxHeartbeats 2000000
-- Exact model SHA256: 96915c67484f8ffb65599c89a5676e431efee0b4b54366627bdc1b0c2e25072b
-- Exact shield SHA256: 1d4898cdcb8dedb5b4ac6c4bbf06169fc02da84c9bf91664584da3e34bb81980
namespace PCSActionShieldReplay
def model : PCSActionShield.Model := ⟨[0], [0, 1, 2, 3], [⟨0, 0, 0⟩, ⟨0, 0, 4⟩, ⟨0, 1, 0⟩, ⟨0, 1, 4⟩, ⟨1, 0, 1⟩, ⟨1, 2, 4⟩, ⟨2, 0, 1⟩, ⟨2, 0, 2⟩, ⟨2, 3, 1⟩, ⟨3, 0, 3⟩, ⟨3, 1, 4⟩, ⟨3, 2, 4⟩, ⟨3, 3, 0⟩, ⟨3, 3, 2⟩, ⟨3, 3, 3⟩, ⟨4, 1, 0⟩, ⟨4, 2, 1⟩, ⟨4, 3, 4⟩], [(1, 0), (2, 0), (3, 0)], [3]⟩
theorem certificate_checked : PCSActionShield.check model = true := by decide
theorem all_finite_histories_safe {history : List PCSActionShield.Edge} {s : Nat}
    (h : PCSActionShield.History model history s) :
    s ∈ model.safe ∧ ∀ e ∈ history, e.action ∉ model.forbidden :=
  PCSActionShield.admitted_histories_safe certificate_checked h
#print axioms certificate_checked
#print axioms all_finite_histories_safe
end PCSActionShieldReplay
