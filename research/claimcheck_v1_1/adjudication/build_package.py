"""Build a BLINDED package for independent human adjudication.

    python -m research.claimcheck_v1_1.adjudication.build_package v1-discrepancies --out research/claimcheck_v1_1/adjudication/v1_discrepancies

A package holds, per paper: the article text, the data file, a data dictionary taken from the
deposit, and a sheet of printed numbers to classify.  It holds NO system output: no proposed
reading, no verdict, no label.  Items of interest are mixed with control items in a seeded random
order.  The key that says which is which is written to a separate directory and must not be sent.

This script prepares materials.  It does not adjudicate anything, and nothing produced by it is a
human judgement.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import shutil
from pathlib import Path

from ...claimcheck_v1.grounding import sentence_window
from ..dev.common import documents

HERE = Path(__file__).resolve().parent
COLUMNS = ["item", "printed_number", "sentence_with_the_number_marked", "class_T_F_N_A", "what_the_number_is_in_your_words",
           "statistic", "column", "rows_or_group", "value_you_computed_optional", "how_sure_1_to_5", "notes"]
# The apparent paper-versus-data discrepancies reported for v1 (REPORT.md of claimcheck_v1): gold item ids.
V1_DISCREPANCIES = {"06_pmc5980576": ["H06-08", "H06-14", "H06-15"], "09_pmc6476783": None, "10_pmc5817150": None}
CONTROLS_PER_PAPER = 8


def _mark(text: str, start: int, end: int) -> str:
    w0, w1 = sentence_window(text, start, end)
    return (text[w0:start] + "«" + text[start:end] + "»" + text[end:w1]).replace("\n", " ")


def build_v1_discrepancies(out: Path, seed: str = "adjudication-v1-discrepancies") -> dict:
    docs = {d.slug: d for d in documents("heldout") if d.variant == "original"}
    package, keys = out / "package", out / "KEY_DO_NOT_SEND"
    for p in (package, keys):
        if p.exists():
            shutil.rmtree(p)
        p.mkdir(parents=True)
    key, summary = {}, {}
    for slug in sorted(V1_DISCREPANCIES):
        doc = docs[slug]
        wanted = V1_DISCREPANCIES[slug]
        interest = [g for g in doc.gold if g.get("truth") == "inconsistent"] if wanted is None else [g for g in doc.gold if g["id"] in wanted]
        rng = random.Random(hashlib.sha256(f"{seed}|{slug}".encode()).hexdigest())
        others = [g for g in doc.gold if g not in interest]
        controls = rng.sample(others, min(CONTROLS_PER_PAPER, len(others)))
        items = interest + controls
        rng.shuffle(items)
        folder = package / slug
        folder.mkdir()
        (folder / "article.txt").write_text(doc.text, encoding="utf-8")
        (folder / doc.meta["table"]).write_bytes(doc.data)
        dictionary = {"citation": doc.meta.get("citation"), "article_licence": doc.meta.get("article_license"),
                      "data_licence": doc.meta.get("data_license"), "data_file": doc.meta["table"], "data_sha256": hashlib.sha256(doc.data).hexdigest(),
                      "what_one_row_is": doc.manifest.get("note") or doc.manifest.get("description"),
                      "missing_value_tokens": doc.manifest.get("na_tokens"),
                      "columns": {name: {"unit": (spec or {}).get("unit")} for name, spec in (doc.manifest.get("columns") or {}).items()}}
        (folder / "data_dictionary.json").write_text(json.dumps(dictionary, indent=1, ensure_ascii=False), encoding="utf-8")
        with (folder / "sheet.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(COLUMNS)
            for i, g in enumerate(items, 1):
                w.writerow([f"{slug[:2]}-{i:02d}", doc.text[g["start"]:g["end"]], _mark(doc.text, g["start"], g["end"])] + [""] * (len(COLUMNS) - 3))
                key[f"{slug[:2]}-{i:02d}"] = {"paper": slug, "gold_id": g["id"], "start": g["start"], "role": "apparent_discrepancy_in_v1" if g in interest else "control",
                                              "ai_assisted_label": {"kind": g["kind"], "truth": g.get("truth")}}
        summary[slug] = {"items": len(items), "of_interest": len(interest), "controls": len(controls)}
    (keys / "key.json").write_text(json.dumps({"WARNING": "Do not send to adjudicators. AI-assisted labels and roles.", "items": key}, indent=1), encoding="utf-8")
    shutil.copy(HERE / "INSTRUCTIONS_FOR_ADJUDICATORS.md", package / "INSTRUCTIONS_FOR_ADJUDICATORS.md")
    index = {"status": "PREPARED. No adjudicator has seen this package. No human judgement exists yet.", "papers": summary,
             "send": "the 'package' directory only", "do_not_send": "KEY_DO_NOT_SEND, REPORT.md of claimcheck_v1, any ClaimCheck output"}
    (out / "INDEX.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
    return index


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("what", choices=("v1-discrepancies",))
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    print(json.dumps(build_v1_discrepancies(Path(args.out)), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
