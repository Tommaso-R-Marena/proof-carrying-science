"""Source-bound regressions for the unchanged PR199–203 research stack.

These tests use synthetic files and checkpoint copies. No heldout corpus,
annotation, old evidence file, controller or runtime implementation is edited.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[3]
AUDIT = ROOT / "research/scientific_review_v4/evidence/stack-audit.json"
CANDIDATE = "26a8adda12dbb7fd949f14eeddee3d7d870cadd1"
PROTECTED = "bc78660b5fac857fce3873eb6cda0445d1903da1"


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def _tree(ref):
    result = {}
    for row in _git("ls-tree", "-rz", "--full-tree", ref).split(b"\0"):
        if row:
            metadata, path = row.split(b"\t", 1)
            result[path.decode()] = metadata.decode()
    return result


def _pdf(padding=0):
    stream = b"BT /F1 12 Tf 20 100 Td (Iterations: 7) Tj ET\n%" + b"x" * padding + b"\n"
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>",
               b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
               b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
               b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"endstream"]
    raw = b"%PDF-1.4\n"
    offsets = []
    for index, obj in enumerate(objects, 1):
        offsets.append(len(raw))
        raw += f"{index} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(raw)
    return (raw + b"xref\n0 6\n0000000000 65535 f \n" +
            b"".join(f"{offset:010} 00000 n \n".encode() for offset in offsets) +
            b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n" + str(xref).encode() + b"\n%%EOF\n")


def test_frozen_stack_runtime_identities_and_census():
    audit = json.loads(AUDIT.read_text())
    records = audit["source_census"]["files"]
    assert len(records) == 70
    assert sum(record["lines"] for record in records) == 14083
    assert len(audit["source_census"]["exact_duplicate_body_groups"]) == 11
    for record in records:
        raw = _git("show", CANDIDATE + ":" + record["path"])
        assert _sha(raw) == record["sha256"]
        # The active old implementation must retain the independently audited bytes.
        assert (ROOT / record["path"]).read_bytes() == raw


def test_five_prs_preserve_every_protected_blob_and_mode():
    old, new = _tree(PROTECTED), _tree(CANDIDATE)
    assert len(old) == 8047 and len(new) == 8556
    assert old.keys() <= new.keys()
    assert all(new[path] == identity for path, identity in old.items())
    additions = new.keys() - old.keys()
    assert len(additions) == 509
    assert len([p for p in additions if p.startswith(".github/workflows/")]) == 5
    assert {p.split("/")[1] for p in additions if p.startswith("research/")} == {
        "proof_jepa_rl_v1", "safety_jepa_v1", "scientific_intake_v1",
        "scientific_understanding_v2", "scientific_semantics_v3"}


def test_admission_plan_keeps_v22_separate_and_pending_review():
    plan = json.loads((AUDIT.parents[1] / "source_admission_plan.json").read_text())
    assert plan["status"] == "PENDING_REVIEW_NOT_IMPLEMENTED"
    assert plan["authority_granted"] is False
    assert plan["protected_baseline"]["snapshot_files"] == 8042
    assert plan["protected_baseline"]["control_files"] == 5
    assert plan["protected_baseline"]["historical_prs"] == 72
    assert plan["proposed_successor"]["historical_prs"] == 77
    assert plan["protected_baseline"]["v22_executed_by_this_audit"] is False
    path = plan["protected_baseline"]["manifest_path"]
    raw = _git("show", PROTECTED + ":" + path)
    assert _sha(raw) == plan["protected_baseline"]["manifest_sha256"]
    assert _git("show", CANDIDATE + ":" + path) == raw


def test_large_valid_pdf_admitted_then_v3_aborts_whole_semantic_stage(tmp_path):
    from research.scientific_intake_v1.intake import ingest
    from research.scientific_semantics_v3 import pipeline
    source = tmp_path / "source"
    source.mkdir()
    raw = _pdf(1_001_000)
    (source / "paper.pdf").write_bytes(raw)
    inventory = ingest(source, tmp_path / "intake")
    artifact = inventory["artifacts"][0]
    assert 1_000_000 < artifact["size"] < 5 * 1024**2
    assert (tmp_path / "intake" / artifact["object"]).read_bytes() == raw
    if Path("/usr/bin/pdftotext").is_file():
        assert artifact["status"] == "EXTRACTED"
    with pytest.raises(ValueError, match="bounded semantic worker failed"):
        pipeline.run(source, tmp_path / "v3", check=False)
    assert not (tmp_path / "v3/summary.json").exists()


def test_jats_and_pdf_do_not_inherit_text_meaning_support(tmp_path):
    from research.scientific_semantics_v3.semantics import interpret_project
    sources = {"report.txt": b"Iterations: 7\n",
               "article.xml": b"<article><body><p>Iterations: 7</p></body></article>",
               "paper.pdf": _pdf()}
    results = {}
    for name, raw in sources.items():
        folder = tmp_path / name.replace(".", "-")
        folder.mkdir()
        (folder / name).write_bytes(raw)
        results[name] = interpret_project(folder)
    assert len(results["report.txt"]["claims"]) == 1
    for name in ("article.xml", "paper.pdf"):
        assert results[name]["claims"] == []
        assert results[name]["unresolved"]


def test_unlisted_physical_file_is_ignored_without_authority(tmp_path):
    from research.scientific_semantics_v3 import pipeline
    source = tmp_path / "source"
    source.mkdir()
    (source / "report.txt").write_text("Iterations: 7\n")
    packet = tmp_path / "packet"
    pipeline.run(source, packet, check=False)
    pin = _sha((packet / "manifest.json").read_bytes())
    before = pipeline.replay(packet, recheck=False, expected_manifest_sha256=pin)
    meaning_bytes = (packet / "semantics.json").read_bytes()
    (packet / "unlisted.txt").write_text("Iterations: 999\n")
    after = pipeline.replay(packet, recheck=False, expected_manifest_sha256=pin)
    assert after == before
    assert after["authority"] is False
    assert after["scientific_meaning"] == "OPEN"
    assert (packet / "semantics.json").read_bytes() == meaning_bytes
    assert all(c.get("value") != "999" for c in json.loads(meaning_bytes)["claims"])


def test_checkpoint_copy_reproduces_stale_cache_and_duplicate_key_limit(tmp_path):
    from research.scientific_understanding_v2 import retrieval
    retrieval._load_checkpoint.cache_clear()
    try:
        path = tmp_path / "checkpoint.json"
        raw = Path(retrieval.DEFAULT_CHECKPOINT).read_bytes()
        path.write_bytes(raw)
        sidecar = path.with_suffix(".json.sha256")
        sidecar.write_text(_sha(raw))
        stamp = path.stat().st_mtime_ns
        original = retrieval.load_checkpoint(path)
        modified = json.loads(raw)
        modified["weights"]["embedding"][0][0] += 1
        changed = json.dumps(modified).encode()
        path.write_bytes(changed)
        sidecar.write_text(_sha(changed))
        os.utime(path, ns=(stamp, stamp))
        assert retrieval.load_checkpoint(path) is original
        assert original["weights"]["embedding"][0][0] != modified["weights"]["embedding"][0][0]
        retrieval._load_checkpoint.cache_clear()
        duplicate = b'{"schema":"invalid-shadow",' + raw.lstrip()[1:]
        path.write_bytes(duplicate)
        sidecar.write_text(_sha(duplicate))
        assert retrieval.load_checkpoint(path)["schema"] == "scientific-source-encoder-v1"
    finally:
        retrieval._load_checkpoint.cache_clear()
