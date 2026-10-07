"""Read-only provenance validator for the 40 real PCS V2 Lean theorem targets.

This validates a pinned source-tree index. It does not execute Lean, construct a
new proof, certify missing scientific evidence, or fix the separate P0 authority
trust boundary. Verified-in-repository and verified-right-now are not synonymous.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

BENCHMARK_FORMAT = "pcs-prooflab-lean-obligation-benchmark-v1"
PUBLIC_FORMAT = "pcs-prooflab-public-source-index-v1"
SOURCE_REVISION = "717c00ea6f362fe059267184273e1a733d59f0ce"
SPLITS = {
    "Binding": "training", "Workflow": "training", "PKPDCheck": "training",
    "Checkers": "validation", "PackageProofs": "evaluation", "Frontier": "evaluation",
}
EXPECTED_COUNTS = {"Binding": 8, "Workflow": 7, "PKPDCheck": 7, "Checkers": 8,
                   "PackageProofs": 7, "Frontier": 3}
DECLARATION = re.compile(r"^(?:theorem|lemma|def|private\s+(?:theorem|def)|abbrev|instance|structure|inductive|namespace|section|end|#eval|#check)\b", re.M)
SYMBOL = re.compile(r"^[a-zA-Z][a-zA-Z0-9_']{1,100}$")


def source_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\x00" + data).hexdigest()


def declaration_span(source: str, name: str) -> tuple[int, str, str]:
    if not SYMBOL.fullmatch(name):
        raise ValueError("Invalid source declaration symbol")
    m = re.search(r"^theorem\s+" + re.escape(name) + r"\b", source, re.M)
    if not m:
        raise ValueError(f"Missing actual theorem declaration: {name}")
    next_decl = DECLARATION.search(source, m.end())
    text = source[m.start() : next_decl.start() if next_decl else len(source)]
    sep = text.find(":=")
    if sep < 0:
        raise ValueError(f"Missing proof body: {name}")
    stmt = re.sub(r"\s+", " ", text[:sep]).strip()
    return source[:m.start()].count("\n") + 1, stmt, text[sep + 2:]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_benchmark(root: Path, index: dict, published: dict) -> dict:
    """Validate the pinned source bytes and public copy; never use public
    pedagogical dependencies as evidence of Lean proof-checking."""
    if (index.get("format") != BENCHMARK_FORMAT or
            published.get("format") != PUBLIC_FORMAT or
            index.get("origin_commit") != SOURCE_REVISION or
            published.get("origin_commit") != SOURCE_REVISION):
        raise ValueError("Unexpected prooflab benchmark schema or source revision")
    cases, views = index.get("cases"), published.get("cases")
    if not isinstance(cases, list) or not isinstance(views, list) or len(cases) != 40 or len(views) != 22:
        raise ValueError("Exactly 40 public-indexed real Lean targets required")
    if len({c["id"] for c in cases}) != 40 or len({v["id"] for v in views}) != 22:
        raise ValueError("Duplicate prooflab case ID")
    view_by_id = {c["id"]: c for c in views}
    names_by_source: dict[str, list[str]] = {}
    path_bytes: dict[str, bytes] = {}
    for c in cases:
        mod, path = c["module"], c["source_path"]
        if mod not in SPLITS or path != f"formal/PCS/V2/{mod}.lean":
            raise ValueError("Source path outside approved PCS Lean V2 modules")
        if c.get("split") != SPLITS[mod] or c.get("project_group") != "pcs-lean-v2":
            raise ValueError("Module held-out benchmark split was changed")
        if c.get("source_revision") != SOURCE_REVISION:
            raise ValueError("Unexpected source commit")
        if path not in path_bytes:
            p = root / path
            data = p.read_bytes()
            path_bytes[path] = data
        actual_blob = source_blob_sha1(path_bytes[path])
        if c.get("source_blob_sha1") != actual_blob:
            raise ValueError(f"Source blob SHA-1 differs for {path}")
        names_by_source.setdefault(path, []).append(c["source_symbol"])
    counts = {m: 0 for m in SPLITS}
    edges = 0
    for c in cases:
        mod, path, name = c["module"], c["source_path"], c["source_symbol"]
        counts[mod] += 1
        source = path_bytes[path].decode("utf-8")
        line, stmt, body = declaration_span(source, name)
        if line != c.get("source_line") or stmt != c.get("source_statement"):
            raise ValueError(f"Tampered or moved theorem statement: {name}")
        targets = names_by_source[path]
        expected = sorted(dep for dep in targets if dep != name and
                          declaration_span(source, dep)[0] < line and
                          re.search(r"\b" + re.escape(dep) + r"\b", body))
        if c.get("cited_theorems") != expected:
            raise ValueError(f"Incorrect source-cited lemma references: {name}")
        edges += len(expected)
        if c["split"] != "training":
            if c["id"] in view_by_id:
                raise ValueError("Held-out theorem leaked to the public game")
            continue
        view = view_by_id[name_id(c)]
        if view.get("source", {}).get("revision") != SOURCE_REVISION:
            raise ValueError("Public source revision mismatch")
        if view["source"].get("blob_sha1") != c["source_blob_sha1"] or (
                view["source"].get("path") != path or view["source"].get("line") != line):
            raise ValueError("Public/source index disagreement")
        if (view.get("theorem") != name or view.get("split") != c["split"] or
                view.get("campaign") != mod or view.get("cited_theorems") != expected):
            raise ValueError("Public puzzle has different provenance or module split")
        if any(key in view for key in ("source_statement", "source_proof_body", "proof_term")):
            raise ValueError("Do not export full private proof bodies")
        nodes = view.get("nodes")
        if not isinstance(nodes, list) or not 7 <= len(nodes) <= 15:
            raise ValueError("Unplayable educational planning graph")
        node_by_id = {n.get("id"): n for n in nodes}
        if len(node_by_id) != len(nodes) or node_by_id["review"]["kind"] != "external-check":
            raise ValueError("Invalid or misleading planning graph")
        for node in nodes:
            if not isinstance(node.get("needs"), list) or node.get("id") in node["needs"]:
                raise ValueError("Invalid prerequisites")
            for need in node["needs"]:
                if need not in node_by_id:
                    raise ValueError("Missing planning prerequisite")
        visiting: set[str] = set()
        visited: set[str] = set()
        def visit(node_id: str) -> None:
            if node_id in visiting:
                raise ValueError("Cyclic planning graph")
            if node_id in visited:
                return
            visiting.add(node_id)
            for prerequisite in node_by_id[node_id]["needs"]:
                visit(prerequisite)
            visiting.remove(node_id)
            visited.add(node_id)
        for node_id in node_by_id:
            visit(node_id)
        for dep in expected:
            if node_by_id.get("lemma-" + dep, {}).get("source_theorem") != dep:
                raise ValueError("Claimed source mention without matching public lemma node")
    if counts != EXPECTED_COUNTS:
        raise ValueError("Incorrect module split counts")
    if (index.get("case_count") != 40 or published.get("case_count") != 40
            or published.get("public_case_count") != 22):
        raise ValueError("Incorrect declared benchmark size")
    if published.get("withheld_by_module") != {
        "Checkers": {"split": "validation", "count": 8},
        "PackageProofs": {"split": "evaluation", "count": 7},
        "Frontier": {"split": "evaluation", "count": 3},
    }:
        raise ValueError("Withheld task counts changed")
    # Previously published 40-case views are not allowed here.
    if any(v.get("split") != "training" for v in views):
        raise ValueError("Nontraining mission published")
    if index.get("case_count") != 40 or published.get("case_count") != 40:
        raise ValueError("Incorrect declared benchmark size")
    return {"case_count": 40, "source_modules": len(SPLITS), "source_cited_edges": edges,
            "training": 22, "validation": 8, "evaluation": 10,
            "split_warning": "Only ONE source PCS project; no cross-project holdout."}


def name_id(case: dict) -> str:
    return case["id"]


def validate_checked_in(root: Path) -> dict:
    index = load(root / "benchmarks/prooflab/pcs_lean_v2_40.json")
    published = load(root / "benchmarks/prooflab/prooflab_public_view.json")
    return validate_benchmark(root, index, published)
