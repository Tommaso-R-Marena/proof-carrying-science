# Independent scientific pilot — evidence report

- Format: `pcs-independent-pilot-evidence-ledger-v1`
- Pilot ID: `PCS-INDEPENDENT-PILOT-SYNTHETIC-001`
- Commit: `ee75cbbac6c1b9753807686955afc1472942df7f`
- Bundle SHA-256: `acafa67973b77b7421a2c2f3dbe186bd15d39f953470b3828819b6878d8f7fe5`
- Intake semantic hash: `ab9fec8d50a28c2d432f68ecc8d5fa01e7e3f4867bc061ba289b37947b3a14cd`
- Signer fingerprint: `ff935ffffcf117c49bb0d5ef393b866ccb6da527b35f2abb38031aeceb89bb6a`

## Stage outcomes

- `intake_frozen`: `True`
- `discovery_confirmed`: `True`
- `attested`: `True`
- `second_environment_verified`: `True`
- `authoritative`: `True`
- `adversarial_pass`: `True`
- `closeout_planned`: `True`
- `closeout_applied`: `True`

## Adversarial results

- Pass: `True`
- Failed attacks: `[]`

- `changed_scientific_artifact` rejected=`True`
- `false_certificate_bytes` rejected=`True`
- `signature_substitution_wrong_key` rejected=`True`
- `path_traversal_member` rejected=`True`
- `absolute_archive_member` rejected=`True`
- `stale_receipt_bundle_binding` rejected=`True`
- `ambiguous_post_hoc_claim` rejected=`True`
- `unexpected_source_modification_detected` rejected=`True`

## Trust boundary

See `archive/TRUST_BOUNDARY_ASSESSMENT.json` for the machine-readable
separation of kernel-proved guarantees, independently tested properties,
and unproved environmental assumptions.

## Exact reproduce commands

```bash
python -m pip install -e '.[dev]'
source scripts/activate_lean_428.sh
cd formal && lake build pcs-lean-authority && cd ..
python scripts/run_independent_scientific_pilot_v1.py --output /tmp/pcs-independent-pilot
python scripts/run_cleanroom_independent_pilot_v1.py --output /tmp/pcs-cleanroom-pilot
```
