# Scientific receiving ledger v1 integration contract

This research join is based on the explicitly stacked validation head
`cb9f4960cb7edbcc7c7ff92e96668d835646b4a1`. It leaves the scientific
receiver, authenticated-history implementation, production authority and their
existing formal statements unchanged.

## Admission contract

The signed envelope's candidate is the entire canonical `PCS-SCI-BOUND-V1`
bundle. Its auxiliary certificate must be empty. The receiver-owned root policy
is exactly the ASCII bytes `PCS-SCI-HISTORY-V1`; its checker identity is the raw
32-byte SHA-256 of the existing host's canonical operator-configuration identity.
Neither identity is supplied by the admission request.

Admission first executes the actual scientific receiver on the captured candidate
bytes under the fixed operator configuration. It then submits the same captured
signed envelope bytes to the existing authenticated history's transactional
compare-and-swap append. A stale generation, changed incumbent or predecessor,
bad signature, invalid scientific input or verifier failure must prevent a new
snapshot. The history append remains the commitment linearization point.

An admitted snapshot captures the exact candidate bytes, their digest, the
checked mathematical result and the committed external-anchor value. Reading
the snapshot does not reopen a mutable candidate path. Restart independently
checks the current incumbent again; checkpoint publication and explicit crash
recovery remain operator duties.

## Formal and runtime claims

The new pure Lean transition calls the existing scientific `receive` and existing
history transition. A successful result must imply scientific soundness of the
exact signed candidate, exact committed incumbent, append-only history and a
one-step generation increase. Signature authenticity remains conditional on the
explicit signature-verification soundness assumption. No cryptographic,
compiler, SQLite or Python implementation-refinement axiom is added.

Every newly accepted transition checks its own candidate without assuming that
older entries were scientifically checked. A theorem about scientific validity
of an entire trace must explicitly require scientific validity of its initial
history. Runtime startup rechecks the current incumbent only. Correctly signed
older entries alone do not establish their mathematical validity, historical
occurrence or full-history scientific audit.

## Scope and exclusions

This is artifact admission for a narrowly specified scientific computation.
Each bundle declares its own initial state, schedule and claim. No fixed-problem
preservation, model improvement, inference-service promotion, empirical validity
or production authority follows. Scientific-acceptance, production-authority
and promotion-authority flags remain false.

The constructor receives trusted operator configuration, root and external
checkpoint. Local files, ordinary hashes, Python object attributes, process
separation and SQLite transactions do not establish an independently protected
root. Replacing the database and its purported external checkpoint together is
still outside the demonstrated protection. The runtime/formal correspondence
and source-to-executable correspondence remain independently testable obligations.
