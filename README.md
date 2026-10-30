# Proof-Carrying Science

PCS packages computational claims with exact artifacts, explicit assumptions and
independently replayable evidence. It keeps four questions separate: is the
mathematics proved, does the implementation match it, are the scientific
assumptions appropriate, and does independent empirical evidence support them?

## Start here

- **Explore without installing anything:** [PCS website](https://proof-carrying-science-site.marenatommaso.workers.dev/experience.html).
  Its beginner investigation uses fictional facts and downloadable witnesses.
  Browser calculations are labeled separately from actual Lean verification.
- **Verify a delivered scientific package:** use the
  [v0.6 verification boundary](docs/LEAN_KERNEL_STATUS.md) and
  [pilot operations runbook](docs/PILOT_OPERATIONS_RUNBOOK.md).
- **Study the AI-safety experiments:** start with the
  [research guide](research/README.md) and
  [actual-weight/public-study results](research/public_study_validation_v1_results/README.md).
- **Contribute:** read [CONTRIBUTING.md](CONTRIBUTING.md) and the
  [repository integrity policy](docs/REPOSITORY_INTEGRITY_POLICY.md).

The public website has its own [repository](https://github.com/Tommaso-R-Marena/proof-carrying-science-site).
The `site/` directory here is an archived preview, not the deployed website.

## What PCS currently verifies

The production v0.6 path requires the compiled Lean authority to accept exact
canonical package bytes and certificate-bound observations. Python handles
archive I/O and explicitly external replay/capture/workflow stages. Package
validity, scientific claim status, reviewer acceptance and deployment readiness
are distinct results. The v0.5 browser fixture remains a legacy transparency demo.

The executable workflow includes local project discovery, human confirmation,
artifact hashing, restricted scientific evidence replay, signed packages,
deterministic self-verified ZIP delivery, signer-fingerprint pinning,
reviewer-owned acceptance policies and verification receipts. The Lean library
covers byte/codec and mathematical obligations at the documented boundaries;
external validators, runtime/toolchain components and scientific adequacy retain
explicit assumptions. See [formal build instructions](formal/README.md).

A typical reviewer invocation is:

```sh
pcs verify-v06 delivered-package \
  --public-key trusted-public-key.pem \
  --expected-signer-fingerprint EXPECTED_SHA256 \
  --receipt verification-receipt.json
```

Obtain the expected fingerprint independently of the delivered package. A valid
signature does not establish biological validity, general AI safety, clinical
safety, regulatory acceptance or arbitrary-program correctness.

## Latest research evidence

The additive public-study evaluation uses official Qwen3-0.6B and Qwen3-1.7B Q8_0
weights and five published AgentDojo attack templates in a fixed synthetic PCS
tool workflow. All 72 planned fresh model responses are retained. There were
18 unsafe/forbidden action proposals, eight malformed proposals and six responses
containing the synthetic private marker; these categories overlap. All 72 guarded
executions and 72 separate receiving replays published only the approved summary.
The receiving pass regenerated 216 wire, row and path proof checks. The focused
suite passed 38 tests. These are local measurements, not an official AgentDojo
score, frontier-model evaluation or external partner validation.

Six new Lean declarations establish proposal-independent tool traces under an
explicit unique-action premise and exhibit a separate raw-reply countermodel.
This explains why completion under a correcting guard does not establish model
competence or full-output confidentiality. The full [report](research/public_study_validation_v1_results/README.md)
includes raw requests/responses, negative findings, exact revisions, source hashes,
trust assumptions and replay commands.

Other research libraries cover exact token/byte policy binding, safe progress,
controller-version budgets, causal/relational disclosure, authenticated scientific
history, transport, certified numerics and epistemic composition. They are scoped
research capabilities; importing them does not promote a learned model or grant
production verification authority. [The research guide](research/README.md)
identifies their entry points and versioned evidence.

## Install and check locally

Use Python 3.12.14 and Lean 4.28.0 on Linux for the documented research paths:

```sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --require-hashes -r requirements-build.lock -r requirements-dev.lock
python -m pip install --no-deps --no-build-isolation -e .
source scripts/activate_lean_428.sh
python scripts/check_repository_integrity.py
lake -d formal build PCS pcs-lean-authority pcs-semantic-check
pcs --help
```

Run the reviewed combined-source check from a clean committed checkout:

```sh
python -m research.integration_v2.reconcile --require-committed
```

It pins exact file bytes, executable modes, original PR source identities and the
reviewed combined tree. It is source admission, not a scientific verdict. Older
phase-specific preservation checks retain their original Git context; use the
combined CI boundary rather than weakening them to accept a different tree.

To replay the retained public-study responses without downloading model weights:

```sh
PYTHONPATH=. python research/public_study_validation_v1_results/receiving.py \
  research/public_study_validation_v1_results/recorded/producer /tmp/new-pcs-receiver
```

Use a fresh output path. This runs actual native Lean/SQLite verification but
performs no new neural inference. Fresh neural generation requires about 2.5 GB
of pinned downloads; see the study report. The compiler, Python/C implementations,
libraries, host OS and custody of trusted inputs remain explicit trust boundaries.
Sealed snapshots, hashes and same-host child processes are not an immutable root.

## Integration and readiness

The [current integration status](docs/integration/2026-10-29/README.md) separates
local qualification, hosted CI and protected merge evidence. Historical reports
and source-bound READMEs retain their original bytes and dates. The
[README audit](docs/integration/2026-10-29/README_AUDIT.json) identifies current
entry points and preserved versioned/source evidence. The earlier founding README
is retained [verbatim](docs/integration/2026-10-29/predecessor/v12/ROOT_README.md).

PR #117 remains under its explicit no-merge hold. Unavailable final Aristotle V8
outputs are not assumed present. No untrusted proof-generation trace is used as
model-training data. Experimental self-modification is not deployed to production.

PCS is suitable for bounded developer research and independently replayable
computational assurance at its stated boundaries. Genuine external-partner
validation, third-party/historical rights review, counsel-reviewed terms and
commercial/payment arrangements remain open under issues #9, #11, #13 and #14.
A public study cannot satisfy those exit criteria. A custom website domain remains
optional. See [owner/external requirements](docs/integration/2026-10-28/OWNER_DEPENDENCIES.md).

## License and attribution

First-party PCS source is public under [Apache-2.0](LICENSE); third-party inputs
retain their own notices and rights. See [NOTICE](NOTICE) and the
[publication firewall](docs/PUBLICATION_FIREWALL.md). First-party publication
authorization does not establish independent clearance of the complete history.

Aristotle-assisted formal artifacts retain their source provenance. See
[Aristotle](https://aristotle.harmonic.fun); applicable commits retain the
`Aristotle (Harmonic) <aristotle-harmonic@harmonic.fun>` co-author attribution.
