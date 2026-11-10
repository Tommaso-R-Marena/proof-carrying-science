"""Independent Writ/16 pinned-file readback reference (not a PCS production adapter).

A historical receiver signature is insufficient to certify present bytes. Read
the receiver's persisted ACK journal and output from the same pinned directory
FD, rejecting missing, non-regular, symlink, changed or mismatched files.

A correct readback is a point-in-time observation, not future durability.
The host must protect receiver keys, directory access and the socket from
attacker-controlled writes; this reference is NOT an OS sandbox.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import stat
from .destination_reference import check_ack, canonical, DestinationProofError

MAX_BYTES=262144

def readback(directory, signed_ack, pinned_receiver_key:bytes, expected:dict):
    """Check exact signed ACK *and* current retained payload bytes."""
    if not getattr(os, "O_NOFOLLOW", 0) or not getattr(os, "O_DIRECTORY", 0):
        raise DestinationProofError("pinned readback requires POSIX nofollow directories")
    check_ack(signed_ack,pinned_receiver_key,expected)
    body=signed_ack["body"]
    eid=body["effect_id"]
    size=body["size"]
    if type(eid) is not int or eid<=0 or type(size) is not int or not 0<=size<=MAX_BYTES:
        raise DestinationProofError("invalid effect size")
    fd=os.open(Path(directory).resolve(strict=True),
               os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        ackpath=f"writ-{eid:012d}.ack.json"
        file_id=f"writ-{eid:012d}.bin"
        a=os.open(ackpath,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=fd)
        with os.fdopen(a,"rb") as handle:
            raw=handle.read(4097)
        try:
            stored=json.loads(raw)
        except (json.JSONDecodeError,UnicodeDecodeError) as exc:
            raise DestinationProofError("receiver ACK journal corrupted") from exc
        if raw!=canonical(signed_ack) or stored!=signed_ack:
            raise DestinationProofError("receiver ACK journal not identical to verified receipt")
        f=os.open(file_id,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=fd)
        with os.fdopen(f,"rb") as handle:
            before=os.fstat(handle.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size!=size:
                raise DestinationProofError("receiver file is not the acknowledged regular file")
            contents=handle.read(size+1)
            after=os.fstat(handle.fileno())
            if (len(contents)!=size or
                any(getattr(before,k)!=getattr(after,k)
                    for k in ("st_dev","st_ino","st_size","st_ctime_ns","st_mtime_ns"))):
                raise DestinationProofError("receiver file changed during readback")
            if hashlib.sha256(contents).hexdigest()!=body["digest"]:
                raise DestinationProofError("retained bytes disagree with signed ACK")
        return {"effect_id":eid,"sha256":body["digest"],"size":size}
    except OSError as exc:
        raise DestinationProofError("receiver output or journal absent/unsafe") from exc
    finally:
        os.close(fd)
