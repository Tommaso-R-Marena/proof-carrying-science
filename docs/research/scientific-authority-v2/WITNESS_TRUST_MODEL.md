# Witness trust and falsification boundaries

The implementation executes actual Lean at genesis and prepare, verifies real
Ed25519 signatures, persists real SQLite transactions and provides a separate
server process. These establish functional, explicitly scoped research results.
They do not establish an independently administered witness in this environment.

**Profile A:** local processes and distinct real keys, one host/administrator.
The producer's administrator may be able to read or replace witness keys/store.
Python privacy/freezing, POSIX permissions, hashes and separate PIDs do not
prevent that administrator. The actual subprocess demonstration is this profile.

**Profile B:** reference deployment under distinct OS users and protected storage
can reduce ordinary-user write/key access. This work's portable commands describe
that setup; only separately recorded actual principal tests can count as executed.
It still trusts host root, kernel and storage. No document silently upgrades A to B.

**Profile C:** an external independently administered witness needs a distinct
operator/host, protected key/store, receiver-authenticated public-key bootstrap,
fixed verifier configuration and independently retained checkpoints. This remains
blocked on external administrative infrastructure; deployable software alone is
not its demonstration.

The security property assumes an honest witness and continuity of its durable
state, pinned receiver root/key/configuration, Ed25519 authenticity, SHA256
collision resistance and honest Python/compiler/OS/SQLite execution. The pure
Lean model does not verify those implementations. Before/after artifact pins
also do not exclude transient substitution or dishonest loading. The current
witness runtime test fixture pins a partial inventory, labeled as such.

Under these assumptions a fresh challenge reveals witness state independent of a
rolled-back producer database. Exact signed intent and a successful mathematical
check are required before witness preparation. Only that prepared successor can
finalize; no conflicting successor finalizes from that same honest serial state.
Signatures on intent mean authorization for consideration; signatures on witness
statements attest this witness's scoped verification/commitment observation.
Historical occurrence is conditional on witness honesty and protected bootstrap,
not a theorem inferred from a raw hash or retrospective mathematical replay.

Preserved counterexamples: if the witness's own database is restored to a prior
valid snapshot with the same signing key, its only monotonic memory is gone and
it can sign an old fresh-nonce view. If the receiver also replaces all trusted
root/key material, an entirely substituted world authenticates against that new
bootstrap. Compromised keys or separately forked witness copies can equivocate;
a single serial honest-witness theorem does not establish Byzantine consensus.

Independent review found an unauthenticated slow-header availability attack in
the initial serial HTTP implementation: a per-read idle timeout could be reset
indefinitely and TLS handshake occurred before handler protection. The repair
uses absolute acquisition deadlines and explicitly bounds handshake before
handler creation. Negative transport controls do not invoke a mock scientific
verifier. Authenticated work can still consume bounded verification time and
serial capacity; global availability remains an open obligation.

Separate scientific-history replay establishes retrospective correctness of every
retained artifact under the pinned current interpretation. It does not prove an
honest verifier historically checked the bytes, absent the additional trusted
witness-attestation assumptions. The witness reconstructs and authenticates its
retained signed chain at startup; it rechecks genesis, not all old science. A
whole-history auditor performs that separate stronger mathematical replay.
