"""Writ/17 first-write durable claim for a single local file destination.

An exclusive link and directory fsync reserve an effect ID before side
effects. Existing claims never authorize a new write or acknowledgment;
they may only be used to return a previously persisted, identical ACK.

This reference implementation is self-contained and intentionally outside
PCS production. Assumptions: private pinned directory, trustworthy fsync,
no complete rollback of claim/output/ack together.
"""
from __future__ import annotations
import hashlib
import json
import os
import secrets
import stat
from pathlib import Path

MAX_CLAIM_BYTES = 2048


class ClaimError(ValueError):
    pass


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def digest(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()


def expected_claim(request: dict) -> bytes:
    if type(request) is not dict or set(request) != {
        "version", "policy_hash", "effect_id", "action", "sink", "endpoint",
        "route_id", "digest", "size", "nonce", "payload_b64"
    } or type(request["effect_id"]) is not int or request["effect_id"] <= 0:
        raise ClaimError("invalid signed request projection")
    value = {"version": "writ/receiver-claim/1", "effect_id": request["effect_id"],
             "request_hash": digest(request), "digest": request["digest"],
             "lease_nonce": request["nonce"]}
    data = canonical(value)
    if len(data) > MAX_CLAIM_BYTES:
        raise ClaimError("oversized claim")
    return data


def _exists(dirfd: int, name: str) -> bool:
    try:
        os.stat(name, dir_fd=dirfd, follow_symlinks=False)
    except FileNotFoundError:
        return False
    return True


def _read(dirfd: int, name: str) -> bytes:
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=dirfd)
    with os.fdopen(fd, "rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_CLAIM_BYTES:
            raise ClaimError("invalid claim inode")
        return handle.read(MAX_CLAIM_BYTES + 1)


def reserve(request: dict, directory: str | Path) -> bool:
    """True: new claim durable. False: same claim exists; DO NOT reexecute.

    Caller must check a previously committed ACK on False. If the ACK is
    missing, mark outcome uncertain and fail closed, even if the file is
    absent. Never infer from 'output absent' that an effect never occurred.
    """
    if not (getattr(os, "O_NOFOLLOW", 0) and getattr(os, "O_DIRECTORY", 0)):
        raise ClaimError("requires POSIX directory-relative no-follow I/O")
    data = expected_claim(request)
    eid = request["effect_id"]
    claim = f"writ-{eid:012d}.claim.json"
    ack = f"writ-{eid:012d}.ack.json"
    output = f"writ-{eid:012d}.bin"
    dirfd = os.open(Path(directory).resolve(strict=True),
                    os.O_RDONLY | os.O_NOFOLLOW | os.O_DIRECTORY)
    try:
        if _exists(dirfd, claim):
            if _read(dirfd, claim) != data:
                raise ClaimError("conflicting effect claim")
            return False
        if _exists(dirfd, output) or _exists(dirfd, ack):
            raise ClaimError("orphaned output or signed acknowledgment")
        tmp = ".writ-claim-" + secrets.token_hex(16)
        fd = os.open(tmp, os.O_CREAT | os.O_EXCL | os.O_WRONLY |
                     os.O_NOFOLLOW, 0o600, dir_fd=dirfd)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(tmp, claim, src_dir_fd=dirfd,
                        dst_dir_fd=dirfd, follow_symlinks=False)
            except FileExistsError:
                # Concurrent process won. Equal binding is not authorization
                # to redo an operation: only an identical saved ACK may replay.
                if _read(dirfd, claim) != data:
                    raise ClaimError("concurrent conflicting reservation")
                return False
            os.fsync(dirfd)
            return True
        finally:
            os.unlink(tmp, dir_fd=dirfd)
    finally:
        os.close(dirfd)
