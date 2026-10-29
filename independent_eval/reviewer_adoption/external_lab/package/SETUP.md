# External lab — SETUP

This kit prepares an **external laboratory** to attempt PCS-style evidence review
and reconstruction **without** claiming completed validation.

## Requirements

- Python 3.11+ available on the lab machine
- Ability to read this repository checkout (or a documented subset)
- No requirement to modify production credentials or live infrastructure

## Steps

1. Confirm you will work offline or on an air-gapped clone as required by lab policy.
2. Create a lab-local virtualenv (do not share with production services).
3. Install only packages your lab policy allows; prefer pinned lockfiles from the
   repository when available.
4. Confirm you can run:

   ```bash
   python3 -m independent_eval.reviewer_adoption.workbench.generate_report --help
   ```

5. Log time spent with `burden_tracker` (`--step read_setup`, `--step provision_python`).

## Non-goals

- Do not rotate, delete, or push real credentials.
- Do not treat local tool output as PCS `ACCEPT` / `PASS`.
- Do not claim external-lab validation is complete by finishing SETUP alone.
