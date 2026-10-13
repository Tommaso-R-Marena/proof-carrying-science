# Runtime output refinement v3 evidence

These artifacts support [the continuation report](../../docs/PCS_RUNTIME_REFINEMENT_CONTINUATION_REPORT.md).
The actual source is selected from the owner's Apache-2.0 CertiForge repository at
`c71e8575db2800b015a9d444f8ed572490f3a871`. The copied source declarations preserve
their exact bytes; the authored native fixture uses the selected local crates.

`verification.json` and `verification.log` preserve the final positive check and both
expected fresh kernel source-mutation rejections. `native_output_controls.rs` is the
fixed 40-assertion integration fixture. `pytest.log` records 32 passing gates.
`initial-elaboration-failure.log`, `kernel-attempt-2.log`, and `kernel-attempt-3.log`
preserve failed and successful proof development. `initial-verification-pass.json`
and `.log` preserve the first full positive receipt before source-freezing and resource
metadata were strengthened.

The manifest binds these artifacts and source files with SHA-256. It is an unsigned
integrity inventory, not an external attestation or scientific certificate. There are
no human trajectories, private data, credentials, training results, or claims of
model superiority in this dataset.
