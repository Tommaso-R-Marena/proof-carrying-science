"""External monotonic checkpoint for the experimental PGSC6 state controller.

A separate, independently protected checkpoint directory can detect an
otherwise fully consistent rollback of the MODEL STORE (HEAD, objects, receipts)
to a previously valid history.

Important threat model:
* Trusted process exclusively owns checkpoint directory and runs this wrapper.
* Proposer can replace/replay the model store while this process is stopped,
  but cannot modify the checkpoint directory, trusted Python, or Lean executable.
* If the proposal actor has the same credentials as the trusted process, or
  can replace both store AND checkpoint, rollback resistance is NOT provided.
* The file checkpoint is NOT a TEE, HSM, signed transparency log, trusted
  clock, or hardware monotonic counter. OS ACLs remain the external premise.
* File writes use POSIX fsync/rename and an advisory lock. Crash after
  model commit but before checkpoint update halts the service; safe recovery
  requires external review. No automatic forward/rollback recovery.
* Any use of underlying PinnedPGSC6Store without this wrapper bypasses the
  anchor: the trusted service must expose ONLY this API.

No formal theorem covers this Python/OS implementation. No production use.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from contextlib import contextmanager
import fcntl
import hashlib
import os
from typing import Iterator

from pgsc6_pinned_store import (
    PinnedPGSC6Store, PinnedSnapshot, POLICY_DIGEST, IntegrityFailure,
    StaleHead, _regular_dir, _lockfile,
)
from promotion_v2 import (
    Head, _read_regular, _write_once, _replace_head, canonical, strict_json,
)

ANCHOR_VERSION = "pgsc6-independent-checkpoint-v1"
MAX_ANCHOR_BYTES = 4096


def _path_is_inside(path: Path, root: Path) -> bool:
    return path == root or path.is_relative_to(root)


@dataclass(frozen=True)
class ExternalCheckpoint:
    version: str
    store_path: str
    generation: int
    active_sha256: str
    policy_sha256: str
    last_receipt_sha256: str

    @classmethod
    def for_head(cls, store_path: Path, head: Head) -> "ExternalCheckpoint":
        return cls(
            ANCHOR_VERSION, str(store_path), head.generation, head.active_sha256,
            head.policy_sha256, head.last_receipt_sha256,
        )

    @classmethod
    def parse(cls, raw: bytes) -> "ExternalCheckpoint":
        obj = strict_json(raw)
        if not isinstance(obj, dict) or set(obj) != set(cls.__dataclass_fields__):
            raise IntegrityFailure("invalid independent checkpoint schema")
        if obj.get("version") != ANCHOR_VERSION or type(obj.get("store_path")) is not str:
            raise IntegrityFailure("invalid independent checkpoint identity")
        head = Head.parse({
            "generation": obj["generation"],
            "active_sha256": obj["active_sha256"],
            "policy_sha256": obj["policy_sha256"],
            "last_receipt_sha256": obj["last_receipt_sha256"],
        })
        return cls.for_head(Path(obj["store_path"]), head)

    def head(self) -> Head:
        return Head(
            self.generation, self.active_sha256,
            self.policy_sha256, self.last_receipt_sha256,
        )


class ExternallyAnchoredPGSC6:
    """Require separately guarded checkpoint agreement for serving and update.

    WARNING: protects against model-store-only rollback, NOT replacing this
    source code or the external checkpoint. The kernel-proved policy predicate
    is still verified by the actual Lean V6 checker in the base controller.
    """

    def __init__(self, store_root: Path, anchor_root: Path):
        self.store = PinnedPGSC6Store(store_root)
        self.anchor_root = Path(os.path.abspath(anchor_root))
        self._assert_separate()

    def _assert_separate(self) -> None:
        store_root = self.store.root
        anchor_root = self.anchor_root
        if _path_is_inside(store_root, anchor_root) or _path_is_inside(anchor_root, store_root):
            raise IntegrityFailure("independent anchor cannot share model-store subtree")
        if store_root == anchor_root:
            raise IntegrityFailure("anchor and model-store paths must differ")

    @classmethod
    def initialize(cls, store_root: Path, anchor_root: Path) -> "ExternallyAnchoredPGSC6":
        """Create a fresh store and separate checkpoint, both exclusively.

        If process crashes after creating a store but before writing checkpoint,
        both directories remain and this method refuses to reinitialize.
        """
        store_root = Path(os.path.abspath(store_root))
        anchor_root = Path(os.path.abspath(anchor_root))
        if _path_is_inside(store_root, anchor_root) or _path_is_inside(anchor_root, store_root):
            raise IntegrityFailure("anchor must be outside store")
        # Avoid silently overwriting any existing authority checkpoint.
        if anchor_root.exists() or anchor_root.is_symlink():
            raise IntegrityFailure("anchor already exists")
        store = PinnedPGSC6Store.initialize(store_root)
        anchor_root.mkdir(mode=0o700, parents=False, exist_ok=False)
        os.chmod(anchor_root, 0o700)
        _write_once(anchor_root / ".lock", b"")
        initial = ExternalCheckpoint.for_head(store.root, store.audit())
        _write_once(anchor_root / "CHECKPOINT.json", canonical(initial.__dict__))
        return cls(store_root, anchor_root)

    @contextmanager
    def _anchor_lock(self) -> Iterator[None]:
        self._assert_separate()
        _regular_dir(self.anchor_root)
        fd = _lockfile(self.anchor_root / ".lock")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def _checkpoint_locked(self) -> ExternalCheckpoint:
        anchor = ExternalCheckpoint.parse(_read_regular(
            self.anchor_root / "CHECKPOINT.json", MAX_ANCHOR_BYTES
        ))
        if anchor.store_path != str(self.store.root):
            raise IntegrityFailure("checkpoint belongs to a different model store")
        if anchor.policy_sha256 != POLICY_DIGEST:
            raise IntegrityFailure("independent checkpoint policy mismatch")
        return anchor

    def _verified_head_locked(self) -> Head:
        checkpoint = self._checkpoint_locked()
        current = self.store.audit()
        if checkpoint.head() != current:
            raise IntegrityFailure(
                "independent checkpoint disagrees with model history: rollback, "
                "unexpected mutation, or crash; manual review required"
            )
        return current

    def audit(self) -> Head:
        with self._anchor_lock():
            return self._verified_head_locked()

    def snapshot(self, expected: Head | None = None) -> PinnedSnapshot:
        with self._anchor_lock():
            current = self._verified_head_locked()
            if expected is not None and expected != current:
                raise StaleHead("pinned external checkpoint differs from expectation")
            snap = self.store.snapshot(expected=current)
            if snap.head != self._checkpoint_locked().head():
                raise IntegrityFailure("checkpoint changed during inference snapshot")
            return snap

    def promote(self, certificate_bytes: bytes, expected: Head) -> Head:
        """Only accepts certificate bytes and expected audited Head.

        All checks/commits happen under the anchor's exclusive cooperative
        lock. An external attacker with anchor write access can defeat it.
        """
        with self._anchor_lock():
            old = self._verified_head_locked()
            if expected != old:
                raise StaleHead("external expected head is stale")
            new = self.store.promote(certificate_bytes, old)
            # If this atomic replacement fails after model promotion, the
            # checkpoint remains OLD and every subsequent operation FAILS.
            checkpoint = ExternalCheckpoint.for_head(self.store.root, new)
            _replace_head(
                self.anchor_root / "CHECKPOINT.json", canonical(checkpoint.__dict__)
            )
            if self._verified_head_locked() != new:
                raise IntegrityFailure("post-commit external checkpoint mismatch")
            return new
