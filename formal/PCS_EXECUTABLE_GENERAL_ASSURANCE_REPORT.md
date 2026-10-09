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
            PCS.V2.SHA256.sha256 bytes.data.toList = art.sha256 ∧
            TraceSafe bytes.data.toList b f
```

In words: if the executable prints `ACCEPT`, then `raw` is a canonical ZIP. Take any evidence
item that the parsed signed certificate records as `PASS` with the certified tag
`trace_invariant` and parameters `(a, b, f)`. The ZIP member that holds artifact `a`, whose
digest is bound by the certificate, has exact bytes satisfying the bounded invariant: action `f`
never occurs, and cumulative risk stays ≤ `b` after every step.

Variants with the same content:

- `executableAuthorityEntries_trace_evidence_sound`: directory mode, `executableAuthorityEntries`.
- `zipModeOutput_trace_evidence_sound`: the **command-line function**. The hypothesis is that
  `zipModeOutput archive transcriptBytes keyB64 fp = some "ACCEPT"` for arbitrary file contents,
  key string and pin. The conclusion adds that the transcript bytes decode.
- `executableAuthority_trace_claim_sound`: the **claim-level, graph-free** form. Take a
  certificate claim whose signed predicate the AI-safety adapter decodes to `tc`. Every trace
  of `tc` that is covered by a `PASS` evidence item accepted by the adapter's leaf check has
  safe archived bytes. If every trace is covered, then `aiDomain.Holds r.table tc`.
  `executableAuthority_domain_sound` reaches the same conclusion but needs an obligation graph;
  this version states the coverage condition directly on the signed certificate.
- `executableAuthority_deployed_trace_safe`: the **deployed-run form**. It holds for every
  deployed run `ew` with `FaithfulLog r.table ew`, which is an explicit premise.

How the proof reuses earlier results: `executableAuthority_refines_certifiedAuthority`, then
`acceptPCS_sound` (stage facts), then `replayOK_spec`, then `authorityWith_faithful` with
`replayFaithful_reported`, then `registry_valid`. Its only new ingredients are small stage
lemmas (`verifyPackage_cert`, `acceptPCSWithCheckers_stages`, `certifiedAuthority_stages`,
`lookup_files_mem`) and `aiLeafCheck_spec`.

### 2.2 General negative bridge (same file)

The contrapositive is stated **only in terms of pre-acceptance parsing** of the input:

```lean
theorem executableAuthority_rejects_unsafe_trace_evidence {raw : ByteArray}
    {es : List (String × ByteArray)} {inp : PackageInput} {c : CertV2} {m : CertModel}
    (hz : decodeZip raw = some es) (hi : fromArchiveEntries es = some inp)
    (hc : verifyCertBytes inp.certificateBytes = some c) (hm : decodeCertModel c = some m)
    {e : CertEvidence} (he : e ∈ m.evidence) (hpass : e.outcome = .pass)
    (ht : isCheckType "trace_invariant" e.json = true)
    {a : String} {b f : Nat} (hp : parseTrace e.json = some (a, b, f))
    (hunsafe : ∀ art ∈ m.artifacts, art.id = a → ∀ bytes,
      lookup inp.files art.path = some bytes → ¬ TraceSafe bytes.data.toList b f)
    (t : AuthorityTranscript) (T : TrustAnchor) :
    executableAuthority t T raw ≠ "ACCEPT"
```

Directory mode: `executableAuthorityEntries_rejects_unsafe_trace_evidence`. Rejection holds for
**every** transcript and **every** trust anchor. No choice of key, signer or signature can turn
a certified `PASS` over an unsafe trace into `ACCEPT`.

### 2.3 Kernel-checked rejections of concrete archives

- `PCS/V2/Golden/Rejection.lean`, the **swapped-trace attack**. `tamperedRaw` is the golden
  archive with only the trace member replaced by `[0,1,2,4,1,7]`. The original certificate,
  genuine signatures, manifest, wire and index are kept.
  - `tamperedRaw_rejected (t T) : executableAuthority t T tamperedRaw ≠ "ACCEPT"`
  - `tamperedEntries_rejected` (directory mode)
  - `golden_vs_tampered`: same transcript and anchor; the golden bytes give `ACCEPT` and the
    tampered bytes do not.
- `PCS/V2/Golden/Insider.lean`, the **insider re-signing attack**, campaign mutation `m1`. The
  certificate is consistently rebuilt for the unsafe trace: correct digests, hashes, wire, index
  and manifest. `E1` is recorded as a `PASS` `trace_invariant` replay. The *original*
  transcript-only production authority accepts this archive (`#guard` in the campaign file).
  - `insider_rejected_entries (csig psig t T) : executableAuthorityEntries t T (m1.entriesWith csig psig) ≠ "ACCEPT"`
    holds for **all signature byte strings**, so it covers the genuine test-key signatures an
    insider would produce.
  - `insider_rejected_zip (csig psig) (hz : decodeZip raw = some (m1.entriesWith csig psig)) t T : executableAuthority t T raw ≠ "ACCEPT"`.
    That the concrete `m1.build` decodes to these entries is checked by evaluation, not by the
    kernel: proving it would require running Ed25519 *signing* inside the kernel.

These proofs evaluate no signature and, for the swapped trace, no hash. They follow from the
general rejection theorem plus a kernel-checked parse of the certificate.

### 2.4 Impossibility of the unconditional claim-level statement (kernel-checked)

`PCS/V2/GoldenCx/Counterexample.lean` uses the archive `cxRaw`. It is consistently built and
signed: trace `[0,1,2,4,1,7]`; claim `C1` with predicate `ai.trace_invariant`, budget 4,
forbidden action 7; evidence tagged with the **unregistered** `trace_invariant_v2`; and a
transcript reporting `PASS`.

- `cx_accepts : executableAuthority cxTranscript goldenAnchor cxRaw = "ACCEPT"` is proved in the
  kernel stage by stage. This includes both Ed25519 verifications and every hash. The stage
  files `PCS/V2/GoldenCx/{Provenance,Provenance2,Crypto,Stages,PackageStage,PackageStage2,AuthorityStage}.lean`
  are mechanical clones of the golden stage files, with literals regenerated by
  `tools/GenCxLiterals.lean`; that generator is untrusted because every literal is re-derived
  in the kernel.
- `cx_claim_false`: the accepted claim `C1` decodes to `⟨["trace"], 4, 7⟩`, PCS records it at
  decision level `computational`, and `¬ aiDomain.Holds resultV.table ⟨["trace"], 4, 7⟩`.
- The impossibility statement:

  ```lean
  theorem no_unconditional_claim_bridge :
      ¬ ∀ (t : AuthorityTranscript) (T : TrustAnchor) (raw : ByteArray),
          executableAuthority t T raw = "ACCEPT" →
            ∃ inp r, certifiedAuthority t T raw = some (inp, r) ∧
              ∀ cl ∈ r.model.claims, ∀ tc, aiAdapter.decode cl.predicate = some tc →
                aiDomain.Holds r.table tc
  ```

- `cx_no_graph_accepted (g c) : domainAccepts aiAdapter resultV "C1" g ≠ some c`. This agrees
  with the existing generic theorem: on this accepted archive **no** obligation graph, honest or
  adversarial, domain-accepts `C1`. It is derived from soundness rather than by enumerating
  graphs.

**Why it fails, in one sentence.** The executable does not interpret claim predicates, and an
evidence item with an uncertified tag gets its `PASS` from the transcript
(`ExecutableLimits.uncertifiedTag_passes_unsafe`). So `ACCEPT` certifies a claim's truth only
through `PASS` evidence with a **certified** tag. That is exactly the hypothesis of §2.1.

Further obstructions (`PCS/V2/ExecutableLimits.lean`):
- `certifiedTag_fails_unsafe`: the certified tag on an unsafe trace replays as `FAIL` for
  **every** transcript. A transcript cannot override a certified checker. Consequently a
  certificate that honestly *records* `FAIL` passes the replay stage. `ACCEPT` alone, without
  `PASS`, therefore implies nothing about safety.
- Deployed runs require `FaithfulLog`. This was already shown necessary by
  `committed_safe_deployed_unsafe`.

## 3. What is proved, what is trusted, what needs `FaithfulLog`

**Proved about the pure executable decision** (`executableAuthority`, `executableAuthorityEntries`,
`AuthorityCLI.zipModeOutput`), for all inputs:
- `ACCEPT` ⇒ for each `PASS`, certified-tag `trace_invariant` evidence item, the archived member
  bytes satisfy `TraceSafe`. Digest binding and canonical ZIP decoding are part of the
  conclusion, not assumptions.
- The claim-level corollary under certified-tag coverage.
- Rejection of every archive whose certificate records a certified `PASS` over unsafe bytes.
  This holds for every transcript and key.
- No hypothesis about cryptographic authenticity is needed for these committed-bytes
  statements. `NoForgery` is needed only for *attribution* (who signed), as in
  `executableAuthority_sound`.

**Trusted, outside the kernel proof:**
- That the compiled binary computes the Lean function. This covers the Lean compiler, runtime
  and C toolchain.
- The I/O half of `PCSAuthority.main`: file reads, `println`, directory traversal and its member
  order.
- The transcript, for evidence with **uncertified** tags. Its reports are taken at face value.
  §2.4 shows this trust is unavoidable for such evidence.
- That the fixture files on disk match the Lean literals. This is checked by
  `tools/CheckGoldenFileLiterals.lean` for the golden archive only. The new fixtures under
  `fixtures/ai_safety_{tampered,insider,counterexample}/` are written from the Lean values by
  `tools/WriteGeneralFixtures.lean`. They are an operational cross-check, not evidence.

**Needs `FaithfulLog`:** any statement about a *deployed* run, i.e.
`executableAuthority_deployed_trace_safe` and the golden `aiSafetyGoldenArchive_deployed_safe`.
Without it, PCS speaks only about committed bytes.

**Canonical decoding** is not an assumption anywhere: `decodeZip_sound` / `CanonicalZip` appear
in the conclusions.

## 4. Axiom audit

`PCS/V2/ExecutableGeneralAudit.lean` prints the axioms of all 19 new headline results on every
build. Each depends only on `[propext, Classical.choice, Quot.sound]`; there is no
`Lean.ofReduceBool`, so no `native_decide`. The golden audit files are unchanged and print the
same.

The production sources contain no `sorry`, `admit` tactic, `axiom` declaration, `unsafe`,
`extern`, `implemented_by` or `native_decide`. Search results: occurrences of "unsafe" are prose
about unsafe traces, and `admit` is the existing function name in `DistributedContributors.lean`.

## 5. Build and commands

```
lake build                       # default targets PCS + pcs-lean-authority
# → Build completed successfully (245 jobs).  Only warning: existing unused variable in
#   PCS/V2/SHA256.lean:137.

lake env lean --run tools/CheckGoldenFileLiterals.lean     # → OK
lake env lean --run tools/WriteGeneralFixtures.lean        # writes the three new fixtures

F=fixtures/ai_safety_golden;  .lake/build/bin/pcs-lean-authority --zip $F/archive.zip $(cat $F/pk.b64) $F/observations.json $(cat $F/fingerprint.hex)   # ACCEPT
F=fixtures/ai_safety_tampered;       …   # REJECT:package
F=fixtures/ai_safety_insider;        …   # REJECT:replay
F=fixtures/ai_safety_counterexample; …   # ACCEPT   (the kernel-checked counterexample)
```

The `*.zip` files are ignored by git (`.gitignore`); regenerate them with the commands above.

New kernel-evaluation cost, roughly: `GoldenCx` stage files about 9 minutes in total (as for
the golden archive), `Golden/Insider.lean` about 2 minutes, everything else seconds.

## 6. What remains open

- A kernel proof that the concrete `m1.build` bytes decode to the insider members. The rejection
  is proved for every byte string that decodes to them; the decoding itself is checked only by
  `#guard`.
- Directory-mode member *order* from the filesystem is not modelled. As before, the theorems
  quantify over the entry list.
- Domains other than AI safety get only the domain-independent form
  (`executableAuthority_registered_evidence_sound`). A per-domain byte-level corollary like
  §2.1 would be a short specialisation of it.
- Nothing here is a claim of global AI safety. The property is the declared bounded invariant
  of committed traces.
