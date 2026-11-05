# Canonical scientific codec audit

The normative wire specification is
`research/scientific_receiver_v1/PROTOCOL.md`. The protocol is fixed ASCII
`PCS-SCI-BOUND-V1`, followed by 31+2n canonical integer fields. Fourteen header
integers pin policy, A→B model, species, matrix, weights, expression, reference
step, unit/physical modes, and explicit assumption/limitation declarations.
Eight reduced rational pairs and an exact firing count precede the firing pairs.

The receiver rejects non-ASCII bytes, extra delimiters/fields, whitespace,
newlines, signs other than canonical negative integers, negative zero, leading
zeros, unknown versions/policies, nonpositive denominators and nonreduced
rationals. Zero is exactly `0|1`. Fields are limited to 20 ASCII characters,
raw payloads to 8,192 bytes and schedules to 64 firings. Main rejects an
oversize frame before body allocation; a u32 big-endian framing header is not
part of the proved scientific wire codec.

The transparent decimal codec from `PCS.V2.ProofGatedCodec` and ASCII helpers from
`PCS.V2.ProofGatedBytes` are reused without source changes. The new rational,
scientific-header, list/count and byte mappings are proved in `Codec.lean`.
Canonicality includes an explicit re-encoding check. Independent encoder
roundtrip and a literal nontrivial accepted wire prevent this from being a
vacuous accept-nothing claim.

The Python producer computes a proposed final value directly from a firing sum.
The independent reference manually scans integers and replays every transition;
it imports neither the producer nor Lean decoding decisions. Actual Lean
differential tests compare exact received-byte echoes and all rational result
fields, not merely a Boolean. A consistently changed input may correctly accept
with a changed result; mutation itself is not an intrinsic rejection reason.

No future Aristotle codec snapshot is assumed present. Existing protected formal
sources are unchanged. A future serialization version requires its own complete
refinement and differential qualification; this protocol does not silently
accept a broader grammar to accommodate it.
