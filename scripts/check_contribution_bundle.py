#!/usr/bin/env python3
"""Static integrity gate for untrusted PCS contribution bundles.

This tool NEVER considers a passing static check evidence of scientific truth.
The GitHub PR contains only data files under contributions/pcs-submissions/.
"""
from __future__ import annotations
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "contributions" / "pcs-submissions"
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,78}\.(lean|py|md|txt|json|js|html|css|csv)$")
TASK = re.compile(r"^[A-Z][A-Z0-9._-]{2,31}$")
UUID = re.compile(r"^[0-9a-f-]{36}$", re.I)
FORBIDDEN = re.compile(r"(^|[^A-Za-z0-9_])(sorry|admit|axiom|unsafe|extern|native_decide|implemented_by)([^A-Za-z0-9_]|$)")
MAX_TOTAL_BYTES = 40000

def main() -> int:
    manifests = sorted(BASE.glob("*/*/manifest.json")) if BASE.exists() else []
    if not manifests:
        print("No staged PCS submission manifest found; fail closed.")
        return 2
    errors = []
    for manifest_path in manifests:
        folder = manifest_path.parent
        task, submission_id = folder.parent.name, folder.name
        if not TASK.fullmatch(task) or not UUID.fullmatch(submission_id):
            errors.append(f"Invalid submission folder: {folder.relative_to(ROOT)}")
            continue
        try:
            manifest = json.loads(manifest_path.read_text("utf-8"))
            assert manifest.get("format") == "pcs-submission-artifacts-v1"
            assert manifest.get("task_id") == task
            assert manifest.get("submission_id") == submission_id
            items = manifest.get("files")
            assert isinstance(items, list) and 1 <= len(items) <= 3
            expected = {"manifest.json"}
            total = 0
            for f in items:
                name = f["name"]
                assert NAME.fullmatch(name) and ".." not in name and name != "manifest.json"
                assert name.lower() not in {x.lower() for x in expected}
                expected.add(name)
                path = folder / name
                assert path.is_file() and not path.is_symlink()
                raw = path.read_bytes()
                total += len(raw)
                assert 0 < len(raw) <= 20000 and total <= MAX_TOTAL_BYTES
                assert len(raw) == f["size_bytes"]
                assert hashlib.sha256(raw).hexdigest() == f["sha256"]
                text = raw.decode("utf-8")
                if name.endswith(".json"):
                    json.loads(text)
                if name.endswith(".lean") and FORBIDDEN.search(text):
                    raise ValueError("Forbidden Lean proof shortcut in " + name)
            actual = {p.name for p in folder.iterdir()}
            assert actual == expected, f"Unexpected or missing files: {actual ^ expected}"
            print(f"Bundle integrity PASS: {task}/{submission_id}, {len(items)} files, {total} bytes")
        except Exception as exc:
            errors.append(f"{folder.relative_to(ROOT)}: {exc}")
    for error in errors:
        print("FAIL:", error, file=sys.stderr)
    return 1 if errors else 0

if __name__ == "__main__":
    raise SystemExit(main())
