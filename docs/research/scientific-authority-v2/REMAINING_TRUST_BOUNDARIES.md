# Established boundaries, negative results and release decision

## What the proofs cover

The original byte receiver's universal soundness theorem remains unchanged. The
new typed trace auditor calls that exact receiver on genesis and every candidate,
rejects a rejected suffix rather than silently skipping it, and derives exact
history/final-artifact/scientific properties. The witness/serving proofs close
their invariants from actual checked initialization and an honest action trace.
Pure signature semantics remain an explicit soundness hypothesis where needed.

Bare structural state equality is insufficient for science: independent kernel
controls exhibit an uninitialized equal state that serves, and a forged unsound
pending record that bare finalization accepts. These do not refute the closed
initialized-trace theorem. They show why its initialization, pending soundness
and state-continuity conditions cannot be discarded. Cloned valid witnesses can
finalize different descendants; one retained honest serial state rejects them.

## What actual execution adds and assumes

The runtime uses real Lean4.28.0 compiled IR via `lean --run`, real cryptography
Ed25519, exact bytes/results, SQLite transactions and real HTTP/TLS processes.
Currentness uses receiver-created nonce challenges, not stale permanent receipts.
Snapshots retain the full verified signed response; a later auditor still needs
its own challenge. Full-history mathematics is retrospective, not proof that the
original author performed verification at the historical time.

Witness post-verification statements authenticate what the witness asserts it
observed/committed. Inferring actual historical verification occurrence requires
an honest witness, trusted key/bootstrap and durable state continuity. Same-host
fixture keys do not establish independent administration. Source/profile hashes
do not establish cryptographic signer identity, immutable execution or physical
storage durability.

Neither Python/JSON/crypto/SQLite-to-Lean refinement nor compiler/OS correctness
is proved. Pure full-state equality is stronger than a hash equality without
collision-resistance/encoding assumptions. File pins do not exclude transient
replacement, malicious loaders or same-UID/root compromise. Host process-group
cleanup is not a complete sandbox against arbitrary hostile processes. The data-
only supported Lean receiver does not accept arbitrary user code.

## Preserved falsifications

The independently executed campaign contains two important accepted old-world
counterexamples. Rolling back the witness database while retaining its signing
key can produce a nonce-fresh authenticated old checkpoint. Rolling back both
stores after losing the only latest monotonic evidence can reopen an eligible
old state. A public key authenticates a principal, not persistence of its deleted
history. The prototype's producer-only rollback detection assumes the witness
and independently pinned root/checkpoint continuity remain uncompromised.

This is not Byzantine consensus, globally non-equivocating transparency, or an
atomic distributed commit. An honest fixed witness safely blocks conflicting
pending descendants; unavailable witnesses and ambiguous recovery can halt
progress. Process termination tests do not establish power-loss durability.

## Ranked open obligations

1. Independently administered witness/key/storage with externally retained latest
   checkpoints and rollback/equivocation observation. Profile C is unavailable;
   no paid infrastructure, credential rotation or deployment was attempted.
2. Restricted executable/encoding refinement, actual loaded-object attestation,
   cryptographic implementation and storage guarantees. Existing differential
   and process tests are evidence, not these proofs.
3. Liveness and performance under slow storage, adversarial load, service loss,
   interrupted publication and true power failure. Deadlines/resources bound
   specified operations; they are not general DoS resistance.
4. Scientifically broader models, units/kinetics/ODE/float/GPU semantics and real
   empirical applicability. Current examples are synthetic and narrow.
5. Authorized version/key transitions and portable historical profile mapping.
   Unsupported rotations reject rather than silently change authority.
6. Authoritative missing Aristotle V8 and external research adoption remain open.
   No stale proof snapshot or proof-generation trace was integrated/trained here.

## Release and publication decision

The work is suitable for research reproduction and independent formal/security
review after final exact-tree CI. It grants no production authority, model
promotion or empirical scientific acceptance. All predecessor files/modes remain
unchanged and all drafts remain unmerged.

The defensible publication candidate is reproducible composition of a narrowly
verified scientific interpretation, complete retrospective replay, authenticated
staged witnessing and explicit crash/rollback counterexamples. RFC9162 already
distinguishes consistency proofs from cross-observer misbehavior detection;
Gray/Lamport transaction-commit work supplies established durability/blocking
context. This is not a novel consensus algorithm. Primary read scope and further
PCC/Verdi metadata are recorded in the independent prior-art report. Priority,
external validation and broad novelty have not been established.

The next highest-value milestone is a genuinely separate witness operator with
independently retained/public latest checkpoints, followed by adversarial producer
and witness rollback/fork experiments across that administrative boundary.
