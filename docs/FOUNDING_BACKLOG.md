# Founding Backlog

## P0 — Must close before external product claims

- [ ] Compile `formal/PCS/Core.lean` with a pinned Lean/mathlib toolchain.
- [ ] Replace the draft Boolean acceptance logic with a fully specified assurance judgment and prove soundness properties.
- [ ] Define canonical JSON/certificate serialization precisely enough that independent implementations compute identical hashes.
- [ ] Add certificate versioning/migration rules.
- [ ] Threat-model certificate forgery, artifact substitution, TOCTOU, path traversal, malicious archives, and checker confusion.
- [ ] Add signed certificates; design an optional transparency-log mechanism.
- [ ] Prove/validate that external formal-proof adapters never elevate a claim without replay/checking by an accepted checker.
- [ ] Separate product terminology for formal verification, computational checks, empirical validation, and regulatory documentation.
- [ ] Complete IP/provenance matrix for every existing project before copying source into this project.
- [ ] Get qualified legal review before choosing company entity, contributor terms, dual licensing, or patent strategy.

## P0 — Initial biopharma product

- [ ] Interview 20-30 pharmacometrics/computational-biology/quality/regulatory users.
- [ ] Identify the single most expensive recurring verification bottleneck.
- [ ] Build PK/PD domain-pack prototype around a restricted model representation.
- [ ] Add equation-to-implementation correspondence checks for the restricted representation.
- [ ] Add data-schema / subject-identity / replicate-aware split rules.
- [ ] Capture executable environment/SBOM/container identity.
- [ ] Generate human-readable assurance report alongside JSON certificate.
- [ ] Map certificate evidence fields to FDA M15 verification/documentation concepts.

## P1 — Research publication

- [ ] Formalize claim/evidence graph semantics.
- [ ] Formalize invalidation propagation.
- [ ] Define evidence composition theorem(s).
- [ ] Construct three case studies: CertiForge, MS/omics evaluation, AI-policy trace.
- [ ] Build adversarial benchmark suite with explicit false-accept metric.
- [ ] Draft “Proof-Carrying Scientific Workflows” paper.
- [ ] Release reproducibility package only after IP/disclosure review.

## P1 — Productization

- [ ] GitHub App / CI integration.
- [ ] Policy-as-code for required claims/assurance levels.
- [ ] Evidence storage with immutable IDs.
- [ ] Private deployment architecture.
- [ ] Organization/user/RBAC model.
- [ ] Audit and invalidation dashboard.
- [ ] API/SDK for domain adapters.

## P2 — Expansion research

- [ ] Chemistry/reaction-network domain pack.
- [ ] Validated numerics adapter.
- [ ] AI authority/trace domain pack.
- [ ] Medical-device computational-model evidence pack.
- [ ] Explore aerospace/energy only after the core and first market are stable.
