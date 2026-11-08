"""Fixed bounded byte-only worker; imported projects cannot select code paths."""
from __future__ import annotations

import base64
import hashlib
import resource
import sys

from pcs.jsonio import strict_json_loads
from research.scientific_intake_v1.intake import canonical, safe_name, MAX_FILE, MAX_FILES, MAX_TOTAL


def main():
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (75, 75))
    resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024**2, 64 * 1024**2))
    resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
    from .pipeline import MAX_REQUEST, MAX_RESPONSE, _authorize, analyze_snapshots
    data = sys.stdin.buffer.read(MAX_REQUEST + 1)
    if len(data) > MAX_REQUEST:
        raise ValueError("worker request bound")
    request = strict_json_loads(data.decode("utf-8"))
    if type(request) is not dict or set(request) != {"artifacts", "inventory", "check", "formal_check"} or type(request["artifacts"]) is not dict or type(request["inventory"]) is not dict:
        raise ValueError("invalid worker request")
    _authorize(request["check"], request["formal_check"])
    if len(request["artifacts"]) > MAX_FILES:
        raise ValueError("worker file-count bound")
    artifacts, total = {}, 0
    for name, encoded in request["artifacts"].items():
        safe_name(name)
        if not isinstance(encoded, str):
            raise ValueError("worker byte encoding")
        raw = base64.b64decode(encoded, validate=True)
        total += len(raw)
        if len(raw) > MAX_FILE or total > MAX_TOTAL:
            raise ValueError("worker byte bound")
        artifacts[name] = raw
    records = request["inventory"].get("artifacts")
    if type(records) is not list or len(records) != len(artifacts) or any(type(a) is not dict for a in records):
        raise ValueError("worker inventory shape")
    if len({a.get("path") for a in records}) != len(records):
        raise ValueError("worker duplicate inventory path")
    for artifact in records:
        raw = artifacts.get(artifact.get("path"))
        if raw is None or len(raw) != artifact.get("size") or hashlib.sha256(raw).hexdigest() != artifact.get("sha256") or "snapshot_path" in artifact:
            raise ValueError("worker inventory byte binding")
    result = analyze_snapshots(artifacts, request["inventory"], request["check"], request["formal_check"])
    encoded = canonical(result)
    if len(encoded) > MAX_RESPONSE:
        raise ValueError("worker output bound")
    sys.stdout.buffer.write(encoded)


if __name__ == "__main__":
    main()
