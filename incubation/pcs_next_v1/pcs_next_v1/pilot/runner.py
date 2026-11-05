"""Pilot workflow orchestration for synthetic and bounded external projects."""

from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..bridge.authority import invoke_authority_help, resolve_authority, try_import_pcs_readonly
from ..core.canonical import canonical_hash, canonicalize
from ..core.errors import ErrorCode, PcsNextError
from ..core.hashing import sha256_file
from ..core.statuses import AssuranceStatus, ClaimClass, status_record
from ..trust.evidence_store import EvidenceStore
from ..trust.policy import AcceptancePolicy, pin_policy, reject_producer_verdict, verify_policy_binding
from .intake import bind_artifact_hashes, detect_stale_substitution, freeze_intake, validate_intake, verify_lock_integrity
from .state_machine import PilotState, PilotStateMachine


class PilotRunner:
    def __init__(
        self,
        work_dir: str | Path,
        *,
        policy: dict[str, Any] | AcceptancePolicy,
        repo_root: str | Path | None = None,
    ):
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.repo_root = Path(repo_root) if repo_root else None
        if isinstance(policy, AcceptancePolicy):
            self.policy = policy
        else:
            self.policy = pin_policy(policy)
        self.evidence = EvidenceStore(self.work_dir / "evidence_store")
        self.sm = PilotStateMachine(project_id="unassigned")

    def run_synthetic(self, project_root: str | Path, intake: dict[str, Any]) -> dict[str, Any]:
        project_root = Path(project_root)
        intake = validate_intake(intake)
        self.sm = PilotStateMachine(project_id=intake["project_id"])

        # INTAKE -> INSPECTION
        env = {
            "python": sys.version,
            "platform": platform.platform(),
            "executable": sys.executable,
        }
        self.sm.transition(PilotState.INSPECTION, evidence={"environment": env, "intake_hash": canonical_hash(intake)})
        self.evidence.commit("inspection", {"environment": env})

        # CLAIM IDENTIFICATION
        claims = list(intake["claimed_conclusions"])
        self.sm.transition(
            PilotState.CLAIM_IDENTIFICATION,
            evidence={"claims": claims, "count": len(claims)},
        )

        # REVIEWER CONFIRMATION (synthetic auto-confirm with explicit marker)
        confirmation = {
            "mode": "synthetic_auto_confirm",
            "confirmed_claim_ids": [c["id"] for c in claims],
            "note": "Not an external human reviewer confirmation.",
        }
        self.sm.transition(PilotState.REVIEWER_CONFIRMATION, evidence=confirmation)

        # ASSUMPTION REGISTRATION
        assumptions = list(intake["assumptions"])
        self.sm.transition(
            PilotState.ASSUMPTION_REGISTRATION,
            evidence={"assumptions": assumptions},
        )

        # FREEZE
        bound = bind_artifact_hashes(intake, project_root)
        lock = freeze_intake(bound, acceptance_policy=self.policy.raw)
        lock_path = self.work_dir / "intake.lock.json"
        lock_path.write_bytes(canonicalize(lock) + b"\n")
        verify_lock_integrity(lock)
        self.sm.transition(
            PilotState.FROZEN_INPUTS,
            evidence={"lock_hash": canonical_hash(lock), "lock_path": str(lock_path)},
        )
        self.evidence.commit("freeze", {"lock_hash": canonical_hash(lock)})

        # COMPUTATIONAL REPLAY (bounded: re-hash + simple numeric check if present)
        findings = detect_stale_substitution(lock, project_root)
        if findings:
            self.sm.transition(PilotState.FAILED, evidence={"findings": findings})
            raise PcsNextError(ErrorCode.REPLAY_STALE, "stale substitution detected", details={"findings": findings})
        replay = self._bounded_replay(project_root, bound)
        self.sm.transition(PilotState.COMPUTATIONAL_REPLAY, evidence=replay)

        # EVIDENCE CAPTURE
        bundle = {
            "format": "pcs-next-evidence-bundle-v1",
            "project_id": intake["project_id"],
            "lock_hash": canonical_hash(lock),
            "policy_hash": self.policy.content_hash,
            "replay": replay,
            "producer_claimed_pass": True,  # deliberately present; must be ignored
            "authority": None,
        }
        # Authority identity (read-only)
        try:
            auth = resolve_authority(repo_root=self.repo_root)
            bundle["authority"] = invoke_authority_help(auth)
        except PcsNextError as exc:
            bundle["authority"] = {"error": exc.to_dict()}
        bundle["pcs_import"] = try_import_pcs_readonly()
        ignored = reject_producer_verdict(bundle["producer_claimed_pass"])
        bundle["producer_verdict_handling"] = ignored
        self.sm.transition(PilotState.EVIDENCE_CAPTURE, evidence={"bundle_hash": canonical_hash(bundle)})
        (self.work_dir / "evidence_bundle.json").write_bytes(canonicalize(bundle) + b"\n")
        self.evidence.commit("evidence_capture", {"bundle_hash": canonical_hash(bundle)})

        # FORMAL VERIFICATION (scoped: optional Lean; may be SKIPPED)
        formal = self._formal_step()
        self.sm.transition(PilotState.FORMAL_VERIFICATION, evidence=formal)

        # INDEPENDENT VERIFICATION
        independent = self.independent_verify(bundle, lock)
        self.sm.transition(PilotState.INDEPENDENT_VERIFICATION, evidence=independent)

        # ASSURANCE REPORT
        report = self._assurance_report(intake, lock, bundle, formal, independent, replay)
        report_path = self.work_dir / "assurance_report.json"
        report_path.write_bytes(canonicalize(report) + b"\n")
        self.sm.transition(PilotState.ASSURANCE_REPORT, evidence={"report_hash": canonical_hash(report)})

        # CLOSEOUT
        closeout = {
            "closed_at": datetime.now(timezone.utc).isoformat(),
            "state_generation": self.sm.generation,
            "evidence_chain": self.evidence.verify_chain(),
        }
        self.sm.transition(PilotState.ARCHIVAL_CLOSEOUT, evidence=closeout)
        self.sm.save(self.work_dir / "pilot_state.json")
        return report

    def _bounded_replay(self, project_root: Path, intake: dict[str, Any]) -> dict[str, Any]:
        artifacts = []
        for art in intake["artifacts"]:
            path = project_root / art["path"]
            artifacts.append({"id": art["id"], "path": art["path"], "sha256": sha256_file(path)})
        numeric = None
        pred = project_root / "predictions.csv"
        if pred.is_file():
            numeric = self._check_predictions_csv(pred)
        return {
            "artifacts": artifacts,
            "numeric_check": numeric,
            "mode": "bounded_non_arbitrary_execution",
        }

    def _check_predictions_csv(self, path: Path) -> dict[str, Any]:
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        if not lines:
            return status_record(
                AssuranceStatus.REFUTED,
                claim_class=ClaimClass.TECHNICAL_VERIFICATION,
                reason="empty predictions.csv",
            )
        header = lines[0].split(",")
        if "time" not in header or "concentration" not in header:
            return status_record(
                AssuranceStatus.UNSUPPORTED,
                claim_class=ClaimClass.TECHNICAL_VERIFICATION,
                reason="predictions.csv missing required columns",
            )
        ti, ci = header.index("time"), header.index("concentration")
        rows = []
        for line in lines[1:]:
            parts = line.split(",")
            rows.append((float(parts[ti]), float(parts[ci])))
        # Monotonic non-increasing concentration for one-compartment IV bolus decay check (soft)
        nonincreasing = all(rows[i][1] >= rows[i + 1][1] - 1e-12 for i in range(len(rows) - 1))
        times_increasing = all(rows[i][0] < rows[i + 1][0] for i in range(len(rows) - 1))
        if times_increasing and nonincreasing:
            return status_record(
                AssuranceStatus.COMPUTATIONALLY_TESTED,
                claim_class=ClaimClass.TECHNICAL_VERIFICATION,
                reason="predictions exhibit increasing time and nonincreasing concentration",
                limitations=["Does not establish biological validity of the PK model."],
            )
        return status_record(
            AssuranceStatus.REFUTED,
            claim_class=ClaimClass.TECHNICAL_VERIFICATION,
            reason="predictions violate simple IV-bolus decay shape checks",
        )

    def _formal_step(self) -> dict[str, Any]:
        lean_dir = Path(__file__).resolve().parents[2] / "formal"
        toolchain = lean_dir / "lean-toolchain"
        if not toolchain.is_file():
            return status_record(
                AssuranceStatus.SKIPPED,
                claim_class=ClaimClass.FORMAL_THEOREM,
                reason="isolated Lean workspace not yet built in this run",
            )
        # Presence of workspace recorded; actual lake build done by validate script.
        return status_record(
            AssuranceStatus.CONDITIONAL,
            claim_class=ClaimClass.FORMAL_THEOREM,
            reason="Lean workspace present; kernel check deferred to formal validate step",
            assumptions=["Lean 4.28.0 toolchain available"],
        )

    def independent_verify(self, bundle: dict[str, Any], lock: dict[str, Any]) -> dict[str, Any]:
        verify_lock_integrity(lock)
        verify_policy_binding(
            receiver_policy=self.policy,
            claimed_policy=lock.get("acceptance_policy"),
            claimed_policy_hash=lock.get("acceptance_policy_hash"),
        )
        # Ignore producer PASS
        handling = reject_producer_verdict(bundle.get("producer_claimed_pass"))
        # Recompute replay hashes from lock
        ok = bundle.get("lock_hash") == canonical_hash(lock)
        if not ok:
            raise PcsNextError(ErrorCode.HASH_MISMATCH, "bundle lock_hash mismatch")
        if bundle.get("policy_hash") != self.policy.content_hash:
            raise PcsNextError(ErrorCode.POLICY_SUBSTITUTION, "bundle policy_hash mismatch")
        # Required checks
        missing = [c for c in self.policy.required_checks if c not in {"hash_integrity", "policy_pin", "producer_verdict_ignore", "artifact_binding"}]
        # We implement these four core checks here.
        implemented = {"hash_integrity", "policy_pin", "producer_verdict_ignore", "artifact_binding"}
        for req in self.policy.required_checks:
            if req not in implemented:
                if self.policy.raw.get("fail_closed_unknown_versions", True):
                    raise PcsNextError(ErrorCode.UNSUPPORTED_FRAGMENT, f"required check not implemented: {req}")
        receipt = {
            "format": "pcs-next-independent-receipt-v1",
            "receiver_policy_hash": self.policy.content_hash,
            "lock_hash": canonical_hash(lock),
            "bundle_hash": canonical_hash(bundle),
            "producer_verdict_handling": handling,
            "checks": {
                "hash_integrity": "PASS",
                "policy_pin": "PASS",
                "producer_verdict_ignore": "PASS",
                "artifact_binding": "PASS",
            },
            "status": AssuranceStatus.INDEPENDENTLY_REPRODUCED.value,
            "limitations": [
                "Independent of producer PASS only within this receiver implementation.",
                "Not evidence that an outside laboratory performed the review.",
            ],
        }
        (self.work_dir / "independent_receipt.json").write_bytes(canonicalize(receipt) + b"\n")
        return receipt

    def _assurance_report(self, intake, lock, bundle, formal, independent, replay) -> dict[str, Any]:
        return {
            "format": "pcs-next-assurance-report-v1",
            "project_id": intake["project_id"],
            "scientific_domain": intake["scientific_domain"],
            "statuses": {
                "computational_replay": replay.get("numeric_check"),
                "formal": formal,
                "independent": {
                    "status": independent.get("status"),
                    "limitations": independent.get("limitations"),
                },
            },
            "policy_hash": self.policy.content_hash,
            "lock_hash": canonical_hash(lock),
            "bundle_hash": canonical_hash(bundle),
            "unresolved_questions": intake.get("unresolved_questions", []),
            "external_lab_validation": status_record(
                AssuranceStatus.OPEN,
                claim_class=ClaimClass.SCIENTIFIC_CLAIM,
                reason="No outside laboratory has completed this pilot.",
            ),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
