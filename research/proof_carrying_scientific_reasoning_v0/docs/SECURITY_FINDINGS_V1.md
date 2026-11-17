# SECURITY_FINDINGS_V1 — Independent review reproduction

**Branch head at reproduction:** `518aa06847a7abbee07825f6b40d2206191cdf07`  
**Checker under test:** `independent_checker/check_certificate.py` (pre-hardening)  
**Artifacts (immutable reproducers):** `results/security_findings_v1/*.json`  
**Date:** 2026-11-17 (America/New_York)

Do not modify the JSON reproducers after recording. Hardened checkers must reject A/Bneg/C; F is a trust-boundary finding (label alone ≠ established math).

## Finding A — Unjustified conjunction introduction

**Class:** Forged derivation / unbound rule output.

**Reproducer:** `results/security_findings_v1/finding_A_forged_andI.json`  
Sole premise `atom 0`; claimed `andI` conclusion `atom 42 ∧ atom 99`; support `[0]`; authority `mathVerified`.

**Observed:** `ACCEPTED` by pre-hardening checker.

**Root cause:** `andI` only checks that the conclusion is syntactically an `and` and support is non-empty. No citations to prior judgments; claimed conjuncts never verified.

## Finding B — Unjustified conjunction elimination

**Class:** Forged elimination / missing premise judgment.

**Negative:** `finding_B_forged_andE1.json` — `andE1` of `atom 42` with no prior conjunction. **Observed: ACCEPTED.**

**Positive control:** `finding_B_valid_andE1_control.json` — structurally well-formed hyp/andI/andE1 chain. **Observed: ACCEPTED** (but acceptance does not prove step linking; same weak path).

**Root cause:** `andE1`/`andE2` only check that authority is in RANK; no reference to a prior `and` judgment.

## Finding C — Authority escalation via max-rank bound

**Class:** Spec/implementation mismatch on meet vs max.

**Reproducer:** `finding_C_authority_escalation_andI.json`  
Premises empirical + mathVerified; `andI` claims conclusion authority `mathVerified`.

**Spec:** `Authority.meet` = GLB by rank (minimum).  
**Checker:** allows authority rank ≤ **max** of support premise ranks.

**Observed:** `ACCEPTED` (unauthorized escalation relative to meet semantics).

## Finding D — Abstract `Certificate.valid` ignores `steps`

**Location:** `lean/ScientificReasoning/Certificates.lean`

```lean
def Certificate.valid (c : Certificate) : Prop :=
  Derives c.context c.finalSupport c.finalAuthority c.conclusion
```

**Analysis:** Validity is existence of *some* derivation of the final judgment, not validation of the recorded `steps` trace. Therefore `valid_implies_sound` does **not** establish that a submitted certificate's proof steps are correct. A certificate with garbage steps and a hypothetically true final judgment (or even empty steps with a Hyp that matches) is “valid” abstractly without step integrity.

**Required fix:** Executable `checkCertificate` over structured steps with citations; prove `checkCertificate c = ok j → Derives …`.

## Finding E — Classical entailment vs derivability non-explosion

- `Entails` uses Boolean assignments; inconsistent Γ has no model ⇒ classical entailment of every φ is **vacuous**.
- Calculus has **no ExFalso**; `no_ex_falso_unrelated_atom` is a **derivability** property.

**Claim boundary:** v0 must not advertise “semantic paraconsistency” from classical `Entails` alone. Investigate Belnap/FOUR or similar for semantic non-explosion (Phase 6).

## Finding F — Self-declared `mathVerified`

**Reproducer:** `finding_F_self_declared_mathVerified.json`  
Author labels an arbitrary atom as `mathVerified`; Hyp accepts.

**Observed:** `ACCEPTED`.

**Root cause:** Authority is an untrusted certificate field. Declared ≠ established.

**Policy:** Separate `DeclaredAuthority` from `EstablishedAuthority`. Hyp may carry declared labels; certificates must expose that mathematical verification of empirical content is **not** established unless an external attestation boundary is separately qualified (deferred). Checker must not treat declared math as stronger than external trust.

## Finding G — Rank collision and meet order dependence

`assumption` and `empiricalAsserted` share rank 2.  
`meet a b := if rank(a) ≤ rank(b) then a else b` ⇒ when ranks equal, **left operand wins**.

```
meet(assumption, empiricalAsserted) = assumption
meet(empiricalAsserted, assumption) = empiricalAsserted
```

Not commutative as a classification operation; only rank-min is commutative. Equal ranks ≠ equal classifications.

**Fix direction:** Multi-dimensional assurance (math dimension × evidence kind) or commutative meet on a lattice of product labels; stop treating equal-rank labels as interchangeable.

---

## General defect classes (not just examples)

1. Unbound rule conclusions (forged intro/elim).  
2. Missing step citations / forward refs / cycles.  
3. Authority bound using max instead of meet.  
4. Abstract existence validity ≠ trace checking.  
5. Classical explosion under inconsistency vs rule-level non-explosion.  
6. Unauthenticated authority labels.  
7. Non-commutative meet under rank ties.

## Reproduction command (frozen artifacts)

```bash
cd research/proof_carrying_scientific_reasoning_v0
PYTHONPATH=independent_checker python3 -c "
import json, check_certificate as c, pathlib
for p in sorted(pathlib.Path('results/security_findings_v1').glob('finding_*.json')):
  try:
    c.check(json.loads(p.read_text())); print(p.name, 'ACCEPTED')
  except Exception as e:
    print(p.name, 'REJECTED', e)
"
```

At head `518aa068`, A / B_forged / C / F accept. After Phase 1 hardening, A / B_forged / C must reject; F remains accepted only as “declared math label with disclosure,” never as established kernel verification of empirical content.
