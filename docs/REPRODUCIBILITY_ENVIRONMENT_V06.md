# PCS v0.6 reproducibility environment capture

## Purpose

PCS v0.6 can bind the declared computational environment needed to interpret and
reconstruct a scientific workflow. The environment layer is deliberately separate
from scientific truth: it establishes what environment specifications were present,
what they declared, and whether a reviewer can independently re-derive the same
static environment contract from the exact delivered bytes.

Formats:

- `pcs-environment-capture-v1`
- `pcs-environment-binding-v1`
- `pcs-manifest-environment-contract-v1`
- `pcs-environment-replay-plan-v1`

## Producer path

```text
project directory
    ↓
discover-v06
    ↓
environment files inventoried + hashed
    ↓
dependency/interpreter/container parsing
    ↓
hermeticity classification
    ↓
pcs-environment-plan.json
    ↓
human review + confirm-v06
    ↓
signed environment binding in certificate
    ↓
attest-v06 self-verification
```

Environment source files are ordinary signed PCS artifacts. Their exact bytes,
SHA-256 values, project-relative source paths, and discovery snapshots therefore
participate in the package and certificate commitments.

## Captured declarations

### Python

PCS recognizes, within bounded local files:

- `pyproject.toml` PEP 621 dependencies and `requires-python`;
- Poetry dependency declarations;
- `requirements*.txt`, `requirements*.in`, and `requirements.lock`;
- `.python-version` and `runtime.txt`;
- `uv.lock`, `poetry.lock`, and `Pipfile.lock`;
- `Pipfile` interpreter declarations;
- pip dependencies embedded in a Conda environment file.

Exact pins and SHA-256 requirement hashes are recorded separately. A loose
declaration such as `numpy>=1.26` is never treated as equivalent to a hash-pinned
lock.

### R

PCS recognizes:

- `renv.lock` R version and package versions;
- `DESCRIPTION` dependency fields and R version constraints.

R package declarations and lock records remain separate so a declared dependency is
not mislabeled as an exact lock.

### Conda / Nix

PCS captures:

- `environment.yml` / `environment.yaml`;
- `conda-lock.yml` / `conda-lock.yaml`;
- `flake.nix` and `flake.lock`.

Conda YAML parsing is intentionally conservative and does not claim arbitrary YAML
semantic completeness. Exact environment source bytes remain signed even when a
field is not structurally interpreted.

### Containers

PCS inspects `Dockerfile` and `Containerfile` without building them.

For each `FROM` stage it records:

- image reference;
- whether the reference is dynamic;
- whether it is pinned by `@sha256:...`;
- tag when present.

PCS distinguishes tag-only bases from digest-pinned bases. Dynamic bases such as
`FROM $BASE` are explicitly unresolved.

Selected package-install/build commands are surfaced for review, but are not run
during verification.

## Hermeticity classification

The current classifier is descriptive, not a proof of runtime equivalence.

```text
strongly_pinned
container_base_pinned
locked_application_dependencies
hash_pinned_dependencies
declared_dependencies
environment_unspecified
```

Examples:

- digest-pinned container base + recognized lockfile → `strongly_pinned`;
- digest-pinned container base without an application lock → `container_base_pinned`;
- `uv.lock`, `poetry.lock`, `Pipfile.lock`, or `renv.lock` → `locked_application_dependencies`;
- every selected requirements record is exactly pinned and carries a SHA-256 hash →
  `hash_pinned_dependencies`;
- dependency declarations without sufficient locking → `declared_dependencies`.

These labels do **not** assert that every transitive system library, compiler,
kernel, driver, CPU feature, or external registry object is frozen.

## Reconstruction plan

`pcs discover-v06` emits `pcs-environment-plan.json`.

The same plan can be extracted later from a discovery report, confirmed manifest,
or signed certificate:

```bash
pcs environment-plan-v06 manifest.json -o environment-plan.json
```

A review-before-run shell script can also be generated:

```bash
pcs environment-plan-v06 manifest.json \
  --script reconstruct-environment.sh
```

PCS **never executes this script automatically**. Package managers and container
builds can execute arbitrary project/dependency code and can access the network.
The generated script begins with an explicit review warning.

Supported reconstruction strategies currently include:

- OCI/Docker build;
- Nix flake;
- conda-lock;
- uv frozen sync;
- Poetry sync;
- Pipenv sync;
- pip requirements, optionally with `--require-hashes`;
- renv restore;
- Conda environment creation.

## Authoritative confirmation recapture

The browser Project Mapper may provide a lower-assurance environment preview, but
that preview is never promoted directly into a signed environment proposition.

At `confirm-v06`, PCS re-reads the already snapshotted, selected environment
artifacts with the authoritative Python `capture_environment_v06` implementation
and replaces the draft environment object with that fresh canonical capture before
setting `human_confirmed = true`.

This guarantees that browser → CLI onboarding and CLI-only onboarding converge on
the same producer-side environment parser before attestation.

## Reviewer-side environment replay

The end-to-end verifier order is:

```text
canonical_inputs
→ certificate_signature
→ package_binding
→ environment_replay
→ workflow_replay
→ scientific replay
→ normalized_set
```

At `environment_replay`, PCS:

1. obtains the exact environment source artifacts from the signed package;
2. verifies their SHA-256 values and project-relative source paths;
3. reconstructs a temporary project tree without executing user code;
4. reruns `capture_environment_v06`;
5. compares the fresh canonical capture against the human-confirmed signed
   environment proposition.

A producer cannot make a false environment claim valid merely by recomputing hashes
and signatures. A forged dependency version, interpreter constraint, lockfile claim,
container reference, replay plan, or hermeticity label must disagree with fresh
capture and fail this stage.

## Human confirmation

Discovery produces a non-attestable draft. Confirmation marks the environment record
as human-reviewed only after selected environment source artifacts pass the same
SHA-256 snapshot checks used for the rest of guided discovery.

Human confirmation means:

> these static environment declarations and reconstruction instructions are the
> environment metadata the producer intends to attest.

It does **not** mean:

- dependency registries will still serve the same objects;
- installers/package managers are correct;
- native extension ABIs are identical;
- host kernels/drivers/CPU features match;
- a container build succeeds;
- the reconstructed workflow produces identical runtime behavior;
- the scientific model is empirically valid.

## Verified reviewer replay workspace

A reviewer can prepare a local replay tree directly from a delivered PCS bundle:

```bash
pcs prepare-environment-v06 study.pcs.zip \
  -o replay-workspace \
  --public-key trusted-producer.pem \
  --expected-signer-fingerprint <fingerprint>
```

PCS performs the complete v0.6 bundle verification first, including
`environment_replay`, `workflow_replay`, scientific replay and normalized-set
regeneration. Only a valid delivery may be materialized.

The workspace preserves certificate `source_path` layout for signed project
artifacts and writes:

```text
pcs-environment-workspace.json
pcs-environment-plan.json
reconstruct-environment.sh
<signed project-relative artifacts...>
```

`pcs-environment-workspace.json` binds the prepared tree back to the delivery
bundle SHA-256 and certificate semantic/integrity hashes and records which
materialized artifacts were environment sources.

Workspace preparation is still non-executing. A Dockerfile, setup hook, notebook,
script or installer in the verified project is copied as data only. The generated
reconstruction script must be reviewed and run explicitly by the reviewer if they
choose to construct the environment.

## Trust boundary

Environment capture and replay do not alter claim PASS/FAIL semantics. A valid
environment contract can coexist with failed science, and a scientifically valid
package can have weak or incomplete environment declarations.

The environment layer is reproducibility provenance, not scientific evidence
promotion.


## Sandboxed realized-environment replay

A prepared workspace can now be executed explicitly:

\`\`\`bash
pcs execute-environment-v06 replay-workspace \
  -o realized-replay \
  --public-key trusted-producer.pem \
  --expected-signer-fingerprint <fingerprint>
\`\`\`

The execution stage re-verifies the producer-signed certificate, re-derives the
execution plan from the signed workflow/environment contract, validates every
materialized source artifact against its signed SHA-256 value, and then copies
only those signed artifacts into a disposable OCI sandbox. The prepared workspace
itself is never mutated.

Before any workflow node runs, PCS removes every pre-existing signed workflow
output from the disposable copy. This prevents a producer-supplied output from
being mistaken for a successfully reproduced result. Python, Jupyter, and R
static workflow nodes are topologically ordered and run with network disabled,
a read-only container root filesystem, dropped Linux capabilities, no-new-
privileges, bounded CPU/memory/PIDs, a temporary /tmp, and a fixed process
environment. There is deliberately no unsandboxed fallback.

If the signed environment includes exactly one container specification whose
base stages are digest-pinned, PCS can rebuild it with an offline/no-pull OCI
build. Otherwise the reviewer must provide an already-local image with
\`--image\`. A signed container reference that cannot be related to the realized
image fails the enforceable environment comparison.

After execution, PCS writes:

\`\`\`text
realized-replay/
  pcs-realized-environment.json
  pcs-replay-execution.json
  outputs/<reproduced workflow outputs...>
\`\`\`

The realized-environment record captures Python and R interpreter versions,
installed Python/R/Conda package versions, Python/R interpreter executable
SHA-256 where available, OS/kernel/architecture evidence, OCI image ID/repo
digests, and a canonical dependency-tree fingerprint. The execution receipt
also records bounded stdout/stderr plus hashes, whether stale outputs were
removed, regenerated output hashes/sizes, mutations to signed non-output
artifacts, unexpected files, and a field-by-field comparison with the producer's
signed reconstruction contract.

Exact signed package pins and interpreter constraints are enforced. Non-exact
dependency declarations must at least be present and are labeled as not exactly
version-enforced. Values that the existing static contract never promised
(interpreter binary hash, full realized dependency-tree fingerprint, final OCI
image digest, and complete OS/kernel identity) are captured as
\`observed_not_signed\`; PCS does not retroactively mislabel them as producer
commitments.

A replay receipt is valid only when every selected workflow node exits zero,
all declared outputs are recreated byte-for-byte, signed non-output artifacts
remain unchanged, the exact output namespace is respected when the static
workflow contract claimed an exact set, and every enforceable environment
expectation matches.

### Determinism boundary

The runner removes common nondeterminism by fixing process environment/thread
counts, disabling network access, starting from clean signed inputs, removing
pre-existing outputs, applying fixed resource limits, and comparing exact output
bytes. v0.6 does **not** virtualize the host kernel's wall clock or entropy
source. Therefore the receipt reports those limits explicitly instead of
claiming universal deterministic behavior for programs that intentionally read
time, entropy, hardware-specific state, or other kernel facilities.

The OCI runtime, host kernel, language/package introspection APIs, local image
store/build engine, and SHA-256 implementation remain in the execution TCB.
