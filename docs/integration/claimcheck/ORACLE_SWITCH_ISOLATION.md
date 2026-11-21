# Development-only oracle switches: exposure, and the minimal isolation needed before a public release

**Analysis and requirements only.** Nothing described here is implemented by this document. The
scientific policy (`research/claimcheck_v1_1/policy.py`) and all frozen v1 material are unchanged.
Prepared 2026-11-19 at the owner's request.

## 1. The switches

`policy.assess_document(ctx, receipts, *, tau=TAU, oracle_siblings=False, oracle_receipts=False)` has
two development switches. Both are off by default.

| Switch | What it does when on | What it is for |
| --- | --- | --- |
| `oracle_receipts` | `established_status` accepts a receipt marked `oracle_predicted_only: true` at its summary fields, without kernel-accepted variants | development analysis and offline tests: `dev.common.oracle_receipts_raw` builds receipts whose arithmetic is predicted by the untrusted Python oracle instead of the kernel |
| `oracle_siblings` | `assess_document` builds sibling readings whose match is predicted by the Python oracle, and lets them corroborate. A weak match can then become CONFIRMATION, and a proved mismatch DISCREPANCY_FOR_REVIEW. The record marks each such sibling `"kernel_checked": false` | development evaluation, where siblings were not kernel-checked; the verification pipeline kernel-checks siblings as ordinary receipts |

## 2. Who passes them today

| Caller | `oracle_receipts` | `oracle_siblings` | Status |
| --- | --- | --- | --- |
| `verify.py` (the verification pipeline) | no | no | outward |
| `export_site_v11.py` (the website catalog) | no | no | outward |
| `dev/evaluate.py`, `dev/adversary.py` | yes | evaluate: yes | development |
| `prospective/score.py` `demo()` | no | yes | development demonstration on cached kernel receipts |
| `tests/test_v11_offline.py` | yes | yes / no | tests |

`tests/test_oracle_opt_in.py` enforces the outward rows: `verify.py` and `export_site_v11.py` must
pass neither switch, and every function that builds oracle receipts must opt in literally.

## 3. What a misuse would do (demonstrated, 2026-11-19)

Four receipts were built with `oracle_receipts_raw` for sentences about the offline test table. All
four are marked `oracle_predicted_only`, and none was put to the kernel.

| Call | Verdicts |
| --- | --- |
| `assess_document(ctx, receipts)` | UNKNOWN ×4 |
| `assess_document(ctx, receipts, oracle_receipts=True)` | CONFIRMATION ×3, DISCREPANCY_FOR_REVIEW ×1 |

So the default path is fail-closed: an oracle-marked receipt has no kernel-accepted variant, so
`established_status` gives NOT_ESTABLISHED and the verdict is UNKNOWN. This holds whoever crafted
the receipt. But a single keyword argument in an outward caller would let a receipt that anyone can
write produce a confirmation or a discrepancy with no kernel run. With `oracle_siblings=True`,
verdicts can rest on siblings the kernel never checked. The final fail-closed check in `_decide`
covers the main receipt's status, not its corroborators.

Today's control is a test, not a runtime barrier. It catches the two known outward callers, and any
function that builds oracle receipts. It would not catch a new outward caller added outside the
listed files.

## 4. Minimal runtime isolation required before any public release

None of these changes a verdict rule. Each is small, and each has a test that shows it.

| # | Requirement | Minimal implementation | Test that must accompany it |
| --- | --- | --- | --- |
| I1 | **The public entry point has no development switch.** | `policy.assess_document(ctx, receipts, *, tau=TAU)` keeps only `tau`. The switch handling moves to a private function, for example `policy._assess(ctx, receipts, tau, *, oracle_siblings, oracle_receipts)`, called by the public function with both off. `dev/` and the tests call the private function explicitly. | the public signature has exactly `ctx`, `receipts`, `tau`; a call with a switch raises `TypeError` |
| I2 | **Oracle-marked input is refused at the public boundary, explicitly.** | In the public function, any receipt carrying `oracle_predicted_only` (or another non-kernel origin marker) gets UNKNOWN with the reason "development receipt; not kernel-checked", before any other rule. This is today's effect made an explicit rule. | the four receipts above give UNKNOWN ×4 through the public function, with that reason |
| I3 | **Corroboration must be kernel-checked in public output.** | In the public function, a verdict whose `corroborated_by` contains `"kernel_checked": false` is withheld (UNKNOWN). With I1 this cannot occur; the check guards against regressions. | a decision built through the private function with oracle siblings is withheld by the public wrapper |
| I4 | **The release artifact contains no development path.** | The public package or deployment excludes `dev/`, `tests/` and the `score.demo` command. A release check fails if any shipped module imports `research.claimcheck_v1_1.dev` or calls the private function. | the release check run on the artifact |
| I5 | **New outward callers are covered automatically.** | Replace the fixed `PIPELINE` list in `tests/test_oracle_opt_in.py` with a scan of every module outside `dev/` and `tests/`. | the scan finds the two known callers and fails on a planted one |

**Acceptance for I1 to I5:**

* the whole v1.1 suite passes;
* the development results regenerate byte-identically: `dev_arms.json` on every recorded value,
  `dev_adversary.json`, the draft-3 demonstration, `DESIGN_120.json` and `DECISION_SUPPORT.json`;
* the website catalog re-exports byte-identically.

Implementation needs the owner's authorisation, because it touches `policy.py` (outward-verdict
code), though not its rules. It should be done before any public release or any outward caller
beyond `verify.py` and the site export.

## 5. What isolation does not cover

* **A consistent lie in the kernel record itself** (a receipt claiming kernel acceptance that never
  happened). Only re-running the kernel, the replay, detects it. A receipt is a report, not a
  verification.
* **The website's own receipt rule** (decision D4) is separate JavaScript and does not call the
  Python policy.
* **The prospective protocol:** the real run's outward decisions come from the verification
  pipeline (step 4), which passes no switch. The demonstration on development data uses
  `oracle_siblings=True` and says so in its output (`policy_flags`).
