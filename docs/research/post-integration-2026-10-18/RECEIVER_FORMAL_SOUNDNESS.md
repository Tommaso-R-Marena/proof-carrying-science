# Scientific receiver soundness

New sources are under `research/scientific_receiver_v1/formal/`. This is an
isolated research project. It neither imports submitted source code nor changes
the PCS production authority.

## Mathematical domain

A contract declares exact rationals `a₀,b₀, f₀,…,fₙ₋₁`, with `0 ≤ n ≤ 64`.
Every submitted numerator has absolute value at most `10^18`; every denominator
is positive, reduced, and at most `10^18`. Species are exactly A and B,
stoichiometry is exactly `(-1,+1)`, and conserved weights are exactly `(1,1)`.
At step k, `aₖ₊₁=aₖ−fₖ` and `bₖ₊₁=bₖ+fₖ`. There is no kinetic rate law,
real-time integrator, stochastic interpretation, or empirical chemistry claim.

The unit code is either uninterpreted common amount or declared mol. Neither
dimensional calibration nor a conversion is proved. A physical-mode request
additionally requires every received firing and every state at steps 0 through n
to be nonnegative. Algebraic mode permits signed quantities.

## Complete principal theorem statements

The source statements, rather than this mathematical paraphrase, are normative.
All names below are in namespace `PCSScientificReceiver`.

```lean
theorem verifiedWireSound (raw : List UInt8) (r : Result)
    (accepted : receive raw = some r) : ScopedScientificClaimHolds raw r

def ScopedScientificClaimHolds (raw : List UInt8) (r : Result) : Prop :=
  ∃ c, decode raw = some c ∧ encodeBytes c = raw ∧ ResultSound c r

theorem checkContract_sound (c : Contract)
    (accepted : checkContract c = true) : ContractSound c

theorem resultOfContract_sound (c : Contract)
    (accepted : checkContract c = true) :
    ResultSound c (resultOfContract c)
```

`ResultSound` asserts the returned fields equal the computed state and reference
step, `r.finalA+r.finalB=r.total`, `r.lowerA≤r.finalA≤r.upperA`, and
`r.lowerB≤r.finalB≤r.upperB`. It retains the checked contract, including
`envValue=finalState c 0`, certificate acceptance, valid box/claim endpoints,
the declared total's equality to `a₀+b₀`, and optional finite physical validity.
The complementary bounds are exactly `total−upperA` and `total−lowerA`.

The expression is receiver-fixed to `A_final`. `expression_state_of_binding`
derives its interpretation from the checked environment binding. There is no
producer-supplied `semLink` premise. The existing
`PCSIntegration.conserved_complement_enclosure` theorem supplies conservation
and numerical support; these older mathematical results are imported unchanged.
The new work discharges their semantic premise at the actual receiving boundary.

The byte theorem applies to **every** accepted byte list and result, not only a
fixture or generated corpus. Its existential contract has both successful
decoding and exact byte re-encoding. It implies no acceptance for rejected bytes.

## Codec domain

`decode_canonical` proves successful decoding implies exact re-encoding;
`decode_bounded` and `decode_supported` prove the declared bounds and structural
resource conditions. `decode_iff raw c` characterizes successful decoding as
`OperationallySupported c ∧ encodeBytes c=raw`. `CodecBounds.lean` then derives
those structural resource conditions from `bounded c=true` alone. Its general
decimal-length proof yields fields of at most 20 characters and total encoding
of at most 3,360 bytes. Consequently the strengthened complete characterization is:

```lean
theorem decode_encodeBytes_bounded (c : Contract) (hc : bounded c = true) :
    decode (encodeBytes c) = some c
theorem decode_iff_bounded (raw : List UInt8) (c : Contract) :
    decode raw = some c ↔ bounded c = true ∧ encodeBytes c = raw
```

No field-length, decoder-success or desired scientific conclusion is assumed in
the bounded-domain roundtrip theorem. The original codec is unchanged; the new
arithmetic refinement supplies its structural premises.

## Trust and proof status

The initial complete environment audit inventories 150 theorem declarations
before the additional `CodecBounds` strengthening,
including compiler-generated declarations. Every closure is a subset of
`propext`, `Classical.choice`, and `Quot.sound`. No new admission or axiom is
used. See the recorded environment statement/axiom log and qualification JSON.

The proof is about pure Lean definitions. It does not verify the Lean compiler,
interpreter, imported object provenance, byte-framing IO, JSON rendering, Python
reference, OS, signing key, source storage, or historical execution occurrence.
Those are separate assumptions, tests, or open obligations. Synthetic scientific
examples remain empirically unvalidated even when their mathematical implication
is proved.
