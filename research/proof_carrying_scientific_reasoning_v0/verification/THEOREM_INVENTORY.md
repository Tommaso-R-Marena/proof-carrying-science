# Theorem inventory (Phase II)

Toolchain: Lean **4.28.0**. No `sorry` / `admit` / custom axioms.

| Theorem | File | Claim | Axioms |
|---|---|---|---|
| `derives_sound` | Soundness | Derives ⇒ classical Entails | propext |
| `derives_support_in_context` | Soundness | support ⊆ ids | propext, Quot.sound |
| `meet_comm` / `meet_empirical_not_math` | Authority | commutative meet; empirical ≰ math | none |
| `no_ex_falso_unrelated_atom` | Contradictions | derivability non-explosion | propext, Quot.sound |
| `retract_removes` | Retraction | withdrawn ids absent | propext, Quot.sound |
| `valid_implies_sound` | Certificates | **abstract** valid ⇒ Entails (does not check steps) | propext |
| **`checkCertificate_sound`** | CheckCertificate | **executable check ⇒ Derives** | propext |
| **`checkCertificate_implies_entails`** | CheckCertificate | check ⇒ Entails | propext |
| **`hyp_not_math_established`** | CheckCertificate | Hyp ⇒ mathEstablished=false | propext |
| `demo_premises_designated_atom99_not` | Belnap | FOUR witness | propext |

## Distinctions (mandatory)

1. Abstract `Certificate.valid` ≠ step-trace checking.  
2. `checkCertificate_sound` is the Phase II bridge.  
3. Classical Entails ≠ Belnap Entails4.  
4. Python checker correspondence is tested, not refinement-proved.
