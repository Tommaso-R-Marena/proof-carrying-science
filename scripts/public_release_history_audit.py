#!/usr/bin/env python3
"""Conservative, redacted Git-history disclosure preflight. Not a release approval."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

MAX_BLOB_BYTES = 8 * 1024 * 1024
MAX_OBJECTS = 100_000

PATTERNS = {
    "private_key_header": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"),
    "github_legacy_token": re.compile(r"\bgh[pousr]_[a-zA-Z0-9_]{30,}\b"),
    "github_fine_grained_token": re.compile(r"\bgithub_pat_[a-zA-Z0-9_]{40,}\b"),
    "aws_access_key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "stripe_live_key": re.compile(r"\b(?:sk_live|rk_live)_[a-zA-Z0-9]{16,}\b"),
    "slack_token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    "plaintext_secret_assignment": re.compile(
        r"""(?im)\b(?:CLOUDFLARE_API_TOKEN|AWS_SECRET_ACCESS_KEY|GITHUB_TOKEN|DATABASE_PASSWORD)\s*[:=]\s*["']?([a-zA-Z0-9_+\-/.=]{20,})["']?"""
    ),
}
RISK_FILENAMES = re.compile(
    r"(?i)(?:^|/)(?:\.env(?:\.[^/]*)?|\.npmrc|id_(?:rsa|ecdsa|ed25519)|credentials|secrets?\.json|[^/]+\.(?:p12|pfx|jks|keystore|sqlite3?|db))$"
)


def matches_in_text(data: bytes) -> list[str]:
    if b"\x00" in data:
        return []
    try:
        value = data.decode("utf-8")
    except UnicodeDecodeError:
        return []
    return [name for name, pattern in PATTERNS.items() if pattern.search(value)]


def _git(root: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    result = subprocess.run(
        ["git", *args], cwd=root, input=input_bytes, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False,
    )
    if result.returncode:
        raise RuntimeError(f"git {args[0]} failed (exit {result.returncode})")
    return result.stdout


def scan(root: Path) -> dict:
    root = root.resolve()
    head = _git(root, "rev-parse", "HEAD").decode("ascii").strip()
    is_shallow = _git(root, "rev-parse", "--is-shallow-repository").strip() == b"true"
    dirty = bool(_git(root, "status", "--porcelain"))
    raw = _git(root, "rev-list", "--objects", "--all").decode("utf-8", "replace")
    object_paths: dict[str, set[str]] = defaultdict(set)
    for line in raw.splitlines():
        oid, sep, name = line.partition(" ")
        if oid:
            object_paths[oid].add(name if sep else "")
    if not object_paths or len(object_paths) > MAX_OBJECTS:
        raise RuntimeError("invalid or oversized Git object inventory")
    all_oids = sorted(object_paths)
    check = _git(
        root, "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)",
        input_bytes=("\n".join(all_oids) + "\n").encode(),
    ).decode("ascii").splitlines()
    if len(check) != len(all_oids):
        raise RuntimeError("Git object inventory incomplete")
    findings = []
    inspected = 0
    skipped_binary = 0
    for record in check:
        oid, kind, raw_size = record.split()
        if kind != "blob":
            continue
        names = sorted(object_paths[oid])
        size = int(raw_size)
        if size > MAX_BLOB_BYTES:
            findings.append({"object": oid, "paths": names, "reason": "large_blob_uninspected"})
            continue
        body = _git(root, "cat-file", "blob", oid)
        if len(body) != size:
            raise RuntimeError("Git blob size mismatch")
        if b"\x00" in body:
            skipped_binary += 1
            reasons = []
        else:
            try:
                body.decode("utf-8")
            except UnicodeDecodeError:
                skipped_binary += 1
                reasons = []
            else:
                inspected += 1
                reasons = matches_in_text(body)
        if any(RISK_FILENAMES.search(p) for p in names):
            reasons.append("sensitive_filename")
        if reasons:
            # Never print secret bytes, snippets, or matching line content.
            findings.append({"object": oid, "paths": names, "reason": sorted(set(reasons))})
    return {
        "format": "pcs-public-release-history-preflight-v1",
        "head": head,
        "shallow": is_shallow,
        "dirty_checkout": dirty,
        "reachable_git_objects": len(all_oids),
        "utf8_blobs_inspected": inspected,
        "binary_blobs_not_content_scanned": skipped_binary,
        "suspected_findings": findings,
        "candidate_count": len(findings),
        "preflight_pass": not is_shallow and not dirty and not findings,
        "release_approved": False,
        "note": "Heuristic check of reachable local refs only. Fetch all heads/tags/PR refs; independently inspect logs, archives, licenses, binary data and rights. No zero-finding result authorizes public release.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, help="write redacted report to path")
    args = parser.parse_args()
    try:
        report = scan(Path.cwd())
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Public release preflight INCOMPLETE: {exc}", file=sys.stderr)
        return 2
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json:
        args.json.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0 if report["preflight_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
