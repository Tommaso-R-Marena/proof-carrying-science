"""Lossless deterministic archive support for trusted local research evidence.

Logical result names remain *.json. Publication may use *.json.gz with a
manifest binding the exact original bytes; readers handle either without reruns.
This utility has no verifier authority and executes no embedded proof or code.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil


def exists(path):
    path = Path(path)
    return path.exists() or Path(str(path) + ".gz").exists()


def raw_bytes(path, *, max_bytes=64 * 1024 * 1024):
    path = Path(path)
    archived = Path(str(path) + ".gz")
    source = path if path.exists() else archived
    try:
        if source == path and source.stat().st_size > max_bytes:
            raise ValueError("research evidence exceeds bounded reader size")
        opener = gzip.open if source == archived else open
        with opener(source, "rb") as handle:
            value = handle.read(max_bytes + 1)
    except FileNotFoundError:
        # A concurrently completed archive removes raw bytes only after its
        # gzip has been validated. Retry that exact alternate, never a result.
        if source != path:
            raise
        with gzip.open(archived, "rb") as handle:
            value = handle.read(max_bytes + 1)
    if len(value) > max_bytes:
        raise ValueError("research evidence exceeds bounded reader size")
    return value


def read(path):
    return json.loads(raw_bytes(path))


def logical_paths(folder):
    folder = Path(folder)
    return sorted(set(folder.glob("*.json")) | {Path(str(path)[:-3]) for path in folder.glob("*.json.gz")})


def verify_archive(folder, manifest):
    folder = Path(folder)
    if manifest.get("format") != "pcs-lossless-research-archive-v1":
        raise ValueError("invalid research archive manifest")
    names = set()
    for row in manifest["records"]:
        name = row["logical_name"]
        if Path(name).name != name or not name.endswith(".json") or name in names:
            raise ValueError("invalid or duplicate logical result")
        names.add(name)
        archived = folder / row["archive_name"]
        if row["archive_name"] != name + ".gz":
            raise ValueError("archive path binding mismatch")
        if archived.stat().st_size != row["archive_bytes"] or hashlib.sha256(archived.read_bytes()).hexdigest() != row["archive_sha256"]:
            raise ValueError("changed research archive")
        original = raw_bytes(folder / name)
        if len(original) != row["raw_bytes"] or hashlib.sha256(original).hexdigest() != row["raw_sha256"]:
            raise ValueError("changed original research result bytes")
    return {"verified": len(names), "raw_bytes_changed": False}


def archive(folder, private, *, pattern="*.json"):
    folder, private = Path(folder), Path(private)
    if private.exists():
        raise ValueError("original-byte backup must use a new directory")
    private.mkdir(parents=True)
    records = []
    if Path(pattern).name != pattern or not pattern.endswith(".json"):
        raise ValueError("archive pattern must select direct JSON files")
    for source in sorted(folder.glob(pattern)):
        compressed = Path(str(source) + ".gz")
        if compressed.exists():
            raise ValueError("existing compressed evidence cannot be overwritten")
        shutil.copy2(source, private / source.name)
        with source.open("rb") as incoming, compressed.open("wb") as output:
            with gzip.GzipFile(fileobj=output, mode="wb", filename="", mtime=0) as zipped:
                shutil.copyfileobj(incoming, zipped, length=64 * 1024)
        original = raw_bytes(source)
        with gzip.open(compressed, "rb") as checked:
            decoded = checked.read(64 * 1024 * 1024 + 1)
        if decoded != original:
            raise ValueError("lossless archive validation failed")
        records.append({"logical_name": source.name, "archive_name": compressed.name,
                        "raw_bytes": len(original), "archive_bytes": compressed.stat().st_size,
                        "raw_sha256": hashlib.sha256(original).hexdigest(),
                        "archive_sha256": hashlib.sha256(compressed.read_bytes()).hexdigest()})
        source.unlink()
    return {"format": "pcs-lossless-research-archive-v1", "records": records,
            "raw_bytes_preserved_privately": True, "result_values_changed": False,
            "raw_bytes": sum(row["raw_bytes"] for row in records),
            "archive_bytes": sum(row["archive_bytes"] for row in records)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder")
    parser.add_argument("--private-backup", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--pattern", default="*.json")
    args = parser.parse_args()
    report = archive(args.folder, args.private_backup, pattern=args.pattern)
    Path(args.manifest).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "records"}))
