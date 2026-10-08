import PCS.V2.GoldenCx.Literals
import PCS.V2.KernelRfl
import PCS.V2.Ed25519
import PCS.V2.GoldenCx.Spec

/-!
# Kernel-checked Ed25519 verification of the two cx signatures

*Counterexample archive `cx` (`PCS.V2.GoldenCx.Spec`).*  This file is a mechanical
clone of the corresponding `PCS.V2.Golden` file with the fixture `golden` replaced by `cx`;
all generic lemmas are reused from `PCS.V2.Golden`.

The production RFC 8032 verifier `PCS.V2.Ed25519.verify` (natural-number field
arithmetic, extended-coordinate group law, SHA-512 challenge) is evaluated **by the
kernel** on the RFC 8032 TEST 1 public key, the exact signed messages (literals whose
provenance from the fixture builder is `PCS.V2.Golden.certMsg_eq` / `pkgMsg_eq`) and the
committed signature literals.

This is a *functional* statement (the verifier accepts these bytes); it is **not** a
provenance statement: the TEST 1 secret key is published in RFC 8032, so anyone can
produce such signatures and `NoForgery` is false for this key.
-/

namespace PCS.V2.GoldenCx

open PCS.V2.Witnesses.AISafetyGolden

theorem certSig_verifies : PCS.V2.Ed25519.verify testPk Lit.certMsg cxCertSig = true := by
  kernel_rfl

theorem pkgSig_verifies : PCS.V2.Ed25519.verify testPk Lit.pkgMsg cxPkgSig = true := by
  kernel_rfl

end PCS.V2.GoldenCx
