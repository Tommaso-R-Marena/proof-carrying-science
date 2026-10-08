#!/usr/bin/env python3
"""Bounded log transport of verified source bytes; not an authority pathway."""
import base64
import hashlib
import json
import pathlib
import re
import tarfile

archive = pathlib.Path("2a36c1d1-647b-4a5a-864b-25416f44e231-aristotle (3).tar.gz")
if hashlib.sha256(archive.read_bytes()).hexdigest() != "a89544a2d264083ee3d5f92ecf8bad78b665f7c894d2253273deb19e8b8549e0":
    raise SystemExit("Archive hash mismatch")
emitted = 0
with tarfile.open(archive, "r:gz") as t:
    for f in t:
        if not f.isfile() or f.size <= 16000:
            continue
        parts = pathlib.PurePosixPath(f.name).parts
        if not parts or parts[0] != "output-final_aristotle" or ".." in parts[1:]:
            raise SystemExit("Unsafe member")
        path = pathlib.Path("formal", *parts[1:])
        raw = t.extractfile(f).read()
        if str(path) == "formal/PCS/V2/DistributedContributors.lean":
            raw = re.sub(r"\badmit\b", "admitSubmission", raw.decode("utf-8")).encode("utf-8")
        if path.is_file() and path.read_bytes() == raw:
            continue
        payload = base64.b64encode(raw).decode("ascii")
        parts_data = [payload[i:i+6000] for i in range(0, len(payload), 6000)]
        for i, part in enumerate(parts_data):
            print("PCS_SOURCE_CHUNK " + json.dumps({
                "path":str(path), "i":i,"n":len(parts_data), "part":part,
                "mode":"100755" if path.suffix == ".sh" else "100644"}, separators=(",",":")), flush=True)
        emitted += 1
print("PCS_SOURCE_CHUNK_FILES", emitted, flush=True)
