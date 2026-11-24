"""Contamination safeguards for the prospective benchmark: what may NOT enter it, and how that is checked.

    python -m research.claimcheck_v1_1.prospective.contamination build      # writes EXCLUSIONS.json from the v1 pool
    python -m research.claimcheck_v1_1.prospective.contamination check CANDIDATE.json [--article a.txt] [--data d.csv]

Excluded from the prospective benchmark:
  * every record of the v1 candidate pool (all 51, whether or not it was screened or used);
  * anything that shares an identifier with one (Zenodo record, data DOI, article DOI, PMCID);
  * a near-duplicate title (token Jaccard >= 0.6 after normalisation);
  * a data file whose bytes (SHA-256) equal a file already used;
  * an article whose text shares >= 20 % of its 8-word shingles with an article already used
    (a companion paper, a preprint of the same study, a corrected version).

The check is mechanical and is recorded for every candidate, including the ones it rejects.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

V1 = Path(__file__).resolve().parents[2] / "claimcheck_v1" / "benchmark"
OUT = Path(__file__).with_name("EXCLUSIONS.json")
TITLE_JACCARD = 0.6
SHINGLE_OVERLAP = 0.2


def _tokens(title: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", title.lower()) if len(w) > 2}


def _stable_shingles(text: str, k: int = 8) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {hashlib.sha256(" ".join(words[i:i + k]).encode()).hexdigest()[:16] for i in range(max(0, len(words) - k + 1))}


def build() -> dict:
    pool = json.loads((V1 / "candidates.json").read_text(encoding="utf-8"))
    used = []
    for split in ("dev", "heldout"):
        for root in sorted((V1 / split).iterdir()):
            if not (root / "document.json").exists():
                continue
            meta = json.loads((root / "document.json").read_text(encoding="utf-8"))
            used.append({"slug": root.name, "split": split, "citation": meta.get("citation"), "article_doi": meta.get("article_doi"),
                         "zenodo_record": str(meta.get("zenodo_record")), "data_sha256": hashlib.sha256((root / meta["table"]).read_bytes()).hexdigest(),
                         "article_sha256": hashlib.sha256((root / "article.txt").read_bytes()).hexdigest(),
                         "article_path": str((root / "article.txt").relative_to(V1.parents[1]))})
    out = {
        "note": "Everything here was seen while ClaimCheck v1 or v1.1 was developed. None of it may enter the prospective benchmark.",
        "identifiers": {"zenodo": sorted({str(c["zenodo"]) for c in pool} | {u["zenodo_record"] for u in used}),
                        "data_doi": sorted({c["zenodo_doi"].lower() for c in pool if c.get("zenodo_doi")}),
                        "article_doi": sorted({c["article_doi"].lower() for c in pool if c.get("article_doi")} | {u["article_doi"].lower() for u in used if u.get("article_doi")}),
                        "pmcid": sorted({c["pmcid"] for c in pool if c.get("pmcid")})},
        "titles": sorted({c["title"] for c in pool if c.get("title")}),
        "used_documents": used,
        "thresholds": {"title_token_jaccard": TITLE_JACCARD, "article_8_word_shingle_overlap": SHINGLE_OVERLAP},
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    return out


def check(candidate: dict, article_text: str | None = None, data: bytes | None = None, exclusions: dict | None = None) -> list[str]:
    """Reasons this candidate is excluded (empty list: it passes the mechanical safeguards)."""
    ex = exclusions or json.loads(OUT.read_text(encoding="utf-8"))
    ids = ex["identifiers"]
    reasons = []
    if str(candidate.get("zenodo", "")) in ids["zenodo"]:
        reasons.append("the data record was in the v1 candidate pool")
    for key, field in (("data_doi", "zenodo_doi"), ("article_doi", "article_doi")):
        if str(candidate.get(field, "")).lower() in ids[key] and candidate.get(field):
            reasons.append(f"{field} was in the v1 candidate pool")
    if candidate.get("pmcid") in ids["pmcid"]:
        reasons.append("the article was in the v1 candidate pool")
    mine = _tokens(candidate.get("title", ""))
    for title in ex["titles"]:
        other = _tokens(title)
        if mine and other and len(mine & other) / len(mine | other) >= ex["thresholds"]["title_token_jaccard"]:
            reasons.append(f"title is a near-duplicate of a v1 pool title: {title[:80]}")
            break
    if data is not None and hashlib.sha256(data).hexdigest() in {u["data_sha256"] for u in ex["used_documents"]}:
        reasons.append("the data file's bytes equal a data file already used")
    if article_text is not None:
        mine_s = _stable_shingles(article_text)
        for u in ex["used_documents"]:
            path = V1.parents[1] / u["article_path"]
            if path.exists() and mine_s:
                share = len(mine_s & _stable_shingles(path.read_text(encoding="utf-8"))) / len(mine_s)
                if share >= ex["thresholds"]["article_8_word_shingle_overlap"]:
                    reasons.append(f"article text overlaps a used article ({u['slug']}): {share:.0%} of 8-word shingles")
                    break
    return reasons


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    c = sub.add_parser("check")
    c.add_argument("candidate")
    c.add_argument("--article")
    c.add_argument("--data")
    args = ap.parse_args(argv)
    if args.cmd == "build":
        out = build()
        print(json.dumps({"excluded_zenodo_records": len(out["identifiers"]["zenodo"]), "used_documents": len(out["used_documents"]), "written": str(OUT)}))
        return 0
    reasons = check(json.loads(Path(args.candidate).read_text(encoding="utf-8")),
                    Path(args.article).read_text(encoding="utf-8") if args.article else None,
                    Path(args.data).read_bytes() if args.data else None)
    print(json.dumps({"excluded": bool(reasons), "reasons": reasons}, indent=1))
    return 1 if reasons else 0


if __name__ == "__main__":
    raise SystemExit(main())
