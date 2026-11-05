# Adversarial testing report

Covered in `tests/adversarial/test_adversarial_packages.py` and unit tests:

- Truncated JSON
- Duplicate keys
- Policy substitution
- Hash mismatch
- Missing package members
- Signature byte mutation
- Producer PASS ignored
- Stale generation CAS

Expected outcomes: fail closed with stable `ErrorCode`s.
