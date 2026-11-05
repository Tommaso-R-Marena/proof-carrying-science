import PCS.V2.Witnesses.AISafetyGolden

/-!
# Counterexample archive: an uncertified check tag over an unsafe trace

`cx` is the golden fixture with two changes: the committed trace is `[0, 1, 2, 4, 1, 7]`
(it takes the forbidden action `7`), and the evidence item `E1` declares the **unregistered**
`check_spec.type = "trace_invariant_v2"`.  The certificate claim `C1` still carries the
predicate `{"kind": "ai.trace_invariant", "budget": 4, "forbidden": 7,
"trace_artifact": "trace"}`.  The archive is consistently built and signed with the
RFC 8032 TEST 1 key (signatures stored as literals, produced once by the untrusted signer).

Its transcript reports `PASS` for `E1`.  Because no certified checker handles the tag, the
executable's replay executor falls back to that report.  The files in this directory prove,
in the kernel, that the executable accepts this archive, so its claim predicate is false of
the committed bytes (`PCS.V2.GoldenCx.Counterexample`).
-/

set_option autoImplicit false

namespace PCS.V2.GoldenCx

open PCS.V2.Witnesses.AISafetyGolden

/-- The counterexample fixture specification. -/
def cx : FixtureSpec := { trace := ⟨#[0, 1, 2, 4, 1, 7]⟩, checkTag := "trace_invariant_v2" }

/-- Certificate signature (literal; produced once by `cx.genCertSig`). -/
def cxCertSig : List UInt8 :=
  hx ("7466a41c9f4e931150d614a84254632cfc544f3bd99f218689010f72a184c384" ++
      "00380c46af34c691d317703ce48018a17f11b2965052edb7959440177ceca50d")

/-- Package signature (literal; produced once by `cx.genPkgSig`). -/
def cxPkgSig : List UInt8 :=
  hx ("720f22c17361d956773900d4c218ebfc9ac7349a4c75b93a6aed7a6d1687f2b2" ++
      "12aa519ddece7daa1b13e77d54f7e76c200d903fe74af3a881a401a2146f4508")

/-- The archive members, in canonical order. -/
def cxEntries : List (String × ByteArray) := cx.entriesWith cxCertSig cxPkgSig

/-- The raw canonical ZIP bytes of the counterexample archive. -/
def cxRaw : ByteArray := ⟨(PCS.V2.Zip.encodeZip cxEntries).toArray⟩

/-- Its transcript: binds the certificate semantic hash and reports `PASS` for `E1`. -/
def cxTranscript : PCS.V2.Authority.AuthorityTranscript := cx.transcript

end PCS.V2.GoldenCx
