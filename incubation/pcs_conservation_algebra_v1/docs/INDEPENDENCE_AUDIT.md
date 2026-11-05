# Independence audit

## Namespace

`incubation/pcs_conservation_algebra_v1/**` only.

## Forbidden touch targets

- `pcs/**` production runtime
- `formal/PCS/**`, `formal/real/**` production Lean
- `incubation/pcs_certified_numerics_v1/**` (CertNum)
- `incubation/pcs_next_v1/**`
- Website / PGSC / PGSI / Aristotle integration trees

## Parallel work awareness

Open PR lanes (CertNum, PGSC6, PGSI, independent evals, PCS Next) are not
modified. PCCA addresses the OPEN conservation-algebra / continuum-bridge
gap complementary to CertNum's interval engine and Transport's matrix kernel.

## Enforcement

`scripts/noninterference_check.sh` fails if any changed path escapes the
namespace or hits a forbidden prefix.
