# PCS Semantic Translation Contract v1 — Runtime precheck (draft)

**Status:** Implemented Python candidate, **not kernel-certified**, **not PCS-authoritative**, and intentionally isolated from the concurrent Aristotle Lean task. No model was trained, no scientific conclusion was certified, and the existing v0.6 translation contract remains unchanged.

## How this builds on PCS

The production runtime extends the current `pcs-proof-translation-v1` / `pcs-claim-ir-v1` pipeline without changing its accepted syntax. The key entrypoints are `pcs/semantic_translation_v1.py`, `pcs/schemas/semantic_translation_v1.schema.json`, `scripts/run_semantic_translation_v1.py` and `pcs semantic-translation-v1` in the existing CLI. `attach_to_claim_ir` emits a separate `pcs-claim-ir-semantic-overlay-v1` artifact; it does not modify existing claim IR or turn an exploratory translation into a signed receipt. The **original** claim-IR content is rehashed using PCS's existing JCS canonicalization both at initial binding and at overlay export.

## A deliberately bounded semantic language

- Typed primitive variables and declared free variables, sort-indexed constants, registered typed atomic predicates, equality and inequality of terms of the same sort.
- `true`, `false`, `not`, `and`, `or`, `implies`, `forall`, `exists`, quantifier scope, explicit assumptions and declared context.
- Alpha-renamed bound variables normalize to nameless indices; order of assumptions is ignored but assumptions cannot be added, dropped or duplicated. Quantifier order, implication direction, predicate identity, negation, scope and variable binding are not normalized away.
- **Not supported:** arbitrary English semantics, unrestricted Lean syntax, temporal operators, modal operators, higher-order logic, computations on terms, floating-point arithmetic, implicit sort coercions, unrestricted inference and quantifier interchange.

A conservative syntactic match is not a proof of general semantic equivalence. Logically equivalent but structurally different propositions may be rejected.

## Input authority and trust

`registry.json` has `pcs-semantic-symbol-registry-v1` format and must be bound to a **separately approved SHA-256** supplied by the host; a model-provided hash is not trusted. Registered definitions have canonical IDs, declared arity/argument sorts and a definition digest. Reused canonical definition IDs and duplicate/shadowed symbol IDs reject. The registry's asserted definition digest is **metadata only** until separately bound to actual Lean source by the authority.

The `pcs-human-interpretation-v1` specifies the original words, selected structured meaning, interpretation scope, assumptions and unresolved ambiguity. A nonempty ambiguity list rejects. The exact interpretation's SHA-256 is required for the structurally-confirmed outcome. **A digest supplied on a command line does not authenticate the human.** The host still needs an authorized, audited confirmation workflow; an LLM can compute a digest but cannot thereby grant authority.

Model proposals use `pcs-semantic-translation-candidate-v1`. Model confidence is informational only, but must be a finite number in [0,1] if present; unknown or malformed values reject. Inline `proof_receipt` and `elaboration_receipt` fields are **rejected** until an independent verifier and proof-level bridge exists; they cannot be self-attested by a proposer. Unregistered definitions, duplicate grounding, incorrect definition hashes and unsupported syntax reject.

`pcs-semantic-translation-decision-v1` output has deterministic error codes and one of:
- `REJECTED` (invalid structure, grounding, ambiguity, symbols, receipts, claim binding or other mismatch),
- `NEEDS_CONFIRMATION` (structure accepted, independent selection digest missing/mismatched),
- `STRUCTURALLY_CONFORMANT_NONAUTHORITATIVE` (structure and supplied digest match, **still not certified**).

All results set `authoritative: false`, and unverified bridges remain blocking: Python-checker to Lean refinement, external elaboration, external proof/kernel receipt, and production PCS executable authority. Untrusted candidate bytes never enter the required check registry as a certified built-in or bypass the existing authority.

## Explanation IR and structural round trip

`pcs-explanation-ir-v1` stores the deterministic normalized conclusion, assumptions, bindings, scope, trusted **registry metadata**, known limitations and references. The new `explanation_roundtrip_check` detects changes to conclusion/assumptions/scope/grounding/limitations and returns `ROUNDTRIP_MISMATCH`. It does not assert that a stylistic natural-language renderer is semantically correct or that arbitrary prose can be back-translated. Explanation reports include the statement that human intent is not proved.

## CLI example

From the repository root:

```bash
python - <<'PY'
import json
from pathlib import Path
from pcs.semantic_translation_v1 import sha256, interpretation_digest
root = Path("examples/semantic_translation_v1")
reg = json.loads((root/"registry.json").read_text())
human = json.loads((root/"interpretation.json").read_text())
print("approved_registry_sha256 =", sha256(reg))
print("selected_interpretation_sha256 =", interpretation_digest(human))
PY

pcs semantic-translation-v1 \
  --registry examples/semantic_translation_v1/registry.json \
  --approved-registry-sha256 REPLACE_WITH_INDEPENDENTLY_APPROVED_REGISTRY_HASH \
  --interpretation examples/semantic_translation_v1/interpretation.json \
  --candidate examples/semantic_translation_v1/candidate.json \
  --confirmed-interpretation-sha256 REPLACE_WITH_AUTHORIZED_SELECTION_HASH \
  -o semantic-decision.json
```

The first command prints *candidate commitments only*; a trusted reviewer must verify the selected objects and approve hashes out of band. Omit the confirmation flag to obtain `NEEDS_CONFIRMATION`. Do not paste production secrets or unpublished human research into the synthetic demo.

Equivalent lower-level CLI: `python scripts/run_semantic_translation_v1.py --registry ...`. Optional `--claim-ir` binds an original `pcs-claim-ir-v1` artifact by claim ID, unchanged human statement and verified JCS SHA-256; `--overlay` writes a non-authoritative integration artifact.

## Acceptance evidence and adversarial tests

```bash
python -m pip install -e '.[dev]'
python -m pytest -q tests/test_semantic_translation_v1.py
python -m pytest -q
python -m compileall -q pcs scripts tests
bash scripts/core_ci_cloudflare.sh
```

The final full gate requires the pinned Lean toolchain and exact integrated source. The adversarial unit tests include quantifier swaps, negation changes, dropped and added assumptions, variable capture, hallucinated symbols, name/definition shadowing, false confidence, forged proof/elaboration receipts, tampered Claim IR and explanation round trip. A local partial test is not a Lean PASS. **Never report a full build PASS unless it actually completes on the current exact Git revision.**

## Training and research boundary

A learned translator may propose structured interpretations, candidates and repair actions. Training labels must be attached to the checker version, approved registry version, selected interpretation digest, source revision, human authorization evidence and exact deterministic reason code. **No Aristotle-generated text is presumed to be model training truth.** Store private human/user data only under explicit scope and consent. Distinguish structural rejections from failures of semantic denotation, human intent, formal proof or empirical validity.

## Outstanding formal bridge for Aristotle

The following are OPEN: independently defined typed denotation, correctness of normalization and binder handling, interpretation-to-typed-AST parsing, Python ↔ Lean serialization and validator refinement, binding of registry IDs/digests to real Lean constants, independent elaboration/kernel proof evidence, signed human-confirmation authority, and final existing PCS authority integration. The exact Lean AST and meaning equivalence theorems must be compared against Aristotle's implementation **without weakening its soundness hypotheses**.

**Defensible present claim:** the *tested Python implementation* rejects the enumerated structural failures, emits Explanation IR and reason codes, and **never grants** PCS authority. It is not a formally verified natural-language translator.

## Signed interpretation confirmation (2026-10-08 extension)

For production-quality approval provenance, use `pcs/semantic_confirmation_v1.py` with `pcs/schemas/interpretation_confirmation_v1.schema.json`. A separately authorized reviewer signs the canonical JSON approval body with Ed25519. PCS verifies:

1. A host-configured **approved public key** supplied outside the model/proposal channel (the receipt never chooses its own trust anchor).
2. The exact claim ID, interpretation SHA-256, approved registry SHA-256 and optional Claim IR SHA-256, all inside the signed bytes.
3. Domain separation `PCS_INTERPRETATION_CONFIRMATION_V1\x00`, signer signature, nonce, issued/expiry timestamps and a maximum 30-day receipt lifetime.
4. The typed candidate's semantic invariants **after** verifying the receipt. A valid signature cannot override a quantifier or other semantic rejection.

The time source and reviewer key custody are external trust assumptions. The signer must actually have authority to approve the selected interpretation and keep the private key secret. The public key should be rotated/revoked if compromised; an approval receipt does not prove real human intent or scientific truth. Reuse is possible within its validity interval; preventing replay across distinct sessions, if required by a workflow, needs external nonce-state management.

Example of the standalone CLI **after an external reviewer has legitimately signed the receipt**:

```bash
pcs semantic-translation-v1 \
  --registry examples/semantic_translation_v1/registry.json \
  --approved-registry-sha256 <trusted_registry_digest> \
  --interpretation examples/semantic_translation_v1/interpretation.json \
  --candidate examples/semantic_translation_v1/candidate.json \
  --confirmation-receipt approved-interpretation-receipt.json \
  --approved-confirmation-public-key-hex <independently_pinned_signer_public_key_hex> \
  -o decision.json
```

This path sets `confirmation_authenticated: true` and records the receipt commitment after successful signature verification, but `authoritative: false` remains mandatory. The old `--confirmed-interpretation-sha256` option remains as a **digest-only** provisional path and always sets `confirmation_authenticated: false`. Supplying both confirmation methods rejects.

`python -m pytest -q tests/test_semantic_translation_v1.py tests/test_semantic_confirmation_v1.py` tests malformed and forged receipts, signature/key mismatch, statement/registry/claim misbinding, clock window, schema validation, quantifier attacks after valid human approval, and signed CLI behavior. These are executable tests, **not Lean refinements**.


### Exact-byte structural equality hardening

The Explanation IR round-trip checker now compares canonical serialized JSON bytes, not Python equality. Python considers `True == 1`, but those have different meanings in a typed AST (a Boolean must never be accepted in place of a de Bruijn binder index). The corresponding negative regression test explicitly verifies this rejection. The isolated suite now includes **73 passing tests**.
