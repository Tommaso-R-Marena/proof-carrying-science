from __future__ import annotations
from pathlib import Path

# Strict, fail-closed high-assurance CSV subset, implemented identically by the Lean
# authority (formal/PCS/V2/Csv.lean, `CsvTable` / `parseCsv`):
#
# * valid UTF-8 bytes;
# * no '"' (0x22) and no NUL byte, so no quoting/escaping rule can ever apply;
# * lines separated by LF; a line may end with one CR (CRLF); no other CR;
# * first line = non-empty header; empty data lines are ignored;
# * fields separated by ',' with no unquoting or trimming;
# * distinct header names, every data row exactly as wide as the header, and every
#   field at most 131072 bytes (Python's default csv field size limit).
#
# Inside the subset the table is exactly what `csv.DictReader` produces; outside it
# the check raises (and replay reports FAIL) instead of inheriting DictReader's
# lenient behaviour (last-wins duplicate headers, `None` for short rows, quote
# handling, lone-CR line ends). See counterexamples 9-12 in
# formal/PCS_FRONTIER_FORMALIZATION_REPORT.md.

MAX_STRICT_CSV_FIELD_BYTES = 131072


class StrictCSVError(ValueError):
    pass


def parse_strict_csv(raw: bytes) -> tuple[list[bytes], list[list[bytes]]]:
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StrictCSVError(f"CSV is not valid UTF-8: {exc}") from exc
    if b'"' in raw:
        raise StrictCSVError("quoted CSV fields are outside the strict CSV subset")
    if b"\x00" in raw:
        raise StrictCSVError("NUL byte is outside the strict CSV subset")
    lines: list[bytes] = []
    for raw_line in raw.split(b"\n"):
        line = raw_line[:-1] if raw_line.endswith(b"\r") else raw_line
        if b"\r" in line:
            raise StrictCSVError("bare CR is outside the strict CSV subset")
        lines.append(line)
    header_line, rest = lines[0], lines[1:]
    if header_line == b"":
        raise StrictCSVError("missing CSV header")
    header = header_line.split(b",")
    if len(set(header)) != len(header):
        raise StrictCSVError("duplicate CSV header name")
    rows = [line.split(b",") for line in rest if line != b""]
    for row in rows:
        if len(row) != len(header):
            raise StrictCSVError("ragged CSV row is outside the strict CSV subset")
    for field in header + [f for row in rows for f in row]:
        if len(field) > MAX_STRICT_CSV_FIELD_BYTES:
            raise StrictCSVError("CSV field exceeds the strict field size limit")
    return header, rows


def _key_values(raw: bytes, key: bytes, label: str) -> set[bytes]:
    header, rows = parse_strict_csv(raw)
    if key not in header:
        raise ValueError(f"missing key column in {label}")
    index = header.index(key)
    return {row[index] for row in rows}


def csv_key_disjoint(left: str | Path, right: str | Path, key: str) -> tuple[bool, dict]:
    key_bytes = key.encode("utf-8")
    a = _key_values(Path(left).read_bytes(), key_bytes, str(left))
    b = _key_values(Path(right).read_bytes(), key_bytes, str(right))
    overlap = sorted(a & b)
    return (not overlap, {
        "key": key,
        "left_unique": len(a),
        "right_unique": len(b),
        "overlap_count": len(overlap),
        "overlap_sample": [v.decode("utf-8") for v in overlap[:20]],
        "csv_profile": "pcs-strict-csv-v1",
    })
