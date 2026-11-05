from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path

from pcs.attest import attest
from pcs.bundle_verify import verify_bundle
from pcs.scaffold import init_project
from pcs.signing import generate_keypair
from pcs.intake import freeze_intake_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a complete PCS synthetic PK/PD reference demo.")
    parser.add_argument("--output", default="demo-run", help="demo output directory")
    parser.add_argument("--force", action="store_true", help="replace an existing demo directory")
    args = parser.parse_args()

    root = Path(args.output).resolve()
    if root.exists():
        if not args.force:
            raise SystemExit(f"refusing to overwrite existing directory: {root}")
        shutil.rmtree(root)
    root.mkdir(parents=True)

    project = root / "project"
    evidence = root / "evidence"
    bundle = root / "evidence.zip"
    policy_path = root / "reviewer-policy.json"
    intake_lock = root / "pilot-intake.lock.json"

    init_project(project, template="pkpd", subject="pcs-reference-demo")
    freeze_intake_file(project / "pilot_intake.json", intake_lock)

    with tempfile.TemporaryDirectory(prefix="pcs-demo-key-") as keydir:
        keydir = Path(keydir)
        private_key = keydir / "signing-private.pem"
        public_key = root / "signer-public.pem"
        keys = generate_keypair(private_key, public_key)

        attestation = attest(
            project / "manifest.json",
            evidence,
            private_key=private_key,
            public_key=public_key,
            bundle_path=bundle,
            intake_lock=intake_lock,
        )

        policy = {
            "policy_version": "pcs-acceptance-policy-v1",
            "require_signature": True,
            "expected_signer_fingerprint": keys["fingerprint"],
            "required_claims": {
                "C_PKPD_CONTRACT": ["COMPUTATIONALLY_SUPPORTED"],
                "C_PKPD_REPLAY": ["COMPUTATIONALLY_SUPPORTED"],
            },
        }
        policy_path.write_text(json.dumps(policy, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        verification = verify_bundle(
            bundle,
            public_key=public_key,
            require_signature=True,
            expected_signer_fingerprint=keys["fingerprint"],
            policy=policy_path,
        )

    summary = {
        "output": str(root),
        "bundle": str(bundle),
        "bundle_sha256": attestation["bundle"]["sha256"],
        "signer_fingerprint": verification["signature"]["public_key_fingerprint"] if verification.get("signature") else None,
        "valid": verification["valid"],
        "assurance_dimensions": verification["assurance_dimensions"],
        "claim_statuses": verification["certificate"]["claim_statuses"],
        "pilot_intake_lock": str(intake_lock),
        "errors": verification["errors"],
    }
    (root / "demo-summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if verification["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
