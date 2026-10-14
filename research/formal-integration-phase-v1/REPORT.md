# PCS formal integration phase: receiving verification

Status at 2026-10-14: implemented and individually checked finite-model action
shield and signed conditional-guard replay; full new Aristotle library remains
pending protected kernel qualification. PR #109 is a draft. This report does not
promote either a partial proof build or producer-supplied proof logs.

## Current source and supplied research

The initial protected source audit used core
`c600b007940881fd65fe41d2adddd5f002679478`, site
`a6a9a54bb8f2e8fb45f783a9df56929aca11a54b`, and CertiForge
`c71e8575db2800b015a9d444f8ed572490f3a871`. Handoff PR #108 was subsequently
merged through the ordinary protected gate after all ten required contexts passed
on head `8e9720034b631520c5d020f3f67465987a750e44`, run `38584900099`.
Core main became `c627995627e19411746c5b368b22649b03e224e9`; the integration
branch incorporates it. Site and CertiForge source are unchanged.

The new Aristotle archive has SHA-256
`8ec6dcfe96c8171ff64343ed53a29e0d1c7af194a323e02c707d5b6e959cebca`.
Its source comparison identifies 673 newly supplied public theorem declarations
in the 68-module conditional-runtime library. The returned root build files were
not substituted. Original proof bytes, historical failed attempts and source
manifests remain separate from receiving verification. See
`../aristotle-conditional-runtime-v1/REPORT.md` for the exact boundary.

The separate AI-safety research path supplied by the user is a Windows-local
directory, `C:\Users\amarena\Documents\Codex\2026-09-13\google-drive-plugin-google-drive-openai-2`.
It is registered on the local desktop host but unavailable to this cloud
filesystem. Its contents have not been inspected, validated or integrated. The
shield work below is a first-party continuation, not a result attributed to that
external material. An attached archive is needed to complete that research audit.

## Implemented assurance capability

An untrusted policy proposes actions in a declared finite nondeterministic model.
The receiving checker validates all declared successors, regenerates a private
literal-model Lean proof, and proves safety by induction for every finite admitted
history. It checks outcomes absent from a submitted log and does not bound the
history length. The executable shield rejects unknown, malformed and unsafe
proposals. Certificate limits are 32 states, 16 actions, 512 edges/allowed pairs,
and natural identifiers below 65536.

A signed v0.6 package additionally binds an original Boolean admission guard and
its proposed equivalent replacement to the model and allowed table. A separate
receiving process regenerates the model proof, checks the real conditional
equivalence decision, checks the complete modeled state/action domain, and binds
the exact receiving code and formal source snapshots. The executable
`admit_guarded_action` requires both model closure and guard equivalence before
admission. Guard packages support at most 24 allowed pairs. Resource exhaustion
does not establish equivalence or permit admission.

The four new typed claims have explicit proof obligations and three open
deployment premises: model completeness, exclusive shield enforcement and
faithful state observation. The existing certificate authority leaves all four
unregistered claims OPEN. Separate replay reports scoped mathematical support;
it does not silently extend the authority registry. Liveness and deployed-world
safety remain OPEN, including for an all-deny shield.

## Exact new mathematical results

Independently compiled first-party general results:

- `PCSActionShield.check_iff_certified`: the executable finite certificate checker
  is equivalent to the declared closure predicate.
- `PCSActionShield.admitted_histories_safe`: every finite admitted modeled history
  stays in safe states and contains no forbidden action.
- `PCSActionShield.optimized_guard_histories_safe`: the same conclusion for a
  guard with explicit `GuardMatches` correspondence.
- `PCSActionShield.deployed_histories_safe`: concrete histories satisfy the model
  invariant under an explicit `Correspondence` structure.
- `PCSConditionalShield.equivalent_guard_matches`: the conditional decision
  derives guard correspondence under explicit task-context and source-encoding
  hypotheses.
- `PCSConditionalShield.conditional_guard_histories_safe`: composes that
  correspondence with universal modeled-history safety.

Each accepted literal model independently elaborates
`PCSActionShieldReplay.certificate_checked` and
`PCSActionShieldReplay.all_finite_histories_safe`. The four general shield
theorems use only `propext` and `Quot.sound`; the conditional bridge also uses
`Classical.choice`. These are standard Lean axioms. Producer proof text is never
executed as receiving authority.

Pending full new-library qualification, not yet counted as independently admitted:

- `PCSCR.Py.python_conditional_refines_reference`.
- `PCSCR.Js.javascript_conditional_refines_reference`.
- `PCSConditionalShield.python_runtime_and_guard_histories_safe`.
- `PCSConditionalShield.javascript_runtime_and_guard_histories_safe`.

The latter two explicitly combine extracted heap receipt correspondence and the
independently established guard-history result. They do not derive a trusted
decision from an arbitrary producer receipt. Python retains `ValidateAccepts`
and `DigestOK`; JavaScript additionally retains `JValidateAccepts`, `JExactOK`,
`JIntegerOK` and bounded task syntax. Actual CPython/V8/compiler/OS behavior,
JSON parsing, SHA-256/JCS and deployed-world correspondence are not proved.

## Executed evidence and exact commits

- Shield final campaign: 53 actual kernel cases, 27 accepts and 26 rejects,
  zero mismatches, 57.331705 seconds. Seven static negative controls and 33 shield
  tests passed. Cases are first-party synthetic finite models, not external
  empirical observations. Source seals and all individual results are retained
  under `../action-shield-v1/final/`.
- Clean `8b9001fcc155fb7ff3e84f92d3c13208bde44bdf`: complete Python execution
  had 1,785 passes, three fixture failures, one optional skip and one warning.
  Failures came from contribution tests deriving a repository identity from the
  worktree folder. The production gate correctly rejected that identity.
  The optional actual-prover control separately passed with `PCS_REQUIRE_PROVER=1`.
- Repaired clean `45cbdb393e53955f0eb6876e346ab3e93da7ebb0`: all seven
  contribution fixture tests and all 15 assurance tests passed (22 total).
  Production contribution rules were unchanged. The assurance regression also
  rejects an equivalent guard on a model with an unsafe initial state.
- At `8b9001f`, existing campaigns rejected all 25 foundational attacks and all
  12 v0.6 hardening attacks, with zero false accepts.
- Signed campaign at `45cbdb3`: eight independent receiving processes produced
  all expected outcomes. The valid case passed; seven authentically re-signed
  report/source/proof/artifact/premise/claim attacks failed semantic replay even
  though package integrity passed. The temporary private key was destroyed; the
  public key, exact packages, receiver outputs and byte inventory are retained
  in `signed-guarded-shield-45cbdb3/`. Positive package SHA-256 is
  `87a4d8ac46ab0b8f732f9897094ca9f7dc4c8e3c4aabbb08100e5ed60b7ffa04`.
- Exact unchanged site `a6a9a54`: complete Node suite, 425 passes, zero failures
  or skips, 64.953 seconds. Exact unchanged CertiForge `c71e857`: locked Rust
  workspace suite, 25 passes, zero failures.
- Historical synthetic scientific-transport evidence was independently replayed:
  package validity, replay consistency and its bounded contract passed;
  scientific acceptance stayed false. This is no new scientific discovery.

Final independent review found that the first 478-name declaration scan omitted
195 inline-attribute declarations. The complete inventory must cover 673 names;
the 478-name source gate is partial evidence, not a full axiom audit.

The initial protected run `38591704320` failed because a source-reading
prerequisite had not been built. The fix explicitly builds it. Current run
`38636060406` tests head `8b9001f` against current main `c627995`; eight component,
portability, source-policy and learning-loop lanes passed. Its full core gate is
still checking the new conditional library. No complete protected pass is claimed.
The later `45cbdb3` changes require their own final protected run before merge.

The approved Lake extension is accepted by two exact full-file hashes and exact
baseline-prefix/extension-tail checks. Historical manifests are unchanged.
Mutations to the environment, theorem inventory, source limits, counters, digests
and axiom inventory remain rejected; no source-integrity wildcard was introduced.

## Adoption boundary and remaining work

The independently replayable finite-model shield is useful for bounded research
models with explicit trusted deployment premises. Signed receiver replay is
available for researchers to inspect and reproduce. This is experimental,
reviewable assurance, not a global AI-safety or scientific-validity certificate.
Full Aristotle build/audit, four-way extracted/native parity and final protected
integration remain outstanding. The external Windows research remains missing.

The mathematical intelligence reports retain their original v4 outcome: primitive,
neural and reinforcement methods each 0/22, strong portfolio 9/22. No model was
promoted, no superiority result was inferred, and no untrusted proof-generation
trace was used for training. The 59-workstream status remains historical until
new independently executed evidence supports a specific update.
