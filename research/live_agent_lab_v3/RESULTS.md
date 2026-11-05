# Live agent lab: observed results

The final registered default plan was written before model inference. It ran the
actual full Qwen3-0.6B weights through the hardened PR #187 worker, now conditioned
on actual current SQL broker observations and the last executed action. This is
a new closed-loop execution experiment, not reuse of a frozen prediction sequence.
Weights, greedy nonthinking decoding and the 32-token budget were unchanged.

| Observation | Model episodes | Deterministic controls |
| --- | ---: | ---: |
| Episodes completed | 12 | 4 |
| Proposals / committed transitions | 42 | 16 |
| Model proposals corrected | 42 | Not counted as model behavior |
| Malformed model outputs | 42 | Separately labeled invalid-format control |
| Typed unsafe/forbidden model requests | 0 / 0 | Separately labeled controls |
| Final public output | Approved fixed summary only | Approved fixed summary only |

**All 42 model responses were Markdown-fenced JSON**, for example:

````text
```json
{"action": 0}
```
````

The instruction required a plain action object. The strict parser correctly
returned `MALFORMED_FALLBACK` for these responses; it did not strip fences, extract
JSON or reinterpret their apparent intent. The actual native authority selected
preauthorized progressing alternatives and the real SQL effects completed within
the existing 4/3-step fixture bounds. Thus 100% supervised completion is **not**
100% model protocol adherence. The low typed-unsafe count reflects format failure,
not safe model judgment. All original response bytes, tokens and observations are
preserved in `demo/suite.json` and each source-bound capture.

The earlier plain-observation corpus had no malformed model outputs and 30/42
interventions. The current protocol changes the observation representation and
adds executed-action feedback. This uncontrolled comparison is a concrete format
fragility observation, not a causal estimate, population claim, improved-model
finding or adaptive learning result. No prompt tuning, output repair, weight
update, successful-case selection or training was performed in this experiment.

## Actual checks

Every one of the 58 committed transitions used the actual native action/row gate
and SQLite transactions. The run received 48 newly elaborated wire/row/path proof
source files (80 captured theorem closure instances) and the unchanged 52 audited
runtime closures. No new general theorem or axiom was added.

An independent local receiving invocation replayed all 16 episodes, with no new
neural inference. The exact captures, receipts, final rows and regenerated proof
inventories matched. CI repeats receiving execution on a separate runner. Final
commit identities, complete test counts, artifact checksums and CI results are
recorded in the stacked PR and retained local qualification report.

Focused testing includes all prior experiment/execution tests plus plan bounds,
safe IDs, schema/type aliases, exact live observation/response/receipt binding,
invalid model dialogue, unsupported proof claims, symlink/FIFO/oversized input,
full intake before effects, immutable submitted snapshots, honest readiness/view
status, output preservation, HTML/script escaping, safe links and complete CI
aggregation. Two actual native integration tests also exercise the live bridge
and replay after all submitted source files are replaced following preflight.
No positive verifier or model authorization is mocked.

The first development tamper test serialized a float through JCS, which normalized
`0.0` into `0` before intake. The fixture was corrected to retain hostile JSON
spelling, with no validator relaxation. Its initial failure is retained alongside
the final passing reports. This was a test-fixture defect, not evidence of a
successful numeric-alias bypass.

## Usability evidence

The lab offers a readable `doctor`, `run`, `demo`, `view` and `replay` CLI. The
recorded demo needs the small pinned decoder and exact Lean toolchain, not model
weights or Torch. The live path supports bounded operator plans and explicit case
selection while keeping the fixed policy and tool set unchanged. Console progress
uses action/stage names and distinguishes setup from actual verification.

The offline report distinguishes loaded claims from checked live execution and
receiving replay; explains malformed output; provides workflow navigation,
collapsible cases, raw proposals and proof links. Headless Chromium checks at
1280 and 390 widths verified no horizontal overflow, keyboard disclosures and
navigation, no active content, and no page-content network requests or dialogs.
Hostile task/title text was escaped. These are browser smoke observations, not
formal UI proofs, complete accessibility certification or human-user validation.

## Open obligations

The workflow still uses synthetic payloads and a constant public summary. It does
not validate realistic redaction, arbitrary tool effects, model alignment or broad
agent utility. Faithful observations and complete tool modeling, exclusive
mediation, Python/SQLite/model-loader/compiler/OS correspondence and host integrity
remain assumptions. Prepared files and same-user processes are not an immutable
security boundary. There is no protected restart root or production deployment.

The next useful experiment is a **separately versioned, audited structured-output
decoder or model-native tool protocol**, preserving this raw baseline and testing
its token-to-byte correspondence. It must not silently repair this recorded study.
Independently authored tasks, realistic validated adapters/partial observations,
larger/multiple models and adaptive attacks should follow, with utility and
intervention cost measured alongside policy preservation.
