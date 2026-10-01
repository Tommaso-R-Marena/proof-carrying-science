from __future__ import annotations

import base64
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .canonical_json import canonicalize_jcs_bytes


LEAN_AUTHORITY_TRANSCRIPT_FORMAT_V06 = "pcs-lean-authority-observations-v1"
LEAN_AUTHORITY_RESULT_FORMAT_V06 = "pcs-lean-authority-result-v1"
LEAN_AUTHORITY_ENV_V06 = "PCS_LEAN_AUTHORITY_BIN"
LEAN_AUTHORITY_TIMEOUT_SECONDS_V06 = 300


class V06LeanAuthorityError(RuntimeError):
    pass


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _repo_root() -> Path | None:
    here = Path(__file__).resolve()
    candidate = here.parents[1]
    if (candidate / "formal" / "lakefile.toml").is_file():
        return candidate
    return None


def _bundled_authority_path() -> Path | None:
    root = getattr(sys, "_MEIPASS", None)
    if not root:
        return None
    name = "pcs-lean-authority.exe" if os.name == "nt" else "pcs-lean-authority"
    candidate = Path(root) / name
    return candidate if candidate.is_file() else None


def _repo_authority_path(root: Path) -> Path | None:
    name = "pcs-lean-authority.exe" if os.name == "nt" else "pcs-lean-authority"
    candidate = root / "formal" / ".lake" / "build" / "bin" / name
    return candidate if candidate.is_file() else None


def resolve_lean_authority_v06(explicit: str | Path | None = None) -> dict[str, Any]:
    """Resolve receiver-owned Lean authority without trusting producer content.

    Resolution is intentionally narrow: explicit receiver path, receiver-set
    environment variable, PyInstaller-embedded authority, repository build, then
    repository source through Lake. Arbitrary PATH entries are not trusted
    implicitly.
    """
    if explicit is not None:
        path = Path(explicit).expanduser().resolve()
        if not path.is_file():
            raise V06LeanAuthorityError(f"Lean authority executable does not exist: {path}")
        return {"mode": "binary", "path": path}

    configured = os.environ.get(LEAN_AUTHORITY_ENV_V06)
    if configured:
        path = Path(configured).expanduser().resolve()
        if not path.is_file():
            raise V06LeanAuthorityError(
                f"{LEAN_AUTHORITY_ENV_V06} points to a missing authority executable: {path}"
            )
        return {"mode": "binary", "path": path}

    bundled = _bundled_authority_path()
    if bundled is not None:
        return {"mode": "embedded-binary", "path": bundled}

    root = _repo_root()
    if root is not None:
        built = _repo_authority_path(root)
        if built is not None:
            return {"mode": "repository-binary", "path": built}
        lake = shutil.which("lake")
        driver = root / "formal" / "PCSAuthority.lean"
        if lake and driver.is_file():
            return {
                "mode": "repository-source",
                "lake": Path(lake).resolve(),
                "formal_root": root / "formal",
                "driver": driver,
            }

    raise V06LeanAuthorityError(
        "Lean authority is required but unavailable. Build it with "
        "`cd formal && lake build pcs-lean-authority`, use the standalone verifier "
        "artifact, or provide a receiver-owned authority with --lean-authority."
    )


def _public_key_raw_base64(public_key: Ed25519PublicKey) -> str:
    raw = public_key.public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    return base64.b64encode(raw).decode("ascii")


def build_authority_transcript_v06(
    *,
    certificate: Mapping[str, Any],
    environment_replay: Mapping[str, Any],
    workflow_replay: Mapping[str, Any],
    replay: Mapping[str, Any],
) -> dict[str, Any]:
    if environment_replay.get("valid") is not True:
        raise V06LeanAuthorityError("cannot authorize failed environment replay")
    if workflow_replay.get("valid") is not True:
        raise V06LeanAuthorityError("cannot authorize failed workflow replay")
    if replay.get("valid") is not True:
        raise V06LeanAuthorityError("cannot authorize failed scientific replay")

    observations = []
    for item in replay.get("evidence", []):
        if not isinstance(item, Mapping):
            raise V06LeanAuthorityError("replay evidence observation is not an object")
        observations.append(
            {
                "evidence_id": item.get("id"),
                "kind": item.get("kind"),
                "outcome": item.get("outcome"),
            }
        )
    expected_ids = [item.get("id") for item in certificate.get("evidence", [])]
    actual_ids = [item["evidence_id"] for item in observations]
    if actual_ids != expected_ids:
        raise V06LeanAuthorityError(
            "authority replay observations do not exactly cover certificate evidence in order"
        )

    fresh_capture = environment_replay.get("_authority_fresh_capture")
    if certificate.get("environment") is not None and fresh_capture is None:
        raise V06LeanAuthorityError(
            "environment-bound certificate is missing fresh authority capture"
        )

    return {
        "format": LEAN_AUTHORITY_TRANSCRIPT_FORMAT_V06,
        "certificate_semantic_hash": certificate["semantic_hash"],
        "checker_version": certificate["checker_version"],
        "workflow_ok": True,
        "environment_capture": fresh_capture,
        "replay": observations,
    }


def _safe_materialize(
    root: Path,
    package_files: Mapping[str, bytes],
    *,
    certificate_signature_bytes: bytes,
    package_manifest_bytes: bytes,
    package_signature_bytes: bytes,
) -> None:
    all_files: dict[str, bytes] = dict(package_files)
    all_files["certificate_signature.json"] = certificate_signature_bytes
    all_files["package_manifest.json"] = package_manifest_bytes
    all_files["package_signature.json"] = package_signature_bytes
    for name, raw in all_files.items():
        if not isinstance(name, str) or not isinstance(raw, bytes):
            raise V06LeanAuthorityError(
                "authority materialization requires string names and bytes"
            )
        path = PurePosixPath(name)
        if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
            raise V06LeanAuthorityError(f"unsafe authority member path: {name!r}")
        target = root.joinpath(*path.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)


def run_lean_authority_v06(
    *,
    certificate: Mapping[str, Any],
    environment_replay: Mapping[str, Any],
    workflow_replay: Mapping[str, Any],
    replay: Mapping[str, Any],
    certificate_signature_bytes: bytes,
    package_manifest_bytes: bytes,
    package_signature_bytes: bytes,
    package_files: Mapping[str, bytes],
    public_key: Ed25519PublicKey,
    expected_fingerprint: str | None,
    authority_path: str | Path | None = None,
    timeout_seconds: int = LEAN_AUTHORITY_TIMEOUT_SECONDS_V06,
) -> dict[str, Any]:
    transcript = build_authority_transcript_v06(
        certificate=certificate,
        environment_replay=environment_replay,
        workflow_replay=workflow_replay,
        replay=replay,
    )
    transcript_bytes = canonicalize_jcs_bytes(transcript)
    resolved = resolve_lean_authority_v06(authority_path)

    with tempfile.TemporaryDirectory(prefix="pcs-v06-lean-authority-") as tmp:
        temp = Path(tmp)
        package_root = temp / "package"
        package_root.mkdir()
        _safe_materialize(
            package_root,
            package_files,
            certificate_signature_bytes=certificate_signature_bytes,
            package_manifest_bytes=package_manifest_bytes,
            package_signature_bytes=package_signature_bytes,
        )
        transcript_path = temp / "observations.json"
        transcript_path.write_bytes(transcript_bytes)
        args = [
            str(package_root),
            _public_key_raw_base64(public_key),
            str(transcript_path),
        ]
        if expected_fingerprint:
            args.append(expected_fingerprint)

        if resolved["mode"] == "repository-source":
            cmd = [
                str(resolved["lake"]),
                "env",
                "lean",
                "--run",
                str(resolved["driver"]),
                *args,
            ]
            cwd = resolved["formal_root"]
            authority_sha256 = hashlib.sha256(
                Path(resolved["driver"]).read_bytes()
            ).hexdigest()
        else:
            executable = Path(resolved["path"])
            cmd = [str(executable), *args]
            cwd = None
            authority_sha256 = _sha256_file(executable)

        try:
            proc = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise V06LeanAuthorityError(
                f"Lean authority invocation failed: {type(exc).__name__}: {exc}"
            ) from exc

    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        raise V06LeanAuthorityError(
            f"Lean authority failed with exit code {proc.returncode}: {detail}"
        )
    verdict = proc.stdout.strip()
    if verdict not in {"ACCEPT", "REJECT"}:
        raise V06LeanAuthorityError(
            f"Lean authority returned an invalid verdict: {verdict!r}"
        )
    return {
        "format": LEAN_AUTHORITY_RESULT_FORMAT_V06,
        "required": True,
        "accepted": verdict == "ACCEPT",
        "verdict": verdict,
        "mode": resolved["mode"],
        "authority_sha256": authority_sha256,
        "observation_transcript_sha256": hashlib.sha256(transcript_bytes).hexdigest(),
        "certificate_semantic_hash": certificate["semantic_hash"],
    }


def enforce_lean_authority_v06(
    verification: Mapping[str, Any],
    *,
    authority_context: Mapping[str, Any],
    certificate_signature_bytes: bytes,
    package_manifest_bytes: bytes,
    package_signature_bytes: bytes,
    package_files: Mapping[str, bytes],
    public_key: Ed25519PublicKey,
    expected_fingerprint: str | None,
    authority_path: str | Path | None = None,
) -> dict[str, Any]:
    result = dict(verification)
    stages = dict(result.get("stages", {}))
    stages["lean_authority"] = False
    result["stages"] = stages
    if result.get("valid") is not True:
        result["authority_required"] = True
        result["authoritative"] = False
        result["lean_authority"] = {
            "format": LEAN_AUTHORITY_RESULT_FORMAT_V06,
            "required": True,
            "accepted": False,
            "verdict": "NOT_RUN_PYTHON_PRECHECK_FAILED",
        }
        return result

    authority = run_lean_authority_v06(
        certificate=authority_context["certificate"],
        environment_replay=authority_context["environment_replay"],
        workflow_replay=authority_context["workflow_replay"],
        replay=authority_context["replay"],
        certificate_signature_bytes=certificate_signature_bytes,
        package_manifest_bytes=package_manifest_bytes,
        package_signature_bytes=package_signature_bytes,
        package_files=package_files,
        public_key=public_key,
        expected_fingerprint=expected_fingerprint,
        authority_path=authority_path,
    )
    result["lean_authority"] = authority
    result["authority_required"] = True
    result["authoritative"] = bool(authority["accepted"])
    if not authority["accepted"]:
        result["valid"] = False
        result["failed_stage"] = "lean_authority"
        result["errors"] = [
            "Lean authority rejected the exact package bytes and external observation transcript"
        ]
        return result
    stages["lean_authority"] = True
    return result
