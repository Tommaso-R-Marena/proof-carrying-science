# Proof-Carrying Science — Founding Architecture v0.5.1

> **Pre-publication / private founding build.** PCS is maintained in its own standalone repository and deliberately isolated from constituent research projects so those works can be published on their own terms first. See `docs/PUBLICATION_FIREWALL.md`.

**Working category:** scientific assurance / formal verification infrastructure  
**Initial vertical:** computational biopharma  
**Long-term scope:** critical computation across biology, chemistry, AI, medicine, engineering, and other high-consequence sectors.

## Mission

**Make critical computation worthy of trust.**

PCS is built around the idea that consequential computational claims should carry independently checkable evidence of what was computed, which artifacts produced it, which assumptions it depends on, which properties were checked, which obligations require empirical validation, and what remains unresolved.

The formal target is the conditional assurance judgment `Γ ; E ⊢ C @ L`: under explicit assumptions `Γ`, evidence `E` supports scoped claim `C` at assurance class `L`.

PCS deliberately does **not** equate formal or computational verification with scientific truth. A program can satisfy a formal specification while the underlying biological model is still empirically inadequate.

## v0.5.1 launch-candidate capabilities

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
- emit reviewer verification receipts binding exact bundle/policy bytes and assurance dimensions;\n- enforce claim-status gates in CI;
- scaffold a bounded PK/PD pilot project;
- perform an environment/reference self-check;
- generate a complete evidence package, HTML report, optional signature, and deterministic ZIP with one command;
- validate and replay a restricted one-compartment IV-bolus PK + direct-Emax PD workflow.

The PCS assurance decision and normalized-state soundness layer is **machine-checked in Lean 4.28.0**. This does not yet prove the raw JSON/ZIP → Python replay → normalized-state path end-to-end; the Python parser, domain checkers, hashing/crypto, and serialization/refinement path remain explicit parts of the executable TCB. v0.5.1 adds a claim-scoped normalized decision handoff so that remaining boundary is small, versioned, and independently testable. See `docs/LEAN_KERNEL_STATUS.md` and `docs/NORMALIZED_WIRE_V1.md`.

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

## Lean / next proof target

The formal project is pinned to `leanprover/lean4:v4.28.0`. The production decision and normalized-state soundness theorems have been independently rebuilt successfully under that toolchain, with no placeholders or PCS-specific axioms. The current draft proof target is the finite normalized-wire checker on branch `formal/serialized-refinement-v1`; unfinished obligations remain isolated under `formal/ProofTasks/` and are not imported into the clean production root.

See `formal/WIRE_CHECK_ARISTOTLE_PROMPT.md` for the focused next proof pass.

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

Today, the Python parser/replay/crypto/normalization path remains part of the TCB. Core acceptance semantics and normalized-state soundness are already machine-checked; the active research program is to shrink the remaining serialized/executable refinement boundary and make domain-specific evidence producers independently checkable wherever practical.

## Current limitations

- The decision/normalized-state Lean layer is machine-checked, but raw serialized-package parsing/replay → typed normalized state is not yet proved end-to-end.
- No arbitrary Python/R/C++ correctness theorem is claimed.
- The PK/PD adapter is intentionally restricted and synthetic-first.
- Chemical parsing is intentionally narrow.
- Production identity, HSM/KMS key custody, revocation, transparency logs, and organization trust policy remain open.
- No GxP validation or regulator endorsement is claimed.

For launch work, start with `docs/FOUNDING_OFFER.md`, `docs/DESIGN_PARTNER_PILOT.md`, `docs/PILOT_OPERATIONS_RUNBOOK.md`, `docs/DATA_HANDLING_FOR_PILOTS.md`, and `docs/LAUNCH_READINESS_SCORECARD.md`.
