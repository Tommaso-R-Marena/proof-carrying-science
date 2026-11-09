"""Research v5: byte-grounded, exact-rational CSV arithmetic proof obligations.

A reviewed, out-of-band JSON *template* is required: no model may invent column
units or formulae. CSV rows are deliberately a strict subset (ASCII, unquoted,
number-only cells). This lets every cell carry an exact byte span without relying
on heuristics about CSV quoting/newlines. Formal proofs are only about generated
closed arithmetic terms, NOT CSV semantic correctness or scientific validity.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any, TYPE_CHECKING

from .core import Source, canonical, sha
from .typed import (
    IDENT, MAX_SYMBOLS, UnsupportedTyped, parse_bindings, parse_typed_claim,
    unit_value, typed_truth,
)

if TYPE_CHECKING:
    from .pipeline import LeanChecker

_TABLE_SCHEMA = "pcs-tabular-evidence-v5-research"
_NUM = re.compile(rb"-?(?:0|[1-9][0-9]{0,5})(?:\.[0-9]{1,6})?\Z")
_MAX_ROWS = 16
_MAX_ASSERTIONS = 4
_MAX_CELL_BYTES = 24
_MAX_CONFIG_BYTES = 8192


class UnsupportedTable(ValueError):
    """Invalid CSV, template or evidence-bound typed calculation."""


def _strict_pairs(items: list[tuple[str, Any]]) -> dict:
    seen: dict = {}
    for key, value in items:
        if key in seen:
            raise UnsupportedTable("duplicate JSON key in table manifest")
        seen[key] = value
    return seen


@dataclass(frozen=True)
class Column:
    name: str
    unit: str


@dataclass(frozen=True)
class Assertion:
    claim_id: str
    expression: str


@dataclass(frozen=True)
class TableSpec:
    raw_sha256: str
    columns: tuple[Column, ...]
    assertions: tuple[Assertion, ...]


def parse_table_spec(raw: bytes) -> TableSpec:
    if not 0 < len(raw) <= _MAX_CONFIG_BYTES:
        raise UnsupportedTable("manifest byte limit exceeded or empty")
    try:
        data = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=_strict_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(UnsupportedTable("nonfinite JSON number")))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise UnsupportedTable("manifest must be strict UTF-8 JSON") from exc
    if type(data) is not dict or set(data) != {"schema", "columns", "assertions"} or data["schema"] != _TABLE_SCHEMA:
        raise UnsupportedTable("wrong table manifest schema")
    raw_columns, raw_assertions = data["columns"], data["assertions"]
    if type(raw_columns) is not list or not 1 <= len(raw_columns) <= MAX_SYMBOLS:
        raise UnsupportedTable("invalid column count")
    if type(raw_assertions) is not list or not 1 <= len(raw_assertions) <= _MAX_ASSERTIONS:
        raise UnsupportedTable("invalid assertion count")
    columns, used = [], set()
    for raw_col in raw_columns:
        if type(raw_col) is not dict or set(raw_col) != {"name", "unit"}:
            raise UnsupportedTable("column requires only name/unit")
        name, unit = raw_col["name"], raw_col["unit"]
        if type(name) is not str or not IDENT.fullmatch(name) or name in used:
            raise UnsupportedTable("duplicate/invalid column name")
        if type(unit) is not str or len(unit) > 60:
            raise UnsupportedTable("column unit must be a bounded string")
        try:
            unit_value(unit)
        except (UnsupportedTyped, ValueError, OverflowError, ZeroDivisionError) as exc:
            raise UnsupportedTable("unsupported declared unit") from exc
        used.add(name)
        columns.append(Column(name, unit))
    assertions, seen_assertions = [], set()
    for item in raw_assertions:
        if type(item) is not dict or set(item) != {"id", "expression"}:
            raise UnsupportedTable("assertion requires only id/expression")
        cid, expr = item["id"], item["expression"]
        if type(cid) is not str or not IDENT.fullmatch(cid) or cid in seen_assertions:
            raise UnsupportedTable("duplicate/invalid assertion ID")
        if type(expr) is not str or not (1 <= len(expr) <= 240) or any(ch in expr for ch in "\r\n\x00"):
            raise UnsupportedTable("unsupported expression length or control characters")
        seen_assertions.add(cid)
        assertions.append(Assertion(cid, expr))
    return TableSpec(sha(raw), tuple(columns), tuple(assertions))


@dataclass(frozen=True)
class CSVCell:
    name: str
    value: str
    start: int
    end: int

    def receipt(self) -> dict:
        return {"column": self.name, "source_span": {"start": self.start, "end": self.end},
                "raw_value_sha256": sha(self.value.encode("ascii"))}


@dataclass(frozen=True)
class CSVRow:
    number: int
    start: int
    end: int
    cells: tuple[CSVCell, ...]
    raw_sha256: str


def parse_table_rows(source: Source, spec: TableSpec) -> tuple[CSVRow, ...]:
    raw = source.raw
    if not raw.isascii() or b"\x00" in raw or b"\r" in raw.replace(b"\r\n", b""):
        raise UnsupportedTable("CSV must be ASCII with LF or CRLF line endings")
    if b'"' in raw or b"'" in raw or b"\t" in raw or b";" in raw:
        raise UnsupportedTable("quoted, tab-separated or semicolon CSV unsupported")
    # split with original offsets preserved; no embedded newlines/quotes allowed.
    physical = raw.splitlines(keepends=True)
    if not physical or any(not item.rstrip(b"\r\n") for item in physical):
        raise UnsupportedTable("blank CSV records unsupported")
    if len(physical) < 2 or len(physical) - 1 > _MAX_ROWS:
        raise UnsupportedTable("CSV row count outside 1..16")
    headers = physical[0].rstrip(b"\r\n").split(b",")
    if headers != [c.name.encode("ascii") for c in spec.columns]:
        raise UnsupportedTable("CSV header order/names do not match reviewed template")
    pos = len(physical[0])
    rows = []
    for rowno, physical_row in enumerate(physical[1:], 1):
        line = physical_row.rstrip(b"\r\n")
        pieces = line.split(b",")
        if len(pieces) != len(spec.columns):
            raise UnsupportedTable("CSV row has missing or extra cells")
        cells, offset = [], pos
        for piece, col in zip(pieces, spec.columns):
            if len(piece) > _MAX_CELL_BYTES or not _NUM.fullmatch(piece):
                raise UnsupportedTable("non-exact or malformed numeric CSV cell")
            cells.append(CSVCell(col.name, piece.decode("ascii"), offset, offset + len(piece)))
            offset += len(piece) + 1
        rows.append(CSVRow(rowno, pos, pos + len(line), tuple(cells), sha(line)))
        pos += len(physical_row)
    return tuple(rows)


def row_claim(row: CSVRow, spec: TableSpec, assertion: Assertion):
    """Build one closed, strictly parsed typed expression from exact CSV cells."""
    declarations = "".join(f"let {col.name} : {col.unit} = {cell.value}\n"
                           for col, cell in zip(spec.columns, row.cells))
    claim_line = "assert " + assertion.expression
    synthetic = Source.from_bytes(("PCS-TYPED/1\n" + declarations + claim_line + "\n").encode("utf-8"))
    start = synthetic.text.index(claim_line)
    raw = {"id": assertion.claim_id, "source_span": {"start": start, "end": start + len(claim_line)},
           "source_quote": claim_line, "assumptions": []}
    try:
        bindings = parse_bindings(synthetic)
        return parse_typed_claim(raw, synthetic, bindings)
    except (UnsupportedTyped, ValueError, TypeError, OverflowError, ZeroDivisionError) as exc:
        raise UnsupportedTable(f"typed template rejected at row {row.number}: {exc}") from exc


def run_table(source: Source, manifest_bytes: bytes, *, lean: LeanChecker | None = None) -> dict:
    """Full-table fail-closed validation precedes ANY Lean execution.

    Deliberately do not evaluate early rows when later rows/templates are bad:
    this prevents partial acceptance from a malformed or adversarial dataset.
    """
    from .pipeline import LeanChecker
    spec = parse_table_spec(manifest_bytes)
    rows = parse_table_rows(source, spec)
    prepared = [(r, a, row_claim(r, spec, a)) for r in rows for a in spec.assertions]
    if lean is None:
        lean = LeanChecker(executable="__pcs_missing_lean_executable__")
    results = []
    for row, assertion, claim in prepared:
        check = lean.check_typed(claim)
        results.append({
            "id": f"{assertion.claim_id}_row{row.number}",
            "row_number": row.number,
            "csv_row_span": {"start": row.start, "end": row.end},
            "csv_row_sha256": row.raw_sha256,
            "cell_anchors": [c.receipt() for c in row.cells],
            "template_id": assertion.claim_id,
            "template_expression_sha256": sha(assertion.expression.encode("utf-8")),
            "manifest_sha256": spec.raw_sha256,
            "data_sha256": source.digest,
            "ast_sha256": claim.to_dict()["ast_sha256"],
            "lhs_si": str(claim.lhs.quantity.value),
            "rhs_si": str(claim.rhs.quantity.value),
            "dimension": list(claim.lhs.quantity.dim),
            "formal_status": check["status"],
            "kernel_checked": check["kernel_checked"],
            "status": "SEMANTIC_REVIEW_REQUIRED",
            "semantic_fidelity": "UNREVIEWED",
            "scientific_status": "NOT_ASSESSED",
            "source_semantics": "Exact CSV cells and review-supplied schema/template; units/row meaning not certified",
            **{k: v for k, v in check.items() if k not in {"status", "kernel_checked"}},
        })
    return {
        "schema_version": _TABLE_SCHEMA,
        "authority": "EXPERIMENTAL_NOT_PCS_V06_AUTHORITY",
        "data_sha256": source.digest,
        "manifest_sha256": spec.raw_sha256,
        "header_columns": [c.name for c in spec.columns],
        "template_origin": "CALLER_SUPPLIED_UNATTESTED",
        "template_human_review_verified": False,
        "semantic_fidelity": "UNREVIEWED",
        "scientific_status": "NOT_ASSESSED",
        "scope": "Closed typed rational expressions over exact unquoted ASCII CSV cells, no empirical or semantic certification",
        "claims": results,
        "rejected": [],
        "reviewer_rejected": [],
        "counts": {"primary_proposed": len(prepared),
                   "accepted_grounding": len(prepared), "rejected_grounding": 0,
                   "kernel_checked": sum(r["kernel_checked"] for r in results),
                   "needs_review": len(results)},
    }
