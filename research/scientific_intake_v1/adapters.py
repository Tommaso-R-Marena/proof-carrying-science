"""Bounded, data-only scientific document extraction.

Extraction never certifies a claim, executes source, loads a pickle, evaluates a
formula, follows a link, or accesses the network. Locators refer to supplied bytes;
the inventory layer adds their exact artifact hash. Format support is deliberately
smaller than full application support and is described by ``capabilities()``.
"""
from __future__ import annotations

import ast
import csv
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import resource
import stat
import struct
import subprocess
import tempfile
from typing import Any
import xml.etree.ElementTree as ET
import zipfile
import zlib

from pcs.jsonio import strict_json_loads

VERSION = "1.0"
MAX_RAW_BYTES = 5 * 1024 * 1024
MAX_TEXT_CHARS = 1_000_000
MAX_SEGMENTS = 10_000
MAX_NODES = 50_000
MAX_DEPTH = 64
MAX_ROWS = 10_000
MAX_ZIP_MEMBERS = 512
MAX_EXPANDED_BYTES = 20 * 1024 * 1024
MAX_PDF_PAGES = 200
PDFTOTEXT = "/usr/bin/pdftotext"
UNVERIFIED = "Extraction is unverified source data; no extracted claim or numeric value is certified."

_FORMATS = {
    "text": {"extensions": [".txt", ".md", ".markdown", ".rst", ".log"], "scope": "strict UTF-8 lines"},
    "csv": {"extensions": [".csv", ".tsv"], "scope": "strict rows with a unique, nonempty header"},
    "json": {"extensions": [".json"], "scope": "strict finite JSON values and JSON Pointer locators"},
    "python": {"extensions": [".py"], "scope": "AST declarations, imports, constants and source; never executed"},
    "notebook": {"extensions": [".ipynb"], "scope": "notebook v4 source and stored, UNVERIFIED outputs; never executed"},
    "lean": {"extensions": [".lean"], "scope": "text declarations/imports; no compilation or proof verification"},
    "pdf": {"extensions": [".pdf"], "scope": "pdftotext text extraction, bounded to 200 pages; no OCR"},
    "docx": {"extensions": [".docx"], "scope": "OOXML body paragraphs and table cells; links forbidden"},
    "xlsx": {"extensions": [".xlsx"], "scope": "OOXML stored cell values/formulas; formulas never evaluated"},
    "fasta": {"extensions": [".fa", ".fasta", ".faa", ".fna"], "scope": "bounded sequence records and alphabet validation"},
    "pdb": {"extensions": [".pdb", ".ent"], "scope": "fixed-column ATOM/HETATM and SEQRES records"},
    "mmcif": {"extensions": [".cif", ".mmcif"], "scope": "bounded atom_site, struct_asym and entity_poly_seq loops"},
    "safetensors": {"extensions": [".safetensors"], "scope": "strict tensor header metadata only; no weight loading"},
    "onnx": {"extensions": [".onnx"], "scope": "bounded protobuf model metadata only; no inference or graph certification"},
}
_EXTENSIONS = {ext: name for name, spec in _FORMATS.items() for ext in spec["extensions"]}


def capabilities() -> dict[str, Any]:
    return {"version": VERSION, "formats": {name: {**spec, "extensions": list(spec["extensions"]), "available": (os.path.isfile(PDFTOTEXT) if name == "pdf" else True)} for name, spec in _FORMATS.items()},
            "limits": {"raw_bytes": MAX_RAW_BYTES, "text_chars": MAX_TEXT_CHARS, "segments": MAX_SEGMENTS,
                       "nodes": MAX_NODES, "depth": MAX_DEPTH, "rows": MAX_ROWS, "pdf_pages": MAX_PDF_PAGES,
                       "zip_members": MAX_ZIP_MEMBERS, "expanded_bytes": MAX_EXPANDED_BYTES},
            "execution": False, "network": False, "certification": False,
            "opaque_model_extensions": [".pt", ".pth", ".pkl", ".pickle", ".bin", ".ckpt", ".h5", ".hdf5"]}


class Unsupported(ValueError):
    """A known format whose required feature is outside the declared subset."""


def _segment(locator: dict, text: str, kind: str, data: dict | None = None) -> dict:
    return {"locator": locator, "text": text, "kind": kind, "data": data or {}}


def _utf8(raw: bytes) -> str:
    text = raw.decode("utf-8-sig", errors="strict")
    if "\x00" in text:
        raise ValueError("NUL bytes are not supported in textual inputs")
    if len(text) > MAX_TEXT_CHARS:
        raise ValueError("text character limit exceeded")
    return text


def _check_tree(value: Any) -> None:
    stack = [(value, 0)]
    count = 0
    while stack:
        item, depth = stack.pop()
        count += 1
        if count > MAX_NODES or depth > MAX_DEPTH:
            raise ValueError("JSON structure limit exceeded")
        if isinstance(item, float) and not math.isfinite(item):
            raise ValueError("non-finite JSON number")
        if isinstance(item, dict):
            stack.extend((v, depth + 1) for v in item.values())
        elif isinstance(item, list):
            stack.extend((v, depth + 1) for v in item)


def _json(raw: bytes) -> Any:
    value = strict_json_loads(_utf8(raw))
    _check_tree(value)
    return value


def _text(raw: bytes) -> list[dict]:
    lines = _utf8(raw).splitlines()
    if len(lines) > MAX_SEGMENTS:
        raise ValueError("text line limit exceeded")
    return [_segment({"line": number}, line, "text_line") for number, line in enumerate(lines, 1)]


def _csv(raw: bytes, delimiter: str) -> list[dict]:
    # csv.field_size_limit is process-global: leave it unchanged and use its safe
    # stdlib default plus our independent whole-input and row bounds.
    reader = csv.reader(io.StringIO(_utf8(raw), newline=""), delimiter=delimiter, strict=True)
    try:
        headers = next(reader)
    except StopIteration:
        raise ValueError("CSV has no header")
    if not headers or any(not h.strip() for h in headers) or len(set(headers)) != len(headers):
        raise ValueError("CSV headers must be nonempty and unique")
    if len(headers) > 1024:
        raise ValueError("CSV column limit exceeded")
    result = [_segment({"row": 1, "line_start": 1, "line_end": reader.line_num}, delimiter.join(headers), "csv_header", {"headers": headers})]
    previous_line = reader.line_num
    for row_number, row in enumerate(reader, 2):
        if row_number > MAX_ROWS + 1:
            raise ValueError("CSV row limit exceeded")
        if len(row) != len(headers):
            raise ValueError(f"CSV row {row_number} has a different column count")
        result.append(_segment({"row": row_number, "line_start": previous_line + 1, "line_end": reader.line_num}, delimiter.join(row), "csv_row", {"headers": headers, "values": row, "row": row_number}))
        previous_line = reader.line_num
    return result


def _json_segments(raw: bytes) -> list[dict]:
    value = _json(raw)
    result = []
    stack = [("", value)]
    while stack:
        pointer, item = stack.pop()
        if isinstance(item, dict) and item:
            stack.extend((pointer + "/" + key.replace("~", "~0").replace("/", "~1"), val) for key, val in reversed(list(item.items())))
        elif isinstance(item, list) and item:
            stack.extend((pointer + "/" + str(index), item[index]) for index in reversed(range(len(item))))
        else:
            result.append(_segment({"json_pointer": pointer}, json.dumps(item, ensure_ascii=False, allow_nan=False), "json_value", {"value": item}))
        if len(result) > MAX_SEGMENTS:
            raise ValueError("JSON segment limit exceeded")
    return result


def _python(raw: bytes) -> list[dict]:
    text = _utf8(raw)
    tree = ast.parse(text, mode="exec")
    nodes = list(ast.walk(tree))
    if len(nodes) > MAX_NODES:
        raise ValueError("Python AST node limit exceeded")
    stack = [(tree, 0)]
    while stack:
        node, depth = stack.pop()
        if depth > MAX_DEPTH:
            raise ValueError("Python AST depth limit exceeded")
        stack.extend((child, depth + 1) for child in ast.iter_child_nodes(node))
    lines = text.splitlines()
    result = []
    for node in nodes:
        if not isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Assign, ast.AnnAssign)):
            continue
        locator = {"line_start": node.lineno, "line_end": node.end_lineno}
        source = "\n".join(lines[node.lineno - 1:node.end_lineno])
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    result.append(_segment(locator, source, "python_import", {"module": alias.name, "names": [alias.name]}))
                continue
            data = {"module": "." * node.level + (node.module or ""), "names": [alias.name for alias in node.names]}
            kind = "python_import"
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            data = {"name": node.name, "declaration": type(node).__name__}
            kind = "python_declaration"
        else:
            value = node.value
            data = {"value": value.value} if isinstance(value, ast.Constant) and isinstance(value.value, (str, int, float, bool, type(None))) else {"expression": "unexecuted"}
            if isinstance(data.get("value"), float) and not math.isfinite(data["value"]):
                data = {"expression": "non-finite numeric literal, unexecuted"}
            kind = "python_data"
        result.append(_segment(locator, source, kind, data))
    if not result and text:
        result = [_segment({"line_start": 1, "line_end": len(lines)}, text, "python_source", {"execution": "NEVER"})]
    return result


def _notebook(raw: bytes) -> list[dict]:
    notebook = _json(raw)
    if not isinstance(notebook, dict) or notebook.get("nbformat") != 4 or not isinstance(notebook.get("cells"), list):
        raise ValueError("expected a notebook v4 cells array")
    result = []

    def source_string(value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, list) and all(isinstance(line, str) for line in value):
            return "".join(value)
        raise ValueError("notebook text must be a string or string array")

    for cell_number, cell in enumerate(notebook["cells"], 1):
        if not isinstance(cell, dict) or cell.get("cell_type") not in {"code", "markdown", "raw"}:
            raise ValueError("invalid notebook cell")
        source = source_string(cell.get("source", ""))
        execution_count = cell.get("execution_count")
        if execution_count is not None and (type(execution_count) is not int or execution_count < 0):
            raise ValueError("invalid stored notebook execution count")
        result.append(_segment({"cell": cell_number, "part": "source"}, source, "notebook_source", {"cell_type": cell["cell_type"], "execution_count": execution_count, "execution": "NEVER"}))
        outputs = cell.get("outputs", [])
        if not isinstance(outputs, list) or (outputs and cell["cell_type"] != "code"):
            raise ValueError("invalid notebook outputs")
        for output_number, output in enumerate(outputs, 1):
            if not isinstance(output, dict):
                raise ValueError("invalid notebook output")
            output_type = output.get("output_type")
            mimetypes = []
            if output_type == "stream":
                value = source_string(output.get("text", ""))
            elif output_type in {"display_data", "execute_result"}:
                stored = output.get("data", {})
                if not isinstance(stored, dict):
                    raise ValueError("notebook output data must be an object")
                mimetypes = list(stored)
                value = source_string(stored["text/plain"]) if "text/plain" in stored else "[stored rich output omitted; unverified]"
            elif output_type == "error":
                value = source_string(output.get("traceback", []))
            else:
                raise ValueError("unknown notebook output type")
            stored_count = output.get("execution_count")
            if stored_count is not None and (type(stored_count) is not int or stored_count < 0):
                raise ValueError("invalid stored output execution count")
            result.append(_segment({"cell": cell_number, "output": output_number, "part": "stored_output"}, value, "notebook_output", {"output_type": output_type, "stored_output_status": "UNVERIFIED", "execution_count": execution_count, "output_execution_count": stored_count, "mimetypes": mimetypes}))
    return result


def _lean(raw: bytes) -> list[dict]:
    text = _utf8(raw)
    # Strip nested comments for declaration recognition, retaining line locations.
    clean = []
    index = depth = 0
    in_string = False
    escaped = False
    while index < len(text):
        pair = text[index:index + 2]
        char = text[index]
        if depth:
            if pair == "/-":
                depth += 1
                clean.extend("  ")
                index += 2
                continue
            if pair == "-/":
                depth -= 1
                clean.extend("  ")
                index += 2
                continue
            clean.append("\n" if char == "\n" else " ")
        elif not in_string and pair == "/-":
            depth = 1
            clean.extend("  ")
            index += 2
            continue
        elif not in_string and pair == "--":
            end = text.find("\n", index)
            end = len(text) if end < 0 else end
            clean.extend(" " * (end - index))
            index = end
            continue
        else:
            clean.append(char)
            if char == '"' and not escaped:
                in_string = not in_string
            escaped = char == "\\" and not escaped
            if char != "\\":
                escaped = False
        index += 1
    if depth or in_string:
        raise ValueError("unterminated Lean comment or string")
    result = []
    original = text.splitlines()
    declaration = re.compile(r"^\s*(?:(?:private|protected|noncomputable|unsafe|partial)\s+)*(theorem|lemma|def|abbrev|axiom|constant|opaque|inductive|structure|class|instance)\s+([^\s:(\[{]+)?")
    for line_number, line in enumerate("".join(clean).splitlines(), 1):
        match = declaration.match(re.sub(r"^(?:\s*@\[[^]\n]{1,128}\])+\s*", "", line))
        imported = re.match(r"^\s*import\s+(.+?)\s*$", line)
        if match:
            result.append(_segment({"line": line_number}, original[line_number - 1], "lean_declaration", {"declaration": original[line_number - 1], "declaration_kind": match.group(1), "name": match.group(2) or "<anonymous>", "proof_status": "UNVERIFIED"}))
        elif imported:
            result.append(_segment({"line": line_number}, original[line_number - 1], "lean_import", {"modules": imported.group(1).split(), "execution": "NEVER"}))
    if not result and text:
        result.append(_segment({"line_start": 1, "line_end": len(original)}, text, "lean_source", {"proof_status": "UNVERIFIED"}))
    return result


def _pdf_limits() -> None:
    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (2 * 1024 * 1024, 2 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def _pdf(raw: bytes) -> list[dict]:
    if not raw.startswith(b"%PDF-"):
        raise ValueError("missing PDF signature")
    if not os.path.isfile(PDFTOTEXT):
        raise Unsupported("pdftotext is unavailable")
    with tempfile.TemporaryDirectory(prefix="pcs-intake-pdf-") as directory:
        root = Path(directory)
        source, target = root / "source.pdf", root / "text.txt"
        source.write_bytes(raw)
        with (root / "stderr.txt").open("wb") as errors:
            completed = subprocess.run([PDFTOTEXT, "-f", "1", "-l", str(MAX_PDF_PAGES + 1), "-enc", "UTF-8", "-layout", str(source), str(target)],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=errors,
                cwd=directory, env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"}, timeout=8,
                check=False, close_fds=True, preexec_fn=_pdf_limits)
        if completed.returncode != 0 or not target.is_file():
            raise ValueError("PDF text extraction failed")
        output = target.read_bytes()
    text = _utf8(output)
    pages = text.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    if len(pages) > MAX_PDF_PAGES:
        raise ValueError("PDF page limit exceeded")
    if not any(page.strip() for page in pages):
        raise Unsupported("PDF contains no extractable text; OCR is not supported")
    return [_segment({"page": page_number}, page.rstrip(), "pdf_page", {"extraction": "pdftotext", "ocr": False}) for page_number, page in enumerate(pages, 1)]


def _archive(raw: bytes) -> tuple[zipfile.ZipFile, dict[str, zipfile.ZipInfo]]:
    archive = zipfile.ZipFile(io.BytesIO(raw))
    members = {}
    total = 0
    infos = archive.infolist()
    if len(infos) > MAX_ZIP_MEMBERS:
        archive.close()
        raise ValueError("OOXML member limit exceeded")
    for info in infos:
        name = info.filename
        path = PurePosixPath(name)
        mode = info.external_attr >> 16
        if not name or info.orig_filename != name or "\\" in name or "\x00" in info.orig_filename or any(ord(c) < 32 for c in name) or path.is_absolute() or any(part in {"..", "."} for part in name.split("/")) or ":" in name or stat.S_ISLNK(mode):
            archive.close()
            raise ValueError("unsafe OOXML member path or symlink")
        if name in members or info.flag_bits & 1:
            archive.close()
            raise ValueError("duplicate or encrypted OOXML member")
        if info.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}:
            archive.close()
            raise ValueError("unsupported OOXML compression method")
        total += info.file_size
        if info.file_size > MAX_RAW_BYTES or total > MAX_EXPANDED_BYTES or (info.file_size > 100_000 and info.file_size > 200 * max(info.compress_size, 1)):
            archive.close()
            raise ValueError("OOXML decompression limit exceeded")
        members[name] = info
    return archive, members


def _xml(archive: zipfile.ZipFile, members: dict, name: str) -> ET.Element:
    if name not in members:
        raise ValueError(f"missing OOXML member: {name}")
    raw = archive.read(members[name])
    # Office XML is UTF-8 in this subset. NUL rejection also blocks UTF-16 DTDs.
    text = _utf8(raw)
    if "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
        raise ValueError("XML DTDs and entities are forbidden")
    root = ET.fromstring(text)
    stack = [(root, 0)]
    count = 0
    while stack:
        item, depth = stack.pop()
        count += 1
        if count > MAX_NODES or depth > MAX_DEPTH:
            raise ValueError("XML structure limit exceeded")
        stack.extend((child, depth + 1) for child in item)
    return root


def _relationships(archive: zipfile.ZipFile, members: dict) -> None:
    for name in members:
        if name.endswith(".rels"):
            root = _xml(archive, members, name)
            for relationship in root:
                target = relationship.attrib.get("Target", "")
                if relationship.attrib.get("TargetMode", "").lower() == "external" or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("//"):
                    raise ValueError("external OOXML relationships are forbidden")


_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def _word_text(element: ET.Element) -> str:
    parts = []
    for node in element.iter():
        if node.tag == _W + "t":
            parts.append(node.text or "")
        elif node.tag == _W + "tab":
            parts.append("\t")
        elif node.tag in {_W + "br", _W + "cr"}:
            parts.append("\n")
    return "".join(parts)


def _docx(raw: bytes) -> list[dict]:
    archive, members = _archive(raw)
    with archive:
        _relationships(archive, members)
        root = _xml(archive, members, "word/document.xml")
        body = root.find(_W + "body")
        if body is None:
            raise ValueError("DOCX has no document body")
        result = []
        paragraph_number = table_number = 0
        for child in body:
            if child.tag == _W + "p":
                paragraph_number += 1
                result.append(_segment({"paragraph": paragraph_number}, _word_text(child), "docx_paragraph"))
            elif child.tag == _W + "tbl":
                table_number += 1
                for row_number, row in enumerate(child.findall(_W + "tr"), 1):
                    for column, cell in enumerate(row.findall(_W + "tc"), 1):
                        if cell.find(".//" + _W + "tbl") is not None:
                            raise Unsupported("nested DOCX tables are outside the supported subset")
                        value = "\n".join(_word_text(p) for p in cell.findall(_W + "p"))
                        result.append(_segment({"table": table_number, "row": row_number, "column": column}, value, "docx_table_cell", {"value": value}))
            elif child.tag != _W + "sectPr":
                raise Unsupported("DOCX body element is outside the supported subset")
    return result


def _cell_value(cell: ET.Element, shared: list[str]) -> tuple[Any, str]:
    cell_type = cell.attrib.get("t", "n")
    value = cell.findtext(_S + "v", default="")
    if cell_type == "s":
        if not value.isdigit() or int(value) >= len(shared):
            raise ValueError("XLSX shared-string index is invalid")
        return shared[int(value)], cell_type
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.iter(_S + "t")), cell_type
    if cell_type == "b":
        if value not in {"0", "1"}:
            raise ValueError("invalid XLSX boolean")
        return value == "1", cell_type
    if cell_type in {"str", "e", "d"}:
        return value, cell_type
    if cell_type != "n":
        raise Unsupported("XLSX cell type is unsupported")
    if not value:
        return None, cell_type
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("non-finite XLSX number")
    return (int(value) if re.fullmatch(r"[-+]?\d+", value) else number), cell_type


def _xlsx(raw: bytes) -> list[dict]:
    archive, members = _archive(raw)
    with archive:
        _relationships(archive, members)
        book = _xml(archive, members, "xl/workbook.xml")
        rels = _xml(archive, members, "xl/_rels/workbook.xml.rels")
        targets = {}
        for rel in rels:
            target = rel.attrib.get("Target", "")
            if target.startswith("/"):
                target = target[1:]
            else:
                target = "xl/" + target
            if ".." in PurePosixPath(target).parts or "\\" in target or not target.startswith("xl/"):
                raise ValueError("unsafe XLSX sheet target")
            targets[rel.attrib.get("Id")] = target
        shared = []
        if "xl/sharedStrings.xml" in members:
            strings = _xml(archive, members, "xl/sharedStrings.xml")
            shared = ["".join(t.text or "" for t in item.iter(_S + "t")) for item in strings.findall(_S + "si")]
        sheets = book.find(_S + "sheets")
        if sheets is None:
            raise ValueError("XLSX has no sheets")
        result = []
        seen_sheets = set()
        for sheet in sheets:
            name = sheet.attrib.get("name", "")
            if not name or name in seen_sheets:
                raise ValueError("XLSX sheet names must be nonempty and unique")
            seen_sheets.add(name)
            target = targets.get(sheet.attrib.get(_R + "id"))
            if not target:
                raise ValueError("XLSX sheet relationship is missing")
            worksheet = _xml(archive, members, target)
            seen = set()
            rows = worksheet.findall("./" + _S + "sheetData/" + _S + "row")
            if len(rows) > MAX_ROWS:
                raise ValueError("XLSX row limit exceeded")
            for row in rows:
                for cell in row.findall(_S + "c"):
                    reference = cell.attrib.get("r", "")
                    match = re.fullmatch(r"([A-Z]{1,3})([1-9][0-9]{0,6})", reference)
                    if not match or reference in seen:
                        raise ValueError("invalid or duplicate XLSX cell reference")
                    column, row_index = match.group(1), int(match.group(2))
                    column_index = 0
                    for letter in column:
                        column_index = column_index * 26 + ord(letter) - 64
                    if column_index > 16384 or row_index > 1048576 or row.attrib.get("r", str(row_index)) != str(row_index):
                        raise ValueError("XLSX cell is outside its row or valid range")
                    seen.add(reference)
                    value, cell_type = _cell_value(cell, shared)
                    data = {"value": value, "cell_type": cell_type}
                    formula = cell.find(_S + "f")
                    if formula is not None:
                        data.update(formula=formula.text or "", formula_status="UNVERIFIED")
                    result.append(_segment({"sheet": name, "cell": reference, "row": row_index, "column": column}, "" if value is None else str(value), "xlsx_cell", data))
                    if len(result) > MAX_SEGMENTS:
                        raise ValueError("XLSX cell limit exceeded")
    return result


def _safetensors(raw: bytes) -> list[dict]:
    if len(raw) < 8:
        raise ValueError("safetensors header is missing")
    header_size = struct.unpack("<Q", raw[:8])[0]
    if not 2 <= header_size <= min(1024 * 1024, len(raw) - 8):
        raise ValueError("safetensors header size is invalid")
    header = _json(raw[8:8 + header_size])
    if not isinstance(header, dict):
        raise ValueError("safetensors header must be an object")
    widths = {"BOOL": 1, "U8": 1, "I8": 1, "I16": 2, "U16": 2, "F16": 2, "BF16": 2, "I32": 4, "U32": 4, "F32": 4, "I64": 8, "U64": 8, "F64": 8, "F8_E4M3": 1, "F8_E5M2": 1}
    result, ranges = [], []
    data_size = len(raw) - 8 - header_size
    for name, descriptor in header.items():
        if name == "__metadata__":
            if not isinstance(descriptor, dict) or not all(isinstance(v, str) for v in descriptor.values()):
                raise ValueError("invalid safetensors metadata")
            result.append(_segment({"json_pointer": "/__metadata__", "byte_offset": 8}, json.dumps(descriptor, ensure_ascii=False), "model_metadata", {"metadata": descriptor, "weights_loaded": False}))
            continue
        if not isinstance(descriptor, dict):
            raise ValueError("invalid safetensors tensor descriptor")
        dtype, shape, offsets = descriptor.get("dtype"), descriptor.get("shape"), descriptor.get("data_offsets")
        if dtype not in widths:
            raise Unsupported("safetensors dtype is outside the supported metadata subset")
        if not isinstance(shape, list) or len(shape) > 64 or any(type(dim) is not int or dim < 0 or dim > 2**31 for dim in shape):
            raise ValueError("invalid safetensors shape")
        if not isinstance(offsets, list) or len(offsets) != 2 or any(type(v) is not int for v in offsets) or not 0 <= offsets[0] <= offsets[1] <= data_size:
            raise ValueError("invalid safetensors offsets")
        elements = math.prod(shape)
        if elements * widths[dtype] != offsets[1] - offsets[0]:
            raise ValueError("safetensors tensor size does not match shape")
        ranges.append(tuple(offsets))
        result.append(_segment({"tensor": name, "json_pointer": "/" + name.replace("~", "~0").replace("/", "~1"), "byte_offset": 8}, name, "model_tensor_metadata", {"name": name, "dtype": dtype, "shape": shape, "data_offsets": offsets, "weights_loaded": False}))
    end = 0
    for start, stop in sorted(ranges):
        if start != end:
            raise ValueError("safetensors data ranges overlap or have gaps")
        end = stop
    if end != data_size:
        raise ValueError("safetensors has unreferenced data bytes")
    return result


def _protobuf(raw: bytes) -> list[tuple[int, int, Any, int]]:
    offset = 0
    fields = []

    def varint() -> int:
        nonlocal offset
        value = 0
        for shift in range(0, 70, 7):
            if offset >= len(raw):
                raise ValueError("truncated ONNX varint")
            byte = raw[offset]
            offset += 1
            if shift == 63 and byte > 1:
                raise ValueError("overflowed ONNX varint")
            value |= (byte & 127) << shift
            if byte < 128:
                return value
        raise ValueError("ONNX varint limit exceeded")

    while offset < len(raw):
        start = offset
        tag = varint()
        number, wire = tag >> 3, tag & 7
        if not number:
            raise ValueError("invalid ONNX field number")
        if wire == 0:
            value = varint()
        elif wire == 2:
            length = varint()
            if length > len(raw) - offset:
                raise ValueError("truncated ONNX field")
            value = raw[offset:offset + length]
            offset += length
        elif wire in {1, 5}:
            length = 8 if wire == 1 else 4
            if length > len(raw) - offset:
                raise ValueError("truncated ONNX fixed field")
            value = raw[offset:offset + length]
            offset += length
        else:
            raise ValueError("unsupported ONNX protobuf wire type")
        fields.append((number, wire, value, start))
        if len(fields) > MAX_NODES:
            raise ValueError("ONNX field limit exceeded")
    return fields


def _onnx(raw: bytes) -> list[dict]:
    fields = _protobuf(raw)
    names = {1: "ir_version", 2: "producer_name", 3: "producer_version", 4: "domain", 5: "model_version", 6: "doc_string"}
    result = []
    seen = set()
    has_graph = False
    for number, wire, value, offset in fields:
        if number in names:
            if number in seen or wire != (0 if number in {1, 5} else 2):
                raise ValueError("invalid or duplicate ONNX metadata field")
            seen.add(number)
            value = ((value - (1 << 64)) if value >= (1 << 63) else value) if wire == 0 else _utf8(value)
            name = names[number]
            result.append(_segment({"protobuf_field": name, "byte_offset": offset}, str(value), "model_metadata", {"field": name, "value": value, "weights_loaded": False, "graph_validated": False}))
        elif number == 7:
            if has_graph or wire != 2:
                raise ValueError("invalid ONNX graph field")
            has_graph = True
            graph_fields = _protobuf(value)
            for child_number, child_wire, child_value, child_offset in graph_fields:
                if child_number == 2:
                    if child_wire != 2:
                        raise ValueError("invalid ONNX graph name")
                    name = _utf8(child_value)
                    result.append(_segment({"protobuf_field": "graph.name", "byte_offset": offset, "nested_byte_offset": child_offset}, name, "model_metadata", {"field": "graph.name", "value": name, "weights_loaded": False, "graph_validated": False}))
    if 1 not in seen or not has_graph:
        raise ValueError("ONNX requires IR version and a graph field")
    return result


def extract(name: str, raw: bytes) -> dict[str, Any]:
    """Extract bounded source segments; malformed/over-limit input fails closed."""
    adapter = _EXTENSIONS.get(PurePosixPath(name.replace("\\", "/")).suffix.lower(), "unsupported") if isinstance(name, str) else "unsupported"
    result = {"adapter": adapter, "version": VERSION, "status": "ERROR", "segments": [], "warnings": [UNVERIFIED], "capabilities": capabilities()}
    try:
        if not isinstance(name, str) or not name or "\x00" in name or not isinstance(raw, bytes):
            raise ValueError("expected a nonempty artifact name and immutable bytes")
        if len(raw) > MAX_RAW_BYTES:
            raise ValueError("raw byte limit exceeded")
        if adapter == "unsupported":
            raise Unsupported("unsupported or opaque artifact format; bytes were not executed or deserialized")
        if adapter == "text":
            segments = _text(raw)
        elif adapter == "csv":
            segments = _csv(raw, "\t" if name.lower().endswith(".tsv") else ",")
        elif adapter == "json":
            segments = _json_segments(raw)
        elif adapter == "python":
            segments = _python(raw)
        elif adapter == "notebook":
            segments = _notebook(raw)
        elif adapter == "lean":
            segments = _lean(raw)
        elif adapter == "pdf":
            segments = _pdf(raw)
        elif adapter == "docx":
            segments = _docx(raw)
        elif adapter == "xlsx":
            segments = _xlsx(raw)
        elif adapter in {"fasta", "pdb", "mmcif"}:
            from . import bio_adapters
            segments = getattr(bio_adapters, "extract_" + adapter)(_utf8(raw))
        elif adapter == "safetensors":
            segments = _safetensors(raw)
        else:
            segments = _onnx(raw)
        if len(segments) > MAX_SEGMENTS or sum(len(segment["text"]) for segment in segments) > MAX_TEXT_CHARS:
            raise ValueError("extracted segment/text limit exceeded")
        # Guarantee a strict JSON-compatible return, including bounded data fields.
        json.dumps(segments, allow_nan=False)
        result.update(status="EXTRACTED", segments=segments)
        if adapter in {"notebook", "lean", "xlsx", "safetensors", "onnx"}:
            result["warnings"].append("Stored outputs, formulas, proof declarations and model metadata are UNVERIFIED and were not executed.")
    except Unsupported as exc:
        result.update(status="UNSUPPORTED", warnings=[UNVERIFIED, str(exc)])
    except (ValueError, TypeError, KeyError, IndexError, OverflowError, RecursionError, OSError, SyntaxError, csv.Error, zipfile.BadZipFile, zipfile.LargeZipFile, zlib.error, ET.ParseError, subprocess.SubprocessError) as exc:
        result.update(status="ERROR", warnings=[UNVERIFIED, f"{type(exc).__name__}: {str(exc)[:300]}"])
    return result
