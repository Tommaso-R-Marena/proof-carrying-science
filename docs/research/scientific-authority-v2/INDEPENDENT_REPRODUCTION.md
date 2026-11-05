# Reproduce the research system without trusting producer assertions

## Profiles and prerequisites

The automated demonstration is Profile A: real separate services/processes and
three distinct fixture key roles, but one administrator and host. No independently
administered witness is claimed. Profile B cannot currently be exercised: namespace
UID0 maps only to outer UID1000 and no usable distinct-UID mapping helper exists.
Profile C needs an external operator who controls the witness key/storage and
authenticated bootstrap separately from the producer. See the measured probes
and bootstrap instructions in the witness and independent-review reports.

Use Python3.12.14, Lean4.28.0, the repository's nine pinned Git dependencies and
hash-pinned Python requirements. No GPU, paid service or production credentials
are required. Check out the final integration commit recorded in the PR/handoff.
Local qualification used read-only source-checked dependency caches, not a fresh
rebuild of every Mathlib object. The hosted workflow performs standalone Lake
builds of the new project and fresh receiver qualification.

## Build and inspect

From the repository root:

```sh
python -m pip install --require-hashes -r requirements-dev.lock
python -m pip install --no-deps --no-build-isolation -e .
source scripts/activate_lean_428.sh
lake exe cache get
for project in incubation/pcs_certified_numerics_v1 incubation/pcs_conservation_algebra_v1 research/integration_v1/formal research/scientific_receiver_v1/formal research/authorization_history_v1/formal research/scientific_history_v1/formal research/scientific_authority_v2/formal; do
  python -m research.integration_v1.prepare_mathlib_cache --project "$project"
done
python research/scientific_authority_v2/check_formal.py --lean "$(command -v lean)"
python -m research.scientific_receiver_v1.qualify --out /new/path/qualification
```

Read every theorem statement and axiom closure, including `audit_sound`, the
closed initialized-trace theorem and the invariant hypotheses. Review the
scientific and cryptographic/OS assumptions. The independent14-control source
is a kernel-tested model probe; its symbolic signature oracle is not Ed25519.

## One-command functional reproduction

Bootstrap a fixed operator configuration from an independently reviewed
qualification SHA. Hash equality alone is not an authenticated review channel.
The example computes a fresh build's digest within the operator's local context:

```sh
QUAL_SHA="$(sha256sum /new/path/qualification/qualification.json | cut -d ' ' -f 1)"
python -m research.scientific_authority_v2.bootstrap --qualification /new/path/qualification --qualification-sha256 "$QUAL_SHA" --out /new/path/operator.json
python -m research.scientific_authority_v2.demo --config /new/path/operator.json --out /new/path/demo
```

The demo initializes a fresh witness using actual Lean, launches its real service,
admits two valid artifacts, rejects false science, exports and scientifically
replays the whole history, detects a rolled-back producer database against the
live witness, and reconstructs exact witnessed records. It retains precise
results and the actual signed false-science replay. Fixture private keys are
removed after shutdown; no private key belongs in published evidence.

The complete declared Lean artifact inventory plus actual selected Python source
files is pinned. This does not attest OS-loaded mappings, all Python/native
libraries, honest compiler execution or transient file substitution. The host,
configuration and bootstrap remain trusted. Full-inventory hashing is materially
more expensive than the partial test fixture profile.

## Runtime tests and independent auditor

Set the actual receiver environment rather than relying on historical `/tmp`:

```sh
export LEAN_PATH="$(lake -d research/scientific_receiver_v1/formal env printenv LEAN_PATH)"
export PCS_SCIENTIFIC_LEAN="$(command -v lean)"
export PCS_SCIENTIFIC_MAIN="$PWD/research/scientific_receiver_v1/formal/Main.lean"
export PCS_SCIENTIFIC_CWD="$PWD/research/scientific_receiver_v1/formal"
export PCS_AUTHORITY_V2_REPORTS=/new/path/crash-reports
python -m pytest -q research/scientific_history_v2/tests research/scientific_witness_v1 research/scientific_authority_v2/tests
```

The existing receiver/history/join suites and inherited full public workflow must
also pass on the final proposed-merge tree. Missing tooling is a failure, never
a successful mocked verifier or silent skip.

The full-history CLI in `research.scientific_history_v2.cli` accepts operator-owned
root/profile/checkpoint/material paths; inspect `--help` for replay modes. A new
auditor must pin the witness/root independently, retrieve current material with
its own challenge, and rerun the mathematical checks. It must not accept a key
contained only in the history being audited.

Historical checker identity includes absolute paths, cwd and environment hashes.
Replaying an existing signed root on another machine requires reproducing that
reviewed layout/profile. A fresh experiment may create a different reviewed
profile/root/keys. Arbitrary profile migration or key rotation is unsupported;
source-identical binaries at new paths do not silently acquire the old identity.

## Deployable external reference, not a deployment claim

An independent witness operator initializes its own key/store/config and supplies
the trusted public key and root over a separate authenticated bootstrap channel.
The CLI provides explicit `init` and existing-state-only `serve` operations.
Nonloopback serving requires operator-provided TLS certificate/key; clients verify
TLS and the receiver-pinned Ed25519 identity. Neither proves scientific truth or
honest storage continuity. Do not share the witness directory/key with the producer.
Public/observer-retained latest checkpoints are needed to investigate witness
rollback and equivocation beyond one honest durable state. No production service
has been deployed by this work.
