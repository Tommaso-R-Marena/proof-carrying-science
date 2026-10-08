import PCS.V2.Golden.Provenance
import PCS.V2.KernelRfl
import PCS.V2.SHA256Fast
import PCS.V2.GoldenCx.Spec
import PCS.V2.GoldenCx.Literals

/-!
# Provenance of the cx-fixture literals (kernel-checked)

*Counterexample archive `cx` (`PCS.V2.GoldenCx.Spec`).*  This file is a mechanical
clone of the corresponding `PCS.V2.Golden` file with the fixture `golden` replaced by `cx`;
all generic lemmas are reused from `PCS.V2.Golden`.

Every literal of `PCS.V2.Golden.Lit` is proved equal to the value the fixture builder
(`PCS.V2.Witnesses.AISafetyGolden`) computes, by kernel evaluation of the production
functions (`kernel_rfl`, i.e. the trusted kernel checks the definitional equality).
Before evaluation, two *proved* rewrites put the goal in a form the kernel evaluates
efficiently:

* `PCS.V2.Golden.jcsBytes_data` â€” the canonical bytes of a JSON value, as a byte list, are the UTF-8
  encoding of its canonical character list (this avoids the kernel's quadratic
  `ByteArray.push` loop of `List.toByteArray`);
* `PCS.V2.Golden.domainDigest_eq` â€” a domain digest is SHA-256 of that byte list.
-/

set_option autoImplicit false

namespace PCS.V2.GoldenCx

open PCS PCS.V2.Json PCS.V2.Hex PCS.V2.Domains PCS.V2.Package PCS.V2.Signature
open PCS.V2.Witnesses.AISafetyGolden PCS.V2.SHA256 PCS.V2.Index PCS.V2.CertificateModel
open PCS.V2.NormalizedWire

/-! ## Digests and member bytes -/

theorem traceDigest_eq : sha256 cx.trace.data.toList = Lit.traceDigest := by
  rw [sha256_eq_sha256Fast]; kernel_rfl

theorem semHash_eq : cx.semHash = Lit.semHash := by
  rw [FixtureSpec.semHash, PCS.V2.Golden.domainDigest_eq, sha256_eq_sha256Fast]; kernel_rfl

theorem intHash_eq : cx.intHash = Lit.intHash := by
  rw [FixtureSpec.intHash, semHash_eq, PCS.V2.Golden.domainDigest_eq, sha256_eq_sha256Fast]; kernel_rfl

/-- The certificate JSON value with its two hash members as literals. -/
theorem certJ_dÑPÐ€L@ûãM…ªì