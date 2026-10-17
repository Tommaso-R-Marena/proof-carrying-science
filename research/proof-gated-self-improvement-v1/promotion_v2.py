"""Research-only content-addressed, compare-and-swap promotion controller.

The *only* semantic acceptance oracle is the passed file-based Lean authority.
POSIX permissions and flock help against accidental concurrent writers, not a
malicious process with equal filesystem credentials or the ability to modify
the authority checkout/executable. No production security claims.
"""
from __future__ import annotations

from dataclasses import dataclass
import fcntl
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat
from typing import Callable, Iterator
from contextlib import contextmanager

from proof_gate import POLICY_HASH, artifact_gate, wire_bytes, Model

BLOB_PREFIX = b"PCS-PGSI-ARTIFACT-v2\x00"
RECEIPT_PREFIX = b"PCS-PGSI-RECEIPT-v2\x00"
ZERO_HASH = "0" * 64
MAX_ARTIFACT = 80
VERSION = "pgsi-store-v2"

class StoreError(Exception):
    pass

class IntegrityFailure(StoreError):
    pass

class StaleHead(StoreError):
    pass

class ProposalRejected(StoreError):
    pass

@dataclass(frozen=True)
class Head:
    generation: int
    active_sha256: str
    policy_sha256: str
    last_receipt_sha256: str

    @classmethod
    def parse(cls, obj: object) -> "Head":
        if not isinstance(obj, dict) or set(obj) != {
            "generation", "active_sha256", "policy_sha256", "last_receipt_sha256"
        }:
            raise IntegrityFailure("invalid head schema")
        if type(obj["generation"]) is not int or obj["generation"] < 0:
            raise IntegrityFailure("invalid generation")
        for field in ("active_sha256", "policy_sha256", "last_receipt_sha256"):
            require_hash(obj[field])
        return cls(**obj)

def require_hash(value: object) -> None:
    if not isinstance(value, str) or len(value) != 64 or any(
        c not in "0123456789abcdef" for c in value
    ):
        raise IntegrityFailure("invalid hexadecimal digest")

def blob_hash(raw: bytes) -> str:
    return hashlib.sha256(BLOB_PREFIX + raw).hexdigest()

def receipt_hash(raw: bytes) -> str:
    return hashlib.sha256(RECEIPT_PREFIX + raw).hexdigest()

def canonical(obj: object) -> bytes:
    return json.dumps(obj, separators=(",", ":"), sort_keys=True, ensure_ascii=True,
                      allow_nan=False).encode("ascii")

def no_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    out = {}
    for key, value in pairs:
        if key in out:
            raise IntegrityFailure("duplicate JSON property")
        out[key] = value
    return out

def strict_json(raw: bytes) -> object:
    try:
        obj = json.loads(raw.decode("ascii"), object_pairs_hook=no_duplicate_keys)
        if canonical(obj) != raw:
            raise IntegrityFailure("noncanonical JSON")
        return obj
    except (UnicodeError, ValueError, TypeError, OverflowError) as e:
        raise IntegrityFailure("invalid JSON encoding") from e

def _regular(path: Path) -> os.stat_result:
    try:
        info = path.lstat()
    except OSError as e:
        raise IntegrityFailure("missing protected object") from e
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise IntegrityFailure("symlink, hardlink, or special file forbidden")
    return info

def _read_regular(path: Path, limit: int) -> bytes:
    before = _regular(path)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        with os.fdopen(fd, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1 or (
                opened.st_ino, opened.st_dev
            ) != (before.st_ino, before.st_dev):
                raise IntegrityFailure("file replaced while opening")
            data = stream.read(limit + 1)
            if len(data) > limit:
                raise IntegrityFailure("file too large")
            after = os.fstat(stream.fileno())
            if (after.st_size, after.st_mtime_ns, after.st_ctime_ns) != (
                opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns
            ):
                raise IntegrityFailure("file changed while reading")
            return data
    except OSError as e:
        raise IntegrityFailure("protected file read failed") from e

def _write_once(path: Path, raw: bytes) -> None:
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as e:
        raise IntegrityFailure("write-once object failure") from e
    _fsync_dir(path.parent)

def _fsync_dir(directory: Path) -> None:
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)

def _replace_head(path: Path, raw: bytes) -> None:
    temp = path.parent / (".head-" + secrets.token_hex(16))
    _write_once(temp, raw)
    try:
        os.replace(temp, path)
        _fsync_dir(path.parent)
    finally:
        if temp.exists():
            temp.unlink()

class ResearchPromotionStore:
    def __init__(self, root: Path, formal_dir: Path):
        self.root = Path(root).absolute()
        self.formal_dir = Path(formal_dir).absolute()

    def _dirs(self) -> None:
        if self.root.is_symlink() or not self.root.is_dir():
            raise IntegrityFailure("missing or linked store")
        if self.root.resolve() != self.root:
            raise IntegrityFailure("store path traverses a symlink")
        for name in ("blobs", "receipts"):
            path = self.root / name
            if path.is_symlink() or not path.is_dir():
                raise IntegrityFailure("missing or linked store directory")

    @contextmanager
    def _locked(self) -> Iterator[None]:
        self._dirs()
        lockpath = self.root / ".lock"
        _regular(lockpath)
        fd = os.open(lockpath, os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            info = os.fstat(fd)
            if info.st_nlink != 1 or not stat.S_ISREG(info.st_mode):
                raise IntegrityFailure("lock swapped")
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def _blob_path(self, digest: str) -> Path:
        require_hash(digest)
        return self.root / "blobs" / (digest + ".pgsi")

    def _blob(self, digest: str) -> bytes:
        raw = _read_regular(self._blob_path(digest), MAX_ARTIFACT)
        if blob_hash(raw) != digest:
            raise IntegrityFailure("content-addressed blob mismatch")
        return raw

    def _write_blob(self, raw: bytes) -> str:
        if type(raw) is not bytes or len(raw) > MAX_ARTIFACT or not raw:
            raise IntegrityFailure("invalid candidate byte count")
        digest = blob_hash(raw)
        target = self._blob_path(digest)
        if not target.exists() and not target.is_symlink():
            _write_once(target, raw)
        if self._blob(digest) != raw:
            raise IntegrityFailure("blob collision or substitution")
        return digest

    def _head(self) -> Head:
        head = Head.parse(strict_json(_read_regular(self.root / "HEAD.json", 2048)))
        if head.policy_sha256 != POLICY_HASH:
            raise IntegrityFailure("policy version was changed")
        self._blob(head.active_sha256)
        return head

    @classmethod
    def initialize(cls, root: Path, formal_dir: Path, initial: Model) -> "ResearchPromotionStore":
        root = Path(root).absolute()
        # Exclusive creation: never silently open/reinitialize an existing root.
        root.mkdir(mode=0o700, parents=False, exist_ok=False)
        os.chmod(root, 0o700)
        (root / "blobs").mkdir(mode=0o700)
        (root / "receipts").mkdir(mode=0o700)
        _write_once(root / ".lock", b"")
        store = cls(root, formal_dir)
        with store._locked():
            digest = store._write_blob(wire_bytes(initial))
            genesis = {"version": VERSION, "genesis_sha256": digest,
                       "policy_sha256": POLICY_HASH}
            _write_once(root / "GENESIS.json", canonical(genesis))
            head = Head(0, digest, POLICY_HASH, ZERO_HASH)
            _write_once(root / "HEAD.json", canonical(head.__dict__))
        return store

    def snapshot(self) -> Head:
        with self._locked():
            return self._head()

    def read_active(self) -> tuple[Head, bytes]:
        with self._locked():
            head = self._head()
            return head, self._blob(head.active_sha256)

    def promote(self, candidate_bytes: bytes, expected: Head,
                verifier: Callable[[Path, Path, Path], bool] = artifact_gate) -> Head:
        """Compare-and-swap. A *research* wrapper, not tamperproof storage.

        No accepted modification may be committed unless the file-based Lean
        oracle returns positive on the store's content-addressed old/new blobs.
        Re-reads after verification protect against accidental mutations before
        the pointer swap, NOT arbitrary privileged races or host compromise.
        """
        with self._locked():
            old = self._head()
            if old != expected:
                raise StaleHead("incumbent head no longer matches")
            original = self._blob(old.active_sha256)
            candidate_digest = self._write_blob(candidate_bytes)
            candidate_path = self._blob_path(candidate_digest)
            incumbent_path = self._blob_path(old.active_sha256)
            if not verifier(incumbent_path, candidate_path, self.formal_dir):
                raise ProposalRejected("Lean gate did not authorize candidate")
            if self._blob(old.active_sha256) != original or (
                self._blob(candidate_digest) != candidate_bytes
            ):
                raise IntegrityFailure("verified artifacts changed before commit")
            if self._head() != old:
                raise StaleHead("incumbent changed during verification")
            receipt = {
                "version": VERSION,
                "generation": old.generation + 1,
                "old_sha256": old.active_sha256,
                "new_sha256": candidate_digest,
                "previous_receipt_sha256": old.last_receipt_sha256,
                "policy_sha256": POLICY_HASH,
                "verification": "Lean file-authority accepted; unsigned research receipt",
            }
            receipt_raw = canonical(receipt)
            digest = receipt_hash(receipt_raw)
            receipt_path = self.root / "receipts" / f"{old.generation + 1:08d}.json"
            _write_once(receipt_path, receipt_raw)
            next_head = Head(old.generation + 1, candidate_digest, POLICY_HASH, digest)
            _replace_head(self.root / "HEAD.json", canonical(next_head.__dict__))
            return next_head

    def audit(self) -> Head:
        with self._locked():
            head = self._head()
            genesis = strict_json(_read_regular(self.root / "GENESIS.json", 2048))
            if not isinstance(genesis, dict) or set(genesis) != {
                "version", "genesis_sha256", "policy_sha256"
            } or genesis["version"] != VERSION or genesis["policy_sha256"] != POLICY_HASH:
                raise IntegrityFailure("invalid genesis")
            digest = genesis["genesis_sha256"]
            require_hash(digest)
            self._blob(digest)
            expected_files = {f"{gen:08d}.json" for gen in range(1, head.generation + 1)}
            observed_files = {p.name for p in (self.root / "receipts").iterdir()}
            if observed_files != expected_files:
                raise IntegrityFailure("missing or orphaned receipt: possible rollback or crash")
            prev = ZERO_HASH
            for gen in range(1, head.generation + 1):
                receipt_path = self.root / "receipts" / f"{gen:08d}.json"
                raw = _read_regular(receipt_path, 2048)
                event = strict_json(raw)
                if not isinstance(event, dict) or set(event) != {
                    "version", "generation", "old_sha256", "new_sha256",
                    "previous_receipt_sha256", "policy_sha256", "verification",
                } or event != {
                    "version": VERSION, "generation": gen,
                    "old_sha256": digest,
                    "new_sha256": event.get("new_sha256"),
                    "previous_receipt_sha256": prev, "policy_sha256": POLICY_HASH,
                    "verification": "Lean file-authority accepted; unsigned research receipt",
                }:
                    raise IntegrityFailure("invalid or broken receipt chain")
                digest = event["new_sha256"]
                require_hash(digest)
                self._blob(digest)
                prev = receipt_hash(raw)
            if head.active_sha256 != digest or head.last_receipt_sha256 != prev:
                raise IntegrityFailure("head does not match receipt chain")
            return head
