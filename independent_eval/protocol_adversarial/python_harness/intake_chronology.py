"""Frozen-intake chronology and provenance attack scenarios (black-box).

Compatible with current ``main`` intake APIs. When newer reviewer-side intake
verification modules exist (e.g. PR #120), optional extended checks are run.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from .paths import REPO_ROOT, RESULTS


def run_intake_chronology(work: Path) -> dict[str, Any]:
    from pcs.intake import (
        PilotIntakeError,
        assert_lock_matches_certificate,
        freeze_intake,
        freeze_intake_file,
        validate_lock,
    )

    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    lab = work / "lab"
    lab.mkdir()
    src = REPO_ROOT / "examples" / "pkpd_one_compartment"
    shutil.copyfile(src / "pilot_intake.json", lab / "pilot_intake.json")

    lock = freeze_intake_file(lab / "pilot_intake.json", work / "honest.lock.json", overwrite=True)
    validate_lock(lock)
    expected_hash = lock["intake_semantic_hash"]

    scenarios: list[dict[str, Any]] = []

    # 1) Post-hoc claim mutation vs locked intake
    mutated_cert = {
        "claims": [
            {
                "id": c["id"],
                "statement": "Post-hoc claim invented after seeing results.",
                "kind": c.get("desired_assurance", "computational"),
            }
            for c in lock["intake"]["claims"]
        ],
        "assumptions": [
            {"id": a["id"], "statement": a["statement"]} for a in lock["intake"]["assumptions"]
        ],
    }
    try:
        assert_lock_matches_certificate(lock, mutated_cert)
        posthoc = {"rejected": False, "error": None}
    except PilotIntakeError as exc:
        posthoc = {"rejected": True, "error": str(exc)}
    scenarios.append(
        {
            "id": "post_hoc_claim_vs_lock",
            "kind": "attack",
            "result": posthoc,
            "expected": "reject",
        }
    )

    # 2) Forged frozen_at metadata (producer-controlled) with intact intake hash
    forged = dict(lock)
    forged["frozen_at"] = "2099-12-31T23:59:59+00:00"
    try:
        validate_lock(forged)
        forged_valid = True
        forged_error = None
    except PilotIntakeError as exc:
        forged_valid = False
        forged_error = str(exc)
    scenarios.append(
        {
            "id": "forged_frozen_at_still_hash_valid",
            "kind": "chronology",
            "lock_valid": forged_valid,
            "error": forged_error,
            "intake_semantic_hash_unchanged": forged.get("intake_semantic_hash") == expected_hash,
            "observation": (
                "Producer can choose frozen_at without changing intake_semantic_hash; "
                "timestamp alone is not preregistration evidence."
            ),
        }
    )

    # 3) Substituted intake body with recomputed hash (internally consistent, different commitment)
    mutated_intake = json.loads(json.dumps(lock["intake"]))
    mutated_intake["claims"][0]["statement"] = "Substituted weaker claim."
    alt_lock = freeze_intake(mutated_intake)
    scenarios.append(
        {
            "id": "substituted_intake_new_hash",
            "kind": "attack",
            "original_hash": expected_hash,
            "substituted_hash": alt_lock["intake_semantic_hash"],
            "hashes_differ": expected_hash != alt_lock["intake_semantic_hash"],
            "observation": (
                "A reviewer-owned out-of-band commitment to the original hash would detect "
                "this substitution; package-local consistency alone would not."
            ),
        }
    )

    # 4) Replay: copy lock bytes and claim later use
    replay_path = work / "replayed.lock.json"
    shutil.copyfile(work / "honest.lock.json", replay_path)
    scenarios.append(
        {
            "id": "replayed_preregistration_record",
            "kind": "chronology",
            "replay_sha256": hashlib.sha256(replay_path.read_bytes()).hexdigest(),
            "original_sha256": hashlib.sha256((work / "honest.lock.json").read_bytes()).hexdigest(),
            "observation": (
                "Byte-identical replay of a lock is trivial for the producer; "
                "independent timestamping/notary would be required for wall-clock evidence."
            ),
        }
    )

    # Optional extended checks if PR #120 modules exist in the environment under test
    extended = {"available": False}
    try:
        from pcs.intake_verify_v06 import verify_package_intake_lock_v06  # type: ignore
        from pcs.intake import INTAKE_LOCK_PACKAGE_MEMBER_V06  # type: ignore
        from pcs.canonical_json import canonicalize_jcs_bytes

        cert_like = {
            "claims": [
                {
                    "id": c["id"],
                    "statement": c["statement"],
                    "kind": c["desired_assurance"],
                }
                for c in forged["intake"]["claims"]
            ],
            "assumptions": [
                {"id": a["id"], "statement": a["statement"]} for a in forged["intake"]["assumptions"]
            ],
        }
        package_files = {INTAKE_LOCK_PACKAGE_MEMBER_V06: canonicalize_jcs_bytes(forged)}
        checked = verify_package_intake_lock_v06(
            certificate=cert_like,
            package_files=package_files,
            require_intake_lock=True,
        )
        wrong = verify_package_intake_lock_v06(
            certificate=cert_like,
            package_files=package_files,
            require_intake_lock=True,
            expected_intake_semantic_hash="ab" * 32,
        )
        extended = {
            "available": True,
            "forged_time_preregistration_evidence": checked.get("preregistration_evidence"),
            "wrong_expected_hash_valid": wrong.get("valid"),
        }
        scenarios.append(
            {
                "id": "optional_reviewer_expected_hash_module",
                "kind": "extended",
                "extended": extended,
            }
        )
    except Exception as exc:  # noqa: BLE001
        extended = {"available": False, "error": f"{type(exc).__name__}: {exc}"}
        scenarios.append(
            {
                "id": "optional_reviewer_expected_hash_module",
                "kind": "extended",
                "extended": extended,
                "note": "Module absent on this PCS revision; chronology conclusions use lock APIs only.",
            }
        )

    report = {
        "format": "pcs-independent-intake-chronology-v1",
        "scenario_count": len(scenarios),
        "scenarios": scenarios,
        "principles": [
            "Hash integrity ≠ pre-results specification.",
            "Signature authenticity ≠ reviewer-owned preregistration binding.",
            "frozen_at is producer metadata only.",
            "Reviewer-owned expected intake semantic hash is the out-of-band commitment under test when available.",
        ],
        "pass": posthoc["rejected"] is True and expected_hash != alt_lock["intake_semantic_hash"],
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "intake_chronology.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report
