"""A private archive of the model responses whose disposition is to withhold them (L2, L3).  Read-only on the repository.

    python -I research/claimcheck_v1_1/governance/archive_model_outputs.py --out DIR [--from REF]
    python -I research/claimcheck_v1_1/governance/archive_model_outputs.py --verify DIR/model-outputs-withheld.tar

It imports only the standard library and finds the repository from its own path, so it runs as a plain
script, on Windows too (the owner's procedure: `docs/integration/claimcheck/A1_ARCHIVE_PROCEDURE.md`).

`--out` takes, for every inventoried response whose action is to withhold it, the original bytes from
Git history (the file at REF, or the last commit before REF where it still has the inventory's
SHA-256), and writes, under DIR (which must be outside the repository):

* `model-outputs-withheld.tar`: a deterministic tar (sorted names, fixed times, owners and modes),
  so that anyone who builds it from the same history gets the same bytes and the same SHA-256;
* `model-outputs-withheld.tar.sha256`;
* `MANIFEST.json`: per file its path, group, model, SHA-256, size, Git blob and the commit it came from.

DIR is made private to its owner (0700, files 0600).  `--verify` reads an archive back, recomputes
every digest and compares it with the archive's manifest and with the repository's inventory, so it
also shows that the archive can be recovered.

It never prints, uploads or commits a response's text, and it writes nothing inside the repository.
The archive is only as private and as durable as the place DIR is in: a copy in a disposable
container is neither durable nor an archive.  Not an owner decision.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
INVENTORY = "docs/integration/claimcheck/model_outputs_inventory.json"
NAME = "model-outputs-withheld"


def git(*args, raw=False):
    out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True).stdout
    return out if raw else out.decode().strip()


def stored_bytes(spec: str) -> bytes:
    """The exact stored bytes: `cat-file blob` is plumbing, with no textconv, filter or end-of-line conversion whatever the local configuration."""
    return git("cat-file", "blob", spec, raw=True)


def originals(ref: str, inventory: dict) -> list[dict]:
    rows = []
    for f in inventory["files"]:
        if not f["action"].startswith("withhold"):
            continue
        found = None
        for c in git("log", "--format=%H", ref, "--", f["path"]).split():
            try:
                raw = stored_bytes(f"{c}:{f['path']}")
            except subprocess.CalledProcessError:
                continue
            if hashlib.sha256(raw).hexdigest() == f["original_sha256"] and len(raw) == f["original_bytes"]:
                found = (c, raw, git("rev-parse", f"{c}:{f['path']}"))
                break
        if found is None:
            raise SystemExit(f"original bytes of {f['path']} not found in the history of {ref}: archive incomplete, stopping")
        c, raw, blob = found
        rows.append({"path": f["path"], "group": f["group"], "model": f["model"], "sha256": f["original_sha256"], "bytes": len(raw),
                     "git_blob": blob, "taken_from_commit": c, "raw": raw})
    return rows


def deterministic_tar(rows: list[dict], manifest: bytes) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        for name, data in [("MANIFEST.json", manifest)] + [(r["path"], r["raw"]) for r in sorted(rows, key=lambda r: r["path"])]:
            info = tarfile.TarInfo(f"{NAME}/{name}")
            info.size, info.mtime, info.mode, info.uid, info.gid, info.uname, info.gname = len(data), 0, 0o600, 0, 0, "", ""
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def build(out: Path, ref: str) -> dict:
    out = out.resolve()
    if out == ROOT or ROOT in out.parents:
        raise SystemExit("the archive must be written outside the repository")
    inventory = json.loads(stored_bytes(f"{ref}:{INVENTORY}"))
    rows = originals(ref, inventory)
    # the manifest depends only on the originals (not on REF or on later edits of the inventory): the same archive from any REF
    manifest = json.dumps({"what": "Model responses withheld from publication (L2, L3); originals, kept privately by the owner.",
                           "files": [{k: v for k, v in r.items() if k != "raw"} for r in rows]}, indent=1, sort_keys=True).encode() + b"\n"
    tar = deterministic_tar(rows, manifest)
    out.mkdir(parents=True, exist_ok=True)
    os.chmod(out, 0o700)
    for name, data in ((f"{NAME}.tar", tar), (f"{NAME}.tar.sha256", (hashlib.sha256(tar).hexdigest() + f"  {NAME}.tar\n").encode()),
                       ("MANIFEST.json", manifest)):
        p = out / name
        p.write_bytes(data)
        os.chmod(p, 0o600)
    return {"archive": str(out / f"{NAME}.tar"), "archive_sha256": hashlib.sha256(tar).hexdigest(), "files": len(rows),
            "by_group": {g: sum(1 for r in rows if r["group"] == g) for g in sorted({r["group"] for r in rows})},
            "manifest_sha256": hashlib.sha256(manifest).hexdigest(), "from_ref": git("rev-parse", ref)}


def verify(archive: Path, ref: str = "HEAD") -> dict:
    inventory = {f["path"]: f for f in json.loads(stored_bytes(f"{ref}:{INVENTORY}"))["files"] if f["action"].startswith("withhold")}
    result = {"archive_sha256": None, "files_in_archive": 0, "files_the_inventory_withholds": len(inventory),
              "missing_from_archive": sorted(inventory), "digest_mismatches": [], "unexpected_members": [],
              "error": None, "recoverable_and_complete": False}
    try:
        result["archive_sha256"] = hashlib.sha256(Path(archive).read_bytes()).hexdigest()
        # read every member into memory: nothing is extracted, so no Python version's extraction rules matter
        with tarfile.open(archive, "r") as tar:
            members = tar.getmembers()
            if any(m.issym() or m.islnk() or not m.isfile() or m.name.startswith("/") or ".." in Path(m.name).parts
                   or not m.name.startswith(NAME + "/") for m in members):
                raise ValueError("unexpected kind of member, or a member outside " + NAME + "/")
            content = {m.name[len(NAME) + 1:]: tar.extractfile(m).read() for m in members}
        if len(content) != len(members) or "MANIFEST.json" not in content:
            raise ValueError("duplicate members, or no MANIFEST.json")
        files = json.loads(content["MANIFEST.json"])["files"]
    except (OSError, EOFError, tarfile.TarError, ValueError, KeyError, TypeError) as exc:   # unreadable: incomplete, said plainly
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result
    listed = {f["path"] for f in files}
    present = [f for f in files if f["path"] in content]
    result["files_in_archive"] = len(present)
    result["missing_from_archive"] = sorted((set(inventory) - listed) | {f["path"] for f in files if f["path"] not in content})
    result["digest_mismatches"] = [f["path"] for f in present
                                   if hashlib.sha256(content[f["path"]]).hexdigest() != f["sha256"] or len(content[f["path"]]) != f["bytes"]
                                   or inventory.get(f["path"], {}).get("original_sha256") != f["sha256"]]
    result["unexpected_members"] = sorted(set(content) - listed - {"MANIFEST.json"})
    result["recoverable_and_complete"] = (listed == set(inventory) and not result["missing_from_archive"]
                                          and not result["digest_mismatches"] and not result["unexpected_members"])
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path)
    ap.add_argument("--from", dest="ref", default="HEAD")
    ap.add_argument("--verify", type=Path)
    a = ap.parse_args(argv)
    if not (a.out or a.verify):
        ap.error("--out or --verify")
    result = {}
    if a.out:
        result["built"] = build(a.out, a.ref)
    if a.verify or a.out:
        result["verified"] = verify(a.verify or Path(result["built"]["archive"]), a.ref)
    print(json.dumps(result, indent=1))
    return 0 if result["verified"]["recoverable_and_complete"] else 1


if __name__ == "__main__":
    sys.exit(main())
