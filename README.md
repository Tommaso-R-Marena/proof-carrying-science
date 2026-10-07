This project was edited by [Aristotle](https://aristotle.harmonic.fun).

To cite Aristotle:
- Tag @Aristotle-Harmonic on GitHub PRs/issues
- Add as co-author to commits:
```
Co-authored-by: Aristotle (Harmonic) <aristotle-harmonic@harmonic.fun>
```

# Proof-Carrying Science — Founding Architecture v0.5

> **Pre-publication / private founding build.** PCS is maintained in its own standalone repository and deliberately isolated from constituent research projects so those works can be published on their own terms first. See `docs/PUBLICATION_FIREWALL.md`.

> **Repository integrity.** `main` is the authoritative integration branch. Before contributing, read `CONTRIBUTING.md` and `docs/REPOSITORY_INTEGRITY_POLICY.md`. Run `python scripts/check_repository_integrity.py` before every PR or release. The 2026-10-04 branch/CI reconciliation is recorded in `docs/BRANCH_RECONCILIATION_2026-10-04.md`.

**Working category:** scientific assurance / formal verification infrastructure  
**Initial vertical:** computational biopharma  
**Long-term scope:** critical computation across biology, chemistry, AI, medicine, engineering, and other high-consequence sectors.

## Mission

**Make critical computation worthy of trust.**

PCS is built around the idea that consequential computational claims should carry independently checkable evidence of what was computed, which artifacts produced it, which assumptions it depends on, which properties were checked, which obligations require empirical validation, and what remains unresolved.

The formal target is the conditional assurance judgment `Γ ; E ⊢ C @ L`: under explicit assumptions `Γ`, evidence `E` supports scoped claim `C` at assurance class `L`.

PCS deliberately does **not** equate formal or computational verification with scientific truth. A program can satisfy a formal specification while the underlying biological model is still empirically inadequate.

## v0.5 launch-candidate capabilities

The executable reference kernel can:

- package and SHA-256 bind scientific artifacts;
- represent typed `Claim`, `Assumption`, `Evidence`, `Artifact`, and `Workflow` objects;
- reject broken claim/evidence/artifact references;
- verify workflow DAG integrity and reject cycles or multiple producers;
- bind computational claims to machine-readable predicates;
- replay built-in checks rather than trusting recorded PASS/FAIL values;
- derive claim status from replayed evidence;
- produce a stable semantic hash plus per-run integrity hash;
- trace which evidence and claims become stale when an artifact changes;
- diff two certificates structurally;
- sign certificates with Ed25519;
- sign a package manifest that binds the human-readable report and every delivered artifact;
- pin an expected signer identity by public-key fingerprint;
- evaluate reviewer-supplied acceptance policies that remain external to producer bundles;
- create deterministic evidence ZIPs;
- safely unpack and independently verify evidence ZIPs with path-traversal, namespace-collision, portability, and size limits;
- emit reviewer verification receipts binding exact bundle/policy bytes and assurance dimensions;
- enforce claim-status gates in CI;
- scaffold a bounded PK/PD pilot project;
- perform an environment/reference self-check;
- generate a complete evidence package, HTML report, optional signature, and deterministic ZIP with one command;
- validate and replay a restricted one-compartment IV-bolus PK + direct-Emax PD workflow.

The repository also contains the integrated Lean 4.28 v0.6/v2 assurance layer. The production v0.6 path is **Lean-authoritative**: Python performs archive I/O plus the explicitly external replay/capture/workflow stages, but authoritative `valid: true` requires the compiled Lean authority to accept the exact decoded package bytes and certificate-bound observation transcript. v0.5 remains the legacy browser-parity fixture. See `docs/LEAN_KERNEL_STATUS.md`.


## Guided v0.6 project onboarding

Scientists no longer need to hand-author a PCS manifest from scratch.

```bash
pcs discover-v06 ./my-project
```

PCS scans the project locally, safely inventories regular files, excludes key
material and common build/environment directories, snapshots SHA-256/size metadata,
and detects supported patterns such as:

- restricted one-compartment IV-bolus + direct-Emax model JSON;
- matching `time,concentration,effect` prediction tables;
- named train/test/validation CSV splits with a shared subject/sample identifier;
- reaction JSON with reactants/products;
- explicit left-unit/right-unit compatibility specifications.

The command writes:

```text
my-project/
  pcs-manifest.draft.json
  pcs-discovery.json
  pcs-discovery-review.md
```

The draft is intentionally **not attestable**. Review or edit the proposed claims,
assumptions, checks, artifact selection, and workflow first, then explicitly confirm:

```bash
pcs confirm-v06 ./my-project/pcs-manifest.draft.json
```

This writes `my-project/manifest.json` only after re-hashing every selected
artifact against the discovery snapshot. `attest-v06` independently checks the
same snapshot again, so a file changed after human confirmation cannot be silently
signed.

The discovery engine is a usability/recommendation layer, not a scientific verdict.
Confidence scores select only high-confidence supported patterns by default; the
scientist remains responsible for the meaning of the confirmed claims.

Static Python/Jupyter workflow discovery plus conservative review-only R mapping now complements the file-pattern detectors.
The CLI parses source with Python ASTs without importing or executing user code,
resolves conservative local file reads/writes, drafts artifact-dependency workflow
nodes, reports dynamic/ambiguous references instead of guessing, and keeps partial
inferences below the default 0.95 auto-selection threshold. Confirmed workflow
inferences are carried into the signed certificate as explicit static-only
provenance.

The Markdown review summarizes selected checks, source/artifact flow, unresolved items, and a Mermaid graph for human review before confirmation.

Reviewer verification independently reconstructs the delivered source tree and re-runs static workflow analysis on the exact packaged bytes. Human-confirmed workflow nodes therefore have to survive a dedicated `workflow_replay` stage before ordinary scientific evidence replay. Clean AST mappings use exact-set matching; partial/R/browser mappings use a weaker claimed-subset contract where every signed edge still must be rediscovered.

See `docs/STATIC_WORKFLOW_DISCOVERY_V06.md`.

## v0.6 end-to-end reviewer verification

The v0.6 research line exposes one fail-closed reviewer command for a delivered
package directory:

```bash
pcs verify-v06 delivered-package \
  --public-key trusted-reviewer-key.pem \
  --expected-signer-fingerprint <sha256-of-trusted-ed25519-public-key> \
  --receipt verification-receipt.json
```

The command verifies, in order:

1. exact canonical JCS bytes for the certificate, signatures and manifest;
2. the certificate Ed25519 signature;
3. the exact signed package member set, sizes, SHA-256 hashes and certificate binding;
4. fresh replay of all supported scientific evidence;
5. exact equality of the delivered normalized decision set with the replay-derived set.

Exit codes are stable:

- `0`: the complete v0.6 verification chain accepted;
- `1`: the package was read successfully but verification rejected it;
- `2`: an operational/input error prevented verification.

Verification receipts are deterministic JSON derived from the verification result.
Existing receipt files are not overwritten unless `--force-receipt` is supplied
explicitly.

For reviewer deployments, pin `--expected-signer-fingerprint` rather than trusting
an arbitrary public key delivered inside the same package.


### Build a deterministic v0.6 delivery bundle

A complete, already-signed v0.6 package directory can be converted into the
canonical delivery ZIP with:

```bash
pcs bundle-v06 package-directory \
  -o delivery.zip \
  --public-key trusted-public-key.pem \
  --expected-signer-fingerprint <sha256-of-trusted-ed25519-public-key>
```

The builder first runs the full v0.6 end-to-end verifier. It refuses to emit an
archive unless the directory passes signature verification, exact package binding,
fresh scientific replay, and normalized-set regeneration.

The emitted archive contains exactly the manifest-signed members plus:

```text
certificate_signature.json
package_manifest.json
package_signature.json
```

ZIP bytes are deterministic: members are sorted, stored without compression, use a
fixed 1980 timestamp, fixed Unix file mode and fixed ZIP version metadata, with no
extra fields or comments. Rebuilding the same verified package therefore produces
the same ZIP bytes and SHA-256.

The builder also refuses unsigned extras, symlinks, output inside the package
directory, accidental overwrite, and apparent private-key material. Use `--force`
only when intentionally replacing an existing delivery ZIP.

Publication is failure-atomic: PCS writes the candidate ZIP to a temporary sibling,
runs the extraction-free v0.6 verifier against those exact archive bytes, checks the
verifier's `bundle_sha256` against the candidate, and only then atomically publishes
the requested output path. A failed post-build verification deletes the candidate
and leaves any previous output untouched.

### Fast reviewer path: one command with a pinned trust profile

For demos and deployments, reviewers can store the producer key, fingerprint, and
optional reviewer policy once in a local trust profile:

```json
{
  "format": "pcs-verifier-trust-v1",
  "public_key": "trusted-producer.pem",
  "expected_signer_fingerprint": "<64-hex-ed25519-fingerprint>",
  "policy": "reviewer-policy.json"
}
```

Then verification is one command:

```bash
pcs verify-local-v06 study.pcs.zip --trust trust.json --receipt receipt.json
```

The separate `pcs-verifier-v06` entry point exposes the same narrow reviewer
surface. A single-file executable can be built with:

```bash
python -m pip install -e '.[standalone]'
python scripts/build_verifier_artifact.py -o dist/pcs-verifier-v06
```

The builder emits the executable plus a SHA-256 manifest. The trust profile remains
external to the delivered scientific bundle, so an attacker cannot select their own
trusted key by modifying the bundle.

### Three canonical deterministic demos

Run all three end-to-end v0.6 examples with:

```bash
python scripts/run_golden_examples_v06.py -o golden-demo-run
```

The harness produces a positive PK/PD replay, a valid bundle carrying an intentionally
failed PK/PD claim, and an environment-bound discovery/confirmation/replay case. It
uses a deterministic **demo-only** key so repeated builds can be checked for identical
bundle SHA-256 values; that key must never be trusted for real publication.

The focused v0.6 attack campaign is:

```bash
python scripts/adversarial_v06_hardening.py
```

It targets archive namespace ambiguity, unsigned extras, signed-byte tampering,
environment-source drift, and forged environment propositions at the replay boundary.

### Verify the delivered v0.6 ZIP directly

A reviewer does not need to extract the archive first:

```bash
pcs verify-v06-bundle delivered-package.zip \
  --public-key trusted-reviewer-key.pem \
  --expected-signer-fingerprint <sha256-of-trusted-ed25519-public-key> \
  --receipt verification-receipt.json
```

The v0.6 ZIP verifier never calls `extractall` or writes archive members to a
temporary filesystem. It validates the archive namespace, rejects traversal,
duplicate and cross-platform-colliding names, symlinks, encrypted members,
unsupported compression methods and resource-limit violations, then streams each
member under bounded uncompressed-size limits and sends the exact bytes to the
end-to-end verifier.

The receipt additionally binds `bundle_sha256`, the SHA-256 of the exact ZIP
file supplied by the reviewer.

## v0.6 MVP workflow

The v0.6 path now supports the complete producer-to-reviewer loop.

Producer:

```bash
pcs keygen \
  --private-key organization-private.pem \
  --public-key organization-public.pem

pcs attest-v06 project/manifest.json \
  -o study.pcs.zip \
  --private-key organization-private.pem \
  --public-key organization-public.pem
```

`attest-v06` performs the complete bounded workflow:

```text
manifest + source artifacts
        ↓
copy exact artifacts into package namespace
        ↓
run supported checks against the copied bytes
        ↓
build typed pcs-0.6 certificate
        ↓
recompute claim assessments
        ↓
derive normalized decision set
        ↓
optionally validate + bind SBOM / external build provenance
        ↓
sign certificate
        ↓
build + sign exact package manifest
        ↓
independently verify generated directory
        ↓
build deterministic ZIP
        ↓
verify exact candidate ZIP
        ↓
atomically publish study.pcs.zip
```

Reviewer:

```bash
pcs verify-v06-bundle study.pcs.zip \
  --public-key trusted-organization-public.pem \
  --expected-signer-fingerprint <trusted-fingerprint> \
  --receipt verification-receipt.json
```

The initial MVP producer supports the built-in check types
`csv_disjoint`, `reaction_balance`, `unit_compatible`,
`pkpd_contract`, `pkpd_reference_match`, and `pkpd_peak_concentration_threshold`. The peak-threshold checker proves only that every concentration in the committed prediction table is at or below the committed bound in the model-declared concentration unit; it is not a continuous-time Cmax or clinical-safety theorem. It also supports a narrow signed-receipt
adapter for `external_empirical_validation` and `external_statistical_validation`:
PCS can verify a pinned Ed25519 validator identity, exact external predicate, exact
artifact SHA-256 bindings, and the validator's reported PASS/FAIL. Those external
results remain outside the certified Lean checker set; PCS does **not** thereby prove
the validator algorithm, the scientific adequacy of its policy, or biological/clinical
truth. External formal-proof evidence remains verifier-boundary work. Supply-chain provenance is handled separately: PCS can bind CycloneDX/SPDX SBOM bytes and can verify a pinned Ed25519 DSSE/in-toto build-provenance statement for explicitly expected subject SHA-256 digests, without treating that provenance as scientific truth.

A successful PCS verification means the delivered package is authentic under the
selected public key, byte-bound, structurally consistent, freshly replayed for the
supported checks, and exactly agrees with its replay-derived normalized decisions.
It does not mean every scientific claim passed: a valid PCS package can truthfully
carry `FALSIFIED_OR_CHECK_FAILED`.

Passing PCS checks does not establish biological adequacy, clinical validity,
safety, efficacy, GxP validation, or regulatory acceptance.

### SBOM and external build provenance

Export a deterministic CycloneDX inventory of the observed Python runtime:

```bash
pcs export-sbom-v06 -o runtime.cdx.json
```

Bind those exact SBOM bytes into the signed delivery:

```bash
pcs attest-v06 project/manifest.json \
  -o study.pcs.zip \
  --private-key organization-private.pem \
  --public-key organization-public.pem \
  --sbom runtime.cdx.json
```

PCS also accepts CycloneDX JSON 1.4–1.7 or SPDX JSON 2.2–2.3 supplied by an
external build process. For stronger build provenance, `attest-v06` can verify and
bind a DSSE-signed in-toto Statement v1 under an explicitly pinned Ed25519 key and
one or more expected subject SHA-256 digests. See
`docs/SBOM_BUILD_PROVENANCE_V06.md`.

A valid build-provenance signature means only that the pinned key signed the exact
statement for the expected digest(s). It does not prove the builder was uncompromised,
the SBOM is complete, the artifact is safe, or any scientific claim is correct.

### Reviewer-controlled acceptance policy

PCS v0.6 keeps package/replay validity separate from reviewer acceptance.

```bash
pcs verify-v06-bundle study.pcs.zip \
  --public-key trusted-public.pem \
  --expected-signer-fingerprint <trusted-fingerprint> \
  --policy reviewer-policy.json \
  --receipt verification-receipt.json
```

The external policy uses the existing `pcs-acceptance-policy-v1` contract. It can
require specific claim statuses, require authenticated delivery, and independently
pin the expected signer fingerprint.

The verification receipt preserves both axes:

```json
{
  "valid": true,
  "accepted": false,
  "reviewer_policy": {
    "applied": true,
    "pass": false,
    "policy_sha256": "<sha256-of-exact-policy-bytes>",
    "failures": []
  }
}
```

`valid` answers whether PCS accepted the package/replay/normalized-decision chain.
`accepted` answers whether that verified result also satisfies the receiving
reviewer's policy. Policy failure does not rewrite an otherwise valid scientific
record as cryptographically invalid.

### Real-world benchmark registry

PCS v0.6 now includes a provenance-bound validation runner for public scientific
examples:

```bash
pcs benchmark-v06 validation/real_world/registry.json \
  -o real-world-validation.json
```

Each case declares its public source/citation, expected outcome, exact fixture
SHA-256 values, executable PCS check, and interpretation. The runner refuses
fixture-hash drift before replay, executes the same v0.6 replay kernel used by
certificates, compares actual with predeclared expected outcome, and emits a
deterministic report with registry and report semantic hashes.

The initial registry contains five cases:

- Haber-Bosch atom balance — expected PASS;
- clean UCI Iris split — expected PASS;
- one-row contaminated Iris split — expected FAIL;
- Indometh `mg/L` vs `g/m^3` unit equivalence — expected PASS;
- published IV Indometh subject 1 treated as exact single-exponential output —
  expected FAIL.

A direct checker-level execution on 2026-09-29 matched all 5 expected outcomes,
including both negative controls. See
`results/REAL_WORLD_VALIDATION_2026-09-29.md`.

### Reviewer-signed verification receipts

A producer signature answers **who issued the scientific package**. A reviewer
signature answers **who independently verified that exact delivery under that exact
policy and accepted/rejected it**.

```bash
pcs verify-v06-bundle study.pcs.zip \
  --public-key producer-public.pem \
  --expected-signer-fingerprint <producer-fingerprint> \
  --policy reviewer-policy.json \
  --receipt receipt.json \
  --reviewer-private-key reviewer-private.pem \
  --receipt-signature receipt.sig.json
```

The reviewer signature binds the exact receipt bytes through
`pcs-reviewer-receipt-ed25519-v1`. Its signed payload commits to the receipt
SHA-256, bundle SHA-256, certificate semantic/integrity hashes, normalized-index
hash, reviewer-policy SHA-256, PCS `valid`, and reviewer `accepted`.

A later auditor can verify the review decision without rerunning PCS:

```bash
pcs verify-receipt-v06 receipt.json \
  --signature receipt.sig.json \
  --reviewer-public-key reviewer-public.pem \
  --expected-reviewer-fingerprint <reviewer-fingerprint>
```

This signature attests to the review record. It does not make a false scientific
claim true, elevate assurance, or replace package/replay verification.

### Multi-reviewer quorum approval

PCS v0.6 can aggregate multiple independently signed reviewer receipts without
allowing those reviewers to alter the underlying PCS scientific verdict.

A quorum policy may require both a total threshold and role-specific thresholds:

```json
{
  "policy_version": "pcs-review-quorum-policy-v1",
  "min_accepted_reviews": 2,
  "required_roles": {
    "computational": 1,
    "domain": 1
  },
  "reviewers": [
    {
      "fingerprint": "<computational-reviewer-fingerprint>",
      "role": "computational",
      "required_policy_sha256": "<computational-policy-sha256>"
    },
    {
      "fingerprint": "<domain-reviewer-fingerprint>",
      "role": "domain",
      "required_policy_sha256": "<domain-policy-sha256>"
    }
  ]
}
```

Each counted review must have:

- a valid reviewer Ed25519 receipt signature;
- `pcs_valid: true`;
- `reviewer_accepted: true`;
- an authorized reviewer fingerprint;
- the role-specific policy SHA-256 required for that reviewer;
- the same exact reviewed subject commitments as every other counted review.

PCS groups reviews by exact bundle SHA-256, certificate semantic/integrity hashes,
and normalized-index semantic hash before evaluating quorum. Reviews from different
scientific bundles can therefore never be combined into a 2-of-3 result.

Duplicate reviewer identities are disqualified so one key cannot be counted twice.

Portable inputs are supplied through a review-set file:

```bash
pcs verify-quorum-v06 \
  --quorum-policy policies/review_quorum_v06.example.json \
  --review-set review-set.json \
  -o quorum-result.json
```

The result records the exact quorum-policy SHA-256, review-set SHA-256, reviewer
roles, subject groups, accepted-review count, and selected scientific subject.

This layer is governance over already verified reviewer receipts. It does not
rewrite claim status or elevate PCS assurance classes.

### Adaptive replay scheduling

PCS v0.6 now includes a telemetry-driven ordering layer for mandatory replay checks.
It can run deterministic baselines or a contextual LinUCB-style bandit, but the
scheduler never changes which evidence is required or how a scientific check is
evaluated.

Recommended initial deployment is shadow mode:

```bash
pcs verify-v06-bundle study.pcs.zip \
  --public-key trusted-public.pem \
  --scheduler manifest \
  --shadow-bandit \
  --scheduler-history scheduler-history.jsonl \
  --scheduler-telemetry-append scheduler-history.jsonl
```

Analyze accumulated history with:

```bash
pcs scheduler-report-v06 scheduler-history.jsonl \
  -o scheduler-report.json
```

Implemented strategies are `manifest`, `cheapest-first`,
`failure-rate-first`, `failure-per-second`, and `bandit`.

Active bandit ordering has a cold-start guard: it falls back to the deterministic
failure-per-second baseline until there are at least 20 eligible observations
overall and 3 observations for every check type in the current package.

All mandatory checks still execute and replay results are reconstructed in
certificate order before claim assessment. Persisted telemetry hashes evidence IDs
and contains timing/size/outcome metadata only; it is not part of scientific truth
semantics.

See `docs/ADAPTIVE_SCHEDULER_V06.md`.

## Pre-result pilot commitment

A design partner can freeze the requested claims and assumptions before results are inspected:

```bash
pcs freeze-intake pilot_intake.json -o pilot_intake.lock.json
pcs attest manifest.json -o evidence --intake-lock pilot_intake.lock.json
```

The lock binds claim IDs, claim statements, assurance classes, assumption IDs, and assumption statements. The signed package includes the lock so post-hoc weakening is detectable.

## Fastest design-partner workflow

Install in editable form during development:

```bash
python -m pip install -e .
pcs doctor
```

Create a clean restricted PK/PD starter:

```bash
pcs init pilot --template pkpd --subject example-pilot
```

Generate signing keys once for the demo/organization:

```bash
pcs keygen --private-key signing-private.pem --public-key signing-public.pem
```

Produce the full attestation:

```bash
pcs freeze-intake pilot/pilot_intake.json -o pilot-intake.lock.json

pcs attest pilot/manifest.json -o pilot-evidence \
  --private-key signing-private.pem \
  --public-key signing-public.pem \
  --intake-lock pilot-intake.lock.json
```

Independently verify the delivered bundle from scratch:

```bash
pcs verify-bundle pilot-evidence.zip \
  --public-key signing-public.pem \
  --require-signature \
  --expected-signer-fingerprint <trusted-fingerprint> \
  --policy policies/pkpd_design_partner.example.json \
  --receipt verification-receipt.json
```

The reviewer can also run:

```bash
pcs inspect pilot-evidence/certificate.json
pcs impact pilot-evidence/certificate.json --artifact pkpd_model
pcs diff previous/certificate.json pilot-evidence/certificate.json
```


## Launch preview

A static launch-preview website and browser demo live under `site/`.

Preview locally:

```bash
python -m http.server 8000 --directory site
```

Then open `http://localhost:8000/` and `http://localhost:8000/demo.html`.

For the actual product path rather than the browser visualization:

```bash
python scripts/run_reference_demo.py --output demo-run
```

This creates and verifies a signed synthetic PK/PD evidence bundle using an external reviewer policy.

## Aristotle / Lean handoff

The formal project is pinned to `leanprover/lean4:v4.28.0`. The exact v0.6/v2 refinement layer is integrated under `formal/PCS/V2/` and imported by the production formal root. Its archive/package/decision assurance theorems and the verified `reaction_balance` replay layer build in the hosted Lean gate with no production `sorry`/project axioms. Remaining trust contracts and open statements are documented in `formal/PCS_FULL_FORMALIZATION_REPORT.md`.

Older Aristotle task files remain non-production proof-search material unless imported by the production root.

## Initial assurance checks

Built-in checks currently include:

- train/test CSV key disjointness;
- elementary chemical reaction balance;
- dimensional unit compatibility;
- restricted PK/PD representation contracts;
- independent analytic PK/PD output replay.

Passing these checks establishes only their declared computational properties. It does not establish biological adequacy, clinical validity, safety, efficacy, GxP validation, or regulatory acceptance.

## Architecture

```text
Scientific workflow
       |
       v
+-----------------------+
| Domain / tool adapters|  evidence producers
+-----------------------+
       |
       v
+-----------------------+
| Assurance IR          |  claims, assumptions, artifacts,
|                       |  workflows, proof obligations
+-----------------------+
       |
       v
+-----------------------+
| Small checker/kernel  |  independently re-checks evidence
+-----------------------+
       |
       v
Signed certificate + deterministic evidence bundle
```

Long-term product architecture: **open checker + open certificate format + domain packs + commercial enterprise orchestration**.

## Repository map

- `pcs/` — executable Python reference checker and product CLI
- `formal/` — Lean assurance-kernel source
- `schemas/` — portable certificate/manifest schemas
- `examples/` — synthetic/public examples only
- `tests/` — unit, integration, and adversarial tests
- `site/` — static landing-page draft
- `docs/` — founding, product, pilot, publication, security, research, and business architecture
- `results/` — frozen reference outputs and adversarial campaign results

## Trust principle

> **The producer of a claim is not the trust boundary. Independently checkable evidence is.**

The v0.6 production verification path is **Lean-authoritative**: Python performs archive I/O and the external replay/capture/workflow stages, but a result is not authoritative or PCS-valid until the compiled Lean v0.6/v2 authority accepts the exact decoded member bytes together with a certificate-bound canonical observation transcript. The Python stages therefore remain part of the external-computation TCB where explicitly modeled, but Python-only acceptance is no longer sufficient.

## Current limitations

- The exact Lean 4.28 v0.6/v2 assurance layer is integrated. Production now gates authoritative validity on Lean acceptance, avoiding a whole-Python-semantics equivalence claim. ZIP-decoder/materialization fidelity, process invocation, capture/workflow semantics, external-validator scientific semantics, cryptographic unforgeability, and independent Ed25519/SHA-512 spec correspondence remain explicit boundaries.
- No arbitrary Python/R/C++ correctness theorem is claimed.
- The PK/PD adapter is intentionally restricted and synthetic-first.
- Chemical parsing is intentionally narrow.
- Production identity, HSM/KMS key custody, revocation, transparency logs, and organization trust policy remain open.
- No GxP validation or regulator endorsement is claimed.

For launch work, start with `docs/FOUNDING_OFFER.md`, `docs/DESIGN_PARTNER_PILOT.md`, `docs/PILOT_OPERATIONS_RUNBOOK.md`, `docs/DATA_HANDLING_FOR_PILOTS.md`, and `docs/LAUNCH_READINESS_SCORECARD.md`.


## Reproducibility environment capture

Guided v0.6 onboarding now captures the declared software environment alongside
scientific artifacts and static workflow provenance.

```bash
pcs discover-v06 ./my-project
pcs environment-plan-v06 ./my-project/pcs-discovery.json \
  -o environment-plan.json \
  --script reconstruct-environment.sh
```

The environment layer recognizes Python/R dependency declarations, common lockfiles,
Python/R interpreter constraints, Conda/Nix environment specifications, and
Dockerfile/Containerfile base-image pinning. It distinguishes loose declarations
from stronger lock/hash/digest evidence and emits one of:

```text
strongly_pinned
container_base_pinned
locked_application_dependencies
hash_pinned_dependencies
declared_dependencies
environment_unspecified
```

The generated reconstruction script is **review-before-run**. PCS verification never
runs package managers, container builds, or project installation code automatically.

After full bundle verification, a reviewer can materialize the exact signed
project-relative artifact tree plus the bound environment plan and review-before-run
script:

```bash
pcs prepare-environment-v06 study.pcs.zip \
  -o replay-workspace \
  --public-key trusted-public.pem \
  --expected-signer-fingerprint <fingerprint>
```

Workspace preparation is still non-executing. The workspace includes
`pcs-environment-workspace.json`, the verification receipt, exact signed source
artifacts, `pcs-environment-plan.json`, and `reconstruct-environment.sh`. It is
bound to the delivery bundle SHA-256, certificate hashes, normalized-index hash, and
producer fingerprint.

Confirmed guided manifests bind the environment source artifacts and canonical
`pcs-environment-capture-v1` proposition into the signed certificate as
`pcs-environment-binding-v1`.

Independent verification now executes:

```text
package_binding
→ environment_replay
→ workflow_replay
→ scientific replay
→ normalized_set
```

`environment_replay` reconstructs the exact delivered environment source tree and
freshly regenerates the environment capture. A fully re-hashed and re-signed false
dependency/interpreter/container claim is therefore expected to fail before workflow
or scientific replay.

Normative boundary and supported formats:
`docs/REPRODUCIBILITY_ENVIRONMENT_V06.md`.
