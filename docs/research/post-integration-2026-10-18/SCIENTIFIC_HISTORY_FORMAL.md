# Exact scientific receiving joined to serial authorization history

This isolated wrapper joins the unchanged scientific byte receiver and unchanged
history CAS. It changes no production authority, mathematical predecessor,
scientific protocol, signer policy or runtime Main. The combined source baseline
is `cb9f496`; the new library is `PCSScientificHistoryV1` in
`research/scientific_history_v1/formal`.

A candidate is the entire canonical `PCS-SCI-BOUND-V1` bundle: its declared model,
initial state, schedule and numerical claim. `scientificTransition` requires the
receiver-pinned root policy to equal the exact 18 ASCII bytes
`PCS-SCI-HISTORY-V1`, and requires the signed payload's auxiliary `certificate`
field to be empty. It then executes the actual pure
`PCSScientificReceiver.receive` on the exact signed candidate. A scientific
failure returns the original state and no result. Only a successful scientific
result followed by the existing history transition's acceptance commits.
`Root.checker` remains the existing abstract pinned identity. A runtime may
restrict it to a 32-byte configuration SHA-256; this proof does not postulate
that a digest identifies a correct checker implementation. Authority/witness key
identities are likewise opaque byte lists here, with no formal length or
nonempty-key constructor requirement; runtime key validation is a separate boundary.

`accepted_sound` has only an actual wrapper acceptance hypothesis. It establishes
`ScopedScientificClaimHolds` for the exact signed candidate and returned result,
existing history acceptance and pinned authority/witness/policy/checker scope,
exact committed incumbent bytes, exact `old.history ++ [envelope]`, and generation
`old.generation + 1`. It introduces no free decoder, certificate, expression/state
or candidate-science premise. The existing receiving theorem discharges the
scientific mathematics. `accepted_authenticated` adds only an explicitly stated
signature-verifier soundness premise for the chosen authentication predicate;
it does not prove cryptography from a hash.

Rejection theorems retain the entire old state for a wrong root policy, nonempty
auxiliary certificate, malformed candidate, false scientific receiving decision,
failed history CAS, or authority/witness verification failure. An accepted event
cannot replay after any later request trace on this fixed serial root/state.
The wrapper preserves the previous history's authentication and link invariants
when those invariants hold initially.

The history boundary is deliberate. `run_scientific` requires both an initially
scientific history and a checked initial incumbent; it then preserves both.
`initial_run_scientific` uses an empty genesis history and requires only that the
genesis incumbent already passes the scientific receiver. New candidates always
receive an actual scientific check, without an assumption about their validity.
For an arbitrary preexisting history, signatures and pinned policy/checker labels
alone do **not** establish that older entries passed science. The wrapper does
not replay those older candidates. A runtime check of the current incumbent does
not fill that older-history gap.

Each bundle declares its own scientific subject. These are per-subject exact
mathematical claims; the join proves no fixed-problem improvement, neural
no-forgetting, cross-policy capability preservation, empirical adequacy or
kinetic truth. It also proves no Python/Lean refinement, event-byte codec,
Ed25519 implementation correctness, filesystem crash safety, protected-root
integrity, rollback resistance after root substitution, replica consensus or
recovery liveness.

Fixtures contain one checked nontrivial A-to-B transition with a nonsingleton
interval, plus malformed, valid-but-false-total, reserved-certificate and missing
witness controls. Signature verification in these Lean fixtures is an explicitly
symbolic finite allowlist. Scientific acceptance uses the real pure receiver;
there is no substituted affirmative scientific verifier.

Run a normal pinned Lake build with:

```sh
python research/scientific_history_v1/check_formal.py --lean /absolute/lean
```

The explicit local profile uses existing read-only caches and checks source
identity, all nine Git dependency revisions, exact qualified receiver artifact
identities, every new theorem's actual axiom closure, and unchanged new sources:

```sh
python research/scientific_history_v1/check_formal.py \
  --lean /workspace/.onboarding/tools/lean-4.28.0-linux/bin/lean \
  --dependency-checkout /workspace/pcs-all-prs-integration-20261018 \
  --receiver-qualification /workspace/.onboarding/receiver-final-qualified-profile-v3 \
  --history-checkout /workspace/pcs-authenticated-history-v1
```

Only this new project's `.lake/build` receives output. This is a fresh check of
all new join proofs against source-identical prebuilt imports, not a fresh
rebuild of every dependency. Git, qualification evidence, cached object/source
correspondence, the Lean kernel/compiler/runtime and the host remain trusted.
`formal-report.json` and `statements-and-axioms.log` preserve the exact source
hashes and actual queried theorem closures. No production merge or deployment
is authorized by this work.

Local fresh checking passed all **23 authored theorems** and **42 declarations
including generated theorems**. Every queried axiom closure is a subset of
`propext`, `Classical.choice`, `Quot.sound`; several proofs have smaller closures.
The dedicated `PCS Scientific History Join` workflow defines a normal pinned Lake
build and full closure audit. This workflow definition has not itself been
reported as an executed hosted success. Runtime join tests are a separate step
owned by the receiving integration workstream.
