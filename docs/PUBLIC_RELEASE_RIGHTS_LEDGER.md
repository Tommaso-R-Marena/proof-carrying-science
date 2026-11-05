# Public rights/provenance review ledger (working record)

**Public follow-up, 2026-10-08:** The owner made all three repositories public and explicitly confirmed complete first-party ownership and publication authority. See PUBLIC_INTEGRATION_2026-10-08.md. Private-status/missing-owner-decision statements below are historical and superseded. Third-party license obligations and actual technical gates remain distinct.

**Founder ownership declaration (2026-10-08):** The founder states that all intellectual property constituting the original PCS project is entirely theirs. This is recorded as the founder's assertion and is the basis for the chosen Apache-2.0 public-core policy. It is not an independent audit of third-party materials or contractual rights. **No external-source/third-party rights entry is marked CLEARED yet.** Source attribution is not the same as the right to redistribute. This is a release checklist, not a license certification.

| Material | Observed source / scope | Current evidence | Clearance still required |
|---|---|---|---|
| PCS Python implementation and CLIs | `pcs/`, `scripts/` | Repository declares Apache-2.0; NOTICE credits PCS contributors | Ownership and contributor-rights record, employer/university/grant/collaborator obligations |
| PCS Lean 4 formalizations | `formal/`, root Lean bridge | Aristotle-assisted proof-development provenance recorded in repository; standard Lean toolchain pins | Original authorship, external research contributions, disclosure/patent rights, formal statements appropriate to publish |
| Submitted proof trajectories / AI-safety fixtures | proof-search/experimental corpus and tests | Project states consent-aware data collection | Exact provenance, consent and public-data scope for every redistributed training example; no private user submissions |
| Iris benchmark fixtures | `validation/real_world/iris_*.csv` | UCI Iris dataset DOI 10.24432/C56C76; README reports CC BY 4.0 and Rdatasets-derived rows | Preserve CC BY attribution, verify source/derivation, identify any required change notices |
| Indometh benchmark fixtures | `validation/real_world/indometh_subject1_observed.csv` | Public R `datasets::Indometh` / Kwan et al. (1976), 11 observations | Confirm redistribution rights for the exact source and preserve citation |
| Synthetic PK/PD and public demo fixtures | `examples/` | Project docs describe synthetic/public examples | Confirm no undisclosed unpublished constituent research, patient identifiers or protected laboratory data |
| Third-party Python packages | declared in `pyproject.toml`, not vendored by default | `cryptography`, `jsonschema`, test tooling | Review lock/source/container distribution and required third-party notices if packaged for release |
| CI/build service configuration | `.github/`, `.circleci/`, `scripts/core_ci_cloudflare.sh` in PR #74 | No-op CircleCI bridge and shared Cloudflare build token documented | Review logs and current/past credentials; isolate Cloudflare token before public PR builds |
| Website source | Separate `proof-carrying-science-site` GitHub repository | Public website, private Git repository | Separate release, D1/schema/data/privacy and license clearance if source is ever published |

## Release approvers' record

For every file or group to be released, record: repository/ref/blob SHA, author(s), provenance and derivative source, license and obligations, university/employer/collaborator permission (if relevant), publication/patent clearance, adjudication, reviewer, and date. **Leave missing information OPEN.**

## Licensing model

The current repository metadata declares Apache-2.0. An Apache-2.0 licensed component can be commercially redistributed by others under its terms. Keep *new* enterprise/domain features in separate appropriately licensed files/repositories only after confirming ownership and compatibility. Any existing Apache rights granted for prior distributions cannot simply be withdrawn.

**No patent, academic, employment, or contributor-rights clearance is asserted by this document.** Consult qualified IP counsel or your institution's technology-transfer office where relevant.

See `docs/PUBLIC_RELEASE_EXECUTION_2026-10-08.md`, `docs/PUBLICATION_FIREWALL.md`, `docs/CONSTITUENT_RESEARCH_LEDGER.md`, and issue #11.
