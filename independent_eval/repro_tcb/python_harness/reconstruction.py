"""Task 12 — Cross-environment reconstruction harness.

Rebuilds and verifies evidence across clean directories and available Python
interpreters. Distinguishes:

* ``identical_archive_replay`` — same ZIP bytes copied/verified elsewhere
* ``regenerated_archive`` — members re-packed (may differ unless canonical)

Records commits, binary hashes, toolchains, and platforms in the result object.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from .canonical_zip import canonical_zip_bytes, noncanonical_zip_bytes, read_zip_members
from .environment import capture_host_environment
from .hashing import sha256_bytes, sha256_file, sha256_json
from .paths import EVIDENCE_FIXTURES, RESULTS

ReplayMode = Literal["identical_archive_replay", "regenerated_archive", "regenerated_noncanonical"]


@dataclass(frozen=True)
class EvidenceMembers:
    """In-memory evidence package members."""

    members: dict[str, bytes]
    label: str = "synthetic"

    @property
    def canonical_archive(self) -> bytes:
        return canonical_zip_bytes(self.members)

    @property
    def member_digests(self) -> dict[str, str]:
        return {name: sha256_bytes(data) for name, data in sorted(self.members.items())}


def load_fixture_members(fixture_dir: Path | None = None) -> EvidenceMembers:
    root = fixture_dir or EVIDENCE_FIXTURES
    members: dict[str, bytes] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "README.md":
            rel = path.relative_to(root).as_posix()
            members[rel] = path.read_bytes()
    if not members:
        raise FileNotFoundError(f"no evidence members under {root}")
    return EvidenceMembers(members=members, label=root.name)


def build_synthetic_members() -> EvidenceMembers:
    """Deterministic synthetic evidence used when fixtures are being created."""
    cert = {
        "format": "pcs-independent-eval-evidence-v1",
        "claim_id": "reaction_balance.demo",
        "status": "PASS",
        "semantic_hash": "synthetic-semantic-v1",
    }
    policy = {
        "format": "pcs-acceptance-policy-v1",
        "required_claims": {"reaction_balance.demo": ["PASS"]},
    }
    transcript = {
        "format": "pcs-lean-authority-observations-v1",
        "observations": [{"check": "sha256_bound", "result": "ok"}],
    }
    members = {
        "certificate.json": json.dumps(cert, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        "policy.json": json.dumps(policy, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        "transcript.json": json.dumps(transcript, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        "README.txt": b"Synthetic independent-eval evidence fixture. Not a production certificate.\n",
    }
    return EvidenceMembers(members=members, label="synthetic")


def _verify_archive_in_dir(archive: bytes, work: Path) -> dict[str, Any]:
    path = work / "evidence.zip"
    path.write_bytes(archive)
    digest = sha256_file(path)
    members = read_zip_members(archive)
    member_digests = {name: sha256_bytes(data) for name, data in sorted(members.items())}
    roundtrip = canonical_zip_bytes(members)
    return {
        "archive_path": str(path),
        "archive_sha256": digest,
        "member_count": len(members),
        "member_digests": member_digests,
        "canonical_roundtrip_sha256": sha256_bytes(roundtrip),
        "matches_canonical_encoding": roundtrip == archive,
    }


def _cross_python_verify(archive: bytes, interpreters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ask each discovered interpreter to recompute SHA-256 of the archive bytes."""
    results: list[dict[str, Any]] = []
    script = (
        "import hashlib,sys;"
        "data=sys.stdin.buffer.read();"
        "print(hashlib.sha256(data).hexdigest())"
    )
    for interp in interpreters:
        exe = interp.get("path")
        if not exe:
            continue
        try:
            proc = subprocess.run(
                [exe, "-c", script],
                input=archive,
                capture_output=True,
                check=True,
                timeout=30,
            )
            digest = proc.stdout.decode("utf-8").strip()
            results.append(
                {
                    "interpreter": exe,
                    "version": interp.get("version"),
                    "archive_sha256": digest,
                    "ok": True,
                }
            )
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            results.append(
                {
                    "interpreter": exe,
                    "version": interp.get("version"),
                    "ok": False,
                    "error": str(exc),
                }
            )
    return results


def reconstruct(
    *,
    mode: ReplayMode = "identical_archive_replay",
    fixture_dir: Path | None = None,
    output: Path | None = None,
    clean_dir_count: int = 2,
) -> dict[str, Any]:
    """Run a reconstruction campaign and return a machine-readable report."""
    evidence = load_fixture_members(fixture_dir) if (fixture_dir or EVIDENCE_FIXTURES).exists() else build_synthetic_members()
    if fixture_dir is None and not EVIDENCE_FIXTURES.exists():
        evidence = build_synthetic_members()
    else:
        try:
            evidence = load_fixture_members(fixture_dir)
        except FileNotFoundError:
            evidence = build_synthetic_members()

    host = capture_host_environment()
    canonical = evidence.canonical_archive
    canonical_sha = sha256_bytes(canonical)

    if mode == "identical_archive_replay":
        archive = canonical
        expected_identity = True
    elif mode == "regenerated_archive":
        # Re-pack members with the same canonical rules → byte-identical to original.
        archive = canonical_zip_bytes(dict(evidence.members))
        expected_identity = True
    elif mode == "regenerated_noncanonical":
        archive = noncanonical_zip_bytes(evidence.members)
        expected_identity = False
    else:
        raise ValueError(f"unknown mode: {mode}")

    archive_sha = sha256_bytes(archive)
    clean_results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="pcs-repro-tcb-") as tmp:
        base = Path(tmp)
        for i in range(max(1, clean_dir_count)):
            work = base / f"env-{i}"
            work.mkdir()
            # Isolate by copying archive into a fresh directory (no shared state).
            clean_results.append(_verify_archive_in_dir(archive, work))

    cross_python = _cross_python_verify(archive, host.get("interpreters") or [])

    identical_across_clean = len({r["archive_sha256"] for r in clean_results}) == 1
    identical_to_canonical = archive_sha == canonical_sha
    member_digests_stable = all(
        r["member_digests"] == evidence.member_digests for r in clean_results
    )

    cross_python_agree = all(
        row.get("ok") and row.get("archive_sha256") == archive_sha for row in cross_python
    ) if cross_python else False

    report: dict[str, Any] = {
        "format": "pcs-independent-eval-reconstruction-v1",
        "task": 12,
        "mode": mode,
        "distinction": {
            "identical_archive_replay": mode == "identical_archive_replay",
            "regenerated_archive": mode in {"regenerated_archive", "regenerated_noncanonical"},
            "expected_byte_identity_with_canonical": expected_identity,
            "observed_byte_identity_with_canonical": identical_to_canonical,
            "semantic_member_digests_stable": member_digests_stable,
        },
        "evidence": {
            "label": evidence.label,
            "member_digests": evidence.member_digests,
            "canonical_archive_sha256": canonical_sha,
            "delivered_archive_sha256": archive_sha,
        },
        "environment": host,
        "clean_directory_verifications": clean_results,
        "cross_python_verifications": cross_python,
        "verdict": {
            "clean_dirs_agree": identical_across_clean,
            "cross_python_agree": cross_python_agree,
            "mode_expectation_met": identical_to_canonical == expected_identity,
            "pass": identical_across_clean
            and member_digests_stable
            and (identical_to_canonical == expected_identity)
            and (cross_python_agree if cross_python else True),
        },
    }
    report["report_sha256"] = sha256_json(report)

    out = output or (RESULTS / f"reconstruction_{mode}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report["written_to"] = str(out)
    return report


def run_full_campaign(output_dir: Path | None = None) -> dict[str, Any]:
    """Run identical-replay, canonical regeneration, and noncanonical regeneration."""
    dest = output_dir or RESULTS
    dest.mkdir(parents=True, exist_ok=True)
    modes: list[ReplayMode] = [
        "identical_archive_replay",
        "regenerated_archive",
        "regenerated_noncanonical",
    ]
    results = {
        mode: reconstruct(mode=mode, output=dest / f"reconstruction_{mode}.json")
        for mode in modes
    }
    summary = {
        "format": "pcs-independent-eval-reconstruction-campaign-v1",
        "task": 12,
        "modes": {
            mode: {
                "pass": results[mode]["verdict"]["pass"],
                "delivered_archive_sha256": results[mode]["evidence"]["delivered_archive_sha256"],
                "canonical_archive_sha256": results[mode]["evidence"]["canonical_archive_sha256"],
                "observed_byte_identity_with_canonical": results[mode]["distinction"][
                    "observed_byte_identity_with_canonical"
                ],
            }
            for mode in modes
        },
        "pass": all(results[m]["verdict"]["pass"] for m in modes),
    }
    summary_path = dest / "reconstruction_campaign.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary["written_to"] = str(summary_path)
    return summary


def materialize_fixtures(target: Path | None = None) -> dict[str, str]:
    """Write synthetic evidence members and return path→sha256 map."""
    dest = target or EVIDENCE_FIXTURES
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    evidence = build_synthetic_members()
    digests: dict[str, str] = {}
    for name, data in evidence.members.items():
        path = dest / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        digests[name] = sha256_bytes(data)
    archive = evidence.canonical_archive
    archive_path = dest.parent / "evidence_canonical.zip"
    archive_path.write_bytes(archive)
    digests["evidence_canonical.zip"] = sha256_bytes(archive)
    return digests


if __name__ == "__main__":
    materialize_fixtures()
    campaign = run_full_campaign()
    print(json.dumps(campaign, indent=2, sort_keys=True))
