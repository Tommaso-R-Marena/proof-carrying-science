# Compositional disclosure ledger (research only)

A truthful, individually authorized query can become unsafe after previous
answers. This executable research module maintains the exact set of worlds
consistent with the public transcript and allows a query only when **every**
possible answer leaves both values of a protected bit possible. Checking just the
actual answer cell would make denial itself a side channel.

The four-bit example has publicly known total two and protects bit zero. Queries
2,4,8 each pass a stateless privacy test. Together they reconstruct the entire
world. A single shared ledger prevents that composition. This implements known
inference-control principles; no worldwide novelty or general alignment claim.

## Proof and execution

`Ledger.lean` proves 22 theorems, including arbitrary-history invariant, exact
posterior consistency, denial independence, and adaptive public transcript
ambiguity for any planner whose input is public history. Its assumptions include
actual-world membership and a prior containing both protected-bit values. The
adaptive planner cannot receive the actual private world. Randomness can be
modeled by a fixed public seed, independent of the private world.

`Main.lean` executes the same `process` through pinned Lean 4.28.0 native code.
Five-byte frames contain version 4, little-endian 16-world possibility bitmap,
actual world, public subset query. Replies contain version, status (0 denial,
1 answer,2 invalid), posterior bitmap, answer (255 if absent). Batches are a
sequence of frames, with a short final frame rejected. The generic invariant is
kernel proved. Codec/native/compiler/OS correspondence is tested, not proved.

The authority builds fixed sources with pinned proof tools, audits exact axiom
closures, checks fresh compiled objects, seals the executable image, verifies
source/tool/artifact digests around every call, and generates ordinary `by decide`
proofs of captured request/reply pairs. It offers no caller-selected verifier.
No `native_decide`, extra axioms, or production authority changes.

The SQLite ledger commits exact native replies, generation-aware updates and
hash-chained receipts in one transaction. It replays all receipts before and
after staging and checks actual public SQL rows against the native plan. A live
memory anchor detects prefix rollback. Concurrent callers must share the same
trusted dataset namespace and ledger. A denied query still advances its receipt
generation; it does not narrow the possibilities.

## Limits

This is **possibilistic nondisclosure**, not noninterference, differential privacy,
cryptographic privacy or an accuracy guarantee. A query can change probabilities;
in the six-world example a surviving three-world class may favor a bit 2:1. Extra
side information omitted from the prior invalidates the epistemic interpretation.
The theorem covers public query and answer/denial transcripts, not timing,
process errors, private audits or termination. The private actual world and proof
literals remain visible to privileged reviewers. No zero-knowledge claim.

Python, SQLite, compilation, libraries, OS, the caller's public-only prompt
construction and the single-ledger namespace are trusted host obligations. There
is no independently administered immutable root or protected restart anchor.
Creating multiple ledgers for one dataset defeats the policy; an explicit
negative-control test demonstrates this. The constructor refuses unanchored
restart, rather than claiming durable security across host rollback. A host crash
can lose availability. Private-to-model workflows require the preceding relational
release/firewall architecture; a secret-loaded planner may encode secrets in its
query choices and is outside this contract.

## Reproduce

Activate the repository's Lean 4.28.0 and Python environment:

```sh
python -m pytest -q research/compositional_disclosure_v1/test_ledger.py
python -m research.compositional_disclosure_v1 evaluate /path/to/local-weights /tmp/fresh-campaign
python -m research.compositional_disclosure_v1 replay research/compositional_disclosure_v1/evidence/adaptive-v1.json /tmp/fresh-replay
python -m research.compositional_disclosure_v1.preservation
```

The real-weight protocol registers source hashes, pins, prompts and 96-request
budget before any completion. Two actual official Qwen3 GGUF models (0.6B and
1.7B Q8_0) are hash checked, sealed, and mapped by the pinned llama.cpp CPU engine.
Each gets six worlds × two policies × three adaptive queries plus one final guess.
Both policies receive identical public information initially; policy names and
actual worlds never enter prompts. Invalid outputs and failures are retained.
The stateless baseline intentionally resets its safety check to the initial
prior. It does not bypass Lean truth checking. Guess accuracy and deterministic
reconstruction are reported separately. No model training, held-out benchmark,
state-of-the-art model claim or production deployment.
