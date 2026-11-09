Independent references use `scientific-reference-v4`. They are AI-assisted internal
annotations prepared from original papers, data, and author code, without reading
the new scientific interpreter/checker source or outputs. They are not qualified
external expert validation.

Every annotation contains `id`, `project_id`, `split`, `kind`, `statement`, `source`,
`typed_expectation`, `expected_status`, `evidence_kind`, `verification_expectation`,
`assumptions`, `required_obligations`, and `label_provenance`.

`source` has a project-relative `path`, original-byte `sha256`, exact UTF-8 `quote`,
and half-open `byte_start`/`byte_end`. Optional `additional_sources` uses the same
shape. Quotes bind evidence; matching quote text does not itself establish the
typed interpretation or scientific verification.

`typed_expectation` follows v3: `kind`, `entity`, `scope`, `relation`, `value` or
`canonical_rhs`, `quantity_role`, `unit`, and `conditions`. Kinds include `quantity`,
`equation`, and `scientific_claim`. Substantive causal, empirical, reproducibility,
and model-validity claims remain in scope even when automation must abstain.
`conditions` is structured source context. `unit: null` means no explicit unit is
declared for that claim. `caveats` is reviewer explanation, never a literal text
that the candidate must emit to receive credit.

`expected_status` is source support (`supported`, `contradicted`, or
`insufficient_evidence`). `evidence_kind` records the source's evidence level.
`verification_expectation.status` separately says `supported` or `unknown` at its
explicit `level`; a paper's report does not establish numerical reproduction,
formal validity, uncertainty calibration, or empirical truth.

Each study has 15–25 supported annotations and five reviewer-authored counterprobes.
Counterprobes do not assert that the authors made the claim. Each study also has
eight `workflow_utility_rubric` questions with `required_annotation_ids`,
`required_check_scopes`, and `expected_answer: supported|unknown`. Utility requires
answering principal scientific questions with the necessary evidence and an
appropriate support boundary, including useful explicit unknowns.

Final source identities and labels stay outside the developer worktree until
software, protocol and annotation hashes freeze. Later fixes are post-hoc.
