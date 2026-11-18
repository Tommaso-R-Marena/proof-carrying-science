"""Content-addressed compare-and-swap promotion store for PGRA rulebooks.

Inspired by research/proof-gated-self-improvement-v1/promotion_v2.py but simpler
and self-contained: the Python gate is the acceptance oracle for this research
path (no Lean file oracle required). Fail closed on tampering.
``automatic_deployment`` is always False.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat
from typing import Iterator

try:
    from .gate import POLICY_HASH, accept, canonical, digest
except ImportError:  # flat sys.path research execution
    from gate import POLICY_HASH, accept, canonical, digest

BLOB_PREFIX = b"PCS-PGRA-RULES-v1\x00"
RECEIPT_PREFIX = b"PCS-PGRA-RECEIPT-v1\x00"
ZERO_HASH = "0" * 64
VERSION = "pgra-store-v1"
MAX_BLOB = 4096
AUTOMATIC_DEPLOYMENT = False


class StoreError(Exception):
    pass


class IntegrityFailure(StoreError):
    pass


class StaleHead(StoreError):
    pass


class ProposalRejected(StoreError):
    pass


def require_hash(value: object) -> None:
    if not isinstance(value, str) or len(value) != 64 or any(
        c not in "0123456789abcdef" for c in value
    ):
        raise IntegrityFailure("invalid hexadecimal digest")


def blob_hash(raw: bytes) -> str:
    return hashlib.sha256(BLOB_PREFIX + raw).hexdigest()


def receipt_hash(raw: bytes) -> str:
    return hashlib.sha256(RECEIPT_PREFIX + raw).hexdigest()


def no_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    out: dict = {}
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


def rules_bytes(rules: frozenset[str] | set[str] | list[str] | tuple[str, ...]) -> bytes:
    payload = {
        "format": "pcs-pgra-rules-v1",
        "rules": sorted(rules),
        "automatic_deployment": False,
        "pcs_scientific_authority": False,
    }
    return canonical(payload)


def parse_rules(raw: bytes) -> frozenset[str]:
    obj = strict_json(raw)
    if not isinstance(obj, dict) or obj.get("format") != "pcs-pgra-rules-v1":
        raise IntegrityFailure("invalid rules blob format")
    if obj.get("automatic_deployment") is not False:
        raise IntegrityFailure("automatic_deployment must be false")
    if obj.get("pcs_scientific_authority") is not False:
        raise IntegrityFailure("pcs_scientific_authority must be false")
    rules = obj.get("rules")
    if not isinstance(rules, list) or any(type(r) is not str for r in rules):
        raise IntegrityFailure("invalid rules list")
    if sorted(rules) != rules or len(set(rules)) != len(rules):
        raise IntegrityFailure("rules must be sorted unique strings")
    return frozenset(rules)


@dataclass(frozen=True)
class Head:
    generation: int
    active_sha256: str
    policy_sha256: str
    last_receipt_sha256: str

    @classmethod
    def parse(cls, obj: object) -> "Head":
        if not isinstance(obj, dict) or set(obj) != {
            "generation",
            "active_sha256",
            "policy_sha256",
            "last_receipt_sha256",
        }:
            raise IntegrityFailure("invalid head schema")
        if type(obj["generation"]) is not int or obj["generation"] < 0:
            raise IntegrityFailure("invalid generation")
        for field in ("active_sha256", "policy_sha256", "last_receipt_sha256"):
            require_hash(obj[field])
        return cls(**obj)


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
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_nlink != 1
                or (opened.st_ino, opened.st_dev) != (before.st_ino, before.st_dev)
            ):
                raise IntegrityFailure("file replaced while opening")
            data = stream.read(limit + 1)
            if len(data) > limit:
                raise IntegrityFailure("file too large")
            after = os.fstat(stream.fileno())
            if (after.st_size, after.st_mtime_ns, after.st_ctime_ns) != (
                opened.st_size,
                opened.st_mtime_ns,
                opened.st_ctime_ns,
            ):
                raise IntegrityFailure("file changed while reading")
            return data
    except OSError as e:
        raise IntegrityFailure("protected file read failed") from e


def _write_once(path: Path, raw: bytes) -> None:
    try:
        fd = os.open(
            path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
        )
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
            temp.unlink(missing_ok=True)


class FormalizationPromotionStore:
    """Research-only CAS store for rulebook generations."""

    automatic_deployment = False

    def __init__(self, root: Path):
        self.root = Path(root).absolute()

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
        prior = _regular(lockpath)
        fd = os.open(lockpath, os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            info = os.fstat(fd)
            if (
                info.st_nlink != 1
                or not stat.S_ISREG(info.st_mode)
                or (info.st_ino, info.st_dev) != (prior.st_ino, prior.st_dev)
            ):
                raise IntegrityFailure("lock swapped")
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def _blob_path(self, digest_hex: str) -> Path:
        require_hash(digest_hex)
        return self.root / "blobs" / (digest_hex + ".pgra")

    def _blob(self, digest_hex: str) -> bytes:
        raw = _read_regular(self._blob_path(digest_hex), MAX_BLOB)
        if blob_hash(raw) != digest_hex:
            raise IntegrityFailure("content-addressed blob mismatch")
        return raw

    def _write_blob(self, raw: bytes) -> str:
        if type(raw) is not bytes or len(raw) > MAX_BLOB or not raw:
            raise IntegrityFailure("invalid candidate byte count")
        digest_hex = blob_hash(raw)
        target = self._blob_path(digest_hex)
        if not target.exists() and not target.is_symlink():
            _write_once(target, raw)
        if self._blob(digest_hex) != raw:
            raise IntegrityFailure("blob collision or substitution")
        return digest_hex

    def _head(self) -> Head:
        head = Head.parse(strict_json(_read_regular(self.root / "HEAD.json", 2048)))
        if head.policy_sha256 != POLICY_HASH:
            raise IntegrityFailure("policy version was changed")
        self._blob(head.active_sha256)
        return head

    @classmethod
    def initialize(
        cls, root: Path, initial_rules: frozenset[str] | None = None
    ) -> "FormalizationPromotionStore":
        root = Path(root).absolute()
        root.mkdir(mode=0o700, parents=False, exist_ok=False)
        os.chmod(root, 0o700)
        (root / "blobs").mkdir(mode=0o700)
        (root / "receipts").mkdir(mode=0o700)
        _write_once(root / ".lock", b"")
        store = cls(root)
        rules = frozenset(initial_rules or ())
        with store._locked():
            digest_hex = store._write_blob(rules_bytes(rules))
            genesis = {
                "version": VERSION,
                "genesis_sha256": digest_hex,
                "policy_sha256": POLICY_HASH,
                "automatic_deployment": False,
                "pcs_scientific_authority": False,
            }
            _write_once(root / "GENESIS.json", canonical(genesis))
            head = Head(0, digest_hex, POLICY_HASH, ZERO_HASH)
            _write_once(root / "HEAD.json", canonical(head.__dict__))
        return store

    def snapshot(self) -> Head:
        with self._locked():
            return self._head()

    def read_active(self) -> tuple[Head, frozenset[str]]:
        with self._locked():
            head = self._head()
            return head, parse_rules(self._blob(head.active_sha256))

    def promote(
        self,
        new_rules: frozenset[str],
        expected: Head,
        corpus: list | tuple,
    ) -> Head:
        """CAS promote if gate accepts. Never sets automatic_deployment."""
        with self._locked():
            old = self._audit_locked()
            if old != expected:
                raise StaleHead("incumbent head no longer matches")
            old_rules = parse_rules(self._blob(old.active_sha256))
            decision = accept(old_rules, frozenset(new_rules), corpus)
            if not decision.accepted:
                raise ProposalRejected(decision.reason)
            candidate_raw = rules_bytes(new_rules)
            candidate_digest = self._write_blob(candidate_raw)
            if self._audit_locked() != old:
                raise StaleHead("incumbent changed during verification")
            receipt = {
                "version": VERSION,
                "generation": old.generation + 1,
                "old_sha256": old.active_sha256,
                "new_sha256": candidate_digest,
                "previous_receipt_sha256": old.last_receipt_sha256,
                "policy_sha256": POLICY_HASH,
                "decision_reason": decision.reason,
                "decision_digest": digest(decision.as_dict()),
                "automatic_deployment": False,
                "pcs_scientific_authority": False,
                "verification": "PGRA Python reference gate accepted; unsigned research receipt",
            }
            receipt_raw = canonical(receipt)
            rdigest = receipt_hash(receipt_raw)
            receipt_path = self.root / "receipts" / f"{old.generation + 1:08d}.json"
            _write_once(receipt_path, receipt_raw)
            next_head = Head(
                old.generation + 1, candidate_digest, POLICY_HASH, rdigest
            )
            _replace_head(self.root / "HEAD.json", canonical(next_head.__dict__))
            return next_head

    def audit(self) -> Head:
        with self._locked():
            return self._audit_locked()

    def _audit_locked(self) -> Head:
        head = self._head()
        genesis = strict_json(_read_regular(self.root / "GENESIS.json", 2048))
        if (
            not isinstance(genesis, dict)
            or genesis.get("version") != VERSION
            or genesis.get("policy_sha256") != POLICY_HASH
            or genesis.get("automatic_deployment") is not False
            or genesis.get("pcs_scientific_authority") is not False
        ):
            raise IntegrityFailure("invalid genesis")
        require_hash(genesis["genesis_sha256"])
        chain_digest = genesis["genesis_sha256"]
        self._blob(chain_digest)
        expected_files = {f"{gen:08d}.json" for gen in range(1, head.generation + 1)}
        observed_files = {p.name for p in (self.root / "receipts").iterdir()}
        if observed_files != expected_files:
            raise IntegrityFailure("missing or orphaned receipt")
        prev = ZERO_HASH
        for gen in range(1, head.generation + 1):
            receipt_path = self.root / "receipts" / f"{gen:08d}.json"
            raw = _read_regular(receipt_path, 8192)
            event = strict_json(raw)
            if (
                not isinstance(event, dict)
                or event.get("version") != VERSION
                or event.get("generation") != gen
                or event.get("old_sha256") != chain_digest
                or event.get("previous_receipt_sha256") != prev
                or event.get("policy_sha256") != POLICY_HASH
                or event.get("automatic_deployment") is not False
                or event.get("pcs_scientific_authority") is not False
            ):
                raise IntegrityFailure("invalid or broken receipt chain")
            chain_digest = event["new_sha256"]
            require_hash(chain_digest)
            self._blob(chain_digest)
            prev = receipt_hash(raw)
        if head.active_sha256 != chain_digest or head.last_receipt_sha256 != prev:
            raise IntegrityFailure("head does not match receipt chain")
        return head


# Alias for discoverability
PromotionStore = FormalizationPromotionStore

__all__ = [
    "AUTOMATIC_DEPLOYMENT",
    "FormalizationPromotionStore",
    "PromotionStore",
    "Head",
    "IntegrityFailure",
    "ProposalRejected",
    "StaleHead",
    "StoreError",
    "blob_hash",
    "parse_rules",
    "rules_bytes",
]
