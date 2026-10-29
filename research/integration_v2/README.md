# Explicit combined-source qualification

The current contract is **V16**, under
`docs/integration/2026-10-29/RECONCILIATION_V16.json`. It retains the exact historical
70-PR census (69 reviewed source integrations plus held #117), original source
identities, reviewed adaptation reasons, modes and the complete combined tree.
It additionally pins the new public-study implementation, retained real-model
measurements, updated documentation and the fail-closed required-CI source check.
The original V12 manifest/control sources remain inspectable as historical data.

From a clean committed checkout:

```sh
python -m research.integration_v2.reconcile --require-committed
python -m research.integration_v1.source_gate
python -m pytest -q research/integration_v2/test_reconcile.py tests/test_integration_source_successor.py
```

Before publication, `--live` additionally compares the original frozen open-PR
census. Creating an integration PR or closing superseded PRs changes that census;
a mismatch must remain an honest refusal, not be bypassed. Ordinary committed
source checking verifies exact historical Git objects independently of open state.
Use a full-history checkout with the original branch objects available.

The manifest has a fixed digest compiled into the checker. There is no
accept/regenerate command. Its five trusted control paths are explicit and must
match committed HEAD in CI; all other tracked bytes/modes are pinned. Changed
files require a new reviewed successor. Git, Python, the host and checked-in
configuration remain trusted; these hashes are not an immutable security root.

The original phase-specific preservation programs and model-capture test files
remain byte-exact. Workflows explicitly select `integration_v2.boundary` and the
V16 whole-tree predicate. Four historical source assertions run unchanged at
their original commits, with current committed qualification before/after. All
other test nodes execute normally. No assertion or Lean verdict is mocked.

All 29 predecessor workflows remain constrained to the fixed pin and named
source/context-selection transformations. The new public-study workflow uses the
same combined boundary instead of claiming its old additions-only predicate is
true. Default public-study CI checks input tests and six fresh Lean theorems;
manual `real_models=true` additionally generates and receives actual weights.

Source review is not semantic equivalence, scientific acceptance, external partner
validation or deployment authority. [Current status](../../docs/integration/2026-10-29/README.md)
and [owner/external requirements](../../docs/integration/2026-10-28/OWNER_DEPENDENCIES.md)
retain those distinctions. PR #117 remains held; production authority and
Aristotle theorem statements are unchanged.
