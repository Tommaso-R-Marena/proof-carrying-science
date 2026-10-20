# Complete retrospective scientific history replay

## Implemented result

The new `research/scientific_history_v2` namespace rechecks the root-bound genesis
and every retained candidate through the actual fixed scientific receiver. It
does not modify the V1 ledger or infer old scientific validity from the current
incumbent. Its application-source baseline is
`020b8c4d6be81bc49c23fabf862ed9e0ba14b1c8`, based on PR158 at
`7be674df70eb3108c9dbd8b0b97f42a728bde000`.

The actual final suite passes **17 tests, zero failures/errors/skips**, in
28.738 seconds. The earlier overlapping 16-test run passed in 23.988 seconds;
it is preserved separately. An initial nine-test development preflight run is
retained but is not final qualification: its dummy final checkpoint could make
some authorization negatives vacuous. Before the 16/17-test runs, those fixtures
were strengthened to use the exact checkpoint that would result if the disputed
check were omitted. These counts are separate executions, not additive evidence.

The frozen cold-replay manifest SHA256 is
`e3a2f9e8fdbb21c4a35bbde1ba455f288ff5580611c663e83daf3235dc95ffc9`.
It was committed before the benchmark ran. Positive benchmark cases and the
new bad-old/valid-current negative control used actual Lean and real signatures.

## API and admission scope

```python
audit_history(path, root, anchor, config, *, budget=AuditBudget())
audit_material(root, anchor, tuple_of_exact_envelope_bytes, config, *, budget=...)
verify_artifact(raw, root, config)
```

The root, exact external anchor and frozen `OperatorConfig` are explicit
receiver-owned bootstrap inputs. They must not be copied from an untrusted
export and treated as self-authenticating. Root policy is exactly the existing
`PCS-SCI-HISTORY-V1`; checker identity must equal SHA256 of the canonical fixed
operator configuration. Policy/checker upgrades and key rotations are unsupported
and rejected. Requests cannot supply a verifier callback or a positive cache.

The complete material path authenticates each canonical V1 envelope and both
Ed25519 intent signatures, scope, expected generation/incumbent, predecessor
digest, event freshness, and final exact checkpoint. It requires empty auxiliary
certificate bytes. It then actually checks genesis and **every** candidate in
order. Each check verifies the fresh host receipt signature under that service's
ephemeral key, raw bytes/digest/length, exact operator identity, successful
before/after source/dependency checks and exact response/result binding.

The numerical result is frozen into `Fraction` values and boolean/natural
declaration metadata. The report retains exact scientific bytes, response bytes,
their digests and the host receipt digest. The digest is provenance only: this
report is not a complete archive of each ephemeral host receipt. Independent
mathematical replay reexecutes the exact retained artifact bytes.

`audit_history` additionally uses the unchanged V1 `History.snapshot()` before
and after scientific replay. A changed, corrupt or ahead store fails rather than
returning a complete successful audit. No database is created on a missing path.
The portable material API needs no database and validates the same exact chain.
Authentication failures may propagate V1 `history.Rejected`; scientific and new
resource/scope failures use `AuditRejected`. Both are fail-closed `ValueError`s.

`AuditReport` is a frozen value containing the root/config identities, final
anchor, exact envelope digests and genesis-plus-candidate results. Its
`historical_math_valid` property means **retrospective** mathematical replay.
`as_dict()` reports separate dimensions:

- `retrospective_mathematical_validity = EXECUTED_PASS`;
- `authorization_history = AUTHENTICATED` under the externally supplied keys;
- `historically_authenticated_verification = UNVERIFIED`;
- `empirical_validity = UNVERIFIED`;
- `scientific_acceptance = false`, `production_authority = false`.

The old event-class string `model-promotion-authorization` is retained only for
V1 serialization compatibility. No neural promotion or scientific improvement
follows. Each artifact declares its own initial conditions/schedule/claim; this
audit does not establish that a sequence is one continuous physical trajectory.

## Mathematical and historical interpretation

Every actual accepted scientific wire is within the existing receiver's exact
rational, bounded, discrete A→B domain. Under the pinned executable's
correspondence to `PCSScientificReceiver.receive`, its existing
`verifiedWireSound` theorem explains canonical decoding, the receiver-derived
expression/state link, conservation and A/B enclosures. Physical mode means the
existing finite nonnegativity checks, not validated kinetics or empirical truth.

This Python workstream does **not** add a Lean theorem or prove Python/JSON/IO/
Ed25519/SQLite/compiler refinement. The integration's new pure trace proof is
separately audited. Lean `--run` evaluates compiled IR; it is not a fresh kernel
proof of each runtime result. The operator/compiler/import/OS assumptions remain.

Mathematical rerun today does not prove that a verifier ran when an event was
originally committed. The existing two signatures authenticate intent. Historical
verification occurrence needs additional independently trusted post-verification
witness evidence, checked separately by the witness/coordinator workstreams.
This auditor never upgrades that dimension from a successful rerun alone.

## Negative controls

The suite authenticates genuinely signed invalid old science followed by a valid
current artifact, then rejects complete scientific replay. Invalid genesis also
rejects with an empty event list. Corruption of the database after both actual
scientific checks complete causes the final exact re-audit to reject.

Other controls reject missing/reordered/duplicated events, wrong final anchors,
wrong root/key/policy/checker/generation, changed candidate bytes with old
signatures, nonempty auxiliary certificates, truncated/noncanonical encodings,
mutable material, byte/event budgets, missing actual verifier, changed source
pins, missing/corrupt stores and attempted positive-cache/callback substitution.
Preflight-negative tests explicitly forbid verifier launch; they do not mock a
positive mathematical verdict. The live-database fault wraps actual checks,
preserves their genuine results, then injects only a negative storage fault.

## Resource model and progress

Defaults/hard maxima are 32 events, 8,192 scientific bytes per artifact, 262,144
aggregate scientific bytes, 1,048,576 aggregate envelope bytes, 40,000 bytes per
envelope and 256 bytes per event/genesis identifier. Metadata and all signatures
are checked before scientific work. No untrusted cache can skip a check.

The path adapter first invokes the inherited V1 snapshot, whose coarser ceilings
are 1,024 events and 64 MiB retained envelope data (128 MiB database/sidecars),
before imposing the narrower scientific replay domain. Its temporary decode cost
is governed by those inherited bounds, not by the new 1 MiB accepted domain.

The default whole-audit elapsed **acceptance** budget is 300 seconds, capped at
600. It is checked around authentication/science and after the final database
audit. A report cannot succeed after its budget. This is not a hard preemptive
availability guarantee: inherited host pin-file I/O lies outside the child
process timeout. OS/storage hangs and compromised host execution remain outside
the model; per-child execution retains the fixed operator deadline and output
bounds. The audit never changes timeout mid-history to silently change checker
identity.

`audit_material_events` streams deterministic indexed checked-prefix observations.
Each carries `complete_history=False`; only the final `AuditReport` is complete.
Stopping early cannot yield a complete audit. There is no authenticated
incremental cache. Resume explicitly restarts at checked genesis, so an untrusted
progress file cannot bypass prior science.

## Executed cold replay measurements

| Events | Actual artifact checks including genesis | Wall seconds | Scientific bytes |
| --- | --- | --- | --- |
| 0 | 1 | 3.414 | 79 |
| 1 | 2 | 6.107 | 162 |
| 8 | 9 | 28.396 | 727 |
| 32 | 33 | 86.468 | 2,671 |

All four cases passed. A fresh invalid-old/valid-current benchmark then rejected
with the database unchanged. Authentication-only replay of 32 events took
0.0281 seconds. Maximum observed child peak RSS was 2,924,608 KiB using Linux
`RUSAGE_CHILDREN`; it is not simultaneous aggregate RSS. These are single
startup-dominated observations under a shared host, with no OS-page-cache flush
or controlled isolation. “Cold” means no scientific verdict cache. No asymptotic
scaling or speedup claim follows, and these short fixtures do not benchmark the
largest accepted operand schedule. The benchmark uses a partial fixture pin
inventory, not full loader/root attestation.

## Reproduction and historical profile identities

From the repository root, after preparing the actual qualified Lean 4.28.0
environment and hash-pinned Python dependencies:

```sh
python -m unittest research.scientific_history_v2.tests.test_audit -v
python -m research.scientific_history_v2.benchmark --out /new/replay-evidence
python -m research.scientific_history_v2.cli \
  --root /trusted/root.json --anchor /trusted/anchor.json \
  --operator-config /trusted/operator-config.json \
  --material /retained/material.json --report /new/full-audit.json
```

The CLI also accepts `--history /retained/history.sqlite` in place of material.
Runtime and file-descriptor tests are Linux/POSIX; Windows behavior is not tested.
It strictly reads bounded canonical root/checkpoint files and creates report
outputs exclusively, preserving historical evidence. Public fixture keys/root,
exact signed material, configured profile, all numerical results and commands
are retained in `research/scientific_history_v2/reports/`, with hashes indexed by
`EVIDENCE_INDEX.json`. Private signing keys are never retained.

The existing checker identity includes absolute command/source/import paths,
cwd and environment-value digests. Replaying an existing signed root on another
machine therefore requires reproducing its reviewed profile/layout, not silently
substituting source-identical files at different paths. Fresh reproduction may
create its own reviewed profile and root/keys. Historical-profile migration is
not implemented. The fixture bootstrap is public research data, not proof of an
independently administered external identity.

Final source/application identities and executed counts are in
`research/scientific_history_v2/reports/qualification.json`. Existing V1 source
files, theorem statements, historical evidence and production authority remain
unchanged. This workstream is ready for separate review/integration; independently
administered witnessing and external empirical validation remain unestablished.
