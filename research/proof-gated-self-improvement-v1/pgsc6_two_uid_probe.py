"""Linux-only two-UID attack on separately owned PGSC6 checkpoint.

Attacker UID nobody can rewind a deliberately world-writable model store
but cannot rewrite a checkpoint owned by a distinct authority UID.
This is a real Linux access-control test, NOT an HSM, signature, or TEE.
The Lean oracle is mocked only in preparation; the other live CI step
checks three authentic Lean-authorized promotions.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import patch

from pgsc6_external_anchor import ExternallyAnchoredPGSC6
from pgsc6_pinned_store import RESEARCH, IntegrityFailure

CERTS = tuple(
    (RESEARCH.parents[1] / "formal" / "fixtures" / "proof_gated" /
     "v6_certs" / f"step{i}.pgsc6").read_bytes() for i in (1, 2)
)

ATTACKER_CODE = r'''
import os, shutil, sys
from pathlib import Path
store, old_copy, anchor = map(Path, sys.argv[1:])
if os.getuid() == 0:
    raise SystemExit("refuse to run privilege test as root")
if os.access(anchor / "CHECKPOINT.json", os.W_OK):
    raise SystemExit("ERROR: attacker can write external checkpoint")
try:
    with (anchor / "CHECKPOINT.json").open("wb") as handle:
        handle.write(b"forged")
except (PermissionError, FileNotFoundError):
    pass
else:
    raise SystemExit("ERROR: attacker overwrote external checkpoint")
shutil.rmtree(store)
shutil.copytree(old_copy, store)
print("NONTRUSTED_STORE_ROLLBACK_WRITTEN")
'''


def world_writable(root: Path) -> None:
    """Deliberately grant attacker control over nontrusted model store."""
    for current, directories, files in os.walk(root):
        os.chmod(current, 0o777)
        for d in directories:
            os.chmod(Path(current)/d, 0o777)
        for f in files:
            os.chmod(Path(current)/f, 0o666)


def main():
    if sys.platform != "linux" or not shutil.which("sudo"):
        raise RuntimeError("requires Linux runner and sudo permission")
    with tempfile.TemporaryDirectory(prefix="pgsc6-private-trust-") as secure, (
         tempfile.TemporaryDirectory(prefix="pgsc6-attacker-store-") as exposed):
        secure_root, exposed_root = Path(secure), Path(exposed)
        os.chmod(exposed_root, 0o777)
        store_path = exposed_root / "store"
        anchor_path = secure_root / "independent-checkpoint"
        ctrl = ExternallyAnchoredPGSC6.initialize(store_path, anchor_path)
        with patch.object(ctrl.store, "_real_lean_authorizes", return_value=True):
            old = ctrl.promote(CERTS[0], ctrl.audit())
        checkpoint1 = exposed_root / "prior-valid-full-copy"
        shutil.copytree(store_path, checkpoint1)
        with patch.object(ctrl.store, "_real_lean_authorizes", return_value=True):
            current = ctrl.promote(CERTS[1], old)
        assert current.generation == 2
        assert ctrl.audit() == current
        world_writable(store_path)
        world_writable(checkpoint1)
        proc = subprocess.run(
            ["sudo", "-n", "-u", "nobody", sys.executable, "-c", ATTACKER_CODE,
             str(store_path), str(checkpoint1), str(anchor_path)],
            env={"PATH": "/usr/bin:/bin", "HOME": "/tmp"},
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=30, check=False,
        )
        if proc.returncode != 0 or "NONTRUSTED_STORE_ROLLBACK_WRITTEN" not in proc.stdout:
            raise AssertionError(
                "different-UID rollback probe failed: " +
                repr((proc.returncode, proc.stdout, proc.stderr[:2000])))
        if ctrl.store.audit().generation != 1:
            raise AssertionError("malicious rollback did not leave valid old store")
        try:
            ctrl.audit()
        except IntegrityFailure:
            pass
        else:
            raise AssertionError("external checkpoint accepted cross-UID rollback")
        try:
            ctrl.snapshot()
        except IntegrityFailure:
            pass
        else:
            raise AssertionError("external checkpoint served reverted model")
    print(json.dumps({
        "result": "PASS",
        "attacker_uid": "nobody",
        "attacker_replaced_full_nontrusted_store": True,
        "attacker_wrote_protected_checkpoint": False,
        "unanchored_store_accepted_old_valid_history": True,
        "anchored_authority_refused_rollback": True,
        "lean_oracle_mocked_only_in_setup": True,
        "production_security_proved": False
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
