# CERTIFICATE_SPECIFICATION_V1

**Schema version:** `1`  
**Status:** research-only; supersedes the unbound v0 JSON used at `518aa068`.

## Design principles

1. The checker **reconstructs** each judgment from rule + citations; claimed formula/support/authority fields are optional and must match if present.
2. Every non-hyp step cites earlier step indices only (`0 ≤ j < current`).
3. Authority on conclusions is the **meet** (rank-min with commutative tie-break) of cited judgments’ declared authorities — never max.
4. Premise `declared_authority` is **untrusted input**. `math_established` is always `false` for Hyp unless an external attestation record is present (v1: attestation unsupported ⇒ always false).
5. Resource limits: max premises 256, max steps 1024, max formula depth 64, max PropId 2^31-1, reject non-int IDs / bool-as-int.

## JSON schema (conceptual)

```json
{
  "schema_version": 1,
  "premises": [
    {"id": 0, "formula": ["atom", 0], "declared_authority": "empiricalAsserted"}
  ],
  "steps": [
    {"id": 0, "rule": "hyp", "premise_id": 0},
    {"id": 1, "rule": "hyp", "premise_id": 1},
    {"id": 2, "rule": "andI", "left": 0, "right": 1},
    {"id": 3, "rule": "andE1", "from": 2}
  ],
  "conclusion_step": 3
}
```

### Rules

| Rule | Required fields | Reconstruction |
|---|---|---|
| `hyp` | `premise_id` | formula ← premise.formula; support ← `[premise_id]`; declared ← premise.declared_authority; math_established ← false |
| `andI` | `left`, `right` | formula ← `and(L.φ, R.φ)`; support ← L.S ++ R.S; declared ← meet(L.a, R.a); math_established ← L.m ∧ R.m |
| `andE1` | `from` | require `from.φ = and φ ψ`; conclude φ; inherit support/declared/math |
| `andE2` | `from` | dual |

### Rejection classes

Unknown rule; missing/forward/cyclic refs; duplicate step ids; non-contiguous or mismatched `steps[i].id`; wrong formula shape; support/authority mismatch vs reconstruction; conclusion_step OOB; schema_version ≠ 1; malformed JSON types; duplicate premise ids; PropId not JSON integer (reject `true`); depth/size limits.

### Relation to Lean

`CheckCertificate.checkCertificate` mirrors this reconstruction. Acceptance ⇒ `Derives` (proved). Python independent checker must agree on the finite fragment under differential tests.
