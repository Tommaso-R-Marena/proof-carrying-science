# PCS: what the executable's `ACCEPT` means for arbitrary archives

> **Superseded in part (fail-closed update).** `pcs-lean-authority` now rejects any evidence
> whose `check_spec.type` is missing or unregistered (`REJECT:unsupported_check_type`) and any
> supported AI-safety/biology claim not bound by its own certified evidence
> (`REJECT:claim_binding`). The counterexample archive below is now **rejected** in both modes
> (`GoldenCx.cx_rejected`, `cx_entries_rejected`, `cx_cli_rejected`); `cx_accepts` was replaced by
> `legacyAuthority_cx` (acceptance by the old transcript-fallback authority only), and
> `executableAuthorityWith_nil` is now one-directional. See `PCS_FAIL_CLOSED_REPORT.md`.

This report covers the push from *one* kernel-checked golden archive to **every** archive and
transcript. The subject is the pure decision function run by `pcs-lean-authority`.

## 0. Checkpoint

The complete state before this work is the git tag
`checkpoint-golden-results-before-generalization`. Since that tag, the only change to an
existing file is one added line in `PCS.lean`, which imports the new audit module. Every other
change is a new file. The golden acceptance, committed-trace safety and deployed-run theorems
(`PCS/V2/Golden/*.lean`) are byte-for-byte unchanged. They still build, and their axiom audit
(`PCS/V2/Golden/Audit.lean`) still prints on every build.

## 1. What existed, and what was missing

| Existing result | What it says |
|---|---|
| `executableAuthority_refines_certifiedAuthority` | `executableAuthority t T raw = "ACCEPT"` ⇔ the certified extended authority accepts `raw` |
| `executableAuthority_sound` | `ACCEPT` ∧ `NoForgery` ⇒ frontier-strength `ExtendedAssurance` plus domain propositions for domain-accepted claims |
| `executableAuthority_domain_sound` | `ACCEPT` ⇒ every AI-safety claim **domain-accepted with some obligation graph** holds of the committed traces (no `NoForgery`) |
| `aiSafetyGoldenArchive_accepts`, `…_committed_safe`, `…_deployed_safe` | kernel-checked facts about the one golden archive |

The general theorem `executableAuthority_domain_sound` already quantified over all archives.
However, its conclusion is gated by `domainAccepts A r cid g`, and that check is **not run by the
executable**: the obligation graph `g` is not an input of `pcs-lean-authority`. The missing
bridge was a statement about the executable's verdict **alone**, phrased in terms of the bytes
the executable reads. A second gap was negative: a kernel-checked rejection, as opposed to a
rejection observed from the binary.

## 2. New theorems (all files new; all proofs complete)

### 2.1 General positive bridge (`PCS/V2/ExecutableGeneral.lean`)

Every statement below quantifies over **all** raw byte strings `raw` (or entry lists `es`),
**all** transcripts `t` and **all** trust anchors `T`. None of them assumes `NoForgery`,
`FaithfulLog` or anything about the transcript.

**Domain-independent form**, for any registered certified checker:

```lean
theorem executableAuthority_registered_evidence_sound {t : AuthorityTranscript}
    {T : TrustAnchor} {raw : ByteArray} (h : executableAuthority t T raw = "ACCEPT") :
    ∃ es inp r, decodeZip raw = some es ∧ CanonicalZip raw es ∧
      fromArchiveEntries es = some inp ∧ certifiedAuthority t T raw = some (inp, r) ∧
      verifyCertBytes inp.certificateBytes = some r.pkg.cert ∧
      decodeCertModel r.pkg.cert = some r.model ∧
      artifactTable r.model inp.files = some r.table ∧
      ∀ k ∈ productionCheckers, ∀ e ∈ r.model.evidence, e.outcome = .pass →
        isCheckType k.tag e.json = true → k.Holds (requestFor r.pkg.cert r.model r.table e)
```

**AI-safety form, stated on the archived member bytes:**

```lean
theorem executableAuthority_trace_evidence_sound {t : AuthorityTranscript} {T : TrustAnchor}
    {raw : ByteArray} (h : executableAuthority t T raw = "ACCEPT") :
    ∃ es inp c m, decodeZip raw = some es ∧ CanonicalZip raw es ∧
      fromArchiveEntries es = some inp ∧ verifyCertBytes inp.certificateBytes = some c ∧
      decodeCertModel c = some m ∧
      ∀ e ∈ m.evidence, e.outcome = .pass → isCheckType "trace_invariant" e.json = true →
        ∃ a b f, parseTrace e.json = some (a, b, f) ∧
          ∃ art ∈ m.artifacts, ∃ bytes, art.id = a ∧ (art.path, bytes) ∈ es ∧
            PCS.V2.SHA256.sha256 bytes.dataM�mx�g!j�