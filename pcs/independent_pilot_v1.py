"""Independent scientific-assurance pilot workflow (v1).

Orchestrates a bounded producer→reviewer→closeout path that a new laboratory
can reproduce from a clean checkout. Scientific validity remains explicitly
separate from formal/computational verification.

This module does **not** claim an external partnership, legal clearance, or
production trust-root security. Demo keys are ephemeral and public.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .attest_v06 import V06AttestationError, attest_v06
from .canonical_json import canonicalize_jcs_bytes
from .discover_v06 import (
    V06DiscoveryError,
    confirm_manifest_draft_v06,
    discover_project_v06,
    write_discovery_outputs_v06,
)
from .intake import (
    PilotIntakeError,
    assert_lock_matches_certificate,
    freeze_intake,
    freeze_intake_file,
    validate_lock,
)
from .jsonio import StrictJSONError, strict_json_load
from .lean_authority_v06 import V06LeanAuthorityError, resolve_lean_authority_v06
from .limitations import write_limitations
from .pilot_closeout import (
    apply_closeout_plan,
    build_closeout_plan,
    write_closeout_plan,
    write_closeout_receipt,
)
from .signing import public_key_fingerprint
from .verifier_zip_v06 import (
    V06BundleVerificationError,
    verify_package_zip_end_to_end_v06,
)

FORMAT = "pcs-independent-scientific-pilot-v1"
EVIDENCE_FORMAT = "pcs-independent-pilot-evidence-ledger-v1"
TRUST_BOUNDARY_FORMAT = "pcs-trust-boundary-assessment-v1"
ADVERSARIAL_FORMAT = "pcs-independent-pilot-adversarial-v1"
PILOT_ID = "PCS-INDEPENDENT-PILOT-SYNTHETIC-001"
DEMO_KEY_SEED = hashlib.sha256(
    b"PCS independent scientific pilot v1 - PUBLIC DEMO KEY - NOT A SECRET"
).digest()
GENERATED_AT = "2026-10-17T00:00:00+00:00"

# Explicit separation of what this pilot proves vs what remains unproved.
TRUST_BOUNDARY: dict[str, Any] = {
    "format": TRUST_BOUNDARY_FORMAT,
    "kernel_proved_guarantees": [
        "Lean-authoritative v0.6 archive acceptance for the delivered canonical ZIP "
        "(when pcs-lean-authority ACCEPT is required and obtained).",
        "SHA-256 equality to an independent FIPS 180-4 specification inside the "
        "Lean authority for certificate-bound digests.",
        "Built-in Lean replay for pkpd_contract and pkpd_reference_match on the "
        "committed prediction table bytes.",
        "Fail-closed rejection of path-traversal archive members and unsigned "
        "package substitution when fingerprint pinning is enforced.",
    ],
    "independently_tested_properties": [
        "Intake semantic-hash freeze rejects post-hoc claim/assumption mutation.",
        "Discovery draft cannot be attested until human confirmation.",
        "Second-environment verification reproduces ACCEPT on exact bundle bytes.",
        "Adversarial mutations of artifacts, signatures, receipts, and archives "
        "are rejected (finite regression suite, not a security proof).",
        "Closeout plan requires every workspace file to be classified RETAIN or DELETE.",
    ],
    "unproved_environmental_assumptions": [
        "Ed25519 unforgeability of the trust anchor (no RFC 8032 Lean proof).",
        "OS/Python/cryptography runtime refinement is not proved.",
        "Demo signing keys are public and must never be used for production pilots.",
        "Biological/clinical/regulatory adequacy of the PK/PD model is not established.",
        "No claim of an actual external partner engagement or legal clearance.",
        "Python precheck observations must match Lean authority transcripts; "
        "arbitrary external validators remain outside Lean authority.",
    ],
    "scientific_vs_computational": {
        "computational_verification": (
            "Replayed restricted one-compartment IV-bolus PK + direct-Emax PD "
            "equations against the delivered prediction table within declared tolerances."
        ),
        "empirical_scientific_validity": (
            "Explicitly OPEN. This pilot does not establish biological adequacy, "
            "clinical safety/efficacy, GxP validation, or regulatory acceptance."
        ),
    },
}


class IndependentPilotError(ValueError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                return digest.hexdigest()
            digest.update(chunk)


def _write_json(path: Path, value: Mapping[str, Any], *, overwrite: bool = False) -> Path:
    path = Path(path)
    if path.exists() and not overwrite:
        raise IndependentPilotError(f"refusing to overwrite existing evidence: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonicalize_jcs_bytes(dict(value)))
    return path


def _write_text(path: Path, text: str, *, overwrite: bool = False) -> Path:
    path = Path(path)
    if path.exists() and not overwrite:
        raise IndependentPilotError(f"refusing to overwrite existing evidence: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _demo_keypair(directory: Path) -> tuple[Path, Path, str]:
    directory.mkdir(parents=True, exist_ok=True)
    private = Ed25519PrivateKey.from_private_bytes(DEMO_KEY_SEED)
    public = private.public_key()
    private_path = directory / "demo-producer-private.pem"
    public_path = directory / "demo-producer-public.pem"
    private_path.write_bytes(
        private.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    public_path.write_bytes(
        public.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    try:
        private_path.chmod(0o600)
    except OSError:
        pass
    fingerprint = public_key_fingerprint(public)
    return private_path, public_path, fingerprint


def stage_external_lab_project(destination: str | Path, *, overwrite: bool = False) -> dict[str, Any]:
    """Stage a synthetic external-lab PK/PD project suitable for a clean-room pilot.

    Artifacts are public/synthetic. The project is staged as if authored outside
    PCS development so the subsequent discovery/confirmation path is exercised.
    """
    dest = Path(destination).resolve()
    if dest.exists():
        if not overwrite:
            raise IndependentPilotError(f"lab project destination already exists: {dest}")
        if not dest.is_dir():
            raise IndependentPilotError(f"lab project destination is not a directory: {dest}")
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=False)

    source = _repo_root() / "examples" / "pkpd_one_compartment"
    for name in ("pk_model.json", "predictions.csv", "pilot_intake.json"):
        src = source / name
        if not src.is_file():
            raise IndependentPilotError(f"missing reference artifact: {src}")
        shutil.copyfile(src, dest / name)

    # Hand-authored lab README — not a PCS control document.
    _write_text(
        dest / "LAB_README.md",
        "\n".join(
            [
                "# Synthetic external-lab PK/PD pilot inputs",
                "",
                "This directory simulates a laboratory-authored computational workflow.",
                "It uses a restricted one-compartment IV-bolus PK model with direct",
                "Emax PD. All inputs are synthetic and public.",
                "",
                "Claims and assumptions are frozen in `pilot_intake.json` *before*",
                "PCS attestation. Computational replay does **not** establish",
                "biological adequacy, clinical validity, or regulatory acceptance.",
                "",
            ]
        ),
        overwrite=True,
    )

    # Explicit unit-compatible helper used only as an authored artifact inventory
    # signal; PCS discovery must still be confirmed by a human (or this runner).
    intake = strict_json_load(dest / "pilot_intake.json")
    intake["pilot_id"] = PILOT_ID
    intake["workflow_summary"] = (
        "Synthetic external-lab one-compartment IV-bolus PK with direct Emax PD; "
        "verify restricted model contract and analytic replay only."
    )
    _write_json(dest / "pilot_intake.json", intake, overwrite=True)

    inventory = {
        "format": "pcs-independent-pilot-lab-inventory-v1",
        "pilot_id": PILOT_ID,
        "data_classification": "synthetic",
        "files": {
            path.relative_to(dest).as_posix(): {
                "sha256": _sha256_file(path),
                "size": path.stat().st_size,
            }
            for path in sorted(dest.rglob("*"))
            if path.is_file()
        },
    }
    _write_json(dest / "lab-inventory.json", inventory, overwrite=True)
    return {
        "format": FORMAT,
        "pilot_id": PILOT_ID,
        "project_root": str(dest),
        "inventory_sha256": _sha256_file(dest / "lab-inventory.json"),
        "files": inventory["files"],
    }


def _align_draft_to_intake(draft: dict[str, Any], intake: Mapping[str, Any]) -> dict[str, Any]:
    """Rewrite discovery draft IDs to the frozen pre-result intake inventory.

    Discovery may emit generated identifiers. Independent pilots require the
    attested certificate to match the intake lock exactly, so confirmation uses
    the partner-declared claim/assumption IDs while preserving discovered
    predicates, checks, artifacts, and workflow structure.
    """
    aligned = json.loads(json.dumps(draft))
    intake_claims = list(intake.get("claims", []))
    intake_assumptions = list(intake.get("assumptions", []))
    draft_claims = list(aligned.get("claims", []))
    draft_assumptions = list(aligned.get("assumptions", []))
    if len(draft_claims) != len(intake_claims):
        raise IndependentPilotError(
            "discovery claim count does not match frozen intake; "
            "refuse silent remapping of an ambiguous claim inventory"
        )
    if len(draft_assumptions) != len(intake_assumptions):
        raise IndependentPilotError(
            "discovery assumption count does not match frozen intake; "
            "refuse silent remapping of an ambiguous assumption inventory"
        )

    claim_map = {
        old["id"]: new["id"]
        for old, new in zip(draft_claims, intake_claims, strict=True)
    }
    assumption_map = {
        old["id"]: new["id"]
        for old, new in zip(draft_assumptions, intake_assumptions, strict=True)
    }

    aligned["assumptions"] = [
        {
            **old,
            "id": new["id"],
            "statement": new["statement"],
            "scope": [
                claim_map.get(cid, cid) for cid in old.get("scope", [])
            ]
            if isinstance(old.get("scope"), list)
            else [c["id"] for c in intake_claims],
        }
        for old, new in zip(draft_assumptions, intake_assumptions, strict=True)
    ]
    aligned["claims"] = [
        {
            **old,
            "id": new["id"],
            "statement": new["statement"],
            "kind": (
                "computational"
                if new.get("desired_assurance") == "computational"
                else old.get("kind", "computational")
            ),
            "assumptions": [
                assumption_map.get(aid, aid) for aid in old.get("assumptions", [])
            ]
            if isinstance(old.get("assumptions"), list)
            else [a["id"] for a in intake_assumptions],
        }
        for old, new in zip(draft_claims, intake_claims, strict=True)
    ]
    for check in aligned.get("checks", []):
        if not isinstance(check, dict):
            continue
        check["claim_ids"] = [
            claim_map.get(cid, cid) for cid in check.get("claim_ids", [])
        ]
        # Keep check IDs stable relative to claim IDs for reviewer readability.
        if check.get("type") == "pkpd_contract" and len(intake_claims) >= 1:
            check["id"] = "E_" + intake_claims[0]["id"].removeprefix("C_")
            for claim in aligned["claims"]:
                if claim["id"] == intake_claims[0]["id"]:
                    claim["required_evidence"] = [check["id"]]
        if check.get("type") == "pkpd_reference_match" and len(intake_claims) >= 2:
            check["id"] = "E_" + intake_claims[1]["id"].removeprefix("C_")
            for claim in aligned["claims"]:
                if claim["id"] == intake_claims[1]["id"]:
                    claim["required_evidence"] = [check["id"]]
    return aligned


def _confirm_or_use_manifest(project: Path, intake_lock: Mapping[str, Any]) -> Path:
    """Discover → align to frozen intake → human-confirm a manifest."""
    manifest = project / "manifest.json"
    discovered = discover_project_v06(project)
    draft = project / "pcs-manifest.draft.json"
    report = project / "pcs-discovery.json"
    write_discovery_outputs_v06(
        discovered,
        manifest_output=draft,
        report_output=report,
        overwrite=True,
    )
    draft_obj = strict_json_load(draft)
    aligned = _align_draft_to_intake(draft_obj, intake_lock["intake"])
    _write_json(draft, aligned, overwrite=True)
    confirm_manifest_draft_v06(
        draft,
        manifest,
        project_root=project,
        overwrite=True,
    )
    return manifest


def _freeze_intake(project: Path, locks_dir: Path) -> dict[str, Any]:
    lock_path = locks_dir / "pilot-intake.lock.json"
    result = freeze_intake_file(project / "pilot_intake.json", lock_path, overwrite=True)
    return result


def _rewrite_zip(source: Path, dest: Path, transform) -> None:
    with zipfile.ZipFile(source, "r") as zin, zipfile.ZipFile(
        dest, "w", compression=zipfile.ZIP_STORED
    ) as zout:
        for info in zin.infolist():
            raw = zin.read(info.filename)
            name, raw2 = transform(info.filename, raw)
            out = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            out.create_system = 3
            out.external_attr = 0o100644 << 16
            out.compress_type = zipfile.ZIP_STORED
            zout.writestr(out, raw2)


def run_adversarial_cases(
    *,
    bundle: Path,
    public_key: Path,
    fingerprint: str,
    work: Path,
    lean_authority_path: str | Path | None,
    receipt_path: Path,
) -> dict[str, Any]:
    """Finite fail-closed adversarial campaign over the delivered pilot bundle."""
    results: list[dict[str, Any]] = []

    def record(name: str, rejected: bool, detail: Any) -> None:
        results.append(
            {
                "attack": name,
                "rejected": bool(rejected),
                "detail": detail if isinstance(detail, (str, list, dict, type(None))) else str(detail),
            }
        )

    def expect_reject(name: str, mutated: Path, **kwargs: Any) -> None:
        try:
            checked = verify_package_zip_end_to_end_v06(
                mutated,
                public_key,
                expected_fingerprint=fingerprint,
                lean_authority_path=lean_authority_path,
                **kwargs,
            )
            record(
                name,
                checked.get("valid") is not True,
                checked.get("failed_stage") or checked.get("errors"),
            )
        except (
            V06BundleVerificationError,
            V06LeanAuthorityError,
            OSError,
            ValueError,
        ) as exc:
            record(name, True, f"{type(exc).__name__}: {exc}")

    with zipfile.ZipFile(bundle, "r") as zin:
        member_names = list(zin.namelist())
        payload_members = [
            name
            for name in member_names
            if name.startswith("artifacts/") and name.endswith("/payload")
        ]
    if not payload_members:
        record(
            "changed_scientific_artifact",
            False,
            "no content-addressed artifact payloads found to mutate",
        )
    else:
        target_payload = sorted(payload_members)[0]

        # 1. Artifact scientific bytes changed (content-addressed payload).
        tampered = work / "attack-artifact-changed.zip"
        _rewrite_zip(
            bundle,
            tampered,
            lambda n, r: (
                n,
                (b"time,concentration,effect\n0,999,1\n" if n == target_payload else r),
            ),
        )
        expect_reject("changed_scientific_artifact", tampered)

    # 2. False evidence / forged certificate object.
    false_cert = work / "attack-false-certificate.zip"
    _rewrite_zip(bundle, false_cert, lambda n, r: (n, b"{}" if n == "certificate.json" else r))
    expect_reject("false_certificate_bytes", false_cert)

    # 3. Signature substitution with attacker key.
    attacker_priv = Ed25519PrivateKey.generate()
    attacker_pub = attacker_priv.public_key()
    attacker_pub_path = work / "attacker-public.pem"
    attacker_pub_path.write_bytes(
        attacker_pub.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    try:
        checked = verify_package_zip_end_to_end_v06(
            bundle,
            attacker_pub_path,
            expected_fingerprint=fingerprint,
            lean_authority_path=lean_authority_path,
        )
        record(
            "signature_substitution_wrong_key",
            checked.get("valid") is not True,
            checked.get("failed_stage") or checked.get("errors"),
        )
    except (V06BundleVerificationError, V06LeanAuthorityError, ValueError) as exc:
        record("signature_substitution_wrong_key", True, f"{type(exc).__name__}: {exc}")

    # 4. Path traversal member.
    traversal = work / "attack-path-traversal.zip"
    try:
        with zipfile.ZipFile(bundle, "r") as zin, zipfile.ZipFile(
            traversal, "w", compression=zipfile.ZIP_STORED
        ) as zout:
            for info in zin.infolist():
                out = zipfile.ZipInfo(info.filename, (1980, 1, 1, 0, 0, 0))
                out.create_system = 3
                out.external_attr = 0o100644 << 16
                out.compress_type = zipfile.ZIP_STORED
                zout.writestr(out, zin.read(info.filename))
            bad = zipfile.ZipInfo("../escape.txt", (1980, 1, 1, 0, 0, 0))
            bad.create_system = 3
            bad.external_attr = 0o100644 << 16
            bad.compress_type = zipfile.ZIP_STORED
            zout.writestr(bad, b"escaped")
        expect_reject("path_traversal_member", traversal)
    except Exception as exc:  # noqa: BLE001 - campaign must record unexpected failures
        record("path_traversal_member", False, f"campaign error {type(exc).__name__}: {exc}")

    # 5. Unsafe archive contents (absolute path member injection).
    abs_member = work / "attack-absolute-member.zip"
    try:
        with zipfile.ZipFile(bundle, "r") as zin, zipfile.ZipFile(
            abs_member, "w", compression=zipfile.ZIP_STORED
        ) as zout:
            for info in zin.infolist():
                out = zipfile.ZipInfo(info.filename, (1980, 1, 1, 0, 0, 0))
                out.create_system = 3
                out.external_attr = 0o100644 << 16
                out.compress_type = zipfile.ZIP_STORED
                zout.writestr(out, zin.read(info.filename))
            bad = zipfile.ZipInfo("/tmp/evil.bin", (1980, 1, 1, 0, 0, 0))
            bad.create_system = 3
            bad.external_attr = 0o100644 << 16
            bad.compress_type = zipfile.ZIP_STORED
            zout.writestr(bad, b"escaped-absolute")
        expect_reject("absolute_archive_member", abs_member)
    except Exception as exc:  # noqa: BLE001
        record("absolute_archive_member", False, f"campaign error {type(exc).__name__}: {exc}")

    # 6. Stale / mutated reviewer receipt (hash mismatch).
    receipt = strict_json_load(receipt_path)
    stale = dict(receipt)
    stale["bundle_sha256"] = "0" * 64
    stale_path = work / "stale-receipt.json"
    stale_path.write_text(json.dumps(stale, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    original_sha = _sha256_file(receipt_path)
    stale_sha = _sha256_file(stale_path)
    record(
        "stale_receipt_bundle_binding",
        original_sha != stale_sha and stale.get("bundle_sha256") != receipt.get("bundle_sha256"),
        {
            "original_receipt_sha256": original_sha,
            "stale_receipt_sha256": stale_sha,
            "note": "Reviewer must re-verify against the delivered bundle; a mutated receipt is not authoritative.",
        },
    )

    # 7. Ambiguous scientific claim: intake lock vs post-hoc statement change.
    try:
        intake = strict_json_load(_repo_root() / "examples" / "pkpd_one_compartment" / "pilot_intake.json")
        lock = freeze_intake(intake)
        validate_lock(lock)
        mutated_cert = {
            "claims": [
                {
                    "id": c["id"],
                    "statement": "Post-hoc weakened claim after seeing results.",
                    "kind": "computational",
                }
                for c in lock["intake"]["claims"]
            ],
            "assumptions": lock["intake"]["assumptions"],
        }
        try:
            assert_lock_matches_certificate(lock, mutated_cert)
            record("ambiguous_post_hoc_claim", False, "intake lock unexpectedly accepted mutated claim")
        except PilotIntakeError as exc:
            record("ambiguous_post_hoc_claim", True, str(exc))
    except Exception as exc:  # noqa: BLE001
        record("ambiguous_post_hoc_claim", False, f"campaign error {type(exc).__name__}: {exc}")

    # 8. Unexpected source modification detected via staged lab inventory.
    lab_inventory = work.parent / "lab" / "lab-inventory.json"
    if lab_inventory.is_file():
        inv = strict_json_load(lab_inventory)
        lab_root = lab_inventory.parent
        mutated_note = lab_root / "LAB_README.md"
        before = _sha256_file(mutated_note)
        original_text = mutated_note.read_text(encoding="utf-8")
        mutated_note.write_text(original_text + "\n# tampered\n", encoding="utf-8")
        after = _sha256_file(mutated_note)
        mutated_note.write_text(original_text, encoding="utf-8")
        expected = inv["files"]["LAB_README.md"]["sha256"]
        record(
            "unexpected_source_modification_detected",
            before == expected and after != expected,
            {"before": before, "after": after, "expected": expected},
        )
    else:
        record(
            "unexpected_source_modification_detected",
            False,
            "lab inventory missing; cannot demonstrate source-modification detection",
        )

    failed = [r for r in results if not r["rejected"]]
    return {
        "format": ADVERSARIAL_FORMAT,
        "pass": not failed,
        "cases": results,
        "failed_attacks": [r["attack"] for r in failed],
    }


def _reviewer_report(
    *,
    verification: Mapping[str, Any],
    fingerprint: str,
    intake_lock: Mapping[str, Any],
    trust_boundary: Mapping[str, Any],
) -> str:
    claims = verification.get("claims") or []
    lines = [
        "# Independent reviewer verification report",
        "",
        "This report is generated by the PCS independent scientific pilot runner.",
        "It records computational/formal verification results. It does **not**",
        "establish empirical scientific validity, clinical adequacy, or regulatory acceptance.",
        "",
        "## Bundle identity",
        "",
        f"- Bundle SHA-256: `{verification.get('bundle_sha256', '')}`",
        f"- Pinned signer fingerprint: `{fingerprint}`",
        f"- Authoritative (Lean): `{verification.get('authoritative')}`",
        f"- Valid: `{verification.get('valid')}`",
        f"- Archive assurance: `{verification.get('archive_assurance', '')}`",
        "",
        "## Frozen intake",
        "",
        f"- Pilot ID: `{intake_lock.get('intake', {}).get('pilot_id', '')}`",
        f"- Intake semantic hash: `{intake_lock.get('intake_semantic_hash', '')}`",
        f"- Frozen at: `{intake_lock.get('frozen_at', '')}`",
        "",
        "## Claim decisions (computational/formal layer)",
        "",
    ]
    if isinstance(claims, list) and claims:
        for claim in claims:
            if not isinstance(claim, dict):
                continue
            lines.append(
                f"- **{claim.get('claim_id', '')}** → `{claim.get('decision', 'OPEN')}`"
            )
    else:
        lines.append("- No claim decisions were present in the verification receipt.")

    lines += [
        "",
        "## Trust boundary (summary)",
        "",
        "### Kernel-proved",
        "",
    ]
    for item in trust_boundary.get("kernel_proved_guarantees", []):
        lines.append(f"- {item}")
    lines += ["", "### Independently tested", ""]
    for item in trust_boundary.get("independently_tested_properties", []):
        lines.append(f"- {item}")
    lines += ["", "### Unproved environmental assumptions", ""]
    for item in trust_boundary.get("unproved_environmental_assumptions", []):
        lines.append(f"- {item}")
    lines += [
        "",
        "## Scientific interpretation rule",
        "",
        trust_boundary.get("scientific_vs_computational", {}).get(
            "empirical_scientific_validity",
            "Empirical scientific validity remains OPEN.",
        ),
        "",
    ]
    return "\n".join(lines)


def run_independent_pilot_v1(
    output_dir: str | Path,
    *,
    lean_authority_path: str | Path | None = None,
    overwrite: bool = False,
    apply_closeout: bool = False,
) -> dict[str, Any]:
    """Execute the complete bounded independent-pilot workflow.

    Stages: intake freeze → discovery → confirmation → semantic hashing /
    attestation → Lean-authoritative verify → second-environment verify →
    reviewer receipt → adversarial fail-closed suite → archival/closeout plan.
    """
    out = Path(output_dir).resolve()
    if out.exists():
        if not overwrite:
            raise IndependentPilotError(f"output directory already exists: {out}")
        if not out.is_dir():
            raise IndependentPilotError(f"output path is not a directory: {out}")
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=False)

    # Resolve Lean authority early so failures are fail-closed and explicit.
    try:
        authority = resolve_lean_authority_v06(lean_authority_path)
    except V06LeanAuthorityError as exc:
        raise IndependentPilotError(
            "Lean-authoritative production boundary unavailable. "
            "Build with `cd formal && lake build pcs-lean-authority` "
            f"or pass --lean-authority. Detail: {exc}"
        ) from exc

    lab = out / "lab"
    producer = out / "producer"
    reviewer = out / "reviewer"
    adversarial = out / "adversarial"
    archive = out / "archive"
    for path in (producer, reviewer, adversarial, archive):
        path.mkdir(parents=True, exist_ok=False)

    staged = stage_external_lab_project(lab, overwrite=False)
    private_key, public_key, fingerprint = _demo_keypair(producer / "keys")

    # A. Intake freeze before attestation / result packaging.
    intake_lock = _freeze_intake(lab, producer / "intake")
    lock_path = producer / "intake" / "pilot-intake.lock.json"

    # Artifact discovery + human confirmation (automated confirmation in this demo
    # records explicit confirmation of the bounded draft; it is not authenticated
    # external institutional review). Claim/assumption IDs are aligned to the
    # frozen intake so attestation cannot silently introduce post-hoc IDs.
    try:
        manifest = _confirm_or_use_manifest(lab, intake_lock)
    except (V06DiscoveryError, OSError, StrictJSONError, IndependentPilotError) as exc:
        raise IndependentPilotError(f"discovery/confirmation failed: {exc}") from exc

    # Attest under Lean authority.
    bundle = producer / "delivery" / "study.pcs.zip"
    bundle.parent.mkdir(parents=True, exist_ok=True)
    try:
        attestation = attest_v06(
            manifest,
            bundle,
            private_key,
            public_key,
            expected_fingerprint=fingerprint,
            overwrite=True,
            lean_authority_path=lean_authority_path or authority.get("path"),
        )
    except (V06AttestationError, V06LeanAuthorityError) as exc:
        raise IndependentPilotError(f"attestation failed: {exc}") from exc

    # Bind intake lock to the produced certificate bytes.
    package_tmp = producer / "delivery" / "unpacked-check"
    if package_tmp.exists():
        shutil.rmtree(package_tmp)
    with zipfile.ZipFile(bundle, "r") as zf:
        zf.extractall(package_tmp)
    certificate = strict_json_load(package_tmp / "certificate.json")
    try:
        assert_lock_matches_certificate(intake_lock, certificate)
    except PilotIntakeError as exc:
        raise IndependentPilotError(
            f"frozen intake does not match attested certificate: {exc}"
        ) from exc
    shutil.copyfile(lock_path, package_tmp / "pilot-intake-lock.json")
    limitations_path = write_limitations(certificate, producer / "delivery" / "LIMITATIONS.md")

    # B. Second-environment verification (fresh directory, no producer workspace).
    reviewer_bundle = reviewer / "study.pcs.zip"
    reviewer_key = reviewer / "trusted-public.pem"
    shutil.copyfile(bundle, reviewer_bundle)
    shutil.copyfile(public_key, reviewer_key)
    # Delete private key material from the reviewer view (never delivered).
    if (reviewer / "demo-producer-private.pem").exists():
        (reviewer / "demo-producer-private.pem").unlink()

    receipt_path = reviewer / "verification-receipt.json"
    try:
        verification = verify_package_zip_end_to_end_v06(
            reviewer_bundle,
            reviewer_key,
            expected_fingerprint=fingerprint,
            lean_authority_path=lean_authority_path or authority.get("path"),
            require_canonical_archive=True,
        )
    except (V06BundleVerificationError, V06LeanAuthorityError) as exc:
        raise IndependentPilotError(f"second-environment verification failed: {exc}") from exc
    if verification.get("valid") is not True or verification.get("authoritative") is not True:
        raise IndependentPilotError(
            f"second-environment verification was not authoritative ACCEPT: "
            f"valid={verification.get('valid')} authoritative={verification.get('authoritative')} "
            f"errors={verification.get('errors')} stage={verification.get('failed_stage')}"
        )

    # Persist a reviewer receipt binding exact bundle bytes (strip non-JSON bytes).
    receipt = {
        key: value
        for key, value in verification.items()
        if key != "archive_bytes" and not isinstance(value, (bytes, bytearray))
    }
    receipt["format"] = receipt.get("format") or "pcs-end-to-end-verifier-v06-v1"
    receipt["pilot_id"] = PILOT_ID
    receipt["intake_semantic_hash"] = intake_lock["intake_semantic_hash"]
    receipt["reviewer_environment"] = {
        "python_version": sys.version.split()[0],
        "platform": sys.platform,
        "cwd": str(reviewer.resolve()),
        "bundle_sha256": verification.get("bundle_sha256"),
        "verified_at": _utc_now(),
    }
    _write_json(receipt_path, receipt, overwrite=True)

    report_text = _reviewer_report(
        verification=verification,
        fingerprint=fingerprint,
        intake_lock=intake_lock,
        trust_boundary=TRUST_BOUNDARY,
    )
    report_path = reviewer / "REVIEWER_REPORT.md"
    _write_text(report_path, report_text, overwrite=True)

    # D. Adversarial fail-closed suite.
    adv = run_adversarial_cases(
        bundle=reviewer_bundle,
        public_key=reviewer_key,
        fingerprint=fingerprint,
        work=adversarial,
        lean_authority_path=lean_authority_path or authority.get("path"),
        receipt_path=receipt_path,
    )
    _write_json(adversarial / "ADVERSARIAL_RESULTS.json", adv, overwrite=True)
    if not adv["pass"]:
        raise IndependentPilotError(
            f"adversarial suite failed to reject: {adv['failed_attacks']}"
        )

    # Archival packaging + closeout plan.
    delivery_archive = archive / "pilot-delivery"
    delivery_archive.mkdir(parents=True, exist_ok=False)
    for src, name in (
        (reviewer_bundle, "study.pcs.zip"),
        (reviewer_key, "trusted-public.pem"),
        (receipt_path, "verification-receipt.json"),
        (report_path, "REVIEWER_REPORT.md"),
        (limitations_path, "LIMITATIONS.md"),
        (lock_path, "pilot-intake.lock.json"),
        (adversarial / "ADVERSARIAL_RESULTS.json", "ADVERSARIAL_RESULTS.json"),
    ):
        shutil.copyfile(src, delivery_archive / name)

    trust_path = archive / "TRUST_BOUNDARY_ASSESSMENT.json"
    trust_doc = dict(TRUST_BOUNDARY)
    trust_doc["pilot_id"] = PILOT_ID
    trust_doc["bundle_sha256"] = verification.get("bundle_sha256")
    trust_doc["signer_fingerprint"] = fingerprint
    trust_doc["lean_authority"] = {
        "mode": verification.get("lean_authority", {}).get("mode"),
        "authority_sha256": verification.get("lean_authority", {}).get("authority_sha256"),
        "verdict": verification.get("lean_authority", {}).get("verdict"),
        "archive_mode": verification.get("lean_authority", {}).get("archive_mode"),
    }
    _write_json(trust_path, trust_doc, overwrite=True)
    shutil.copyfile(trust_path, delivery_archive / "TRUST_BOUNDARY_ASSESSMENT.json")

    # Closeout plan over the archive workspace (retain evidence, delete ephemeral keys).
    # Producer private key is never part of the delivery archive; classify producer keys
    # for deletion in the producer workspace closeout.
    producer_workspace = producer / "keys"
    closeout_plan = build_closeout_plan(
        producer_workspace,
        pilot_id=PILOT_ID,
        retain_paths=["demo-producer-public.pem"],
        delete_paths=["demo-producer-private.pem"],
    )
    plan_path = write_closeout_plan(archive / "closeout-plan.json", closeout_plan, overwrite=True)
    closeout_receipt = None
    if apply_closeout:
        closeout_receipt = apply_closeout_plan(
            producer_workspace,
            closeout_plan,
            confirm_plan_sha256=closeout_plan["plan_sha256"],
            applied_at=GENERATED_AT,
        )
        write_closeout_receipt(
            archive / "closeout-receipt.json",
            closeout_receipt,
            overwrite=True,
        )

    evidence = {
        "format": EVIDENCE_FORMAT,
        "pilot_id": PILOT_ID,
        "generated_at": _utc_now(),
        "commit": _git_head(),
        "toolchain": {
            "python": sys.version.split()[0],
            "platform": sys.platform,
            "lean_authority_mode": authority.get("mode"),
            "lean_authority_path": str(authority.get("path") or ""),
        },
        "stages": {
            "intake_frozen": True,
            "discovery_confirmed": True,
            "attested": attestation.get("valid") is True,
            "second_environment_verified": verification.get("valid") is True,
            "authoritative": verification.get("authoritative") is True,
            "adversarial_pass": adv["pass"],
            "closeout_planned": True,
            "closeout_applied": bool(apply_closeout),
        },
        "intake_semantic_hash": intake_lock["intake_semantic_hash"],
        "bundle_sha256": verification.get("bundle_sha256"),
        "certificate_semantic_hash": attestation.get("certificate_semantic_hash"),
        "signer_fingerprint": fingerprint,
        "claim_decisions": verification.get("claims"),
        "adversarial_failed_attacks": adv["failed_attacks"],
        "paths": {
            "lab": str(lab),
            "bundle": str(bundle),
            "reviewer_receipt": str(receipt_path),
            "reviewer_report": str(report_path),
            "limitations": str(limitations_path),
            "trust_boundary": str(trust_path),
            "adversarial": str(adversarial / "ADVERSARIAL_RESULTS.json"),
            "closeout_plan": str(plan_path),
            "delivery_archive": str(delivery_archive),
        },
        "non_claims": [
            "No external partnership or legal clearance is asserted.",
            "No biological, clinical, or regulatory acceptance is asserted.",
            "Demo keys are public and unsuitable for production trust roots.",
        ],
    }
    evidence_path = out / "EVIDENCE_LEDGER.json"
    _write_json(evidence_path, evidence, overwrite=True)

    md_report = _implementation_markdown(evidence, trust_doc, adv)
    _write_text(out / "INDEPENDENT_PILOT_REPORT.md", md_report, overwrite=True)

    return evidence


def _git_head() -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=_repo_root(),
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    if proc.returncode != 0:
        return "unknown"
    return proc.stdout.strip()


def _implementation_markdown(
    evidence: Mapping[str, Any],
    trust: Mapping[str, Any],
    adversarial: Mapping[str, Any],
) -> str:
    lines = [
        "# Independent scientific pilot — evidence report",
        "",
        f"- Format: `{evidence.get('format')}`",
        f"- Pilot ID: `{evidence.get('pilot_id')}`",
        f"- Commit: `{evidence.get('commit')}`",
        f"- Bundle SHA-256: `{evidence.get('bundle_sha256')}`",
        f"- Intake semantic hash: `{evidence.get('intake_semantic_hash')}`",
        f"- Signer fingerprint: `{evidence.get('signer_fingerprint')}`",
        "",
        "## Stage outcomes",
        "",
    ]
    for key, value in (evidence.get("stages") or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines += [
        "",
        "## Adversarial results",
        "",
        f"- Pass: `{adversarial.get('pass')}`",
        f"- Failed attacks: `{adversarial.get('failed_attacks')}`",
        "",
    ]
    for case in adversarial.get("cases") or []:
        lines.append(
            f"- `{case.get('attack')}` rejected=`{case.get('rejected')}`"
        )
    lines += [
        "",
        "## Trust boundary",
        "",
        "See `archive/TRUST_BOUNDARY_ASSESSMENT.json` for the machine-readable",
        "separation of kernel-proved guarantees, independently tested properties,",
        "and unproved environmental assumptions.",
        "",
        "## Exact reproduce commands",
        "",
        "```bash",
        "python -m pip install -e '.[dev]'",
        "source scripts/activate_lean_428.sh",
        "cd formal && lake build pcs-lean-authority && cd ..",
        "python scripts/run_independent_scientific_pilot_v1.py --output /tmp/pcs-independent-pilot",
        "python scripts/run_cleanroom_independent_pilot_v1.py --output /tmp/pcs-cleanroom-pilot",
        "```",
        "",
    ]
    return "\n".join(lines)


def run_cleanroom_independent_pilot_v1(
    output_dir: str | Path,
    *,
    python_executable: str | None = None,
    lean_authority_path: str | Path | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Run the pilot inside a fresh virtualenv without reusing site-packages caches.

    The clean-room runner:
    - creates a new temporary virtual environment;
    - installs the repository editable package with hash-pinned lock constraints
      when `uv` is available, otherwise pip + requirements-dev.lock hashes;
    - invokes the pilot as a subprocess with a cleared credential-like env;
    - refuses to inherit `PCS_LEAN_AUTHORITY_BIN` unless explicitly passed.
    """
    out = Path(output_dir).resolve()
    if out.exists():
        if not overwrite:
            raise IndependentPilotError(f"clean-room output already exists: {out}")
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=False)

    root = _repo_root()
    py = python_executable or sys.executable
    venv_dir = out / "venv"
    pilot_out = out / "pilot"

    subprocess.run([py, "-m", "venv", str(venv_dir)], check=True, cwd=root)
    if os.name == "nt":
        venv_python = venv_dir / "Scripts" / "python.exe"
        venv_pip = venv_dir / "Scripts" / "pip.exe"
    else:
        venv_python = venv_dir / "bin" / "python"
        venv_pip = venv_dir / "bin" / "pip"

    # Fresh install; disable user site and pip cache for the clean-room claim.
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(out / "home"),
        "TMPDIR": str(out / "tmp"),
        "PYTHONNOUSERSITE": "1",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PIP_NO_CACHE_DIR": "1",
        "LANG": "C.UTF-8",
    }
    (out / "home").mkdir(exist_ok=True)
    (out / "tmp").mkdir(exist_ok=True)

    # Propagate Lean toolchain PATH if present; do not propagate credentials.
    for key in ("PATH",):
        if key in os.environ:
            env[key] = os.environ[key]
    if lean_authority_path is not None:
        env["PCS_LEAN_AUTHORITY_BIN"] = str(Path(lean_authority_path).resolve())
    elif os.environ.get("PCS_LEAN_AUTHORITY_BIN"):
        env["PCS_LEAN_AUTHORITY_BIN"] = os.environ["PCS_LEAN_AUTHORITY_BIN"]

    subprocess.run(
        [
            str(venv_pip),
            "install",
            "--upgrade",
            "pip",
            "setuptools",
            "wheel",
        ],
        check=True,
        cwd=root,
        env=env,
    )
    lock = root / "requirements-dev.lock"
    if lock.is_file():
        subprocess.run(
            [
                str(venv_pip),
                "install",
                "--require-hashes",
                "-r",
                str(lock),
            ],
            check=True,
            cwd=root,
            env=env,
        )
    subprocess.run(
        [str(venv_pip), "install", "--no-deps", "-e", str(root)],
        check=True,
        cwd=root,
        env=env,
    )

    cmd = [
        str(venv_python),
        str(root / "scripts" / "run_independent_scientific_pilot_v1.py"),
        "--output",
        str(pilot_out),
        "--overwrite",
        "--apply-closeout",
    ]
    if lean_authority_path is not None:
        cmd.extend(["--lean-authority", str(lean_authority_path)])
    elif env.get("PCS_LEAN_AUTHORITY_BIN"):
        cmd.extend(["--lean-authority", env["PCS_LEAN_AUTHORITY_BIN"]])

    proc = subprocess.run(
        cmd,
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    (out / "cleanroom-stdout.txt").write_text(proc.stdout, encoding="utf-8")
    (out / "cleanroom-stderr.txt").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        raise IndependentPilotError(
            f"clean-room pilot failed with exit {proc.returncode}: {proc.stderr[-4000:]}"
        )

    evidence_path = pilot_out / "EVIDENCE_LEDGER.json"
    if not evidence_path.is_file():
        raise IndependentPilotError("clean-room pilot did not emit EVIDENCE_LEDGER.json")
    evidence = strict_json_load(evidence_path)
    summary = {
        "format": "pcs-cleanroom-independent-pilot-v1",
        "pass": evidence.get("stages", {}).get("authoritative") is True
        and evidence.get("stages", {}).get("adversarial_pass") is True,
        "venv": str(venv_dir),
        "evidence": evidence,
        "stdout_sha256": hashlib.sha256(proc.stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(proc.stderr.encode()).hexdigest(),
    }
    _write_json(out / "CLEANROOM_SUMMARY.json", summary, overwrite=True)
    return summary
