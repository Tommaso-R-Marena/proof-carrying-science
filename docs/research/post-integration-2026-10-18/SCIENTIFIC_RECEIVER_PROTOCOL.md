# Implemented receiving protocol and scope

The frozen byte grammar is `research/scientific_receiver_v1/PROTOCOL.md`.
Its initial work-in-progress note records specification-time status; the actual
implementation and new proofs are in the sibling `formal/` project. No field,
canonical encoding or bound was broadened during implementation.

The raw payload is data only. A big-endian unsigned 32-bit length precedes each
payload on stdin; Main emits one JSON line. Lengths over 8,192 reject before
reading the body and close the process. Partial headers/bodies reject and close;
EOF between frames is clean. A malformed bounded scientific payload rejects
without preventing the next bounded frame. Submitted expressions, Lean source,
proof-generation traces, verifier commands and authority choices have no wire
representation.

Successful output contains exact rational final A/B values, conserved total,
both final-coordinate bounds, reference-step count and declared unit/physical
codes. Every received bounded payload is echoed as lowercase hex. The host
compares that exact echo and all fields with an independently scanned, stepwise
rational replay. `scientific_acceptance` and `production_authority` remain false.

`decode_iff_bounded` characterizes the full typed bounded model domain. It
separates structural decoding from scientific checking: a canonical contract can
decode yet fail its environment binding, reference step, conservation declaration,
enclosure or optional finite nonnegativity request. This separation is intentional.

Unsupported domains include arbitrary reaction matrices, kinetic ODEs, PDEs,
floating-point error certification, continuous-time physical trajectories,
measured units, arbitrary expressions, causal-effect certification, inference
serving and production model promotion. New versions require separate review.
