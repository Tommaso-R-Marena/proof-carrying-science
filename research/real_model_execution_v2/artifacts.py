"""Exact reviewed bundle; no producer-supplied manifest or executable authority."""
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import shutil
import stat
import time
import urllib.request

from pcs.jsonio import strict_json_loads

ROOT = Path(__file__).resolve().parents[2]
LEGACY = ROOT/"research/real_model_safety_v1/evidence"
LOCK_SHA = "fff09052318ffc3162e16061c5e39fd51eb32dbe0765023947385b506ca875f2"
EXPERIMENT_SHA = "b2b7bf9717ccdfc891ae7f9008b6b2033364b5d56a35d00be65f4782fd3498b9"
TOKENIZER = ("tokenizer.json", "tokenizer_config.json")
REVISION = "c1899de289a04d12100db370d81485cdf75e47ca"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def lock(profile="full"):
    raw = (LEGACY/"weights-manifest.json").read_bytes()
    if digest(raw) != LOCK_SHA:
        raise ValueError("reviewed model lock changed")
    entries = strict_json_loads(raw.decode("ascii"))
    if profile == "full":
        return entries
    if profile == "tokenizer":
        return {n:entries[n] for n in TOKENIZER}
    raise ValueError("fixed artifact profile required")


@contextmanager
def regular(path):
    fd = os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("regular nonsymlink model file required")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            yield stream
    finally:
        os.close(fd)


def stream_file(source, expected, target=None):
    with regular(source) as stream:
        before = os.fstat(stream.fileno())
        if before.st_size != expected["bytes"]:
            raise ValueError("model file size mismatch")
        h, count = hashlib.sha256(), 0
        while chunk := stream.read(min(1024*1024, expected["bytes"]+1-count)):
            count += len(chunk)
            if count > expected["bytes"]:
                raise ValueError("model file grew while reading")
            h.update(chunk)
            if target is not None:
                target.write(chunk)
        after = os.fstat(stream.fileno())
        if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns) != (
                after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):
            raise ValueError("model file changed while reading")
    if count != expected["bytes"] or h.hexdigest() != expected["sha256"]:
        raise ValueError("model file digest mismatch")


def directory(root, expected):
    if root.is_symlink() or not root.is_dir() or {p.name for p in root.iterdir()} != set(expected):
        raise ValueError("exact model directory inventory required")


def verify(root, profile="full"):
    expected = lock(profile)
    directory(root, expected)
    for name, spec in expected.items():
        stream_file(root/name, spec)
    directory(root, expected)
    return expected


def snapshot(source, destination, profile="full"):
    """Copy through checked descriptors; subsequent loading uses only this copy.

    The new directory is owned by this operation. Existing outputs are refused.
    Filesystem routing, loader interpretation and host integrity remain trusted.
    """
    expected = lock(profile)
    directory(source, expected)
    destination.mkdir(parents=True, exist_ok=False)
    try:
        for name, spec in expected.items():
            with (destination/name).open("xb") as target:
                stream_file(source/name, spec, target)
                target.flush()
                os.fsync(target.fileno())
        verify(destination, profile)
    except BaseException:
        shutil.rmtree(destination)
        raise
    return expected


def fetch(destination, profile="tokenizer"):
    """Bounded HTTPS downloads into a fresh directory; never adopts partial data."""
    expected = lock(profile)
    destination.mkdir(parents=True, exist_ok=False)
    try:
        for name, spec in expected.items():
            url = f"https://huggingface.co/Qwen/Qwen3-0.6B/resolve/{REVISION}/{name}"
            deadline=time.monotonic()+(1800 if profile=="full" else 120)
            with urllib.request.urlopen(url, timeout=60) as response, (destination/name).open("xb") as out:
                count = 0
                while True:
                    if time.monotonic()>deadline:raise TimeoutError("artifact transfer deadline")
                    chunk=response.read(min(1024*1024, spec["bytes"]+1-count))
                    if not chunk:break
                    count += len(chunk)
                    if count > spec["bytes"]:
                        raise ValueError("download exceeds pinned byte budget")
                    out.write(chunk)
        verify(destination, profile)
    except BaseException:
        shutil.rmtree(destination)
        raise
    return expected
