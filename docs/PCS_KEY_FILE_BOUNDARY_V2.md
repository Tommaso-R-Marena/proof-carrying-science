# Key-file boundary correction

The legacy lifecycle loader called `resolve()` before `is_symlink()`, allowing a registry or public-key symlink despite its regular-file rule. The reader now inspects the requested leaf, opens it with no-follow/nonblocking flags where supported, compares descriptor identity with the inspected file, checks regular-file type, and limits bytes to 1 MiB. A switched inode is rejected. New registry installation uses an atomic no-clobber hard link; updates replace the leaf itself rather than following a substituted symlink.

Actual filesystem controls reject registry/public-key symlinks, missing/oversized files, directories, FIFOs, a file switched between inspection and opening, and a competing creator during installation. Existing lifecycle and optional signing-policy behavior remains tested: `python -m pytest -q tests/test_key_lifecycle_files.py tests/test_key_lifecycle.py tests/test_signing_policy_v1.py` passed 32 tests.

This protects leaf handling and publication races. Parent directories, operating-system file semantics and an operator who can edit the opened inode remain filesystem trust assumptions. The unsigned legacy registry is still not an authenticated production root. No production keys were read, rotated or changed. Test private keys are temporary synthetic keys.
