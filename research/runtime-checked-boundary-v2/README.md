# Runtime checked boundary v2 evidence

This directory preserves executed evidence for the exact current CertiForge checked
wrapper, described in [the technical report](../../docs/PCS_RUNTIME_CHECKED_BOUNDARY_REPORT.md).

`verification.json` is the positive kernel/native receipt and contains both expected
fresh kernel source-mutation failures. `verification.log` is its command summary.
`pytest.log` records 18 passing gate tests. `native_controls.rs` is the fixed authored
31-case native fixture. `initial-native-fixture-failure.log` preserves the fixture's
initial unsupported `Clone` assumption. `negative-condition.log` preserves the first
independent fresh altered-snapshot rejection before both controls were incorporated
into the repeatable verification command.

The Rust source snapshot comes from the owner's Apache-2.0 CertiForge repository at
`c71e8575db2800b015a9d444f8ed572490f3a871`; see its existing license and the source
binding in the report. The native fixture is authored project test code. There are
no human research trajectories, private inputs, external model labels, or production
credentials in these artifacts. The manifest is an unsigned integrity inventory;
it supplies neither external attestation nor scientific authority.
