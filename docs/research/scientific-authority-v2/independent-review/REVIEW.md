# Independent post-PR158 security and trust review

## Review point and outcome

This review used a separate internal agent/context and a read-only view of the
implementation worktrees. It is not external laboratory validation or an
independent administrator. The audit branch starts at
`7be674df70eb3108c9dbd8b0b97f42a728bde000`.

The independently executed campaign passed **18 controls in 39.233 s**, with
stable before/after source hashes. Sixteen controls establish the expected
acceptance/refusal/recovery behavior; two deliberately demonstrate limits of
rollback resistance. Positive scientific decisions came from the actual pinned
Lean receiver. No affirmative verdict, successful verifier, witness signature or
SQLite commitment was fabricated.

At the reviewed runtime source hashes, there is no remaining blocking false-
admission or false-eligibility finding. One evidence-portability improvement was
forwarded after the campaign: retaining a complete signed checkpoint response
rather than its authenticated payload alone. Its implementation/delta qualification
belongs to the subsequent integration record, not this frozen campaign.

`actual-process-results.json` records all source hashes, fixture public roots,
operator profile identity, signed permanent receipts and individual observations.
`PREREGISTERED_CONTROLS.json` was frozen before that campaign (SHA256
`ed6fdf4576d6f8756db7247d4bbb63102045f6d2006341550e317b131a0509da`).
The earlier parser and metadata probes were exploratory and are recorded separately.
No private fixture signing key is retained in the report.

## Findings and repairs

### R1 — Unauthenticated acquisition could monopolize the serial witness

Severity: **medium availability**. The original serial HTTP service installed a
90-second socket inactivity timeout, without an absolute request-acquisition
deadline. A partial unauthenticated header blocked another connection; trickled
bytes could repeatedly refresh the inactivity timeout. TLS handshake work also
needed a deadline before request-handler setup.

The original negative-only parser probe observed the second request time out at
0.350 s and receive its ordinary HTTP response only after the first connection
closed. This finite experiment establishes head-of-line blocking; indefinite
trickle behavior follows from the original per-read timeout structure and was not
claimed as a measured infinite run. It used no store or successful authorization.

The author added an absolute five-second header/body acquisition timer and a
separately bounded TLS handshake. Independent post-repair tests confirmed that
49 continuously trickled header bytes still released the server after 4.951 s,
and a stalled TLS handshake released a second, certificate-verified TLS request
after 4.959 s. Both ran against unchanged repaired server source
`1846717e6edddaba467e73681dfd382c17a4fab02c9e19442926b4eada1ea927`.
See `slow-header-observation.json`, `availability-retest.json` and their scripts.
This limits acquisition monopolization; it is not general DoS resistance.

### R2 — Witness admission and full-audit resource domains differed

Severity: **medium accepted-domain / recovery availability**, found statically.
The early witness helper admitted a larger envelope/event-ID domain than the
whole-history auditor: an event ID longer than 256 bytes could pass witness
preflight but be outside the auditor's supported domain. A fully finalized entry
outside the mandatory audit domain could prevent eligibility and recovery.

The authors aligned the witness bounds and added prospective full-history
authentication in the coordinator before PREPARE. The repair arrived before the
independent executable probe, so this review does **not** claim to have observed
an actual bad durable commitment. The post-repair probe used a genuinely co-signed
canonical 1,799-byte envelope with a 257-byte event ID: both witness preflight and
auditor authentication rejected it. See `domain-boundary-observation.json` and
the captured `protocol-domain-review-snapshot.py`.

### R3 — Pending recovery field mismatch

Severity: **low integration functionality**, found statically. The early witness
export used `next`, while coordinator recovery expected `next_anchor`. The
schema was aligned before the successful real-process review. This was not a
false mathematical acceptance; the mismatched version would have refused by an
exception. The actual campaign did not claim to reproduce every pending crash
window; the author's crash matrix is separate evidence.

### R4 — Snapshot checkpoint payload was not standalone signed evidence

Severity: **low evidence portability**. The reviewed WitnessClient verified the
nonce-bound signed response before returning its payload, and coordinator
eligibility checked that fresh result. However, the snapshot retained only the
payload. A third party receiving that snapshot alone could not independently
replay the missing response signature/nonce.

Runtime eligibility was still checked; this is not a demonstrated false eligible
snapshot. The parent accepted the recommendation to retain the full signed
checkpoint response via an atomic evidence API. Qualification of that subsequent
delta must be recorded separately. Even a retained signed challenge response does
not establish currentness for a later third party: that party needs its own fresh
challenge or another explicit freshness policy.

## Independently executed actual-process controls

The campaign launched the real witness CLI in another process, with a new SQLite
store, two distinct signed-intent keys and a third distinct witness key. The child
received an explicit minimal environment, not inherited cloud authorization
variables. Its operator profile additionally pinned the reviewed witness,
historical-auditor and coordinator Python source files. Lean dependencies used
the already qualified, source-identical read-only import cache; this was not a
fresh dependency rebuild or complete loader/OS attestation.

The controls establish:

- Actual checked genesis can initialize the witness and authority.
- PREPARED-only state is not eligible; a conflicting reservation is rejected.
- The witness can finalize its own commitment without observing any producer
  SQLite commitment, but the producer's old local state remains ineligible.
- Exact signed material retained by the witness can reconstruct that local state
  without creating a new authorization. The exact rational result remains bound
  to the candidate bytes (the transfer example's final A is 13/2).
- A genuinely co-signed false scientific environment is refused without changing
  the witness database, checkpoint or pending state.
- Whole producer-store rollback is rejected by both a live authority and a
  reopened authority when witness state continuity remains intact.
- Exact witness-history reconstruction repairs that producer rollback.
- Wrong receiver-pinned witness key, cross-root checkpoint transplantation,
  wrong nonce and signature-role confusion are refused.

These are finite controls, not a general Python/SQLite/cryptographic refinement
proof. The experiment exercises process execution and logical COMMIT behavior;
it does not test power loss or physical storage flush correctness.

## Preserved counterexamples

**Witness-store rollback under the unchanged signing key/root.** After restoring
the witness's old genesis database and restarting its real service with the same
key and root, a fresh stateless client authenticated a nonce-fresh old checkpoint.
The key authenticates the speaker, not continuity of its deleted durable state.
This violates the honest durable-witness continuity assumption and is outside the
producer-only rollback protection.

**Simultaneous producer and witness store rollback.** With both stores restored
to genesis, no separately retained latest monotonic checkpoint, and the same
trusted keys/root, the reopened authority accepted the old eligible world. This
is a useful concrete limit even without replacing public keys. It must never be
reported as unconditional rollback resistance. See the two `counterexample:true`
observations in `actual-process-results.json`.

An independently administered witness with uncompromised durable continuity
would prevent the producer from performing that second rollback. The present
host experiment does not establish such administration.

## Administration and platform observations

Actual probes show UID/EUID/GID 1000, no effective capabilities, no `sudo`, and no
`newuidmap`/`newgidmap` helpers. `unshare -Ur` succeeds, but namespace UID 0 maps
only to outer UID 1000. Switching to unmapped UID 65534 fails with EINVAL. The
namespace's apparent root identity therefore does not establish a distinct
storage/key owner. A separate same-UID process can read a fresh fixture key in a
0700 directory with mode0600; no key material was printed.

Profile A is demonstrated (separate process, same administrator). Real distinct
outer-principal Profile B is **BLOCKED_TECHNICAL** under the available setup.
Profile C is **BLOCKED_EXTERNAL**: no independently controlled administrator,
host or protected key/bootstrap was supplied. No production credential, host
configuration, paid infrastructure or deployment was changed. See
`principal-observations.json` and `principal_probe.py`.

## Formal and source-boundary review

The new rejecting pure auditor checks genesis and every supplied envelope rather
than silently dropping rejected entries. Its success theorem derives complete
scientific history validity without assuming it as an opaque initial premise.
The witness theorem concerns one honest serial state's prepare/finalize trace;
clones, compromised keys and rolled-back durable state are outside that model.
Serving requires finalized/pending-free witness state equal to local state. The
pure recovery function checks an actual complete archive and rejects pending
state; runtime explicit pending resolution must correspond to the protocol
transitions followed by that finalized recovery case.

Pure `State` equality is stronger than a runtime hash commitment by itself.
Cryptographic collision resistance, exact encoding, SQLite/OS execution,
source-to-object correspondence and the Python-to-Lean transition relation remain
explicit obligations. The formal empirical-predicate and root-substitution
fixtures are logical countermodels, not empirical studies or cryptographic
breaks. This security review examined the statements/source read-only; it does
not impersonate the formal workstream's kernel build or axiom audit.

Independently compared **961 old Git blob/mode entries** under production formal,
scientific receiver, authorization history and V1 join scopes in each of the
three implementation worktrees against pinned PR158. All matched. See
`old-source-preservation.json`. This is source preservation, not loaded-object
or compiler correctness.

## Prior art and publication assessment

Actual primary material reviewed:

- [RFC9162](https://www.rfc-editor.org/rfc/rfc9162), especially Merkle consistency
  proofs and the security discussion of cross-client signed-tree-head comparison.
  A proof relates supplied roots; detection of a log presenting inconsistent
  views needs additional observation/comparison. A single hash chain does not
  provide global non-equivocation against its compromised operator.
- Gray and Lamport, [Consensus on Transaction Commit](https://www.microsoft.com/en-us/research/publication/consensus-on-transaction-commit/), DOI
  `10.1145/1132863.1132867`: primary PDF abstract, introduction and section3.3.
  Stable-state assumptions and the blocking behavior of staged commit under
  coordinator failure are established prior art. PCS's eligibility gate is not
  a new consensus protocol or a distributed atomic transaction theorem.

Crossref metadata also confirmed Necula's proof-carrying-code paper and Verdi;
those metadata checks are not a full-paper comparison. Source URLs, exact hashes,
read scope and local caches are in `prior-art-metadata.json`; copyrighted PDFs
were not copied into the repository.

The defensible research contribution is the reproducible composition of a
narrow verified scientific interpretation, full retrospective history replay,
authenticated staged witnessing and explicit failure/counterexample evidence.
This review establishes no priority claim, broad novelty, external scientific
adoption, empirical validity, Byzantine consensus or independently administered
production security.

## Reproduction

From this audit checkout, with the three implementation worktrees at the recorded
source hashes and the qualified Lean4.28.0 fixture environment available:

```sh
/workspace/.onboarding/pcs-integration-env/bin/python docs/research/scientific-authority-v2/independent-review/actual_process_review.py
/workspace/.onboarding/pcs-integration-env/bin/python docs/research/scientific-authority-v2/independent-review/availability_retest.py
/workspace/.onboarding/pcs-integration-env/bin/python docs/research/scientific-authority-v2/independent-review/domain_boundary_probe.py
/workspace/.onboarding/pcs-integration-env/bin/python docs/research/scientific-authority-v2/independent-review/principal_probe.py
```

The scripts use disposable local fixtures and never edit reviewed implementation
sources. Preserve existing reports before rerunning: these fixed filenames are
for the captured review campaign, not an append-only evidence service.
