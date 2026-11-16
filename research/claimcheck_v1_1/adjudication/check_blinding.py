"""Check that an adjudication package reveals nothing about any system output.

    python -m research.claimcheck_v1_1.adjudication.check_blinding research/claimcheck_v1_1/adjudication/v1_discrepancies/package

Fails if any file in the package contains a verdict word, a receipt or proof-file digest, a reading
proposed by a model, or the name of a column that is not in the deposited table's header, or if the
package holds anything besides the expected files.  The instructions may name the project (the
adjudicator must confirm they took no part in it); nothing else may.  A pass shows the absence of
these leaks, not that the package is complete or correct.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import sys
from pathlib import Path

VERDICT_WORDS = re.compile(r"\b(CONFIRMATION|DISCREPANCY_FOR_REVIEW|REQUIRE_HUMAN_REVIEW|MATCH_PROVED|MISMATCH_PROVED|"
                           r"NOT_ESTABLISHED|PROVED|REFUTED|kernel|verdict|receipt|proposal|proposer|oracle|Lean|Gemini|Nemotron|"
                           r"OpenRouter|provisional|gold)\b", re.I)
DIGEST = re.compile(r"\b[0-9a-f]{64}\b")
ALLOWED_TOP = {"INSTRUCTIONS_FOR_ADJUDICATORS.md"}
ALLOWED_PER_PAPER = {"article.txt", "data_dictionary.json", "sheet.csv"}


def check(package: Path) -> list[str]:
    problems = []
    for item in sorted(package.iterdir()):
        if item.is_file() and item.name not in ALLOWED_TOP:
            problems.append(f"unexpected file at top level: {item.name}")
        if item.is_dir():
            names = {p.name for p in item.iterdir()}
            extra = {n for n in names if n not in ALLOWED_PER_PAPER and not n.lower().endswith(".csv")}
            if extra:
                problems.append(f"{item.name}: unexpected files {sorted(extra)}")
            data_files = [n for n in names if n.lower().endswith(".csv") and n != "sheet.csv"]
            if len(data_files) != 1:
                problems.append(f"{item.name}: expected exactly one data table, found {data_files}")
            sheet = item / "sheet.csv"
            if sheet.is_file():
                rows = list(csv.DictReader(io.StringIO(sheet.read_text(encoding="utf-8"))))
                header = set(rows[0].keys()) if rows else set()
                for col in header:
                    if VERDICT_WORDS.search(col) or col.lower() in {"result", "status", "class", "label", "truth", "expected"}:
                        problems.append(f"{item.name}/sheet.csv: column '{col}' could reveal an answer")
    for path in sorted(package.rglob("*")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(package)
        if path.name == "article.txt" or (path.suffix.lower() == ".csv" and path.name != "sheet.csv"):
            # third-party text and data: only digests are checked (the words above occur in ordinary prose)
            if DIGEST.search(text):
                problems.append(f"{rel}: contains a 64-hex digest")
            continue
        for m in VERDICT_WORDS.finditer(text):
            problems.append(f"{rel}: contains '{m.group(0)}'")
        allowed = set()
        if path.name == "data_dictionary.json":
            # the digest of the data file shipped next to it identifies that file and reveals nothing
            tables = [p for p in path.parent.iterdir() if p.suffix.lower() == ".csv" and p.name != "sheet.csv"]
            if len(tables) == 1 and json.loads(text).get("data_sha256") == hashlib.sha256(tables[0].read_bytes()).hexdigest():
                allowed.add(json.loads(text)["data_sha256"])
        if any(m.group(0) not in allowed for m in DIGEST.finditer(text)):
            problems.append(f"{rel}: contains a 64-hex digest other than the digest of its own data file")
        if path.name != "INSTRUCTIONS_FOR_ADJUDICATORS.md" and re.search(r"ClaimCheck|Proof-Carrying|PCS", text):
            problems.append(f"{rel}: names the project")
    return problems


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    package = Path(argv[0])
    problems = check(package)
    print(json.dumps({"package": str(package), "blind": not problems, "problems": problems[:50]}, indent=1))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
