# PCS cross-project adapter protocol v1 — provisional, fail closed

**State:** isolated feature branch; **NOT** on protected `main`, not a production PCS authority, and not yet reproduced by core CI. Design remains compatible with the publication firewall: no unpublished CertiForge source, AI-safety code, theorem, research data, or results are imported.

## Interface and threat model

The producer (CertiForge, AI-safety, scientific tool or a synthetic reference producer) is **untrusted**. It may propose typed claims and pin exact input/output evidence bytes. It must not decide whether PCS considers a claim proved.

`pcs-adapter-proposal-v1` is a deliberately restricted interchange format; `python -m pcs.provisional_adapter_v1` is a local precheck, not an authoritative verification entry point.

1. `source`: project slug; 40-character source revision; explicit synthetic/private/public disclosure status. These are metadata, **not authenticated identity**.
2. `claim`: safe claim ID; bounded computational kind; human-readable statement. Human text cannot alter check semantics.
3. `artifacts`: 1–8 files bound to exact SHA-256 digests. Restricted relative paths only; no symlink, traversal, duplicate IDs/path aliases, or oversize content.
4. `check`: **registered and exact** check type. v1 supports `pcs.reference.identical_bytes.v1` and `pcs.reference.bounded_trace.v1` only. No fallback to a transcript's reported result.
5. `assumptions`: bounded, explicit statements, never hidden or used to promote the result.
6. **No PASS fields in the proposal**: any additional key is rejected. A signed or unsigned producer's `PASS` cannot bypass computation.
7. The result is always `kind: UNTRUSTED_ADAPTER_DIAGNOSTIC`, `authoritative:false`, `pcs_acceptance:NOT_EVALUATED`, and `claim_status:OPEN`. Even a local `LOCAL_CHECK_PASS` is **not** a PCS certificate, Lean proof, or assertion of scientific truth.

### Supported sample check semantics

- `identical_bytes`: compare two different, SHA256-pinned input files byte-for-byte. This proves only an actual finite byte equality in the Python reference implementation, **not** semantic equivalence of arbitrary transformed programs.
- `bounded_trace`: reject recorded events with forbidden action or cumulative risk greater than declared budget. This concerns supplied bytes only, **not** a deployed AI agent, actual observation, or log faithfulness.

The unregistered type `certiforge.something.PASS` is **rejected**, even with otherwise correctly hashed bytes. The Aristotle-discovered unknown-check fallback in the formal core is a separate P0 remediation still in progress; this provisional adapter never invokes or approves that path.

## Reproducible local synthetic example

From an installed PCS checkout:

```bash
python -m pcs.provisional_adapter_v1 \
  --envelope examples/adapter_protocol_v1/proposal.json \
  --root examples/adapter_protocol_v1
python -m pytest -q tests/test_provisional_adapter_v1.py
```

Expected: source files `before.txt` and `after.txt` contain the **exact** bytes `hello`, both pinned with SHA-256 `2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824`, yielding only `LOCAL_CHECK_PASS`. Mutating one byte, changing a path, adding `transcript_outcome:PASS`, or swapping the check type to an unsupported value fails closed.

The example `source.commit` is a synthetic 40-zero placeholder, **not** a real GitHub commit provenance claim. The CLI never downloads arbitrary sources or executes user-provided programs.

## Future production adapter: contract to prove, not bypass

1. Preserve independent project releases, source/history, authorship, IP owners, licenses, publication status and documentation. Core and website remain private.
2. Freeze each source version, source byte digest, artifact bytes, checker code digest, semantic theorem and required external-world assumptions. The producer may be arbitrarily large; the checker should be small, independently reviewable, and preferably kernel-checked.
3. Register the precise type and semantic target in PCS's explicit `check_registry_v06` and Lean `PCS.V2` authority. Reject unregistered checker tags at the authoritative boundary; never interpret a signed `PASS` by itself as truth.
4. When deriving a composite claim, independently verify each required evidence node, matching input/output artifact and claim semantics, bound trusted verifier, no unclosed obligation, and all declared assumptions. A cryptographic signature provides provenance only relative to an authorized key.
5. Require explicit trust contracts for machine-code/Lean binary correspondence, logs and real execution (`FaithfulLog`), external model adequacy and environmental claims. No unconditional deployed safety conclusion from a committed trace.
6. Run a clean Lean build + axiom audit, Python/Node suites, malicious/unknown-tag fixtures, independent replay and third-party reproduction at exact SHAs. Release only after the Aristotle unknown-type soundness patch and core CI restoration are verified.

The *first real CertiForge integration* should submit a **publicly describable, IP-cleared** finite transformed program and genuine equivalence proof/receipt to an independently pinned verifier. It should not claim generalized optimizer preservation from the synthetic identity-bytes example.

## Publication ledger

Update `docs/CONSTITUENT_RESEARCH_LEDGER.md` separately when actual constituent research becomes an authorized dependency. Until then this branch contains independently authored, domain-general interop vocabulary and synthetic fixtures only. No external research source has been copied.

**Cross-project integration acceptance criterion:** another independent machine checks the adapter's actual certificate, provenance and bounded theorem in PCS's formal authority, and a deliberately false or unknown-type signed attempt is rejected at the *same* authoritative decision boundary. This is **not** satisfied by this provisional interface alone.
