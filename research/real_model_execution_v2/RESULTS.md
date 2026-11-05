# Checked execution observations

This phase hardens experimental provenance and process IO. It does not change
the finite safety specification, authorize a neural model for production, or
claim that the model has improved.

## Reproduced parent gaps

Using PR #186's actual preflight implementation and copies of its committed
corpus, all four mutations below were accepted. No capture/proposal bytes or
SQL state were changed, and no fake Lean verdict was supplied.

| Mutation | Parent preflight | New semantic audit |
| --- | --- | --- |
| Replace a generated token ID while retaining decoded text | Accept | Refuse |
| Replace a prompt token ID while retaining the prompt | Accept | Refuse |
| Flip the EOS flag while retaining the EOS token | Accept | Refuse |
| Alter the configuration digest in matching report/model metadata | Accept | Refuse |

The machine-readable observations are in `observations/parent-observations.json`.
The test suite independently reconstructs all four corruptions and runs both
actual validators. This is an evidence-integrity finding, not a demonstrated
effect-admission bypass in the original Lean authority.

## Actual-weight reproduction

The final implementation loaded **Qwen/Qwen3-0.6B** from a verified nine-file copy
of the original pinned bundle. The complete 1,503,300,328-byte safetensors file
has SHA-256
`f47f71177f32bcd101b7573ec9171e6a57f4f4d31148d38e382306f42996874b`.
Configuration, tokenizer, merge/vocabulary, generation configuration, license and
model-card files must also match the exact reviewed sizes and digests.

All **42 requests** reproduced the original input IDs, generated IDs, decoded text,
EOS status and exact proposal bytes. Every frame was bound to its fresh process
session, integer sequence and canonical request digest. The worker rechecked its
bundle and runtime sources, closed explicitly and exited successfully. The final
record is `observations/run.json`; all responses are retained, not just examples.

An earlier engineering implementation also matched all 42 requests. Before final
publication, replay intake was refined to freeze the input report hash and expected
capture/proof metadata before effects. The real-weight run was repeated with that
final code. Neither weights nor prompts were tuned. Both complete runs and the
earlier runtime source snapshot are retained in the local qualification package;
they are repetitions of the same 42 prompts, not 84 independent scientific samples.

The independent renderer/Rust-tokenizer path also matched Transformers 4.57.1 on
**64 deterministic Unicode/delimiter prompt pairs**, recorded in
`observations/differential.json`. Both paths share the Rust tokenizer algorithm;
the independent part is rendering, wrapper use and transcript-to-byte checking.

## Tests, proof scope and reproducibility

The focused suite passed **106 tests, zero failures/errors/skips**: 75 new tests
and the unchanged 31 parent experiment tests. It exercises actual pinned token
files, regular-file/FIFO/symlink/inventory rejection, copying followed by source
path replacement, failed-copy cleanup without adopting existing outputs, strict
JSON framing, real pipe read/write deadlines, EOS/control/unknown-token checks,
response correlation, credential-variable hygiene and malformed child shutdown.
It includes the new report's exact schema/type/source checks and verifies that
the returned input hash/expected capture bytes survive replacement of the input
report after preflight. Synthetic protocol fixtures make no authorization claim.

CI additionally runs all **272 unchanged supervisor/authority regressions** and
the actual native Lean/SQL replay of all 16 model/control episodes. Completed
commit identities, test artifacts and CI links are recorded in the stacked PR's
validation section. CI fetches the small pinned tokenizer bundle; it does not
download neural weights or claim new neural inference.

Replay requires all 42 new decoded proposal byte strings to equal the original
frozen capture inputs before effects. It then rebuilds the existing native
authority and checks actual SQL execution, exact receipts/capture bytes, final
rows and newly elaborated wire/row/path proofs. No producer proof source is
executed. Existing 52 runtime closures and per-episode proofs remain the formal
basis; this phase adds **zero general Lean theorems and zero axioms**.

## Limits and next milestone

The original result remains 30 interventions in 42 model turns, including unsafe
modeled publication and forbidden bypass requests. Checked reproduction improves
the credibility of those observations; it is not evidence of improved model
alignment. This is frozen-prompt inference followed by guarded replay of a fixed
synthetic workflow, not a new adaptive agent trial.

The verified copy, token checks, source digests and correlated pipes are tested
host mechanisms. Model-loader/memory interpretation, dependencies, Python/SQLite,
compiler/OS correspondence, complete tool modeling and faithful observations
remain assumptions. The copy is writable by the trusted host. Session IDs are
correlation values, not inference attestations. Process separation and omission
of configured credential variables do not establish hostile-host, network or
same-user isolation. No protected restart root or production deployment is added.

Next priorities are independently authored tasks and validated partial-observation
tool adapters, broader/larger models and adaptive attacks, and independently
controlled enforcement. Those studies must measure utility and intervention cost
as well as safety. No weights, proposal data or proof-development traces are used
for training in this phase.
