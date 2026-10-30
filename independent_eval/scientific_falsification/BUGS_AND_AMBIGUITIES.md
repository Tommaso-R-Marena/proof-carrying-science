# Bugs and ambiguities observed (Workstream B)

Findings from black-box evaluation. None of these were “fixed” in production
PCS (out of writable scope).

## Ambiguities

1. **Classic kernel vs v0.6 check registry.**  
   `pkpd_peak_concentration_threshold` is a certified built-in in
   `pcs/check_registry_v06.py`, but classic `pcs certify` / `pcs.kernel`
   does not execute it. Case `02_pkpd_with_peak_threshold_note` therefore
   declares the peak check while verifying contract+match via classic CLI.

2. **Certify emits certificates for failed claims.**  
   `pcs certify` returns exit code 0 even when claims are not
   `COMPUTATIONALLY_SUPPORTED`. Independent evaluators must inspect claim
   statuses, not only process exit codes. Documented as expected behavior
   for negative controls.

3. **Discovery abstention is implicit.**  
   `pcs discover-v06` does not emit an explicit `abstain: true` field.
   Abstention is inferred as “no checks selected into the draft at the
   configured minimum confidence.”

4. **Scientific workflow examples use external predicates.**  
   `examples/scientific_workflow_v2` and `v3` rely on specialized kernels /
   external claim namespaces beyond the classic built-in check set. The
   casebook therefore mirrors their *scientific concerns* with
   PCS-supported built-ins (`reaction_balance`, `unit_compatible`, PKPD)
   rather than re-executing the full signed v2/v3 experiment scripts.

5. **Unit spelling equivalence.**  
   `mg/L` vs `ug/mL` and `mol/L` vs `mmol/mL` are accepted as compatible by
   the unit checker; whether a given spelling is the *correct measurand*
   remains out of scope (Task 8 example 03).

6. **`csv_disjoint` vs sampling validity.**  
   Disjoint opaque keys computationally PASS even when authored synthetic
   cohorts are single-site / narrow age-band / single-sex (Task 8 example
   04). PCS does not claim representativeness; evaluators must not read
   verify PASS as population adequacy.

## Bugs / sharp edges for evaluators

1. **Tampered evidence after certify.**  
   Mutating packaged artifact bytes after `pcs certify` correctly causes
   `pcs verify` to fail. Mutating only the in-tree source without
   re-certifying is a different failure mode and must be staged explicitly
   in metamorphic tests.

2. **PKPD prediction formatting.**  
   Predictions must use the strict decimal CSV subset. Fixture generation
   freezes adapter-aligned Decimal tables; hand-edited floats may fail
   `pkpd_reference_match` at `1e-9` relative tolerance.

3. **Reaction JSON vs check payload.**  
   Discovery recommends `reaction_balance` from reactants/products JSON, but
   classic manifests embed reactants/products inside the check object. The
   on-disk `reaction.json` is evidence/context; the check fields are
   authoritative for certify. Metamorphic reaction breaks sync both the
   artifact and the check/predicate fields.

4. **Surface-specific invalid transforms.**  
   Applying dose/reaction break to a units-only project is not meaningful.
   The campaign runner selects invalid transforms from declared check types
   and present artifacts so oracle failures are not confounded with
   inapplicable mutations.
