# PCS ‚Äî Executable AI-Safety Assurance Report

> **Superseded in part (fail-closed update).** `pcs-lean-authority` now rejects any evidence
> whose `check_spec.type` is missing or unregistered (`REJECT:unsupported_check_type`) and any
> supported AI-safety/biology claim not bound by its own certified evidence
> (`REJECT:claim_binding`). The counterexample archive below is now **rejected** in both modes
> (`GoldenCx.cx_rejected`, `cx_entries_rejected`, `cx_cli_rejected`); `cx_accepts` was replaced by
> `legacyAuthority_cx` (acceptance by the old transcript-fallback authority only), and
> `executableAuthorityWith_nil` is now one-directional. See `PCS_FAIL_CLOSED_REPORT.md`.

This report covers the run that follows the generic-domain soundness work
(`PCS_GENERIC_DOMAIN_SOUNDNESS_REPORT.md`). All earlier results (`domain_adapter_sound`,
`root_assurance_sound`, `untrusted_proposer_cannot_forge_assurance`, `pipeline_refines`,
`pcs_generic_domain_archive_acceptance_sound` and its certified/extended variants, the
biology / AI-safety / ML-evaluation witnesses, and the counterexample suite) are unchanged
and still build. Their trust boundaries are also unchanged.

New production modules (all imported by `PCS.lean`, so they build as part of the default target):

| File | Content |
|---|---|
| `PCS/V2/ExecutableAuthority.lean` | the executable authority now runs the certified checker registry; refinement and soundness theorems |
| `PCS/V2/Ed25519Sign.lean` | a test-only RFC 8032 Ed25519 *signer*, used only to produce fixtures |
| `PCS/V2/Witnesses/AISafetyGolden.lean` | the golden AI-safety archive builder and its literal signatures |
| `PCS/V2/Witnesses/AISafetyCampaign.lean` | golden-archive theorems and the adversarial campaign |
| `PCS/V2/ExternalWorld.lean` | `ExternalWorldBridge` and the external-world transfer theorems |
| `PCS/V2/Witnesses/AISafetyDeployment.lean` | the AI-safety bridge (committed trace ‚ü∂ deployed run) and a proof that its premise is needed |
| `PCS/V2/DistributedContributors.lean` | distributed-contributor admission protocol and its non-authority theorems |
| `PCS/V2/ClaimGraphMemo.lean` | completeness of `checkGraph`, the memoized checker, and its equality with the spec |
| `PCS/V2/ExecutableAudit.lean` | `#print axioms` for every major new result |
| `tools/WriteAISafetyGolden.lean` | writes `fixtures/ai_safety_golden/` from the Lean builder |
| `PCS/V2/Golden/*.lean` (later run) | kernel proof that the executable authority accepts the golden archive; byte-level link to the committed files; `Golden/Audit.lean` prints axioms |
| `PCS/V2/{KernelRfl,KernelEq,SHA256Fast,SHA256Memo,Crc32Memo,SplitOnFuel,ZipComplete,AuthorityCLI}.lean` (later run) | kernel-evaluation support (each a proved rewrite), ZIP decoder completeness, the CLI's pure verdict function |
| `tools/CheckGoldenFileLiterals.lean` (later run) | checks that the byte literals equal the committed fixture files |

---

## 1. The certified checker registry is now on the executable path

### What changed in the executable

`PCSAuthority.lean` (the root of the `pcs-lean-authority` executable) used to print the verdict
of the production authority (`diagnoseArchiveWithTranscript` / `diagnosePCSWithTranscript`). It
now prints:

* `--zip` mode: `PCS.V2.DomainAuthority.executableAuthority transcript {pk, expected} raw`
* directory mode: `PCS.V2.DomainAuthority.executableAuthorityEntries transcript {pk, expected} entries`

The command-line interface and output format are the same as before: `ACCEPT` or
`REJECT:<stage>`, and a plain `REJECT` for a directory-mode partition failure.

```lean
def productionCheckers : List DomainChecker := Instances.witnessRegistry
  -- residue_bounds, hydrophobic_score (biology), trace_invariant (AI safety)

def buildRegistry (ks : List DomainChecker) : Option (List CertifiedChecker)
  -- some (registry ks) iff tags pairwise distinct and disjoint from the 6 built-in tags

def executableAuthorityWith (ks : List DomainChecker) (t : AuthorityTranscript)
    (T : TrustAnchor) (raw : ByteArray) : String :=
  match buildRegistry ks with
  | none => "checker_registry"
  | some cs => diagnoseArchiveWithCheckers cs t T raw

def executableAuthority (t : AuthorityTranscript) (T : TrustAnchor) (raw : ByteArray) : String :=
  executableAuthorityWith productionCheckers t T raw

def certifiedRegistry : List CertifiedChecker := registry productionCheckers
SECB1„ﬁ˜È»ZÆ