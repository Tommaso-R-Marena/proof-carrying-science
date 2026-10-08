# Summary of changes for run 34bc6452-b7bb-4147-b44f-5084e1d84178
`pcs-lean-authority` now fails closed. If any evidence item's `check_spec.type` is missing or unregistered, the verdict is `REJECT:unsupported_check_type`, in both `--zip` and directory mode. The transcript can no longer supply a replay outcome. A correctly signed archive is therefore not accepted just because its signatures verify. The full `lake build` succeeds (255 jobs), and the axiom audit, fixture tests and golden-file check all pass. Full details are in `PCS_FAIL_CLOSED_REPORT.md`.

**What the executable now does** (`PCS/V2/FailClosedGate.lean`, `PCS/V2/ExecutableAuthority.lean`)
- Replay outcomes come only from the six verified built-in checkers and the three registered domain checkers. Anything else falls back to a constant `FAIL`, never to the transcript.
- A new check-type gate runs before replay and covers *every* evidence item, including items no claim requires.
- I also found a second default-accept path while checking claim aggregation. A claim recorded as supported was accepted once its evidence replayed, even if that evidence certified different parameters. Now every supported AI-safety or biology claim must be backed by its own certified evidence through the checked obligation graph; otherwise the verdict is `REJECT:claim_binding`.
- Directory mode and ZIP mode go through the same decision path.

**Inputs that now fail** (all were `ACCEPT` before)

| fixture | new verdict |
|---|---|
| signed counterexample archive (type `trace_invariant_v2`, false claim) | `unsupported_check_type` |
| unknown type with a *safe* trace | `unsupported_check_type` |
| evidence with no type at all | `unsupported_check_type` |
| valid claim plus an extra unrequired `external_python` item | `unsupported_check_type` |
| claim budget 2 backed by evidence that certifies budget 4 | `claim_binding` |

The golden archive is still `ACCEPT`, the tampered one still `REJECT:package`, and the insider one still `REJECT:replay`.

**Backward-compatibility cost:** any archive that uses a check type outside the nine registered ones is now rejected, even if no claim depends on that item. A new type is supported only by registering a certified checker for it.

**Kernel-checked theorems about the actual decision functions** (`executableAuthority`, `executableAuthorityEntries`, `zipModeOutput`, `dirModeOutput`), for every input, transcript, key and fingerprint pin:
- **Rejection:** `*_rejects_unregistered_type` in four forms (zip, directory, and the two command-line wrappers), plus `*_rejects_false_supported_ai_claim`.
- **Concrete fixtures:** `cx_rejected`, `cx_entries_rejected`, `cx_cli_rejected`, `cx_signed_but_rejected`. The last one shows the archive is signature- and package-valid, was accepted by the old authority, and is rejected now. There are also rejection theorems for four campaign fixtures, valid for every signature pair (`m7`, `m7b`, `m7c`, `m15`).
- **Acceptance:** on `ACCEPT`, every evidence outcome comes from a certified checker (`executableAuthority_evidence_certified`). Every supported AI-safety or biology claim holds of the committed bytes, with no extra graph, `NoForgery` or transcript assumption (`executableAuthority_supported_claims_sound`). The verdict is the same whatever the fallback is (`acceptPCSStrictWith_fallback_irrelevant`).
- The golden-acceptance and refinement theorems were re-proved.

**Theorems removed or weakened:**
- `cx_accepts` and the old impossibility theorem were replaced by `legacyAuthority_cx` and `legacy_no_unconditional_claim_bridge`. These now describe only the old transcript-fallback authority, which is kept for analysis but no longer run by the binary.
- `executableAuthorityWith_nil` now goes in one direction only (strict `ACCEPT` implies old `ACCEPT`); the converse is false.
- `executableAuthorityEntriesWith_nil` was removed.

**Still not proved, or still trusted:**
- The compiler, runtime and file IO are trusted.
- The transcript is still used for the workflow and environment checks and for transcript binding; it no longer affects replay outcomes.
- Claims outside the AI-safety and biology domains (e.g. PK/PD, chemistry) only get the evidence-level guarantee.
- Statements about the deployed world still need the separate external-world hypotheses.
- The earlier generic theorems are unchanged and still proved.

**Checks run**
- `lake build`: succSECB1ßžwéÈZ®