# Case study — conflicting studies (synthetic)

**Claim A (Study 1):** atom `effect_positive` as `empiricalAsserted`.  
**Claim B (Study 2):** `not effect_positive` as `empiricalAsserted`.  
**Hypothesis H:** `mechanism_X` as `hypothesis`.

Under the v0 calculus:

1. Both A and B may be hypotheses in one context → locally contradictory.  
2. Non-explosion: unrelated `policy_recommendation` is **not** derivable from the contradiction.  
3. Certificate for A records support `{A}` and authority `empiricalAsserted`.  
4. Retracting Study 1 invalidates certificates depending on A; B remains.

**Does not establish:** which study is correct, fraud, or world-truth.
