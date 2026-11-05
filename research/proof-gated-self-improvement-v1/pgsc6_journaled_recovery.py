"""Research PGSC6 two-store crash recovery with authority-owned intent log.

The external checkpoint and a durable pending authorization intent live in a
separately governed directory, not in the proposer-controlled model store.

Recovery of a one-generation committed-but-unanchored transaction requires:
  * exact pending intent that pre-dates the model-store transition,
  * exact old checkpoint identity and expected generation,
  * fully self-consistent receipt/model store with exactly one new generation,
  * exact candidate/certificate byte identities and receipt linkage,
  * re-execution of the ACTUAL V6 Lean check on the old artifact/certificate.

A pending intent freezes ordinary audit/serve/promote until explicit recovery.
A crash before any store transition can abandon the intent if the entire
model-store history remains identical to the protected old checkpoint.
A crash after checkpoint publication but before intent cleanup rechecks the
candidate and then removes the intent.

This is research-only. The authority-owned intent is NOT a signature, HSM,
trusted disk, POSIX guarantee or protection against same-UID attackers.
Dual-disk atomicity does not exist: crash/recovery requires an explicitly
trusted operator and a protected external checkpoint. A rollback to the
pre-commit state in the interval between store and anchor write is not
distinguishable from a failed transaction without another monotonic source.
"""
from __future__ import annotations

from pathlib import Path
import hashlib

from pgsc6_external_anchor import (
    ExternallyAnchoredPGSC6, ExternalCheckpoint, ANCHOR_VERSION
)
from pgsc6_pinned_store import (
    POLICY, POLICY_DIGEST, IntegrityFailure, StaleHead,
    RESEARCH, PinnedSnapshot, MAX_CERT_BYTES,
)
from pgsc6_reference import decode_certificate, reference_certificate_passes
from promotion_v2 import (
    Head, _read_regular, _write_once, _replace_head, _fsync_dir,
    canonical, strict_json, require_hash,
)

PENDING_VERSION = "pgsc6-checkpoint-intent-v1"
MAX_PENDING_BYTES = 2 * MAX_CERT_BYTES + 8192


def _sha(raw: bytes) -> str:
    return hashlib.sha256(b"PGSC6-PENDING-v1\x00" + raw).hexdigest()


class JournaledPGSC6(ExternallyAnchoredPGSC6):
    """Two-phase externally documented promotion with explicit recovery."""

    @property
    def pending_path(self) -> Path:
        return self.anchor_root / "PENDING.json"

    def _has_pending(self) -> bool:
        return self.pending_path.exists() or self.pending_path.is_symlink()

    def _require_clean_locked(self) -> Head:
        if self._has_pending():
            raise IntegrityFailure("unresolved authorization intent: recovery required")
        return super()._verified_head_locked()

    def audit(self) -> Head:
        with self._anchor_lock():
            return self._require_clean_locked()

    def snapshot(self, expected: Head | None = None) -> PinnedSnapshot:
        with self._anchor_lock():
            head = self._require_clean_locked()
            if expected is not None and expected != head:
                raise StaleHead("outdated protected checkpoint")
            snap = self.store.snapshot(expected=head)
            if snap.head != self._checkpoint_locked().head():
                raise IntegrityFailure("protected anchor changed during serve")
            return snap

    def _phase_hook(self, phase: str) -> None:
        """Unit-test fault-injection seam. Not a caller-supplied authority."""
        return None

    def _make_intent(self, old: Head, certificate: bytes) -> dict:
        from pgsc6_pinned_store import PinnedPGSC6Store
        if type(certificate) is not bytes or not certificate or (
            len(certificate) > MAX_CERT_BYTES
        ):
            raise IntegrityFailure("certificate has invalid type or size")
        if not reference_certificate_passes(
            certificate, POLICY, old.generation, self.store._model(old.active_sha256)
        ):
            raise IntegrityFailure("fixed-policy precheck refuses proposed certificate")
        parsed = decode_certificate(certificate)
        candidate = parsed.candidate
        record = {
            "version": PENDING_VERSION,
            "store_path": str(self.store.root),
            "policy_sha256": POLICY_DIGEST,
            "before": old.__dict__,
            "certificate_hex": certificate.hex(),
            "certificate_sha256": self.store._certificate_digest(certificate),
            "candidate_sha256": self.store._artifact_digest(candidate),
        }
        record["intent_sha256"] = _sha(canonical(record))
        return record

    def _read_intent(self) -> tuple[Head, bytes, str, str]:
        obj = strict_json(_read_regular(self.pending_path, MAX_PENDING_BYTES))
        needed = {
            "version", "store_path", "policy_sha256", "before",
            "certificate_hex", "certificate_sha256", "candidate_sha256",
            "intent_sha256",
        }
        if type(obj) is not dict or set(obj) != needed:
            raise IntegrityFailure("invalid pending authorization record")
        identity = {k: v for k, v in obj.items() if k != "intent_sha256"}
        require_hash(obj["intent_sha256"])
        if _sha(canonical(identity)) != obj["intent_sha256"]:
            raise IntegrityFailure("pending authorization digest mismatch")
        if (obj["version"] != PENDING_VERSION or
            obj["store_path"] != str(self.store.root) or
            obj["policy_sha256"] != POLICY_DIGEST):
            raise IntegrityFailure("pending authorization policy/store mismatch")
        old = Head.parse(obj["before"])
        if old.policy_sha256 != POLICY_DIGEST:
            raise IntegrityFailure("intent had unapproved policy")
        encoded = obj["certificate_hex"]
        if type(encoded) is not str or len(encoded) > MAX_CERT_BYTES * 2:
            raise IntegrityFailure("invalid pending certificate envelope")
        try:
            cert = bytes.fromhex(encoded)
        except ValueError as exc:
            raise IntegrityFailure("invalid pending hex certificate") from exc
        if not cert or cert.hex() != encoded:
            raise IntegrityFailure("noncanonical pending certificate hex")
        if self.store._certificate_digest(cert) != obj["certificate_sha256"]:
            raise IntegrityFailure("pending certificate digest mismatch")
        require_hash(obj["candidate_sha256"])
        parsed = decode_certificate(cert)
        if self.store._artifact_digest(parsed.candidate) != obj["candidate_sha256"]:
            raise IntegrityFailure("pending candidate mismatch")
        if not reference_certificate_passes(
            cert, POLICY, old.generation, self.store._model(old.active_sha256)
        ):
            raise IntegrityFailure("pending proposal fails independent fixed policy")
        return old, cert, obj["certificate_sha256"], obj["candidate_sha256"]

    def _one_step_matches(self, old: Head, cert: bytes, cert_digest: str,
                          candidate_digest: str, new: Head) -> None:
        if (new.generation != old.generation + 1 or
            new.policy_sha256 != old.policy_sha256 or
            new.active_sha256 != candidate_digest):
            raise IntegrityFailure("journal recovery requires exactly one committed step")
        raw = _read_regular(
            self.store.root / "receipts" / f"{new.generation:08d}.json", 4096
        )
        record = strict_json(raw)
        if (
            not isinstance(record, dict)
            or record.get("generation") != new.generation
            or record.get("previous_model_sha256") != old.active_sha256
            or record.get("candidate_model_sha256") != candidate_digest
            or record.get("certificate_sha256") != cert_digest
            or record.get("previous_receipt_sha256") != old.last_receipt_sha256
            or record.get("policy_sha256") != POLICY_DIGEST
            or new.last_receipt_sha256 != self.store._receipt_digest(raw)
        ):
            raise IntegrityFailure("committed receipt is not the pending authorization")
        if self.store._model(candidate_digest) != decode_certificate(cert).candidate:
            raise IntegrityFailure("committed candidate bytes are not journaled")
        if self.store._cert(cert_digest) != cert:
            raise IntegrityFailure("committed certificate bytes are not journaled")
        if not self.store._real_lean_authorizes(
            old.generation, self.store._model(old.active_sha256), cert
        ):
            raise IntegrityFailure("actual Lean V6 did not reauthorize journal recovery")

    def promote(self, certificate_bytes: bytes, expected: Head) -> Head:
        with self._anchor_lock():
            old = self._require_clean_locked()
            if type(expected) is not Head or expected != old:
                raise StaleHead("expected audited head does not match trusted checkpoint")
            intent = self._make_intent(old, certificate_bytes)
            _write_once(self.pending_path, canonical(intent))
            self._phase_hook("intent_durable")
            new = self.store.promote(certificate_bytes, old)
            self._phase_hook("store_committed")
            checkpoint = ExternalCheckpoint.for_head(self.store.root, new)
            _replace_head(
                self.anchor_root / "CHECKPOINT.json", canonical(checkpoint.__dict__)
            )
            self._phase_hook("anchor_committed")
            self.pending_path.unlink()
            _fsync_dir(self.anchor_root)
            if self._require_clean_locked() != new:
                raise IntegrityFailure("journalled commit and checkpoint diverged")
            return new

    def recover(self) -> str:
        """Explicitly reconcile only a protected intent and exact 0/1 step.

        NEVER infer commit evidence from unprotected receipts alone. No
        arbitrary generation skipping or recovery from a substituted intent.
        """
        with self._anchor_lock():
            if not self._has_pending():
                self._require_clean_locked()
                return "clean"
            old, cert, cert_digest, candidate_digest = self._read_intent()
            anchor = self._checkpoint_locked().head()
            current = self.store.audit()
            if current == old and anchor == old:
                # Crash before committing model state. The protected intent
                # can be discarded because old complete history still agrees.
                self.pending_path.unlink()
                _fsync_dir(self.anchor_root)
                return "aborted_before_commit"
            self._one_step_matches(old, cert, cert_digest, candidate_digest, current)
            if anchor == old:
                _replace_head(
                    self.anchor_root / "CHECKPOINT.json",
                    canonical(ExternalCheckpoint.for_head(self.store.root, current).__dict__)
                )
                result = "completed_one_committed_step"
            elif anchor == current:
                result = "cleaned_committed_intent"
            else:
                raise IntegrityFailure("checkpoint is neither old nor proved successor")
            self.pending_path.unlink()
            _fsync_dir(self.anchor_root)
            if self._require_clean_locked() != current:
                raise IntegrityFailure("recovered checkpoint not consistent")
            return result
