from __future__ import annotations

import argparse
import base64
import json
import stat
import subprocess
import tempfile
import zipfile
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "v06_golden"
META = json.loads((GOLDEN / "metadata.json").read_text(encoding="utf-8"))
MEMBERS = [
    "certificate.json",
    "certificate_signature.json",
    "package_manifest.json",
    "package_signature.json",
    "artifacts/fixture.bin",
    "normalized/index.json",
    META["normalized_wire_path"],
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("verifier")
    args = parser.parse_args()
    verifier = Path(args.verifier).resolve()
    if not verifier.is_file():
        raise SystemExit(f"verifier not found: {verifier}")

    with tempfile.TemporaryDirectory(prefix="pcs-standalone-smoke-") as tmp:
        root = Path(tmp)
        bundle = root / "golden.pcs.zip"
        with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_STORED) as zf:
            for rel in MEMBERS:
                info = zipfile.ZipInfo(rel, (1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                info.compress_type = zipfile.ZIP_STORED
                zf.writestr(info, (GOLDEN / rel).read_bytes())

        key = Ed25519PublicKey.from_public_bytes(
            base64.b64decode(META["public_key_raw_base64"], validate=True)
        )
        public_key = root / "public.pem"
        public_key.write_bytes(
            key.public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )
        trust = root / "trust.json"
        trust.write_text(
            json.dumps(
                {
                    "format": "pcs-verifier-trust-v1",
                    "public_key": "public.pem",
                    "expected_signer_fingerprint": META["public_key_fingerprint"],
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        receipt = root / "receipt.json"
        proc = subprocess.run(
            [
                str(verifier),
                str(bundle),
                "--trust",
                str(trust),
                "--receipt",
                str(receipt),
            ],
            text=True,
            capture_output=True,
            check=False,
            timeout=300,
        )
        if proc.returncode != 0:
            raise SystemExit(proc.stdout + proc.stderr)
        result = json.loads(proc.stdout)
        if result.get("valid") is not True:
            raise SystemExit(f"standalone verifier did not validate golden package: {result}")
        authority = result.get("lean_authority", {})
        if authority.get("accepted") is not True or authority.get("mode") != "embedded-binary":
            raise SystemExit(f"embedded Lean authority was not authoritative: {authority}")
        if not receipt.is_file():
            raise SystemExit("standalone verifier did not write receipt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
