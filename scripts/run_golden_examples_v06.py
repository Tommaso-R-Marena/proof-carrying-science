from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pcs.attest_v06 import attest_v06
from pcs.discover_v06 import discover_project_v06, write_discovery_outputs_v06, confirm_manifest_draft_v06
from pcs.scaffold import init_project
from pcs.verifier_zip_v06 import verify_package_zip_end_to_end_v06


DEMO_KEY_SEED = hashlib.sha256(b"PCS deterministic golden examples v1 - NOT A SECRET").digest()


def _write_demo_keypair(root: Path) -> tuple[Path, Path, str]:
    root.mkdir(parents=True, exist_ok=True)
    private = Ed25519PrivateKey.from_private_bytes(DEMO_KEY_SEED)
    public = private.public_key()
    private_path = root / "demo-private.pem"
    public_path = root / "demo-public.pem"
    private_path.write_bytes(private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ))
    public_path.write_bytes(public.public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ))
    fingerprint = hashlib.sha256(public.public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )).hexdigest()
    return private_path, public_path, fingerprint


def _claim_map(result: dict) -> dict[str, str]:
    return {c["claim_id"]: c["decision"] for c in result.get("claims", [])}


def _run_case(root: Path, name: str, mutate=None, *, discover=False) -> dict:
    project = root / name
    init_project(project, template="pkpd", subject=f"golden-{name}")
    if mutate:
        mutate(project)

    manifest = project / "manifest.json"
    if discover:
        discovered = discover_project_v06(project)
        write_discovery_outputs_v06(
            discovered,
            manifest_output=project / "pcs-manifest.draft.json",
            report_output=project / "pcs-discovery.json",
            overwrite=True,
        )
        confirm_manifest_draft_v06(
            project / "pcs-manifest.draft.json",
            manifest,
            project_root=project,
            overwrite=True,
        )

    private, public, fingerprint = _write_demo_keypair(root)
    bundle = root / f"{name}.pcs.zip"
    produced = attest_v06(
        manifest,
        bundle,
        private,
        public,
        expected_fingerprint=fingerprint,
    )
    checked = verify_package_zip_end_to_end_v06(
        bundle,
        public,
        expected_fingerprint=fingerprint,
    )
    if not checked.get("valid"):
        raise RuntimeError(f"golden case {name} failed independent verification: {checked.get('errors')}")
    return {
        "name": name,
        "bundle": bundle.name,
        "bundle_sha256": checked["bundle_sha256"],
        "valid": checked["valid"],
        "claims": _claim_map(checked),
        "environment_replay": checked.get("environment_replay"),
        "description": {
            "pkpd-supported": "Positive control: restricted PK/PD contract and numerical replay both pass.",
            "pkpd-falsified": "Negative scientific control: package is valid while the numerical scientific claim fails.",
            "environment-bound": "Reproducibility control: discovery binds a declared Python environment before attestation and replay.",
        }[name],
    }


def build_golden_examples(output: str | Path, *, force: bool = False) -> dict:
    out = Path(output).resolve()
    if out.exists() and any(out.iterdir()):
        if not force:
            raise FileExistsError(f"golden-example output directory is not empty: {out}")
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    positive = _run_case(out, "pkpd-supported")

    def falsify(project: Path) -> None:
        (project / "predictions.csv").write_text(
            "time,concentration,effect\n0,999,0\n1,999,0\n",
            encoding="utf-8",
        )

    negative = _run_case(out, "pkpd-falsified", falsify)

    def add_environment(project: Path) -> None:
        (project / "requirements.txt").write_text(
            "cryptography==46.0.2\njsonschema==4.25.1\n",
            encoding="utf-8",
        )
        (project / ".python-version").write_text("3.13.5\n", encoding="utf-8")

    environment = _run_case(out, "environment-bound", add_environment, discover=True)

    report = {
        "format": "pcs-golden-examples-v06-v1",
        "deterministic_demo_key": True,
        "demo_key_warning": "The deterministic key is test/demo-only and must never be trusted for real scientific publication.",
        "cases": [positive, negative, environment],
        "expected": {
            "pkpd-supported": {
                "valid": True,
                "C_PKPD_CONTRACT": "COMPUTATIONALLY_SUPPORTED",
                "C_PKPD_REPLAY": "COMPUTATIONALLY_SUPPORTED",
            },
            "pkpd-falsified": {
                "valid": True,
                "C_PKPD_CONTRACT": "COMPUTATIONALLY_SUPPORTED",
                "C_PKPD_REPLAY": "FALSIFIED_OR_CHECK_FAILED",
            },
            "environment-bound": {
                "valid": True,
            },
        },
    }
    (out / "golden-examples-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    p = argparse.ArgumentParser(description="Build and independently verify the three canonical PCS v0.6 demo cases.")
    p.add_argument("-o", "--output", default="golden-demo-run")
    p.add_argument("--force", action="store_true", help="replace an existing non-empty output directory")
    args = p.parse_args()
    report = build_golden_examples(args.output, force=args.force)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
