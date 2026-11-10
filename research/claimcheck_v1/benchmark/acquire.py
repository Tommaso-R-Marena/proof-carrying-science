"""Acquire openly licensed article text and deposited CSV data for the ClaimCheck benchmark.

    python -m research.claimcheck_v1.benchmark.acquire CANDIDATES.json INDEX [INDEX ...] --out DIR

Sources: Europe PMC (article JATS XML, open-access subset) and Zenodo (openly licensed data files,
mostly Dryad deposits mirrored there).
Everything fetched is recorded with URL, SHA-256, byte length, licence and retrieval time.
The JATS-to-text conversion is deterministic and recorded as a transformation: the text that
ClaimCheck binds quotes to is this derived text, not the publisher's PDF.
"""
from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import io
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

UA = {"User-Agent": "claimcheck-benchmark-acquire/1.0", "Accept": "*/*"}
MAX_CSV_BYTES = 64000
SKIP_SECTIONS = {"ref-list", "ack", "fn-group", "glossary", "app-group", "notes"}


def fetch(url: str, timeout: int = 90) -> bytes:
    last = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(4 * (attempt + 1))
    raise RuntimeError(f"cannot fetch {url}: {type(last).__name__}")


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _text(node: ET.Element) -> str:
    """Flatten inline markup; drop citations' bracket noise only by leaving their text as is."""
    parts = []

    def walk(n):
        tag = n.tag.split("}")[-1]
        if tag in ("table-wrap", "fig", "supplementary-material", "inline-formula", "disp-formula", "xref") and n is not node:
            if tag == "xref" and (n.attrib.get("ref-type") in ("bibr",)):
                pass  # citation markers are dropped; their tail text is kept
            elif tag in ("inline-formula", "disp-formula"):
                parts.append("".join(n.itertext()))
            elif tag == "xref":
                parts.append("".join(n.itertext()))
            if n.tail:
                parts.append(n.tail)
            return
        if n.text:
            parts.append(n.text)
        for c in n:
            walk(c)
        if n is not node and n.tail:
            parts.append(n.tail)

    walk(node)
    return re.sub(r"\s+", " ", "".join(parts)).strip()


def jats_to_text(xml_bytes: bytes) -> tuple[str, dict]:
    """Title, abstract, body paragraphs and figure/table captions; one paragraph per block."""
    root = ET.fromstring(xml_bytes)
    blocks: list[str] = []
    stats = {"paragraphs": 0, "captions": 0, "tables_omitted": 0}
    title = root.find(".//article-title")
    if title is not None:
        blocks.append("TITLE: " + _text(title))
    for ab in root.iter("abstract"):
        for p in ab.iter("p"):
            t = _text(p)
            if t:
                blocks.append("ABSTRACT: " + t)
    body = root.find(".//body")

    def walk(sec, heading):
        for child in sec:
            tag = child.tag.split("}")[-1]
            if tag in SKIP_SECTIONS:
                continue
            if tag == "title":
                heading = _text(child)
                if heading:
                    blocks.append("SECTION: " + heading)
            elif tag == "p":
                t = _text(child)
                if t:
                    blocks.append(t)
                    stats["paragraphs"] += 1
                for sub in child:
                    if sub.tag.split("}")[-1] in ("table-wrap", "fig"):
                        walk_float(sub)
            elif tag == "sec":
                walk(child, heading)
            elif tag in ("table-wrap", "fig"):
                walk_float(child)
            elif tag in ("list",):
                for p in child.iter("p"):
                    t = _text(p)
                    if t:
                        blocks.append(t)

    def walk_float(node):
        tag = node.tag.split("}")[-1]
        label = node.find("label")
        cap = node.find("caption")
        if cap is not None:
            t = " ".join(filter(None, [_text(label) if label is not None else "", _text(cap)]))
            if t:
                blocks.append("CAPTION: " + t)
                stats["captions"] += 1
        if tag == "table-wrap":
            stats["tables_omitted"] += 1

    if body is not None:
        walk(body, "")
    for node in root.iter("floats-group"):
        for child in node:
            walk_float(child)
    text = "\n\n".join(blocks) + "\n"
    return text, stats


def generic_rectangular(data: bytes) -> bool:
    """Format screen with Python's csv module only (NOT the ClaimCheck parser)."""
    try:
        rows = list(csv.reader(io.StringIO(data.decode("utf-8-sig"), newline="")))
    except (UnicodeDecodeError, csv.Error):
        return False
    return len(rows) >= 2 and len({len(r) for r in rows}) == 1


def acquire(rec: dict, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pmcid = rec["pmcid"]
    xml_url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
    xml = fetch(xml_url)
    (out / "article.xml").write_bytes(xml)
    text, stats = jats_to_text(xml)
    (out / "article.txt").write_text(text, encoding="utf-8", newline="")
    record = json.loads(fetch(f"https://zenodo.org/api/records/{rec['zenodo']}"))
    files = []
    for f in record.get("files", []):
        name = f["key"]
        if not name.lower().endswith(".csv") or f["size"] > MAX_CSV_BYTES or "readme" in name.lower():
            continue
        url = f"https://zenodo.org/api/records/{rec['zenodo']}/files/{urllib.parse.quote(name)}/content"
        data = fetch(url)
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", name)
        (out / safe).write_bytes(data)
        files.append({"name": name, "stored_as": safe, "url": url, "sha256": sha(data), "bytes": len(data),
                      "zenodo_checksum": f.get("checksum"), "generic_rectangular_csv": generic_rectangular(data)})
    # Pre-registered choice of the one table used for this article: the largest CSV that the
    # generic csv-module screen reads as rectangular.  Chosen by structure, never by results.
    eligible = sorted((f for f in files if f["generic_rectangular_csv"]), key=lambda f: (-f["bytes"], f["name"]))
    chosen = eligible[0]["stored_as"] if eligible else None
    meta = {
        "article": {"doi": rec["article_doi"], "pmcid": pmcid, "license": rec["license"], "journal": rec.get("journal"),
                    "year": rec.get("year"), "xml_url": xml_url, "xml_sha256": sha(xml), "xml_bytes": len(xml),
                    "text_sha256": sha(text.encode("utf-8")), "text_bytes": len(text.encode("utf-8")),
                    "text_transformation": "research.claimcheck_v1.benchmark.acquire.jats_to_text (title, abstract, body paragraphs, captions; tables, formulas-as-markup, references omitted)",
                    "text_stats": stats},
        "dataset": {"zenodo_record": rec["zenodo"], "doi": rec.get("zenodo_doi"), "title": rec["title"],
                    "license": rec["data_license"], "files": files, "chosen_table": chosen,
                    "choice_rule": "largest CSV <= 64000 bytes, not a README, rectangular under Python's csv module"},
        "retrieved_utc": now,
        "discovery_query": rec.get("query"),
    }
    (out / "acquisition.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
    return meta


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("candidates")
    ap.add_argument("indices", nargs="+", type=int)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    cands = json.loads(Path(args.candidates).read_text(encoding="utf-8"))
    for i in args.indices:
        rec = cands[i]
        slug = f"{i:02d}_" + rec["pmcid"].lower()
        meta = acquire(rec, Path(args.out) / slug)
        print(slug, meta["article"]["text_bytes"], meta["dataset"]["chosen_table"],
              [(f["stored_as"], f["bytes"], f["generic_rectangular_csv"]) for f in meta["dataset"]["files"]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
