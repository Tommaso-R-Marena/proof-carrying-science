#!/usr/bin/env python3
"""Validate exactly mapped, previously archived PCS promotion artifacts.

Run against a pull_request checkout with GITHUB_BASE_SHA pinned to the PR's
base SHA. This is a file-provenance check, not proof of semantic correctness.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PROMOTIONS=ROOT/"contributions"/"pcs-promotions"
UUID=re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",re.I)
SAFE=re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
REPOS={"proof-carrying-science","proof-carrying-science-site"}
FORBIDDEN=re.compile(r"(^|[^A-Za-z0-9_])(sorry|admit|axiom|unsafe|extern|native_decide|implemented_by)([^A-Za-z0-9_]|$)")

def acceptable(repo:str,path:str)->bool:
    parts=path.split("/")
    if not (1<len(parts)<=12 and len(path)<=160 and all(
        SAFE.fullmatch(s) and not s.startswith(".") and s not in (".","..") for s in parts)):
        return False
    if repo=="proof-carrying-science":
        return bool(
            re.fullmatch(r"formal/PCS/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+\.lean",path)
            or re.fullmatch(r"pcs/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+\.py",path)
            or re.fullmatch(r"tests/(?:[A-Za-z0-9_-]+/)*test_[A-Za-z0-9_-]+\.py",path)
            or re.fullmatch(r"docs/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+\.md",path))
    return bool(
        re.fullmatch(r"public/[A-Za-z0-9_-]+\.(?:js|css|html)",path)
        or re.fullmatch(r"src/[A-Za-z0-9_-]+\.js",path)
        or re.fullmatch(r"tests/[A-Za-z0-9_-]+\.test\.mjs",path)
        or re.fullmatch(r"docs/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+\.md",path))

def run()->int:
    repo=os.environ.get("GITHUB_REPOSITORY","").split("/")[-1]
    base=os.environ.get("GITHUB_BASE_SHA","")
    if repo not in REPOS or not re.fullmatch(r"[0-9a-f]{40}",base,re.I):
        raise ValueError("Expected a known PCS GitHub repository and pinned PR base SHA")
    diff=subprocess.run(
        ["git","diff","--name-only",base,"HEAD"],
        cwd=ROOT,capture_output=True,text=True,check=True)
    actual=set(diff.stdout.splitlines())
    manifest_names=[n for n in actual if re.fullmatch(
        r"contributions/pcs-promotions/[0-9a-f-]{36}/manifest\.json",n,re.I)]
    if len(manifest_names)!=1:
        raise ValueError("A promotion PR must introduce exactly one new source-bound promotion manifest")
    manifest_path=ROOT/manifest_names[0]
    obj=json.loads(manifest_path.read_text(encoding="utf-8"))
    promo=manifest_path.parent.name
    source=obj.get("source_submission_id")
    task=obj.get("source_task_id")
    if (obj.get("format")!="pcs-production-promotion-v1" or not UUID.fullmatch(promo)
        or obj.get("promotion_id")!=promo or not UUID.fullmatch(str(source))
        or not re.fullmatch(r"[A-Z][A-Z0-9._-]{2,31}",str(task))
        or obj.get("repository")!=os.environ["GITHUB_REPOSITORY"]
        or obj.get("base_sha")!=base
        or not isinstance(obj.get("attempt"),int) or not 1<=obj["attempt"]<=50
        or not isinstance(obj.get("source_pr_number"),int) or obj["source_pr_number"]<1):
        raise ValueError("Promotion envelope/base/repository is invalid")
    changes=obj.get("changes")
    if not isinstance(changes,list) or not 1<=len(changes)<=3:
        raise ValueError("1–3 exact promotion mappings required")
    expected={manifest_path.relative_to(ROOT).as_posix()}
    used=set()
    source_root=ROOT/"contributions"/"pcs-submissions"/str(task)/str(source)
    if not source_root.is_dir():
        raise ValueError("The accepted submission archive must exist in the repository")
    for item in changes:
        dest=item.get("production_path")
        filename=item.get("source_name")
        if (not isinstance(dest,str) or not acceptable(repo,dest)
            or not isinstance(filename,str) or not re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9._-]{0,78}\.(lean|py|md|txt|json|js|html|css|csv)",filename)
            or filename in used or dest in expected
            or filename.split(".")[-1]!=dest.split(".")[-1]):
            raise ValueError("Forbidden destination or duplicate source mapping")
        used.add(filename)
        expected.add(dest)
        source_path=source_root/filename
        target_path=ROOT/dest
        if not source_path.is_file() or source_path.is_symlink() or not target_path.is_file() or target_path.is_symlink():
            raise ValueError("Archive or production target is missing or symlinked")
        source_bytes=source_path.read_bytes()
        produced_bytes=target_path.read_bytes()
        if (source_bytes!=produced_bytes or len(source_bytes)!=item.get("size_bytes")
            or not 0<len(source_bytes)<=20000
            or hashlib.sha256(source_bytes).hexdigest()!=item.get("sha256")):
            raise ValueError("Destination bytes do not match the accepted archived artifact")
        if dest.endswith(".lean") and FORBIDDEN.search(produced_bytes.decode("utf-8")):
            raise ValueError("Production Lean file contains forbidden proof shortcuts")
    if actual!=expected:
        raise ValueError(f"Promotion altered unexpected paths: missing={sorted(expected-actual)}, extra={sorted(actual-expected)}")
    statuses=subprocess.run(
        ["git","diff","--name-status",base,"HEAD"],cwd=ROOT,
        capture_output=True,text=True,check=True).stdout.splitlines()
    if any(line[0] not in ("A","M") for line in statuses):
        raise ValueError("Promotion PR may only add or modify approved files")
    print(f"PCS PROMOTION FILE GATE PASS: {promo}; {len(changes)} archived files; exact PR diff and baseline bound")
    print("Note: archival byte integrity is NOT proof of scientific or semantic correctness.")
    return 0

if __name__=="__main__":
    try:sys.exit(run())
    except Exception as exc:
        print("PCS PROMOTION FILE GATE FAIL:",str(exc),file=sys.stderr)
        sys.exit(1)
