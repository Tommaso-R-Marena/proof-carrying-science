from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .canonical_json import canonicalize_jcs_bytes
from .certificate_semantics_v06 import artifact_ids_from_predicate
from .certificate_v06 import CHECKER_VERSION_V06
from .jsonio import StrictJSONError, strict_json_load
from .replay_v06 import replay_evidence_item_v06


REGISTRY_FORMAT_V06 = "pcs-real-world-benchmark-registry-v1"
REPORT_FORMAT_V06 = "pcs-real-world-validation-report-v1"
REPORT_HASH_DOMAIN_V06 = "pcs-real-world-validation-sha256-v1"
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_OUTCOMES = {"PASS", "FAIL", "UNVERIFIED"}


class V06BenchmarkError(ValueError):
    pass


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _safe_fixture(root: Path, rel: str) -> Path:
    if not isinstance(rel, str) or not rel:
        raise V06BenchmarkError("fixture path must be a non-empty string")
    raw_path = root / rel
    if raw_path.is_symlink():
        raise V06BenchmarkError(f"benchmark fixture must not be a symlink: {rel!r}")
    path = raw_path.resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise V06BenchmarkError(f"benchmark fixture escapes registry directory: {rel!r}") from exc
    if not path.is_file():
        raise V06BenchmarkError(f"benchmark fixture is not a regular file: {rel!r}")
    return path


def _validate_source(source: Any, case_id: str) -> dict[str, Any]:
    if not isinstance(source, dict):
        raise V06BenchmarkError(f"case {case_id}: source must be an object")
    required = {"name", "url", "citation"}
    if not required.issubset(source):
        raise V06BenchmarkError(
            f"case {case_id}: source requires {sorted(required)}"
        )
    if not isinstance(source["url"], str) or not source["url"].startswith("https://"):
        raise V06BenchmarkError(f"case {case_id}: source.url must be HTTPS")
    for field in ("name", "citation"):
        if not isinstance(source[field], str) or not source[field].strip():
            raise V06BenchmarkError(f"case {case_id}: source.{field} must be non-empty")
    source_hash = source.get("source_sha256")
    if source_hash is not None and (
        not isinstance(source_hash, str)
        or not re.fullmatch(r"[a-f0-9]{64}", source_hash)
    ):
        raise V06BenchmarkError(
            f"case {case_id}: source_sha256 must be lowercase SHA-256 hex"
        )
    return source


def load_benchmark_registry_v06(path: str | Path) -> tuple[dict[str, Any], bytes]:
    registry_path = Path(path)
    try:
        raw = registry_path.read_bytes()
        obj = strict_json_load(registry_path)
    except (OSError, StrictJSONError) as exc:
        raise V06BenchmarkError(
            f"cannot load benchmark registry: {type(exc).__name__}: {exc}"
        ) from exc

    if not isinstance(obj, dict):
        raise V06BenchmarkError("benchmark registry root must be an object")
    if obj.get("format") != REGISTRY_FORMAT_V06:
        raise V06BenchmarkError("unsupported benchmark registry format")
    cases = obj.get("cases")
    if not isinstance(cases, list) or not cases:
        raise V06BenchmarkError("benchmark registry requires a non-empty cases array")

    seen: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            raise V06BenchmarkError("benchmark cases must be objects")
        case_id = case.get("id")
        if not isinstance(case_id, str) or not _SAFE_ID.fullmatch(case_id):
            raise V06BenchmarkError(f"invalid benchmark case id: {case_id!r}")
        if case_id in seen:
            raise V06BenchmarkError(f"duplicate benchmark case id: {case_id}")
        seen.add(case_id)
        _validate_source(case.get("source"), case_id)
        if case.get("expected_outcome") not in _OUTCOMES:
            raise V06BenchmarkError(
                f"case {case_id}: expected_outcome must be one of {sorted(_OUTCOMES)}"
            )
        check = case.get("check")
        if not isinstance(check, dict) or not isinstance(check.get("type"), str):
            raise V06BenchmarkError(f"case {case_id}: check must be a typed object")
        artifacts = case.get("artifacts", {})
        if not isinstance(artifacts, dict):
            raise V06BenchmarkError(f"case {case_id}: artifacts must be an object")

    return obj, raw


def _case_artifacts(
    case: dict[str, Any],
    *,
    registry_root: Path,
) -> tuple[dict[str, Path], list[dict[str, Any]]]:
    artifact_paths: dict[str, Path] = {}
    provenance: list[dict[str, Any]] = []
    for artifact_id, meta in case.get("artifacts", {}).items():
        if not isinstance(artifact_id, str) or not _SAFE_ID.fullmatch(artifact_id):
            raise V06BenchmarkError(
                f"case {case['id']}: invalid artifact id {artifact_id!r}"
            )
        if not isinstance(meta, dict):
            raise V06BenchmarkError(
                f"case {case['id']}: artifact {artifact_id} metadata must be an object"
            )
        path = _safe_fixture(registry_root, meta.get("path"))
        raw = path.read_bytes()
        actual = _sha256_bytes(raw)
        expected = meta.get("sha256")
        if not isinstance(expected, str) or not re.fullmatch(r"[a-f0-9]{64}", expected):
            raise V06BenchmarkError(
                f"case {case['id']}: artifact {artifact_id} requires lowercase sha256"
            )
        if actual != expected:
            raise V06BenchmarkError(
                f"case {case['id']}: fixture hash mismatch for {artifact_id}: "
                f"expected={expected} actual={actual}"
            )
        artifact_paths[artifact_id] = path
        provenance.append(
            {
                "id": artifact_id,
                "path": meta["path"],
                "sha256": actual,
                "size": len(raw),
            }
        )
    return artifact_paths, provenance


def run_benchmark_registry_v06(path: str | Path) -> dict[str, Any]:
    registry_path = Path(path).resolve()
    registry, registry_bytes = load_benchmark_registry_v06(registry_path)
    root = registry_path.parent

    case_results: list[dict[str, Any]] = []
    for case in registry["cases"]:
        artifact_paths, artifact_provenance = _case_artifacts(
            case,
            registry_root=root,
        )
        spec = case["check"]
        required_artifacts = set(artifact_ids_from_predicate(spec))
        missing = sorted(required_artifacts - set(artifact_paths))
        unexpected = sorted(set(artifact_paths) - required_artifacts)
        if missing or unexpected:
            raise V06BenchmarkError(
                f"case {case['id']}: artifact scope mismatch: "
                f"missing={missing} unexpected={unexpected}"
            )

        evidence = {
            "id": case["id"],
            "kind": "computational_test",
            "claim_ids": [],
            "outcome": "UNVERIFIED",
            "checker": CHECKER_VERSION_V06,
            "predicate": spec,
            "artifact_ids": list(artifact_ids_from_predicate(spec)),
            "check_spec": spec,
        }
        replayed = replay_evidence_item_v06(evidence, artifact_paths)
        actual = replayed["outcome"]
        expected = case["expected_outcome"]
        case_results.append(
            {
                "id": case["id"],
                "title": case.get("title", case["id"]),
                "source": case["source"],
                "derivation": case.get("derivation"),
                "check_type": spec["type"],
                "expected_outcome": expected,
                "actual_outcome": actual,
                "matched_expected": actual == expected,
                "artifacts": artifact_provenance,
                "details": replayed.get("details", {}),
                "interpretation": case.get("interpretation"),
            }
        )

    report_without_hash = {
        "format": REPORT_FORMAT_V06,
        "registry_format": registry["format"],
        "registry_sha256": _sha256_bytes(registry_bytes),
        "checker_version": CHECKER_VERSION_V06,
        "cases": case_results,
        "summary": {
            "cases": len(case_results),
            "matched_expected": sum(1 for c in case_results if c["matched_expected"]),
            "unexpected": sum(1 for c in case_results if not c["matched_expected"]),
            "expected_pass": sum(
                1 for c in case_results if c["expected_outcome"] == "PASS"
            ),
            "expected_fail": sum(
                1 for c in case_results if c["expected_outcome"] == "FAIL"
            ),
        },
    }
    semantic_hash = _sha256_bytes(
        REPORT_HASH_DOMAIN_V06.encode("utf-8")
        + b"\x00"
        + canonicalize_jcs_bytes(report_without_hash)
    )
    return {
        **report_without_hash,
        "report_semantic_hash_format": REPORT_HASH_DOMAIN_V06,
        "report_semantic_hash": semantic_hash,
    }


def write_benchmark_report_v06(
    report: dict[str, Any],
    output: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    path = Path(output).resolve()
    if path.exists() and not overwrite:
        raise V06BenchmarkError(f"refusing to overwrite benchmark report: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonicalize_jcs_bytes(report) + b"\n")
    return path
