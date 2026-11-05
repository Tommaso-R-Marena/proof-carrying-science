# Prioritized proposals catalog

**PROPOSALS ONLY — entries describe candidate future Codex/Aristotle work. None of these items are claimed as completed evaluation results.**

Format: `pcs-independent-program-proposals-v1`
Proposal count: 9

| ID | Priority | Title | Affinity | Status |
| --- | --- | --- | --- | --- |
| `E-P01` | 1 | Case-insensitive path collision gate in CI | program_assurance, reviewer_adoption | `proposal` |
| `E-P02` | 1 | Automated sibling-branch nonoverlap report in draft PR CI | program_assurance | `proposal` |
| `E-P03` | 2 | Cross-workstream inventory dashboard from PRESENT reports only | program_assurance | `proposal` |
| `E-P04` | 2 | Unified residual-trust rollup across OPEN_TRUST_ASSUMPTIONS | repro_tcb, program_assurance | `proposal` |
| `E-P09` | 2 | Offline assurance card for external reviewers | assurance_card, reviewer_adoption, program_assurance | `proposal` |
| `E-P05` | 3 | Adversarial protocol corpus expansion beyond JCS/ZIP fixtures | protocol_adversarial | `proposal` |
| `E-P06` | 3 | External-lab burden measurement with human participants | reviewer_adoption | `proposal` |
| `E-P07` | 3 | Aristotle-facing formalization candidates from inadequacy examples | scientific_falsification, program_assurance | `proposal` |
| `E-P08` | 4 | Reconstruction campaign across additional Python/OS matrices | repro_tcb | `proposal` |

## Details

### E-P01 — Case-insensitive path collision gate in CI

- **Priority:** 1
- **Status:** `proposal` (proposal — not claimed done)
- **Affinity:** program_assurance, reviewer_adoption
- **Summary:** Wire the collision scanner as a required check on independent_eval/** so CHECKLIST.json vs checklist.json class failures are caught before merge.
- **Rationale:** Workstream D hit a repository-integrity failure from dual checklist filenames that collide on case-insensitive filesystems.

### E-P02 — Automated sibling-branch nonoverlap report in draft PR CI

- **Priority:** 1
- **Status:** `proposal` (proposal — not claimed done)
- **Affinity:** program_assurance
- **Summary:** Run the nonoverlap auditor against the known independent-eval branches (and PR #120 pilot) and fail soft with a posted artifact when overlaps appear.
- **Rationale:** Parallel workstreams A–D plus the scientific pilot must remain path-disjoint; manual NONOVERLAP.md alone does not detect drift.

### E-P03 — Cross-workstream inventory dashboard from PRESENT reports only

- **Priority:** 2
- **Status:** `proposal` (proposal — not claimed done)
- **Affinity:** program_assurance
- **Summary:** Publish a rolling program inventory that aggregates TEST_INVENTORY / BUGS / OPEN_TRUST_ASSUMPTIONS / TECHNICAL_REPORT when present, marking MISSING otherwise — never inventing counts.
- **Rationale:** Program-level assurance needs a single view without duplicating A–D harness code.

### E-P04 — Unified residual-trust rollup across OPEN_TRUST_ASSUMPTIONS

- **Priority:** 2
- **Status:** `proposal` (proposal — not claimed done)
- **Affinity:** repro_tcb, program_assurance
- **Summary:** When sibling OPEN_TRUST_ASSUMPTIONS.md files exist, extract structured assumption IDs into a program-level residual-trust index.
- **Rationale:** Trust boundaries are currently per-workstream; synthesis is needed for Codex/Aristotle follow-on formalization proposals.

### E-P09 — Offline assurance card for external reviewers

- **Priority:** 2
- **Status:** `proposal` (proposal — not claimed done)
- **Affinity:** assurance_card, reviewer_adoption, program_assurance
- **Summary:** Ship a one-command JSON/HTML assurance card that separates authority-lane `pcs verify` from non-authority inspection classes for any evidence bundle.
- **Rationale:** Reviewers need a single offline artifact that is usable without learning the full PCS toolchain, without conflating inspection with acceptance.

### E-P05 — Adversarial protocol corpus expansion beyond JCS/ZIP fixtures

- **Priority:** 3
- **Status:** `proposal` (proposal — not claimed done)
- **Affinity:** protocol_adversarial
- **Summary:** Continue expanding malformed-intake / signature / lock mutation families on Workstream A; treat further growth as ongoing evaluation, not a security proof.
- **Rationale:** Protocol surface area grows with new claim kinds and archive encodings.

### E-P06 — External-lab burden measurement with human participants

- **Priority:** 3
- **Status:** `proposal` (proposal — not claimed done)
- **Affinity:** reviewer_adoption
- **Summary:** Use the external_lab kit to run a real participant study; do not treat checklist completion as EXTERNAL_VALIDATION_COMPLETE.
- **Rationale:** Workstream D intentionally forbids claiming completed external validation from synthetic fixtures alone.

### E-P07 — Aristotle-facing formalization candidates from inadequacy examples

- **Priority:** 3
- **Status:** `proposal` (proposal — not claimed done)
- **Affinity:** scientific_falsification, program_assurance
- **Summary:** Catalog computationally-supported-but-inadequate cases as candidate proof obligations for future formal work — labeled proposals only.
- **Rationale:** Scientific falsification surfaces gaps between computational support and empirical adequacy that formal methods might later address.

### E-P08 — Reconstruction campaign across additional Python/OS matrices

- **Priority:** 4
- **Status:** `proposal` (proposal — not claimed done)
- **Affinity:** repro_tcb
- **Summary:** Extend cross-environment reconstruction sampling when alternate interpreters/hosts are available; record absences rather than treating them as passes.
- **Rationale:** TCB residual trust shrinks only with measured environments.
